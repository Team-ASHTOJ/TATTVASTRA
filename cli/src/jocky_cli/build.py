"""Composed build commands: forge and pipeline.

Both are deterministic compositions of existing jockyc operations. Neither is
the control-plane Build Forge, and neither claims behaviour the compiler does
not already have.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from . import compiler, options, report, variants

DEFAULT_COUNT = 3

#: `--target all` covers exactly the two cross targets jockyc already accepts.
ALL_TARGETS = ("linux-x86_64", "windows-x86_64")

#: jockyc names its objects after the host it was built on (`object_suffix()`),
#: so discovery accepts either convention while jocky names its own outputs
#: after the host this launcher runs on.
OBJECT_SUFFIXES = (".o", ".obj")
OBJECT_SUFFIX = ".obj" if os.name == "nt" else ".o"

FORGE_DISCLAIMER = (
    "`forge` composes jockyc compile locally; it is not the control-plane Build Forge"
)

CROSS_TARGET_NOTE = (
    "linking and running a non-host object needs a linker for that target "
    "(ENVIRONMENT DEPENDENT); these are compilation artifacts only"
)

STAGES_PER_TARGET = 8


def _targets(values: dict[str, str]) -> tuple[str, ...]:
    requested = values.get("--target", "host")
    return ALL_TARGETS if requested == "all" else (requested,)


def _objects(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    names = sorted(directory.iterdir())
    return [path for path in names if path.is_file() and path.suffix in OBJECT_SUFFIXES]


def _compile_one(source: str, target: str, seed: int, path: Path) -> dict:
    """Run jockyc's `compile` for one seed and return the emitted manifest."""
    argv = [
        "compile",
        source,
        "--target",
        target,
        "--execution",
        "native",
        "--output",
        str(path),
        *compiler.seed_arguments(seed),
        "--json",
    ]
    document = compiler.run_json(argv, Path.cwd(), source)
    return document.get("manifest") or {}


def _base_seed(source: str, explicit: int | None, module: dict | None = None) -> tuple[int, str]:
    """The seed composed commands start from, and where it came from."""
    if explicit is not None:
        return explicit, "explicit --seed"
    if module is None:
        module = compiler.run_json(["jir", source, "--json"], Path.cwd(), source)
    return compiler.default_seed(module)


def _rows(target: str, manifests: list[dict], seeds: list[int]) -> list[tuple]:
    rows = []
    for index, manifest in enumerate(manifests):
        structural = manifest.get("structural_metrics") or {}
        rows.append(
            (
                target,
                compiler.seed_text(seeds[index]),
                variants.display(manifest.get("variant_id")),
                variants.display(structural.get("llvm_basic_block_count")),
                variants.display(structural.get("function_count")),
                variants.display(structural.get("generated_helper_count")),
                variants.display(manifest.get("artifact_hash")),
            )
        )
    return rows


def forge(argv: list[str]) -> int:
    """Emit one AOT object and manifest per deterministic seed and target."""
    source, values, present = compiler.source_and_options(
        argv,
        ("--count", "--seed", "--target", "--output"),
        ("--json",),
        "forge",
    )
    count = options.count(values["--count"]) if "--count" in values else DEFAULT_COUNT
    explicit = options.parse_seed(values["--seed"]) if "--seed" in values else None
    targets = _targets(values)
    root = (
        Path(values["--output"]).resolve()
        if "--output" in values
        else Path.cwd() / f"{Path(source).stem}.forge"
    )

    base, origin = _base_seed(source, explicit)
    seeds = [base + index for index in range(count)]

    results = []
    for target in targets:
        directory = root if len(targets) == 1 else root / target
        manifests = [
            _compile_one(source, target, seed, directory / f"{seed:016x}{OBJECT_SUFFIX}")
            for seed in seeds
        ]
        results.append((target, manifests, directory))

    status = _forge_status(results, count)
    if "--json" in present:
        report.emit_json(
            {
                "schema_version": "1.0.0",
                "kind": "JockyForge",
                "source": source,
                "command": "compile",
                "count": count,
                "base_seed": compiler.seed_text(base),
                "base_seed_origin": origin,
                "status": "PASS" if status == 0 else "FAIL",
                "targets": [
                    {
                        "target": target,
                        "output": str(directory),
                        "distinct_artifacts": variants.distinct(manifests, "artifact_hash"),
                        "manifests": manifests,
                    }
                    for target, manifests, directory in results
                ],
            }
        )
        return status

    print(f"jocky forge — {source}")
    report.field("targets", ", ".join(targets))
    report.field("count", count)
    report.field("base seed", f"{compiler.seed_text(base)} ({origin})")
    report.field("output", str(root))
    for target, manifests, directory in results:
        report.heading(f"{target} — {directory}")
        report.table(
            ("TARGET", "SEED", "VARIANT", "BLOCKS", "FUNCS", "HELPERS", "ARTIFACT"),
            _rows(target, manifests, seeds),
            right=(3, 4, 5),
        )
    report.heading("distinctness")
    for target, manifests, _ in results:
        distinct = variants.distinct(manifests, "artifact_hash")
        verdict = "" if distinct == len(manifests) else "  NOT DISTINCT"
        report.field(target, f"{distinct}/{len(manifests)} distinct artifacts{verdict}")
    if any(target != "host" for target, _, _ in results):
        report.note(CROSS_TARGET_NOTE)
    report.note(FORGE_DISCLAIMER)
    return status


def _forge_status(results: list[tuple], count: int) -> int:
    for _, manifests, _ in results:
        if len(manifests) != count:
            return compiler.EXIT_COMPILER_FAILURE
        if variants.distinct(manifests, "artifact_hash") < count:
            return compiler.EXIT_COMPILER_FAILURE
    return 0


class _Run:
    """One target's pipeline: the stage log and what the stages produced."""

    def __init__(self, target: str, verbose: bool) -> None:
        self.target = target
        self.verbose = verbose
        self.index = 0
        self.failed = False
        self.skipped = 0
        self.identity: dict[str, object] = {}

    def stage(self, name: str, status: str, detail: str, document: dict | None = None) -> None:
        self.index += 1
        if status == "SKIP":
            self.skipped += 1
        if status == "FAIL":
            self.failed = True
        print(f"  [{self.index}/{STAGES_PER_TARGET}] {name:<16}{status:<7}{detail}")
        if self.verbose and document is not None:
            report.emit_json(document)


def _execution_detail(manifests: list[dict], equivalence: bool) -> str:
    timings = [
        profile.get("execution_ms")
        for manifest in manifests
        if isinstance(profile := manifest.get("profile"), dict)
    ]
    measured = [timing for timing in timings if isinstance(timing, (int, float))]
    detail = f"{len(manifests)} fixture executions, semantic equivalence "
    detail += "PASS" if equivalence else "FAIL"
    if measured:
        detail += f", slowest {max(measured):.3f} ms"
    return detail


def _pipeline_target(
    source: str,
    target: str,
    count: int,
    explicit: int | None,
    root: Path,
    verbose: bool,
) -> _Run:
    run = _Run(target, verbose)
    host = target == "host"
    directory = root if host else root / target
    target_args = ["--target", target]

    # CHECK — the compiler's own frontend verdict.
    check = compiler.run_json(["check", source, "--json"], Path.cwd(), source)
    run.identity["source_hash"] = check.get("source_hash")
    run.identity["jir_hash"] = check.get("jir_hash")
    run.stage(
        "CHECK",
        "PASS",
        f"{check.get('hunt')} — {check.get('instruction_count')} typed JIR "
        f"instructions, {len(check.get('warnings') or [])} warnings",
        check,
    )

    # JIR — the typed module every later stage consumes.
    module = compiler.run_json(["jir", source, "--json"], Path.cwd(), source)
    run.stage(
        "JIR",
        "PASS",
        f"{len(module.get('instructions') or [])} instructions, "
        f"{len(module.get('required_capabilities') or [])} capabilities",
        module,
    )

    # LLVM — lowering, with the compiler's own manifest.
    seed_args = compiler.seed_arguments(explicit) if explicit is not None else []
    lowered = compiler.run_json(
        ["llvm", source, "--json", *target_args, *seed_args], Path.cwd(), source
    )
    manifest = lowered.get("manifest") or {}
    structural = manifest.get("structural_metrics") or {}
    run.identity["llvm_ir_hash"] = manifest.get("llvm_ir_hash")
    run.identity["structural_fingerprint"] = manifest.get("structural_fingerprint")
    run.stage(
        "LLVM",
        "PASS",
        f"{structural.get('llvm_basic_block_count')} basic blocks, "
        f"{structural.get('function_count')} functions, "
        f"{structural.get('generated_helper_count')} helpers",
        lowered,
    )

    base, origin = _base_seed(source, explicit, module)
    seeds = [base + index for index in range(count)]

    if host:
        # VARIANTS, COMPILE and MEMORY are the stages jockyc can only run here.
        document, _ = variants.variant_set(source, count, explicit, directory)
        manifests = variants.variant_manifests(document)
        run.stage(
            "VARIANTS",
            "PASS",
            f"{len(manifests)} variants from base seed {compiler.seed_text(base)} ({origin})",
            document,
        )
        run.stage(
            "DISTINCTNESS",
            "PASS" if variants.distinct(manifests, "artifact_hash") == count else "FAIL",
            f"{variants.distinct(manifests, 'artifact_hash')}/{count} distinct artifact hashes",
        )
        objects = _objects(directory)
        run.stage(
            "COMPILE",
            "PASS" if len(objects) == count else "FAIL",
            f"{len(objects)} AOT objects, "
            f"{sum(path.stat().st_size for path in objects)} bytes in {directory}",
        )
        equivalence = bool(document.get("semantic_equivalence"))
        run.stage(
            "MEMORY/JIT",
            "PASS" if equivalence else "FAIL",
            _execution_detail(manifests, equivalence),
        )
        run.identity["semantic_result_hash"] = (
            manifests[0].get("semantic_result_hash") if manifests else None
        )
    else:
        # jockyc refuses variant generation and fixture execution off the host
        # target (E263); these objects are compiled, not executed.
        run.stage("VARIANTS", "SKIP", "jockyc requires the host target (E263)")
        manifests = [
            _compile_one(source, target, seed, directory / f"{seed:016x}{OBJECT_SUFFIX}")
            for seed in seeds
        ]
        run.stage(
            "DISTINCTNESS",
            "PASS" if variants.distinct(manifests, "artifact_hash") == count else "FAIL",
            f"{variants.distinct(manifests, 'artifact_hash')}/{count} distinct artifact hashes",
        )
        run.stage(
            "COMPILE",
            "PASS" if len(manifests) == count else "FAIL",
            f"{len(manifests)} {target} objects in {directory}",
        )
        run.stage("MEMORY/JIT", "SKIP", f"cross-target execution requires {target}")

    # RESULT — the compiled identity, straight from the manifests.
    newest = manifests[0] if manifests else {}
    run.identity["target_triple"] = newest.get("target_triple")
    run.identity["artifact_hashes"] = sorted(
        {manifest.get("artifact_hash") for manifest in manifests} - {None},
    )
    run.stage(
        "RESULT",
        "PASS" if len(manifests) == count else "FAIL",
        f"{len(manifests)}/{count} manifests, base seed from {origin}",
    )
    return run


def pipeline(argv: list[str]) -> int:
    """Run the demo sequence over the stages jockyc actually supports."""
    source, values, present = compiler.source_and_options(
        argv,
        ("--count", "--seed", "--target", "--output"),
        ("--json", "--verbose"),
        "pipeline",
    )
    count = options.count(values["--count"]) if "--count" in values else DEFAULT_COUNT
    explicit = options.parse_seed(values["--seed"]) if "--seed" in values else None
    targets = _targets(values)
    verbose = "--verbose" in present
    root = (
        Path(values["--output"]).resolve()
        if "--output" in values
        else Path.cwd() / f"{Path(source).stem}.pipeline"
    )

    started = time.monotonic()
    print(f"jocky pipeline — {source}")
    report.field("targets", ", ".join(targets))
    report.field("count", count)
    report.field("output", str(root))

    runs = []
    for target in targets:
        report.heading(target)
        runs.append(_pipeline_target(source, target, count, explicit, root, verbose))

    elapsed = (time.monotonic() - started) * 1000
    failed = any(run.failed for run in runs)
    skipped = sum(run.skipped for run in runs)

    if "--json" in present:
        report.emit_json(
            {
                "schema_version": "1.0.0",
                "kind": "JockyPipeline",
                "source": source,
                "count": count,
                "status": "FAIL" if failed else "PASS",
                "duration_ms": round(elapsed, 3),
                "targets": [
                    {
                        "target": run.target,
                        "status": "FAIL" if run.failed else "PASS",
                        "skipped_stages": run.skipped,
                        "identity": run.identity,
                    }
                    for run in runs
                ],
            }
        )
    else:
        report.heading("summary")
        report.field("result", "FAIL" if failed else "PASS")
        report.field("skipped stages", skipped)
        report.field("duration", f"{elapsed:.1f} ms")
        if runs:
            identity = runs[0].identity
            report.heading("compiled identity")
            report.field("source hash", identity.get("source_hash") or "-")
            report.field("jir hash", identity.get("jir_hash") or "-")
            report.field("llvm ir hash", identity.get("llvm_ir_hash") or "-")
            report.field("structural fingerprint", identity.get("structural_fingerprint") or "-")
            report.field("artifact hashes", len(identity.get("artifact_hashes") or []))
            if identity.get("semantic_result_hash"):
                report.field("fixture result hash", identity["semantic_result_hash"])
        report.note(variants.FIXTURE_NOTE)
        report.note(FORGE_DISCLAIMER)

    return compiler.EXIT_COMPILER_FAILURE if failed else 0
