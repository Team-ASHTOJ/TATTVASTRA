"""Generate schemas from the Python contract authority; --check rejects drift."""

import argparse
import importlib
import inspect
import json
from pathlib import Path

from jocky_contracts.common import Contract

ROOT = Path(__file__).resolve().parents[1]
MODULES = ("common", "compiler", "agent", "evidence", "domain", "status", "frontend")


def schema_text() -> str:
    models: dict[str, type[Contract]] = {}
    for module_name in MODULES:
        module = importlib.import_module(f"jocky_contracts.{module_name}")
        for name, model in inspect.getmembers(module, inspect.isclass):
            if issubclass(model, Contract) and model.__module__ == module.__name__:
                models[name] = model
    definitions: dict[str, object] = {}
    for name, model in sorted(models.items()):
        schema = model.model_json_schema(ref_template="#/$defs/{model}")
        definitions.update(schema.pop("$defs", {}))
        definitions[name] = schema
    bundle = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://jocky.invalid/contracts/v1.0.0",
        "title": "JockyContracts",
        "description": (
            "Generated from Pydantic; do not edit. Refinement rules also apply in Python."
        ),
        "type": "object",
        "additionalProperties": False,
        "properties": {name: {"$ref": f"#/$defs/{name}"} for name in sorted(models)},
        "$defs": definitions,
    }
    return json.dumps(bundle, indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = ROOT / "packages/contracts/generated/contracts.schema.json"
    content = schema_text()
    if args.check:
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            raise SystemExit("Contract drift detected. Run make contracts.")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
