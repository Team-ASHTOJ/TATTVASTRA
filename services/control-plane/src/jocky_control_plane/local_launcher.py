"""Internal, single-agent supervisor. Only fixed JOCKY lifecycle commands are accepted."""

import json
import os
import secrets
import signal
import subprocess
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, SecretStr


class Start(BaseModel):
    model_config = ConfigDict(extra="forbid")
    organization_id: UUID
    enrollment_id: UUID | None = None
    token: SecretStr | None = None
    ca: str | None = Field(default=None, max_length=16384)


class Supervisor:
    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = threading.RLock()
        self.process: subprocess.Popen[bytes] | None = None
        self.operation = (
            json.loads((root / "operation.json").read_text())
            if (root / "operation.json").exists()
            else {}
        )
        self.operation.update(state="STOPPED", error=None)
        self.agent = "/usr/local/bin/jocky-agent"
        self.worker = "/usr/local/bin/jocky-worker"

    def save(self) -> None:
        path = self.root / "operation.tmp"
        path.write_text(json.dumps(self.operation))
        path.chmod(0o600)
        path.replace(self.root / "operation.json")

    def status(self) -> dict[str, Any]:
        with self.lock:
            if (
                self.process
                and self.process.poll() is not None
                and self.operation["state"] == "WAITING_FOR_HEARTBEAT"
            ):
                self.operation.update(
                    state="FAILED", error="Agent process exited. Retry to reconnect."
                )
                self.save()
            binding = self.root / "remote.json"
            endpoint_id = (
                json.loads(binding.read_text())["endpoint_id"] if binding.exists() else None
            )
            return {
                **self.operation,
                "endpoint_id": endpoint_id,
                "needs_enrollment": not binding.exists(),
            }

    def start(self, material: Start) -> dict[str, Any]:
        with self.lock:
            status = self.status()
            owner = status.get("organization_id")
            if owner and owner != str(material.organization_id):
                raise HTTPException(409, "Local runtime belongs to another organization")
            if status["state"] in {"STARTING", "ENROLLING", "WAITING_FOR_HEARTBEAT"}:
                return status
            self.operation.update(
                organization_id=str(material.organization_id), state="STARTING", error=None
            )
            if material.enrollment_id:
                self.operation["enrollment_id"] = str(material.enrollment_id)
            self.save()
            threading.Thread(target=self.launch, args=(material,), daemon=True).start()
            return self.status()

    def run(self, args: list[str]) -> None:
        result = subprocess.run(
            [self.agent, "--state-dir", str(self.root), *args],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=40,
            check=False,
        )
        if result.returncode:
            detail = result.stderr.decode(errors="replace").lower()
            if "certificate" in detail or "tls" in detail:
                raise RuntimeError(
                    "TLS/CA validation failed. Check the control-plane CA and runtime certificates."
                )
            if "expired" in detail or "token" in detail:
                raise RuntimeError(
                    "Enrollment rejected or token expired. Retry to create a fresh enrollment."
                )
            raise RuntimeError(
                "Agent enrollment failed. Check that AgentControl is available, then retry."
            )

    def launch(self, material: Start) -> None:
        token_path = self.root / "enrollment.token"
        try:
            if not Path(self.agent).is_file():
                raise RuntimeError("Bundled agent binary is missing. Rebuild the local runtime.")
            if not Path(self.worker).is_file():
                raise RuntimeError("Bundled LLVM worker is missing. Rebuild the local runtime.")
            if not (self.root / "config.json").exists():
                self.run(["init"])
            if not (self.root / "remote.json").exists():
                if not material.token or not material.ca:
                    raise RuntimeError(
                        "Enrollment material is unavailable. Retry from Connect Endpoint."
                    )
                with self.lock:
                    self.operation["state"] = "ENROLLING"
                    self.save()
                # CP permits this retry only while the prior enrollment remains unconsumed.
                for name in ("transport.key", "transport.csr"):
                    (self.root / name).unlink(missing_ok=True)
                token_path.write_text(material.token.get_secret_value())
                token_path.chmod(0o600)
                ca = self.root / "enrollment-ca.pem"
                ca.write_text(material.ca)
                self.run(
                    [
                        "enroll",
                        "--enrollment-server",
                        "https://agent-control:50052",
                        "--server",
                        "https://agent-control:50051",
                        "--ca",
                        str(ca),
                        "--token-file",
                        str(token_path),
                        "--worker",
                        self.worker,
                    ]
                )
            with self.lock:
                self.process = subprocess.Popen(
                    [self.agent, "--state-dir", str(self.root), "connect"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                self.operation.update(
                    state="WAITING_FOR_HEARTBEAT", connected_at=datetime.now(UTC).isoformat()
                )
                self.save()
        except (OSError, RuntimeError, subprocess.TimeoutExpired):
            import sys

            error = sys.exception()
            with self.lock:
                self.operation.update(
                    state="FAILED",
                    error=str(error)
                    if isinstance(error, RuntimeError)
                    else "Runtime operation failed or timed out. Check AgentControl and retry.",
                )
                self.save()
        finally:
            token_path.unlink(missing_ok=True)

    def stop(self) -> dict[str, Any]:
        with self.lock:
            if self.operation["state"] in {"STARTING", "ENROLLING"}:
                raise HTTPException(409, "Wait for enrollment to finish before stopping")
            if self.process and self.process.poll() is None:
                os.killpg(self.process.pid, signal.SIGTERM)
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(self.process.pid, signal.SIGKILL)
                    self.process.wait(timeout=5)
            self.operation.update(state="STOPPED", error=None)
            self.save()
            return self.status()


def create_app(supervisor: Supervisor, token: str) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    def authenticate(authorization: Annotated[str | None, Header()] = None) -> None:
        if not token or not secrets.compare_digest(authorization or "", f"Bearer {token}"):
            raise HTTPException(401, "Internal runtime authentication required")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ready"}

    @app.get("/status", dependencies=[Depends(authenticate)])
    def status() -> dict[str, Any]:
        return supervisor.status()

    @app.post("/start", dependencies=[Depends(authenticate)])
    def start(material: Start) -> dict[str, Any]:
        return supervisor.start(material)

    @app.post("/stop", dependencies=[Depends(authenticate)])
    def stop() -> dict[str, Any]:
        return supervisor.stop()

    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        create_app(
            Supervisor(
                Path("/endpoint/local-agent-" + os.environ.get("JOCKY_LOCAL_AGENT_SLOT", "1"))
            ),
            os.environ["JOCKY_LOCAL_LAUNCHER_TOKEN"],
        ),
        host="0.0.0.0",
        port=8090,
        access_log=False,
    )
