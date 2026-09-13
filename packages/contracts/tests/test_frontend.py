"""Validate actual native compiler snapshots against the Python contract authority."""

import hashlib
import json
from pathlib import Path

import jsonschema
import pytest
from jocky_contracts.frontend import FrontendExecutionPlan, JirModule
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[3]
GOLDENS = ROOT / "fixtures/compiler"


@pytest.mark.parametrize("path", sorted(GOLDENS.glob("*.jir.canonical.json")), ids=lambda p: p.stem)
def test_native_jir_contract(path: Path) -> None:
    raw = json.loads(path.read_text())
    module = JirModule.model_validate(raw)
    jsonschema.Draft202012Validator(JirModule.model_json_schema()).validate(raw)
    plan_path = path.with_name(path.name.replace(".jir.", ".plan."))
    raw_plan = json.loads(plan_path.read_text())
    plan = FrontendExecutionPlan.model_validate(raw_plan)
    jsonschema.Draft202012Validator(FrontendExecutionPlan.model_json_schema()).validate(raw_plan)
    assert plan.jir_hash == hashlib.sha256(path.read_bytes().rstrip(b"\n")).hexdigest()
    assert plan.source_hash == module.source_hash
    assert not module.executable and not plan.dispatchable
    assert [s.result_type for s in plan.expected_result_schemas] == [
        i.result_type for i in module.instructions
    ]


def test_frontend_rejects_tampered_effects_and_executable_claim() -> None:
    raw = json.loads((GOLDENS / "system.jir.canonical.json").read_text())
    raw["instructions"][0]["effect_predecessor"] = 0
    with pytest.raises(ValidationError, match="effect chain"):
        JirModule.model_validate(raw)
    raw["instructions"][0]["effect_predecessor"] = None
    raw["executable"] = True
    with pytest.raises(ValidationError):
        JirModule.model_validate(raw)
