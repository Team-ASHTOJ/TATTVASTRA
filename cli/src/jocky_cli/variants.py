"""Variant commands: diverge, diff, equivalence.

All three consume jockyc's own deterministic variant generation. jocky never
re-seeds, re-lowers, re-hashes or text-diffs LLVM IR; it reports the fields
jockyc emitted for each variant.
"""

from __future__ import annotations

import sys
from pathlib import Path

from . import compiler, options, report
from .options import UsageError

DEFAULT_COUNT = 3

#: jockyc rejects non-host targets for variant generation and fixture
#: execution (`validate_target_mode`, E263), so the composed commands refuse
#: plainly rather than forwarding a request that is bound to fail.
CROSS_TARGET_REFUSAL = (
    "jockyc requires the host target for variant generation and fixture "
    "execution (E263); use `jocky forge` or `jocky pipeline` for a cross target"
)

FIXTURE_NOTE = (
    "SIMULATED deterministic compiler fixture — local ORC execution, "
    "not endpoint evidence"
)

_HEX_DIGITS = set("0123456789abcdef")


def display(value: object) -> str:
    """A manifest value, with 64-character hashes shortened for the table."""
    if value is None:
        return "-"
    text = str(value)
    if len(text) == 64 and set(text) <= _HEX_DIGITS:
        return text[:16]
    return text


def variant_set(
    source: str,
    count: int,
    seed: int | None = None,
    output: Path | None = None,
) -> tuple[dict, Path]:
    """Run jockyc's `variants` and return its document and artifact directory."""
    directory = output or Path.cwd() / f"{Path(source).stem}.variants"
    argv = [
        "variants",
        source,
        "--count",
        str(count),
        "--output",
        str(directory),
        "--json",
    ]
    if seed is not None:
        argv += compiler.seed_arguments(seed)
    return compiler.run_json(argv, Path.cwd(), source), directory


def _require_host(values: dict[str, str], command: str) -> None:
    target = values.get("--target", "host")
    if target != "host":
        raise UsageError(f"{command} --target {target}: {CROSS_TARGET_REFUSAL}")


def variant_manifests(document: dict) -> list[dict]:
    """Every variant manifest jockyc's `variants` document carries."""
    return [sample.get("manifest") or {} for sample in document.get("samples") or []]


def _variant_row(manifest: dict) -> tuple[str, ...]:
    """The columns `diverge` prints for one variant."""
    structural = manifest.get("structural_metrics") or {}
    return (
        display(manifest.get("variant_seed")),
        display(manifest.get("variant_id")),
        display(structural.get("llvm_basic_block_count")),
        display(structural.get("function_count")),
        display(structural.get("generated_helper_count")),
        display(manifest.get("artifact_hash")),
        display(manifest.get("llvm_ir_hash")),
        display(manifest.get("structural_fingerprint")),
    )


def distinct(manifests: list[dict], key: str) -> int:
    """How many distinct values a manifest field takes across a variant set."""
    return len({manifest.get(key) for manifest in manifests if manifest.get(key)})


def _selected(values: dict[str, str]) -> tuple[int, int | None, Path | None]:
    count = options.count(values["--count"]) if "--count" in values else DEFAULT_COUNT
    seed = options.parse_seed(values["--seed"]) if "--seed" in values else None
    output = Path(values["--output"]).resolve() if "--output" in values else None
    return count, seed, output


def diverge(argv: list[str]) -> int:
    """Generate `--count` variants and show what proves they differ."""
    source, values, present = compiler.source_and_options(
        argv,
        ("--count", "--seed", "--target", "--output"),
        ("--json",),
        "diverge",
    )
    _require_host(values, "diverge")
    count, seed, output = _selected(values)

    document, directory = variant_set(source, count, seed, output)
    manifests = variant_manifests(document)
    if not manifests:
        print("jocky: jockyc reported no variants.", file=sys.stderr)
        return compiler.EXIT_COMPILER_FAILURE

    distinct_ids = distinct(manifests, "variant_id")
    distinct_artifacts = distinct(manifests, "artifact_hash")
    distinct_fingerprints = distinct(manifests, "structural_fingerprint")
    equivalence = bool(document.get("semantic_equivalence"))

    if "--json" in present:
        report.emit_json(
            {
                "schema_version": "1.0.0",
                "kind": "JockyDiverge",
                "source": source,
                "command": "variants",
                "count": len(manifests),
                "output": str(directory),
                "distinct": {
                    "variant_ids": distinct_ids,
                    "artifact_hashes": distinct_artifacts,
                    "structural_fingerprints": distinct_fingerprints,
                },
                "semantic_equivalence": equivalence,
                "simulation": bool(document.get("simulation")),
                "simulation_label": document.get("simulation_label"),
                "variants": manifests,
            }
        )
    else:
        print(f"jocky diverge — {source}")
        report.field("count", len(manifests))
        report.field("output", str(directory))
        report.heading("variants (jockyc variants)")
        report.table(
            (
                "SEED",
                "VARIANT",
                "BLOCKS",
                "FUNCS",
                "HELPERS",
                "ARTIFACT",
                "LLVM IR",
                "STRUCTURAL",
            ),
            [_variant_row(manifest) for manifest in manifests],
            right=(2, 3, 4),
        )
        report.heading("distinctness")
        report.field("distinct variant ids", f"{distinct_ids}/{len(manifests)}")
        report.field("distinct artifacts", f"{distinct_artifacts}/{len(manifests)}")
        report.field("distinct fingerprints", f"{distinct_fingerprints}/{len(manifests)}")
        report.field(
            "semantic equivalence",
            "PASS (fixture result hash identical)" if equivalence else "FAIL",
        )
        report.field("runtime", FIXTURE_NOTE)

    if distinct_artifacts < len(manifests):
        print(
            f"jocky: {distinct_artifacts} distinct artifact hashes for "
            f"{len(manifests)} variants — the requested variants are not distinct.",
            file=sys.stderr,
        )
        return compiler.EXIT_COMPILER_FAILURE
    return 0


def equivalence(argv: list[str]) -> int:
    """Report the compiler's own fixture semantic-equivalence evidence."""
    source, values, present = compiler.source_and_options(
        argv,
        ("--count", "--seed", "--target", "--output"),
        ("--json",),
        "equivalence",
    )
    _require_host(values, "equivalence")
    count, seed, output = _selected(values)

    document, directory = variant_set(source, count, seed, output)
    manifests = variant_manifests(document)
    results = [manifest.get("semantic_result_hash") for manifest in manifests]
    equivalence = bool(document.get("semantic_equivalence"))
    shared = bool(results) and len({result for result in results}) == 1

    if "--json" in present:
        report.emit_json(
            {
                "schema_version": "1.0.0",
                "kind": "JockyEquivalence",
                "source": source,
                "command": "variants",
                "count": len(manifests),
                "output": str(directory),
                "semantic_equivalence": equivalence,
                "shared_result_hash": results[0] if shared else None,
                "simulation": bool(document.get("simulation")),
                "simulation_label": document.get("simulation_label"),
                "results": [
                    {
                        "variant_id": manifest.get("variant_id"),
                        "variant_seed": manifest.get("variant_seed"),
                        "semantic_result_hash": manifest.get("semantic_result_hash"),
                    }
                    for manifest in manifests
                ],
            }
        )
    else:
        print(f"jocky equivalence — {source}")
        report.field("variants", len(manifests))
        report.field("semantic equivalence", "PASS" if equivalence else "FAIL")
        report.field(
            "result hash", results[0] if shared else "not shared across variants"
        )
        report.field("evidence source", "jockyc variants fixture runtime")
        report.heading("per-variant fixture result")
        report.table(
            ("VARIANT", "SEED", "RESULT SHA-256"),
            [
                (
                    display(manifest.get("variant_id")),
                    display(manifest.get("variant_seed")),
                    str(manifest.get("semantic_result_hash")),
                )
                for manifest in manifests
            ],
        )
        report.field("runtime", FIXTURE_NOTE)

    return 0 if equivalence and shared else compiler.EXIT_COMPILER_FAILURE


#: Manifest fields compared by `diff`, in the order they are printed.
IDENTITY_FIELDS = (
    ("variant id", "variant_id"),
    ("source hash", "source_hash"),
    ("jir hash", "jir_hash"),
    ("llvm ir hash", "llvm_ir_hash"),
    ("structural fingerprint", "structural_fingerprint"),
    ("target triple", "target_triple"),
)

METRIC_FIELDS = (
    ("basic blocks", "llvm_basic_block_count"),
    ("functions", "function_count"),
    ("generated helpers", "generated_helper_count"),
    ("lowering strategies", "selected_lowering_strategy_ids"),
)


def _verdict(first: dict, second: dict, seed_a: int, seed_b: int) -> str:
    if seed_a == seed_b:
        return "IDENTICAL SEEDS — pass two different seeds to compare"
    ir_differs = first.get("llvm_ir_hash") != second.get("llvm_ir_hash")
    first_fingerprint = first.get("structural_fingerprint")
    second_fingerprint = second.get("structural_fingerprint")
    if ir_differs and first_fingerprint != second_fingerprint:
        return "STRUCTURALLY DISTINCT (LLVM IR hash and structural fingerprint differ)"
    if not ir_differs:
        return "IDENTICAL LOWERING — these seeds select the same lowering"
    return "PARTIALLY DIFFERENT — inspect the fields above"


def diff(argv: list[str]) -> int:
    """Compare two deterministic seed choices structurally."""
    source, values, present = compiler.source_and_options(
        argv, ("--seed-a", "--seed-b", "--target"), ("--json",), "diff"
    )
    if "--seed-a" not in values or "--seed-b" not in values:
        raise UsageError("diff requires --seed-a <n> and --seed-b <n>")
    seed_a = options.parse_seed(values["--seed-a"], "--seed-a")
    seed_b = options.parse_seed(values["--seed-b"], "--seed-b")

    target = compiler.target_option(values)
    cwd = Path.cwd()
    first_argv = ["llvm", source, "--json", *compiler.seed_arguments(seed_a), *target]
    second_argv = ["llvm", source, "--json", *compiler.seed_arguments(seed_b), *target]
    first = compiler.run_json(first_argv, cwd, source).get("manifest") or {}
    second = compiler.run_json(second_argv, cwd, source).get("manifest") or {}
    verdict = _verdict(first, second, seed_a, seed_b)

    first_metrics = first.get("structural_metrics") or {}
    second_metrics = second.get("structural_metrics") or {}

    if "--json" in present:
        report.emit_json(
            {
                "schema_version": "1.0.0",
                "kind": "JockyDiff",
                "source": source,
                "command": "llvm",
                "seed_a": compiler.seed_text(seed_a),
                "seed_b": compiler.seed_text(seed_b),
                "verdict": verdict,
                "identity": [
                    {
                        "field": label,
                        "seed_a": first.get(key),
                        "seed_b": second.get(key),
                        "equal": first.get(key) == second.get(key),
                    }
                    for label, key in IDENTITY_FIELDS
                ],
                "structural_metrics": [
                    {
                        "metric": label,
                        "seed_a": first_metrics.get(key),
                        "seed_b": second_metrics.get(key),
                    }
                    for label, key in METRIC_FIELDS
                ],
            }
        )
        return 0

    print(f"jocky diff — {source}")
    report.field("target", values.get("--target", "host"))
    report.field("seed a", compiler.seed_text(seed_a))
    report.field("seed b", compiler.seed_text(seed_b))

    report.heading("identity (jockyc llvm manifests)")
    report.table(
        ("FIELD", "SEED A", "SEED B", "VERDICT"),
        [
            (
                label,
                display(first.get(key)),
                display(second.get(key)),
                "same" if first.get(key) == second.get(key) else "differs",
            )
            for label, key in IDENTITY_FIELDS
        ],
    )

    report.heading("structural metrics")
    report.table(
        ("METRIC", "SEED A", "SEED B"),
        [
            (label, display(first_metrics.get(key)), display(second_metrics.get(key)))
            for label, key in METRIC_FIELDS
        ],
    )

    report.heading(f"VERDICT  {verdict}")
    report.note("compared from jockyc manifest fields; LLVM IR text is not diffed")
    report.note("structural comparison only — no semantic-equivalence claim")
    return 0
