# JOCKY operator product status

## WORKING NOW

The product follows **Connect → Write → Compile → Diversify → Run → Investigate → Verify**.

- Login returns to Command Center. Primary routes are covered by the operator browser test.
- Connect Endpoint issues a real one-time token, exposes CA download and the actual Rust CLI commands, and tracks the token-bound endpoint. Enrollment remains WAITING until authenticated heartbeat; expired tokens and stale heartbeats are distinct states.
- Endpoint inventory and detail tabs use persisted observations, jobs and evidence. Missing collector data has an explicit empty state.
- Workbench starts empty. Five shared language examples load on demand; CHECK, compile, stages and variant generation use the native compiler and persisted APIs.
- JOCKY Language documents implemented grammar and execution limitations. Examples offer Copy and Open in Workbench and are compiler-checked by acceptance testing.
- Investigations list persisted hunts. The creation wizard selects compilation, endpoints, memory/native mode and reviews capability/provenance constraints before creating and starting real jobs.
- Investigation detail shows endpoint jobs, variants, progress, observations, evidence and committed events. Seeded partial failure is labeled Failure Isolation Scenario, not the default workflow.
- Findings provide supporting observations, endpoint/process/network context, timeline and evidence links. Raw data is collapsed.
- Timeline has chronological presentation, endpoint/type/severity/time/search filters and event detail.
- Graph retains backend-derived relationships with human labels, selection, search, type filtering and fit-to-view.
- Driver inventory uses stored observations with truthful signature/risk fields and SANDBOX provenance.
- Performance exposes actual compiler profiles, variant profiles, benchmark samples, job counts and endpoint last-seen state. Unavailable CPU/memory/duration metrics say Not measured.
- Evidence recomputes actual stored bytes. VALID requires accessible matching hashes; absent content cannot produce a valid result. Manifest signature verification remains separate.

## PARTIAL

- Windows endpoints and richer forensic findings can be demonstrated with backend SANDBOX fixtures; this pass verifies actual Linux Rust-agent execution, not Windows runtime acceptance.
- The remote compiler/agent bridge supports bounded inventory programs. Filters, rich correlation and timeline/export syntax may compile but are not supported in that remote bridge; documentation states this restriction.
- Endpoint health currently reports heartbeat state/last seen. CPU, memory, dispatch latency and collector duration are unavailable unless reported by existing contracts.
- Inventory risk is UNKNOWN unless actual collected metadata provides a supported risk state. No vulnerability or exploitation claim is made.

## MISSING FOR VIDEO

No missing product screen. A real agent requires the existing runtime image and trusted CA; browsers cannot launch host containers. The enrollment drawer provides commands rather than a fake launch action.

## DEFERRED UNTIL FINAL BUILD

Physical Windows acceptance, expanded remote execution beyond bounded collectors, certificate lifecycle, fleet-scale trials, external audit checkpoints, external adapters and production deployment remain outside this product pass. Driver exploitation and evasion are excluded.

## Verification

See BUILD_STATUS.md for executed check results and VIDEO_RECORDING_GUIDE.md for the operator journey. Backend fixtures retain simulation=true; presentation uses SANDBOX without changing evidence data.
