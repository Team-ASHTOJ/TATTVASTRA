"""Run isolated-schema integration tests against the local Compose PostgreSQL."""

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

root = Path(__file__).resolve().parents[1]
environment = os.environ.copy()
if not environment.get("JOCKY_TEST_DATABASE_URL"):
    entries = dict(
        line.split("=", 1)
        for line in (root / ".env").read_text().splitlines()
        if "=" in line and not line.startswith("#")
    )
    environment["JOCKY_TEST_DATABASE_URL"] = (
        "postgresql+psycopg://jocky:"
        + quote(entries["POSTGRES_PASSWORD"], safe="")
        + "@127.0.0.1:15432/jocky"
    )
raise SystemExit(
    subprocess.call(
        [
            sys.executable,
            "-m",
            "pytest",
            "services/control-plane/tests/test_distributed.py",
            "services/control-plane/tests/test_phase4.py",
            "--basetemp=.cache/pytest-postgres",
            "-q",
            "--tb=short",
            *sys.argv[1:],
        ],
        cwd=root,
        env=environment,
    )
)
