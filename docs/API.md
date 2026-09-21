# API and engineering contracts

## Idea-submission demo

`POST /api/demo` requires ANALYST/ADMIN and a backend configured with
`JOCKY_MODE=DEMO`. REAL mode rejects it with 409. It prepares the caller's tenant
scenario through the real native compiler and ordinary persisted domain models;
returns `case_id`, `simulation=true`, and `simulation_label=SIH_VIDEO_DEMO`.
Repeated preparation reuses a ready case. Compilation failure is durable and
returns 503; no prepared marker is written on failure. The separate video stack
prevents synthetic resources from entering the REAL workspace.

All presentation views consume existing cases, hunts/jobs, variants, observations,
findings, graph, timeline, artifacts, manifests and benchmark routes. Verification
and event streaming remain the existing authenticated services. Fixed demo seeds
produce actual compiler artifacts, not example hash strings.

## Phase 4 backend contract checkpoint — 2026-09-20

The historical foundation/design sections below predate the implemented persistent control plane. The authoritative current completion/verification boundary is the **Phase 4 backend contract checkpoint in [BUILD_STATUS.md](BUILD_STATUS.md)**. Remote Rust execution and three-endpoint hunt orchestration are verified within their documented bounded scopes.

With `JOCKY_DATABASE_URL` configured, authenticated routes are hosted under `/api`: `/auth/login`, `/auth/me`, `/auth/logout`, `/users`, cases, scripts/versions/compile, compilations/stage outputs/variants, variants/compare/manifest, endpoint enrollments/inventory/revocation/observations/jobs, hunts/start/cancel/jobs, artifacts/content/verify, manifests/verify, findings, graph, timeline, events, audit verification, benchmarks, compatibility-runs, and JSON reports. `/docs` and `/openapi.json` describe the exact methods and request schemas. Domain resources are UUID-scoped to the authenticated organization. Login returns a one-hour bearer session; ADMIN and ANALYST can author investigations, VIEWER reads and verifies, and ADMIN controls users/enrollment/revocation. Dashboard `/api/control/domain/*` keeps sessions in an HttpOnly same-site cookie.

The focused backend contract suite covers authentication/RBAC, legacy compiler
route gates, evidence sealing/tamper checks, stored-observation correlation,
timeline filters, report generation/download/audit, benchmark lifecycle/events,
compatibility persistence and hunt admission, and simulation-labeled DEMO
provenance against local and PostgreSQL fixtures.

`GET /health/ready` now checks database initialization and signing authority availability. `/api/v1/status` remains a public capability/status utility; legacy compiler/verifier requests require authentication when persistence is configured. Without database configuration these legacy routes remain local development utilities, not a remote deployment mode.

AgentControl has TLS `Enroll`, mTLS bidirectional `Exchange`, and assigned-job `FetchJobArtifact`. Enroll uses a one-time token, ECDSA CSR and an Ed25519 evidence-key proof bound to the CSR. Frames require explicit simulation and contiguous sequence numbers; exact replay returns the original committed receipt. Completion requires a verified evidence manifest. The Rust client and bounded REAL execution path are verified in Docker; strict budgets, richer JOCKY operations, Windows live execution, certificate rotation, and multi-agent load/fault acceptance remain outside scope. `/api/events` streams committed tenant outbox records with SSE `Last-Event-ID` resumption.

Run `python scripts/configure_local.py` then `docker compose up -d --build --wait`. Dashboard: port 3000; API: 8000; gRPC mTLS: 50051; enrollment TLS: 50052; PostgreSQL host port: 15432. Generated credentials stay in ignored `.env`; organization UUID appears in API initialization output. Storage currently uses the local content-addressed volume, not the provisioned MinIO service. See BUILD_STATUS for unverified and absent features before relying on older design claims below.

## P0 executable API

Run `make dev-api`; OpenAPI is generated at `/openapi.json`, interactive documentation at `/docs`. API version prefix is `/api/v1`, schema version is `1.0.0`. Routes are local development utilities; remote authentication and production operation are not implemented. Responses use `Cache-Control: no-store` and an `X-Request-ID`. Logs contain measured request duration/status, not source/evidence content.

| Method / path                              | Behavior now                                                    | Response                                             |
| ------------------------------------------ | --------------------------------------------------------------- | ---------------------------------------------------- |
| GET `/health/live`                         | Process is alive                                                | 200 Health                                           |
| GET `/health/ready`                        | Execution/persistence/authentication unavailable                | 503 Health with reason                               |
| GET `/api/v1/status`                       | Actual phase/mode/availability and complete requirement catalog | 200 PlatformStatus; operational=false                |
| GET `/api/v1/endpoints`                    | Inventory is unavailable, not an observed empty fleet           | 200 EndpointList; available=false, items=[], reason  |
| POST `/api/v1/compilations`                | Runs an allowlisted `jockyc` stage when configured              | 200 native JSON; 422 diagnostic; 501 if unconfigured |
| POST `/api/v1/evidence/verify-observation` | Recomputes submitted observation SHA-256                        | 200 IntegrityResult; signature NOT_CHECKED           |
| GET `/metrics`                             | Actual HTTP response counter                                    | Prometheus text                                      |

Request bodies above 1 MiB return 413 before JSON parsing. Invalid request contracts return 422 `JOCKY_E_SCHEMA` without reflecting sensitive input. Unrepresentable RFC 8785 numbers return 422 `JOCKY_E_CANONICAL_JSON`. Unknown routes return a Problem response. Dashboard uses a small allowlisted server proxy under `/api/control/*`; connection failure returns 503 with retry guidance.

Set `JOCKY_COMPILER_PATH` to an executable built from `native/compiler/jockyc` before starting the API to enable Workbench and Compiler Explorer requests. The API writes source into a private temporary directory and invokes the compiler without a shell, with a fixed command allowlist and a 15-second timeout. Supported request commands are `check`, `tokens`, `ast`, `jir`, `plan`, `llvm`, and `run`; `run` is the compiler's explicitly labeled deterministic fixture, not endpoint execution. If the compiler is not configured, the endpoint returns 501 without invented output.

```sh
curl --fail http://127.0.0.1:8000/api/v1/status
curl --fail -H 'Content-Type: application/json' \
  --data-binary @fixtures/evidence/simulated-observation.json \
  http://127.0.0.1:8000/api/v1/evidence/verify-observation
```

The verifier accepts clearly labeled synthetic or real-labeled submitted documents because it is stateless and does not ingest them into any job. Simulation state is preserved in the result. A matching digest can be supplied by anyone and authenticates no producer. Stored-evidence verification must later fetch trusted expected hashes and signatures independently.

## Contract authority and compatibility

Python source: `packages/contracts/src/jocky_contracts`. Generated JSON Schema/TypeScript: `packages/contracts/generated`. `make contracts` regenerates; `make contracts-check` rejects drift. Types cover all named core entities, variants/manifests, execution plans, budgets, signed job envelopes, observations/audit events, status, problems and compiler metrics. `Variant` domain records are represented by VariantManifest keyed by variant_id in P0.

Contracts reject unknown fields and non-finite numbers, require timezone-aware timestamps, lowercase 64-hex SHA-256 values, explicit simulation flags/labels and bounded budgets. Seeds are 16-character hexadecimal strings. Unsampled metrics are null. `SignedJob` requires signature material, but signature-shaped bytes/status are not trusted until cryptographic verification is implemented. JSON Schema/TypeScript describe structural types; conditional refinements remain authoritative in Python and must be mirrored/tested at Rust ingress before dispatch ships.

Additive optional fields require compatible schema evolution; changing field meaning, enum semantics, canonicalization or required fields requires a versioned transition. Producers/consumers negotiate schema/runtime/compiler versions. Reject unsupported majors and report VERSION_MISMATCH. Canonical signed JSON avoids protobuf serialization differences; absent simulation presence in transport is invalid rather than implicitly false.

## Current persistent domain API

| Area          | Current routes / behavior                                                                                                                  |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Cases/scripts | `/cases`, `/cases/{id}`, `/scripts`, `/scripts/{id}/versions`; tenant-scoped cases and immutable source versions                           |
| Build Forge   | `/compilations/{id}`, `/compilations/{id}/{stage}`, `/compilations/{id}/variants`, `/variants/{id}`; real compiler artifacts and manifests |
| Plans/jobs    | `/hunts`, `/hunts/{id}/start`, `/hunts/{id}/cancel`, `/hunts/{id}/jobs`; signed per-endpoint work and aggregate state                      |
| Agents        | `/endpoints/enrollments`, `/endpoints`, `/endpoints/{id}`, `/endpoints/{id}/revoke`; one-time enrollment and identity-bound health         |
| Events        | `/events` SSE with `Last-Event-ID`, committed sequence IDs, keepalives and tenant/session validation                                       |
| Evidence      | `/observations`, `/artifacts`, `/artifacts/{id}/content`, `/artifacts/{id}/verify`, `/manifests/{id}/verify`; durable hash/seal checks     |
| Analysis      | `/graph`, `/timeline`, `/findings`; endpoint/collector/severity/type/time filters and evidence-linked relationships                        |
| Lab           | `/compatibility-runs`, `/benchmarks`; persisted explicit provenance and benchmark events                                                   |
| Reports       | `/reports`, `/reports/{id}`, authorized artifact download; persisted JSON report with audit verification                                   |

Collection routes are bounded to current API limits. Job transitions and
durable evidence verification are enforced by the control-plane state machine;
cursor pagination, generalized idempotency keys, optimistic version columns,
and object-upload expiry remain later hardening work.

## Agent gRPC

`proto/jocky/v1/agent.proto` defines `AgentControl.Enroll` and bidirectional `AgentControl.Exchange`. AgentFrame carries version, endpoint ID, monotonic sequence, presence-aware simulation flag and heartbeat/observation/manifest/progress. ControlFrame carries signed job/cancellation or durable acknowledgement. CanonicalDocument carries schema-normalized RFC 8785 JSON bytes. The gRPC server and Rust connection loop are active for the verified bounded REAL execution path; generated wire types and replay tests remain the transport contract authority.

Schema validation, frame size limits, certificate identity binding, sequence replay handling, signature verification and simulation agreement between frame/document are required before exposing transport. The runtime C ABI is independently versioned and returns explicit status codes. JIR and native artifact compatibility cannot be inferred from protobuf version alone.
