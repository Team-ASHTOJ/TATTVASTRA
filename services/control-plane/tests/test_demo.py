"""Demo admission must not populate REAL workspaces or bypass operator policy."""

from jocky_contracts import control as contracts
from jocky_contracts.common import Mode
from jocky_control_plane.api import create_domain_router
from jocky_control_plane.models import Case, Compilation, State
from sqlalchemy import select
from test_distributed import PASSWORD, runtime

__all__ = ["runtime"]


def test_login_token_is_durable_before_response_teardown(runtime):
    factory, settings, client, organization, _ = runtime
    login = next(
        route.endpoint
        for route in create_domain_router(factory, settings).routes
        if getattr(route, "path", None) == "/api/auth/login"
    )
    with factory() as db:
        result = login(
            contracts.LoginRequest(
                organization_id=organization, username="admin", password=PASSWORD
            ),
            db,
        )
        # Closing an uncommitted request session must not discard an issued token.
        db.rollback()
    response = client.get(
        "/api/auth/me", headers={"Authorization": "Bearer " + result["access_token"]}
    )
    assert response.status_code == 200


def test_demo_is_explicit_and_compiler_failure_is_durable(runtime):
    factory, settings, client, _, _ = runtime
    assert client.post("/api/demo").status_code == 409
    with factory() as db:
        assert db.scalar(select(Case)) is None
    settings.mode = Mode.DEMO
    response = client.post("/api/demo")
    assert response.status_code == 503
    with factory() as db:
        compilation = db.scalar(select(Compilation))
        assert compilation is not None and compilation.status == State.FAILED
        assert compilation.simulation and compilation.outputs == {}
        assert db.scalar(select(Case)).description != "JOCKY_VIDEO_V1_READY"


def test_demo_rejects_viewer_and_unauthenticated_operator(runtime):
    _, settings, client, organization, _ = runtime
    settings.mode = Mode.DEMO
    assert client.post("/api/demo", headers={"Authorization": ""}).status_code == 401
    login = client.post(
        "/api/auth/login",
        json={
            "organization_id": str(organization),
            "username": "viewer",
            "password": PASSWORD,
        },
    ).json()
    assert (
        client.post(
            "/api/demo", headers={"Authorization": "Bearer " + login["access_token"]}
        ).status_code
        == 403
    )
