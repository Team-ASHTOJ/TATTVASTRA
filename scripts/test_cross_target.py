"""Exercise real target-aware CLI lowering: one program, two genuine machine formats.

This drives the command line the control plane actually invokes. It asserts the
same source and the same semantic JIR lower to distinct, real relocatable
objects: ELF for the supported Linux target and COFF for the Windows target.
Cross-target *execution* is deliberately rejected, because the emitted object
must run on the matching host.
"""

import argparse
import hashlib
import json
import struct
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "examples/investigations/driver-audit.jky"
SEED = "0000000000000001"

TARGETS = {
    "linux-x86_64": {
        "triple": "x86_64-unknown-linux-gnu",
        "layout": "e-m:e",
        "magic": b"\x7fELF",
    },
    "windows-x86_64": {
        "triple": "x86_64-pc-windows-msvc",
        "layout": "e-m:w",
        "magic": None,  # COFF: machine + section count, checked below.
    },
}


def invoke(compiler: str, *arguments: str, expect_success: bool = True):
    result = subprocess.run(
        [compiler, *arguments], capture_output=True, text=True, timeout=60, check=False
    )
    if expect_success:
        assert result.returncode == 0, (arguments, result.stdout, result.stderr)
    else:
        assert result.returncode != 0, (arguments, result.stdout)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", required=True)
    args = parser.parse_args()

    lowered = {}
    with tempfile.TemporaryDirectory(prefix="jocky-cross-") as temporary:
        directory = Path(temporary)
        for target, expected in TARGETS.items():
            document = json.loads(
                invoke(
                    args.compiler,
                    "llvm",
                    str(PROGRAM),
                    "--json",
                    "--target",
                    target,
                    "--execution",
                    "memory",
                    "--seed",
                    SEED,
                ).stdout
            )
            manifest, ir = document["manifest"], document["ir"]
            assert manifest["target_triple"] == expected["triple"], manifest["target_triple"]
            assert f'target triple = "{expected["triple"]}"' in ir
            assert f'target datalayout = "{expected["layout"]}' in ir
            lowered[target] = manifest

        # One program, one semantic JIR. Only the machine-level output differs.
        assert lowered["linux-x86_64"]["source_hash"] == lowered["windows-x86_64"]["source_hash"]
        assert lowered["linux-x86_64"]["jir_hash"] == lowered["windows-x86_64"]["jir_hash"]
        assert lowered["linux-x86_64"]["variant_id"] != lowered["windows-x86_64"]["variant_id"]
        assert lowered["linux-x86_64"]["llvm_ir_hash"] != lowered["windows-x86_64"]["llvm_ir_hash"]

        objects = {}
        for target, expected in TARGETS.items():
            output = directory / f"{target}.o"
            document = json.loads(
                invoke(
                    args.compiler,
                    "compile",
                    str(PROGRAM),
                    "--json",
                    "--target",
                    target,
                    "--execution",
                    "native",
                    "--seed",
                    SEED,
                    "--output",
                    str(output),
                ).stdout
            )
            manifest = document["manifest"]
            content = output.read_bytes()
            assert manifest["target_triple"] == expected["triple"]
            assert manifest["jir_hash"] == lowered[target]["jir_hash"]
            assert manifest["artifact_hash"] == hashlib.sha256(content).hexdigest()
            assert len(content) > 512
            if expected["magic"] is not None:
                assert content[:4] == expected["magic"], content[:4]
            else:
                # COFF header: IMAGE_FILE_MACHINE_AMD64 then the section count.
                machine, sections = struct.unpack("<HH", content[:4])
                assert machine == 0x8664, machine
                assert 0 < sections < 64, sections
            objects[target] = manifest["artifact_hash"]

        assert objects["linux-x86_64"] != objects["windows-x86_64"]

    # Cross-target JIT execution must refuse rather than pretend to run.
    invoke(
        args.compiler,
        "run",
        str(PROGRAM),
        "--json",
        "--target",
        "windows-x86_64",
        "--execution",
        "memory",
        expect_success=False,
    )
    invoke(
        args.compiler,
        "compile",
        str(PROGRAM),
        "--json",
        "--target",
        "plan9-sparc",
        "--execution",
        "native",
        "--output",
        "unsupported.o",
        expect_success=False,
    )
    print(
        "PASS: one program/JIR lowered to real ELF (linux-x86_64) and COFF "
        "(windows-x86_64) objects; cross-target execution and unknown targets rejected"
    )


if __name__ == "__main__":
    main()
