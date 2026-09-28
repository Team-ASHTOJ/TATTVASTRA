"""The `jocky` command line: a thin launcher for the jockyc compiler.

jocky adds no compiler behaviour of its own. It decides how to reach jockyc,
expands the default `.jky` invocation, translates a few documented aliases, and
otherwise forwards every argument untouched, returning the compiler's own exit
status. The composed commands in this package only re-present jockyc's own
output; see docs/JOCKY_CLI.md for what is and is not available.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from . import build
from . import compiler
from . import container as container_backend
from . import evidence
from . import inspect as inspect_commands
from . import variants as variant_commands
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
from .options import UsageError

PROGRAM = "jocky"

#: Exit status for "no usable compiler backend". Matches scripts/jockey and
#: the jockyc E002 toolchain failure.
EXIT_UNAVAILABLE = 70

#: Conventional status for a run cancelled with Ctrl-C.
EXIT_INTERRUPTED = 130

#: Bad arguments, or a command documented as NOT EXPOSED YET.
EXIT_USAGE = compiler.EXIT_USAGE

#: Documented target aliases. Each maps onto a target jockyc already accepts;
#: no new target support is introduced.
TARGET_ALIASES = {
    "linux": "linux-x86_64",
    "windows": "windows-x86_64",
    "arm64": "linux-aarch64",
    "linux-arm64": "linux-aarch64",
}

#: `run --execution jit` is the documented spelling of the existing memory mode.
EXECUTION_ALIASES = {"jit": "memory"}

#: Flags that would ask for endpoint or relay work the launcher cannot do.
UNSUPPORTED_FLAGS = {
    "--endpoint": (
        "real endpoint execution needs an enrolled, authorized runtime host; "
        "this launcher runs the local compiler only"
    ),
    "--transport": (
        "relay transport is a control-plane and agent path; the local compiler "
        "has no transport to select"
    ),
}

#: Commands whose whole capability is absent today. Each is reported with the
#: reason rather than forwarded to jockyc, which would answer E001.
NOT_EXPOSED = {
    "cfg": (
        "no jockyc command emits control-flow-graph edges — the compiler "
        "reports basic-block counts only, and this launcher invokes jockyc "
        "alone rather than external LLVM tooling"
    ),
    "symbols": "no jockyc command emits a symbol table or name-binding structure",
    "seal": (
        "no local artifact signing exists — the compiler writes unsigned "
        "manifests and signing lives in the control-plane evidence service"
    ),
    "endpoints": "control-plane routes require an authenticated tenant session",
    "findings": "control-plane routes require an authenticated tenant session",
    "timeline": "control-plane routes require an authenticated tenant session",
    "drivers": "control-plane routes require an authenticated tenant session",
    "relay": "relay state is reported by the control plane, not by the compiler",
    "hunt": (
        "dispatching a hunt is a mutating control-plane operation over enrolled "
        "endpoints; this launcher holds no session or credentials"
    ),
    "collect": (
        "collection runs on an enrolled endpoint under the Rust agent, not "
        "through the local compiler"
    ),
}

COMPOSED = {
    "caps": inspect_commands.caps,
    "budget": inspect_commands.budget,
    "types": inspect_commands.types,
    "metrics": inspect_commands.metrics,
    "fingerprint": inspect_commands.fingerprint,
    "diverge": variant_commands.diverge,
    "diff": variant_commands.diff,
    "equivalence": variant_commands.equivalence,
    "forge": build.forge,
    "pipeline": build.pipeline,
    "verify": evidence.verify,
    "manifest": evidence.manifest,
}

#: Rendered into the help text; kept out of the f-string so the file parses on
#: every Python the package claims to support.
NOT_EXPOSED_LIST = ", ".join(sorted(NOT_EXPOSED))

HELP = f"""\
{PROGRAM} — run the JOCKY compiler (jockyc) from any directory.

usage:
  {PROGRAM} <file.jky> [options]          compile and run a hunt file
  {PROGRAM} <command> <file.jky> [...]    forward <command> to jockyc
  {PROGRAM} <composed> <file.jky> [...]   composed local commands (below)
  {PROGRAM} doctor                        report environment readiness
  {PROGRAM} --help | help | --version

forwarded to jockyc:
  check  tokens  ast  jir  llvm  plan  compile  run  variants  variant-info
  benchmark

composed locally, from jockyc output only:
  caps         declared capabilities             (jockyc jir)
  budget       effective resource budgets        (jockyc jir + ast)
  types        declared result schema            (jockyc plan)
  metrics      structural lowering metrics       (jockyc llvm)
  fingerprint  compiler hashes and fingerprint   (jockyc llvm)
  diverge      N variants and their artifacts    (jockyc variants)
  diff         two seeds compared structurally   (jockyc llvm)
  equivalence  fixture semantic equivalence      (jockyc variants)
  forge        one AOT object per seed           (jockyc compile)
  pipeline     end-to-end demo sequence          (composition)
  verify       artifact bytes vs manifest hash   (jockyc variant-info)
  manifest     print a variant manifest          (jockyc variant-info)

options, forwarded to jockyc and parsed there:
  --json               canonical JSON output where the command supports it
  --target <target>    host | linux-x86_64 | linux-aarch64 | windows-x86_64
  --execution <mode>   memory | native
  --output <path>      output file or directory
  --seed <n>           variant seed (decimal or hexadecimal)
  --count <n>          variant or benchmark count

options this launcher handles:
  --dry-run            map `run` to the existing `plan` stage, without executing
  --seed-a/--seed-b    the two seeds `diff` compares
  --verbose            `pipeline`: also print each stage's jockyc JSON
  --target all         `forge`, `pipeline`: both cross targets

aliases (translation only, applied to forwarded options):
  --execution jit      -> memory          (run)
  --target linux       -> linux-x86_64
  --target windows     -> windows-x86_64
  --target arm64       -> linux-aarch64

default:
  `{PROGRAM} hunt.jky` is `jockyc run hunt.jky --execution memory`.

backend, chosen in this order and nothing else:
  1. the JOCKYC environment variable
  2. a compiler built in a JOCKY checkout ({LOCAL_BUILD.as_posix()})
  3. jockyc on PATH
  4. the {DOCKER_IMAGE} container image

not exposed yet: {NOT_EXPOSED_LIST}
see docs/JOCKY_CLI.md for each reason and for what is available.
"""


def _apply_aliases(args: list[str]) -> list[str]:
    """Translate the documented option aliases, leaving values untouched.

    Only `--target` and (for `run`) `--execution` are rewritten, and only when
    the value is a documented alias. Everything else is copied verbatim.
    """
    command = args[0] if args else ""
    result: list[str] = []
    index = 0
    while index < len(args):
        argument = args[index]
        index += 1
        if argument in ("--target", "--execution") and index < len(args):
            value = args[index]
            index += 1
            if argument == "--target":
                value = TARGET_ALIASES.get(value, value)
            elif command == "run":
                value = EXECUTION_ALIASES.get(value, value)
            result += [argument, value]
        else:
            result.append(argument)
    return result


def normalize(args: list[str]) -> list[str]:
    """Expand a bare `.jky` invocation into the equivalent jockyc argv.

    An explicit --execution is left alone, so the documented default only
    applies when the caller has not chosen a mode. `--dry-run` maps the run
    onto the existing `plan` stage, which never executes anything.
    """
    arguments = list(args)
    dry_run = "--dry-run" in arguments
    if dry_run:
        arguments = [argument for argument in arguments if argument != "--dry-run"]

    if arguments and arguments[0].endswith(".jky"):
        rest = arguments[1:]
        if dry_run:
            return _apply_aliases(["plan", arguments[0], *rest])
        if "--execution" in rest:
            return _apply_aliases(["run", arguments[0], *rest])
        return _apply_aliases(["run", arguments[0], "--execution", "memory", *rest])

    if dry_run:
        if arguments and arguments[0] == "run":
            return _apply_aliases(["plan", *arguments[1:]])
        raise UsageError(
            "--dry-run is only supported for `jocky <file.jky>` and "
            "`jocky run <file.jky>`, which both map to the existing plan stage",
        )
    return _apply_aliases(arguments)


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


def dispatch(args: list[str]) -> int:
    """Send an already-normalized jockyc argv to the selected backend."""
    try:
        argv = compiler.compiler_argv(args, Path.cwd())
    except compiler.BackendUnavailable as error:
        print(_unavailable(str(error)), file=sys.stderr)
        return EXIT_UNAVAILABLE
    return _run(argv)


def _composed(handler, argv: list[str]) -> int:
    """Run a composed command, reporting its failures the way jocky does."""
    try:
        return handler(argv)
    except UsageError as error:
        print(f"{PROGRAM}: {error}", file=sys.stderr)
        return EXIT_USAGE
    except compiler.BackendUnavailable as error:
        print(_unavailable(str(error)), file=sys.stderr)
        return EXIT_UNAVAILABLE
    except compiler.CompilerError as error:
        print(error.message, file=sys.stderr)
        return error.status
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED


def _not_exposed(name: str, detail: str) -> int:
    print(f"{PROGRAM}: `{name}` is NOT EXPOSED YET — {detail}.", file=sys.stderr)
    print(f"See docs/JOCKY_CLI.md for the command reference.", file=sys.stderr)
    return EXIT_USAGE


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
    if first in ("-h", "--help", "help"):
        print(HELP, end="")
        return 0
    if first == "--version":
        print(f"{PROGRAM} {__version__}")
        return 0
    if first == "doctor":
        return doctor()
    if first in COMPOSED:
        return _composed(COMPOSED[first], args[1:])
    if first in NOT_EXPOSED:
        return _not_exposed(first, NOT_EXPOSED[first])
    for flag, reason in UNSUPPORTED_FLAGS.items():
        if flag in args:
            return _not_exposed(flag, reason)

    try:
        normalized = normalize(args)
    except UsageError as error:
        print(f"{PROGRAM}: {error}", file=sys.stderr)
        return EXIT_USAGE
    return dispatch(normalized)
