from datetime import UTC, datetime

import pytest
from jocky_contracts.agent import AgentObservation, AgentSignedJob, JobState, validate_transition
from jocky_contracts.common import Provenance, Signature
from jocky_contracts.compiler import Budget, CompilerMetrics, LiteralEncryption
from jocky_contracts.evidence import AuditEvent, integrity_hash, verify_audit_chain
from pydantic import ValidationError


def test_simulation_requires_presence_and_visible_label():
    with pytest.raises(ValidationError):
        Provenance()
    with pytest.raises(ValidationError):
        Provenance(simulation=True)
    with pytest.raises(ValidationError):
        Provenance(simulation=False, simulation_label="SIMULATED")
    assert Provenance(simulation=True, simulation_label="SIMULATED lab").simulation is True


@pytest.mark.parametrize("value", ["false", "true", 0, 1, None])
def test_simulation_flag_cannot_be_coerced(value):
    with pytest.raises(ValidationError):
        Provenance(simulation=value)


@pytest.mark.parametrize(
    "source,target",
    [
        (JobState.CREATED, JobState.SUCCESS),
        (JobState.QUEUED, JobState.VERIFIED),
        (JobState.CANCELLED, JobState.RUNNING),
        (JobState.ARCHIVED, JobState.CREATED),
        (JobState.FAILED, JobState.QUEUED),
        (JobState.SUCCESS, JobState.ARCHIVED),
    ],
)
def test_invalid_transitions_cannot_skip_execution_or_verification(source, target):
    with pytest.raises(ValueError):
        validate_transition(source, target)


def test_success_path_and_failure_cancellation_branches():
    path = [
        JobState.CREATED,
        JobState.COMPILED,
        JobState.VALIDATED,
        JobState.QUEUED,
        JobState.DISPATCHED,
        JobState.RUNNING,
        JobState.SUCCESS,
        JobState.VERIFIED,
        JobState.ARCHIVED,
    ]
    for current, target in zip(path, path[1:], strict=False):
        validate_transition(current, target)
    validate_transition(JobState.RUNNING, JobState.CANCELLED)
    validate_transition(JobState.DISPATCHED, JobState.FAILED)


@pytest.mark.parametrize(
    "field,value",
    [
        ("cpu_percent", 0),
        ("cpu_percent", 101),
        ("memory_bytes", 0),
        ("io_bytes", -1),
        ("duration_ms", 0),
        ("duration_ms", 86_400_001),
    ],
)
def test_budget_rejects_invalid_limits(field, value):
    payload = dict(
        cpu_percent=20, memory_bytes=256_000_000, io_bytes=150_000_000, duration_ms=120_000
    )
    payload[field] = value
    with pytest.raises(ValidationError):
        Budget.model_validate(payload)


def test_missing_metrics_stay_null_and_nonfinite_values_fail():
    assert CompilerMetrics().lex_ms is None
    with pytest.raises(ValidationError):
        CompilerMetrics(lex_ms=float("nan"))
    with pytest.raises(ValidationError):
        CompilerMetrics(parse_ms=-1)


def test_incomplete_encryption_or_signature_cannot_claim_enabled():
    with pytest.raises(ValidationError):
        LiteralEncryption(enabled=True)
    with pytest.raises(ValidationError):
        Signature(status="VERIFIED")
    with pytest.raises(ValidationError):
        Signature(status="UNSIGNED", key_id="key-one")


def audit(sequence=0, previous="0" * 64):
    event = AuditEvent(
        simulation=True,
        simulation_label="SIMULATED audit test",
        sequence=sequence,
        organization_id="fixture-org",
        actor_id="fixture-operator",
        action="case.opened",
        timestamp=datetime(2026, 9, 12, tzinfo=UTC),
        resource_id="fixture-case",
        previous_hash=previous,
        data={"label": "fixture"},
        integrity_hash="0" * 64,
    )
    return event.model_copy(update={"integrity_hash": integrity_hash(event)})


def test_audit_tampering_reordering_and_empty_chain():
    first = audit()
    second = audit(1, first.integrity_hash)
    assert verify_audit_chain([first, second]).integrity_valid
    assert not verify_audit_chain([]).integrity_valid
    assert not verify_audit_chain([second, first]).integrity_valid
    altered = second.model_copy(update={"action": "evidence.deleted"})
    assert not verify_audit_chain([first, altered]).integrity_valid
    assert verify_audit_chain([first, altered]).first_invalid_sequence == 1
    assert verify_audit_chain([first]).externally_anchored is False


def test_cross_organization_audit_link_rejected_even_with_valid_hash():
    first = audit()
    second = audit(1, first.integrity_hash).model_copy(update={"organization_id": "other-org"})
    second = second.model_copy(update={"integrity_hash": integrity_hash(second)})
    assert not verify_audit_chain([first, second]).integrity_valid


def test_real_agent_observation_rejects_simulation_and_unknown_fields():
    payload = {
        "simulation": False,
        "simulation_label": None,
        "observation_id": "observation-1",
        "endpoint_id": "endpoint-1",
        "job_id": "job-1",
        "case_id": "case-1",
        "collector": "system",
        "observed_at": datetime(2026, 9, 13, tzinfo=UTC),
        "source_time": None,
        "platform": {"os": "linux", "arch": "x86_64"},
        "data": {"hostname": "host-one", "cpu_count": 8},
        "integrity_hash": "a" * 64,
    }
    observation = AgentObservation.model_validate(payload)
    assert observation.simulation is False
    with pytest.raises(ValidationError):
        AgentObservation.model_validate(payload | {"simulation": True, "simulation_label": "test"})
    with pytest.raises(ValidationError):
        AgentObservation.model_validate(payload | {"unexpected": "field"})


def test_agent_job_requires_real_signed_expiring_envelope():
    payload = {
        "simulation": False,
        "simulation_label": None,
        "job_id": "job-1",
        "case_id": "case-1",
        "organization_id": "org-1",
        "endpoint_id": "endpoint-1",
        "required_capabilities": ["system.read"],
        "collectors": [{"collector": "system"}],
        "budget": {
            "cpu_percent": 20,
            "memory_bytes": 256_000_000,
            "io_bytes": 150_000_000,
            "duration_ms": 120_000,
            "max_result_bytes": 32_000_000,
            "max_file_count": 10_000,
            "max_file_bytes": 150_000_000,
        },
        "enforcement_policy": "MONITORED",
        "nonce": "b" * 64,
        "issued_at": datetime(2026, 9, 13, tzinfo=UTC),
        "expires_at": datetime(2026, 9, 13, 0, 5, tzinfo=UTC),
        "signature": {
            "status": "SIGNED",
            "algorithm": "Ed25519",
            "key_id": "local-dev-authority",
            "value_base64": "fixture-signature",
        },
    }
    assert AgentSignedJob.model_validate(payload).collectors[0].collector == "system"
    with pytest.raises(ValidationError):
        AgentSignedJob.model_validate(payload | {"expires_at": payload["issued_at"]})
