"""Offline frontend/LLVM/ORC acceptance, including optional-Python builds."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

compiler = sys.argv[1]
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    (root / "interop_fixture.py").write_text(
        'simulation = True\nsimulation_label = "Python interop test fixture"\n'
        'def format_value(value): return f"value={value}"\n'
        'def fail(): raise RuntimeError("fixture failure\\nsecond line")\n'
        "def unsupported(): return []\n"
        "def identity(value): return value\n"
        "def nothing(): return None\n"
    )
    env = dict(os.environ, JOCKY_PYTHON_PACKAGES_DIR=directory)
    source = root / "test.jky"

    def run(command, body, *options, success=True):
        source.write_text('hunt "Python test" { ' + body + " }")
        result = subprocess.run(
            [compiler, command, str(source), *options], env=env, capture_output=True, text=True
        )
        assert (result.returncode == 0) == success, result.stdout + result.stderr
        return result.stdout + result.stderr

    prefix = 'capabilities { python.interop } python import "interop_fixture" as fixture '
    body = prefix + "python call fixture.format_value(123) as formatted"
    for command in ("check", "tokens", "ast", "jir", "plan", "llvm"):
        output = run(command, body, "--json")
        if command == "jir":
            instruction = json.loads(output)["instructions"][0]
            assert instruction["opcode"] == "PYTHON_CALL"
            assert instruction["attributes"] == {
                "module": "interop_fixture",
                "function": "format_value",
                "arguments": [{"type": "int", "value": "123"}],
                "result_name": "formatted",
            }
        if command == "llvm":
            assert "jocky_rt_analysis" in output
    obj = root / "python.o"
    run("compile", body, "--target", "host", "--execution", "native", "--output", str(obj))
    assert obj.stat().st_size > 0
    for invalid in (
        prefix + 'python import "other" as fixture',
        prefix + "python call unknown.f(1) as result",
        'python import "fixture" as fixture python call fixture.f(1) as result',
        "python import fixture as fixture",
        'python import "fixture"',
        prefix + "python call fixture.f(1)",
        prefix + "python call fixture.f(1 + 2) as result",
        prefix + "python call fixture.f(x) as result",
        prefix + "python call fixture.a.b(1) as result",
        prefix + "python call fixture.f([1]) as result",
        prefix + "python call fixture.f(x=1) as result",
        body + ' python import "other" as other',
    ):
        run("check", invalid, success=False)
    # Package availability must never affect compilation.
    missing = (
        'capabilities { python.interop } python import "jocky_missing_fixture_xyz" as fixture '
    )
    run("check", missing + "python call fixture.f() as result")
    source.write_text('hunt "Python test" { ' + body + " }")
    result = subprocess.run(
        [compiler, "run", str(source), "--json"], env=env, capture_output=True, text=True
    )
    if "PYTHON_UNAVAILABLE" in result.stdout + result.stderr:
        assert result.returncode != 0
        print(
            "PASS frontend/JIR/LLVM/AOT/ORC optional-Python UNAVAILABLE; "
            "Python execution unavailable"
        )
    else:
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["python_results"] == {"formatted": "value=123"}
        assert "formatted: value=123" in run("run", body)
        for call, expected in [
            ('identity("true")', "true"),
            ("identity(-12)", "-12"),
            ("identity(1.25)", "1.25"),
            ("identity(true)", "true"),
            ("identity(false)", "false"),
            ("nothing()", "null"),
        ]:
            output = run("run", prefix + "python call fixture." + call + " as result", "--json")
            assert json.loads(output)["python_results"]["result"] == expected
        for source_prefix, call, code in [
            (missing, "f()", "PYTHON_MODULE_UNAVAILABLE"),
            (prefix, "xyz()", "PYTHON_FUNCTION_UNAVAILABLE"),
            (prefix, "fail()", "PYTHON_CALL_FAILED"),
            (prefix, "unsupported()", "PYTHON_CALL_FAILED"),
        ]:
            assert code in run(
                "run", source_prefix + "python call fixture." + call + " as result", success=False
            )
        print("PASS frontend/JIR/LLVM/AOT/ORC Python calls and runtime failures")
