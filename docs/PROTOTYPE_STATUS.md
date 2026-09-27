# JOCKY operator product status

## Build Forge delivery — PS-coverage sprint 1

Build Forge (`/forge`) delivers one successful persisted compilation as three seeded, structurally distinct LLVM objects by default (bounded 1–8). It reuses the native compiler's diversity and ORC fixture runner, existing Variant records, object store, outbox/audit infrastructure and Ed25519 signing. Migration `0006_build_forge` persists build/stage history and variant membership. Refresh retains the selected run.

Stages: SOURCE → VALIDATE → JIR → DIVERSIFY → LLVM → BUILD → TEST → EQUIVALENCE → MANIFEST → READY. Source validation/JIR gates reuse the existing compilation; compiler lowering/build/fixture stages execute in a single bounded native invocation. Their timings are measured compiler-stage sums across all candidate seeds, not sequential wall-clock latencies. Seed scanning selects genuinely distinct structural templates and byte hashes; insufficient diversity fails explicitly.

Equivalence is **bounded compiler-fixture equivalence**: same source/JIR/declared plan and normalized deterministic fixture result; optional expected-result hash can reject the set. Fixture inputs carry simulation=true. It does not prove universal behavior or native endpoint execution. Failed gates stop delivery; missing/tampered bytes cannot pass manifest-and-object verification.

Protected AES-256-GCM literals already exist in the compiler and require external key configuration. Endpoint key distribution remains PARTIAL. This sprint delivers host-target memory-worker objects; cross-target worker packaging, fleet rollout and crash-resuming build workers are unavailable. Background-task interruption may leave a persisted RUNNING run; start a new build to repeat delivery.

## WORKING NOW

The product follows **Connect → Write → Compile → Diversify → Run → Investigate → Verify**.

- Login returns to Command Center and the header shows the authenticated username/role. Command Center anchors the product with a clickable, backend-derived seven-stage operation flow. Primary routes are covered by browser tests.
- Connect Endpoint starts up to three independently enrolled real Linux Rust agents with one click per slot through an internal fixed-command supervisor. ONLINE requires its authenticated heartbeat. Start is idempotent; stop/restart preserves identity and history. External enrollment issues a real one-time token, exposes CA download and the actual Rust CLI commands, and tracks the token-bound endpoint. Enrollment remains WAITING until authenticated heartbeat; expired tokens and stale heartbeats are distinct states.
- Endpoint inventory and detail tabs use persisted observations, jobs and evidence. Missing collector data has an explicit empty state.
- Workbench starts empty. Five shared language examples load on demand; CHECK, compile, stages and variant generation use the native compiler and persisted APIs.
- Documentation has an in-page navigation and documents implemented grammar and execution limitations. Examples offer Copy and Open in Workbench and are compiler-checked by acceptance testing.
- Investigations list persisted hunts. The creation wizard selects named compilation, online-first endpoints, memory/native mode and reviews capability/provenance constraints before creating and starting real jobs.
- Investigation detail shows endpoint jobs, variants, progress, observations, evidence and committed events. Seeded partial failure is labeled Failure Isolation Scenario, not the default workflow.
- Findings provide supporting observations, endpoint/process/network context, timeline and evidence links. Raw data is collapsed.
- Timeline has chronological presentation, endpoint/type/severity/time/search filters and event detail.
- Variant comparison shows actual distinct artifact/LLVM identities, retained stage profiles and byte sizes; Build Forge variants show VERIFIED only after signed provenance, actual object integrity and bounded compiler-fixture equivalence gates pass. Older ungated variants stay NOT TESTED. Compiler breadcrumbs select the exact persisted compilation.
- Graph retains raw backend relationships, aggregates only identical logical connections within the same job for visualization, and adds finding focus, hierarchy layout, human labels, selection, search, type filtering and fit-to-view.
- Driver inventory uses platform-appropriate Linux module / Windows driver columns, summaries, stored observations and truthful signature/risk coverage. LOCAL denotes real container agents; SANDBOX denotes fixtures.
- Performance exposes actual compiler profiles, newly retained variant profiles/artifact byte sizes, benchmark samples, job counts and endpoint last-seen state. Unavailable CPU/memory/duration metrics say Not measured.
- Evidence recomputes actual stored bytes. VALID requires accessible matching hashes; absent content cannot produce a valid result. Immediate verification drawers distinguish artifact byte integrity from manifest signature/provenance.

## PARTIAL

- Windows endpoints and richer forensic findings can be demonstrated with backend SANDBOX fixtures; this pass verifies actual Linux Rust-agent execution, not Windows runtime acceptance.
- The remote compiler/agent bridge supports bounded inventory programs. Filters, rich correlation and timeline/export syntax may compile but are not supported in that remote bridge; documentation states this restriction.
- Endpoint health currently reports heartbeat state/last seen. CPU, memory, dispatch latency and collector duration are unavailable unless reported by existing contracts.
- Inventory risk is UNKNOWN unless actual collected metadata provides a supported risk state. No vulnerability or exploitation claim is made.

## MISSING FOR VIDEO

No missing local connection step. make demo-up builds/starts the internal launcher and bundled Rust/LLVM runtime; the browser starts the real agent without another terminal. Manual enrollment remains available for external machines.

## DEFERRED UNTIL FINAL BUILD

Physical Windows acceptance, expanded remote execution beyond bounded collectors, certificate lifecycle, fleet-scale trials, external audit checkpoints, external adapters and production deployment remain outside this product pass. Driver exploitation and evasion are excluded.

## Verification

Three-agent product acceptance passed: 8 desktop/mobile tests plus 4 final context regressions, 85 foundation Python tests, 25 fresh-PostgreSQL integration tests and 24 Rust tests. Frontend lint/typecheck/production build, Compose validation and diff checks passed. All 19 documentation programs compiled through actual LLVM. See BUILD_STATUS.md for commands and VIDEO_RECORDING_GUIDE.md for the operator journey. Backend fixtures retain simulation=true; presentation uses SANDBOX without changing evidence data.
