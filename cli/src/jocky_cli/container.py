"""The Docker fallback: run jockyc inside the jockey-native:foundation image.

This is the cross-platform route, and the only route that works where the
native compiler cannot be built. The image is never rebuilt or pulled here.

Host paths are translated into a bind-mounted work root so the compiler sees
the same files it would natively, and its stdout, stderr and exit status are
passed through untouched.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path, PurePosixPath

from .backend import CONTAINER_WORKDIR, DOCKER_IMAGE, DOCKER_JOCKYC

#: Compiler options whose value is a host path. Mirrors jockyc's own parser;
#: `--json` is the only option jockyc accepts without a value.
PATH_OPTIONS = ("--output",)

#: Mount point for an --output that lies outside the work root.
OUTPUT_MOUNT = "/jocky-out"

#: Suffixes that always name a file the compiler reads.
SOURCE_SUFFIXES = (".jky", ".json")


class DockerUnavailable(RuntimeError):
    """Docker, the daemon, or the fallback image is not usable."""


def docker_cli() -> str | None:
    """Path to the docker client, or None when it is not installed."""
    return shutil.which("docker")


def _probe(argv: list[str]) -> bool:
    """Run a read-only docker query; True when it succeeds."""
    try:
        result = subprocess.run(
            argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def daemon_reachable(docker: str) -> bool:
    """True when the docker client can reach a daemon."""
    return _probe([docker, "info"])


def image_present(docker: str, image: str = DOCKER_IMAGE) -> bool:
    """True when `image` already exists locally. Never pulls."""
    return _probe([docker, "image", "inspect", "--format", "{{.Id}}", image])


def _absolute(value: str, cwd: Path) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = cwd / candidate
    return Path(os.path.normpath(str(candidate)))


def _is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def looks_like_source(value: str, cwd: Path) -> bool:
    """True for arguments that name a file the compiler will read.

    jockyc takes exactly one positional path, so only paths ever reach this.
    Option values such as `host`, `memory` or `3` are filtered out by the
    argument walk instead.
    """
    if value.endswith(SOURCE_SUFFIXES):
        return True
    return _absolute(value, cwd).exists()


def source_argument(args: list[str], cwd: Path) -> Path | None:
    """The source, manifest or artifact path jockyc will read, if any."""
    index = 1  # args[0] is the jockyc subcommand
    while index < len(args):
        argument = args[index]
        index += 1
        if argument == "--json":
            continue
        if argument.startswith("--"):
            index += 1  # skip this option's value
            continue
        return _absolute(argument, cwd)
    return None


def work_root(args: list[str], cwd: Path) -> Path:
    """The host directory bind-mounted at /work.

    The working directory, unless the source file lives outside it, in which
    case that file's own directory is mounted so the mount stays narrow.
    """
    target = source_argument(args, cwd)
    if target is not None and not _is_within(target, cwd):
        return target.parent
    return cwd


def _map_path(value: str, cwd: Path, root: Path) -> str:
    """Translate a host path that is known to sit inside the work root."""
    absolute = _absolute(value, cwd)
    if not _is_within(absolute, root):
        raise DockerUnavailable(f"{absolute} is outside the mounted work root {root}")
    relative = absolute.relative_to(root).as_posix()
    if relative == ".":
        return CONTAINER_WORKDIR
    return str(PurePosixPath(CONTAINER_WORKDIR) / relative)


def _map_output(value: str, cwd: Path, root: Path, mounts: dict[str, str]) -> str:
    """Translate an --output path, mounting its directory if it escapes the root."""
    absolute = _absolute(value, cwd)
    if _is_within(absolute, root):
        return _map_path(value, cwd, root)
    mounts[str(absolute.parent)] = OUTPUT_MOUNT
    return str(PurePosixPath(OUTPUT_MOUNT) / absolute.name)


def container_command(docker: str, args: list[str], cwd: Path) -> list[str]:
    """A full `docker run` argv, with every host path translated.

    The container runs in the mounted work root, so relative paths -- such as
    the default `<stem>.variants` directory a variant run writes -- resolve
    exactly as they would natively.
    """
    root = work_root(args, cwd)
    if root == root.parent:
        raise DockerUnavailable(f"refusing to bind-mount the filesystem root as {DOCKER_IMAGE}")

    mounts: dict[str, str] = {str(root): CONTAINER_WORKDIR}
    translated: list[str] = []
    index = 0
    while index < len(args):
        argument = args[index]
        index += 1

        if argument == "--json":
            translated.append(argument)
            continue

        if argument.startswith("--"):
            translated.append(argument)
            if index < len(args):
                value = args[index]
                index += 1
                if argument in PATH_OPTIONS:
                    translated.append(_map_output(value, cwd, root, mounts))
                else:
                    translated.append(value)
            continue

        if looks_like_source(argument, cwd):
            translated.append(_map_path(argument, cwd, root))
        else:
            translated.append(argument)

    argv = [docker, "run", "--rm", "-w", CONTAINER_WORKDIR]
    for host, container in mounts.items():
        argv += ["-v", f"{host}:{container}"]
    return [*argv, DOCKER_IMAGE, DOCKER_JOCKYC, *translated]
