# API and engineering contracts

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

## Planned domain API (not hosted yet)

| Area          | Planned routes / behavior                                                                                                        |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Cases/scripts | `/cases`, `/cases/{id}`, `/scripts`, `/scripts/{id}/versions`; tenant scope and immutable source versions                        |
| Build Forge   | `/compilations/{id}`, `/compilations/{id}/stages`, `/variants`, `/forge/builds`; actual compiler artifacts and manifest registry |
| Plans/jobs    | `/execution-plans`, `/hunts`, `/jobs/{id}`, `/jobs/{id}/cancel`, `/jobs/{id}/retry`; signed per-endpoint work                    |
| Agents        | `/enrollment-tokens`, endpoint detail/health; one-time enrollment and certificate lifecycle                                      |
| Events        | `/cases/{id}/events` SSE with Last-Event-ID, committed sequence IDs, heartbeat and scope validation                              |
| Evidence      | Scoped observation ingestion, artifact upload initiation/completion, manifest verification, `/artifacts/{id}/verify`             |
| Analysis      | `/cases/{id}/graph`, `/timeline`, `/findings`; source/endpoint/severity filters and evidence links                               |
| Lab           | `/drivers/risk-imports`, `/lab/simulations`, `/compatibility-runs`, `/benchmark-runs`; explicit provenance                       |
| Reports       | `/cases/{id}/reports`, authorized download; PDF/JSON with verification/audit status                                              |

Collection routes use cursor pagination and bounded limits. Mutations accept idempotency keys scoped to organization/action; retries return the original committed result or create explicitly linked new attempts. Job transitions use optimistic version checks/409 conflicts. Object uploads bind expected digest/size/case/job and expire. Never acknowledge evidence before durable verification and metadata commit. These semantics are design contracts, not existing P0 endpoints.

## Agent gRPC

`proto/jocky/v1/agent.proto` defines `AgentControl.Enroll` and bidirectional `AgentControl.Exchange`. AgentFrame carries version, endpoint ID, monotonic sequence, presence-aware simulation flag and heartbeat/observation/manifest/progress. ControlFrame carries signed job/cancellation or durable acknowledgement. CanonicalDocument carries schema-normalized RFC 8785 JSON bytes. Generated Rust client/server types and wire round-trip tests exist; no gRPC server or agent connection loop is active yet.

Schema validation, frame size limits, certificate identity binding, sequence replay handling, signature verification and simulation agreement between frame/document are required before exposing transport. The runtime C ABI is independently versioned and returns explicit status codes. JIR and native artifact compatibility cannot be inferred from protobuf version alone.
