import argparse
import shutil
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--check", action="store_true")
args = parser.parse_args()
tool = shutil.which("clang-format-18") or shutil.which("clang-format")
if not tool:
    raise SystemExit(
        "clang-format is missing. Use the native container or install LLVM 18 tooling."
    )
paths = sorted(str(path) for path in Path("native").rglob("*") if path.suffix in {".h", ".cpp"})
subprocess.run([tool, *(["--dry-run", "--Werror"] if args.check else ["-i"]), *paths], check=True)
