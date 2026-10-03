"""Focused YARA finding derivation over persisted, protocol-valid observations."""

from jocky_control_plane.ingestion import ingest_observation
from jocky_control_plane.models import Endpoint, Finding, User
from sqlalchemy import select
from test_distributed import observation_payload, runtime, setup_job

__all__ = ["runtime"]


def test_matched_yara_observation_creates_one_evidence_linked_finding(runtime):
    factory, _, client, org_id, admin_id = runtime
    identifiers = setup_job(factory, org_id)
    with factory.begin() as db:
        endpoint = db.get(Endpoint, identifiers[3])
        user = db.get(User, admin_id)
        match = ingest_observation(
            db,
            endpoint,
            observation_payload(
                db,
                identifiers,
                "yara",
                {
                    "matched": True,
                    "rule": "approved_demo_marker",
                    "ruleset": "approved-demo",
                    "ruleset_sha256": "a" * 64,
                    "path": "/opt/jocky/evidence/match.txt",
                    "file_sha256": "b" * 64,
                    "size": 20,
                },
            ),
            user,
        )
        from jocky_control_plane.investigation import graph

        graph(db, identifiers[0], user, persist=True)
        rows = db.scalars(select(Finding).where(Finding.case_id == identifiers[0])).all()
        assert len(rows) == 1
        assert rows[0].title == "YARA signature match: approved_demo_marker"
        assert rows[0].severity == "MEDIUM"
        assert rows[0].observation_ids == [str(match.id)]
        assert rows[0].rule_key == f"yara-match:{match.id}"
    assert len(client.get("/api/findings", params={"case_id": str(identifiers[0])}).json()) == 1


def test_zero_match_and_simulated_match_do_not_create_real_yara_finding(runtime):
    factory, _, _, org_id, admin_id = runtime
    identifiers = setup_job(factory, org_id, simulation=True)
    with factory.begin() as db:
        endpoint = db.get(Endpoint, identifiers[3])
        user = db.get(User, admin_id)
        ingest_observation(
            db,
            endpoint,
            observation_payload(db, identifiers, "yara", {"matched": False, "files_scanned": 2}),
            user,
        )
        ingest_observation(
            db,
            endpoint,
            observation_payload(db, identifiers, "yara", {"matched": True, "rule": "fixture"}),
            user,
        )
        assert db.scalars(select(Finding).where(Finding.case_id == identifiers[0])).all() == []
