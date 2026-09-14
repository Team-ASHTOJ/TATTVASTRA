"""Compose API startup: migrations and explicit administrator provisioning."""

import subprocess
import sys

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

    uvicorn.run("jocky_control_plane.app:app", host="0.0.0.0", port=8000, access_log=False)
