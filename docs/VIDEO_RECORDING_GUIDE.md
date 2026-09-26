# JOCKY operator recording guide

Record a 4–6 minute walkthrough at 1366 × 768 or larger.

## Start

```sh
make demo-up
make demo-prepare
make demo-check
```

Open `http://localhost:13000`. Sign in using the organization UUID printed by preparation and local bootstrap credentials. Keep passwords and enrollment tokens out of the recording.

## Connect a real Linux agent

Endpoints → Connect Endpoint → Create enrollment. Download the control-plane CA and save the token in a permission-restricted file. Follow the dialog's native `jocky-agent init`, `enroll`, then `connect` commands. The enrollment channel is `https://localhost:15052`; authenticated control is `https://localhost:15051`. Use the same state directory throughout.

The existing Docker runtime image can run the actual Linux agent on the Compose network. Within that network use `https://agent-control:50052` for enrollment and `https://agent-control:50051` for control, mount the CA/token/state directory, and use `/usr/local/bin/jocky-worker`. The automated operator test exercises exactly this path with `jocky-agent-runtime:phase4-current`. If absent, build the existing `infra/docker/agent-runtime.Dockerfile` workflow documented in BUILD_STATUS.md. The UI does not claim to launch host containers.

WAITING means no authenticated heartbeat yet. ONLINE appears only after the bound agent sends its heartbeat. Stopped agents become stale/offline. SANDBOX fixture machines remain distinct from real agents.

## Operator sequence

| Time      | Action                                                       | Demonstrate                                                                                                                         |
| --------- | ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| 0:00–0:25 | Sign in → Command Center                                     | Persisted resources and clear Connect / Workbench / New Investigation actions.                                                      |
| 0:25–0:55 | Endpoints → Connect Endpoint                                 | Real enrollment instructions and heartbeat state; inspect an endpoint's structured detail tabs.                                     |
| 0:55–1:35 | Workbench → Load Example → System Baseline → CHECK → COMPILE | Empty editor, actual diagnostics, durable compilation and real Tokens / AST / Typed JIR / LLVM / Plan outputs.                      |
| 1:35–2:00 | Variant Explorer → Generate variants                         | Real artifact hashes, seeds and backend comparison. Different hashes alone do not prove equivalence.                                |
| 2:00–2:45 | New Investigation                                            | Select the compilation, real online endpoint and memory mode; review then start. Open actual persisted job completion and evidence. |
| 2:45–3:15 | Findings                                                     | Open the sandbox unsigned-process/external-connection conclusion; supporting observations and provenance remain explicit.           |
| 3:15–3:45 | Graph → Timeline                                             | Select a readable process node; filter chronological events and open detail with related analysis links.                            |
| 3:45–4:15 | Evidence Vault → Verify integrity                            | Actual stored and recomputed SHA-256; separately verify the evidence manifest signature.                                            |
| 4:15–4:40 | Driver Intelligence → Performance                            | Collected driver inventory and genuine measured compiler timings. Missing measurements remain unavailable.                          |
| 4:40–5:00 | JOCKY Language                                               | Implemented syntax, compile-valid examples and Open in Workbench.                                                                   |

For a real run choose a bounded inventory example. Rich filters/correlation/timeline/export are documented compiler syntax but not supported by the current remote execution bridge. The optional Failure Isolation Scenario is seeded backend data; it is not a default newly executed investigation.

## Truth boundary

REAL means actual compiler work, persisted orchestration, authenticated Rust agent results or stored-byte verification. SANDBOX means backend-generated input with simulation=true. Findings/graph/timeline can be genuinely derived from sandbox observations without those inputs being physical-endpoint measurements. Do not rename forensic process/file names merely because their original data contains a training prefix.

No claims of production readiness, Windows live acceptance, antivirus bypass, driver exploitation or invented quality/performance metrics.

## Rehearsal

```sh
npx playwright test -c playwright.prototype.config.ts
```

The test performs login, real TLS agent enrollment/heartbeat, compilation and variants, a real successful job, findings/graph/timeline, actual artifact verification, drivers, measurements, all five documentation examples and primary routes. It stops its temporary agent afterward.

If compilation or integrity fails, inspect the failure; never substitute output or edit hashes. Session expiration requires a fresh sign-in. `make demo-prepare` loads only optional persisted sandbox fixtures, not fake frontend progress.
