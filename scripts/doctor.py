"""Read-only machine dependency inventory; a missing tool is never silently skipped."""

import json
import shutil
import subprocess
import sys

TOOLS = {
    "python3.12": ["--version"],
    "uv": ["--version"],
    "node": ["--version"],
    "npm": ["--version"],
    "rustc": ["--version"],
    "cargo": ["--version"],
    "rustfmt": ["--version"],
    "cmake": ["--version"],
    "clang": ["--version"],
    "llvm-config": ["--version"],
    "clang-format": ["--version"],
    "protoc": ["--version"],
    "docker": ["--version"],
    "make": ["--version"],
}
results = []
for name, args in TOOLS.items():
    path = shutil.which(name)
    entry: dict[str, object] = {"tool": name, "path": path, "available": bool(path)}
    if path:
        try:
            result = subprocess.run([path, *args], capture_output=True, text=True, timeout=15)
            entry["version"] = (result.stdout or result.stderr).splitlines()[:1]
            entry["exit_code"] = result.returncode
        except subprocess.TimeoutExpired:
            entry["error"] = "version probe timed out"
    results.append(entry)
print(json.dumps({"simulation": False, "host_platform": sys.platform, "tools": results}, indent=2))
raise SystemExit(1 if any(not entry["available"] for entry in results) else 0)
