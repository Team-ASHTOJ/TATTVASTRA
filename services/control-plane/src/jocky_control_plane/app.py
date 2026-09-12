import json
import logging
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

import rfc8785
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jocky_contracts.common import Problem
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, generate_latest
from starlette.exceptions import HTTPException

from jocky_control_plane import __version__
from jocky_control_plane.body_limit import BodyLimitMiddleware
from jocky_control_plane.config import Settings
from jocky_control_plane.routes import create_router

logger = logging.getLogger("jocky.http")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.propagate = False


def create_app(settings: Settings | None = None) -> FastAPI:
    application = FastAPI(
        title="JOCKY Control Plane",
        version=__version__,
        description="Foundation API. Capability availability is explicit; dispatch is unavailable.",
    )
    application.add_middleware(BodyLimitMiddleware)
    registry = CollectorRegistry()
    requests = Counter(
        "jocky_http_requests_total",
        "Observed HTTP responses",
        ["method", "status"],
        registry=registry,
    )

    @application.middleware("http")
    async def instrument(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = str(uuid4())
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        requests.labels(method=request.method, status=str(response.status_code)).inc()
        logger.info(
            json.dumps(
                {
                    "event": "http_response",
                    "request_id": request.state.request_id,
                    "method": request.method,
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                }
            )
        )
        return response

    def problem_response(request: Request, status: int, code: str, detail: str) -> JSONResponse:
        problem = Problem(
            simulation=False,
            code=code,
            status=status,
            detail=detail,
            request_id=getattr(request.state, "request_id", None),
        )
        return JSONResponse(status_code=status, content=problem.model_dump(mode="json"))

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, _: RequestValidationError) -> JSONResponse:
        # Do not echo evidence, source literals, credentials, or rejected input in diagnostics.
        return problem_response(request, 422, "JOCKY_E_SCHEMA", "Request violates contract v1.0.0.")

    @application.exception_handler(rfc8785.CanonicalizationError)
    async def invalid_canonical_json(
        request: Request, _: rfc8785.CanonicalizationError
    ) -> JSONResponse:
        return problem_response(
            request, 422, "JOCKY_E_CANONICAL_JSON", "Value cannot be represented in canonical JSON."
        )

    @application.exception_handler(HTTPException)
    async def http_error(request: Request, exception: HTTPException) -> JSONResponse:
        return problem_response(
            request, exception.status_code, "JOCKY_E_HTTP", str(exception.detail)
        )

    @application.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(registry), headers={"Content-Type": CONTENT_TYPE_LATEST})

    application.include_router(create_router(settings or Settings()))
    return application


app = create_app()
