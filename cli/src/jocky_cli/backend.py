"""Deterministic selection of the backend that runs the jockyc compiler.

Exactly one of these is used, in this order, and nothing else:

1. an explicit ``JOCKYC`` environment variable naming an executable file;
2. a jockyc built inside a JOCKY checkout (this one, or an enclosing one);
3. ``jockyc`` on ``PATH``;
4. the ``jockey-native:foundation`` container image.

Resolution is read-only. It never builds, downloads or installs anything, and
it never falls back to an execution method outside this list.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

#: Fallback image, produced by infra/docker/native.Dockerfile.
DOCKER_IMAGE = "jockey-native:foundation"

#: Compiler inside that image, at the path the Dockerfile builds it to.
DOCKER_JOCKYC = "/src/build/native/native/compiler/jockyc"

#: Where the container sees the mounted host working directory.
CONTAINER_WORKDIR = "/work"

#: Compiler path relative to the root of a JOCKY checkout.
LOCAL_BUILD = Path("build/native/native/compiler/jockyc")

#: The documented way to produce the fallback image. jocky never runs this itself.
DOCKER_BUILD_COMMAND = f"docker build -f infra/docker/native.Dockerfile -t {DOCKER_IMAGE} ."

NATIVE = "native"
DOCKER = "docker"


@dataclass(frozen=True)
class Backend:
    """How jocky reaches the compiler."""

    kind: str
    path: str | None
    origin: str


def is_executable(path: Path) -> bool:
    """True when `path` names a file this process is allowed to execute."""
    return path.is_file() and os.access(path, os.X_OK)


def env_jockyc() -> str | None:
    """The JOCKYC environment variable, or None when it is unset or blank."""
    value = os.environ.get("JOCKYC", "").strip()
    return value or None


def local_candidates(cwd: Path) -> list[Path]:
    """Checkout-relative compiler paths, most specific first.

    Covers the working directory and its ancestors, so jocky works from any
    subdirectory of a checkout, and the checkout that owns this module, so an
    editable install finds the compiler it was installed from.
    """
    roots: list[Path] = [cwd, *cwd.parents]
    roots.extend(Path(__file__).resolve().parents)

    candidates: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        candidate = root / LOCAL_BUILD
        if str(candidate) not in seen:
            seen.add(str(candidate))
            candidates.append(candidate)
    return candidates


def find_local_jockyc(cwd: Path) -> Path | None:
    """The first compiler built inside a discoverable JOCKY checkout."""
    for candidate in local_candidates(cwd):
        if is_executable(candidate):
            return candidate
    return None


def resolve_backend(cwd: Path | None = None) -> Backend:
    """Pick the backend using the documented order.

    A Docker backend is returned as the final candidate even when the image is
    absent; callers decide whether it is usable. `jocky doctor` reports why.
    """
    cwd = Path.cwd() if cwd is None else Path(cwd)

    configured = env_jockyc()
    if configured is not None:
        candidate = Path(configured).expanduser()
        if is_executable(candidate):
            return Backend(NATIVE, str(candidate), "JOCKYC environment variable")

    local = find_local_jockyc(cwd)
    if local is not None:
        return Backend(NATIVE, str(local), "local JOCKY checkout")

    on_path = shutil.which("jockyc")
    if on_path is not None:
        return Backend(NATIVE, on_path, "PATH")

    return Backend(DOCKER, None, f"docker image {DOCKER_IMAGE}")
