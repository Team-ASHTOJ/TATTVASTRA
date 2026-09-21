# Idea-submission prototype — frozen 2026-09-21

**PROTOTYPE STATUS: READY**

Targeted audit started at `841f3d5`. Working compiler, Rust agent and Phase 4
control plane were preserved. This sprint delivers the recording path rather
than adding production infrastructure.

## WORKING NOW

- **VERIFIED:** isolated video Compose stack: PostgreSQL, API with the real LLVM
  compiler, and dashboard. Separate `jocky-video` volumes; REAL data is untouched.
- **VERIFIED:** repeatable tenant-scoped DEMO preparation; real source compilation,
  three fixed-seed artifacts with distinct actual hashes, three synthetic endpoint
  outcomes, partial success, observation-derived finding/graph/timeline, actual
  stored evidence bytes, Ed25519 manifests and audit verification.
- **VERIFIED:** 14 focused navigation screens, guided Judge Mode, prepared source
  loading, real compiler actions, interactive graph, endpoint/finding/driver cards,
  timeline filtering, stored-byte/manifest checks and persisted benchmark samples.
- **VERIFIED:** visible backend REAL versus DEMO/SIMULATED labels. No frontend
  endpoint/result fixtures or fabricated progress, LLVM, hashes or timings.
- **VERIFIED:** browser login, refresh persistence and committed SSE. The demo is
  saved backend scenario history; it does not claim live endpoint execution.
- Existing REAL bounded Linux collector execution remains the Phase 4 delivery;
  no compiler/agent subsystem was rebuilt or extended for the video sprint.

## PARTIAL

- Driver Intelligence presents read-only synthetic inventory/risk annotations;
  it is not a sourced CVE database or live Windows driver assessment.
- Compiler stage output and benchmark samples retain detailed JSON inspectors;
  a complete profiling/charting product is deferred.
- The video uses real host-target builds with simulated Windows/Ubuntu inventory.
  It does not prove cross-platform execution or variant semantic equivalence.
- No production accessibility certification or fleet-performance claim. Desktop
  and mobile Chromium walkthroughs and existing responsive checks are tested.

## MISSING FOR VIDEO

No known blocker for the documented 4–6 minute recording path after the verified
setup. Operator tasks remain: sign in immediately before recording, rehearse the
script, and record narration/screen capture. A final video file is not generated.

## DEFERRED UNTIL FINAL BUILD

Full Forge, Compatibility Lab/report management, external forensic adapters,
SIEM/cloud infrastructure, certificate rotation, strict CPU/memory governors,
external audit checkpoints, Windows live acceptance and fleet fault/load trials.
Existing direct routes remain available; no working feature was removed.

Driver exploitation, kernel tampering and evasion claims are excluded, not backlog.

## Verification evidence

- Initial focused Phase 4 smoke: **8 passed**; workspace TypeScript checks passed.
- `make verify-foundation`: **passed**, including **76 Python tests**, contracts /
  generated coverage drift, Ruff/Prettier/ESLint, Python/TypeScript typing, protobuf,
  Python packages and Next.js production build. Two upstream deprecation warnings.
- Native compiler image: corrected demo source `check --json` returned valid
  source/JIR hashes and four typed instructions. No native runtime changes here.
- `make demo-prepare`: **passed against fresh PostgreSQL migrations**. Verifies
  repeat loading, 3 distinct artifacts, 3 simulated jobs, PARTIAL aggregate, derived
  finding/graph, byte hashes, signatures and audit chain.
- `playwright.prototype.config.ts`: **2 passed**, complete desktop/mobile recording
  workflows against real running services; no mocked compiler or evidence APIs.
- Home and graph screenshots visually inspected at 1440px; screenshots stay in
  ignored `.cache`. Automated credential traces/video are disabled.
- Existing browser regression suite: **14 passed** after the obsolete Judge Mode
  expectation was updated to assert REAL/DEMO separation; responsive overflow
  coverage and existing compiler/verifier/disconnect checks remain intact.

The first preparation correctly failed for reserved binding names and saved a
FAILED compilation. The source was corrected and checked with the real compiler;
subsequent preparation passed. Failed records were not relabeled or fabricated.

Run `make demo-up`, then `make demo-prepare`. Open **http://localhost:13000/judge**.
See [DEMO_FLOW.md](DEMO_FLOW.md) for credentials, script, recovery and exact commands.

## Final closure acceptance — 2026-09-21

No application changes were needed during the closure pass. The current worktree
passed the interrupted browser checks before final acceptance:

- `make test-e2e`: **14 passed**, desktop/mobile.
- `COMPOSE_PROJECT_NAME=jocky-video-closure make demo-up`: **passed**; all three
  services healthy, new PostgreSQL/evidence volumes, existing volumes preserved.
- `COMPOSE_PROJECT_NAME=jocky-video-closure make demo-prepare`: **passed** from
  empty demo state; three artifacts/jobs, two simulated successes and one simulated
  failure, PARTIAL hunt, derived finding/graph, hashes, signatures and audit chain.
- `COMPOSE_PROJECT_NAME=jocky-video-closure PLAYWRIGHT_BROWSERS_PATH=.cache/playwright
npx playwright test -c playwright.prototype.config.ts`: **2 passed**. The
  desktop/mobile flows also create actual three-sample compiler benchmark runs.
- `make verify-foundation`: **passed once at closure**; **76 Python tests**, two
  upstream warnings, typechecks, lint/format, generated-contract/coverage checks,
  protobuf, package builds and **23 generated Next.js pages**.
- `git diff --check`: **passed**.

REAL: compiler stages, host-built artifacts/hashes, backend correlation,
cryptographic verification and persistence. MEASURED: actual compiler-fixture
benchmark samples. DEMO/SIMULATED: endpoint inventory/outcomes, observation inputs,
driver risk annotations and their evidence contents. DEFERRED: the final-build
items above. No Windows live-fleet or production-security acceptance is implied.

The prepared closure stack remains at http://localhost:13000/judge. Use
`COMPOSE_PROJECT_NAME=jocky-video-closure` with demo commands to operate it;
the earlier `jocky-video` volumes are preserved and its containers stopped.
