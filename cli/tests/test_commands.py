"""Tests for jocky's composed commands.

The compiler itself is exercised by the native test suite, not here. These
tests drive the composed commands against a stub jockyc that returns the
document shapes jockyc really emits, and assert that jocky re-presents those
fields, forwards a clean argv, and refuses what it cannot back with real data.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from jocky_cli import backend, container, main, options

SOURCE_HASH = "5d43781568ec7fe1da1c695184f717bb13aa026596075bd4cce589e888b3b2a8"
JIR_HASH = "2a1b96faa68d5a0536a48d99d0dbb04a0b40c2934ec19ffe8feb77735634323c"
RESULT_HASH = "25052cb72bd9d7eb5496c4fe18e07ac9420dc7613c3ace8b8208bfccf242f4d3"

#: A stand-in for jockyc. It answers the same subcommands with documents that
#: carry the same fields, so jocky's own parsing and presentation are tested
#: rather than the compiler's.
STUB = '''\
import hashlib
import json
import os
import sys

SOURCE_HASH = "5d43781568ec7fe1da1c695184f717bb13aa026596075bd4cce589e888b3b2a8"
JIR_HASH = "2a1b96faa68d5a0536a48d99d0dbb04a0b40c2934ec19ffe8feb77735634323c"
RESULT_HASH = "25052cb72bd9d7eb5496c4fe18e07ac9420dc7613c3ace8b8208bfccf242f4d3"
TRIPLES = {
    "host": "arm64-apple-darwin",
    "linux-x86_64": "x86_64-unknown-linux-gnu",
    "windows-x86_64": "x86_64-pc-windows-msvc",
    "linux-aarch64": "aarch64-unknown-linux-gnu",
}


def manifest(seed, artifact=None, target="host"):
    return {
        "schema_version": "1.0.0",
        "kind": "VariantManifest",
        "variant_id": "%064x" % seed,
        "variant_seed": "%016x" % seed,
        "source_hash": SOURCE_HASH,
        "jir_hash": JIR_HASH,
        "llvm_ir_hash": "%064x" % (seed + 100),
        "compiler_version": "0.4.0",
        "llvm_version": "18.1.3",
        "target_triple": TRIPLES.get(target, target),
        "execution_mode": "native",
        "profile": "balanced",
        "artifact_hash": artifact,
        "semantic_result_hash": RESULT_HASH,
        "structural_fingerprint": "%064x" % (seed + 200),
        "structural_metrics": {
            "llvm_basic_block_count": 60 + (seed % 7),
            "function_count": 23,
            "generated_helper_count": 15,
            "selected_lowering_strategy_ids": [seed % 5],
        },
        "literal_pool": {"enabled": False},
        "created_at": "2026-09-28T00:00:00Z",
    }


JIR = {
    "schema_version": "1.0.0",
    "kind": "JIRModule",
    "compiler_version": "0.3.0",
    "source_hash": SOURCE_HASH,
    "hunt": "system-baseline",
    "case": "system",
    "targets": [],
    "runtime": {
        "backend": "llvm",
        "execution": "memory",
        "variant": {"enabled": True, "seed": "auto", "profile": "balanced"},
    },
    "target_os": ["linux", "windows"],
    "required_capabilities": ["system.read"],
    "budget": {
        "schema_version": "1.0.0",
        "cpu_percent": 20,
        "memory_bytes": 256000000,
        "io_bytes": 150000000,
        "duration_ms": 120000,
    },
    "instructions": [
        {"id": 1, "opcode": "collect", "required_capabilities": []},
        {"id": 5, "opcode": "collect", "required_capabilities": ["system.read"]},
    ],
    "executable": False,
}


def option(name, literal):
    return {
        "name": name,
        "value": {"kind": "literal", "value": literal, "literal_kind": "quantity"},
        "fields": [],
        "span": {},
    }


AST = {
    "schema_version": "1.0.0",
    "kind": "Program",
    "case": "system",
    "hunt": "system-baseline",
    "selectors": [],
    "target_os": ["linux", "windows"],
    "runtime": {},
    "variant": {},
    "budget": {"cpu": option("cpu", "20%"), "duration": option("duration", "120s")},
    "capabilities": ["system.read"],
    "statements": [],
}

PLAN = {
    "schema_version": "1.0.0",
    "kind": "FrontendExecutionPlan",
    "source_hash": SOURCE_HASH,
    "jir_hash": JIR_HASH,
    "targets": [],
    "target_os": ["linux", "windows"],
    "required_collectors": ["system"],
    "required_capabilities": ["system.read"],
    "pushdown": [],
    "projected_fields": [],
    "expected_result_schemas": [
        {"instruction_id": 1, "result_type": {"name": "dataset", "nullable": False}},
        {"instruction_id": 5, "result_type": {"name": "dataset", "nullable": True}},
    ],
    "budget": {},
    "runtime": {},
    "warnings": [],
    "dispatchable": False,
    "admission_status": "REQUIRES_ENDPOINT_POLICY_AND_LLVM_LOWERING",
}

CHECK = {
    "schema_version": "1.0.0",
    "kind": "FrontendCheck",
    "valid": True,
    "hunt": "system-baseline",
    "source_hash": SOURCE_HASH,
    "jir_hash": JIR_HASH,
    "instruction_count": 6,
    "warnings": [],
    "executable": False,
}


def parse(argv):
    values = {}
    positionals = []
    index = 0
    while index < len(argv):
        item = argv[index]
        index += 1
        if item == "--json":
            continue
        if item.startswith("--"):
            values[item] = argv[index]
            index += 1
        else:
            positionals.append(item)
    return positionals, values


def seed_of(values, index=0):
    if "--seed" in values:
        return int(values["--seed"], 16)
    return int(SOURCE_HASH[:16], 16) + index


def emit(document):
    sys.stdout.write(json.dumps(document) + "\\n")


def main():
    argv = sys.argv[1:]
    log = os.environ.get("JOCKY_STUB_LOG")
    if log:
        with open(log, "a") as handle:
            handle.write(json.dumps(argv) + "\\n")

    command = argv[0] if argv else ""
    positionals, values = parse(argv[1:] if argv else [])

    if command == "check":
        emit(CHECK)
    elif command == "jir":
        emit(JIR)
    elif command == "ast":
        emit(AST)
    elif command == "plan":
        emit(PLAN)
    elif command == "llvm":
        seed = seed_of(values)
        emit({
            "schema_version": "1.0.0",
            "kind": "LLVMModule",
            "ir": "; ModuleID = 'system'\\n",
            "manifest": manifest(seed),
            "profile": {},
        })
    elif command == "variants":
        count = int(values.get("--count", "3"))
        base = seed_of(values)
        directory = values["--output"]
        os.makedirs(directory, exist_ok=True)
        samples = []
        for index in range(count):
            seed = base + index
            artifact = "%064x" % (seed + 300)
            name = os.path.join(directory, "%064x.o" % seed)
            with open(name, "wb") as handle:
                handle.write(b"OBJECT" + str(index).encode())
            samples.append({
                "manifest": manifest(seed, artifact),
                "profile": {"execution_ms": 0.5 + index},
                "artifact_path": name,
            })
        emit({
            "schema_version": "1.0.0",
            "kind": "VariantSet",
            "simulation": True,
            "simulation_label": "DETERMINISTIC_COMPILER_FIXTURE",
            "semantic_equivalence": True,
            "samples": samples,
        })
    elif command == "compile":
        seed = seed_of(values)
        path = values["--output"]
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        payload = b"OBJECT" + ("%x" % seed).encode()
        with open(path, "wb") as handle:
            handle.write(payload)
        emit({
            "manifest": manifest(
                seed,
                hashlib.sha256(payload).hexdigest(),
                values.get("--target", "host"),
            ),
            "profile": {},
        })
    elif command == "variant-info":
        path = positionals[0]
        if "tampered" in path:
            sys.stderr.write(
                "JOCKY E265: Artifact bytes do not match the manifest SHA-256.\\n"
            )
            return 1
        if path.endswith(".json"):
            with open(path) as handle:
                document = json.load(handle)
        else:
            document = manifest(int(SOURCE_HASH[:16], 16), "0" * 64)
        emit(document)
    else:
        sys.stderr.write("jockyc: unknown command %s\\n" % command)
        return 1
    return 0


sys.exit(main())
'''


@pytest.fixture
def compiler_stub(tmp_path, monkeypatch):
    """An executable stub jockyc, selected through JOCKYC, logging every argv."""
    stub = tmp_path / "jockyc-stub.py"
    stub.write_text(STUB)
    launcher = tmp_path / "jockyc"
    launcher.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{stub}" "$@"\n')
    launcher.chmod(0o755)

    log = tmp_path / "argv.log"
    monkeypatch.setenv("JOCKYC", str(launcher))
    monkeypatch.setenv("JOCKY_STUB_LOG", str(log))
    return launcher, log


def calls(log: Path) -> list[list[str]]:
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text().splitlines()]


def source(tmp_path: Path) -> str:
    hunt = tmp_path / "hunt.jky"
    hunt.write_text('hunt "system-baseline" {}\n')
    return str(hunt)


def image_present(path, image=container.DOCKER_IMAGE):
    """Every image lookup succeeds, so only the backend choice is exercised."""
    return True


# --- argument handling -------------------------------------------------------


def test_jit_execution_is_an_alias_for_memory():
    args = main.normalize(["run", "hunt.jky", "--execution", "jit"])
    assert args == ["run", "hunt.jky", "--execution", "memory"]


def test_bare_file_with_jit_is_normalised():
    args = main.normalize(["hunt.jky", "--execution", "jit"])
    assert args == ["run", "hunt.jky", "--execution", "memory"]


def test_dry_run_maps_a_bare_file_to_the_plan_stage():
    assert main.normalize(["hunt.jky", "--dry-run"]) == ["plan", "hunt.jky"]


def test_dry_run_maps_explicit_run_to_the_plan_stage():
    args = main.normalize(["run", "hunt.jky", "--dry-run", "--json"])
    assert args == ["plan", "hunt.jky", "--json"]


def test_dry_run_is_rejected_for_other_commands():
    with pytest.raises(options.UsageError):
        main.normalize(["compile", "hunt.jky", "--dry-run"])


def test_target_aliases_are_translated():
    assert main.normalize(["llvm", "hunt.jky", "--target", "linux"]) == [
        "llvm",
        "hunt.jky",
        "--target",
        "linux-x86_64",
    ]
    assert main.normalize(["llvm", "hunt.jky", "--target", "windows"])[-1] == (
        "windows-x86_64"
    )
    assert main.normalize(["compile", "hunt.jky", "--target", "arm64"])[-1] == (
        "linux-aarch64"
    )


def test_canonical_targets_are_left_alone():
    args = ["compile", "hunt.jky", "--target", "windows-x86_64"]
    assert main.normalize(args) == args


def test_all_target_is_not_rewritten():
    args = ["forge", "hunt.jky", "--target", "all"]
    assert main.normalize(args) == args


# --- help and not-exposed surface -------------------------------------------


def test_help_lists_the_composed_commands(capsys):
    assert main.main(["--help"]) == 0
    printed = capsys.readouterr().out
    for command in ("caps", "budget", "fingerprint", "diverge", "diff", "pipeline"):
        assert command in printed
    assert "not exposed yet" in printed


@pytest.mark.parametrize("command", sorted(main.NOT_EXPOSED))
def test_not_exposed_commands_say_so(command, capsys):
    assert main.main([command]) == main.EXIT_USAGE
    printed = capsys.readouterr().err
    assert "NOT EXPOSED YET" in printed
    assert command in printed


@pytest.mark.parametrize("flag", ["--endpoint", "--transport"])
def test_endpoint_and_transport_requests_are_refused(flag, capsys):
    assert main.main(["run", "hunt.jky", flag, "x"]) == main.EXIT_USAGE
    assert "NOT EXPOSED YET" in capsys.readouterr().err


# --- local inspection --------------------------------------------------------


def test_caps_reports_capabilities_and_their_instruction(compiler_stub, tmp_path, capsys):
    hunt = source(tmp_path)
    assert main.main(["caps", hunt]) == 0
    printed = capsys.readouterr().out
    assert "system.read" in printed
    assert "collect" in printed
    assert SOURCE_HASH in printed


def test_caps_json_carries_the_compiler_values(compiler_stub, tmp_path, capsys):
    hunt = source(tmp_path)
    assert main.main(["caps", hunt, "--json"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["kind"] == "JockyCaps"
    assert document["capabilities"] == ["system.read"]
    assert document["source_hash"] == SOURCE_HASH


def test_budget_reports_values_and_declared_literals(compiler_stub, tmp_path, capsys):
    hunt = source(tmp_path)
    assert main.main(["budget", hunt]) == 0
    printed = capsys.readouterr().out
    assert "cpu_percent" in printed
    assert "declared" in printed
    assert "default" in printed
    # The declared spelling comes from the compiler's AST, not from jocky.
    assert "20%" in printed
    assert "120s" in printed
    # The resolved integers come from the compiler's JIR.
    assert "256000000" in printed
    assert "120000" in printed


def test_budget_json_names_its_two_sources(compiler_stub, tmp_path, capsys):
    hunt = source(tmp_path)
    assert main.main(["budget", hunt, "--json"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["command"] == "jir+ast"
    origins = {entry["field"]: entry["origin"] for entry in document["budget"]}
    assert origins["cpu_percent"] == "declared"
    assert origins["memory_bytes"] == "default"


def test_types_reports_the_plan_result_schema(compiler_stub, tmp_path, capsys):
    hunt = source(tmp_path)
    assert main.main(["types", hunt]) == 0
    printed = capsys.readouterr().out
    assert "dataset" in printed
    assert "true" in printed


def test_metrics_reports_structural_metrics_only(compiler_stub, tmp_path, capsys):
    hunt = source(tmp_path)
    assert main.main(["metrics", hunt]) == 0
    printed = capsys.readouterr().out
    assert "basic blocks" in printed
    assert "structural fingerprint" in printed


def test_fingerprint_uses_compiler_hashes(compiler_stub, tmp_path, capsys):
    hunt = source(tmp_path)
    assert main.main(["fingerprint", hunt]) == 0
    printed = capsys.readouterr().out
    assert SOURCE_HASH in printed
    assert JIR_HASH in printed
    assert "structural fingerprint" in printed
    # An artifact hash is not invented when the llvm stage emits no object.
    assert "not emitted by `llvm`" in printed


def test_fingerprint_forwards_target_and_seed(compiler_stub, tmp_path):
    hunt = source(tmp_path)
    launcher, log = compiler_stub
    assert main.main(["fingerprint", hunt, "--target", "linux-x86_64", "--seed", "7"]) == 0
    forwarded = calls(log)[0]
    assert forwarded[0] == "llvm"
    assert "--target" in forwarded and forwarded[forwarded.index("--target") + 1] == (
        "linux-x86_64"
    )
    assert forwarded[forwarded.index("--seed") + 1] == "0x7"


def test_source_file_is_required(compiler_stub, capsys):
    assert main.main(["caps"]) == main.EXIT_USAGE
    assert "exactly one" in capsys.readouterr().err


# --- variants ----------------------------------------------------------------


def test_diverge_reports_distinct_variants(compiler_stub, tmp_path, capsys):
    hunt = source(tmp_path)
    output = tmp_path / "variants"
    assert main.main(["diverge", hunt, "--count", "3", "--output", str(output)]) == 0
    printed = capsys.readouterr().out
    assert "distinct variant ids" in printed
    assert "3/3" in printed
    assert "semantic equivalence" in printed
    assert "not endpoint evidence" in printed


def test_diverge_json_exposes_the_manifests(compiler_stub, tmp_path, capsys):
    hunt = source(tmp_path)
    output = tmp_path / "variants"
    assert main.main(["diverge", hunt, "--count", "2", "--output", str(output), "--json"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["kind"] == "JockyDiverge"
    assert document["count"] == 2
    assert document["distinct"]["artifact_hashes"] == 2
    assert len(document["variants"]) == 2


def test_diverge_asks_jockyc_for_the_host_target(compiler_stub, tmp_path):
    hunt = source(tmp_path)
    _, log = compiler_stub
    main.main(["diverge", hunt, "--count", "2", "--output", str(tmp_path / "v")])
    forwarded = calls(log)[0]
    assert forwarded[0] == "variants"
    assert "--execution" not in forwarded
    assert "--json" in forwarded


def test_diverge_refuses_a_cross_target(compiler_stub, tmp_path, capsys):
    hunt = source(tmp_path)
    assert main.main(["diverge", hunt, "--target", "linux-x86_64"]) == main.EXIT_USAGE
    assert "E263" in capsys.readouterr().err


def test_equivalence_reports_the_shared_result_hash(compiler_stub, tmp_path, capsys):
    hunt = source(tmp_path)
    output = tmp_path / "variants"
    assert main.main(["equivalence", hunt, "--count", "3", "--output", str(output)]) == 0
    printed = capsys.readouterr().out
    assert "PASS" in printed
    assert RESULT_HASH in printed


def test_diff_compares_two_seeds_structurally(compiler_stub, tmp_path, capsys):
    hunt = source(tmp_path)
    assert main.main(["diff", hunt, "--seed-a", "1", "--seed-b", "2"]) == 0
    printed = capsys.readouterr().out
    assert "STRUCTURALLY DISTINCT" in printed
    assert "source hash" in printed
    assert "basic blocks" in printed
    assert "LLVM IR text is not diffed" in printed


def test_diff_requires_both_seeds(compiler_stub, tmp_path, capsys):
    hunt = source(tmp_path)
    assert main.main(["diff", hunt, "--seed-a", "1"]) == main.EXIT_USAGE
    assert "--seed-b" in capsys.readouterr().err


def test_diff_says_identical_seeds_are_identical(compiler_stub, tmp_path, capsys):
    hunt = source(tmp_path)
    assert main.main(["diff", hunt, "--seed-a", "4", "--seed-b", "4"]) == 0
    assert "IDENTICAL SEEDS" in capsys.readouterr().out


# --- forge and pipeline ------------------------------------------------------


def test_forge_writes_one_object_per_seed(compiler_stub, tmp_path, capsys):
    hunt = source(tmp_path)
    output = tmp_path / "forge"
    assert main.main(["forge", hunt, "--count", "3", "--output", str(output)]) == 0
    objects = sorted(output.glob("*.o"))
    assert len(objects) == 3
    printed = capsys.readouterr().out
    assert "distinct artifacts" in printed
    assert "not the control-plane Build Forge" in printed


def test_forge_compiles_each_requested_target(compiler_stub, tmp_path, capsys):
    hunt = source(tmp_path)
    output = tmp_path / "forge"
    launcher, log = compiler_stub
    argv = ["forge", hunt, "--count", "2", "--target", "all", "--output", str(output)]
    assert main.main(argv) == 0
    targets = [call[call.index("--target") + 1] for call in calls(log) if "--target" in call]
    assert targets == ["linux-x86_64", "linux-x86_64", "windows-x86_64", "windows-x86_64"]
    assert (output / "linux-x86_64").is_dir()
    assert (output / "windows-x86_64").is_dir()
    assert "ENVIRONMENT DEPENDENT" in capsys.readouterr().out


def test_pipeline_runs_every_stage_on_the_host(compiler_stub, tmp_path, capsys):
    hunt = source(tmp_path)
    output = tmp_path / "pipeline"
    assert main.main(["pipeline", hunt, "--count", "3", "--output", str(output)]) == 0
    printed = capsys.readouterr().out
    for stage in ("CHECK", "JIR", "LLVM", "VARIANTS", "DISTINCTNESS", "COMPILE", "RESULT"):
        assert stage in printed
    assert "MEMORY/JIT" in printed
    assert "SKIP" not in printed
    assert "3/3 distinct artifact hashes" in printed


def test_pipeline_skips_cross_target_stages_honestly(compiler_stub, tmp_path, capsys):
    hunt = source(tmp_path)
    output = tmp_path / "pipeline"
    argv = ["pipeline", hunt, "--count", "2", "--target", "linux-x86_64"]
    argv += ["--output", str(output)]
    assert main.main(argv) == 0
    printed = capsys.readouterr().out
    assert "SKIP" in printed
    assert "requires the host target" in printed
    assert "cross-target execution requires linux-x86_64" in printed
    assert (output / "linux-x86_64").is_dir()


def test_pipeline_json_summarises_identity(compiler_stub, tmp_path, capsys):
    hunt = source(tmp_path)
    output = tmp_path / "pipeline"
    argv = ["pipeline", hunt, "--count", "2", "--output", str(output), "--json"]
    assert main.main(argv) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["kind"] == "JockyPipeline"
    assert document["status"] == "PASS"
    identity = document["targets"][0]["identity"]
    assert identity["source_hash"] == SOURCE_HASH
    assert len(identity["artifact_hashes"]) == 2


def test_pipeline_verbose_prints_stage_documents(compiler_stub, tmp_path, capsys):
    hunt = source(tmp_path)
    output = tmp_path / "pipeline"
    argv = ["pipeline", hunt, "--count", "1", "--output", str(output), "--verbose"]
    assert main.main(argv) == 0
    printed = capsys.readouterr().out
    assert '"kind": "FrontendCheck"' in printed
    _, log = compiler_stub
    assert all("--verbose" not in call for call in calls(log))


# --- evidence ----------------------------------------------------------------


def test_verify_passes_for_a_matching_artifact(compiler_stub, tmp_path, capsys):
    artifact = tmp_path / "variant.o"
    artifact.write_bytes(b"OBJECT")
    assert main.main(["verify", str(artifact)]) == 0
    printed = capsys.readouterr().out
    assert "artifact bytes match the manifest SHA-256" in printed
    assert "no signature is checked" in printed


def test_verify_reports_a_compiler_rejection(compiler_stub, tmp_path, capsys):
    artifact = tmp_path / "tampered.o"
    artifact.write_bytes(b"TAMPERED")
    assert main.main(["verify", str(artifact)]) == 1
    assert "E265" in capsys.readouterr().err


def test_verify_says_when_no_bytes_were_compared(compiler_stub, tmp_path, capsys):
    manifest = tmp_path / "variant.manifest.json"
    manifest.write_text(json.dumps({"kind": "VariantManifest", "variant_id": "ab"}))
    assert main.main(["verify", str(manifest)]) == 0
    printed = capsys.readouterr().out
    assert "no artifact bytes were supplied" in printed


def test_manifest_forwards_to_variant_info(compiler_stub, tmp_path, capsys):
    artifact = tmp_path / "variant.o"
    artifact.write_bytes(b"OBJECT")
    _, log = compiler_stub
    assert main.main(["manifest", str(artifact), "--json"]) == 0
    forwarded = calls(log)[0]
    assert forwarded[0] == "variant-info"
    assert forwarded[-1] == "--json"
    assert json.loads(capsys.readouterr().out)["kind"] == "VariantManifest"


# --- docker fallback ---------------------------------------------------------


def test_composed_commands_work_through_the_docker_fallback(tmp_path, monkeypatch, capsys):
    stub = tmp_path / "jockyc-stub.py"
    stub.write_text(STUB)
    docker = tmp_path / "docker"
    docker.write_text(
        "#!/bin/sh\n"
        "# Drop docker's own arguments and run the containerised compiler.\n"
        "while [ -n \"$1\" ]; do\n"
        "  case \"$1\" in\n"
        "    -v|-w) shift 2 ;;\n"
        "    run|--rm) shift ;;\n"
        "    *) break ;;\n"
        "  esac\n"
        "done\n"
        "shift\n"  # image
        "shift\n"  # compiler path inside the image
        f'exec "{sys.executable}" "{stub}" "$@"\n',
    )
    docker.chmod(0o755)

    log = tmp_path / "argv.log"
    monkeypatch.setenv("JOCKY_STUB_LOG", str(log))
    monkeypatch.delenv("JOCKYC", raising=False)
    monkeypatch.setattr(backend, "local_candidates", lambda cwd: [])
    monkeypatch.setattr(backend.shutil, "which", lambda name: None)
    monkeypatch.setattr(container, "docker_cli", lambda: str(docker))
    monkeypatch.setattr(container, "daemon_reachable", lambda path: True)
    monkeypatch.setattr(container, "image_present", image_present)

    hunt = source(tmp_path)
    assert main.main(["caps", hunt, "--json"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["capabilities"] == ["system.read"]

    forwarded = calls(log)[0]
    assert forwarded[0] == "jir"
    assert forwarded[-1] == "--json"
    # The bind mount is what keeps the compiler's view of the source intact.
    assert forwarded[1].startswith(container.CONTAINER_WORKDIR)


def test_docker_fallback_reports_a_missing_image(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("JOCKYC", raising=False)
    monkeypatch.setattr(backend, "local_candidates", lambda cwd: [])
    monkeypatch.setattr(backend.shutil, "which", lambda name: None)
    monkeypatch.setattr(container, "docker_cli", lambda: "/usr/bin/docker")
    monkeypatch.setattr(container, "daemon_reachable", lambda path: True)
    monkeypatch.setattr(container, "image_present", lambda path, image=None: False)

    hunt = source(tmp_path)
    assert main.main(["caps", hunt]) == main.EXIT_UNAVAILABLE
    printed = capsys.readouterr().err
    assert "not built" in printed
    assert container.DOCKER_IMAGE in printed
