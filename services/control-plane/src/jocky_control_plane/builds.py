"""Real compiler invocation and durable build representations."""

import json
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
        for _ in range(count):
            seed = secrets.token_hex(8)
            output = directory / "variant.o"
            try:
                result = subprocess.run(
                    [
                        str(settings.compiler_path.resolve()),
                        "compile",
                        str(source),
                        "--json",
                        "--target",
                        "host",
                        "--execution",
                        "native",
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
                content = output.read_bytes()
                if digest(content) != manifest["artifact_hash"]:
                    raise HTTPException(422, "Compiler artifact does not match its manifest")
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
