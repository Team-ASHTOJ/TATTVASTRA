"""The install command delegates to pip without shell expansion."""

import subprocess
import sys

import pytest
from jocky_cli import container, main


@pytest.mark.parametrize("arguments", [[], ["-evil"], ["one", "two"], [""]])
def test_invalid_install(arguments, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("pip must not run for invalid arguments")

    monkeypatch.setattr(main.subprocess, "run", unexpected)
    assert main.main(["install", *arguments]) == main.EXIT_USAGE


@pytest.mark.parametrize("status", [0, 17])
def test_install_target_and_status(tmp_path, monkeypatch, capsys, status):
    target = tmp_path / "packages"
    monkeypatch.setenv("JOCKY_PYTHON_PACKAGES_DIR", str(target))
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        assert target.is_dir()
        return subprocess.CompletedProcess(argv, status)

    monkeypatch.setattr(main.subprocess, "run", run)
    assert main.main(["install", "humanize"]) == status
    assert calls == [
        (
            [sys.executable, "-m", "pip", "install", "--target", str(target), "humanize"],
            {"shell": False, "check": False},
        )
    ]
    output = capsys.readouterr().out
    if status == 0:
        assert output == (f"Installed humanize into JOCKY Python environment\nLocation: {target}\n")
    else:
        assert output == ""


def test_install_default_isolated_target(tmp_path, monkeypatch):
    monkeypatch.delenv("JOCKY_PYTHON_PACKAGES_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    target = tmp_path / ".jocky/python/site-packages"

    def run(argv, **kwargs):
        assert argv[-2] == str(target)
        assert target.is_dir()
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(main.subprocess, "run", run)
    assert main.main(["install", "humanize"]) == 0
    assert "install <package-spec>" in main.HELP


def test_container_run_mounts_same_packages_read_only(tmp_path, monkeypatch):
    packages = tmp_path / "packages"
    packages.mkdir()
    monkeypatch.setenv("JOCKY_PYTHON_PACKAGES_DIR", str(packages))
    argv = container.container_command("docker", ["run", "demo.jky"], tmp_path)
    assert f"{packages}:/jocky-python/site-packages:ro" in argv
    assert "JOCKY_PYTHON_PACKAGES_DIR=/jocky-python/site-packages" in argv


def test_container_run_without_packages_keeps_working(tmp_path, monkeypatch):
    monkeypatch.setenv("JOCKY_PYTHON_PACKAGES_DIR", str(tmp_path / "missing"))
    argv = container.container_command("docker", ["run", "demo.jky"], tmp_path)
    assert "/jocky-python/site-packages:ro" not in " ".join(argv)
    assert not any(value.startswith("JOCKY_PYTHON_PACKAGES_DIR=") for value in argv)
