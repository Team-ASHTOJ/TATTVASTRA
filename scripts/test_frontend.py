"""Exercise the real C++ CLI; snapshots are reviewed static compiler output, not evidence."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(compiler: str, command: str, path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [compiler, command, str(path), "--json"], capture_output=True, text=True, timeout=15
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", required=True)
    parser.add_argument("--update-goldens", action="store_true")
    args = parser.parse_args()
    valid = sorted(p for p in (ROOT / "examples").rglob("*.jky") if "invalid" not in p.parts)
    for path in valid:
        for command in ("tokens", "ast", "jir", "plan", "check"):
            result = run(args.compiler, command, path)
            assert result.returncode == 0, (path, command, result.stdout, result.stderr)
            output = json.loads(result.stdout)
            assert output["schema_version"] == "1.0.0"
            assert result.stdout == run(args.compiler, command, path).stdout, (path, command)
            if command == "jir":
                assert output["executable"] is False
                assert output["source_hash"] == hashlib.sha256(path.read_bytes()).hexdigest()
            if command == "plan":
                assert output["dispatchable"] is False
                jir = run(args.compiler, "jir", path).stdout.rstrip("\n")
                assert output["jir_hash"] == hashlib.sha256(jir.encode()).hexdigest()
            if command in {"ast", "jir", "plan"}:
                golden = ROOT / "fixtures/compiler" / f"{path.stem}.{command}.canonical.json"
                if args.update_goldens:
                    golden.write_text(result.stdout, encoding="utf-8", newline="\n")
                assert golden.read_text(encoding="utf-8") == result.stdout, (
                    f"Golden drift: {golden}"
                )
    invalid = ROOT / "examples/invalid"
    expected = json.loads((invalid / "expected.json").read_text(encoding="utf-8"))
    assert set(expected) == {p.name for p in invalid.glob("*.jky")}
    for name, code in expected.items():
        for command in ("check", "jir", "plan"):
            result = run(args.compiler, command, invalid / name)
            assert result.returncode == 1, (name, command, result.stderr)
            error = json.loads(result.stdout)
            assert error["valid"] is False
            assert error["diagnostics"][0]["code"] == code, (name, error)
    missing = run(args.compiler, "check", ROOT / "examples/does-not-exist.jky")
    assert missing.returncode == 1
    assert json.loads(missing.stdout)["diagnostics"][0]["code"] == "E003"
    print(
        f"PASS: {len(valid)} valid examples × 5 commands; deterministic outputs; "
        f"{len(valid) * 3} goldens; {len(expected)} invalid examples × 3 commands; "
        "missing-file diagnostic"
    )


if __name__ == "__main__":
    main()
