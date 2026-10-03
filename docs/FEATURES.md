# JOCKY features

**One Language. Every Endpoint. No Noise.**

This document describes the repository at commit `e268b39` (2026-09-29). It
separates working behavior from platform-dependent or planned behavior. See
[BUILD_STATUS.md](BUILD_STATUS.md) for test evidence and
[REQUIREMENT_TRACEABILITY.md](REQUIREMENT_TRACEABILITY.md) for requirement-level
status.

## Product overview

JOCKY is a defensive forensic platform with one traceable path from analyst
intent to evidence:

```text
.jky source -> typed JIR -> LLVM -> authorized Agent worker -> read-only collectors
-> normalized evidence -> findings/graph/timeline -> report
```

Its distinctive combination is a real forensic DSL, mandatory LLVM compilation,
deterministic build diversity, supervised multi-endpoint execution and evidence
provenance carried through the whole workflow. Python orchestrates services and
supports bounded local interoperability; it does not interpret JOCKY.

## At a glance

| Area                | Available now                                                                                                             | Boundary                                                                   |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Language            | Handwritten C++20 frontend, diagnostics, typed expressions, collectors, correlation, findings, timelines and report plans | Static vocabulary is broader than the bounded remote worker                |
| JIR                 | Versioned, typed, platform-independent, effect-aware instruction document                                                 | Currently a straight-line ordered SSA-like sequence                        |
| Compiler            | Verified LLVM IR, optimization, real AOT objects and ORC LLJIT                                                            | LLVM is mandatory; no interpreter fallback                                 |
| Cross-target builds | Real Linux ELF and Windows COFF objects from one semantic JIR                                                             | Windows linking/runtime acceptance is still environment-dependent          |
| Diversity           | Seeded structural variation, real hashes/fingerprints and bounded fixture equivalence                                     | Not a universal equivalence or antivirus-bypass claim                      |
| Build Forge         | Persisted SOURCE-to-READY pipeline, 1–8 variants, signed build provenance and byte verification                           | Host-target delivery; no crash-resuming build queue/fleet rollout          |
| CLI                 | Build, inspect, compare, benchmark, verify, pipeline, doctor and Python package commands                                  | Does not hold control-plane credentials or dispatch endpoints              |
| Python interop      | Isolated packages, typed imports/calls, JIR/LLVM lowering and local ORC execution                                         | Local, bounded scalar interface; not remote collection                     |
| Endpoint Agent      | Enrollment, mTLS, signed jobs, real collectors, cancellation, replay protection and encrypted spool                       | Linux verified; live Windows and hard CPU/RAM/network controls remain open |
| Live endpoints      | Three independently enrolled Linux Agents, direct/relay transport and real JIT/AOT jobs                                   | Shared Docker host, not three external machines                            |
| Evidence            | Canonical hashes, content-addressed artifacts, Ed25519 manifests and audit hash chain                                     | No Merkle tree or external audit checkpoint                                |
| Analysis            | Persisted findings, graph, timeline, reports and optional AI hypothesis cards                                             | Live AI provider execution is configuration-dependent and unverified       |
| UI                  | Authenticated responsive console with SSE-backed live workflow                                                            | Fleet-scale/production operation remains incomplete                        |

## 1. Independent forensic language

JOCKY is not a Python wrapper or collection of shell commands. Its C++20
frontend owns lexing, parsing, name binding, type checking, capability validation,
diagnostics and JIR construction.

The language supports:

- OS, host, group and explicit endpoint selectors;
- runtime, capability, resource-budget and variant declarations;
- system, process, network, filesystem, log, service, startup, package, driver
  and module collection;
- immutable pipelines with filters, projection, stable sorting, limits and
  grouping;
- typed same-endpoint correlation, evidence-backed findings and timelines;
- integrity-required JSON/PDF report plans and driver-risk analysis;
- bounded local Python imports and calls.

Forensic types such as `pid`, `path`, `ip`, `hash`, `time`, `duration` and
`bytes` are not interchangeable strings. `Option<T>` and three-valued logic keep
unknown data unknown—for example, unknown signature status never becomes
“unsigned.” Input size, token count, nesting and schema complexity are bounded.
There is no dynamic evaluation, arbitrary native import, shell execution,
mutation loop or native-payload literal.

## 2. Typed, effect-aware JIR

The JOCKY Intermediate Representation is the stable boundary between forensic
intent and physical execution. Instructions carry stable opcodes, typed operands
and results, source spans, target constraints, capability requirements, resource
classes, nullability and an ordered effect predecessor.

Dataset handles behave as SSA values. Explicit effect order prevents optimization
or diversity from reordering collection and evidence writes. Projection retains
the full endpoint/job/clock/variant/integrity/simulation envelope.

JIR is canonical JSON with a deterministic hash and can be transported unchanged
inside protobuf `CanonicalDocument`. Unsupported opcodes fail; Python or a VM is
never used as an implicit fallback.

## 3. Mandatory LLVM and two execution modes

Supported JIR lowers through a fixed runtime ABI to verified LLVM IR. JOCKY runs
the optimizer, emits real TargetMachine objects and records physical metrics.

- **MEMORY / JIT:** LLVM ORC LLJIT executes inside a dedicated JOCKY-owned worker.
- **NATIVE / AOT:** a linked standalone worker executes under Agent supervision.

Both modes re-hash the artifact before execution. Neither injects into, hollows or
mutates another process. Missing LLVM is a build failure, never permission to
substitute fake compilation.

The same semantic JIR has produced real Linux x86_64 ELF and Windows x86_64 COFF
objects with target-specific triples/data layouts. Cross-target compilation is
real; final Windows linking and endpoint execution have not been verified.

## 4. Deterministic Build Diversity Engine

A seed selects bounded helper ordering, internal naming and wrapper-layout
strategies while preserving opcodes, arguments, capability requirements, budgets,
evidence membership and effect order.

Each variant can retain source/JIR/LLVM/artifact hashes, seed, target and toolchain
identity, structural fingerprint, helper/function/basic-block counts, object size,
stage measurements and fixture result hash. The same complete input and seed
reproduces identity. Requested variants must have genuinely distinct structures
and bytes or the build fails.

Semantic equivalence is a bounded test against an immutable, explicitly
`SIMULATED` fixture. It is not a universal proof and is never optimized against
antivirus outcomes.

## 5. Persistent Build Forge

Build Forge turns a Compilation into a durable delivery run:

```text
SOURCE -> VALIDATE -> JIR -> DIVERSIFY -> LLVM -> BUILD
       -> TEST -> EQUIVALENCE -> MANIFEST -> READY
```

It selects one to eight variants, stores actual object bytes, records gate state
and timing scope, checks bounded fixture equivalence, and signs a manifest in the
`JOCKY:build:v1` Ed25519 domain. Verification checks the signature, database
provenance and current object bytes; missing or modified content cannot pass.

AES-256-GCM protected literal pools use an external key ID, random nonce,
authenticated associated data and plaintext cleansing. Keys do not enter IR,
artifacts, manifests or logs. Endpoint key distribution is still incomplete.

## 6. Rich local CLI

`jocky` is a thin Python launcher around authoritative `jockyc` output. It can
select an explicit compiler, checkout build, PATH binary or existing Docker image.

| Family        | Commands                                                              |
| ------------- | --------------------------------------------------------------------- |
| Build/inspect | `check`, `tokens`, `ast`, `jir`, `plan`, `llvm`, `compile`, `run`     |
| Variants      | `variants`, `variant-info`, `diverge`, `diff`, `equivalence`, `forge` |
| Explain       | `caps`, `budget`, `types`, `metrics`, `fingerprint`                   |
| Validate      | `verify`, `manifest`, `benchmark`, `pipeline`, `doctor`               |
| Python        | `install`, `packages`                                                 |

`jocky <file.jky>` is local ORC execution against the labeled deterministic
fixture, not endpoint evidence. Endpoint/hunt/relay commands are explicitly
rejected because this CLI has no authenticated tenant session.

## 7. Python package interoperability

The CLI installs packages into an isolated directory (default
`~/.jocky/python/site-packages`), lists installed distributions and mounts the
directory read-only in the Docker backend.

```jocky
hunt "Python Package Interop" {
    capabilities { python.interop }
    python import "humanize" as humanize
    python call humanize.intcomma(1234567) as formatted
}
```

The C++ frontend validates aliases/functions/literal arguments, emits a typed
`PYTHON_CALL`, and LLVM lowers it to the fixed `jocky_rt_analysis` ABI. When built
with Python development support, the runtime embeds CPython and returns the scalar
value through the normal owned dataset-handle lifecycle. Missing modules, failed
calls and unsupported return types have explicit error codes.

The boundary is intentional: string/integer/float/boolean literal arguments,
scalar results and local LLVM ORC execution behind `python.interop`. It is not an
unrestricted FFI and is not part of remote endpoint execution.

## 8. Rust Agent and live endpoints

The Rust Agent owns endpoint identity, policy, transport and execution. Standalone
mode initializes an identity, reports actual platform/collectors, runs real local
collectors through signed development jobs, handles cancellation and flushes the
encrypted spool.

Remote mode generates its key/CSR locally, consumes a one-time enrollment token,
proves its Ed25519 evidence key, receives a short-lived certificate, maintains an
mTLS stream, replays durable sequenced frames and accepts only signed,
endpoint-bound work. Admission validates signature, audience, expiry, nonce,
capabilities, budgets and artifact identity before a child worker starts.

Replay protection survives restart. An exact duplicate returns the stored receipt
without running again. The supervisor bounds concurrency, deadline/cancellation,
result size, file count and file/read bytes. Linux CPU and peak RSS are measured
but not hard-limited; strict jobs requiring unavailable controls fail admission.

The verified prototype operates three independently enrolled Linux Agent
instances. Two connect directly and one through the trusted relay. Each reports a
real worker PID, duration, execution engine and signed evidence. They are real
processes on a shared Docker host, not a claim of three physical machines.

## 9. Read-only collector coverage

The fixed registry covers:

- system information, users and sessions;
- processes and process metadata;
- interfaces, TCP/UDP connections, listening ports and routes;
- approved-path file metadata and SHA-256 hashing;
- services, startup locations and scheduled tasks;
- system/event logs and installed software/packages;
- drivers and loaded kernel modules.

Linux uses procfs/sysfs and fixed read-only utilities where necessary. Windows
uses fixed non-interactive PowerShell/CIM/NetTCPIP calls; that code cross-builds,
but live Windows acceptance remains open. Errors become `PARTIAL`, `DENIED` or
`UNAVAILABLE`, never a fabricated empty success. A bounded YARA collector is
implemented for static approved rulesets and approved file roots, but its live
Linux-container acceptance is BLOCKED_ENVIRONMENT on this development host.
Volatility 3 and osquery remain detected but execution-unavailable.

## 10. Multi-endpoint investigations

One Hunt binds a Case, immutable source/Compilation, ExecutionPlan, endpoint set
and execution policy. The control plane creates an independent Job per endpoint
with its own variant, attempt, mode, nonce, deadline and provenance.

It supports simultaneous dispatch, per-endpoint JIT/AOT mode, compatibility
rejection, cancellation, deadline sweeping, isolated retries and aggregate
`SUCCESS`/`FAILED`/`PARTIAL`/`CANCELLED` state. Evidence from successful endpoints
survives a sibling failure. ONLINE requires a fresh authenticated heartbeat.

## 11. Direct and trusted-relay transport

DIRECT uses end-to-end TLS/mTLS. TRUSTED_RELAY is a fixed-destination TLS byte
pass-through; it does not inspect TLS, rewrite identity, implement SOCKS or hide
origin through domain fronting. Transport mode is recorded from the authenticated
connection and propagated through endpoint, job, manifest, report and UI.

## 12. Evidence, signatures and the “Merkle” distinction

JOCKY separates integrity and authenticity:

- RFC 8785 canonical observation JSON plus SHA-256 detects document changes;
- content-addressed artifact verification re-reads and hashes stored bytes;
- endpoint Ed25519 evidence manifests bind ordered observations to source, JIR,
  artifact, endpoint, job, transport and execution;
- Build Forge Ed25519 manifests bind build provenance in a separate domain;
- organization audit events form an append-only SHA-256 previous-hash chain.

There is **no Merkle tree, Merkle root or inclusion-proof implementation in this
repository**. The audit log is a linear hash chain. It detects edits, gaps,
reordering and mixed-organization links when checked from the expected beginning.
It cannot alone detect tail removal or wholesale recomputation by an attacker who
controls storage. Signed external sequence/head checkpoints are the planned
rollback defense.

Hashes prove byte integrity; signatures bind a producer/key; provenance binds an
artifact to a workflow; external anchoring would protect history continuity.
JOCKY reports these as separate facts.

## 13. Findings, graph and semantic timeline

Server-side correlation reads persisted observations and creates evidence-linked
findings, typed graph relationships and normalized timeline events. The dashboard
adds a semantic investigation narrative across session, investigation,
collection, detection, correlation, finding, evidence, verification and response
stages. That narrative is a projection of stored hunts/jobs/observations/findings,
not a replacement or synthetic evidence source.

Filters cover endpoint, collector, severity, type, time and search text, with
evidence click-through from findings and graph nodes.

## 14. Hunt-scoped reports

A report queries only one Hunt's source/Compilation, plan, endpoints, jobs,
variants, observations, artifacts, manifests, findings and audit events. It
contains deterministic metrics/text, structured intent, endpoint outcomes,
bounded observation samples, provenance, distinct integrity/signature/audit
states and data-derived limitations. Missing values are omitted; zero findings is
not called proof of safety.

Canonical JSON is stored content-addressably with matching Artifact/Report rows
and an audit event, then re-hashed before retrieval. Browser print provides Save
as PDF; PDF is not a second canonical server artifact.

## 15. Report-grounded AI assistance

Insight can attach separate AI-assisted hypothesis cards to a persisted report.
The server sends a bounded report-derived brief—not exact source or the complete
raw observation set—to an OpenRouter-compatible endpoint using the configured
model (default `openai/gpt-oss-20b`) and strict JSON Schema.

Validation requires exactly three distinct ranked hypotheses, report-owned
evidence IDs and platform responses copied from a report-derived allowlist. The
cards separate evidence, inference, uncertainty and suggested action. They never
replace Findings or mutate the canonical report.

`PENDING`, `READY` and `FAILED` state is bound to the report artifact hash and can
be retried. Missing provider credentials fail only the optional analysis. Mocked
provider and UI tests are recorded; live provider generation is not verified.

## 16. Operator console and live events

The authenticated Next.js console covers Command Center; Workbench and language
docs; Compiler Explorer; Build Forge/Variant Explorer; endpoint enrollment and
detail; investigations and per-job progress; Insight/findings; graph/timeline;
artifacts/manifests; driver intelligence; performance; and requirement coverage.

It has responsive layouts and explicit loading, empty, unavailable, partial,
error and retry states. Persistent Judge Mode guides the end-to-end operator flow.

`/api/events` is authenticated SSE backed by committed outbox sequence IDs and
supports `Last-Event-ID` resumption. Keepalives are not domain events; incoming
events invalidate the relevant persisted queries.

## 17. Contracts, tenancy and honest simulation

PostgreSQL is authoritative for organizations, users/sessions, cases, immutable
script versions, compilations, builds, variants, plans, hunts/jobs, evidence,
findings, timeline, audit/outbox, benchmarks, compatibility records and reports.
ADMIN/ANALYST/VIEWER permissions and organization scope are server-enforced.

Pydantic is the JSON contract authority; JSON Schema and TypeScript are generated
and drift-checked. Protobuf frames exact canonical JSON instead of being signed
directly. Every receiving trust boundary validates independently.

Synthetic data always carries `simulation=true` and a label through evidence,
findings, graphs, timelines, manifests, reports and metrics. REAL jobs reject
synthetic results. The UI distinguishes REAL, DEMO/SIMULATED, SANDBOX and measured
fixture behavior.

## 18. What makes JOCKY attractive

1. **One typed intent across platforms:** forensic programs replace per-OS command
   scripts.
2. **Inspectability from source to bytes:** source, JIR, LLVM, object, variant and
   execution identities remain connected.
3. **Accountable diversity:** reproducible seeds and real equivalence evidence,
   not opaque mutation.
4. **Constrained execution:** authorized compiler output reaches only JOCKY-owned
   workers and a fixed read-only collector ABI.
5. **Failure as evidence:** denial, unavailability and partial collection stay
   visible.
6. **Precise trust claims:** hashes, signatures, provenance and audit continuity
   are independent statuses.
7. **Simulation cannot silently become reality:** provenance travels through every
   layer.
8. **One operator journey:** code, live endpoints, investigation, graph, timeline,
   artifacts and reports share the same identities.

## Known limits

- No verified live Windows endpoint execution yet.
- Remote execution intentionally supports a bounded inventory subset.
- Hard CPU/RAM/network governance, spool quotas and certificate rotation are open.
- The relay is TLS pass-through, not an HTTP gateway or domain-fronting feature.
- Audit history is hash-chained, not Merkle-based or externally anchored.
- The active ObjectStore is local content-addressed storage, not MinIO authority.
- Fleet-scale trials and distributed throughput claims remain incomplete.
- Optional adapters and production risk-intelligence ingestion are unavailable.
- AI assistance is optional and not verified against a live provider.

Unsupported states are reported explicitly rather than replaced by fabricated
output.
