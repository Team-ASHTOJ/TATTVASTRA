# Architecture

## Current versus target

The repository contains the typed C++ frontend plus an initial real LLVM backend: fixed runtime-ABI lowering, verified modules, host TargetMachine objects, own-process ORC execution against a deterministic SIMULATED fixture, seeded compiler structural diversity, manifests and AES-256-GCM literal pools. The Rust Agent still does not host execution or real collectors, enroll agents, ingest evidence or persist domain objects. The following diagram remains the target production architecture.

```mermaid
flowchart LR
  UI[Next.js operator console] --> API[FastAPI control plane]
  API --> PG[(PostgreSQL metadata and audit)]
  API --> Q[(Redis transient queues)]
  API --> S3[(MinIO / S3 evidence)]
  API --> Forge[Build Forge]
  Forge --> Front[C++ lexer / parser / types]
  Front --> JIR[Typed platform-independent JIR]
  JIR --> Diversity[Seeded generated wrapper diversity]
  Diversity --> LLVM[LLVM IR / optimization]
  LLVM --> AOT[TargetMachine AOT]
  LLVM --> ORC[ORC-compatible module]
  API --> Relay[Direct mTLS or legitimate relay]
  Relay --> Agent[Rust agent supervisor]
  Agent --> Worker[Agent-owned execution worker]
  AOT --> Worker
  ORC --> Worker
  Worker --> ABI[Versioned JOCKY runtime ABI]
  ABI --> Collect[Windows APIs / Linux procfs and sysfs]
  Collect --> Spool[Encrypted SQLite spool]
  Spool --> API
  API --> Graph[NetworkX correlation / timeline / findings]
  API --> SSE[Committed event SSE]
  SSE --> UI
```

## Decisions

1. **One monorepo, native-first compiler.** CMake manages C++20/LLVM, Cargo manages Rust, uv manages Python workspaces, npm workspaces manage TypeScript. Root Make targets compose them. Keep the compiler out of Python and React.
2. **Mandatory LLVM.** CMake uses `find_package(LLVM REQUIRED CONFIG)`. Ubuntu LLVM 18 is the reference baseline; newer majors must pass validation before being called supported. ORC probe proves linkage/code generation only. Complete source lowering and TargetMachine artifacts are subsequent acceptance gates. [LLVM CMake documentation](https://llvm.org/docs/CMake.html) describes `LLVM_DIR` discovery.
3. **Typed effectful JIR.** Stable op registry, explicit dataset types, source spans, capabilities and estimated costs. Backend lowering must preserve evaluation order for effectful collection. See JIR_SPEC.md.
4. **Rust host with a C ABI.** C++ does not own endpoint identity or OS policy. The Rust supervisor creates opaque runtime contexts containing granted capability scope, cancellation token, resource ledger, collector table and observation sink. C++ wrappers only call the registered ABI. No user-selected symbols or arbitrary libraries.
5. **Own-worker JIT.** The supervisor stays responsive; an Agent-owned execution worker contains ORC and collectors. This is the Agent's own execution process, never third-party injection. Worker termination bounds non-cooperative code and peak memory. Optional Windows JIT entitlement/policy conflicts are explicit compatibility outcomes.
6. **PostgreSQL is authoritative.** Redis carries ephemeral scheduling hints, not durable evidence or audit truth. Use a transactional outbox and append-only event offsets for job transitions. Celery is deferred until real asynchronous scheduling requires it; no redundant worker system in P0.
7. **Evidence bytes and metadata separate.** MinIO stores content-addressed blobs; PostgreSQL stores authorization/provenance and expected hashes. Atomic publish protocol stages objects, verifies hash, commits metadata and outbox, then acknowledges the agent. Orphans are reconciled. UI never accesses objects by unscoped storage key.
8. **Versioned contract authority.** Pydantic emits JSON Schema and TypeScript. Protobuf defines transport framing around canonical signed JSON, avoiding signatures over unstable protobuf serialization. Python refinement validation is stricter than generated structural TS types; every receiving boundary must validate independently.
9. **Monotonic events, no fabricated live state.** SSE uses committed sequence offsets, resumable cursors and heartbeats. Endpoint heartbeat age affects reported health; disconnection cannot be shown as online. A parent hunt summarizes independent child jobs rather than forcing a single success value.
10. **Measured frontend features.** Next.js with strict TypeScript/Tailwind/TanStack Query in P0; Monaco, React Flow, Recharts and optional shadcn primitives enter with working backend features. UI shell keeps empty/error/loading states. Next build and lint are separate checks, as documented for [Next.js installation](https://nextjs.org/docs/app/getting-started/installation).

## State and data model

Organization owns users, cases, endpoint identities and scripts. Script has immutable ScriptVersions. Compilation links ScriptVersion and zero or more Variants. Variant stores a VariantManifest; ExecutionPlan binds approved source/JIR/capabilities/budget to endpoints. Each endpoint receives its own Job attempt and nonce. Observations, Artifacts and Findings belong to a case/job with immutable provenance. TimelineEvent references an observation. AuditEvent is append-only. Report references a generated artifact. BenchmarkRun and CompatibilityRun retain environment and variant identity.

Core schemas exist in P0; database entities are not silently inferred from them. The initial Alembic revision is an explicitly empty migration baseline. Domain tables, tenancy constraints, foreign keys, optimistic transition checks and durable audit transactions belong to P5/P7.

## Deployment and failure boundaries

Local development uses loopback API/dashboard and Docker backing services. TRUSTED_RELAY is a declared TLS gateway whose public host matches its certificate. The proxy template is not an active mTLS implementation. Agent mTLS must terminate at an authenticated boundary with protected peer identity, or pass through to the control plane; never trust public forwarded identity headers.

Compilation runs in restricted workers with source size/time/memory bounds. Unknown source operations fail diagnostics. Unavailable compiler returns 501. Non-ready orchestration returns readiness 503 even when liveness is 200. Missing LLVM fails the native build. Unsupported collectors return UNAVAILABLE/DENIED/PARTIAL, not static JSON. Object-store outages cause spool/retry with bounded quotas. Cancellation retains valid partial evidence and records final outcome. Retries receive a new job ID, nonce and expiry, linked to the previous attempt.

Build reproducibility pins source bytes, JIR schema, target triple, compiler/LLVM versions, optimization and seed. Wall-clock manifest creation belongs outside artifact identity. Encrypted-pool reproducibility uses a previously generated immutable pool blob as an additional build input; fresh key/nonce material intentionally changes that build input. See SECURITY_MODEL.md for nonce uniqueness.

## Environments and trust

Ubuntu 24.04 and supported Windows versions are endpoint targets; the precise Windows release matrix must be measured in P6/P10. macOS arm64 is only a development host today. Linux arm64 container tests do not prove Windows or x86_64 support. Production enablement requires mTLS, RBAC, signature verification, nonce durability, encrypted spool, tenant isolation, governor tests and independent Windows acceptance.
