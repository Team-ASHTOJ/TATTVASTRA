"""Real compiler invocation and durable build representations."""

import json
import re
import secrets
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from jocky_contracts.compiler import CompileRequest
from sqlalchemy.orm import Session

from jocky_control_plane.compiler import (
    CompilerInvocationError,
    CompilerUnavailableError,
    invoke_compiler,
)
from jocky_control_plane.config import Settings
from jocky_control_plane.models import Compilation, ScriptVersion, State, User, Variant
from jocky_control_plane.objects import ObjectStore
from jocky_control_plane.security import digest, provenance, publish


def compile_version(
    db: Session, version: ScriptVersion, user: User, settings: Settings
) -> Compilation:
    compilation = Compilation(
        **provenance(version), script_version_id=version.id, status=State.RUNNING
    )
    db.add(compilation)
    db.flush()
    publish(
        db,
        user,
        "compiler.started",
        compilation.id,
        simulation=version.simulation,
        simulation_label=version.simulation_label,
    )
    db.commit()
    outputs: dict[str, Any] = {}
    try:
        for command in ("check", "tokens", "ast", "jir", "plan", "llvm"):
            request = CompileRequest.model_validate(
                {
                    "simulation": version.simulation,
                    "simulation_label": version.simulation_label,
                    "command": command,
                    "source": version.source,
                    "target": {"os": "linux", "arch": "x86_64"},
                    "execution_mode": "memory",
                }
            )
            outputs[command] = invoke_compiler(
                settings.compiler_path, request, settings.compiler_timeout_seconds
            )
            compilation.outputs = dict(outputs)
            publish(
                db,
                user,
                "compiler.stage",
                compilation.id,
                {"stage": command},
                simulation=version.simulation,
                simulation_label=version.simulation_label,
            )
            db.commit()
        compilation.status = State.SUCCESS
    except (CompilerInvocationError, CompilerUnavailableError) as error:
        compilation.status = State.FAILED
        compilation.error = str(error) or "JOCKY_COMPILER_PATH is unavailable"
    publish(
        db,
        user,
        "compiler.completed",
        compilation.id,
        {"status": compilation.status},
        simulation=version.simulation,
        simulation_label=version.simulation_label,
    )
    db.commit()
    return compilation


def build_variants(
    db: Session,
    compilation: Compilation,
    version: ScriptVersion,
    count: int,
    user: User,
    settings: Settings,
    *,
    execution_mode: str = "memory",
    seed_values: list[str] | None = None,
    target: str = "host",
    object_only: bool = False,
) -> list[Variant]:
    if compilation.status != State.SUCCESS:
        raise HTTPException(409, "Compilation must succeed before generating variants")
    if settings.compiler_path is None or not settings.compiler_path.is_file():
        raise HTTPException(503, "Native compiler unavailable")
    records = []
    store = ObjectStore(settings.object_root)
    # compile emits actual relocatable objects without invoking the simulated runtime.
    with tempfile.TemporaryDirectory(prefix="jocky-build-") as temporary:
        directory = Path(temporary)
        source = directory / "source.jky"
        source.write_text(version.source, encoding="utf-8", newline="\n")
        if seed_values is not None and (
            len(seed_values) != count
            or any(not re.fullmatch(r"[0-9a-f]{16}", seed) for seed in seed_values)
        ):
            raise ValueError("Expected one 64-bit hexadecimal seed per variant")
        for index in range(count):
            seed = seed_values[index] if seed_values is not None else secrets.token_hex(8)
            output = directory / "variant.o"
            try:
                result = subprocess.run(
                    [
                        str(settings.compiler_path.resolve()),
                        "llvm" if execution_mode == "memory" and not object_only else "compile",
                        str(source),
                        "--json",
                        "--target",
                        target,
                        "--execution",
                        "memory" if execution_mode == "memory" and not object_only else "native",
                        "--seed",
                        seed,
                        "--output",
                        str(output),
                    ],
                    capture_output=True,
                    check=False,
                    timeout=settings.compiler_timeout_seconds,
                )
                if result.returncode:
                    raise HTTPException(422, "Native object compilation failed")
                document = json.loads(result.stdout)
                manifest = document["manifest"]
                # The compiler emits relocatable LLVM objects through its native
                # compilation mode; the signed manifest still records the agent
                # execution mode selected by the hunt.
                manifest["execution_mode"] = execution_mode
                content = output.read_bytes()
                if execution_mode == "memory" and not object_only:
                    manifest["artifact_hash"] = digest(content)
                if digest(content) != manifest["artifact_hash"]:
                    raise HTTPException(422, "Compiler artifact does not match its manifest")
                manifest["entry_symbol"] = "jocky_entry_" + manifest["variant_id"][:16]
                manifest["artifact_format"] = (
                    "llvm-ir" if execution_mode == "memory" and not object_only else "llvm-object"
                )
                manifest["link_status"] = (
                    "ENVIRONMENT DEPENDENT"
                    if object_only
                    else "NOT REQUIRED"
                    if execution_mode == "memory"
                    else "LINKED"
                )
                if execution_mode == "native" and not object_only:
                    sdk = settings.worker_sdk_path
                    if sdk is None:
                        raise HTTPException(503, "Native execution worker SDK unavailable")
                    entry = manifest["entry_symbol"]
                    if not re.fullmatch(r"jocky_entry_[0-9a-f]{16}", entry):
                        raise HTTPException(422, "Invalid compiler entry symbol")
                    wrapper = directory / "entry.cpp"
                    wrapper.write_text(
                        '#include "jocky/worker.h"\n'
                        f'extern "C" uint32_t {entry}(jocky_context *);\n'
                        f"int main() {{ return jocky_worker_run(&{entry}); }}\n"
                    )
                    executable = directory / "variant-worker"
                    linked = subprocess.run(
                        [
                            "c++",
                            str(wrapper),
                            str(output),
                            "-I",
                            str(sdk / "include"),
                            str(sdk / "libjocky_worker_host.a"),
                            str(sdk / "libjocky_runtime.a"),
                            "-lcrypto",
                            "-o",
                            str(executable),
                        ],
                        capture_output=True,
                        check=False,
                        timeout=settings.compiler_timeout_seconds,
                    )
                    if linked.returncode:
                        raise HTTPException(503, "Native worker linking failed")
                    manifest["compiler_object_hash"] = manifest["artifact_hash"]
                    content = executable.read_bytes()
                    manifest["artifact_hash"] = digest(content)
                    manifest["artifact_format"] = "native-worker"
                # Retain the compiler's measured profile alongside persisted build provenance.
                if isinstance(document.get("profile"), dict):
                    manifest["profile"] = document["profile"]
                manifest["artifact_size_bytes"] = len(content)
                key = store.put(content)
            except (OSError, subprocess.TimeoutExpired, ValueError, KeyError) as error:
                raise HTTPException(
                    503, "Native build failed or returned invalid output"
                ) from error
            variant = Variant(
                **provenance(compilation),
                compilation_id=compilation.id,
                seed=seed,
                manifest=manifest,
                content_hash=key,
                storage_key=key,
            )
            db.add(variant)
            db.flush()
            publish(
                db,
                user,
                "variant.generated",
                variant.id,
                {"content_hash": key},
                simulation=variant.simulation,
                simulation_label=variant.simulation_label,
            )
            records.append(variant)
    return records
