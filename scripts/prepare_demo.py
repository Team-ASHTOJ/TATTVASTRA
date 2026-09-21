"""Prepare and verify the isolated video stack without printing credentials."""

import argparse
import json
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
READY = "JOCKY_VIDEO_V2_READY"
COMPOSE = [
    "docker",
    "compose",
    "--env-file",
    str(ROOT / ".env"),
    "-f",
    str(ROOT / "infra/docker/prototype.compose.yaml"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check the existing prepared scenario")
    args = parser.parse_args()
    if args.check:
        with urllib.request.urlopen("http://127.0.0.1:13000", timeout=15) as response:
            assert response.status == 200, "Dashboard unavailable"
        print("PASS dashboard")
        with urllib.request.urlopen("http://127.0.0.1:18080/health/live", timeout=15) as response:
            assert response.status == 200, "Control plane unavailable"
        print("PASS control plane")
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
    if args.check:
        cases = request("cases")
        scenario = next(
            (row for row in cases if row["description"] == READY and row["simulation"]),
            None,
        )
        assert scenario, "Run make demo-prepare first"
        prepared = {"case_id": scenario["id"]}
    else:
        prepared = request("demo", {})
        assert prepared == request("demo", {}), "Prepared scenario must be reusable"
    case_id = prepared["case_id"]
    hunts = [row for row in request("hunts") if row["case_id"] == case_id]
    assert len(hunts) == 1 and hunts[0]["status"] == "PARTIAL"
    jobs = request(f"hunts/{hunts[0]['id']}/jobs")
    assert sorted(row["status"] for row in jobs) == ["FAILED", "SUCCESS", "SUCCESS"]
    assert all(row["simulation"] for row in jobs)
    print("PASS demo hunt/scenario availability")
    fixture = json.loads(
        (ROOT / "services/control-plane/src/jocky_control_plane/data/demo.json").read_text()
    )
    observations = request(f"observations?case_id={case_id}")
    expected_observations = sum(len(row["observations"]) for row in fixture["endpoints"])
    assert len(observations) == expected_observations, (
        f"Expected {expected_observations} demo observations, got {len(observations)}"
    )
    assert all(row["simulation"] for row in observations), (
        "Demo observations must all be explicitly simulated"
    )
    assert all(row["document"]["source_time"] == fixture["timestamp"] for row in observations), (
        "Prepared observations do not use the current fixture source time"
    )
    job_by_id = {row["id"]: row for row in jobs}
    for observation in observations:
        job = job_by_id[observation["job_id"]]
        assert observation["endpoint_id"] == job["endpoint_id"]
        assert observation["document"]["variant_id"] == job["variant_id"]
    print("PASS demo fixture service (embedded in control plane)")
    compilation = request(f"compilations/{hunts[0]['compilation_id']}")
    assert compilation["status"] == "SUCCESS"
    payload = {
        "schema_version": "1.0.0",
        "simulation": False,
        "command": "check",
        "source": fixture["source"],
        "target": {"os": "linux", "arch": "x86_64"},
        "execution_mode": "native",
        "variant_seed": fixture["seeds"][0],
        "profile": "balanced",
    }
    compiler_request = urllib.request.Request(
        "http://127.0.0.1:18080/api/v1/compilations",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + token},
    )
    with urllib.request.urlopen(compiler_request, timeout=180) as response:
        assert response.status == 200
    print("PASS compiler endpoint")
    variants = [
        row for row in request("variants") if row["compilation_id"] == hunts[0]["compilation_id"]
    ]
    assert len({row["content_hash"] for row in variants}) == 3
    findings = request(f"findings?case_id={case_id}")
    assert len(findings) == 1 and findings[0]["simulation"]
    graph = request(f"graph?case_id={case_id}")
    assert len(graph["nodes"]) > 10 and len(graph["edges"]) > 8
    observation_ids = {row["id"] for row in observations}
    assert set(findings[0]["observation_ids"]) <= observation_ids
    assert any(row["id"] == "finding:" + findings[0]["id"] for row in graph["nodes"])
    timeline = request(f"timeline?case_id={case_id}")
    assert {row["observation_id"] for row in timeline} == observation_ids
    assert all(row["time_basis"] == "source" for row in timeline)
    artifacts = [row for row in request("artifacts") if row["case_id"] == case_id]
    assert len(artifacts) == 3, "Expected three persisted evidence objects"
    for artifact in artifacts:
        assert request(f"artifacts/{artifact['id']}/verify", {})["integrity_valid"]
    for job in jobs:
        manifests = request(f"manifests?job_id={job['id']}")
        assert len(manifests) == 1, "Expected one signed manifest per job"
        for manifest in manifests:
            assert request(f"manifests/{manifest['id']}/verify", {})["integrity_valid"]
    assert request("audit/verify")["integrity_valid"]
    print("PASS evidence verification")
    print("Verified: real compilation, 3 distinct artifacts, 3 simulated jobs, partial success,")
    print(
        "Derived finding/graph, stored-byte hashes, signed manifests, audit chain, repeat loading."
    )
    print(f"Open http://localhost:13000/judge - organization: {organization}; username: admin")
    print("Password: use JOCKY_BOOTSTRAP_PASSWORD from your local .env (not printed).")


if __name__ == "__main__":
    try:
        main()
    except (
        AssertionError,
        OSError,
        subprocess.CalledProcessError,
        StopIteration,
        KeyError,
    ) as error:
        raise SystemExit(f"FAIL prototype dependency: {error}") from None
