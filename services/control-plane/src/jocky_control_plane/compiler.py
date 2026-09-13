import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from jocky_contracts.compiler import CompileRequest


class CompilerUnavailableError(RuntimeError):
    pass


class CompilerInvocationError(RuntimeError):
    def __init__(self, detail: str, output: dict[str, Any] | None = None) -> None:
        super().__init__(detail)
        self.output = output


def invoke_compiler(
    compiler_path: Path | None, payload: CompileRequest, timeout_seconds: float
) -> dict[str, Any]:
    if compiler_path is None or not compiler_path.is_file():
        raise CompilerUnavailableError

    with tempfile.TemporaryDirectory(prefix="jocky-compile-") as directory:
        source_path = Path(directory) / "workbench.jky"
        source_path.write_text(payload.source, encoding="utf-8", newline="\n")
        arguments = [str(compiler_path), payload.command, str(source_path), "--json"]
        if payload.command in {"check", "llvm", "run"}:
            arguments.extend(["--seed", payload.variant_seed])
        if payload.command == "run":
            arguments.extend(["--execution", "memory"])

        try:
            result = subprocess.run(
                arguments,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise CompilerInvocationError(f"Compiler invocation failed: {error}") from error

    raw_output = result.stdout.strip() or result.stderr.strip()
    parsed: dict[str, Any] | None = None
    if raw_output:
        try:
            value = json.loads(raw_output)
            if isinstance(value, dict):
                parsed = value
        except json.JSONDecodeError:
            pass
    if result.returncode != 0:
        detail = "Compiler rejected the submitted source."
        if parsed and isinstance(parsed.get("message"), str):
            detail = parsed["message"]
        elif raw_output:
            detail = raw_output[:4096]
        raise CompilerInvocationError(detail, parsed)
    if parsed is None:
        raise CompilerInvocationError("Compiler returned an invalid JSON response.")
    return parsed
