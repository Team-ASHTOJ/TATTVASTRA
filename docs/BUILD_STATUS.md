# Build status

## Compatibility Lab V1 — 2026-10-03

Status: **IMPLEMENTED** for the existing CompatibilityRun API, server-resolved
completed-job candidates, job-linked measurement derivation, environment
fingerprints, and the interactive `/compatibility` bench. **VERIFIED** only by
the checks listed below. Windows/Defender execution compatibility is
**NOT_MEASURED / BLOCKED_ENVIRONMENT**; no real Windows security-product run was
recorded.

- The existing CompatibilityRun table and `compatibility.recorded` event remain
  authoritative. The typed request contract adds optional measurement metadata;
  generated JSON Schema and TypeScript were regenerated. Historical request
  payloads still work. No database migration or CLI control-plane capability was
  added.
- The server snapshots persisted variant, compilation/JIR, source, endpoint,
  recorder, and REAL/SIMULATED identity into each run's `observations`. A linked
  job must match tenant, variant, and supplied endpoint. Its execution status,
  reported duration/CPU/memory where present, and persisted observation counts
  are server-derived; client overrides are rejected. Unreported Peak RSS and
  other missing metrics remain null/UNAVAILABLE.
- The authenticated Compatibility Lab now starts with persisted successful jobs.
  Selection or native drag/drop hydrates build, endpoint, execution, collector,
  and simulation provenance server-side; the operator modal contains only the
  security product/version, realtime state, alert observation, and policy note.
  The existing POST remains authoritative and rejects client overrides of
  job-derived execution measurements.
- A normalized SHA-256-derived `ENV-XXXXXX` fingerprint identifies a persisted
  job baseline from OS/architecture/transport/execution context, then records a
  more specific product/version/realtime environment when an operator adds that
  observation. Comparisons require the exact persisted fingerprint. Alert
  observations do not rank variants or feed
  the compiler. Existing admission remains correctness-only and endpoint-scoped:
  `FAIL` may reject, while an alert by itself does not.
- The bench presents a fixed build → endpoint → security environment → execution
  → result chain, a three-axis compatibility signal (not a score), movable
  provenance tokens with click/focus fallback, measurement history, a truthful
  `NOT_MEASURED` path, reduced-motion behavior, and a stacked mobile layout.

Executed checks:

- `make contracts-check`: PASS (schema, TypeScript, coverage drift).
- `.venv/bin/pytest services/control-plane/tests/test_compatibility_lab.py services/control-plane/tests/test_phase4.py -q`: **16 passed** using persisted protocol fixtures, not Windows measurements.
- Focused Ruff check and repository-configured `.venv/bin/mypy`: PASS.
- Dashboard typecheck and production build: PASS.
- `npx playwright test tests/e2e/compatibility.spec.ts --project=chromium --workers=1`: **6 passed** with mocked UI responses; immediate idempotent job-derived baseline recording, optional security-observation enrichment, persisted history, drag/drop plus click fallback, server-derived fields, exact-fingerprint comparison, actionable empty state, and mobile overflow were exercised.
- `git diff --check`: PASS.
- `make verify-foundation`: **NOT PASSED**. It stopped at the repository-wide
  Ruff format check because 12 pre-existing unrelated files would be reformatted;
  those files were not changed for this feature. The remaining foundation stages
  were not run by that command.


## Standalone TATTVASTRA product website — 2026-09-30

Status: **IMPLEMENTED and VERIFIED as a standalone static Next.js application.**

- Built the product website as a standalone application, now maintained outside
  this repository at the sibling `tattvastra-website` directory. The single-page
  public site presents JOCKY, typed JIR,
  mandatory LLVM compilation, Build Forge, authorized Agent execution, evidence,
  reports, bounded AI hypotheses, local Python interoperability and the CLI using
  repository-grounded claims and explicit current boundaries.
- The site has no backend, authentication, environment-variable, Docker or
  operational-console dependency. It uses copies of the TATTVASTRA mark,
  wordmark, logo and icon and is independently deployable with the standalone
  project root selected in Vercel.
- Client JavaScript is limited to mobile navigation, active-section tracking,
  one-time scroll reveals, code tabs/copy and pausing decorative SVG motion while
  the document is hidden. The page is otherwise statically prerendered.

Executed checks:

- `(cd ../tattvastra-website && npm run typecheck)`: PASS.
- `(cd ../tattvastra-website && npm run build)`: PASS; `/` is statically prerendered.
- Standalone website scoped formatting and `git diff --check`: PASS.
- Headless Chromium at 1440 × 1000, 768 × 1024 and 390 × 844: PASS with 23
  sections, zero browser errors, working mobile navigation and no page-level
  horizontal overflow.
- Existing dashboard typecheck and production build: PASS. The repository-wide
  Prettier check remains blocked by ten pre-existing/unrelated files outside this
  website change; all files changed for the website pass the scoped check.

## Report-grounded AI hypothesis analysis — 2026-09-29

Status: **IMPLEMENTED and VERIFIED with mocked Groq; live Groq generation is not verified.**

- A Hunt report queues optional analysis after its canonical artifact is persisted. Report rows retain PENDING, READY, or FAILED status, model, input artifact hash, generated document/time, and a sanitized failure message. Existing case reports and persisted Findings are unchanged. A failed analysis can be retried; READY/PENDING analysis for the same artifact hash is not regenerated.
- The server sends a bounded packet derived from the persisted report to Groq GPT-OSS 20B using strict JSON Schema, low reasoning effort, no returned reasoning, no tools, a 30-second timeout and at most one transient retry. Exact source text and the full raw observation set are excluded. Server validation requires three ranked hypotheses, report-backed evidence IDs, and platform responses from report-derived allowed actions. The API key is read only from `GROQ_API_KEY` on the server; `GROQ_MODEL` defaults to `openai/gpt-oss-20b`.
- Insight retains its evidence-backed Findings table and adds separate AI-assisted cards, report selection, polling, and failure retry. The canonical forensic report contains only an understated link to Insight.

Executed checks: focused report/hypothesis API tests **7 passed** with Groq mocked; targeted Insight Playwright test **1 passed** against the current local production build. Backend Ruff/mypy, dashboard typecheck/build, Prettier and `git diff --check`: PASS. Live Groq requests were not made; missing `GROQ_API_KEY` yields FAILED analysis without failing report creation.

# Build status

## Local Python package interoperability — 2026-09-29

Status: **VERIFIED for local ORC execution in the Python-capable LLVM container.**

- Rebuilt `jockey-native:foundation` from `infra/docker/native.Dockerfile` with Python 3 development support. The runtime compiled with `JOCKY_WITH_PYTHON=1`; `jockyc` links `libpython3.12`. The existing `jocky` container launcher mounts `JOCKY_PYTHON_PACKAGES_DIR` (or `~/.jocky/python/site-packages`) read-only for local runs.
- `PYTHONPATH=cli/src jocky install humanize`: PASS; `humanize` is present in `~/.jocky/python/site-packages`. `jocky check examples/python/humanize_demo.jky`, `jocky jir examples/python/humanize_demo.jky --json`, `jocky llvm examples/python/humanize_demo.jky`, and `jocky compile examples/python/humanize_demo.jky --target host --execution native --output /tmp/jocky-python-demo.o`: PASS; object non-empty. JIR contains `PYTHON_CALL`, LLVM contains `jocky_rt_analysis`.
- `jocky examples/python/humanize_demo.jky`: PASS through LLVM ORC, `formatted: 1,234,567`. `jocky examples/python/humanize_demo.jky --json`: PASS, `python_results.formatted` is `1,234,567`. With `JOCKY_PYTHON_PACKAGES_DIR` set to a temporary empty directory, the same run failed cleanly with `PYTHON_MODULE_UNAVAILABLE`.
- Docker image build ran the native/compiler/runtime suite: 39/39 PASS, including focused Python interop. `PYTHONPATH=cli/src .venv/bin/python -m pytest cli/tests/test_python_install.py -q`: 9/9 PASS. `git diff --check`: PASS.

## Hunt-scoped forensic investigation reports — 2026-09-29

Status: **IMPLEMENTED and VERIFIED within persisted investigation data.**

- Reports may now reference one Hunt while historical case-level Report rows remain valid. The canonical JSON is built only from the Hunt's Compilation/ScriptVersion, Jobs, Endpoints, ExecutionPlans, Variants, Observations, Artifacts, EvidenceManifests, linked Findings and audit events. Data belonging only to another Hunt in the same Case is excluded.
- The dedicated report presents deterministic summary metrics and text, actual intent and structured semantic operations, per-endpoint results, persisted findings, bounded observation samples, real timestamps, available compiler provenance, distinct signature/hash/audit-chain states, exact source, and data-derived limitations. Missing values are omitted; zero findings does not claim safety; SANDBOX provenance remains explicit.
- Report JSON is stored through the content-addressed ObjectStore with matching Artifact and Report rows and the existing `report.generated` audit event. The report route verifies stored bytes before returning the backend document. Browser print provides Save PDF without changing the canonical JSON artifact.
- Investigation Detail now contains only the outcome counts and the report action. `/investigations/<hunt-id>/report` uses the existing dashboard shell and has focused print styling.

Executed checks:

- Focused reporting/API tests: **3 passed**, covering legacy case reports, Hunt scoping, unrelated-Hunt exclusion, jobs/endpoints, source identity, job-related manifests/artifacts, sandbox provenance, zero findings, failed-job limitations, and stored-byte hash verification.
- Targeted Playwright report acceptance: **1 passed** on desktop, covering Investigation Detail navigation, dedicated report rendering with optional runtime metadata absent, zero-findings language, exact source and browser print invocation.
- Backend Ruff and targeted mypy: PASS. Dashboard typecheck and production build: PASS. `git diff --check`: PASS.

## PS-coverage sprint 2 — cross-target compilation, real execution and relay transport — 2026-09-28

Status: **IMPLEMENTED and verified within the bounded scope below. Windows linking and Windows runtime execution remain ENVIRONMENT DEPENDENT.**

- One program and one semantic JIR now lower to genuinely different machine targets. `jockyc compile --target linux-x86_64` emits ELF for `x86_64-unknown-linux-gnu` (datalayout `e-m:e`) and `--target windows-x86_64` emits COFF for `x86_64-pc-windows-msvc` (datalayout `e-m:w`). The two variants share `source_hash` and `jir_hash` and differ in `llvm_ir_hash`, `variant_id` and object bytes; the object bytes are real ELF (`7f 45 4c 46`) and real COFF (machine `0x8664`), not stubs.
- `POST /compilations/{id}/target-builds` persists a per-target manifest carrying the real triple, LLVM version, object size and hashes. Final linking needs a toolchain for the target, which this host does not have, so every variant honestly reports `link_status = ENVIRONMENT DEPENDENT`. No Windows link and no Windows runtime execution is claimed anywhere in the product.
- MEMORY execution runs LLVM ORC LLJIT over the compiler's IR inside JOCKY's own agent-owned worker process. NATIVE execution runs a linked standalone executable (`artifact_format = native-worker`, `link_status = LINKED`) produced by the same worker. Neither mode injects into, hollows, or executes in a foreign process, and both re-verify the artifact hash before running, rejecting a mismatch as `ARTIFACT_HASH`.
- A real investigation across three enrolled Linux endpoints returns `SUCCESS` for all three memory jobs with `execution_engine = LLVM_ORC_JIT`, real `worker_pid > 0`, real `execution_duration_ms > 0`, and one distinct compiler-generated `variant_id` per endpoint. A separate native job returns `SUCCESS` with `execution_engine = NATIVE_AOT`.
- Transport provenance is authoritative rather than inferred. `endpoints.transport_mode` is written from the authenticated connection and flows into the job envelope, the agent manifest, the signed evidence manifest and the operator console. In the prototype stack `LOCAL-LINUX-02` reaches the control plane through the trusted relay while `LOCAL-LINUX-01` and `-03` connect directly, so the same memory investigation completes one relayed job and two direct jobs.
- TRUSTED_RELAY is a fixed-destination TLS byte pass-through (`relay.py`). It does not terminate, re-originate or inspect TLS, so the endpoint still authenticates end-to-end with the control plane and endpoint identity is unaffected. It is explicitly not an HTTP gateway, reverse proxy, or domain-fronting front.
- Evidence separates cleanly: artifact bytes verify through `POST /artifacts/{id}/verify`, and each job's manifest verifies separately through `POST /manifests/{id}/verify` with `signature_valid`, `integrity_valid` and `provenance_valid`. Manifests carry `execution_engine`, `worker_pid`, `execution_duration_ms` and `transport_mode` matching the job they describe.
- The console labels canonical values without replacing them: `MEMORY / JIT`, `NATIVE / AOT`, `DIRECT`, `TRUSTED RELAY`. An unreported engine stays "Not reported".
- The prototype Compose stack runs the same control-plane deadline sweeper as the development stack (`sweeper`, `jocky_control_plane.cli sweep`); previously it was the only stack without one, so a job dispatched to an endpoint that then stopped stayed `RUNNING` past its deadline forever and its hunt never reached a terminal state. With the sweeper the job is reclaimed as `FAILED` at the 10-minute deadline and lapsed heartbeats are persisted `OFFLINE`.

Executed checks:

- `make verify-foundation`: EXIT 0 — generated contract/coverage drift, formatting, Ruff/ESLint, mypy, workspace typecheck, the host Python suite (87 passed, 4 native-only cases skipped) and the dashboard production build.
- Linux LLVM 18 container (`make verify-native-container` to build the image, then `ctest` executed inside it): 37/37 ctest passed, including `cross_target_objects_and_rejections` — one JIR to both triples with distinct datalayouts, real ELF (`7f 45 4c 46`) versus real COFF (machine `0x8664`) bytes, `artifact_hash` equal to the SHA-256 of the actual content, and rejection of a cross-target `run` — plus the LLVM ORC toolchain and runtime ABI probe.
- Rust workspace in the container: 18 and 6 tests passed, `cargo fmt --all --check` clean, `cargo clippy --all-targets -- -D warnings` clean, and `jocky-agent doctor` reporting actual host, policy and collector state.
- PostgreSQL integration (`scripts/test_postgres.py` against PostgreSQL 17.6 with isolated schemas): 18 passed, covering every migration through `0007_execution_transport`, TLS enrollment/heartbeat/replay/wrong-identity under both DIRECT and TRUSTED_RELAY, evidence and audit.
- Targeted Sprint-2 Playwright acceptance (`tests/prototype/execution.spec.ts`, desktop project): PASS — three enrolled endpoints, both compiler targets, both transports, MEMORY/JIT and NATIVE/AOT provenance, separate artifact and manifest verification, and no browser errors.
- Prototype Playwright regressions from a freshly recreated stack: `tests/prototype/coherence.spec.ts` PASS three consecutive runs in isolation (each a full operator journey: three real agents, compile, three-target build, investigation, findings, graph, timeline, evidence and performance), and `tests/prototype/local-endpoint.spec.ts` PASS. Every coherence journey reached `SUCCESS` for all three child jobs; the persisted jobs carry `LLVM_ORC_JIT` with a real `worker_pid` and duration, one of them per journey carried over `TRUSTED_RELAY`, alongside a `NATIVE_AOT` job from the acceptance run.
- `docker compose --config` validation, generated-coverage `--check` and `git diff --check`: PASS.

Useful verification: `make verify-native-container` then an explicit `ctest` inside it; `.venv/bin/python scripts/test_postgres.py` with the dev Compose PostgreSQL up; `npx playwright test -c playwright.prototype.config.ts tests/prototype/execution.spec.ts`.

Known limitations: Windows target objects are emitted but cannot be linked or executed on this macOS host, so Windows remains a compilation-target claim only — **ENVIRONMENT DEPENDENT**. Certificate rotation and production OS credential storage remain open, so `SEC-02`/`AGT-03` are PARTIAL, and the endpoint state set beyond ONLINE/STALE/OFFLINE/WAITING_FOR_HEARTBEAT remains specified only (`AGT-04` PARTIAL). The relay is a byte pass-through, not a domain-fronting gateway, so `SAFE-11` is PARTIAL. cgroup hard limits are still unavailable.

## Terminal `jockey` entry point and LLVM 20+ triple compatibility — 2026-09-28

Status: **IMPLEMENTED and verified on LLVM 22.1.8 (Arch Linux)**. The pinned LLVM 18 branch of the new compatibility shim is **NOT TESTED** here.

- `scripts/jockey` is a POSIX `sh` dispatcher. A first argument naming a `.jky` file runs `jockyc run <file> --execution memory`; any other argument is passed through to `jockyc` unchanged. `JOCKYC` overrides the located binary. `make jockey-install` builds `jockyc` and symlinks the script into `~/.local/bin`. No compiler, runtime, agent or protocol behaviour changed.
- `native/compiler/include/jocky/llvm_compat.h` adds three inline shims (`triple_argument`, `set_module_triple`, `module_triple`) guarded by `LLVM_VERSION_MAJOR >= 20`. LLVM 20 moved `Module::getTargetTriple`/`setTargetTriple`, `TargetRegistry::lookupTarget` and `Target::createTargetMachine` from `StringRef`/`std::string` to `llvm::Triple`; the shim keeps one source tree building on both layouts. Six call sites in `src/backend.cpp` and `src/llvm_probe.cpp` were updated. Signatures were confirmed against the `release/18.x` headers, not assumed.
- `native/compiler/CMakeLists.txt` links the LLVM shared library when `LLVMConfig` reports `LLVM_LINK_LLVM_DYLIB`. Distributions that ship only `libLLVM.so` (Arch) provide no static component archives, so `llvm_map_components_to_libnames` alone failed to link. Component linking is unchanged when the static archives are present.

Executed checks, LLVM 22.1.8, `cmake -DBUILD_TESTING=ON -DCMAKE_BUILD_TYPE=Release`:

- `make jockey-install`: PASS. Builds `jockyc`, `jocky-worker`, and all four test executables with no warnings under `-Wall -Wextra -Wpedantic -Werror`.
- `ctest --test-dir build/native --output-on-failure`: **35/35 PASS**, including `LLVMBackend.*`, `LiteralPool.*`, `frontend_examples_and_goldens` and `compiler_rejects_missing_source`.
- `jockyc --self-test`: PASS (ORC toolchain and runtime ABI probe).
- `jockyc check examples/basic/system.jky` → PASS, 6 typed JIR instructions. `jockyc check examples/invalid/parse.jky` → `JOCKY E120`, exit 1.
- `jockey examples/basic/system.jky` and `cd /tmp && jockey hi.jky` → exit 0, fixture SHA-256 emitted. `jockey check <file>` passes through. `jockey examples/invalid/parse.jky` → exit 1.
- `python3 scripts/format_native.py --check` and `npx prettier --check README.md`: PASS.

Known limitations: the LLVM 18 path through `llvm_compat.h` compiles against signatures read from the `release/18.x` headers but was not executed — only LLVM 22 is installed on this host, so LLVM 18 CI remains the first real test of that branch. `jockey <file>` executes against the deterministic SIMULATED fixture collector; it is not endpoint evidence and no Agent host is involved. Passing a second `--execution` flag alongside a `.jky` path is rejected as a duplicate option rather than overridden.

## PS-coverage sprint 1 — Build Forge delivery — 2026-09-27

## PS-coverage sprint 1 — Build Forge delivery — 2026-09-27

Status: **IMPLEMENTED and verified within the bounded delivery scope below**.

- New persistent BuildRun and migration `0006_build_forge` reuse existing Compilation, Variant, object storage, outbox/audit and Ed25519 infrastructure. No compiler, Rust agent or protocol rewrite.
- `/forge` runs SOURCE → VALIDATE → JIR → DIVERSIFY → LLVM → BUILD → TEST → EQUIVALENCE → MANIFEST → READY. Source validation/JIR gates reuse an existing successful compilation. Native lowering/AOT/ORC fixture execution are bundled by the existing compiler; persisted timings explicitly identify gate wall time versus native-stage sums across candidate seeds.
- Default three (bounded 1–8) selected variants have actual object bytes, seeds, JIR/LLVM hashes, structural fingerprints, block/function/helper metrics, measured profiles and sizes. A bounded deterministic seed scan selects distinct structural templates and artifact hashes; insufficient diversity fails honestly. Same base seed/source/compiler/key reproduces artifact identities, while timestamps/timings differ.
- Equivalence VERIFIED means equal source/JIR/declared plan and normalized deterministic benign ORC fixture result; a supplied expected result hash can reject delivery. Fixture inputs carry simulation=true. This does not prove universal or native endpoint equivalence.
- Build manifests bind source/version, compilation, seed, target/mode, variant membership, actual hashes and fixture result in a separate `JOCKY:build:v1` Ed25519 domain. Verification checks signature, stored provenance and actual object bytes. Missing/tampered content cannot pass. Variant comparison only reports VERIFIED for delivery sets whose READY manifests and bytes still verify.
- Existing AES-256-GCM protected literal pools are surfaced and integration-tested with an ephemeral externally provided key: protected fixture build READY, plaintext marker absent from the actual object, missing key rejects compilation. Native tests additionally reject wrong keys and tampering. PS protected-configuration coverage remains PARTIAL because endpoint key provisioning/distribution is absent.
- Build Forge and Variant Explorer provide the repeatable delivery path, actual stage/status history, compact hash copy/full-value affordances, comparison and refresh persistence. Requirement Coverage and API/operator documentation describe these same capabilities and limits.

Executed checks:

- `make verify-foundation`: PASS, including generated contract/coverage/protobuf drift, formatting, Ruff/ESLint, mypy, workspace typecheck, Python tests, package builds and production build.
- Python Ruff and mypy: PASS (35 typed source files).
- Host Python suite: 86 passed, four native-only cases skipped; native Forge cases explicitly require a real LLVM compiler and are skipped on this macOS environment. All five native Forge tests were separately executed, not counted as passing skips.
- Compiler-bearing container, fresh isolated PostgreSQL schemas: five Build Forge tests PASS; nine existing distributed/migration/auth/TLS/evidence/audit tests PASS. Every schema migrates from empty through 0006. Final container tests used the image’s pinned runtime dependencies and an isolated pytest/httpx2 runner. A first combined attempt inherited product sandbox/compiler settings that contradicted two existing test assumptions; rerun used REAL/no-compiler settings for those regressions and REAL/native-compiler settings for Forge. The source-corruption test was corrected to insert invalid input rather than overwriting an append-only version; PostgreSQL protections remain intact.
- `make verify-native-container` and an uncached container `ctest`/compiler self-test: 35 C++/frontend tests PASS; ORC ABI probe PASS. No Rust source changed.
- Targeted Playwright Build Forge acceptance: two desktop/mobile tests PASS, actual CHECK/compile, three distinct artifacts/LLVM/structural identities, bounded equivalence, Ed25519/byte verification, comparison and refresh; no console/runtime errors or main-view destructive overflow.
- Generated contract/traceability checks and `git diff --check`: PASS.
- `make demo-up`, `make demo-check` and Compose config validation: PASS with PostgreSQL, API, gRPC, dashboard and three existing internal local-agent runtimes. Previously persisted identities and evidence are preserved.

Known limitations: only compiler-host memory-worker LLVM objects are delivered here; native worker packaging, cross-target compilation and fleet deployment are not gates. Fixture equivalence is bounded ORC execution of compiler-produced lowering after successful AOT emission; it is not execution of the emitted object on an endpoint. The API uses a bounded background task, not a crash-resuming queue: process interruption may leave a RUNNING record; repeat the build. Candidate scanning is bounded, so requests may fail when a program cannot yield enough distinct structural templates. Protected endpoint key distribution remains PARTIAL. No antivirus optimization/bypass is claimed.

Useful verification: `make verify-foundation`; `make verify-native-container`; `npx playwright test -c playwright.prototype.config.ts tests/prototype/forge.spec.ts`; `.venv/bin/python -m pytest services/control-plane/tests/test_forge.py` with an actual configured `JOCKY_COMPILER_PATH` (and optional isolated `JOCKY_TEST_DATABASE_URL`).

## Operator coherence and three real local agents — 2026-09-27

Status: **VERIFIED within the existing prototype capabilities**. This supersedes the single-slot local endpoint limit below. The existing internal fixed-command supervisor is reused in three isolated containers/state volumes, each enrolling its own Rust agent normally. ADMIN-only lifecycle APIs accept bounded slots 1–3; repeated start reuses enrollment and identity. No Docker socket, arbitrary execution API or Rust/protobuf change was introduced.

The authenticated header, Command Center operation flow, online-first inventory, spacious investigation wizard, compact variant comparison, focused/aggregated visual graph, separate immediate artifact/manifest verification drawers, platform-specific driver inventory, measured performance history and navigable Documentation now form one operator journey. Raw observations and evidence are preserved. New variant manifests retain actual compiler stage profiles and stored artifact byte size; no synthetic measurements are introduced. Investigation detail safely uses the newly persisted API response during cache refresh.

Observed actual Linux/aarch64 agents (version 0.1.0, simulation=false):

- LOCAL-LINUX-01: `1a590a8d-e7f8-487c-99f7-cc123dd8e56b`
- LOCAL-LINUX-02: `ae5bfd53-a8ee-4892-97f4-5da547811863`
- LOCAL-LINUX-03: `17c296b7-2ba1-4e10-8ae7-7d200365022d`

Executed verification:

- `make demo-up`: PASS, including PostgreSQL, API, authenticated gRPC, dashboard and three internal launcher containers. Native agent identities survived image recreation; no secrets are committed.
- `make verify-foundation`: PASS, including Ruff/Prettier, ESLint, mypy, workspace typecheck, production build, contracts/protobuf drift, packaging and **85 Python tests**.
- `.venv/bin/python scripts/test_postgres.py services/control-plane/tests/test_local_agent.py services/control-plane/tests/test_operator_product.py` with `JOCKY_TEST_DATABASE_URL` pointing to a temporary fresh PostgreSQL 17.6 instance: **25 passed**. The disposable container was removed. This includes persistence, tenant/RBAC, real TLS, evidence, hunt lifecycle, slot idempotency and the newest-resource inventory window. An initial attempt used the unpublished product database port and failed; it is not counted as passing.
- `make verify-agent-container`: PASS; locked build, format, **24 Rust tests** (18 agent + 6 transport), clippy and doctor. No Rust source or transport contract changed.
- `npx playwright test -c playwright.prototype.config.ts`: **8 passed**, desktop/mobile. Actual browser-only three-agent enrollment/heartbeat, independently selected jobs with three SUCCESS outcomes, measured variant metadata, refresh/idempotency, stop/90-second heartbeat expiry/restart, external native enrollment, artifact byte recomputation, separate manifest provenance/signature, driver inventory, real benchmarks, all **19** documentation programs compiled through LLVM, primary routes and viewport overflow checks passed. No browser runtime/console errors occurred.
- `npx playwright test -c playwright.prototype.config.ts tests/prototype/coherence.spec.ts`: **4 passed** after the final contextual breadcrumb change. Compiler Explorer selects the just-created compilation; the variant link opens that exact record. Frontend lint/typecheck/production build also passed after this change.
- `make demo-check`: PASS for existing compiler/fixture/evidence/audit invariants. This command checks the labelled sandbox scenario; the browser tests separately prove real local execution.
- `docker compose --env-file .env -f infra/docker/prototype.compose.yaml config --quiet` and `git diff --check`: PASS. No launcher publishes a host port or mounts a Docker socket. Tracked/non-ignored files contain zero matches for locally generated secret values.
- Desktop screenshots were inspected at 1366 × 768 for Command Center and wizard spacing.

Acceptance caught and fixed an invalid uppercase documentation severity, a stale comparison-label assertion and a race between the persisted start response and the refreshed hunt list. The final runs above passed after fixes. Bounded inventories now return their newest window in chronological order (500 records by default; cases retain the requested 100/default, 500 maximum), so old records cannot bury current operations. Direct detail APIs preserve access to historical records; full fleet pagination remains outside this prototype.

Known limits: semantic-equivalence evaluation is not exposed for persisted variant comparisons (NOT TESTED); old variants lack stored profiles/byte size. Total wall-clock build latency, CPU/memory telemetry and collector durations are not reported. Rich DSL filters/correlation compile but exceed the bounded remote inventory bridge. Findings used for the walkthrough include explicitly labelled backend sandbox observations; ordinary Linux inventory does not manufacture suspicious findings. Physical Windows live acceptance remains unverified. Local agents collect their own containers, not the macOS host. Each slot belongs to its first enrolling organization, and restart preserves identity but requires an explicit start.

## One-click local endpoint — 2026-09-27 (macOS development host)

Status: **VERIFIED** for the local Linux container workflow. `make demo-up` now builds the existing Rust agent into the bundled worker/runtime and starts an internal local-agent-launcher. Its fixed-command supervisor initializes, enrolls and connects exactly one real agent using persistent `/endpoint/local-agent-1` state. No Rust protocol change or Docker socket was introduced. The launcher is unpublished on the host, authenticated with a generated internal credential, and runs as UID 10001. Local API start/status/stop require ADMIN and enforce organization ownership. Repeated start reuses active operation/enrollment/identity; stop preserves history. ONLINE is derived only from an authenticated heartbeat newer than the current connect process, never from process launch success.

Executed verification:

- `make demo-up`: PASS; PostgreSQL, API, gRPC, dashboard and internal launcher healthy. Rust workspace was built with the existing locked source; no Rust code was changed.
- `make demo-prepare`, `make demo-check`: PASS; existing compiler/fixture/evidence/audit checks preserved.
- `make verify-foundation`: PASS, including frontend lint, strict mypy, dashboard/workspace typecheck, production build, contract/protobuf checks, packaging and **83 Python tests**. Four new targeted tests cover fixed-command/internal authentication, missing-agent failure, persistent identity/idempotency, ADMIN/tenant boundaries, unavailable runtime and heartbeat-based status. An initial formatting gate failure was corrected before the successful aggregate.
- `npx playwright test -c playwright.prototype.config.ts`: **4 passed** across desktop/mobile, including browser-only local startup with real TLS enrollment/heartbeat, refresh, duplicate prevention, actual stop plus 90-second expiry on desktop, same-identity restart and preserved artifact history. The launcher container was also restarted before the final suite, retaining credentials/identity. Existing external native-agent enrollment, execution and full operator journey still passed. No runtime/console errors were observed.
- `docker compose --env-file .env -f infra/docker/prototype.compose.yaml config --quiet`: PASS. Launcher has no published host port and no service mounts a Docker socket.
- `git diff --check`: PASS.

Observed real local endpoint: **LOCAL-LINUX-01**, Linux **aarch64**, agent **0.1.0**, `simulation=false`, endpoint ID `1a590a8d-e7f8-487c-99f7-cc123dd8e56b`. Repeated starts and agent/launcher restarts reused the identity and enrollment. The first browser attempt revealed a missing dashboard proxy allowlist entry; it was fixed and the actual final suite passed.

Limitations: one local endpoint/owning organization per launcher; this Linux container collects its own environment, not the macOS host. Runtime restart leaves the agent STOPPED until Start is requested. External machines still require native agent/worker installation and a correctly addressed trusted TLS certificate. Consumed enrollment with missing local credentials is rejected rather than silently creating a duplicate endpoint; restore the persistent state in that corruption case. Physical Windows acceptance remains outside this change.

## Operator product workflow — 2026-09-27 (macOS development host)

Status: **VERIFIED within the existing prototype capabilities**. This entry supersedes earlier product UI descriptions; it does not declare final Phase 4 or physical Windows acceptance complete.

Implemented endpoint enrollment/status and detail, persisted investigation wizard/detail, analyst findings, interactive timeline, driver inventory, measured compiler/variant observability, graph controls, language documentation and Workbench example transfer. Existing compiler, Rust agent, evidence design and domain models were reused. Small backend additions provide tenant/admin-scoped enrollment status and public CA download; unavailable artifact content retains its expected hash while remaining unverified. The existing prototype Compose stack now runs the real gRPC control service.

Executed verification:

- `make verify-foundation`: PASS, including Ruff/Prettier, ESLint, mypy, workspace typecheck, **79 pytest tests**, generated contract/protobuf drift checks, Python packaging and dashboard production build. Initial sandbox run passed 78 tests but denied the TLS socket bind; the unchanged aggregate passed with local socket permission.
- `.venv/bin/python scripts/test_postgres.py services/control-plane/tests/test_operator_product.py`: **19 passed** against a temporary fresh PostgreSQL 17.6 container. Fresh schemas/migrations, tenant/RBAC, real TLS, replay, hunt isolation/cancellation, evidence tampering/sealing, timeline and enrollment/content regressions passed. The temporary container was removed. An earlier attempt used an unpublished host port and failed to connect; it was not counted as passing.
- `make demo-up`, `make demo-prepare`, `make demo-check`: PASS. PostgreSQL, FastAPI, gRPC agent control and dashboard healthy; persisted sandbox compiler/evidence/audit invariants passed.
- `npx playwright test -c playwright.prototype.config.ts`: **2 passed**, desktop and mobile. Actual one-time enrollment, authenticated Rust-agent heartbeat, native compilation/variants, successful real Linux agent job and persisted artifact verification; findings/graph/timeline/driver observations retain sandbox provenance. All five language examples passed actual LLVM generation. Primary routes, empty editor, documentation transfer, zero console/runtime errors and viewport overflow checks passed.
- `git diff --check`: PASS. Focused regression coverage verifies enrollment waits for its bound heartbeat and unavailable content cannot report valid integrity; browser coverage preserves login redirect to `/` and checks all primary routes.

Remaining limitations: physical Windows execution is unverified; remote execution is the existing bounded inventory bridge, not the full rich DSL; CPU/memory/collector duration/dispatch metrics absent from contracts remain Not measured. A browser cannot launch host containers; exact native-agent instructions and the existing container runtime path are provided. Driver risk remains UNKNOWN without supporting metadata. No synthetic state, hashes, timings or frontend jobs were introduced. Broader final-build capabilities remain outside this product pass.

## Persistent demo scenario compatibility — 2026-09-21 (macOS development host)

Status: **VERIFIED**. `make demo-prepare` previously reused an older persisted
`JOCKY_VIDEO_V1_READY` case whose observations predated the fixed `source_time`
contract, then failed the current verifier with an empty assertion message. The
prepared-scenario marker is now V2 across the loader, preparation checker, and
dashboard consumers. Existing isolated demo data is preserved; it is no longer
mistaken for the current scenario, and preparation creates a current case.

- `make demo-up`: PASS; native LLVM/control-plane and dashboard images rebuilt,
  and PostgreSQL, control plane, and dashboard reported healthy.
- `make demo-prepare`: PASS against the existing `jocky-video` volume, including
  real compilation, three distinct artifact hashes, simulated PARTIAL outcomes,
  evidence verification, audit verification, and repeat loading.
- `make demo-check`: PASS for dashboard/control-plane health and all prepared
  scenario invariants.
- Focused demo tests: 3 passed with two existing upstream deprecation warnings.
- Changed Python Ruff lint/format and dashboard TypeScript checks: PASS.
- `make verify-foundation`: PASS with 77 Python tests (two existing upstream
  warnings), formatting, lint, typing, generated-contract/protobuf drift checks,
  Python package builds, and the 23-page dashboard production build. The first
  sandboxed attempt reached 76 passed and one local gRPC bind denial; the full
  rerun with loopback socket permission passed.
- macOS is the development host only; no endpoint collector support claim is
  added by this verification.

## Prompt B recording stabilization - 2026-09-21 (Windows)

Current acceptance: **READY within the documented recording scope**. This entry supersedes
historical claims below about a currently running stack on another host.
Base commit: `232eb3d4b1276bc942ade8ebefa9efd774fe6b37`.

Scope: existing recording path only. Persistent Judge Mode now remembers its
position, follows actual screens, gates navigation during transitions, and calls
the existing seed/restore endpoint for Restart Demo. Workbench exposes persisted
compilation of the prepared source. Fixture source times are fixed at
2026-09-20T10:00:00Z; collection/signing/ingestion times remain actual. The critical
checker verifies job/endpoint/variant/finding/graph/timeline relationships and
requires all three evidence objects/manifests. Login commits its token before
responding: repeated immediate seed calls exposed a real response/commit race.

Validation on Windows / Docker Desktop Linux containers:

- Clean `make demo-up`: PASS, real LLVM native image and fresh PostgreSQL/object
  volumes; `make demo-down` and subsequent `make demo-up`: PASS, data retained.
- `make demo-prepare`, `make demo-reset`, `make demo-check`: PASS. The checker
  covers dashboard, control plane, actual compiler invocation, embedded fixture
  service, hunt availability and real evidence verification; Redis/MinIO/gRPC
  are deliberately not required by this existing simulated recording stack.
- Python full suite: 75 passed, one Windows cp1252 documentation-decoding failure.
  The unchanged failing test passed with `python -X utf8`; use UTF-8 on Windows.
  After the login fix, focused tests passed: 3 demo/auth and 9 distributed checks,
  including a new token-durability regression. All 77 distinct current tests have
  passing evidence across the full run and targeted corrective reruns. Two
  upstream Starlette/AnyIO deprecation warnings remain.
- `npm.cmd run lint`: PASS; changed navigation/layout/test files rechecked after
  fixes. Workspace `npm.cmd run typecheck`: PASS. `npm.cmd run build`: PASS,
  23 generated pages. Final image production build also passed.
- `npx.cmd playwright test -c playwright.config.ts`: 14 passed, desktop/mobile.
- Prototype rehearsal: desktop PASS in the final combined run; affected mobile
  PASS in `npx.cmd playwright test -c playwright.prototype.config.ts
--project=video-mobile` (1 passed). Both validate actual compiler/evidence APIs,
  guided navigation/reload, zero runtime/console errors and no horizontal overflow.
  The mobile blocker was replay-triggered API request bursts: the demo now opens
  the event feed only on Live Investigation and batches invalidations. Targeted
  lint/typecheck and the affected production image build passed afterward.
  Final mobile evidence: `.cache/video-mobile-final.log`.
- Changed Python Ruff lint/format and frontend Prettier checks: PASS.
- `make verify-foundation`: attempted once; contract/schema/coverage checks passed,
  then blocked by pre-existing `.venv/bin/ruff` POSIX path on Windows. This is not
  recorded as a passing aggregate. Individual submission checks above replace no
  test assertion. Native/Rust final-production suites were not expanded or rerun.
- Intermediate defects retained in the record: guide TypeScript bounds fixed;
  missing favicon fixed; rapid mobile navigation gated; icon moved to public
  metadata because the framework metadata loader mishandles the apostrophe in
  this workspace's Windows path. No test assertion was weakened.

Evidence logs/screenshots are ignored under `.cache/video-*` and
`.cache/prototype-*`. Login traces/video remain disabled. The recording stack
is `jocky-video`, http://localhost:13000/judge; sign in before the take.
See VIDEO_RECORDING_GUIDE.md, PROTOTYPE_STATUS.md and PROTOTYPE_FREEZE.md.

## Idea-submission prototype freeze — 2026-09-21

**READY.** Closure required no further application changes. `make test-e2e`
passed 14 tests; the dedicated desktop/mobile prototype walkthrough passed 2.
`make verify-foundation` passed with 76 Python tests (2 upstream warnings), all
format/lint/type/contract/protobuf/package checks, and a 23-page production build.
Fresh preparation passed in `jocky-video-closure` with separate PostgreSQL/evidence
volumes: actual compilation and three hashes, two simulated successes plus one
simulated failure, PARTIAL hunt, derived finding/graph, signed manifests, stored
byte verification and audit chain. All three demo services are healthy.

No final-production features were added. The exact REAL / MEASURED / SIMULATED /
DEFERRED boundary and recording commands are in PROTOTYPE_STATUS.md and DEMO_FLOW.md.

## Idea-submission video prototype — 2026-09-20

**READY within the documented simulated recording scope.** This supersedes the
old foundation-only Judge Mode / DEMO_FLOW descriptions, not the Phase 4 platform
limitations below. See [PROTOTYPE_STATUS.md](PROTOTYPE_STATUS.md) and
[DEMO_FLOW.md](DEMO_FLOW.md).

- Isolated PostgreSQL/API/dashboard DEMO stack built and started healthy on
  ports 18080/13000. Fresh database migrations and actual compiler preparation ran.
- `make verify-foundation` passed: 76 Python tests, format/lint, contracts and
  coverage drift, Python/TypeScript typing, protobuf, package and Next.js builds.
- `make demo-prepare` passed: real compilation, three actual distinct artifact
  hashes, three simulated endpoint outcomes with PARTIAL aggregate, persisted
  correlation, signed evidence/byte rehashing, audit chain and repeat loading.
- Existing browser regression suite: 14 passed (desktop/mobile). The obsolete
  Judge Mode expectation now checks explicit REAL/DEMO separation.
- Dedicated prototype browser suite: 2 passed (desktop/mobile), exercising the
  recording flow, actual compiler, evidence verification, benchmark and refresh.
- No production or Windows live execution claim was added. Driver risk and
  endpoint outcomes are explicit backend fixtures. Measured compiler samples
  are real timings of the labeled compiler fixture, not fleet benchmarks.

The reference video stack needs no Redis/MinIO/gRPC service because it does not
execute endpoint jobs. The existing full REAL Compose workflow is unchanged.

## PHASE 4 STATUS — COMPLETE

Phase 4 is **COMPLETE** within the documented prototype acceptance boundary.
Required control-plane, agent, multi-endpoint, evidence, dashboard, and live
event flows pass; remaining items are explicit noncritical/platform
limitations, not untracked TODOs.

Final verification on 2026-09-20:

- Python: full current suite **74 passed**, 2 upstream deprecation warnings.
- PostgreSQL: fresh disposable-schema integration suite **17 passed**, 2
  upstream deprecation warnings.
- Rust: Docker Rust 1.90 `fmt`, `cargo check --locked --workspace`, and
  workspace tests **18 unit + 6 CLI = 24 passed**.
- Native: Docker LLVM 18 configure/build, CTest, and `jockyc --self-test`
  passed.
- Dashboard: all workspace typechecks and Next.js production build passed;
  **23 pages** generated.
- Browser E2E: Playwright Chromium desktop/mobile **14 passed**.
- Docker: Compose config passed; PostgreSQL, Redis, MinIO, API, gRPC control,
  scheduler, and dashboard built/started healthy. `/health/live`,
  `/health/ready`, and dashboard HTTP smoke passed.
- Live dashboard event smoke: authenticated proxy login -> persisted case POST
  -> `case.created` SSE receipt -> persisted cases refetch passed.
- REAL distributed evidence remains recorded in the remote execution section
  below: enrollment, heartbeat, dispatch, worker execution, observation,
  artifact, manifest, completion, reconnect, partial success, and audit checks.

Known limitations: bounded inventory collectors only, MONITORED budgets only,
Linux live endpoint acceptance only, Windows live execution and certificate
rotation unavailable, no external audit checkpoint, local content-addressed
storage rather than MinIO authority, no PDF report, and no multi-agent load or
fault trial. These limitations are documented as LIMITATION in the final gap
matrix and do not conceal failed required prototype checks.

## Real Rust remote execution — 2026-09-20

Status: **IMPLEMENTED + VERIFIED** for the supported REAL bounded-inventory
execution path on Ubuntu 24.04 arm64 in Docker. This supersedes the earlier
Phase 4 stabilization note that described the Rust bridge as unavailable.

The verified path is:

`control plane -> mTLS-enrolled Rust Agent -> signed job admission -> streamed
artifact retrieval and SHA-256 verification -> LLVM worker -> Rust system
collector -> signed observation/artifact/manifest/progress frames -> durable
PostgreSQL state`.

Fresh live evidence:

- The current Rust agent passed `cargo fmt --all -- --check`, locked workspace
  tests (**18 unit + 6 CLI = 24 Rust tests**), and warnings-denied Clippy in the
  Rust 1.90 Docker toolchain. The durable remote replay test is
  `remote_frame_replays_without_reclaiming_or_rerunning_job`.
- The real agent enrolled through the existing `Enroll` RPC, reused its
  persisted identity across control-plane restart, and reached ONLINE through
  the existing mTLS `Exchange` stream. The initial stream deadlock and the
  memory-object build-mode mismatch were fixed in this checkpoint.
- REAL hunt `6fef8a00-2796-437f-afe5-cb628f7110c3`, job
  `34b9b086-edf5-4093-89ab-5d72faf9db5b`: terminal `SUCCESS`, one persisted
  `simulation=false` system observation, one artifact, one signed evidence
  manifest, `bytes_read=1839`, and 24 durable transport receipts. The agent
  spool was empty after acknowledgement.
- Reconnecting the same enrolled agent left exactly one observation for that
  job, proving the completed job was not rerun.
- A live cancellation request reached `CANCEL_REQUESTED`; when execution had
  already completed, the state machine accepted the late `SUCCESS` rather than
  leaving the job stuck. Active cancellation remains fail-closed through the
  Rust supervisor and signed cancellation tests.
- The corrected control-plane/native images built with the current source;
  native CTest/self-test and the focused Python distributed/Phase 4 tests pass.

Known verified boundary: the bridge currently admits bounded inventory
collectors with empty options and `MONITORED` budgets. It rejects strict
enforcement and richer JOCKY operations. Windows live execution, certificate
rotation, multi-agent fault/load acceptance, and external audit checkpoints
remain outside this checkpoint.

## Multi-endpoint hunt orchestration — 2026-09-20

Status: **IMPLEMENTED + VERIFIED** for endpoint-scoped scheduling and aggregate
state semantics.

`test_multi_endpoint_hunt_isolates_variants_failures_retries_and_evidence` in
`services/control-plane/tests/test_phase4.py` proves one logical compilation
creates independent jobs for three endpoints: A receives a memory Variant A,
B receives a native Variant B and fails at runtime, and C receives a distinct
memory Variant C. A and C evidence rows survive, B gets one endpoint-scoped
retry, no successful endpoint is retried, and the Hunt becomes `PARTIAL`.
The same test verifies shared source/JIR/plan provenance and endpoint-specific
variant/mode provenance.

Additional targeted coverage proves recorded compatibility failure marks only
that endpoint `INCOMPATIBLE`, and a variant build failure for endpoint A leaves
endpoint B and C queued with valid variants. The focused distributed and Phase
4 suites pass **16/16** in both the local SQLite fixture and the PostgreSQL
integration runner (`scripts/test_postgres.py`).

Cancellation and retry remain endpoint/job-scoped through the existing state
machine; active cancellation preserves already-persisted evidence. Broader
multi-agent load/fault acceptance remains open.

## Backend contract closure — 2026-09-20

| Area               | Classification | Evidence                                                                                                                                                   |
| ------------------ | -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Auth / RBAC        | GREEN          | ADMIN/ANALYST/VIEWER, unauthenticated rejection, tenant isolation, viewer mutation denial, and legacy `/api/v1/compilations` auth gates pass.              |
| Evidence           | GREEN          | Manifest artifact membership, stored-byte rehashing, tamper rejection, sealed-job late evidence rejection, and audit mutation detection pass.              |
| Correlation        | GREEN          | Persisted observations produce all eight required relationships and the unsigned-process/external-connection finding.                                      |
| Timeline           | GREEN          | Persisted timeline records support endpoint, collector, severity, type, and timezone-aware start/end filters.                                              |
| Reports            | GREEN          | POST generation persists SUCCESS status/artifact, GET status returns metadata, download returns stored JSON, and generation is audited.                    |
| Benchmarks         | GREEN          | POST creates a persisted simulated compiler-fixture run, samples/status/events persist, and GET lists runs.                                                |
| Compatibility runs | GREEN          | POST/GET persistence is tested and an API-recorded correctness FAIL is consumed by endpoint-specific hunt admission.                                       |
| DEMO fixtures      | PARTIAL        | Backend loader uses normal persisted contracts with `simulation=true` and labels; direct loader acceptance is not independently tested in this checkpoint. |

The focused backend contract suite passes **17/17** locally and **17/17**
against PostgreSQL. Two existing Starlette/httpx/AnyIO deprecation warnings
remain. DEMO is the only listed area left PARTIAL; no UI-only synthetic records
are claimed.

## Dashboard integration and live events — 2026-09-20

Status: **IMPLEMENTED + VERIFIED** for the authenticated persisted-resource
surface and committed SSE event refresh path.

- Dashboard typecheck and production build pass; Next.js generated 23 pages,
  including persisted Scripts / Versions.
- The existing HttpOnly same-site session proxy forwards bearer authentication
  to domain routes, clears invalid sessions on 401, and prompts/redirects to
  login without an auth retry loop. ADMIN/ANALYST write controls remain hidden
  for VIEWER sessions.
- `useControlEvents` consumes the existing `/api/control/domain/events` SSE
  proxy, preserves durable event IDs across reconnects, ignores duplicate or
  out-of-order events, and invalidates persisted case/resource/child queries.
  Expired SSE sessions now emit `auth.expired`, clear the cookie, and redirect
  through the existing session flow.
- Live smoke through the production dashboard on port 3001: authenticated
  proxy login -> POST persisted case -> received `case.created` SSE event ->
  GET cases contained the same case. No frontend-generated progress or result
  store was used.
- Scripts/versions and job-scoped evidence manifests now use existing
  persisted API routes. Stale unavailable execution metrics and claims were
  removed from the platform overview; compiler fixture text remains explicitly
  labeled as a fixture.

## Phase 4 stabilization checkpoint — 2026-09-14

Scope frozen at the operator's request. This section supersedes older control-plane availability claims below. Changes remain in the working tree; no commit, push, or GitHub CI success is claimed. Preserve this architecture and continue from these files rather than restarting implementation.

### VERIFIED COMPLETE

These are scoped backend checks, **not completion of the distributed endpoint product**:

- PostgreSQL UUID models and Alembic migrations for the requested resources, sessions, transactional event outbox, and durable agent receipts. PostgreSQL rejects modification/deletion of protected evidence/audit records. Tests use disposable, uniquely named schemas; only those test schemas are removed.
- Prototype password sessions and ADMIN/ANALYST/VIEWER enforcement: authenticated domain APIs, viewer write denial, tenant-scoped lookup/list isolation. Configured legacy compiler/verifier routes also require sessions. Live Compose login, authenticated reads, logout, unauthenticated denial, and audit verification passed.
- Server-side TLS enrollment and mTLS exchange: one-time enrollment token, ECDSA transport certificate plus bound Ed25519 evidence key, heartbeat, durable exact-frame replay receipts, wrong identity rejection. The same protocol test covers job dispatch/reconnect, assigned-artifact byte retrieval, progress, manifest-gated completion, and cancellation acknowledgement using an explicit protocol fixture.
- Persisted observation hashing, manifest signature/build/agent provenance checks, sealing evidence after manifest submission, actual stored-artifact hash recomputation, tamper detection, and audit-chain checking. Audit has no external checkpoint and does not claim rollback protection.
- Backend correlation for an explicitly unsigned process and external connection, evidence-linked graph records, timeline filtering; report JSON bytes/metadata and verification; SSE committed-event cursor/resumption; retry identity and partial/cancellation state transitions passed focused tests.
- Current Python suite, PostgreSQL suite, backend typing/imports, generated contract/binding consistency, dashboard types, and production dashboard build pass as recorded below.

### IMPLEMENTED BUT NOT FULLY VERIFIED

| Component                                          | Actual completion boundary                                                                                                                                                                                                                                                                                                                                   |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Dashboard authentication/resource views            | Login page, HttpOnly same-site cookie proxy, resource tables/details, case/script/hunt/report actions exist; types/build and HTTP page smoke pass. Browser-interactive login, writes, and role-sensitive rendering were **not** acceptance-tested in this checkpoint. Some tools remain API-only; graph is a JSON relationship view, not a graphical canvas. |
| SSE/live events                                    | Backend durable outbox/cursor tests pass. Browser EventSource view exists; reconnect/session-expiry behavior across real browsers and long-running deployment is not fully tested.                                                                                                                                                                           |
| Multi-endpoint hunt dispatch/retry/partial-success | IMPLEMENTED + VERIFIED for three-endpoint endpoint-scoped orchestration, per-job retry, compatibility/build isolation, partial success, and provenance tests. Multi-agent load/fault acceptance remains open.                                                                                                                                                |
| Correlation/timeline                               | Backend fixture acceptance passes. Live Rust evidence integration, full relationship-field coverage, PID reuse edge cases, and large-case performance remain unverified.                                                                                                                                                                                     |
| Reports                                            | GREEN for backend JSON generation/status/download/audit and evidence verification; PDF and browser acceptance are absent.                                                                                                                                                                                                                                    |
| Benchmarks                                         | GREEN for the persisted simulated compiler-fixture lifecycle, samples, status, and events; no remote performance claim.                                                                                                                                                                                                                                      |
| Compatibility runs                                 | GREEN for POST/GET persistence and hunt admission consuming recorded endpoint correctness; automated security-tool execution remains outside scope.                                                                                                                                                                                                          |
| Evidence verification                              | Backend positive/tamper tests pass. Not verified with evidence emitted by a remotely connected Rust agent. Uploaded artifact hashes are not themselves independent producer signatures.                                                                                                                                                                      |
| RBAC/tenant isolation                              | Prototype API boundaries tested, not a production security review. Full endpoint lifecycle, abuse/rate limiting, and multi-operator concurrency need further acceptance.                                                                                                                                                                                     |
| Native compilation/variants and DEMO loader        | Native compiler image self-test passes. Durable native-build API and backend DEMO loader exist, but their full deployed workflow was not exercised at checkpoint. Never substitute compiler fixture output for REAL endpoint execution.                                                                                                                      |

### NOT YET IMPLEMENTED

- Certificate renewal/rotation workflow, production deployment hardening, externally anchored audit checkpoints, S3/MinIO object-store adapter/reconciliation, PDF reports, automated compatibility execution, and full cross-platform distributed acceptance.
- Existing object storage is a content-addressed local filesystem volume with PostgreSQL metadata. MinIO and Redis run in Compose but are not used as authoritative evidence storage or the job queue; PostgreSQL is the queue of record.

### KNOWN ISSUES

- No known blocker in the critical checks below. Two upstream Starlette/httpx/AnyIO deprecation warnings remain.
- Domain list APIs are bounded but do not yet implement complete cursor pagination. Compilation requests are synchronous and commit stages individually; interrupted build recovery and long-running/concurrent scheduling need acceptance.
- `/api/variants/{id}/manifest` currently returns the variant resource wrapper including its manifest. Legacy `/api/v1/endpoints` and coverage/Judge text still describe the standalone/foundation scope; use authenticated `/api/endpoints` and this checkpoint for current backend status. Coverage catalog/older architecture sections require later reconciliation; do not inflate their end-to-end status.
- If `JOCKY_DATABASE_URL` is unset, only legacy local development utilities are exposed, without domain authentication. Compose configures the database; do not expose the unconfigured utility mode remotely.
- Compose image smoke used the running image build from this work. Some final source-only fixes/tests postdate that build; rebuild with `docker compose up -d --build --wait` before treating containers as identical to the final working tree. Dashboard, gRPC, and scheduler services have no dedicated Compose healthcheck; “running” is not a healthcheck result.
- A failed early PostgreSQL test used port 5432 instead of Compose's 15432 and printed a generated local password in its traceback. That password was rotated in PostgreSQL and ignored `.env`; application services were recreated and authenticated smoke passed. Test runner now defaults to 15432 and short tracebacks. No secrets were intentionally added to tracked config. Current generated credential values were scanned against tracked and non-ignored files: zero matches; `.env` is ignored and untracked. CI's password is an explicit disposable test fixture.
- Broader browser E2E, Rust/native acceptance suites, DEMO loading, benchmark/compatibility acceptance, and GitHub-hosted CI were intentionally not rerun after the scope-freeze instruction.

### Exact important checks and results

Windows PowerShell, repository `C:\SIH'26\JOCKEY`, Python 3.12 environment, Docker Desktop Linux containers/PostgreSQL 17.6:

| Command/check                                                                          | Result                                                                                                                                                                                 |
| -------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.venv/Scripts/python.exe -m pytest -q --tb=short --basetemp=.cache/pytest-checkpoint` | **66 passed**, 2 deprecation warnings, 32.15 s                                                                                                                                         |
| `.venv/Scripts/python.exe scripts/test_postgres.py`                                    | **9 passed**, 2 warnings, 28.01 s; isolated real PostgreSQL schemas                                                                                                                    |
| `test_grpc_tls_enrollment_heartbeat_replay_and_wrong_identity` in both suites above    | **Passed**, real TLS/mTLS sockets, including dispatch/reconnect/artifact/completion/cancel protocol checks; fixture client, not Rust                                                   |
| `.venv/Scripts/mypy.exe`                                                               | **Passed**, 32 source files; imports also exercised by pytest and live service                                                                                                         |
| `.venv/Scripts/ruff.exe check .`                                                       | **Passed**                                                                                                                                                                             |
| `.venv/Scripts/python.exe scripts/generate_contracts.py --check`                       | **Passed**                                                                                                                                                                             |
| `node scripts/generate-types.mjs --check`                                              | **Passed**                                                                                                                                                                             |
| `.venv/Scripts/python.exe scripts/generate_agent_python.py --check`                    | **Passed**                                                                                                                                                                             |
| `npm.cmd run typecheck`                                                                | **Passed**, all four workspaces                                                                                                                                                        |
| `npm.cmd run build`                                                                    | **Passed**, Next.js 16.3.5, 22 generated pages                                                                                                                                         |
| `docker compose config --quiet`                                                        | **Passed**                                                                                                                                                                             |
| `docker compose ps --format json`                                                      | Seven running services; PostgreSQL, Redis, MinIO, API reported healthy; other three have no dedicated healthcheck                                                                      |
| `docker compose exec -T control-plane /usr/local/bin/jockyc --self-test`               | **PASS: LLVM ORC toolchain and runtime ABI probe**                                                                                                                                     |
| Inline local HTTP/SQL smoke (credentials read from ignored `.env`, never printed)      | `/health/live`, `/health/ready` 200; unauthenticated `/api/cases` 401; login/me/cases/logout passed; audit integrity true; dashboard `/login`, `/workbench`, `/compiler`, `/cases` 200 |

### Inspect first at handoff

1. `AGENTS.md`, this checkpoint, `docs/API.md`, `docs/ARCHITECTURE.md`, `docs/DEFINITION_OF_DONE.md`, `docs/SECURITY_MODEL.md`.
2. `services/control-plane/src/jocky_control_plane/{models,api,security,builds,hunts,transport,pki,ingestion,investigation,reporting,scheduler,demo}.py`; `services/control-plane/migrations/versions/`; `services/control-plane/tests/test_distributed.py`.
3. `proto/jocky/v1/agent.proto`, `scripts/generate_agent_python.py`, `packages/contracts/src/jocky_contracts/control.py`, generated contracts/bindings.
4. `apps/dashboard/src/components/control-resources.tsx`, `apps/dashboard/src/app/login/page.tsx`, `apps/dashboard/src/app/api/control/[...path]/route.ts`, existing `compiler-workbench.tsx`.
5. `compose.yaml`, `infra/docker/compose.yaml`, `infra/docker/control-plane.Dockerfile`, `scripts/configure_local.py`, `scripts/test_postgres.py`, `.github/workflows/ci.yml`.
6. Before any future Rust integration: `services/agent/src/{identity,model}.rs`, existing supervisor/spool/worker code, and `native/runtime/include/jocky/runtime.h`. Preserve their trust boundaries; do not silently reinterpret standalone collector jobs as compiler jobs.

## Endpoint Agent delivery — 2026-09-14

Status: **IMPLEMENTED and acceptance-tested for local standalone Ubuntu/WSL collection; Windows is compile-checked but not live-verified; distributed endpoint operation remains incomplete.**

The Rust Agent now creates a stable Ed25519 endpoint identity and separate local-development job authority, persists bounded configuration, cryptographically verifies canonical signed jobs, validates audience/status/expiry/skew/nonce/capability/budget, and stores replay receipts durably in SQLite. Accepted collector jobs run in a dedicated child process with a one-worker lock, monotonic timeout/cancellation, bounded pipes and result/file/read limits. Each real record is normalized into an RFC 8785/SHA-256 `Observation` with endpoint/job/case/collector/time/platform provenance and `simulation=false`; ordered manifests are signed by the endpoint identity. AES-256-GCM spool records survive restart and are acknowledged only after durable local export.

Real read-only adapters exist for system, users/sessions, processes, interfaces/connections/routes, file metadata/hash, services/startup, events, software and drivers/modules on Linux and Windows. Linux uses procfs/sysfs plus fixed read-only utilities; Windows uses fixed non-interactive PowerShell/CIM/NetTCPIP queries. Driver risk is a bounded source/version/hash adapter interface and never performs remediation or exploitation. YARA, Volatility 3 and osquery availability is detected; absent tools report `UNAVAILABLE`, while execution remains input-gated. The CLI provides `init`, `doctor`, `collectors`, `collect`, signed `fixture-job`/`run`, heartbeat, metrics, cancellation and encrypted spool inspection/export.

### Agent verification evidence

- Rust 1.90.0 on Ubuntu 24.04.4 WSL2: `cargo test --locked --workspace` passed **23/23** tests. Coverage includes stable/tamper-resistant identity state, canonical evidence tamper detection, normalized journal source time, Linux CPU/RSS sampling, signed/expired/malformed/replayed jobs, inaccessible/denied/empty file paths, hard file/read/result budgets, encrypted spool restart/ack and missing-key denial, child timeout/crash, cancellation, process reconnect, and real Linux system/process/connection CLI execution.
- `cargo fmt --all -- --check`, `cargo build --locked --workspace`, and warnings-denied `cargo clippy --locked --workspace --all-targets` passed.
- `cargo check --locked --workspace --target x86_64-pc-windows-gnu` passed after installing the Windows GNU standard library and MinGW compiler. This verifies Windows code compilation only; no Windows endpoint was available for execution tests.
- Live standalone WSL runs produced actual Ubuntu system metadata, process rows, TCP/UDP rows including PID ownership, and IPv4/IPv6 interface addresses. Every observation reported `simulation=false`; results included integrity hashes and signed manifests. No records were hardcoded.
- Targeted Pydantic contracts passed **25/25** tests; the full Python/integration suite passed **57/57**. Generated JSON Schema, TypeScript and requirement traceability are drift-free; Ruff and strict mypy over 16 source files pass.

## Workbench and Compiler Explorer delivery — 2026-09-14

Status: **IMPLEMENTED for native compiler inspection through a locally configured control plane.** `/workbench` and `/compiler` now provide an editable JOCKY source surface and invoke the real `jockyc` `check`, `tokens`, `ast`, `jir`, `plan`, `llvm`, and explicitly simulated `run` stages. The API uses a fixed command allowlist, no shell, a private temporary source file, and a bounded timeout. It returns 501 rather than invented results when `JOCKY_COMPILER_PATH` is absent. Desktop/mobile browser coverage passes **14/14**, the production Next.js build passes with 21 generated pages, and cross-platform Prettier line endings are pinned.

### Explicitly open Agent work

The verified remote path is limited to the bounded REAL inventory bridge. The
compiler's current ORC host remains a SIMULATED fixture and its output cannot
enter REAL evidence. Timeout/result/file/concurrency limits are `ENFORCED`;
Linux CPU/memory are sampled `OBSERVED_ONLY`, Windows CPU/memory and network
bytes are `UNSUPPORTED`, and strict jobs needing those controls fail
admission. Certificate rotation, Windows credential-store integration, spool
quotas, OpenTelemetry spans, optional-adapter execution, independent Windows
runtime acceptance, and multi-agent distributed fault acceptance remain open.

## Current LLVM backend delivery — 2026-09-13

Status: **IMPLEMENTED and acceptance-tested in the compiler-owned fixture scope; not operationally VERIFIED as an endpoint product.** The C++20 compiler now lowers typed JIR through LLVM 18, verifies and optimizes real IR, emits host relocatable objects with `TargetMachine`, and executes in-process machine code with ORC `LLJIT`. Runtime ABI v2 has fixed collector entry points, opaque explicitly retained/released dataset handles, owned error state, and a closed analysis dispatcher. Seeded variants make deterministic, compiler-controlled structural choices without changing instruction/effect order, configuration, evidence semantics, or OS behavior.

`compile`, `llvm`, `run --execution memory`, `variants`, `variant-info`, and `benchmark` are real CLI paths. Manifests carry source/JIR/IR/artifact hashes, compiler/LLVM versions, target triple, seed/profile/mode, structural measurements and literal-pool metadata. Protected literal pools use AES-256-GCM with a random 96-bit nonce, AAD bound to build identity, an external key plus key ID, authenticated decryption and transient plaintext cleansing. Keys are neither logged nor embedded.

This compiler scope is deliberately a **SIMULATED deterministic fixture**, not endpoint evidence. The runtime host callbacks return deterministic fixture datasets for equivalence testing. Real Windows/Ubuntu collector adapters, Agent-owned collector-job admission, supervision/cancellation and evidence signing now exist in the separate Rust runtime, but the compiler AOT/ORC artifact is not integrated with that worker. AOT output is a relocatable host object referencing runtime ABI v2, not a linked or signed endpoint executable. Cross-compilation fails closed with `E263`.

### Final native measurements

Environment: Windows host with Ubuntu 24.04.4 LTS under WSL2, x86_64 target `x86_64-pc-linux-gnu`, LLVM/Clang 18.1.3, CMake 3.28.3 and OpenSSL 3.0.13. The initial required pre-edit Docker test could not start because `//./pipe/docker_engine` was absent; the Windows host also lacked CMake/LLVM/Clang/Ninja/CTest. The acceptance toolchain was therefore installed in WSL and the mandatory LLVM dependency was not bypassed.

For `sih-demo.jky`, all variants shared source hash `5d43781568ec7fe1da1c695184f717bb13aa026596075bd4cce589e888b3b2a8`, JIR hash `2a1b96faa68d5a0536a48d99d0dbb04a0b40c2934ec19ffe8feb77735634323c`, and fixture semantic hash `25052cb72bd9d7eb5496c4fe18e07ac9420dc7613c3ace8b8208bfccf242f4d3`.

| Seed   | Basic blocks / functions / helpers | LLVM IR hash                                                       | AOT object hash                                                    | Structural fingerprint                                             |
| ------ | ---------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------ |
| `0x64` | 66 / 23 / 15                       | `5572515817d0a2b28f3a37b8e461ac944cd343656d57793f3ef644793b6cfc64` | `e346534397a53ebccedc5bf626e769c2b2ec0cc6b55da793706a938b46c2835e` | `be1fbbf39ca10cde1ced230cdde3fc019cbfc1ba721fa7891509f0bd63fee274` |
| `0x65` | 58 / 23 / 15                       | `3623b0cbc26e8a38f283f668ad03bcfde1971f61ecfb754230cc038eb08e49fe` | `40cd9571b44c847a4e0b9759aaf5f1e4984480c7b930c2873c9c904335a45a02` | `396d4ae4eea183a66f69380802fb2eeee41a70636c57c328908b25971f52a023` |
| `0x66` | 69 / 23 / 15                       | `314b728ca42102e6c7b251274f581cc32d60750c948b677a667f2a3c4c6bb992` | `41612eead23d5b4d809be68f36774534d897477fd0fcd2d90ebcb4a2ed859b61` | `bf840cb1cf186a328470e620c299dec107f41e47d948f31791dfa517d731eb17` |

Measured milliseconds from the same three-variant run (steady clock):

| Seed   |      Lex |    Parse |  Semantic |       JIR |   Variant | LLVM generation | Optimization |        AOT | JIT compile |  Execute |
| ------ | -------: | -------: | --------: | --------: | --------: | --------------: | -----------: | ---------: | ----------: | -------: |
| `0x64` | 8.780720 | 4.555240 | 48.396782 | 17.795949 | 18.749035 |       93.412585 |   254.450344 | 282.236136 |   96.809417 | 2.723343 |
| `0x65` | 8.780720 | 4.555240 | 48.396782 | 17.795949 | 26.127873 |        8.882736 |    21.593094 |  49.054213 |   26.848154 | 0.193211 |
| `0x66` | 8.780720 | 4.555240 | 48.396782 | 17.795949 | 12.990554 |        3.785826 |    15.144650 |  40.567577 |   35.732377 | 0.421317 |

Two independent seed-`0x64` AOT builds were byte-identical: 14,032 bytes each, SHA-256 `e346534397a53ebccedc5bf626e769c2b2ec0cc6b55da793706a938b46c2835e`. The protected-literal fixture reported AES-256-GCM, key ID `acceptance-test`, no AOT artifact, semantic hash `11b9f2695dab0d5d550d0aee9ae3b90bcc7bb47934bda4399bd806bb58d8210a`, JIT compile 130.730899 ms and execution 0.353732 ms. Its nonce/ciphertext digest is intentionally fresh per encryption and is not a deterministic-build assertion.

### Final verification

- Native CTest: **35/35 passed** in 24.69 seconds, including fixed ABI lowering, real ORC execution, actual objects, same-seed reproduction, different-seed diversity, semantic equivalence, correct-key decryption, wrong-key denial and ciphertext-tag tamper denial.
- Frontend corpus: **7 valid examples × 5 commands**, 21 deterministic goldens, **19 invalid examples × 3 commands**, and the missing-source diagnostic passed.
- Python/contracts: **53/53 passed**; generated schema/TypeScript/catalog checks, Ruff, and strict mypy over 15 source files passed.
- JavaScript/TypeScript: ESLint, all four workspace typechecks, and the Next.js 16.3.5 optimized build with 21 generated static pages passed.
- Protobuf descriptor/Python stubs and both Python sdists/wheels built successfully.
- Repository-wide Prettier remains a checkout-wide failure on 66 files, including many untouched baseline files; unrelated formatting was preserved. Docker/Rust/container/e2e checks were not rerun because Docker was unavailable. Native Windows compiler/runtime and live collectors were not run.

## Frontend delivery history — 2026-09-13

P1 (P0 product priority) implements the real C++20 lexer → parser/AST → types/semantics/capabilities → typed JIR → static execution-plan pipeline. All five CLI commands are available. Linux LLVM 18 validation currently passes 29 CTest checks, including all seven valid programs, 19 invalid programs and 21 deterministic snapshots. Python contract and protobuf roundtrip checks pass for all seven JIR modules. The full repository verification aggregate passed; detailed commands and limitations are recorded below.

This delivery produces compiler documents, not endpoint observations. Plans remain non-dispatchable. Source LLVM lowering, collectors, signed admission, resource enforcement, driver-risk evaluation and report generation are still later phases.

## Foundation delivery history

Delivery: **P0 repository foundation — COMPLETE and VERIFIED within the scope below**, begun 2026-09-12 from an empty directory on macOS arm64. No prior files, Git repository, or ancestor AGENTS.md existed. The attached project brief was inspected before changes. Root AGENTS.md now defines ownership, mandatory LLVM, provenance, simulation and safety rules.

This is not a completed forensic product. A working API/dashboard shell and LLVM diagnostic do not imply a working JOCKY compiler, distributed agents or evidence vault. Full product acceptance is in DEFINITION_OF_DONE.md. The 122-row requirement catalog is served by the API and rendered to REQUIREMENT_TRACEABILITY.md.

Status vocabulary: PLANNED, SCAFFOLDED, IMPLEMENTED, VERIFIED, BLOCKED_ENVIRONMENT. VERIFIED is always scoped to the behavior and environment tested. Phase numbers denote sequence, not product priority: **LLVM is a mandatory P0 priority in every build**.

## Phase plan and acceptance

| Phase | Priority / scope                                          | Acceptance criteria                                                                                                                                                                                                                         | Current status / dependency                                                                                      |
| ----- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| P0    | Mandatory engineering foundation                          | Required directories/docs, AGENTS, schema/protobuf authority, lockfiles, Make/CI, buildable C++/Rust/Python/Next boundaries, explicit unavailability, formatter/linter/type/test/build evidence                                             | VERIFIED foundation; acceptance scope and limits below                                                           |
| P1    | P0 language frontend and typed JIR                        | Handwritten lexer/parser with spans; AST/types/nullability/capabilities/budget grammar; all accepted source examples and negative corpus; deterministic typed JIR and CLI check/ast/jir/plan                                                | VERIFIED static frontend; see current delivery evidence                                                          |
| P2    | P0 complete LLVM backend and runtime ABI                  | JIR lowering, verified real LLVM IR, optimization metrics, TargetMachine AOT, ABI conformance and minimal system/process collector vertical slice                                                                                           | IMPLEMENTED compiler/ABI/AOT scope; real collector slice remains open                                            |
| P3    | P0 native and own-memory ORC execution                    | Trusted Agent-owned worker, native/memory equivalence, capability context, cancellation and enforceable resource governor, CPU/RAM/I/O/deadline negative tests                                                                              | IMPLEMENTED separate compiler ORC fixture and Agent collector worker; integration remains open                   |
| P4    | P0 Build Diversity Engine, encrypted configuration, Forge | Reproducible same-input/seed builds, three distinct artifact hashes, normalized fixture equivalence, complete real manifests/signing status, AEAD pool/no plaintext/tag tamper checks, actual build-to-registry lifecycle                   | IMPLEMENTED diversity/AEAD slice; signing/Forge lifecycle remain open                                            |
| P5    | P0 secure distributed control plane and agents            | Domain migrations, cases/scripts/plans, mTLS enrollment/health, signed expiring nonce-bound jobs, durable replay protection, policy, simultaneous child jobs, scheduling/retry/cancel, encrypted spool/reconnect, direct transport          | IMPLEMENTED + VERIFIED for one REAL bounded-inventory Rust Agent path; multi-agent/load and rotation remain open |
| P6    | P0 real Windows and Ubuntu collector coverage             | All fourteen collector groups plus supported DNS; normalized types, documented native APIs, availability/permission matrix, file race checks, optional adapter detection, bounded I/O                                                       | IMPLEMENTED adapters; Ubuntu P0 live-tested, Windows compile-only, DNS/optional execution open                   |
| P7    | P0 provenance, investigation and operational UI           | Persistent scoped evidence/manifest verification, durable audit with checkpoints, NetworkX correlation, timeline/findings, SSE, PDF/JSON, Workbench/Compiler/Variant/Forge/Endpoints/Jobs/Live/Graph/Evidence pages use actual data         | IMPLEMENTED Workbench/Compiler bridge and stateless verifier; persistent investigation surfaces remain open      |
| P8    | Safe driver-risk, fixtures and compatibility lab          | Real driver analysis plus sourced blocklist/CVE imports, separate LAB SIMULATION, harmless fixture lifecycle, operator-recorded correctness/alerts/resources, no attack capabilities                                                        | PLANNED; fixture documents only, no operational simulator                                                        |
| P9    | Profiling, scale, presentation                            | Raw compiler/variant/agent/distributed samples, baseline comparisons, real chart data, 1/2/10/50 endpoint trials as available, complete 3–5 minute Judge Mode                                                                               | PLANNED; no forensic benchmark values collected                                                                  |
| P10   | Release hardening and endpoint compatibility              | Windows/Ubuntu CI and live acceptance, mTLS rotation/revocation, RBAC/tenant/object isolation, anchored audit rollback detection, offline/tamper/cancel/replay cases, signed artifacts, dependency/SBOM review, legitimate relay validation | PLANNED; remote/product deployment remains disabled                                                              |

## Implementation inventory

- C++20/CMake requires LLVM. The compiler emits verified optimized LLVM IR, real host objects, and in-process ORC machine code through runtime ABI v2. check/tokens/ast/jir/plan/llvm/compile/run/variants/variant-info/benchmark are implemented in their documented host/fixture scope. Cross-compilation and unsupported opcodes fail explicitly. Fixed collector calls currently dispatch only to the deterministic fixture or a supplied runtime host; no real OS adapter is claimed.
- Rust/Tokio/tonic Agent implements local and mTLS remote identity/admission, real fixed-registry Windows/Linux collectors, compiler-worker supervision, normalized signed evidence, encrypted SQLite spool, replay-safe transport, and operational CLI. The verified remote scope is bounded inventory; ORC remains a simulated compiler fixture.
- Python contracts contain provenance, all core entities, state machine, budgets, variants/encryption/signatures, nullable stage metrics and evidence. The stateless RFC 8785/SHA-256 observation and audit-chain primitives are implemented. AES-GCM protected pools are implemented in the native compiler/runtime; artifact signing remains unimplemented.
- FastAPI provides liveness, explicit non-readiness, capability coverage, unavailable endpoint inventory, unavailable compiler and stateless verification. Database metadata/Alembic baseline exists with no domain tables. Redis/MinIO/NetworkX/OTel dependencies do not imply integrated domain features.
- Next.js/Tailwind/TanStack Query console provides the 18 navigation routes, Judge Mode readiness, backend coverage, unavailable metrics, errors/retry and real submitted-observation verification. Monaco, React Flow and Recharts integration awaits working backend features. No demo telemetry is hardcoded into components.
- Compose includes PostgreSQL, Redis, MinIO, optional app/monitoring/relay profiles, loopback bindings and generated local credentials. Monitoring configuration does not invent metrics; relay template is not mTLS support.

## Machine dependency inventory

Initial host: Python 3.12.2 and 3.14.0, uv 0.7.16, Node 24.10.0, npm 11.6.0, pnpm 10.28.2, CMake 3.31.6, Apple Clang 17, protobuf compiler 33.0, Docker 29.1.2, Make 3.81, Git 2.39.5.

Missing on host: Rust/cargo/rustfmt/Clippy, LLVM development libraries/llvm-config, clang-format, Ninja and GoogleTest package. Apple Clang alone does not supply the LLVM C++ development package. Docker daemon is available and provides an isolated Ubuntu LLVM 18/GoogleTest/Clang-format environment and Rust 1.90 build environment. Host deficiencies are not hidden by disabling LLVM.

Python packages were installed into `.venv`, npm packages into local node_modules, with lockfiles. Registry access required sandbox network escalation; no global toolchain replacement was performed. Browser binaries are repository-local under `.cache/playwright` when installed. Certificates/signing keys, endpoint enrollment credentials and authorized Windows/Ubuntu lab machines are not provided by the brief.

## Verification record

Final verification on 2026-09-12: **`make verify-containers` exited 0**. This aggregate ran every declared foundation formatter/linter/type/schema/test/package/build gate plus native/Rust container checks, Compose validation and real browser integration. There are **54 passing tests: 38 Python, 4 native CTest, 2 Rust, 10 desktop/mobile browser**. These are correctness checks, not fabricated performance benchmark values.

| Command / check                                            | Result / scope                                                                                                                                                      |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `make contracts-check`                                     | PASS: Pydantic JSON Schema, generated TypeScript and requirement catalog/markdown agree                                                                             |
| `make format-check`                                        | PASS: Ruff formatting and Prettier; canonical golden bytes excluded intentionally                                                                                   |
| `make lint`                                                | PASS: Ruff and ESLint with zero linter warnings                                                                                                                     |
| `make typecheck`                                           | PASS: strict mypy over 14 source modules and TypeScript over all four npm workspaces                                                                                |
| `make test`                                                | PASS: 38 tests cover provenance, budgets, states, schema/catalog, real hash/tamper verification, audit chains, unavailability and request bounds                    |
| `make proto-check`                                         | PASS: Python gRPC/protobuf generation and descriptor; Rust protobuf also compiled in agent build                                                                    |
| `make build-python`                                        | PASS: source distributions and wheels for contracts/control-plane                                                                                                   |
| `make build`                                               | PASS: Next.js 16.3.5 production build, 21 static pages generated plus API proxy route                                                                               |
| `make verify-native-container`                             | PASS: C++20/Clang/LLVM 18.1.3 on Ubuntu 24.04 Linux arm64, clang-format, four CTest tests, actual ORC machine-code self-test                                        |
| `make verify-agent-container`                              | PASS: Rust 1.90 locked build, rustfmt, two tests, Clippy with warnings denied, actual host diagnostic                                                               |
| `make test-e2e`                                            | PASS: 10 Chromium desktop/mobile cases, live API/proxy, evidence tamper mismatch, coverage, unavailable transport/retry, Judge Mode readiness and responsive layout |
| `make infra-check`                                         | PASS: all Compose profiles validate without exposing credentials                                                                                                    |
| Compose app image builds/start                             | PASS: Python and Next images built and API/dashboard run on loopback; proxy/liveness checked; execution readiness remains 503                                       |
| PostgreSQL / Alembic                                       | PASS: real local connection, SELECT 1 and baseline revision 0001_foundation applied; no domain persistence claimed                                                  |
| Redis / MinIO                                              | PASS: PONG and object-store liveness; Compose healthchecks pass; no evidence-ingestion integration claimed                                                          |
| Monitoring profile                                         | PASS: Prometheus readiness, Grafana database health and OTel Collector startup/config; OTLP application instrumentation remains planned                             |
| `npm audit --omit=dev`                                     | PASS: zero reported production npm advisories at verification time; not a universal dependency/security certification                                               |
| `make doctor` and host CMake configure                     | EXPECTED FAILURE: report missing host Rust/LLVM tools; CMake refuses absent LLVM rather than substituting a backend                                                 |
| Windows / x86_64 endpoint execution                        | NOT RUN: Windows CI is configured but not executed here; no supplied authorized endpoint or implemented collectors                                                  |
| TLS relay / mTLS / signing                                 | CONFIGURATION ONLY: supplied certificates and completed identity/signing implementation required; not tested as trusted transport                                   |
| Operational compiler/diversity/collectors/distributed hunt | NOT IMPLEMENTED: phases P1–P9 remain planned                                                                                                                        |

The initial tonic method collision was fixed by using Exchange instead of Connect. The mobile API status badge now remains visible. MinIO's unavailable Docker Hub image was replaced with its documented Quay release and validated; no storage mock was used. Network/socket sandbox restrictions were handled through scoped tool escalation. Git was initialized on main; no commit or remote was created.

Upstream development warnings remain documented: the currently compatible Next React/accessibility lint plugins require ESLint 9, so the attempted ESLint 10 upgrade was rejected and no force/legacy-peer-deps override was used. ESLint 9 lint passes; its upstream support/deprecation must be reviewed during dependency maintenance. Starlette's test client emits HTTPX/AnyIO deprecation notices; tests pass. The environment supplies both NO_COLOR and FORCE_COLOR, which produces harmless Node warnings during Playwright. None of these warnings is counted as a failed check or hidden by changing test expectations.

Local evidence: `.cache/verify-containers.log`, `.cache/native-build.log`, `.cache/agent-build.log`, `.cache/e2e.log`, `.cache/npm-audit.json`, and `.cache/command-center.png` (ignored development outputs). The running local stack is available at http://127.0.0.1:3000 and API docs at http://127.0.0.1:8000/docs. Use `make infra-down` to stop the stack while retaining its data volumes. Generated credentials remain in ignored `.env` with mode 0600.

At foundation delivery, the requirement catalog had 8 narrowly VERIFIED foundation rows, 1 SCAFFOLDED tooling/CI row and 113 PLANNED product rows. This deliberately does not present documentation or route coverage as a completed operational product. All **135 newly created files** are listed in [FOUNDATION_FILES.md](FOUNDATION_FILES.md).

## Next work and blockers

Next implementation work closes the remaining P2/P3 operational scope: add real bounded system/process adapters, move execution behind authenticated Agent-owned admission, and enforce cancellation and hard budgets. The API compilation endpoint remains 501 because the new native compiler is not yet integrated into the control-plane trust boundary.

The reference Linux container removes the immediate host LLVM/Rust build blocker. Windows native compiler/runtime acceptance still needs Windows LLVM development libraries/GoogleTest plus an authorized Windows endpoint. Actual Ubuntu collector/governor acceptance needs a suitable authorized host with cgroup delegation or an explicitly denied hard-limit plan. mTLS enrollment/signing/AEAD keys and domain storage are implementation work, not credentials to invent. Full Judge Mode remains blocked on the implemented and verified product phases above.

## Frontend verification record — 2026-09-13

**`make verify-containers` exited 0** for the frontend implementation. The aggregate includes `make verify-foundation`, the native and Rust image gates, Compose validation and live Chromium tests. Evidence is in `.cache/verify-frontend-containers.log`. Test evidence comprises **53 Python tests, 29 native CTest checks, 2 Rust tests and 10 desktop/mobile browser tests**. Rust image layers were cached, so `docker run --rm jocky-agent:foundation cargo test --locked --workspace` was also executed freshly and passed both tests. No skipped check is counted as passing.

| Command / scope                                                                        | Result                                                                                                                                                                                                                                                               |
| -------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `make verify-foundation` (inside aggregate)                                            | PASS: contract/schema/TypeScript/catalog drift, Ruff/Prettier, Ruff/ESLint, strict mypy (15 modules), workspace TypeScript, 53 pytest tests, protobuf generation, Python sdists/wheels and Next production build                                                     |
| `make verify-native-container`                                                         | PASS: clean C++20 Release build with Clang/LLVM 18.1.3 on Ubuntu 24.04 arm64, clang-format, 29 CTest checks, real ORC ABI probe                                                                                                                                      |
| `ctest --test-dir build/frontend-linux --output-on-failure` (Ubuntu container)         | PASS: Debug build, 29 checks; independent of the Release build                                                                                                                                                                                                       |
| `scripts/test_frontend.py --compiler <actual-jockyc>`                                  | PASS: seven valid examples through tokens/AST/check/JIR/plan, repeated deterministic bytes, 21 AST/JIR/plan snapshots, 19 invalid examples through check/JIR/plan with expected codes, missing-file error                                                            |
| Native semantic/robustness tests                                                       | PASS: all collector capability requirements, narrow legacy grants, typed fields/literals, Windows and Linux target semantics, JIR effect/SSA/type invariants, pushdown barriers, 500 deterministic malformed-source mutations and bounded nested correlation schemas |
| Python frontend contracts                                                              | PASS: all seven actual native JIR/plan snapshots validate against Pydantic and generated JSON Schema; schema and hash consistency; tampered effects/executable claim rejected                                                                                        |
| Protobuf document bridge                                                               | PASS: all seven actual native JIR modules preserve exact canonical bytes through generated v1 CanonicalDocument serialization/deserialization; repeat packing is deterministic                                                                                       |
| `make verify-agent-container` and fresh `cargo test --locked --workspace` in its image | PASS: locked Rust build/format/Clippy gate (cached layers), two freshly executed transport/scaffold tests; no agent execution capability added                                                                                                                       |
| `make infra-check` and `make test-e2e` (inside aggregate)                              | PASS: Compose configuration and ten live API/dashboard Chromium desktop/mobile tests                                                                                                                                                                                 |
| Native Windows compiler or live Windows/Ubuntu collectors                              | NOT RUN / NOT IMPLEMENTED respectively. Cross-OS semantic constraints were tested in the Linux compiler; that is not a native Windows acceptance run                                                                                                                 |
| Host `make verify`                                                                     | NOT RUN for this phase: required host LLVM/Rust tools remain absent as recorded above. Its mandatory toolchain checks have not been weakened; the container aggregate supplies the required reference toolchains                                                     |

Two existing example comments were corrected after the aggregate's image context was captured; their exact source hashes and snapshots were regenerated by the real CLI, and the complete corpus passed again. The final native image is revalidated in `.cache/verify-frontend-native-final.log`. The final foundation gate is recorded in `.cache/verify-frontend-foundation-final.log`. No endpoint data, artifact hash, risk match, signature, compiler timing or resource measurement was synthesized.

Frontend implementation is split into focused source/lexer/parser/AST/type/registry/configuration/expression/collection/query/investigation/JIR modules; the current CLI and JIR contract report version 0.3.0. JSON integration contracts originate in `packages/contracts/src/jocky_contracts/frontend.py`; the existing v1 protobuf transport remains unchanged. Static collector schemas and all accepted grammar are frozen in LANGUAGE_SPEC.md. The backend now produces verified optimized LLVM basic blocks and physical variant metrics; the compilation API remains HTTP 501 pending trusted service integration.

The 122-row catalog now has **12 VERIFIED, 3 IMPLEMENTED, 1 SCAFFOLDED and 106 PLANNED** rows. LANG-01–04 are verified within the static frontend scope. LANG-05 stays IMPLEMENTED because native Windows compiler equivalence has not run; LANG-06 still needs opcode lowering/runtime coverage; LANG-07 still needs llvm/compile/variants/run/benchmark. All original requirements remain present.

Remaining P2–P4 acceptance requires real system/process adapters, authorized Agent-owned execution workers, enforceable budgets/cancellation, signing, and the Forge/registry lifecycle. Risk metadata resolution, evidence/report production and authenticated transport remain their original phases. Compiler-owned ORC fixture execution proves generated JOCKY code reaches the fixed ABI with equivalent semantics; it does not prove an operational endpoint hunt.
