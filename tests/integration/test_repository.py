import importlib.util
import json
from pathlib import Path

import jsonschema
from jocky_contracts.evidence import Observation, canonical_bytes

ROOT = Path(__file__).resolve().parents[2]


def test_required_architecture_docs_exist_and_are_substantive():
    names = [
        "PRODUCT_SPEC",
        "ARCHITECTURE",
        "LANGUAGE_SPEC",
        "JIR_SPEC",
        "SECURITY_MODEL",
        "THREAT_MODEL",
        "REQUIREMENT_TRACEABILITY",
        "DEFINITION_OF_DONE",
        "DEMO_FLOW",
        "BUILD_STATUS",
        "API",
        "BENCHMARK_PLAN",
    ]
    for name in names:
        path = ROOT / "docs" / f"{name}.md"
        assert path.is_file(), path
        assert len(path.read_text()) > 1000, path


def test_json_schema_validates_fixture_and_canonical_golden_bytes():
    bundle = json.loads((ROOT / "packages/contracts/generated/contracts.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(bundle)
    data = json.loads((ROOT / "fixtures/evidence/simulated-observation.json").read_text())
    jsonschema.validate({"Observation": data}, bundle)
    observation = Observation.model_validate(data)
    expected = (ROOT / "fixtures/evidence/simulated-observation.canonical.json").read_bytes()
    assert canonical_bytes(observation, {"integrity_hash"}) == expected


def test_every_committed_synthetic_json_record_is_labeled():
    for path in (ROOT / "fixtures").rglob("*.json"):
        if ".canonical." in path.name:
            continue
        data = json.loads(path.read_text())
        assert data["simulation"] is True, path
        assert "SIMULATED" in data["simulation_label"], path


def test_documented_coverage_matches_backend_catalog():
    spec = importlib.util.spec_from_file_location(
        "generate_coverage", ROOT / "scripts/generate_coverage.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert (ROOT / "docs/REQUIREMENT_TRACEABILITY.md").read_text(
        encoding="utf-8"
    ) == module.render()
