"""Prepare and verify the isolated video stack without printing credentials."""

import json
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = [
    "docker",
    "compose",
    "--env-file",
    str(ROOT / ".env"),
    "-f",
    str(ROOT / "infra/docker/prototype.compose.yaml"),
]


def main() -> None:
    entries = dict(
        line.split("=", 1)
        for line in (ROOT / ".env").read_text().splitlines()
        if "=" in line and not line.startswith("#")
    )
    result = subprocess.run(
        [
            *COMPOSE,
            "exec",
            "-T",
            "control-plane",
            "/app/.venv/bin/python",
            "-m",
            "jocky_control_plane.cli",
            "init",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    match = re.search(r"Organization: ([0-9a-f-]+)", result.stdout)
    if not match:
        raise SystemExit("Could not discover the demo organization")
    organization = match[1]
    token = ""

    def request(path: str, body: object = None) -> object:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(
            "http://127.0.0.1:18080/api/" + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise SystemExit(
                f"Demo verification failed: {path} HTTP {error.code}; inspect service logs"
            ) from None

    login = request(
        "auth/login",
        {
            "organization_id": organization,
            "username": "admin",
            "password": entries["JOCKY_BOOTSTRAP_PASSWORD"],
        },
    )
    token = login["access_token"]
    prepared = request("demo", {})
    assert prepared == request("demo", {}), "Prepared scenario must be reusable"
    case_id = prepared["case_id"]
    hunts = [row for row in request("hunts") if row["case_id"] == case_id]
    assert len(hunts) == 1 and hunts[0]["status"] == "PARTIAL"
    jobs = request(f"hunts/{hunts[0]['id']}/jobs")
    assert sorted(row["status"] for row in jobs) == ["FAILED", "SUCCESS", "SUCCESS"]
    assert all(row["simulation"] for row in jobs)
    variants = [
        row for row in request("variants") if row["compilation_id"] == hunts[0]["compilation_id"]
    ]
    assert len({row["content_hash"] for row in variants}) == 3
    findings = request(f"findings?case_id={case_id}")
    assert len(findings) == 1 and findings[0]["simulation"]
    graph = request(f"graph?case_id={case_id}")
    assert len(graph["nodes"]) > 10 and len(graph["edges"]) > 8
    for artifact in request("artifacts"):
        if artifact["case_id"] == case_id:
            assert request(f"artifacts/{artifact['id']}/verify", {})["integrity_valid"]
    for job in jobs:
        for manifest in request(f"manifests?job_id={job['id']}"):
            assert request(f"manifests/{manifest['id']}/verify", {})["integrity_valid"]
    assert request("audit/verify")["integrity_valid"]
    print("Verified: real compilation, 3 distinct artifacts, 3 simulated jobs, partial success,")
    print(
        "Derived finding/graph, stored-byte hashes, signed manifests, audit chain, repeat loading."
    )
    print(f"Open http://localhost:13000/judge — organization: {organization}; username: admin")
    print("Password: use JOCKY_BOOTSTRAP_PASSWORD from your local .env (not printed).")


if __name__ == "__main__":
    main()
