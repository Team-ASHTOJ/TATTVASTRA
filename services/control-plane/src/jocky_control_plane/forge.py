"""Durable delivery of compiler-generated objects; bounded, explicitly synthetic fixture gates."""

import base64
import json
import math
import os
import re
import secrets
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import UUID

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from jocky_control_plane.config import Settings
from jocky_control_plane.models import (
    BuildRun,
    BuildState,
    Compilation,
    ScriptVersion,
    User,
    Variant,
)
from jocky_control_plane.objects import ObjectStore
from jocky_control_plane.security import digest, provenance, publish, sign

STAGES = (
    "SOURCE",
    "VALIDATE",
    "JIR",
    "DIVERSIFY",
    "LLVM",
    "BUILD",
    "TEST",
    "EQUIVALENCE",
    "MANIFEST",
    "READY",
)
DOMAIN = b"JOCKY:build:v1\n"


def initial_stages() -> list[dict[str, Any]]:
    return [
        {"name": name, "status": "PENDING", "duration_ms": None, "details": {}} for name in STAGES
    ]


def capabilities(settings: Settings) -> dict[str, Any]:
    return {
        "available": settings.compiler_path is not None and settings.compiler_path.is_file(),
        "targets": ["host"],
        "execution_modes": ["memory"],
        "max_variants": 8,
        "protected_literals": "IMPLEMENTED",
        "literal_key_configured": bool(
            re.fullmatch(r"[0-9a-fA-F]{64}", os.getenv("JOCKY_LITERAL_KEY_HEX", ""))
            and os.getenv("JOCKY_LITERAL_KEY_ID")
        ),
        "fixture_scope": (
            "Deterministic compiler fixture via ORC; "
            "not endpoint execution or universal equivalence"
        ),
    }


def start_run(db: Session, compilation: Compilation, count: int, seed: str | None) -> BuildRun:
    if compilation.status.value != "SUCCESS":
        raise HTTPException(409, "Choose a successful compilation")
    run = BuildRun(
        **provenance(compilation),
        compilation_id=compilation.id,
        variant_count=count,
        seed=seed or secrets.token_hex(8),
        stages=initial_stages(),
    )
    db.add(run)
    db.flush()
    return run


def checkpoint(
    db: Session,
    run: BuildRun,
    user: User,
    stage: str,
    status: str,
    duration: float | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    run.stages = [
        {
            **s,
            "status": status,
            "duration_ms": duration,
            "details": {
                "timing_scope": "compiler-stage sum across candidates"
                if stage in ("DIVERSIFY", "LLVM", "BUILD", "TEST")
                else "control-plane gate wall time; reused compilation",
                **(details or {}),
            },
            "updated_at": datetime.now(UTC).isoformat(),
        }
        if s["name"] == stage
        else s
        for s in run.stages
    ]
    publish(
        db,
        user,
        "build.stage",
        run.id,
        {"stage": stage, "status": status},
        simulation=run.simulation,
        simulation_label=run.simulation_label,
    )
    db.commit()


def execute(
    factory: sessionmaker[Session],
    settings: Settings,
    identifier: UUID,
    user_id: UUID,
    expected_hash: str | None = None,
) -> None:
    with factory() as db:
        run = db.get(BuildRun, identifier)
        user = db.get(User, user_id)
        if run is None or user is None or run.status != BuildState.QUEUED:
            return
        stage = "SOURCE"
        try:
            run.status = BuildState.RUNNING
            checkpoint(db, run, user, stage, "RUNNING")
            compilation = db.get(Compilation, run.compilation_id)
            if compilation is None:
                raise ValueError("Compilation no longer exists")
            version = db.get(ScriptVersion, compilation.script_version_id)
            started = perf_counter()
            if version is None or digest(version.source.encode()) != version.source_hash:
                raise ValueError("Stored source integrity failed")
            checkpoint(
                db,
                run,
                user,
                stage,
                "SUCCESS",
                (perf_counter() - started) * 1000,
                {"source_hash": version.source_hash, "script_version_id": str(version.id)},
            )
            stage = "VALIDATE"
            started = perf_counter()
            if compilation.status.value != "SUCCESS" or not compilation.outputs.get("check"):
                raise ValueError("Compilation validation is unavailable")
            checkpoint(
                db,
                run,
                user,
                stage,
                "SUCCESS",
                (perf_counter() - started) * 1000,
                {"reused_compilation": str(compilation.id)},
            )
            stage = "JIR"
            started = perf_counter()
            original = compilation.outputs.get("llvm", {}).get("manifest", {})
            jir_hash = original.get("jir_hash")
            plan = compilation.outputs.get("plan")
            if original.get("source_hash") != version.source_hash:
                raise ValueError("Compilation source identity does not match its stored version")
            if not jir_hash or not plan or not compilation.outputs.get("jir"):
                raise ValueError("Typed JIR or authorized plan is unavailable")
            plan_hash = digest(rfc8785.dumps(plan))
            checkpoint(
                db,
                run,
                user,
                stage,
                "SUCCESS",
                (perf_counter() - started) * 1000,
                {"jir_hash": jir_hash, "plan_hash": plan_hash, "plan": plan},
            )
            stage = "DIVERSIFY"
            checkpoint(
                db,
                run,
                user,
                stage,
                "RUNNING",
                details={
                    "engine": "jockyc variants",
                    "note": (
                        "Native lowering, object build and fixture gates run together; "
                        "completion metrics are reported by the compiler."
                    ),
                },
            )
            if settings.compiler_path is None or not settings.compiler_path.is_file():
                raise ValueError("Native compiler unavailable")
            # Scan a bounded deterministic seed range: coarse CFG fingerprints may repeat.
            candidates = min(run.variant_count * 8, 64)
            with tempfile.TemporaryDirectory(prefix="jocky-forge-") as temporary:
                directory = Path(temporary)
                source = directory / "source.jky"
                source.write_text(version.source, encoding="utf-8")
                result = subprocess.run(
                    [
                        str(settings.compiler_path.resolve()),
                        "variants",
                        str(source),
                        "--json",
                        "--target",
                        "host",
                        "--execution",
                        "native",
                        "--count",
                        str(candidates),
                        "--seed",
                        run.seed,
                        "--output",
                        str(directory / "variants"),
                    ],
                    capture_output=True,
                    check=False,
                    timeout=settings.compiler_timeout_seconds,
                )
                if result.returncode:
                    # Compiler diagnostics never echo environment keys or arbitrary stderr.
                    raise ValueError(
                        "Compiler variant/fixture gate failed; validate the program "
                        "and protected-literal key configuration"
                    )
                data = json.loads(result.stdout)
                samples = data.get("samples", [])
                if data.get("semantic_equivalence") is not True or len(samples) != candidates:
                    raise ValueError("Compiler did not return a complete verified fixture matrix")
                hashes: set[str] = set()
                fingerprints: set[str] = set()
                selected = []
                reference = samples[0]["manifest"].get("semantic_result_hash")
                if not reference or not re.fullmatch(r"[0-9a-f]{64}", reference):
                    raise ValueError("Fixture reference result is unavailable")
                for sample in samples:
                    manifest = sample["manifest"]
                    if (
                        manifest.get("source_hash") != version.source_hash
                        or manifest.get("jir_hash") != jir_hash
                    ):
                        raise ValueError("Variant source/JIR/capability identity mismatch")
                    if manifest.get("semantic_result_hash") != reference:
                        raise ValueError("Variant fixture result differs from reference")
                    artifact = manifest.get("artifact_hash")
                    fingerprint = manifest.get("structural_fingerprint")
                    if (
                        artifact
                        and fingerprint
                        and artifact not in hashes
                        and fingerprint not in fingerprints
                    ):
                        selected.append(sample)
                        hashes.add(artifact)
                        fingerprints.add(fingerprint)
                    if len(selected) == run.variant_count:
                        break
                if len(selected) != run.variant_count:
                    raise ValueError(
                        "Insufficient distinct structural templates in the bounded seed range; "
                        "use fewer variants or a richer forensic program"
                    )

                def measured(keys: tuple[str, ...]) -> float | None:
                    values = [
                        sample.get("profile", {}).get(key) for sample in samples for key in keys
                    ]
                    if any(
                        not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0
                        for v in values
                    ):
                        return None
                    return float(sum(values))

                checkpoint(
                    db,
                    run,
                    user,
                    stage,
                    "SUCCESS",
                    measured(("variant_ms",)),
                    {
                        "base_seed": run.seed,
                        "candidates_tested": candidates,
                        "selected_seeds": [s["manifest"]["variant_seed"] for s in selected],
                    },
                )
                stage = "LLVM"
                checkpoint(
                    db,
                    run,
                    user,
                    stage,
                    "SUCCESS",
                    measured(("llvm_generation_ms", "optimization_ms")),
                    {"identities": [s["manifest"]["llvm_ir_hash"] for s in selected]},
                )
                stage = "BUILD"
                store = ObjectStore(settings.object_root)
                variants = []
                for sample in selected:
                    path = Path(sample["artifact_path"]).resolve()
                    if not path.is_relative_to(directory.resolve()):
                        raise ValueError("Compiler artifact escaped its build directory")
                    content = path.read_bytes()
                    manifest = dict(sample["manifest"])
                    if digest(content) != manifest["artifact_hash"]:
                        raise ValueError("Actual object bytes do not match compiler hash")
                    manifest.update(
                        execution_mode=run.execution_mode,
                        artifact_format="llvm-object",
                        entry_symbol="jocky_entry_" + manifest["variant_id"][:16],
                        artifact_size_bytes=len(content),
                        compiler_profile=manifest.get("profile"),
                        profile=sample.get("profile", {}),
                        equivalence_status="NOT_TESTED",
                        plan_hash=plan_hash,
                    )
                    key = store.put(content)
                    variant = Variant(
                        **provenance(run),
                        compilation_id=compilation.id,
                        build_run_id=run.id,
                        seed=manifest["variant_seed"],
                        manifest=manifest,
                        content_hash=key,
                        storage_key=key,
                    )
                    db.add(variant)
                    db.flush()
                    variants.append(variant)
                run.target = str(selected[0]["manifest"]["target_triple"])
                checkpoint(
                    db,
                    run,
                    user,
                    stage,
                    "SUCCESS",
                    measured(("aot_ms",)),
                    {"variants": [str(v.id) for v in variants], "target": run.target},
                )
                stage = "TEST"
                run.results = {
                    "simulation": True,
                    "simulation_label": "DETERMINISTIC_COMPILER_FIXTURE",
                    "fixture": "JOCKY native fixture runtime v1",
                    "reference_seed": samples[0]["manifest"]["variant_seed"],
                    "reference_hash": reference,
                    "expected_hash": expected_hash or reference,
                    "candidate_count": candidates,
                    "plan_hash": plan_hash,
                    "scope": (
                        "Same source/JIR/declared plan, successful AOT emission "
                        "and ORC fixture results. "
                        "Not native endpoint or universal equivalence."
                    ),
                }
                checkpoint(
                    db,
                    run,
                    user,
                    stage,
                    "SUCCESS",
                    measured(("jit_compile_ms", "execution_ms")),
                    run.results,
                )
                stage = "EQUIVALENCE"
                started = perf_counter()
                if expected_hash is not None and expected_hash != reference:
                    run.results = {**run.results, "equivalence_status": "FAILED"}
                    raise ValueError("Fixture result does not match supplied expected result")
                run.results = {**run.results, "equivalence_status": "VERIFIED"}
                for variant in variants:
                    variant.manifest = {
                        **variant.manifest,
                        "equivalence_status": "VERIFIED",
                        "equivalence_scope": run.results["scope"],
                    }
                checkpoint(
                    db, run, user, stage, "SUCCESS", (perf_counter() - started) * 1000, run.results
                )
                stage = "MANIFEST"
                started = perf_counter()
                run.manifest = sign(
                    settings.signing_key_path,
                    {
                        "schema_version": "1.0.0",
                        "kind": "BuildManifest",
                        "build_run_id": str(run.id),
                        "organization_id": str(run.organization_id),
                        "compilation_id": str(compilation.id),
                        "script_version_id": str(version.id),
                        "source_hash": version.source_hash,
                        "jir_hash": jir_hash,
                        "plan_hash": plan_hash,
                        "base_seed": run.seed,
                        "target": run.target,
                        "execution_mode": run.execution_mode,
                        "fixture_result": run.results,
                        "variants": [{"id": str(v.id), **v.manifest} for v in variants],
                        "created_at": datetime.now(UTC).isoformat(),
                        "simulation": run.simulation,
                        "simulation_label": run.simulation_label,
                    },
                    DOMAIN,
                )
                checkpoint(
                    db,
                    run,
                    user,
                    stage,
                    "SUCCESS",
                    (perf_counter() - started) * 1000,
                    {
                        "signature": "Ed25519",
                        "manifest_route": f"/api/build-runs/{run.id}/manifest",
                    },
                )
                stage = "READY"
                run.status = BuildState.READY
                run.completed_at = datetime.now(UTC)
                checkpoint(
                    db,
                    run,
                    user,
                    stage,
                    "SUCCESS",
                    details={
                        "registry": "Published verified objects and signed provenance",
                        "variant_count": len(variants),
                    },
                )
        except (
            ValueError,
            KeyError,
            TypeError,
            OSError,
            subprocess.TimeoutExpired,
            HTTPException,
        ) as error:
            db.rollback()
            run = db.get(BuildRun, identifier)
            if run is None:
                return
            run.status = BuildState.FAILED
            run.error = error.detail if isinstance(error, HTTPException) else str(error)
            run.completed_at = datetime.now(UTC)
            run.stages = [
                {**s, "status": "SKIPPED"} if s["status"] == "PENDING" and s["name"] != stage else s
                for s in run.stages
            ]
            run.results = {
                **run.results,
                "equivalence_status": "FAILED" if stage == "EQUIVALENCE" else "NOT_TESTED",
            }
            checkpoint(db, run, user, stage, "FAILED", details={"error": run.error})


def verify(db: Session, run: BuildRun, settings: Settings) -> dict[str, Any]:
    signature_valid = False
    content_valid = False
    provenance_valid = False
    body = dict(run.manifest or {})
    signature = body.pop("signature", {})
    try:
        key = Ed25519PrivateKey.from_private_bytes(
            settings.signing_key_path.read_bytes()
        ).public_key()
        key.verify(
            base64.b64decode(signature["value_base64"], validate=True), DOMAIN + rfc8785.dumps(body)
        )
        signature_valid = True
        compilation = db.get(Compilation, run.compilation_id)
        version = db.get(ScriptVersion, compilation.script_version_id) if compilation else None
        provenance_valid = bool(
            compilation
            and version
            and compilation.organization_id == run.organization_id
            and version.organization_id == run.organization_id
            and body["source_hash"] == version.source_hash
            and body["build_run_id"] == str(run.id)
            and body["compilation_id"] == str(run.compilation_id)
            and body["organization_id"] == str(run.organization_id)
            and body["target"] == run.target
            and body["execution_mode"] == run.execution_mode
            and body["base_seed"] == run.seed
            and body["script_version_id"] == str(version.id)
            and body["plan_hash"] == digest(rfc8785.dumps(compilation.outputs.get("plan")))
            and body["jir_hash"] == compilation.outputs["llvm"]["manifest"]["jir_hash"]
            and body["source_hash"] == compilation.outputs["llvm"]["manifest"]["source_hash"]
            and body["fixture_result"] == run.results
            and body["fixture_result"].get("equivalence_status") == "VERIFIED"
            and len(body["variants"]) == run.variant_count
            and {UUID(v["id"]) for v in body["variants"]}
            == set(db.scalars(select(Variant.id).where(Variant.build_run_id == run.id)))
        )
        content_valid = bool(body["variants"])
        for item in body["variants"]:
            variant = db.get(Variant, UUID(item["id"]))
            if (
                variant is None
                or variant.build_run_id != run.id
                or variant.compilation_id != run.compilation_id
            ):
                content_valid = False
                continue
            provenance_valid &= (
                variant.organization_id == run.organization_id
                and variant.seed == item["variant_seed"]
                and variant.manifest == {k: v for k, v in item.items() if k != "id"}
            )
            content = ObjectStore(settings.object_root).get(variant.storage_key)
            content_valid &= (
                digest(content) == item["artifact_hash"] == variant.content_hash
                and len(content) == item["artifact_size_bytes"]
            )
    except (InvalidSignature, ValueError, KeyError, TypeError, OSError, HTTPException):
        content_valid = False
    return {
        "signature_valid": signature_valid,
        "provenance_valid": provenance_valid,
        "artifact_integrity_valid": content_valid,
        "valid": signature_valid and provenance_valid and content_valid,
    }
