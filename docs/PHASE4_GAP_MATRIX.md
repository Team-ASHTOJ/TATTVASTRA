# Phase 4 control-plane gap matrix — 2026-09-20

> **Windows and status reconciliation — 2026-09-28.** The tables below are the
> frozen Phase 4 checkpoint of 2026-09-20 and are kept as a historical record.
> Current status lives in `docs/BUILD_STATUS.md` and in the requirement catalog
> (`services/control-plane/src/jocky_control_plane/data/requirements.json`),
> from which `docs/REQUIREMENT_TRACEABILITY.md` is generated. Since this
> checkpoint: the Windows agent is built, tested and published by Windows CI,
> a Windows bootstrap drives the existing enrollment flow, Windows target
> compilation is VERIFIED against real COFF output, and the requirement catalog
> was reconciled with recorded evidence. Every remaining "Windows live
> execution" limitation below still stands: no Windows host ran enrollment,
> heartbeat, collection or a compiled job, and Windows compiled-job execution
> stays ENVIRONMENT DEPENDENT because it needs an LLVM worker.

## Stabilization checkpoint

The current remote execution bridge is **IMPLEMENTED + VERIFIED** for one REAL
bounded-inventory Rust Agent path on Ubuntu 24.04 arm64 in Docker. The bridge
uses the existing mTLS `Enroll`/`Exchange`/`FetchJobArtifact` protocol, signed
job admission, durable replay, artifact hash verification, the agent-owned
LLVM worker, Rust collectors, signed evidence, progress, completion/failure,
and reconnect handling.

Fresh stabilization evidence on this host:

- Python: `74 passed`; focused Phase 4/distributed tests: `17 passed`; two
  existing Starlette/httpx/AnyIO deprecation warnings remain.
- PostgreSQL: `17 passed` from `scripts/test_postgres.py`.
- Dashboard: all workspace typechecks, production build, and Playwright E2E
  (**14/14**) passed.
- Docker: both Compose configurations validated; `agent-runtime.Dockerfile`
  built successfully.
- Rust: Docker toolchain passed 18 unit + 6 CLI tests, format, build, and
  warnings-denied Clippy.
- Native worker: Docker LLVM 18 configure/build/CTest/self-test passed.

Exact remaining bridge gaps are Windows live execution, certificate rotation,
multi-agent/load/fault acceptance, and external audit checkpoints. The worker
admits only bounded inventory collectors without options and rejects strict
budget enforcement or richer JOCKY operations.

Multi-endpoint orchestration is **IMPLEMENTED + VERIFIED** in the focused
control-plane scope. The three-endpoint acceptance creates one logical plan,
selects memory/native/memory modes, creates independent endpoint jobs and
variants, isolates endpoint B runtime/build failure, preserves A/C evidence,
creates only B's retry, and reaches `PARTIAL`. Compatibility rejection and
build-failure isolation are separately covered. Multi-agent load/fault tests
and live three-agent acceptance remain open.

Backend contract closure classifications:

| Area               | Classification | Evidence / remaining gap                                                                                                                                                                        |
| ------------------ | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Auth / RBAC        | GREEN          | ADMIN/ANALYST/VIEWER, unauthenticated denial, tenant isolation, viewer mutation denial, and legacy compiler-route authentication are covered by the PostgreSQL-backed suite.                    |
| Evidence           | GREEN          | Uploaded artifact membership, stored-byte rehash, tamper failure, sealing, and audit mutation detection are covered.                                                                            |
| Correlation        | GREEN          | Persisted observations drive all eight required relationships and the unsigned external-connection finding.                                                                                     |
| Timeline           | GREEN          | Endpoint, collector, severity, type, and timezone-aware start/end filters are tested against persisted rows.                                                                                    |
| Reports            | GREEN          | Generation, persisted SUCCESS metadata, authorized download, integrity verification, and audit evidence are tested.                                                                             |
| Benchmarks         | GREEN          | POST/GET lifecycle, persisted simulated samples/status, and benchmark events are tested.                                                                                                        |
| Compatibility runs | GREEN          | POST/GET persistence is tested; an API-recorded correctness failure changes only the affected endpoint's hunt assignment.                                                                       |
| DEMO fixtures      | LIMITATION     | `demo.load` is backend-owned and propagates `simulation=true` plus a label through cases, observations, manifests, and events; a dedicated loader acceptance test was not rerun in this freeze. |

Final acceptance against all sixteen requested areas. PASS means the required
prototype flow and evidence passed. LIMITATION means a documented prototype,
platform, or noncritical acceptance boundary remains. No MISSING, BROKEN, or
vague TODO classification remains.

| Requirement                                                                                                                                      | Final classification | Evidence / limitation                                                                                                                                                                          |
| ------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1. FastAPI/PostgreSQL domain resources and migrations                                                                                            | PASS                 | Models, UUID/FKs, tenant scope, migrations, full Python suite, and 17 PostgreSQL integration tests pass.                                                                                       |
| 2. Cases create/list/detail/patch                                                                                                                | PASS                 | Authenticated persisted API and dashboard resource flow pass; browser E2E and API tests pass.                                                                                                  |
| 2. Scripts/create/version/compile and compilation stages                                                                                         | PASS                 | Persisted script/version routes, compiler outputs, dashboard Scripts / Versions, and compiler E2E pass.                                                                                        |
| 2. Variants/create/detail/manifest/compare                                                                                                       | PASS                 | Real artifact registry, manifest/provenance routes, endpoint-specific variants, and backend tests pass.                                                                                        |
| 2. Endpoints enrollment/list/detail/observations/jobs                                                                                            | PASS                 | mTLS enrollment, heartbeat, persisted observations/jobs, real agent execution, and dashboard views pass within Linux/bounded scope.                                                            |
| 2. Hunts create/start/cancel/detail/jobs                                                                                                         | PASS                 | Multi-endpoint dispatch, retry, cancellation, partial-success, persisted jobs, and dashboard E2E pass.                                                                                         |
| 2. Evidence artifact list/detail/verify, manifest detail/verify                                                                                  | PASS                 | Artifact membership, byte rehash, tamper rejection, sealing, manifest verification, downloads, and tests pass.                                                                                 |
| 2. Findings/timeline/graph                                                                                                                       | PASS                 | Persisted observations drive required graph relationships, finding, timeline filters, and dashboard views.                                                                                     |
| 2. Benchmark/compatibility/report APIs                                                                                                           | GREEN (scoped)       | Backend POST/GET/report lifecycle, benchmark fixture lifecycle/events, compatibility persistence, and hunt admission consumption pass; browser/PDF and remote performance remain out of scope. |
| 3. gRPC enrollment/heartbeat/dispatch/ack/progress/observations/artifact/completion/failure/cancel                                               | PASS                 | Live Rust protocol flow and replay/cancellation tests pass.                                                                                                                                    |
| 3. Rust remote enrollment/stream/replay/upload/execute/finish                                                                                    | PASS                 | REAL job evidence persisted; Rust spool replay/idempotency tests pass.                                                                                                                         |
| 4. Multi-endpoint selection/compatibility/compile-once/variants/concurrency/retry/cancel/partial outcome                                         | PASS                 | Three-endpoint A-success/B-failure/C-success, per-endpoint variants/modes, retry, evidence preservation, and compatibility/build isolation pass.                                               |
| 5. SSE compiler/hunt/agent/observation/finding/timeline/benchmark                                                                                | PASS                 | Durable outbox, Last-Event-ID, dashboard SSE receipt, query invalidation, and browser tests pass.                                                                                              |
| 6. SHA/object metadata/manifest/provenance/sealing/verification/audit                                                                            | LIMITATION           | Required integrity flow passes; external rollback checkpoints and MinIO authority are prototype limitations.                                                                                   |
| 7. All eight graph relationships and unsigned process/external connection                                                                        | PASS                 | Persisted-observation graph and finding acceptance pass without hard-coded results.                                                                                                            |
| 8. Normalized timeline with endpoint/collector/severity/type/time filters                                                                        | PASS                 | All requested filters and invalid-range rejection pass.                                                                                                                                        |
| 9. ADMIN/ANALYST/VIEWER, unauthenticated denial, tenant isolation, utility auth, gRPC identity                                                   | LIMITATION           | Required authorization and identity tests pass; this is not a production security certification.                                                                                               |
| 10. Required actions audited with tamper-evident chaining                                                                                        | LIMITATION           | Required append-only chain and mutation detection pass; external rollback checkpointing remains unavailable.                                                                                   |
| 11. Backend DEMO loading with simulation contracts                                                                                               | LIMITATION           | Backend loader propagates simulation labels; dedicated loader acceptance and full demo workflow were not rerun in this freeze.                                                                 |
| 12. Browser login/session/cases/scripts/compilations/endpoints/hunts/jobs/observations/findings/timeline/graph/evidence/live/refresh/auth errors | PASS                 | 14/14 browser E2E, persisted resource views, authenticated proxy, SSE smoke, and role/session behavior pass.                                                                                   |
| 13. Benchmark create/status/results/list/events                                                                                                  | PASS                 | Persisted simulated fixture lifecycle, samples, status, and events pass. Remote performance is not claimed.                                                                                    |
| 13. Compatibility create/outcome/list/hunt decisions                                                                                             | PASS                 | API POST/GET persistence and recorded correctness consumed by hunt admission pass. Automated security-tool execution is out of scope.                                                          |
| 13. Reports request/status/metadata/download/audit                                                                                               | PASS                 | Real JSON generation, status, metadata, authorized download, integrity, and audit event pass. PDF remains unavailable.                                                                         |
| 14. Preserve tests; PostgreSQL/lifecycle/real agent/partial evidence/auth/replay/seal/tamper/cancel                                              | PASS                 | 74 Python, 17 PostgreSQL, 24 Rust, native, dashboard, E2E, and live-stack evidence pass.                                                                                                       |
| 15. Documented Compose/fresh start, seven services                                                                                               | PASS                 | Compose config/build/start passed; PostgreSQL, Redis, MinIO, API, gRPC, scheduler, and dashboard healthy.                                                                                      |
| 16. API/status/docs with exact completion and limits                                                                                             | PASS                 | API, BUILD_STATUS, API docs, and final matrix are reconciled; scoped limitations are explicit.                                                                                                 |

Implementation order after this checkpoint: Windows live execution, certificate rotation, multi-agent fault/load acceptance, and external audit checkpoints. Unsupported instructions or platform artifacts must be rejected during compatibility/admission, never silently interpreted or simulated.
