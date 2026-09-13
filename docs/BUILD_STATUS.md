# Build status

## Current LLVM backend delivery — 2026-09-13

Status: **IMPLEMENTED and acceptance-tested in the compiler-owned fixture scope; not operationally VERIFIED as an endpoint product.** The C++20 compiler now lowers typed JIR through LLVM 18, verifies and optimizes real IR, emits host relocatable objects with `TargetMachine`, and executes in-process machine code with ORC `LLJIT`. Runtime ABI v2 has fixed collector entry points, opaque explicitly retained/released dataset handles, owned error state, and a closed analysis dispatcher. Seeded variants make deterministic, compiler-controlled structural choices without changing instruction/effect order, configuration, evidence semantics, or OS behavior.

`compile`, `llvm`, `run --execution memory`, `variants`, `variant-info`, and `benchmark` are real CLI paths. Manifests carry source/JIR/IR/artifact hashes, compiler/LLVM versions, target triple, seed/profile/mode, structural measurements and literal-pool metadata. Protected literal pools use AES-256-GCM with a random 96-bit nonce, AAD bound to build identity, an external key plus key ID, authenticated decryption and transient plaintext cleansing. Keys are neither logged nor embedded.

This scope is deliberately a **SIMULATED deterministic compiler fixture**, not endpoint evidence. The runtime host callbacks return deterministic fixture datasets for equivalence testing; real Windows/Ubuntu collector adapters, Agent-owned worker admission, hard resource governance/cancellation, signing, Forge/registry integration, and native Windows acceptance remain unimplemented. AOT output is a relocatable host object referencing runtime ABI v2, not a linked or signed endpoint executable. Cross-compilation fails closed with `E263`.

### Final native measurements

Environment: Windows host with Ubuntu 24.04.4 LTS under WSL2, x86_64 target `x86_64-pc-linux-gnu`, LLVM/Clang 18.1.3, CMake 3.28.3 and OpenSSL 3.0.13. The initial required pre-edit Docker test could not start because `//./pipe/docker_engine` was absent; the Windows host also lacked CMake/LLVM/Clang/Ninja/CTest. The acceptance toolchain was therefore installed in WSL and the mandatory LLVM dependency was not bypassed.

For `sih-demo.jky`, all variants shared source hash `5d43781568ec7fe1da1c695184f717bb13aa026596075bd4cce589e888b3b2a8`, JIR hash `2a1b96faa68d5a0536a48d99d0dbb04a0b40c2934ec19ffe8feb77735634323c`, and fixture semantic hash `25052cb72bd9d7eb5496c4fe18e07ac9420dc7613c3ace8b8208bfccf242f4d3`.

| Seed | Basic blocks / functions / helpers | LLVM IR hash | AOT object hash | Structural fingerprint |
| --- | --- | --- | --- | --- |
| `0x64` | 66 / 23 / 15 | `5572515817d0a2b28f3a37b8e461ac944cd343656d57793f3ef644793b6cfc64` | `e346534397a53ebccedc5bf626e769c2b2ec0cc6b55da793706a938b46c2835e` | `be1fbbf39ca10cde1ced230cdde3fc019cbfc1ba721fa7891509f0bd63fee274` |
| `0x65` | 58 / 23 / 15 | `3623b0cbc26e8a38f283f668ad03bcfde1971f61ecfb754230cc038eb08e49fe` | `40cd9571b44c847a4e0b9759aaf5f1e4984480c7b930c2873c9c904335a45a02` | `396d4ae4eea183a66f69380802fb2eeee41a70636c57c328908b25971f52a023` |
| `0x66` | 69 / 23 / 15 | `314b728ca42102e6c7b251274f581cc32d60750c948b677a667f2a3c4c6bb992` | `41612eead23d5b4d809be68f36774534d897477fd0fcd2d90ebcb4a2ed859b61` | `bf840cb1cf186a328470e620c299dec107f41e47d948f31791dfa517d731eb17` |

Measured milliseconds from the same three-variant run (steady clock):

| Seed | Lex | Parse | Semantic | JIR | Variant | LLVM generation | Optimization | AOT | JIT compile | Execute |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `0x64` | 8.780720 | 4.555240 | 48.396782 | 17.795949 | 18.749035 | 93.412585 | 254.450344 | 282.236136 | 96.809417 | 2.723343 |
| `0x65` | 8.780720 | 4.555240 | 48.396782 | 17.795949 | 26.127873 | 8.882736 | 21.593094 | 49.054213 | 26.848154 | 0.193211 |
| `0x66` | 8.780720 | 4.555240 | 48.396782 | 17.795949 | 12.990554 | 3.785826 | 15.144650 | 40.567577 | 35.732377 | 0.421317 |

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

| Phase | Priority / scope                                          | Acceptance criteria                                                                                                                                                                                                                         | Current status / dependency                                            |
| ----- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| P0    | Mandatory engineering foundation                          | Required directories/docs, AGENTS, schema/protobuf authority, lockfiles, Make/CI, buildable C++/Rust/Python/Next boundaries, explicit unavailability, formatter/linter/type/test/build evidence                                             | VERIFIED foundation; acceptance scope and limits below                 |
| P1    | P0 language frontend and typed JIR                        | Handwritten lexer/parser with spans; AST/types/nullability/capabilities/budget grammar; all accepted source examples and negative corpus; deterministic typed JIR and CLI check/ast/jir/plan                                                | VERIFIED static frontend; see current delivery evidence                |
| P2    | P0 complete LLVM backend and runtime ABI                  | JIR lowering, verified real LLVM IR, optimization metrics, TargetMachine AOT, ABI conformance and minimal system/process collector vertical slice                                                                                           | IMPLEMENTED compiler/ABI/AOT scope; real collector slice remains open |
| P3    | P0 native and own-memory ORC execution                    | Trusted Agent-owned worker, native/memory equivalence, capability context, cancellation and enforceable resource governor, CPU/RAM/I/O/deadline negative tests                                                                              | IMPLEMENTED compiler-owned ORC fixture; Agent/governor remain open     |
| P4    | P0 Build Diversity Engine, encrypted configuration, Forge | Reproducible same-input/seed builds, three distinct artifact hashes, normalized fixture equivalence, complete real manifests/signing status, AEAD pool/no plaintext/tag tamper checks, actual build-to-registry lifecycle                   | IMPLEMENTED diversity/AEAD slice; signing/Forge lifecycle remain open |
| P5    | P0 secure distributed control plane and agents            | Domain migrations, cases/scripts/plans, mTLS enrollment/health, signed expiring nonce-bound jobs, durable replay protection, policy, simultaneous child jobs, scheduling/retry/cancel, encrypted spool/reconnect, direct transport          | PLANNED; schemas and Rust transport scaffold exist                     |
| P6    | P0 real Windows and Ubuntu collector coverage             | All fourteen collector groups plus supported DNS; normalized types, documented native APIs, availability/permission matrix, file race checks, optional adapter detection, bounded I/O                                                       | PLANNED; requires authorized Windows/Ubuntu environments and P3/P5     |
| P7    | P0 provenance, investigation and operational UI           | Persistent scoped evidence/manifest verification, durable audit with checkpoints, NetworkX correlation, timeline/findings, SSE, PDF/JSON, Workbench/Compiler/Variant/Forge/Endpoints/Jobs/Live/Graph/Evidence pages use actual data         | PLANNED; stateless hash utilities and route shells are foundation only |
| P8    | Safe driver-risk, fixtures and compatibility lab          | Real driver analysis plus sourced blocklist/CVE imports, separate LAB SIMULATION, harmless fixture lifecycle, operator-recorded correctness/alerts/resources, no attack capabilities                                                        | PLANNED; fixture documents only, no operational simulator              |
| P9    | Profiling, scale, presentation                            | Raw compiler/variant/agent/distributed samples, baseline comparisons, real chart data, 1/2/10/50 endpoint trials as available, complete 3–5 minute Judge Mode                                                                               | PLANNED; no forensic benchmark values collected                        |
| P10   | Release hardening and endpoint compatibility              | Windows/Ubuntu CI and live acceptance, mTLS rotation/revocation, RBAC/tenant/object isolation, anchored audit rollback detection, offline/tamper/cancel/replay cases, signed artifacts, dependency/SBOM review, legitimate relay validation | PLANNED; remote/product deployment remains disabled                    |

## Implementation inventory

- C++20/CMake requires LLVM. The compiler emits verified optimized LLVM IR, real host objects, and in-process ORC machine code through runtime ABI v2. check/tokens/ast/jir/plan/llvm/compile/run/variants/variant-info/benchmark are implemented in their documented host/fixture scope. Cross-compilation and unsupported opcodes fail explicitly. Fixed collector calls currently dispatch only to the deterministic fixture or a supplied runtime host; no real OS adapter is claimed.
- Rust/Tokio/tonic scaffold exposes `jocky-agent doctor`, host/platform detection, generated protocol and wire tests. It reports operational=false, no collectors and no execution. SQLite/windows-rs/native Linux dependencies are declared for subsequent implementation; a dependency declaration is not functionality.
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
