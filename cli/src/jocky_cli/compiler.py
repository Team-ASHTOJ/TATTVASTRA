"""Reach jockyc and read back the machine-readable output it already emits.

No composed `jocky` command re-implements the compiler. Each one runs an
existing jockyc subcommand (usually with `--json`) and reports fields that
subcommand produced. Nothing in this package parses `.jky` source, infers a
type, resolves a capability or hashes a source file on the compiler's behalf.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from . import container as container_backend
from . import options as options_module
from .backend import DOCKER_IMAGE, NATIVE, resolve_backend
from .options import UsageError

#: jockyc's own status for a rejected program or a failed stage.
EXIT_COMPILER_FAILURE = 1

#: jocky could not run the request at all: bad arguments here, or a command
#: documented as NOT EXPOSED YET in docs/JOCKY_CLI.md.
EXIT_USAGE = 2

#: No usable compiler backend. Matches main.EXIT_UNAVAILABLE and jockyc E002.
EXIT_BACKEND_UNAVAILABLE = 70


class BackendUnavailable(RuntimeError):
    """No backend can run the compiler; the message is the reason."""


class CompilerError(RuntimeError):
    """jockyc ran and failed. Carries its own exit status and diagnostics."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def compiler_argv(args: list[str], cwd: Path) -> list[str]:
    """An argv that runs jockyc with `args`, using the documented backend order.

    Raises BackendUnavailable when the only remaining backend is Docker and
    Docker cannot be used, with the same reason text `jocky doctor` reports.
    """
    backend = resolve_backend(cwd)
    if backend.kind == NATIVE and backend.path is not None:
        return [backend.path, *args]

    docker = container_backend.docker_cli()
    if docker is None:
        raise BackendUnavailable("the docker client is not on PATH")
    if not container_backend.daemon_reachable(docker):
        raise BackendUnavailable("the docker daemon is not reachable")
    if not container_backend.image_present(docker):
        raise BackendUnavailable(f"the {DOCKER_IMAGE} image is not built")
    try:
        return container_backend.container_command(docker, args, cwd)
    except container_backend.DockerUnavailable as error:
        raise BackendUnavailable(str(error)) from error


def run_capture(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run jockyc with `args`, capturing its streams for parsing."""
    argv = compiler_argv(args, cwd)
    try:
        return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)
    except OSError as error:
        raise BackendUnavailable(f"cannot run {argv[0]}: {error}") from error


def run_stream(args: list[str], cwd: Path) -> int:
    """Run jockyc with `args`, passing its streams and exit status straight through."""
    argv = compiler_argv(args, cwd)
    try:
        return subprocess.run(argv, cwd=cwd, check=False).returncode
    except OSError as error:
        raise BackendUnavailable(f"cannot run {argv[0]}: {error}") from error


def failure_message(result: subprocess.CompletedProcess[str], source: str) -> str:
    """The most useful message jockyc gave for a failed run.

    With `--json`, a rejected program is reported as a CompilerFailure document
    on stdout rather than as rendered stderr text, so both are inspected.
    """
    text = (result.stderr or "").strip()
    if text:
        return text
    try:
        document = json.loads(result.stdout or "")
    except json.JSONDecodeError:
        return (result.stdout or "").strip() or "jockyc failed without a diagnostic"
    if not isinstance(document, dict):
        return "jockyc failed without a diagnostic"
    lines: list[str] = []
    for diagnostic in document.get("diagnostics") or []:
        start = (diagnostic.get("span") or {}).get("start") or {}
        location = f"{source}:{start.get('line')}:{start.get('column')}"
        detail = f"{diagnostic.get('code')}: {diagnostic.get('message')}"
        lines.append(f"{location}: JOCKY {detail}")
        if diagnostic.get("help"):
            lines.append(f"help: {diagnostic['help']}")
    return "\n".join(lines) or "jockyc failed without a diagnostic"


def run_json(args: list[str], cwd: Path, source: str) -> dict:
    """Run a `--json` jockyc command and return the parsed document."""
    result = run_capture(args, cwd)
    if result.returncode != 0:
        raise CompilerError(result.returncode, failure_message(result, source))
    try:
        document = json.loads(result.stdout or "")
    except json.JSONDecodeError as error:
        raise CompilerError(
            EXIT_BACKEND_UNAVAILABLE,
            f"jockyc returned no JSON for `{args[0]}`: {error}",
        ) from error
    if not isinstance(document, dict):
        raise CompilerError(
            EXIT_BACKEND_UNAVAILABLE,
            f"jockyc returned an unexpected document for `{args[0]}`",
        )
    return document


def source_and_options(
    argv: list[str],
    valued: set[str],
    flags: set[str],
    command: str,
) -> tuple[str, dict[str, str], set[str]]:
    """Parse a composed command's arguments and require exactly one source path."""
    positionals, values, present = options_module.parse(argv, valued, flags)
    if len(positionals) != 1:
        raise UsageError(
            f"usage: jocky {command} <file.jky> [options] "
            "(exactly one .jky file is required)"
        )
    return positionals[0], values, present


def target_option(values: dict[str, str]) -> list[str]:
    """`--target <value>` only when the caller asked for one.

    jockyc's own default is `host`, so omitting the option keeps its default
    rather than restating it here.
    """
    return ["--target", values["--target"]] if "--target" in values else []


def seed_arguments(seed: int) -> list[str]:
    """`--seed <value>` in the unambiguous hexadecimal form jockyc accepts."""
    return ["--seed", f"0x{seed:x}"]


def seed_option(values: dict[str, str], name: str = "--seed") -> list[str]:
    """`--seed <value>` from a caller-supplied string, when present."""
    if name not in values:
        return []
    return seed_arguments(options_module.parse_seed(values[name], name))


def default_seed(module: dict) -> tuple[int, str]:
    """jockyc's own default variant seed, read back from its JIR output.

    Mirrors jockyc's seed resolution: an explicit `variant { seed <hex> }`
    declaration wins, otherwise the seed is the first 16 hexadecimal characters
    of the compiler's own source hash. This exists only so composed commands
    that must pass explicit seeds (`forge`, `pipeline`) start from the base
    jockyc would itself have chosen. Both inputs are read from compiler output;
    nothing here is derived from the source text.
    """
    runtime = module.get("runtime") or {}
    variant = runtime.get("variant") or {}
    declared = variant.get("seed")
    if isinstance(declared, str) and declared and declared.lower() != "auto":
        return _seed_from_text(declared, "declared by variant { seed }")
    source_hash = str(module.get("source_hash") or "")
    if len(source_hash) < 16:
        raise CompilerError(
            EXIT_BACKEND_UNAVAILABLE,
            "jockyc reported no source hash to derive a seed from",
        )
    return _seed_from_text(source_hash[:16], "jockyc default (source hash prefix)")


def _seed_from_text(text: str, origin: str) -> tuple[int, str]:
    """A seed jockyc printed, or a clean failure rather than a traceback."""
    try:
        return int(text, 16), origin
    except ValueError as error:
        raise CompilerError(
            EXIT_BACKEND_UNAVAILABLE,
            f"jockyc reported an unusable variant seed {text!r}",
        ) from error


def seed_text(seed: int) -> str:
    """A seed in the 16-digit hexadecimal form jockyc prints."""
    return f"{seed:016x}"
