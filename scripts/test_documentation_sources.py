"""Validate every Documentation and Workbench source with the real C++ compiler."""

import argparse
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = re.compile(r"source: \`(.*?)\`,", re.DOTALL)


def programs(path: Path) -> list[str]:
    sources = SOURCE.findall(path.read_text(encoding="utf-8"))
    assert sources, f"No JOCKY sources found in {path}"
    return sources


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", required=True)
    args = parser.parse_args()
    documentation = programs(ROOT / "apps/dashboard/src/lib/documentation.ts")
    runnable = programs(ROOT / "apps/dashboard/src/lib/language-examples.ts")
    sources = [*documentation, *runnable]
    with tempfile.TemporaryDirectory(prefix="jocky-documentation-") as directory:
        for index, source in enumerate(sources):
            path = Path(directory) / f"example-{index}.jky"
            path.write_text(source, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [args.compiler, "check", str(path)],
                capture_output=True,
                text=True,
                timeout=15,
            )
            assert result.returncode == 0, (path.name, result.stdout, result.stderr)
            if index >= len(documentation):
                object_path = Path(directory) / f"example-{index}.o"
                result = subprocess.run(
                    [
                        args.compiler,
                        "compile",
                        str(path),
                        "--target",
                        "host",
                        "--execution",
                        "native",
                        "--output",
                        str(object_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                assert result.returncode == 0, (
                    path.name,
                    result.stdout,
                    result.stderr,
                )
                assert object_path.is_file() and object_path.stat().st_size > 0
    print(
        f"PASS: {len(sources)} documentation and Workbench sources compile-check; "
        f"{len(runnable)} runnable sources AOT-compile"
    )


if __name__ == "__main__":
    main()
