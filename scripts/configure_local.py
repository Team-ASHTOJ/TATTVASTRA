"""Generate local credentials without overwriting operator configuration or printing secrets."""

import os
import secrets
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / ".env"
if target.exists():
    existing = target.read_text(encoding="utf-8")
    if "--rotate-postgres" in sys.argv:
        # Explicit local credential recovery. No password appears in argv/logs.
        from urllib.parse import urlsplit

        import psycopg
        from psycopg import sql

        entries = dict(
            line.split("=", 1)
            for line in existing.splitlines()
            if "=" in line and not line.startswith("#")
        )
        address = urlsplit(entries["JOCKY_DATABASE_URL"].replace("+psycopg", ""))
        if address.hostname != "127.0.0.1" or address.port != 15432:
            raise SystemExit("Rotation is restricted to the local Compose PostgreSQL.")
        replacement = secrets.token_urlsafe(32)
        try:
            with psycopg.connect(entries["JOCKY_DATABASE_URL"].replace("+psycopg", "")) as db:
                db.execute(
                    sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                        sql.Identifier(entries["POSTGRES_USER"]), sql.Literal(replacement)
                    )
                )
        except psycopg.Error:
            raise SystemExit(
                "Local credential rotation failed; no configuration was changed."
            ) from None
        existing = existing.replace(entries["POSTGRES_PASSWORD"], replacement)
        target.write_text(existing, encoding="utf-8")
        print(
            "Rotated local PostgreSQL credential. "
            "Recreate Compose application services to reconnect."
        )
        raise SystemExit(0)
    if not any(line.startswith("JOCKY_BOOTSTRAP_PASSWORD=") for line in existing.splitlines()):
        with target.open("a", encoding="utf-8") as handle:
            handle.write("\nJOCKY_BOOTSTRAP_PASSWORD=" + secrets.token_urlsafe(32) + "\n")
        print("Added a unique bootstrap password; existing operator configuration was preserved.")
    else:
        print(".env already configured; preserved existing operator configuration.")
    raise SystemExit(0)
password = secrets.token_urlsafe(32)
values = {
    "JOCKY_ENVIRONMENT": "development",
    "JOCKY_MODE": "REAL",
    "JOCKY_TRANSPORT_MODE": "DIRECT",
    "JOCKY_API_URL": "http://127.0.0.1:8000",
    "JOCKY_DATABASE_URL": f"postgresql+psycopg://jocky:{password}@127.0.0.1:15432/jocky",
    "POSTGRES_USER": "jocky",
    "POSTGRES_DB": "jocky",
    "POSTGRES_PASSWORD": password,
    "MINIO_ROOT_USER": "jocky-local",
    "MINIO_ROOT_PASSWORD": secrets.token_urlsafe(32),
    "GRAFANA_ADMIN_PASSWORD": secrets.token_urlsafe(32),
    "JOCKY_BOOTSTRAP_PASSWORD": secrets.token_urlsafe(32),
}
fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as handle:
    handle.write("# Generated local development credentials; do not commit.\n")
    handle.writelines(f"{key}={value}\n" for key, value in values.items())
print("Created ignored .env with unique local credentials and mode 0600.")
