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

## Operator enrollment state

`POST /api/endpoints/enrollments` remains the administrator-only issuance route.
The token is returned once. `GET /api/endpoints/enrollments/{id}` is an
administrator/tenant-scoped status adapter: WAITING before enrollment, EXPIRED
for an unused expired token, ONLINE only for its bound endpoint with an
unrevoked authenticated heartbeat within 90 seconds, otherwise STALE.
`GET /api/endpoints/enrollments/{id}/ca` downloads the public transport CA for
that enrollment; it never exposes a private key or stored token hash.

Artifact verification returns `available`, `expected_hash`, `computed_hash`,
and `integrity_valid`. Missing stored content returns unavailable/false with a
null computed hash. Matching metadata alone is not content verification.
Manifest signature verification remains a separate operation.

## Local endpoint lifecycle

ADMIN-only `POST /api/local-agent/start` and `POST /api/local-agent/stop`, plus `GET /api/local-agent/status`, manage a selected internal runtime. The optional `slot` query parameter defaults to 1 and accepts only 1–3. ADMIN-only `GET /api/local-agents` returns all three slots; each has its own process, state volume, endpoint identity and tenant ownership. Start reuses active operations/identity; stop preserves all persisted jobs/evidence. The launcher is tenant-bound on first use. A different organization cannot inspect or control it.

States are STOPPED, STARTING, ENROLLING, WAITING_FOR_HEARTBEAT, ONLINE, FAILED and STALE. ONLINE is derived by the control plane from the enrolled endpoint's authenticated heartbeat after the current connect process began. Missing, overdue or pre-restart heartbeats do not establish ONLINE. A heartbeat timeout reports FAILED with an actionable error.

No agent token is returned by these APIs. The launcher uses a generated internal bearer credential, is unpublished on the host, accepts only a fixed typed enrollment body, and runs the existing init/enroll/connect commands without a shell or Docker socket. Agent credentials live in separate local_agent_state, local_agent_state_2 and local_agent_state_3 volumes; ephemeral enrollment token files are removed after use.

New variant manifests retain the compiler-returned `profile` and the actual stored `artifact_size_bytes`. Old variants may lack these fields; missing measurements remain unavailable. Profile stage durations do not represent total control-plane wall-clock build time.

Bounded inventory routes return their newest window in chronological order (default 500, or the route-specific requested limit). Historical resources remain available through detail APIs. This prototype does not expose complete fleet pagination.

## Persistent Build Forge

Authenticated reader routes: GET `/api/build-capabilities`, `/api/build-runs`, `/api/build-runs/{id}`, `/api/build-runs/{id}/manifest`; POST `/api/build-runs/{id}/verify` recomputes object hashes and verifies the Ed25519 build-signing domain and provenance. Tenant ownership is enforced on every run.

ADMIN/ANALYST POST `/api/build-runs` accepts `compilation_id`, `count` (1–8, default 3), `target:"host"`, `execution_mode:"memory"`, optional 16-lowercase-hex `seed`, and optional SHA-256 `expected_semantic_hash`. Returns 202 with a durable QUEUED run; the existing API background task invokes the real native compiler, commits stage events and produces READY or FAILED. GET status exposes stages, actual timing scopes, selected seeds, errors, fixture results and signed manifest. Manifest retrieval returns 409 before signing. Capabilities list the actual supported delivery options and protected-literal key availability without key material.

Build states: QUEUED / RUNNING / READY / FAILED. Stage states: PENDING / RUNNING / SUCCESS / FAILED / SKIPPED. Timings may be null. Deterministic fixture input is explicitly simulation=true; objects and compiler execution remain real. The manifest has a separate `JOCKY:build:v1` signing domain; it is build provenance, not an agent evidence seal. Verification exposes signature_valid, provenance_valid, artifact_integrity_valid and combined valid; missing bytes cannot be valid.

Variants retain build_run_id and bounded equivalence metadata. `/api/variants/compare` reports VERIFIED only for fixture-equivalent variants whose READY delivery manifests and stored bytes still verify. Legacy variants remain NOT_TESTED. Build delivery is host-target LLVM object publication; fleet rollout, native worker linking and crash-resuming queues are not provided by this route.
