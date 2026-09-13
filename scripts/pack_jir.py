"""Wrap C++ JIR JSON in the existing versioned protobuf CanonicalDocument.

Requires `make proto-check`. This is serialization orchestration, not a DSL interpreter
or an agent dispatch path. Unsigned JIR alone is never an authorized job.
"""

import argparse
import importlib.util
import json
from pathlib import Path

import rfc8785
from jocky_contracts.frontend import JirModule

ROOT = Path(__file__).resolve().parents[1]


def pack_jir(raw: bytes) -> bytes:
    document = json.loads(raw)
    JirModule.model_validate(document)
    canonical = rfc8785.dumps(document)
    if canonical != raw.rstrip(b"\n"):
        raise ValueError("Expected canonical jockyc --json bytes; do not rewrite JIR")
    generated = ROOT / "build/proto/jocky/v1/agent_pb2.py"
    if not generated.is_file():
        raise ValueError("Run make proto-check to generate the versioned protobuf bindings")
    spec = importlib.util.spec_from_file_location("jocky_frontend_agent_pb2", generated)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    envelope = module.CanonicalDocument(json_utf8=canonical)
    packed: bytes = envelope.SerializeToString(deterministic=True)
    restored = module.CanonicalDocument.FromString(packed)
    if restored.json_utf8 != canonical:
        raise ValueError("Protobuf roundtrip changed the JIR bytes")
    return packed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_bytes(pack_jir(args.input.read_bytes()))
