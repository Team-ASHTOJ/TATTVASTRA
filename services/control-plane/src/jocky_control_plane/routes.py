from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from jocky_contracts.common import Problem
from jocky_contracts.compiler import CompileRequest
from jocky_contracts.evidence import IntegrityResult, Observation, verify_observation
from jocky_contracts.status import EndpointList, Health, PlatformStatus

from jocky_control_plane import __version__
from jocky_control_plane.config import Settings
from jocky_control_plane.coverage import load_coverage


def create_router(settings: Settings) -> APIRouter:
    router = APIRouter()

    @router.get("/health/live", response_model=Health, tags=["health"])
    def live() -> Health:
        return Health(
            simulation=False, status="alive", service="control-plane", version=__version__
        )

    @router.get("/health/ready", response_model=Health, responses={503: {"model": Health}})
    def ready() -> JSONResponse:
        health = Health(
            simulation=False,
            status="not_ready",
            service="control-plane",
            version=__version__,
            reason=(
                "Foundation API only. Compiler, authenticated dispatch and storage are unavailable."
            ),
        )
        return JSONResponse(status_code=503, content=health.model_dump(mode="json"))

    @router.get("/api/v1/status", response_model=PlatformStatus, tags=["platform"])
    def status() -> PlatformStatus:
        return PlatformStatus(
            simulation=False,
            version=__version__,
            tagline="One Language. Every Endpoint. No Noise.",
            phase="P0 — repository foundation",
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
        response_model=Problem,
        responses={501: {"model": Problem}},
        tags=["build-forge"],
    )
    def compile_source(payload: CompileRequest, request: Request) -> JSONResponse:
        problem = Problem(
            simulation=payload.simulation,
            simulation_label=payload.simulation_label,
            code="JOCKY_E_COMPILER_UNAVAILABLE",
            detail="JOCKY frontend and LLVM source lowering are not implemented. See phases P1–P3.",
            status=501,
            request_id=request.state.request_id,
        )
        return JSONResponse(status_code=501, content=problem.model_dump(mode="json"))

    @router.post(
        "/api/v1/evidence/verify-observation",
        response_model=IntegrityResult,
        tags=["evidence"],
    )
    def verify(payload: Observation) -> IntegrityResult:
        # Stateless hash recomputation only. No ingestion or identity authentication is implied.
        return verify_observation(payload)

    return router
