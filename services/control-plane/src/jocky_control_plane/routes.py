from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from jocky_contracts.common import Problem
from jocky_contracts.compiler import CompileRequest
from jocky_contracts.evidence import IntegrityResult, Observation, verify_observation
from jocky_contracts.status import EndpointList, Health, PlatformStatus

from jocky_control_plane import __version__
from jocky_control_plane.compiler import (
    CompilerInvocationError,
    CompilerUnavailableError,
    invoke_compiler,
)
from jocky_control_plane.config import Settings
from jocky_control_plane.coverage import load_coverage
from jocky_control_plane.models import Role
from jocky_control_plane.security import session_user


def create_router(settings: Settings) -> APIRouter:
    router = APIRouter()

    @router.get("/health/live", response_model=Health, tags=["health"])
    def live() -> Health:
        return Health(
            simulation=False, status="alive", service="control-plane", version=__version__
        )

    @router.get("/health/ready", response_model=Health, responses={503: {"model": Health}})
    def ready(request: Request) -> JSONResponse:
        if settings.database_url:
            from sqlalchemy import select
            from sqlalchemy.exc import SQLAlchemyError

            from jocky_control_plane.models import Organization

            try:
                with request.app.state.session_factory() as db:
                    initialized = db.scalar(select(Organization.id).limit(1)) is not None
                if initialized and settings.signing_key_path.is_file():
                    health = Health(
                        simulation=False,
                        status="ready",
                        service="control-plane",
                        version=__version__,
                    )
                    return JSONResponse(content=health.model_dump(mode="json"))
            except SQLAlchemyError:
                pass
        health = Health(
            simulation=False,
            status="not_ready",
            service="control-plane",
            version=__version__,
            reason=(
                "Authenticated dispatch and storage are unavailable. "
                "Compiler requests require JOCKY_COMPILER_PATH."
            ),
        )
        return JSONResponse(status_code=503, content=health.model_dump(mode="json"))

    @router.get("/api/v1/status", response_model=PlatformStatus, tags=["platform"])
    def status() -> PlatformStatus:
        return PlatformStatus(
            simulation=False,
            version=__version__,
            tagline="One Language. Every Endpoint. No Noise.",
            phase="P1–P6 implemented slices",
            mode=settings.mode,
            operational=False,
            observed_at=datetime.now(UTC),
            capabilities=load_coverage(),
        )

    @router.get("/api/v1/endpoints", response_model=EndpointList, tags=["endpoints"])
    def endpoints() -> EndpointList:
        return EndpointList(
            simulation=False,
            reason=(
                "Endpoint enrollment and persistence are not implemented; no inventory is reported."
            ),
        )

    @router.post(
        "/api/v1/compilations",
        responses={422: {"model": Problem}, 501: {"model": Problem}},
        tags=["build-forge"],
    )
    def compile_source(payload: CompileRequest, request: Request) -> JSONResponse:
        if settings.database_url:
            with request.app.state.session_factory() as db:
                user = session_user(db, request.headers.get("authorization"))
                if user.role not in {Role.ADMIN, Role.ANALYST}:
                    raise HTTPException(403, "ANALYST or ADMIN role required")
        try:
            output = invoke_compiler(
                settings.compiler_path, payload, settings.compiler_timeout_seconds
            )
            return JSONResponse(content=output)
        except CompilerUnavailableError:
            problem = Problem(
                simulation=payload.simulation,
                simulation_label=payload.simulation_label,
                code="JOCKY_E_COMPILER_UNAVAILABLE",
                detail=(
                    "Compiler service is not configured. Set JOCKY_COMPILER_PATH to the "
                    "jockyc executable, restart the API, and retry."
                ),
                status=501,
                request_id=request.state.request_id,
            )
            return JSONResponse(status_code=501, content=problem.model_dump(mode="json"))
        except CompilerInvocationError as error:
            if error.output is not None:
                return JSONResponse(status_code=422, content=error.output)
            problem = Problem(
                simulation=payload.simulation,
                simulation_label=payload.simulation_label,
                code="JOCKY_E_COMPILER_INVOCATION",
                detail=str(error),
                status=422,
                request_id=request.state.request_id,
            )
            return JSONResponse(status_code=422, content=problem.model_dump(mode="json"))

    @router.post(
        "/api/v1/evidence/verify-observation",
        response_model=IntegrityResult,
        tags=["evidence"],
    )
    def verify(payload: Observation, request: Request) -> IntegrityResult:
        if settings.database_url:
            with request.app.state.session_factory() as db:
                session_user(db, request.headers.get("authorization"))
        # Stateless hash recomputation only. No ingestion or identity authentication is implied.
        return verify_observation(payload)

    return router
