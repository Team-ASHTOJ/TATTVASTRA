# Definition of done

## Status vocabulary

- **PLANNED:** documented design/acceptance only.
- **SCAFFOLDED:** buildable module/interface exists; product behavior incomplete.
- **IMPLEMENTED:** relevant behavior exists but required acceptance is incomplete.
- **VERIFIED:** explicitly scoped behavior passed recorded checks on named environments.
- **BLOCKED_ENVIRONMENT:** a required external prerequisite prevents validation; never counts as a pass.

Phase completion, product priority and platform validation are different dimensions. LLVM is mandatory/P0 priority. A passing ORC probe is not a completed compiler. A route shell is not a completed application feature.

## Foundation acceptance (this task)

- Repository inspection and machine inventory recorded; existing good work preserved (initial directory was empty).
- Required monorepo paths, root AGENTS.md, all twelve docs and a complete requirement matrix exist.
- Shared schemas cover all domain entities, provenance, budgets, variants, evidence, state enums and transport framing; JSON Schema/TypeScript generation rejects drift.
- Root commands install dependencies, run API/dashboard, build native/Rust, generate schemas/protobuf, lint/typecheck/test/package and operate local infrastructure.
- C++ build requires LLVM and executes a real ORC diagnostic; unimplemented source commands fail explicitly.
- Rust binary builds and reports actual host support with no invented collector availability. Protocol encodes simulation presence explicitly.
- FastAPI liveness/status/contracts/verifier work; non-ready orchestration and missing compiler produce explicit failures.
- Next.js builds with strict types, accessible navigation, loading/error/empty/retry states and no hardcoded endpoint/benchmark telemetry. Coverage is backend-sourced; stateless verification actually recomputes a hash.
- Tests exercise rejection/tampering/state/provenance boundaries. Formatters/linters/builds available locally or in containers run, failures are fixed, and platform/environment limitations are recorded.
- Local secrets are generated into ignored files, never committed. No operational attack capabilities or undisclosed simulation are introduced.

## Feature completion gate

For every requirement, a concrete implementation and meaningful test/demo evidence must match the catalog status. Update the API/schema/docs/UI together. Record explicit unknown/partial/unavailable cases, retries, cancellation and failure behavior. Collectors use real supported OS interfaces. Data lineage and simulation state survive every transform. No guessed metrics, hash-only artifact fabrication, fake compiler stage dumps, or static dashboards may satisfy acceptance.

## Full prototype acceptance

1. Real lexer/parser/AST/type/capability pipeline accepts the example hunts and rejects invalid programs with source spans.
2. Typed JIR lowers to verified LLVM IR. Native TargetMachine and ORC execution produce actual forensic observations via the runtime ABI on Windows and Ubuntu.
3. Three seeds yield distinct generated artifact bytes; identical full inputs/seed reproduce artifacts; normalized immutable fixture results agree. Manifests carry real hashes and signing status.
4. Enabled literal pools use authenticated encryption, avoid plaintext test secrets in artifacts, reject tampering and do not reuse nonces. Runtime tokens never enter source/artifacts.
5. Multiple agents enroll with identity, receive signed expiring capability-scoped jobs, reject replay across restart, enforce budgets, spool encrypted results, reconnect and cancel cleanly.
6. All fourteen required collector groups plus supported DNS metadata are real; optional adapters detect availability. Windows and Linux field/permission differences are explicit.
7. Case/job/observation/artifact/finding/timeline/report persistence, tenant authorization, verified manifests/signatures and externally anchored audit history pass negative tests.
8. Graph/timeline/findings correlate harmless fixtures and real observations with evidence click-through. Stored evidence verification detects modified bytes and does not confuse hashing with authenticity.
9. Driver Intelligence uses actual inventory and sourced risk metadata; the controlled visibility simulator is clearly separate. Compatibility Lab records operator observations with no evasion optimization.
10. The 18 pages and Judge Mode operate on actual backend states; demo fixtures have simulation=true everywhere. REAL mode never displays invented endpoints or measured values.
11. Raw compiler/variant/agent/distributed performance samples back charts and exports. Environment, repetitions, warmup, unknowns and failure rates are recorded.
12. Clean-checkout CI, Windows/Ubuntu builds, security/compatibility tests, offline/replay/tamper/cancel/partial-success tests and the 3–5 minute live demo pass. Release artifacts are traceable and signed or explicitly UNSIGNED development artifacts.
