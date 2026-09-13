import json
from pathlib import Path

import pytest
from jocky_contracts.compiler import CompileRequest, ExecutionMode, Target
from jocky_control_plane.compiler import CompilerInvocationError, invoke_compiler


def request(command: str = "check") -> CompileRequest:
    return CompileRequest(
        simulation=False,
        command=command,
        source='hunt "test" {}',
        target=Target(os="linux", arch="x86_64"),
        execution_mode=ExecutionMode.MEMORY,
    )


def test_compiler_adapter_uses_an_argument_list_and_parses_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = Path(__file__)
    observed: list[str] = []

    def fake_run(arguments: list[str], **_: object):
        observed.extend(arguments)

        class Result:
            returncode = 0
            stdout = json.dumps({"kind": "FrontendCheck", "valid": True})
            stderr = ""

        return Result()

    monkeypatch.setattr("jocky_control_plane.compiler.subprocess.run", fake_run)
    result = invoke_compiler(executable, request(), 1.0)
    assert result == {"kind": "FrontendCheck", "valid": True}
    assert observed[0:2] == [str(executable), "check"]
    assert observed[-2:] == ["--seed", "0000000000000000"]


def test_compiler_adapter_does_not_return_non_json_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = Path(__file__)

    class Result:
        returncode = 0
        stdout = "not json"
        stderr = ""

    monkeypatch.setattr(
        "jocky_control_plane.compiler.subprocess.run", lambda *_args, **_kwargs: Result()
    )
    with pytest.raises(CompilerInvocationError, match="invalid JSON"):
        invoke_compiler(executable, request(), 1.0)
