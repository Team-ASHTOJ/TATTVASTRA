"""Actual native JIR goldens cross the existing protobuf transport document boundary."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def packer():
    import sys

    (ROOT / "build/proto").mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            "-I",
            "proto",
            f"--python_out={ROOT / 'build/proto'}",
            "proto/jocky/v1/agent.proto",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    spec = importlib.util.spec_from_file_location("pack_jir", ROOT / "scripts/pack_jir.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.pack_jir


@pytest.mark.parametrize("path", sorted((ROOT / "fixtures/compiler").glob("*.jir.canonical.json")))
def test_protobuf_preserves_actual_jir_bytes(packer, path: Path) -> None:
    raw = path.read_bytes()
    assert packer(raw) == packer(raw)
    assert raw.rstrip(b"\n") in packer(raw)
