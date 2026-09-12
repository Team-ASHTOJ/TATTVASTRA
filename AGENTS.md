# JOCKY engineering contract

JOCKY — One Language. Every Endpoint. No Noise.

## Non-negotiable principles

1. Read `docs/BUILD_STATUS.md`, the relevant specifications, and existing code before changing a subsystem. Preserve working code. Keep changes within the requested phase.
2. JOCKY is an independent forensic DSL with a handwritten C++20 frontend, typed platform-independent JIR, and a mandatory LLVM backend. Python orchestrates; it does not interpret JOCKY. Missing LLVM is a build error, never permission to substitute fake compilation.
3. Implement capabilities end to end before calling them implemented. Use `PLANNED`, `SCAFFOLDED`, `IMPLEMENTED`, `VERIFIED`, or `BLOCKED_ENVIRONMENT` precisely. `VERIFIED` requires recorded test evidence. A declaration, route, or schema is not the feature.
4. Never fabricate compiler output, variant hashes, endpoint states, signatures, evidence verification, or performance. Missing measurements are null/unavailable, never zero. Disabled features explain why. No placeholder TODOs masquerading as P0 implementation.
5. Every synthetic datum carries `simulation=true` and a simulation label. API and UI must distinguish REAL from DEMO/SIMULATED. Synthetic evidence cannot enter a REAL job. Fixture data originates in backend fixtures, never React constants.
6. Execution accepts compiler-generated, authorized JOCKY programs only. ORC JIT runs in a dedicated JOCKY Agent execution worker's own process memory. Never inject into unrelated processes.
7. Do not implement vulnerable-driver exploitation, callback removal, kernel tampering, arbitrary process injection/hollowing, reflective injection, security-tool unhooking, direct-syscall evasion, privilege escalation, persistence installation, covert SOCKS routing, or domain-fronting. Preserve requirement coverage with the safe mappings in `docs/REQUIREMENT_TRACEABILITY.md`.
8. Diversity is deterministic compiler-generated variation, with real artifact hashes and fixture-based semantic-equivalence tests. Never accept arbitrary native payloads or optimize against antivirus outcomes.
9. Secrets stay out of source, logs, artifacts, and fixtures. Use established AEAD, TLS/mTLS, signed expiring jobs, persistent replay protection, capability policy, resource limits, and explicit trust boundaries. Hash verification alone does not authenticate a producer.
10. Observation provenance, variant identity, clock source, integrity, and simulation state travel together. Never silently drop permission errors or collector limitations. Audits are append-only hash chains with external checkpoints before claiming rollback protection.
11. Windows and Ubuntu are endpoint targets. macOS is a development host, not an implicitly supported collector platform. Optional adapters report UNAVAILABLE when absent.
12. Contracts originate in `packages/contracts/src/jocky_contracts`; generated JSON Schema/TypeScript must be regenerated and checked for drift. Protobuf is the versioned transport contract. Breaking changes require an explicit version transition.
13. Keep modules focused, typed, and testable. Document architectural decisions and update traceability/build status alongside implementation. Run `make verify-foundation`, plus native/agent/infrastructure checks when those toolchains are available. Full `make verify` must fail when a required toolchain is missing.
14. Never claim skipped, blocked, configured-only, or unexecuted checks passed. Record commands, environment, and limitations in `docs/BUILD_STATUS.md`.
15. Do not introduce operational attack capabilities to satisfy a rubric. Compatibility Lab measures benign workloads; it makes no universal bypass claims.

## Workspace ownership

- `native/compiler`: C++ frontend, typed JIR, LLVM lowering/AOT/ORC, compiler metrics.
- `native/runtime`: versioned C ABI and trusted execution boundary.
- `services/agent`: Rust identity, policy, transport, collectors, spool, supervision.
- `services/control-plane`: FastAPI orchestration, persistence, evidence, correlation.
- `apps/dashboard`: Next.js operator UI consuming contracts and API status.
- `packages/contracts`, `proto`: schemas and wire protocol.
- `packages/jocky-language`: editor language metadata; never an alternate compiler.
- `infra`, `fixtures`, `tests`, `benchmark`, `docs`: reproducible operation and evidence.

Use ordinary engineering judgment for reversible work. This file does not require extra approval for routine implementation or validation.
