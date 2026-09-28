"""The `jocky` command line: a thin launcher for the jockyc compiler.

jocky adds no compiler behaviour of its own. It decides how to reach jockyc,
expands the default `.jky` invocation, and otherwise forwards every argument
untouched, returning the compiler's own exit status.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from . import container as container_backend
from .backend import (
    DOCKER_BUILD_COMMAND,
    DOCKER_IMAGE,
    LOCAL_BUILD,
    NATIVE,
    env_jockyc,
    find_local_jockyc,
    is_executable,
    resolve_backend,
)

PROGRAM = "jocky"

#: Exit status for "no usable compiler backend". Matches scripts/jockey and
#: the jockyc E002 toolchain failure.
EXIT_UNAVAILABLE = 70

#: Conventional status for a run cancelled with Ctrl-C.
EXIT_INTERRUPTED = 130

HELP = f"""\
{PROGRAM} — run the JOCKY compiler (jockyc) from any directory.

usage:
  {PROGRAM} <file.jky> [options]          compile and run a hunt file
  {PROGRAM} <command> <file.jky> [...]    forward <command> to jockyc
  {PROGRAM} doctor                        report environment readiness
  {PROGRAM} --help | --version

commands forwarded to jockyc:
  check  tokens  ast  jir  llvm  plan  compile  run  variants  variant-info
  benchmark

options (parsed by jockyc, forwarded untouched):
  --json               canonical JSON output where the command supports it
  --target <target>    host | linux-x86_64 | linux-aarch64 | windows-x86_64
  --execution <mode>   memory | native
  --output <path>      output file or directory
  --seed <n>           variant seed (decimal or hexadecimal)
  --count <n>          variant or benchmark count

default:
  `{PROGRAM} hunt.jky` is `jockyc run hunt.jky --execution memory`.

backend, chosen in this order and nothing else:
  1. the JOCKYC environment variable
  2. a compiler built in a JOCKY checkout ({LOCAL_BUILD.as_posix()})
  3. jockyc on PATH
  4. the {DOCKER_IMAGE} container image
"""


def normalize(args: list[str]) -> list[str]:
    """Expand a bare `.jky` invocation into the equivalent jockyc argv.

    An explicit --execution is left alone, so the documented default only
    applies when the caller has not chosen a mode.
    """
    if args and args[0].endswith(".jky"):
        rest = args[1:]
        if "--execution" in rest:
            return ["run", args[0], *rest]
        return ["run", args[0], "--execution", "memory", *rest]
    return args


def _unavailable(reason: str) -> str:
    return (
        f"{PROGRAM}: no usable compiler backend — {reason}.\n"
        f"\n"
        "Build the compiler natively with `make jockey-install`, or build the\n"
        "container fallback with:\n"
        f"\n"
        f"  {DOCKER_BUILD_COMMAND}\n"
        f"\n"
        f"Then re-check with `{PROGRAM} doctor`."
    )


def _run(argv: list[str]) -> int:
    """Run a command with inherited stdio and return its real exit status."""
    try:
        return subprocess.run(argv, check=False).returncode
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED
    except OSError as error:
        print(f"{PROGRAM}: cannot run {argv[0]}: {error}", file=sys.stderr)
        return EXIT_UNAVAILABLE


def _run_native(path: str, args: list[str]) -> int:
    return _run([path, *args])


def _run_docker(args: list[str]) -> int:
    docker = container_backend.docker_cli()
    if docker is None:
        print(_unavailable("the docker client is not on PATH"), file=sys.stderr)
        return EXIT_UNAVAILABLE
    if not container_backend.daemon_reachable(docker):
        print(_unavailable("the docker daemon is not reachable"), file=sys.stderr)
        return EXIT_UNAVAILABLE
    if not container_backend.image_present(docker):
        print(_unavailable(f"the {DOCKER_IMAGE} image is not built"), file=sys.stderr)
        return EXIT_UNAVAILABLE

    try:
        argv = container_backend.container_command(docker, args, Path.cwd())
    except container_backend.DockerUnavailable as error:
        print(_unavailable(str(error)), file=sys.stderr)
        return EXIT_UNAVAILABLE
    return _run(argv)


def dispatch(args: list[str]) -> int:
    """Send an already-normalized jockyc argv to the selected backend."""
    backend = resolve_backend()
    if backend.kind == NATIVE and backend.path is not None:
        return _run_native(backend.path, args)
    return _run_docker(args)


def _report(label: str, value: str) -> None:
    print(f"  {label:<18}{value}")


def doctor() -> int:
    """Report environment readiness. Read-only: nothing is built or changed."""
    print(f"{PROGRAM} {__version__} — environment readiness")
    print()

    script = shutil.which(PROGRAM)
    _report("cli", f"{PROGRAM} {__version__} ({script or 'not on PATH'})")
    _report("python", f"{sys.executable} ({sys.version.split()[0]})")

    configured = env_jockyc()
    if configured is None:
        _report("JOCKYC", "unset")
    else:
        state = "executable" if is_executable(Path(configured).expanduser()) else "NOT executable"
        _report("JOCKYC", f"{configured} ({state})")

    local = find_local_jockyc(Path.cwd())
    _report("local build", str(local) if local is not None else "not found")
    _report("jockyc on PATH", shutil.which("jockyc") or "not found")

    docker = container_backend.docker_cli()
    _report("docker", docker or "not found")

    daemon = bool(docker) and container_backend.daemon_reachable(docker)
    _report(
        "docker daemon",
        "reachable" if daemon else ("not reachable" if docker else "n/a"),
    )

    image = daemon and docker is not None and container_backend.image_present(docker)
    _report("image", f"{DOCKER_IMAGE} ({'present' if image else 'missing'})")

    backend = resolve_backend()
    if backend.kind == NATIVE:
        selected = f"native — {backend.origin} ({backend.path})"
    elif image:
        selected = f"docker — {DOCKER_IMAGE}"
    else:
        selected = "none"

    print()
    _report("selected backend", selected)

    if backend.kind == NATIVE:
        return 0

    print()
    if docker is None:
        reason = "the docker client is not on PATH"
    elif not daemon:
        reason = "the docker daemon is not reachable"
    elif not image:
        reason = f"the {DOCKER_IMAGE} image is not built"
    else:
        return 0

    print(f"{PROGRAM}: no native compiler found, and the docker fallback is unusable.")
    print(f"  {reason}.")
    if daemon:
        print()
        print("Build the fallback image with:")
        print()
        print(f"  {DOCKER_BUILD_COMMAND}")
    return EXIT_UNAVAILABLE


def main(argv: list[str] | None = None) -> int:
    """Entry point for the `jocky` console script."""
    args = list(sys.argv[1:] if argv is None else argv)

    if not args:
        print(HELP, end="")
        return 0
    first = args[0]
    if first in ("-h", "--help"):
        print(HELP, end="")
        return 0
    if first == "--version":
        print(f"{PROGRAM} {__version__}")
        return 0
    if first == "doctor":
        return doctor()

    return dispatch(normalize(args))
