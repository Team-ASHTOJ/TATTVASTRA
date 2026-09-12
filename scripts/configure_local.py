"""Generate local credentials without overwriting operator configuration or printing secrets."""

import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / ".env"
if target.exists():
    raise SystemExit(".env already exists; preserved existing operator configuration.")
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
}
fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as handle:
    handle.write("# Generated local development credentials; do not commit.\n")
    handle.writelines(f"{key}={value}\n" for key, value in values.items())
print("Created ignored .env with unique local credentials and mode 0600.")
