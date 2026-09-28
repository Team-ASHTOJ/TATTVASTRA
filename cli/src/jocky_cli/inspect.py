"""Read-only local inspection: caps, budget, types, metrics, fingerprint.

Each command runs an existing jockyc subcommand with `--json` and prints fields
that subcommand already emits. jocky never parses `.jky` source, infers a type,
resolves a capability or hashes anything itself.
"""

from __future__ import annotations

from pathlib import Path

from . import compiler, report

SCHEMA_VERSION = "1.0.0"

#: jockyc's resolved budget keys, paired with the `budget { ... }` name they
#: come from (jockyc `configuration.cpp`).
BUDGET_FIELDS = (
    ("cpu_percent", "cpu"),
    ("memory_bytes", "memory"),
    ("io_bytes", "io"),
    ("duration_ms", "duration"),
)


def _open(source: str, name: str) -> None:
    print(f"jocky {name} — {source}")


def caps(argv: list[str]) -> int:
    """Declared capabilities, from the compiler's validated JIR."""
    source, _, present = compiler.source_and_options(argv, (), ("--json",), "caps")
    module = compiler.run_json(["jir", source, "--json"], Path.cwd(), source)

    capabilities = [str(name) for name in module.get("required_capabilities") or []]
    declared_by = [
        {
            "instruction_id": instruction.get("id"),
            "opcode": instruction.get("opcode"),
            "capabilities": list(instruction.get("required_capabilities") or []),
        }
        for instruction in module.get("instructions") or []
        if instruction.get("required_capabilities")
    ]

    if "--json" in present:
        report.emit_json(
            {
                "schema_version": SCHEMA_VERSION,
                "kind": "JockyCaps",
                "source": source,
                "command": "jir",
                "hunt": module.get("hunt"),
                "source_hash": module.get("source_hash"),
                "capabilities": capabilities,
                "declared_by": declared_by,
            }
        )
        return 0

    _open(source, "caps")
    report.field("hunt", module.get("hunt") or "-")
    report.field("source hash", module.get("source_hash") or "-")
    report.field("capabilities", ", ".join(capabilities) or "none declared")
    if declared_by:
        report.heading("declared by instruction")
        report.table(
            ("INSTRUCTION", "OPCODE", "CAPABILITY"),
            [
                (
                    str(entry["instruction_id"]),
                    str(entry["opcode"]),
                    ", ".join(entry["capabilities"]),
                )
                for entry in declared_by
            ],
            right=(0,),
        )
    return 0


def budget(argv: list[str]) -> int:
    """Effective budgets from JIR, labelled with what the AST declared.

    JIR carries the resolved integers the compiler will use; the AST carries the
    literal the program wrote (`20%`, `256MB`, `120s`). Both documents come from
    jockyc, so neither the value nor its declared spelling is jocky's own.
    """
    source, _, present = compiler.source_and_options(argv, (), ("--json",), "budget")
    cwd = Path.cwd()
    module = compiler.run_json(["jir", source, "--json"], cwd, source)
    program = compiler.run_json(["ast", source, "--json"], cwd, source)

    declared = program.get("budget") or {}
    values = module.get("budget") or {}
    entries = []
    for key, declared_name in BUDGET_FIELDS:
        option = declared.get(declared_name) or {}
        literal = (option.get("value") or {}).get("value")
        entries.append(
            {
                "field": key,
                "value": values.get(key),
                "origin": "declared" if declared_name in declared else "default",
                "declared_as": literal if declared_name in declared else None,
            }
        )

    if "--json" in present:
        report.emit_json(
            {
                "schema_version": SCHEMA_VERSION,
                "kind": "JockyBudget",
                "source": source,
                "command": "jir+ast",
                "hunt": module.get("hunt"),
                "source_hash": module.get("source_hash"),
                "budget": entries,
            }
        )
        return 0

    _open(source, "budget")
    report.field("hunt", module.get("hunt") or "-")
    report.field("source hash", module.get("source_hash") or "-")
    report.heading("resolved values (jockyc jir) and declared literals (jockyc ast)")
    report.table(
        ("FIELD", "VALUE", "ORIGIN", "DECLARED"),
        [
            (
                entry["field"],
                str(entry["value"]),
                entry["origin"],
                entry["declared_as"] or "-",
            )
            for entry in entries
        ],
    )
    report.note("`default` means the program omitted it and jockyc's conservative")
    report.note("default applies; the value is jockyc's own resolved integer.")
    return 0


def types(argv: list[str]) -> int:
    """The result schema the compiler's plan expects per JIR instruction."""
    source, _, present = compiler.source_and_options(argv, (), ("--json",), "types")
    plan = compiler.run_json(["plan", source, "--json"], Path.cwd(), source)

    schemas = [
        {
            "instruction_id": entry.get("instruction_id"),
            "type": (entry.get("result_type") or {}).get("name"),
            "nullable": bool((entry.get("result_type") or {}).get("nullable")),
        }
        for entry in plan.get("expected_result_schemas") or []
    ]

    if "--json" in present:
        report.emit_json(
            {
                "schema_version": SCHEMA_VERSION,
                "kind": "JockyTypes",
                "source": source,
                "command": "plan",
                "source_hash": plan.get("source_hash"),
                "jir_hash": plan.get("jir_hash"),
                "expected_result_schemas": schemas,
            }
        )
        return 0

    _open(source, "types")
    report.field("source hash", plan.get("source_hash") or "-")
    report.field("jir hash", plan.get("jir_hash") or "-")
    report.note("declared JIR result schema per instruction (jockyc plan)")
    report.heading(f"expected result schemas ({len(schemas)})")
    report.table(
        ("INSTRUCTION", "RESULT TYPE", "NULLABLE"),
        [
            (str(entry["instruction_id"]), str(entry["type"]), str(entry["nullable"]).lower())
            for entry in schemas
        ],
        right=(0,),
    )
    return 0


def _lowered(source: str, values: dict[str, str]) -> dict:
    """The manifest jockyc's `llvm` stage produced for this source."""
    argv = [
        "llvm",
        source,
        "--json",
        *compiler.target_option(values),
        *compiler.seed_option(values),
    ]
    return compiler.run_json(argv, Path.cwd(), source)


def metrics(argv: list[str]) -> int:
    """Structural lowering metrics from the compiler's variant manifest."""
    source, values, present = compiler.source_and_options(
        argv, ("--target", "--seed"), ("--json",), "metrics"
    )
    manifest = _lowered(source, values).get("manifest") or {}
    structural = manifest.get("structural_metrics") or {}

    payload = {
        "variant_id": manifest.get("variant_id"),
        "variant_seed": manifest.get("variant_seed"),
        "target_triple": manifest.get("target_triple"),
        "profile": manifest.get("profile"),
        "structural_fingerprint": manifest.get("structural_fingerprint"),
        "structural_metrics": structural,
    }

    if "--json" in present:
        report.emit_json(
            {
                "schema_version": SCHEMA_VERSION,
                "kind": "JockyMetrics",
                "source": source,
                "command": "llvm",
                "manifest": payload,
            }
        )
        return 0

    _open(source, "metrics")
    report.field("variant id", payload["variant_id"] or "-")
    report.field("seed", payload["variant_seed"] or "-")
    report.field("target triple", payload["target_triple"] or "-")
    report.field("profile", payload["profile"] or "-")
    report.heading("structural metrics (jockyc llvm manifest)")
    report.field("basic blocks", structural.get("llvm_basic_block_count", "-"))
    report.field("functions", structural.get("function_count", "-"))
    report.field("generated helpers", structural.get("generated_helper_count", "-"))
    report.field(
        "lowering strategies",
        structural.get("selected_lowering_strategy_ids", "-"),
    )
    report.field("structural fingerprint", payload["structural_fingerprint"] or "-")
    return 0


def fingerprint(argv: list[str]) -> int:
    """The compiler's own hashes and structural fingerprint for a source.

    Every value is emitted by jockyc. jocky hashes nothing, so this is a
    compiled identity rather than a hash of the source text.
    """
    source, values, present = compiler.source_and_options(
        argv, ("--target", "--seed"), ("--json",), "fingerprint"
    )
    manifest = _lowered(source, values).get("manifest") or {}

    payload = {
        "variant_id": manifest.get("variant_id"),
        "variant_seed": manifest.get("variant_seed"),
        "source_hash": manifest.get("source_hash"),
        "jir_hash": manifest.get("jir_hash"),
        "llvm_ir_hash": manifest.get("llvm_ir_hash"),
        "structural_fingerprint": manifest.get("structural_fingerprint"),
        "artifact_hash": manifest.get("artifact_hash"),
        "target_triple": manifest.get("target_triple"),
        "compiler_version": manifest.get("compiler_version"),
        "llvm_version": manifest.get("llvm_version"),
    }

    if "--json" in present:
        report.emit_json(
            {
                "schema_version": SCHEMA_VERSION,
                "kind": "JockyFingerprint",
                "source": source,
                "command": "llvm",
                "manifest": payload,
            }
        )
        return 0

    _open(source, "fingerprint")
    report.field("variant id", payload["variant_id"] or "-")
    report.field("seed", payload["variant_seed"] or "-")
    report.heading("compiler-emitted hashes")
    report.field("source hash", payload["source_hash"] or "-")
    report.field("jir hash", payload["jir_hash"] or "-")
    report.field("llvm ir hash", payload["llvm_ir_hash"] or "-")
    report.field("structural fingerprint", payload["structural_fingerprint"] or "-")
    report.field(
        "artifact hash",
        payload["artifact_hash"] or "not emitted by `llvm` — see `jocky forge`",
    )
    report.heading("provenance")
    report.field("target triple", payload["target_triple"] or "-")
    report.field(
        "compiler",
        f"{payload['compiler_version']} (LLVM {payload['llvm_version']})",
    )
    return 0
