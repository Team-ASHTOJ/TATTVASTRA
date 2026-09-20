# Phase 4 control-plane gap matrix — 2026-09-20

## Stabilization checkpoint

The current remote execution bridge is **PARTIAL**. The Rust source contains
TLS enrollment, signed job admission, durable remote replay, artifact hash
verification, cancellation, and an agent-owned compiler worker. It is not
classified as verified because this macOS host has no `cargo`/`rustfmt`, the
clean native configure is blocked by missing LLVM development files, and no
real Rust-agent-to-control-plane execution acceptance was run. The Docker
agent-runtime image built successfully, but its Dockerfile copies the binary
from the prebuilt `jocky-agent:foundation` image, so that result does not
compile the current working-tree Rust bridge.

Fresh stabilization evidence on this host:

- Python: `70 passed`; focused Phase 4/distributed tests: `13 passed`; two
	existing Starlette/httpx/AnyIO deprecation warnings remain.
- PostgreSQL: `13 passed` from `scripts/test_postgres.py`.
- Dashboard: all workspace typechecks and the production Next.js build passed.
- Docker: both Compose configurations validated; `agent-runtime.Dockerfile`
	built successfully.
- Rust: blocked by missing host Cargo; no current-source Rust result is claimed.
- Native worker: blocked during clean CMake configure by missing `LLVMConfig.cmake`;
	the existing `build/frontend-linux` cache points to `/workspace` and is not
	a valid local build result.

Exact remaining bridge gaps are current-source Rust/native compilation,
real mTLS enrollment and heartbeat against the running control plane, remote
artifact download and worker execution, durable upload/ack/reconnect under
failure, and distributed cancellation/partial-outcome acceptance. The worker
currently admits only bounded inventory collectors without options and rejects
strict budget enforcement or richer JOCKY operations.

Pre-edit inspection against all sixteen requested areas. PASS means scoped implementation plus test evidence; PARTIAL includes unverified acceptance; MISSING means no working path; BROKEN means observed failure. Historical acceptance is distinguished from this machine's fresh results. Existing uncommitted dashboard next-env changes and `.freebuff/` belong to the operator and are preserved.

| Requirement | Initial classification | Evidence / remaining gap |
| --- | --- | --- |
| 1. FastAPI/PostgreSQL; Organization, User, Case, Endpoint, EndpointEnrollment, Script, ScriptVersion, Compilation, Variant, ExecutionPlan, Hunt, Job, Observation, Artifact, EvidenceManifest, Finding, TimelineEvent, AuditEvent, BenchmarkRun, CompatibilityRun, Report | PARTIAL | All 22 requested entities share existing SQLAlchemy models; UUID/FKs/tenant IDs/creation times and migrations exist. Nine historical PostgreSQL tests; fresh database verification pending. Existing enum/state scopes and migration constraints need targeted inspection, not replacement. |
| 2. Cases create/list/detail/patch | PASS (historical scoped tests) | Existing authenticated APIs and persisted model; browser acceptance pending. |
| 2. Scripts/create/version/compile and compilation stages | PARTIAL | All routes exist, actual compiler subprocess adapter and durable stage outputs. Native deployed happy path not yet accepted here; utility auth already tested. |
| 2. Variants/create/detail/manifest/compare | PARTIAL | Real object registry exists; manifest route returns resource wrapper; correct execution-mode provenance and happy-path acceptance needed. |
| 2. Endpoints enrollment/list/detail/observations/jobs | PARTIAL | TLS identity-bound server flow tested historically; Rust client missing, detail heartbeat staleness differs from list. |
| 2. Hunts create/start/cancel/detail/jobs | PARTIAL | Durable routes exist; mixed endpoint modes and real-agent partial-failure acceptance missing. |
| 2. Evidence artifact list/detail/verify, manifest detail/verify | PARTIAL | Rehashes actual local content and checks Ed25519 manifests. Artifact sealing and signed artifact membership missing. |
| 2. Findings/timeline/graph | PARTIAL | NetworkX and persisted observations/findings present; full relationships and live-agent integration unverified. |
| 2. Benchmark/compatibility/report APIs | PARTIAL | Persisted code paths exist; native run happy paths and browser flow unverified, compatibility observations not consulted during hunt admission. |
| 3. gRPC enrollment/heartbeat/dispatch/ack/progress/observations/artifact/completion/failure/cancel | PARTIAL | Server protocol fixture tests cover most operations, and the Rust bridge source implements the client path. Current-source Rust compilation and real Rust execution remain unverified. |
| 3. Rust remote enrollment/stream/replay/upload/execute/finish | MISSING | Standalone Rust supervisor/collectors/spool are working code; no network connection loop or compiler artifact host. Add the smallest signed compiler-artifact bridge; preserve standalone behavior. |
| 4. Multi-endpoint selection/compatibility/compile-once/variants/concurrency/retry/cancel/partial outcome | PARTIAL | One durable compilation, per-endpoint jobs, seeded object variants, retry/cancel aggregation exist. One execution mode per hunt, no real multi-agent test, build failure can abort whole start transaction. |
| 5. SSE compiler/hunt/agent/observation/finding/timeline/benchmark | PARTIAL | Transactional outbox and Last-Event-ID tests exist; browser feed misses some topics and does not refresh resource views; reconnect/session acceptance missing. |
| 6. SHA/object metadata/manifest/provenance/sealing/verification/audit | PARTIAL | Existing actual hashing, local content-addressed storage, Ed25519 and append-only PostgreSQL are preserved. Manifest has no artifact hash membership or full time validation; artifact frames can arrive after sealing. MinIO adapter absent (local store documented). |
| 7. All eight graph relationships and unsigned process/external connection | PARTIAL | Basic NetworkX rule tested. Remote field aliases, unowned connections/IP, process association nodes, PID start identity and derived edge simulation metadata need coverage. |
| 8. Normalized timeline with endpoint/collector/severity/type/time filters | PARTIAL | All filter parameters exist; ingestion always assigns INFO, malformed/naive time range behavior and source precision need tests. |
| 9. ADMIN/ANALYST/VIEWER, unauthenticated denial, tenant isolation, utility auth, gRPC identity | PASS (historical scoped tests) | Existing session and transport gates retained; extend targeted tests to new actions, stream/session and mixed-tenant resources. Not a production security certification. |
| 10. Required actions audited with tamper-evident chaining | PARTIAL | publish atomically appends outbox/audit; login/case/script/build/variant/hunt/artifact/report paths exist; append-only and tamper tests historical. New actions must reuse it. External rollback checkpoints remain unimplemented and are not claimed. |
| 11. Backend DEMO loading with simulation contracts | PARTIAL | CLI fixture loader/data exists; full compiler-backed loading and same API/browser consumption unverified. No frontend telemetry fixtures. |
| 12. Browser login/session/cases/scripts/compilations/endpoints/hunts/jobs/observations/findings/timeline/graph/evidence/live/refresh/auth errors | PARTIAL | Existing forms and resource tables preserved. Browser acceptance absent; endpoint observations/jobs and hunt child jobs lack complete views; resource refresh/event integration incomplete. |
| 13. Benchmark create/status/results/list/events | PARTIAL | Runs actual compiler fixture with simulation provenance, but no happy-path acceptance. No remote benchmark claim. |
| 13. Compatibility create/outcome/list/hunt decisions | PARTIAL | Operator observations persisted; no endpoint decision integration or acceptance. Automated security-tool execution is outside safe prototype scope. |
| 13. Reports request/status/metadata/download/audit | PARTIAL | Real JSON artifact path tested; full evidence/manifest report membership and browser acceptance pending. PDF not required by current request contract. |
| 14. Preserve tests; PostgreSQL/lifecycle/real agent/partial evidence/auth/replay/seal/tamper/cancel | PARTIAL | Fresh local run: 70 Python tests and 13 PostgreSQL tests pass. Protocol fixtures pass, but real Rust-agent execution and distributed failure/cancel acceptance remain open. |
| 15. Documented Compose/fresh start, seven services | PARTIAL | Both Compose configurations validate and the agent-runtime image builds. This checkpoint did not claim a fresh seven-service health/start acceptance. |
| 16. API/status/docs with exact completion and limits | PARTIAL | This checkpoint records current host evidence, the bridge as PARTIAL, and exact remaining Rust/native/distributed gaps. Older architecture/API sections still need later reconciliation. |

Implementation order: restore baseline environment; close integrity/correlation/API gaps with PostgreSQL tests; implement the signed Rust/LLVM execution bridge and mixed-endpoint hunts; verify real distributed failure/cancel/reconnect; complete existing browser views/events and acceptance; run full checks and record precise platform/optional limits. Unsupported instructions or platform artifacts must be rejected during compatibility/admission, never silently interpreted or simulated.
