# JIR specification — version 1 target

Status: specified, not emitted by the P0 compiler. JIR is typed, platform-independent and effect-aware. It is not a list of shell commands and contains no arbitrary native payloads.

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

This is specification notation, not generated compiler output. Every effect resolves through a validated runtime context.

## Instruction registry

| Family                 | Required instructions                                                                                                | Result/effect                                             | Capability / lowering boundary                                            |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------- |
| System                 | SYSTEM_INFO, HOSTNAME_READ, SESSION_ENUMERATE, USER_ENUMERATE, ENVIRONMENT_READ                                      | Endpoint/session/user/environment datasets; read effect   | system.read / users.read; sensitive environment values redacted by policy |
| Process                | PROCESS_ENUMERATE, PROCESS_METADATA, PROCESS_HASH, PROCESS_SIGNATURE_STATUS                                          | Process metadata/hash/status datasets; read effect        | process.read plus filesystem.read for executable hashing                  |
| Network                | NETWORK_INTERFACE_ENUMERATE, NETWORK_CONNECTION_ENUMERATE, LISTENING_PORT_ENUMERATE, ROUTE_ENUMERATE, DNS_STATE_READ | Typed interface/connection/route/DNS rows                 | network.read; unsupported ownership/DNS fields nullable                   |
| Filesystem             | FILE_METADATA, FILE_HASH, FILE_COLLECT, DIRECTORY_ENUMERATE                                                          | File datasets or artifact handle; read/store effects      | filesystem.metadata/read and approved root scope                          |
| Logs                   | EVENT_QUERY, EVENT_FILTER, EVENT_NORMALIZE                                                                           | Dataset<Event>; bounded query followed by pure transforms | logs.read for source query                                                |
| Persistence inspection | SERVICE_ENUMERATE, STARTUP_ENUMERATE, SCHEDULED_TASK_ENUMERATE                                                       | Read-only service/startup/task inventory                  | services.read / system.read; no create/install operation                  |
| Driver                 | DRIVER_ENUMERATE, DRIVER_SIGNATURE_STATUS, DRIVER_HASH, DRIVER_RISK_LOOKUP                                           | Driver/status/hash/risk records                           | drivers.read; hashing separately scoped; supplied risk dataset identity   |
| Analysis               | FILTER, PROJECT, SORT, GROUP, JOIN, CORRELATE, TIMELINE, FINDING_CREATE                                              | Typed datasets/findings/timeline with retained provenance | Pure transforms except finding emission; bounded joins/sorts              |
| Evidence               | ARTIFACT_STORE, ARTIFACT_HASH, MANIFEST_CREATE, REPORT_GENERATE                                                      | Artifact/manifest/report handles; ordered output effects  | Explicit case/job sink, output quotas and policy                          |

Each opcode must eventually have: arity/types, null behavior, supported OS field matrix, required capabilities, I/O accounting, cancellation points, deterministic fixture behavior, LLVM lowering and conformance tests. Unsupported opcodes are compile/plan errors; no VM fallback is implied.

## Validation

Reject use-before-definition, duplicate IDs, type mismatch, incompatible correlation keys, missing capability declarations, invalid source spans, over-limit literal pools and unbounded collection/joins. Every dataset crossing an ABI boundary has a schema ID and owned handle; raw pointers do not appear in JIR. Integer arithmetic uses defined overflow handling. Unknown predicates cannot become true through lowering.

Runtime returns OK, UNAVAILABLE, DENIED, BUDGET_EXCEEDED, CANCELLED, INVALID_ARGUMENT or INTERNAL_ERROR; future partial-dataset results must carry explicit diagnostics. A failed collector does not manufacture an empty successful observation set.

## LLVM lowering and diversity invariants

The lowering stage creates LLVM functions using the fixed C ABI in `native/runtime/include/jocky/runtime.h`, verifies the module, runs recorded optimization passes, and emits TargetMachine objects or ORC-compatible code. Runtime context and dataset handles have explicit ABI widths and ownership; exceptions never cross C/Rust boundaries.

Diversity may alter internal helper names/order, wrapper layout and equivalent generated control structures. It cannot alter opcodes, arguments, capability requirements, budget ceilings, evidence membership or effect ordering. Canonical pre-diversity JIR hash stays constant. Variant seed affects generated LLVM/artifacts, never semantic JIR.

Semantic comparisons run against immutable collector fixtures, normalize only documented nondeterminism (run IDs, collection timestamps and ordering where unspecified), and compare every meaningful field plus error/partial status. Live process/network samples are not a valid deterministic equivalence oracle. Reproducibility and semantic equivalence are distinct tests.
