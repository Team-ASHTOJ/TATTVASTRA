# JIR specification — version 1 target

Status: frontend representation IMPLEMENTED; LLVM lowering and runtime execution remain PLANNED. The current serialization boundary is specified below. JIR is typed, platform-independent and effect-aware. It is not a list of shell commands and contains no arbitrary native payloads.

## Representation

A module contains schema version, source hash, source spans, named hunt/case binding, required capabilities, Budget, target OS constraints, runtime mode, typed record definitions and ordered basic blocks. Each instruction has a stable numeric ID, opcode, typed operands, optional result handle, source span, effect class, capabilities, cost estimate and nullability contract. Dataset handles behave as SSA values; rows and immutable projections retain observation provenance.

Types include scalar primitives, Option<T>, Record<fields>, Dataset<T>, Finding and TimelineEvent. Path/IP/PID/hash remain semantic types, not generic strings. Physical target layout and syscall names do not appear in semantic JIR. Effectful operations use an explicit ordered execution token; diversity cannot reorder collections or evidence writes. Schema-normalized JIR hashing excludes source-location cosmetics only when specified by the canonical JIR serializer; version/semantic configuration always participate.

```text
%sys : Dataset<Endpoint> = SYSTEM_INFO !effect0
%proc : Dataset<Process> = PROCESS_ENUMERATE(fields=[pid, name]) !effect1
%net : Dataset<Connection> = NETWORK_CONNECTION_ENUMERATE !effect2
%public : Dataset<Connection> = FILTER %net, remote.is_public == true
%related : Dataset<Record<process, connection>> = CORRELATE %proc.pid, %public.pid
```

This is illustrative specification notation; the compiler emits the structured JSON described below. Every effect resolves through a validated runtime context.

## Instruction registry

| Family                 | Required instructions                                                                                                | Result/effect                                             | Capability / lowering boundary                                                       |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| System                 | SYSTEM_INFO, HOSTNAME_READ, SESSION_ENUMERATE, USER_ENUMERATE, ENVIRONMENT_READ                                      | Endpoint/session/user/environment datasets; read effect   | system.read / users.read; sensitive environment values redacted by policy            |
| Process                | PROCESS_ENUMERATE, PROCESS_METADATA, PROCESS_HASH, PROCESS_SIGNATURE_STATUS                                          | Process metadata/hash/status datasets; read effect        | process.read plus filesystem.content for executable hashing                          |
| Network                | NETWORK_INTERFACE_ENUMERATE, NETWORK_CONNECTION_ENUMERATE, LISTENING_PORT_ENUMERATE, ROUTE_ENUMERATE, DNS_STATE_READ | Typed interface/connection/route/DNS rows                 | network.read; unsupported ownership/DNS fields nullable                              |
| Filesystem             | FILE_METADATA, FILE_HASH, FILE_COLLECT, DIRECTORY_ENUMERATE                                                          | File datasets or artifact handle; read/store effects      | filesystem.metadata/content and approved root scope                                  |
| Logs                   | EVENT_QUERY, EVENT_FILTER, EVENT_NORMALIZE                                                                           | Dataset<Event>; bounded query followed by pure transforms | logs.read for source query                                                           |
| Persistence inspection | SERVICE_ENUMERATE, STARTUP_ENUMERATE, SCHEDULED_TASK_ENUMERATE                                                       | Read-only service/startup/task inventory                  | persistence.read; legacy services.read is services-only; no create/install operation |
| Driver                 | DRIVER_ENUMERATE, DRIVER_SIGNATURE_STATUS, DRIVER_HASH, DRIVER_RISK_LOOKUP                                           | Driver/status/hash/risk records                           | drivers.read; hashing separately scoped; supplied risk dataset identity              |
| Analysis               | FILTER, PROJECT, SORT, GROUP, JOIN, CORRELATE, TIMELINE, FINDING_CREATE                                              | Typed datasets/findings/timeline with retained provenance | Pure transforms except finding emission; bounded joins/sorts                         |
| Evidence               | ARTIFACT_STORE, ARTIFACT_HASH, MANIFEST_CREATE, REPORT_GENERATE                                                      | Artifact/manifest/report handles; ordered output effects  | Explicit case/job sink, output quotas and policy                                     |

Each opcode must eventually have: arity/types, null behavior, supported OS field matrix, required capabilities, I/O accounting, cancellation points, deterministic fixture behavior, LLVM lowering and conformance tests. Unsupported opcodes are compile/plan errors; no VM fallback is implied.

## Validation

Reject use-before-definition, duplicate IDs, type mismatch, incompatible correlation keys, missing capability declarations, invalid source spans, over-limit literal pools and unbounded collection/joins. Every dataset crossing an ABI boundary has a schema ID and owned handle; raw pointers do not appear in JIR. Integer arithmetic uses defined overflow handling. Unknown predicates cannot become true through lowering.

Runtime returns OK, UNAVAILABLE, DENIED, BUDGET_EXCEEDED, CANCELLED, INVALID_ARGUMENT or INTERNAL_ERROR; future partial-dataset results must carry explicit diagnostics. A failed collector does not manufacture an empty successful observation set.

## LLVM lowering and diversity invariants

The lowering stage creates LLVM functions using the fixed C ABI in `native/runtime/include/jocky/runtime.h`, verifies the module, runs recorded optimization passes, and emits TargetMachine objects or ORC-compatible code. Runtime context and dataset handles have explicit ABI widths and ownership; exceptions never cross C/Rust boundaries.

Diversity may alter internal helper names/order, wrapper layout and equivalent generated control structures. It cannot alter opcodes, arguments, capability requirements, budget ceilings, evidence membership or effect ordering. Canonical pre-diversity JIR hash stays constant. Variant seed affects generated LLVM/artifacts, never semantic JIR.

Semantic comparisons run against immutable collector fixtures, normalize only documented nondeterminism (run IDs, collection timestamps and ordering where unspecified), and compare every meaningful field plus error/partial status. Live process/network samples are not a valid deterministic equivalence oracle. Reproducibility and semantic equivalence are distinct tests.

## Frontend 0.2.0 implementation boundary

The C++ frontend now emits JIRModule schema 1.0.0. The earlier sections retain the full lowering/ABI acceptance requirements; current output is a straight-line SSA instruction sequence, not executable basic blocks. There is no untrusted JIR loader, interpreter or dispatch path. All nine instruction families are registered with operand arity, effect and resource class. Collectors, pipelines, investigation statements and reports emit actual typed instructions. JOIN is registered for later lowering/optimization; the source correlation form emits CORRELATE. LIMIT and BIND are explicit analysis instructions, PACKAGE_ENUMERATE and MODULE_ENUMERATE extend inventory coverage. Constructor/arithmetic/count expressions are typed trees inside instruction attributes.

A module contains kind, schema/compiler version, exact source SHA-256, hunt/case labels, unresolved selectors, sorted OS constraints and capabilities, budget, runtime/variant configuration, instructions and executable=false. Instructions contain sequential ID, prior SSA operand IDs, opcode/family, structural result type, typed attributes, half-open source span, direct capability requirements, resource class, effect predecessor and target OS. Pure transforms require no additional grant beyond the capabilities of their source instructions. Result types contain name, nullable, domain and recursively typed fields. Every dataset implicitly retains the complete observation envelope; field projection does not strip provenance.

Resource classes are categorical planning estimates, not fabricated measurements: bounded_inventory, bounded_content_io, bounded_materialization, bounded_output and linear_transform. A collection requesting hashes also carries filesystem.content even if its inventory opcode uses bounded_inventory; that class is not a byte-cost estimate or an exemption from I/O accounting. Actual measurement, quotas, supported OS adapters and cancellation remain backend/runtime requirements.

Validation checks registered opcodes, arity, earlier operands, sequential IDs, valid spans, dataset operand/result shapes, collector schema agreement, row-preserving/projected types, required capabilities and the ordered effect chain. Source semantics additionally validate predicate/key/options/budget types before emission. The Python JirModule contract validates the serialized structure, SSA/effects and target/capability consistency. This is not a security verifier for externally supplied instructions: later signed-job admission must reject unsupported lowering, unknown policy/adapter versions and all untrusted native payloads.

`jockyc jir file.jky --json` writes sorted-key UTF-8 JSON without insignificant whitespace and one terminal newline. Literal numeric spellings are strings in typed expression nodes, avoiding loss of int64/seed precision. Structural JSON numbers are bounded portable integers. `jir_hash` is SHA-256 of those exact canonical bytes excluding the terminal newline. Source spans and runtime/variant settings currently participate: editing source, comments or seed changes this debug-module identity. This does not replace the future normalized pre-diversity semantic fingerprint; identical source and configuration produce identical current JIR. Diversity must never change semantics, effects or evidence membership.

The public document authority is `packages/contracts/src/jocky_contracts/frontend.py`; JSON Schema and TypeScript are generated with `make contracts`. Tokens and AST are versioned compiler debug representations; JIR and execution plans are the integration contracts. `scripts/pack_jir.py` validates native JIR and wraps its unchanged canonical bytes in the existing `jocky.v1.CanonicalDocument` protobuf using generated bindings. It roundtrips the bytes and rejects noncanonical input. This supplies a stable binary serialization without changing the v1 agent wire schema. It does not send a job or authenticate a producer. Example:

```sh
make proto-check
build/native/native/compiler/jockyc jir examples/basic/system.jky --json > build/system.jir.json
.venv/bin/python scripts/pack_jir.py --input build/system.jir.json --output build/system.jir.pb
```

## Explainable execution plans

`jockyc plan` produces FrontendExecutionPlan schema 1.0.0: source/JIR hashes, unresolved target selectors, OS constraints, collector/capability sets, filter/project candidates, projected fields, expected schemas per instruction, budgets, backend/mode/variant settings and warnings. dispatchable is false and admission_status is REQUIRES_ENDPOINT_POLICY_AND_LLVM_LOWERING. Automatic seed resolution is deferred, driver-risk data is absent, and neither endpoint availability nor runtime metrics are invented.

Pushdown metadata is a branch-local candidate with applied=false, collector and branch instruction IDs, operation attributes, and a dependency/adapter precondition. Candidates traverse only single-input BIND/FILTER/PROJECT/EVENT_FILTER/EVENT_NORMALIZE prefixes. Sort, limit, group, correlation, risk lookup and cross-binding dependencies are barriers. A predicate after a limit therefore cannot silently filter before that limit. A projection on one branch never removes fields needed by a sibling. Lowering must preserve predicate columns, scalar dependencies, null semantics and observation envelopes before applying an adapter-specific rewrite. This phase emits metadata and retains the full semantic instruction sequence; it does not claim physical query optimization has executed.

Frozen schemas, grammar, diagnostic codes and null behavior are in LANGUAGE_SPEC.md. Compiler snapshot fixtures are static outputs, not simulated forensic observations. Native tests and Python schema/protobuf tests compare actual compiler-produced bytes. Remaining acceptance before execution includes source-to-LLVM lowering, ABI dataset ownership, typed expression evaluation, runtime collectors, policy/resource enforcement, risk metadata, report/evidence sinks and fixture semantic equivalence.
