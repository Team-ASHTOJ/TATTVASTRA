"""Compose API startup: migrations and explicit administrator provisioning."""

import subprocess
import sys
import threading

if __name__ == "__main__":
    subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "/app/services/control-plane/alembic.ini",
            "upgrade",
            "head",
        ],
        check=True,
    )
    subprocess.run([sys.executable, "-m", "jocky_control_plane.cli", "init"], check=True)
    import uvicorn

    from jocky_control_plane.config import Settings

    settings = Settings()
    if settings.agent_public_host:
        # An external endpoint is handed this address over a TLS client that
        # trusts only the control-plane CA, so it is served with the same
        # certificate the agent listeners already use. Verification is never
        # relaxed and this listener is never plaintext.
        for path in (settings.tls_cert_path, settings.tls_key_path):
            if not path.is_file():
                raise RuntimeError(f"External endpoint TLS requires {path}")
        threading.Thread(
            target=uvicorn.run,
            args=("jocky_control_plane.app:app",),
            kwargs={
                "host": "0.0.0.0",
                "port": settings.agent_api_port,
                "access_log": False,
                "ssl_certfile": str(settings.tls_cert_path),
                "ssl_keyfile": str(settings.tls_key_path),
            },
            daemon=True,
        ).start()

    uvicorn.run("jocky_control_plane.app:app", host="0.0.0.0", port=8000, access_log=False)
