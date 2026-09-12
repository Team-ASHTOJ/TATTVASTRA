# Product specification

JOCKY — One Language. Every Endpoint. No Noise.

## Mission and scope

Translate authorized, platform-independent forensic intent into traceable LLVM programs, execute them on multiple Windows and Ubuntu endpoints, and correlate integrity-protected evidence. Five mandatory pillars: independent language, typed JIR, LLVM backend, deterministic Build Diversity Engine, distributed evidence provenance.

The first delivery establishes the repository, architecture, contracts, tooling and buildable scaffolds. Product features become available only after their acceptance criteria pass. Current capabilities and limitations are recorded in BUILD_STATUS.md and the requirement catalog. LLVM is a P0 product requirement even though complete lowering follows frontend implementation.

## Operators and core workflows

- **Analyst:** opens a case, writes a hunt, examines diagnostics and plans, reviews findings and provenance.
- **Operator:** enrolls authorized endpoints, approves capability scope, schedules/cancels hunts, diagnoses partial failures.
- **Evidence reviewer:** recomputes hashes, verifies signatures/manifests and audit checkpoints, exports scoped reports.
- **Lab operator/judge:** inspects real compilation/diversity/execution and clearly separated harmless synthetic scenarios.

The principal workflow is case → immutable script version → compilation → variants → validated execution plan → per-endpoint jobs → observations/artifacts → verified evidence → correlation/findings/timeline → report. Build Forge owns the actual build-to-registry lifecycle. GitHub Actions runs engineering checks; it does not replace Build Forge.

## Product behavior

Windows and Ubuntu normalize to the same forensic types. Fields unavailable on an OS or without permission remain nullable and carry field/collector availability metadata. Unknown signature status is never treated as unsigned. Process identity includes boot/session context and start time to prevent PID reuse errors. Collection can be partially successful; successful endpoints remain visible when another fails.

Native execution uses signed compiler-generated artifacts. Memory execution uses LLVM ORC inside an Agent-owned worker. Optional VM/debug execution cannot replace LLVM. Every executed observation links to the source, JIR, variant, collector, endpoint, job and case.

REAL mode contains actual endpoint data. DEMO mode uses backend fixture services with `simulation=true` and explicit labels propagated to observations, graphs, timelines, manifests, reports and metrics. REAL jobs reject simulated results. Capability metadata describes software implementation and is not synthetic telemetry.

## UI product surface

The 18 required pages are Command Center, Cases, Workbench, Compiler Explorer, Variant Explorer, Build Forge, Endpoints, Hunts/Jobs, Live Investigation, Findings, Graph, Timeline, Evidence Vault, Driver Intelligence, Compatibility Lab, Performance, Reports, Architecture/Coverage. Judge Mode guides actual state transitions through those pages. P0 provides route shells, connected coverage and a stateless verifier; route existence is not operational coverage.

The Command Center eventually reports endpoint and OS counts, active hunts, severity counts, recent variants, verified evidence fraction, compilation statistics, measured execution latency, driver alerts, agent health and live events. Until those data sources exist, show unavailable indicators. Workbench requires Monaco and server diagnostics; graph and charts use React Flow/Recharts once backed by real data. Do not install a mock compiler into the browser.

## Success and non-goals

Success means a valid hunt runs on both target platforms, three real variants differ in bytes while returning equivalent normalized fixture results, live evidence verifies, tampering is detected, and measured performance explains costs. Judge Mode must execute this 3–5 minute sequence, not play slides.

Excluded operational capabilities: callback disabling, driver exploitation, arbitrary injection/hollowing/reflective loading, security unhooking, syscall evasion, escalation, persistence installation, covert proxies, origin-concealing domain-fronting. Their explicit safe mappings remain in REQUIREMENT_TRACEABILITY.md. Driver-risk intelligence, own-process JIT, benign compatibility measurements, legitimate TLS relays and labeled visibility-loss fixtures satisfy the safe prototype coverage.
