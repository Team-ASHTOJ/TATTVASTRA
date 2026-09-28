"""Focused tests for jocky's launcher behaviour.

These cover the parts jocky actually owns: backend selection order, the
default `.jky` expansion, and Docker path translation. The compiler itself is
exercised by the native test suite, not here.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from jocky_cli import backend, container, main


def make_executable(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\nexit 0\n")
    path.chmod(0o755)
    return path


@pytest.fixture
def clean_env(monkeypatch):
    """No JOCKYC, and no jockyc on PATH unless a test says otherwise."""
    monkeypatch.delenv("JOCKYC", raising=False)
    real_which = shutil.which

    def fake_which(name, *args, **kwargs):
        if name == "jockyc":
            return None
        return real_which(name, *args, **kwargs)

    monkeypatch.setattr(backend.shutil, "which", fake_which)


# --- default `.jky` expansion ------------------------------------------------


def test_bare_jky_runs_with_memory_execution():
    assert main.normalize(["hunt.jky"]) == ["run", "hunt.jky", "--execution", "memory"]


def test_bare_jky_keeps_extra_options():
    args = main.normalize(["hunt.jky", "--json", "--seed", "7"])
    assert args == ["run", "hunt.jky", "--execution", "memory", "--json", "--seed", "7"]


def test_explicit_execution_is_not_overridden():
    args = main.normalize(["hunt.jky", "--execution", "native"])
    assert args == ["run", "hunt.jky", "--execution", "native"]


def test_subcommands_pass_through_untouched():
    assert main.normalize(["check", "hunt.jky"]) == ["check", "hunt.jky"]
    assert main.normalize(["variants", "hunt.jky", "--count", "3"]) == [
        "variants",
        "hunt.jky",
        "--count",
        "3",
    ]


# --- backend selection -------------------------------------------------------


def test_jockyc_env_var_wins(tmp_path, monkeypatch, clean_env):
    compiler = make_executable(tmp_path / "custom-jockyc")
    monkeypatch.setenv("JOCKYC", str(compiler))
    selected = backend.resolve_backend(cwd=tmp_path)
    assert selected.kind == backend.NATIVE
    assert selected.path == str(compiler)


def test_invalid_jockyc_env_var_is_skipped(tmp_path, monkeypatch, clean_env):
    monkeypatch.setenv("JOCKYC", str(tmp_path / "missing"))
    monkeypatch.setattr(backend, "local_candidates", lambda cwd: [])
    monkeypatch.setattr(backend.shutil, "which", lambda name: "/usr/bin/jockyc")
    selected = backend.resolve_backend(cwd=tmp_path)
    assert selected.kind == backend.NATIVE
    assert selected.path == "/usr/bin/jockyc"


def test_local_checkout_is_preferred_over_path(tmp_path, monkeypatch, clean_env):
    local = make_executable(tmp_path / backend.LOCAL_BUILD)
    monkeypatch.setattr(backend.shutil, "which", lambda name: "/usr/bin/jockyc")
    selected = backend.resolve_backend(cwd=tmp_path)
    assert selected.kind == backend.NATIVE
    assert selected.path == str(local)


def test_local_checkout_is_found_from_a_subdirectory(tmp_path, clean_env):
    local = make_executable(tmp_path / backend.LOCAL_BUILD)
    nested = tmp_path / "examples" / "basic"
    nested.mkdir(parents=True)
    assert backend.find_local_jockyc(nested) == local


def test_docker_is_the_last_resort(tmp_path, monkeypatch, clean_env):
    monkeypatch.setattr(backend, "local_candidates", lambda cwd: [])
    selected = backend.resolve_backend(cwd=tmp_path)
    assert selected.kind == backend.DOCKER
    assert backend.DOCKER_IMAGE in selected.origin


# --- docker path translation -------------------------------------------------


def test_relative_source_is_translated_into_the_work_mount(tmp_path):
    argv = container.container_command("docker", ["check", "hunt.jky"], tmp_path)
    assert f"{tmp_path}:{container.CONTAINER_WORKDIR}" in argv
    assert argv[-4:] == [
        backend.DOCKER_IMAGE,
        backend.DOCKER_JOCKYC,
        "check",
        f"{container.CONTAINER_WORKDIR}/hunt.jky",
    ]


def test_work_root_is_the_working_directory_for_a_local_source(tmp_path):
    assert container.work_root(["check", "hunt.jky"], tmp_path) == tmp_path


def test_work_root_narrows_to_an_outside_source(tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    source = elsewhere / "hunt.jky"
    source.write_text("hunt x {}\n")
    workdir = tmp_path / "here"
    workdir.mkdir()
    assert container.work_root(["check", str(source)], workdir) == elsewhere


def test_paths_with_spaces_survive_translation(tmp_path):
    spaced = tmp_path / "with space"
    spaced.mkdir()
    (spaced / "hunt.jky").write_text("hunt x {}\n")
    argv = container.container_command("docker", ["check", "with space/hunt.jky"], tmp_path)
    assert f"{tmp_path}:{container.CONTAINER_WORKDIR}" in argv
    assert f"{container.CONTAINER_WORKDIR}/with space/hunt.jky" in argv


def test_option_values_are_never_mistaken_for_paths(tmp_path):
    argv = container.container_command(
        "docker",
        ["llvm", "hunt.jky", "--target", "host", "--execution", "memory", "--count", "3"],
        tmp_path,
    )
    assert argv[-8:] == [
        "llvm",
        f"{container.CONTAINER_WORKDIR}/hunt.jky",
        "--target",
        "host",
        "--execution",
        "memory",
        "--count",
        "3",
    ]


def test_output_outside_the_root_gets_its_own_mount(tmp_path):
    workdir = tmp_path / "work"
    workdir.mkdir()
    (workdir / "hunt.jky").write_text("hunt x {}\n")
    target = tmp_path / "out" / "variant.ll"
    argv = container.container_command(
        "docker", ["llvm", "hunt.jky", "--output", str(target)], workdir
    )
    assert f"{target.parent}:{container.OUTPUT_MOUNT}" in argv
    assert f"{container.OUTPUT_MOUNT}/variant.ll" in argv


def test_container_runs_in_the_work_root(tmp_path):
    argv = container.container_command("docker", ["check", "hunt.jky"], tmp_path)
    assert argv[:5] == ["docker", "run", "--rm", "-w", container.CONTAINER_WORKDIR]


def test_mounting_the_filesystem_root_is_refused():
    with pytest.raises(container.DockerUnavailable):
        container.container_command("docker", ["check", "/hunt.jky"], Path("/"))


# --- exit status -------------------------------------------------------------


def test_compiler_exit_status_propagates(tmp_path, monkeypatch, clean_env):
    compiler = tmp_path / "jockyc"
    compiler.write_text("#!/bin/sh\nexit 3\n")
    compiler.chmod(0o755)
    monkeypatch.setenv("JOCKYC", str(compiler))
    assert main.main(["check", str(tmp_path / "hunt.jky")]) == 3


def test_help_and_version_do_not_need_a_backend(monkeypatch):
    monkeypatch.setattr(backend, "local_candidates", lambda cwd: [])
    monkeypatch.delenv("JOCKYC", raising=False)
    assert main.main(["--help"]) == 0
    assert main.main(["--version"]) == 0
    assert main.main([]) == 0
