# JOCKY

**One Language. Every Endpoint. No Noise.**

JOCKY is TATTVASTRA's defensive forensic platform: a typed language and native
compiler path that carries investigation intent from `.jky` source through typed
JIR, LLVM, authorized endpoint execution, normalized observations, findings,
reports, and verifiable evidence.

```text
.jky source
  → typed, effect-aware JIR
  → LLVM IR / ORC JIT / AOT object
  → signed job to an authorized Rust Agent
  → supervised JOCKY-owned worker
  → fixed read-only collectors
  → normalized evidence
  → findings / graph / timeline / Hunt report
```

Python orchestrates the CLI and control plane. It does not parse, type-check, or
interpret JOCKY.

## What is implemented

- Handwritten C++20 lexer, parser, type system, capability validation, diagnostics,
  collector schemas, correlation, findings, timelines, and report plans.
- Versioned typed JIR with deterministic canonical identity, SSA-like dataset
  handles, explicit effect ordering, target constraints, budgets, and provenance.
- Mandatory LLVM lowering with verified IR, optimization, real AOT objects, and
  LLVM ORC LLJIT memory execution. There is no interpreter fallback.
- Real Linux ELF and Windows COFF objects from the same semantic JIR. Linux
  endpoint execution is verified; Windows linking and live endpoint execution
  remain environment-dependent.
- Build Forge with one to eight deterministic seeded variants, structural
  fingerprints, real artifact hashes, bounded fixture equivalence, protected
  literal pools, and Ed25519 build manifests.
- Rust Agent identity, one-time enrollment, mTLS, signed expiring jobs,
  nonce-bound replay protection, artifact re-hashing, cancellation, supervision,
  and encrypted offline spooling.
- Three independently enrolled Linux Agent instances in the verified prototype:
  two direct connections and one trusted relay, all on a shared Docker host.
- Read-only collection for system, users, processes, interfaces, connections,
  routes, approved-path files, services, startup, scheduled tasks, logs,
  software, drivers, and kernel modules.
- Content-addressed artifact/evidence verification, Ed25519 manifests, and a
  per-organization append-only SHA-256 audit hash chain.
- Hunt-scoped reports with canonical JSON, stored-byte re-hashing, browser/PDF
  presentation, findings, graph, timeline, and explicit limitations.
- Optional report-grounded AI hypothesis cards. AI receives a bounded report
  brief, returns exactly three schema-validated hypotheses, and cannot mutate
  Findings or the canonical report.
- Bounded local Python interoperability through typed `PYTHON_CALL` JIR and the
  `jocky_rt_analysis` ABI. It is not unrestricted FFI or remote collection.
- Responsive Next.js operator console with Workbench, Compiler Explorer, Build
  Forge, endpoint lifecycle, investigations, evidence, Insight, Judge Mode, and
  live SSE-backed workflow state.
- PostgreSQL-backed organization tenancy and RBAC, immutable script versions,
  durable Hunts/jobs/outbox events, generated JSON Schema/TypeScript contracts,
  and versioned protobuf transport carrying canonical JSON.

See [docs/FEATURES.md](docs/FEATURES.md) for the detailed product surface and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for layer boundaries and flows.

## Start locally

Requires Python 3.12+, uv, Node 22+, npm, Rust 1.90, protobuf, CMake 3.25+,
LLVM development files, and GoogleTest for the full host toolchain. Docker
provides isolated native and Agent alternatives.

```sh
make bootstrap
make dev-api
# In another terminal:
make dev-dashboard
```

Open <http://127.0.0.1:3000>. The API documentation is at
<http://127.0.0.1:8000/docs>.

The default is REAL mode with no operational endpoint inventory. Demo and
fixture-backed paths are explicitly labelled; synthetic data carries
`simulation=true` and cannot enter a REAL job. An unavailable API produces an
error/retry state rather than fabricated endpoints.

## Run the compiler from the terminal

```sh
make jockey-install
jockey check hunt.jky
jockey jir hunt.jky
jockey llvm hunt.jky
jockey compile hunt.jky --target linux-x86_64
jockey pipeline hunt.jky --count 3
```

The terminal entry point dispatches to the authoritative `jockyc` compiler. It
supports these command families:

| Family          | Commands                                                              |
| --------------- | --------------------------------------------------------------------- |
| Build / inspect | `check`, `tokens`, `ast`, `jir`, `plan`, `llvm`, `compile`, `run`     |
| Variants        | `variants`, `variant-info`, `diverge`, `diff`, `equivalence`, `forge` |
| Explain         | `caps`, `budget`, `types`, `metrics`, `fingerprint`                   |
| Validate        | `verify`, `manifest`, `benchmark`, `pipeline`, `doctor`               |
| Python          | `install`, `packages`                                                 |

`jockey <file.jky>` runs local ORC execution against the labelled deterministic
fixture. That path is not endpoint evidence and does not hold control-plane
credentials.

## Durable workflow and contracts

PostgreSQL is authoritative for organizations, users and sessions, cases,
immutable scripts, compilations, Build Forge runs, variants, execution plans,
Hunts, per-endpoint Jobs, observations, evidence, findings, timelines, reports,
benchmarks, audit events, and committed outbox events. Organization scope and
ADMIN/ANALYST/VIEWER permissions are enforced server-side.

Pydantic defines canonical application documents. Generated JSON Schema and
TypeScript are drift-checked consumers, while protobuf v1 frames exact
canonical JSON for Agent transport. Required-field, enum, canonicalization, or
signature changes require an explicit version transition.

## Verify the repository

```sh
make verify-foundation
make verify-native-container
make verify-agent-container
make test-e2e
make infra-check
make verify
```

`make verify` requires all required host toolchains and fails when one is
missing. See [docs/BUILD_STATUS.md](docs/BUILD_STATUS.md) for dated commands,
test evidence, environment limitations, and current verification status.

## Architecture at a glance

| Layer                                        | Responsibility                                                                            |
| -------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `native/compiler`                            | C++20 frontend, typed JIR, plans, LLVM lowering, diversity, AOT/ORC, metrics              |
| `native/runtime`                             | Versioned C ABI, dataset ownership, protected literals, local Python bridge               |
| `services/agent`                             | Endpoint identity/policy, collectors, signed jobs, supervision, mTLS, replay, spool       |
| `services/control-plane`                     | FastAPI APIs, PostgreSQL state, Build Forge, scheduler, gRPC, evidence, analysis, reports |
| `apps/dashboard`                             | Authenticated Next.js console and SSE-driven resource refresh                             |
| `cli`, `scripts/jockey`                      | Compiler discovery, command composition, isolated Python packages                         |
| `packages/contracts`                         | Pydantic authority and generated JSON Schema/TypeScript                                   |
| `proto`                                      | Versioned Agent transport around canonical JSON                                           |
| `packages/jocky-language`                    | Editor metadata only; never an alternate compiler                                         |
| `infra`                                      | Images, Compose topologies, monitoring, and relay configuration                           |
| `examples`, `fixtures`, `tests`, `benchmark` | Programs, labelled data, acceptance tests, and measurement methodology                    |

The public-facing TATTVASTRA website is maintained as a separate standalone
project at `../tattvastra-website` and has no backend or dashboard dependency.

## Trust and safety boundaries

JOCKY keeps integrity, authenticity, provenance, and audit continuity as separate
verdicts. It uses canonical JSON and SHA-256 for integrity, Ed25519 manifests for
producer authenticity, source-to-evidence identities for provenance, and a
linear previous-hash audit chain for continuity. It does **not** claim a
cryptographic Merkle tree.

Execution is limited to compiler-generated, authorized programs in a dedicated
JOCKY-owned worker. The platform does not provide shell execution, arbitrary
native payloads, process injection or hollowing, callback removal, EDR/AV
disabling, kernel tampering, privilege escalation, persistence installation,
covert SOCKS routing, or domain fronting.

Known limits include live Windows endpoint execution, hard CPU/RAM/network
governance, certificate rotation and production credential storage, external
audit checkpoints, broad remote JIR execution, fleet-scale trials, and optional
YARA/Volatility/osquery adapter execution. Missing measurements remain
unavailable rather than being shown as zero.

## Further reading

- [Features](docs/FEATURES.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Build status](docs/BUILD_STATUS.md)
- [Requirement traceability](docs/REQUIREMENT_TRACEABILITY.md)
- [Definition of done](docs/DEFINITION_OF_DONE.md)
- [Agent runtime](docs/AGENT_RUNTIME.md)
- [Install guide](docs/INSTALL.md)
- [Repository instructions](AGENTS.md)
