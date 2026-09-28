# JOCKY operator recording guide

Record a 4–6 minute walkthrough at 1366 × 768 or larger.

## Start

```sh
make demo-up
make demo-prepare
make demo-check
```

Open `http://localhost:13000`. Sign in using the organization UUID printed by preparation and local bootstrap credentials. Keep passwords and enrollment tokens out of the recording.

## Connect three real local Linux endpoints

No additional terminal is needed after the three startup commands above.

1. Open Endpoints → Connect Endpoint.
2. Under Local Endpoint, click Start Local Endpoint.
3. The internal runtime initializes/enrolls the actual Rust agent and starts its TLS connection. Progress comes from launcher state, not frontend timers.
4. Wait for Endpoint connected. ONLINE requires a newly persisted authenticated heartbeat.
5. Click Open Endpoint to inspect LOCAL-LINUX-01, its actual architecture/version and last heartbeat.
6. Choose Start Another Local Endpoint twice to connect LOCAL-LINUX-02 and LOCAL-LINUX-03. Each enrolls separately with its own TLS identity, worker and persistent state. The dialog shows running slots out of three; selecting an existing slot and starting it again reuses that identity.

Repeated starts reuse the agent, enrollment and persistent identity. Stop Local Endpoint terminates only that supervised process, preserving jobs/evidence. Connection becomes stale, then offline after the 90-second heartbeat window. Start again reconnects the same identity. Restarting the launcher container preserves credentials but leaves the agent stopped until the operator starts it again.

The bundled Linux endpoints run inside Docker; LOCAL identifies this location and REAL identifies its genuine agent data. It is not a simulated fixture and does not collect the macOS host.

## Preconfigured Windows endpoint

A prepared Windows VM needs no terminal during a recording. Open **Endpoints → Connect Endpoint → Windows → Start Windows Endpoint**. The UI reports the service's bounded lifecycle and changes to ONLINE only when the native agent's mTLS heartbeat is persisted. Show `WINDOWS-01`, platform, architecture and last heartbeat only when an actual Windows VM is connected.

If the VM has not been prepared, the dialog reports **WINDOWS ENDPOINT NOT CONFIGURED** and exposes Advanced Setup; do not present it as an online endpoint. This development environment has no Windows VM, so omit a live Windows claim from the recording.

## External Endpoint / Advanced Setup

Connect Endpoint → Generate Enrollment retains one-time tokens, public CA download, expiry and native commands. Save the token to a protected file and use the same agent state directory for init, enroll and connect. Use the control-plane CA; never replace it with an untrusted certificate. Native external machines need their own compatible worker and a reachable control-plane TLS address.

For this local stack the enrollment channel is `https://localhost:15052` and authenticated control is `https://localhost:15051`. Replace localhost with the authorized server address for external hosts and configure a certificate valid for that address. Native Windows/Ubuntu support is not replaced by the local convenience runtime; physical Windows execution is not verified by this walkthrough.

## Operator sequence

| Time      | Action                                                              | Demonstrate                                                                                                                                                       |
| --------- | ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0:00–0:25 | Sign in → Command Center                                            | Authenticated user/role, operation flow and Connect / Workbench / New Investigation actions.                                                                      |
| 0:25–0:55 | Endpoints → Connect Endpoint                                        | Start three local endpoints; independent authenticated heartbeats and structured detail.                                                                          |
| 0:55–1:35 | Workbench → Load Example → Combined Investigation → CHECK → COMPILE | Empty editor, actual diagnostics, durable compilation and real Tokens / AST / Typed JIR / LLVM / Plan outputs.                                                    |
| 1:35–2:00 | Build Forge → BUILD 3 VARIANTS                                      | Follow persisted stage gates to READY; verify signed build provenance and bytes, then compare real hashes/structural identities with bounded fixture equivalence. |
| 2:00–2:45 | New Investigation                                                   | Select the named compilation, three real online endpoints and memory mode; review then start. Open actual persisted job completion and evidence.                  |
| 2:45–3:15 | Findings                                                            | Open the sandbox unsigned-process/external-connection conclusion; supporting observations and provenance remain explicit.                                         |
| 3:15–3:45 | Graph → Timeline                                                    | Select a readable process node; filter chronological events and open detail with related analysis links.                                                          |
| 3:45–4:15 | Evidence Vault → Verify integrity                                   | Immediate verification drawer with actual stored/recomputed SHA-256; separate manifest provenance/signature.                                                      |
| 4:15–4:40 | Driver Intelligence → Performance                                   | Collected driver inventory and genuine measured compiler timings. Missing measurements remain unavailable.                                                        |
| 4:40–5:00 | Documentation                                                       | Implemented syntax, compile-valid examples and Open in Workbench.                                                                                                 |

For a real run choose a bounded inventory example. Rich filters/correlation/timeline/export are documented compiler syntax but not supported by the current remote execution bridge. The optional Failure Isolation Scenario is seeded backend data; it is not a default newly executed investigation.

## Truth boundary

REAL means actual compiler work, persisted orchestration, authenticated Rust agent results or stored-byte verification. SANDBOX means backend-generated input with simulation=true. Findings/graph/timeline can be genuinely derived from sandbox observations without those inputs being physical-endpoint measurements. Do not rename forensic process/file names merely because their original data contains a training prefix.

No claims of production readiness, Windows live acceptance, antivirus bypass, driver exploitation or invented quality/performance metrics.

## Rehearsal

```sh
npx playwright test -c playwright.prototype.config.ts
```

The local-endpoint test performs browser-only startup, real TLS enrollment/heartbeat, refresh, duplicate prevention, stop/heartbeat expiry and same-identity restart. The coherence test connects all three actual agents, executes one program across them, compares variants, verifies real artifact bytes and its manifest separately, compiles every documentation example, and checks primary routes. The operator test separately preserves external native enrollment and real execution/compilation/evidence acceptance.

If compilation or integrity fails, inspect the failure; never substitute output or edit hashes. Session expiration requires a fresh sign-in. `make demo-prepare` loads only optional persisted sandbox fixtures, not fake frontend progress.

## Build Forge: repeatable delivery proof

After Workbench CHECK/COMPILE, open Build Forge and select that compilation. Choose three variants, compiler-host target and memory-worker object delivery. An optional 16-hex-digit base seed makes byte/structural identities reproducible. Click BUILD 3 VARIANTS, follow persisted stage results and wait for READY. No endpoint jobs are launched by this action.

Show A/B/C: identical JIR intent, distinct real LLVM identities, structural fingerprints and artifact SHA-256; sizes and compiler profiles come from actual builds. Open Variant Explorer for measured basic-block/function/helper counts. Click Verify build manifest & bytes: Ed25519 signature, provenance and recomputed stored objects must all pass. Click Variant A → Compare variants to show VERIFIED **only for the deterministic compiler fixture**, never universal equivalence. Refresh preserves the run. Rebuild with the same base seed to demonstrate deterministic artifact hashes; timings/timestamps can differ.

Protected literals require operator-provisioned JOCKY_LITERAL_KEY_HEX and JOCKY_LITERAL_KEY_ID in the compiler environment. Do not display keys; do not imply endpoint key distribution or full fleet deployment is implemented. Native endpoint packaging/cross-target rollout are outside this delivery proof.

Targeted verification: `npx playwright test -c playwright.prototype.config.ts tests/prototype/forge.spec.ts`. Native acceptance runs `make verify-native-container`; Build Forge Python tests require an actual `JOCKY_COMPILER_PATH`, otherwise native cases are explicitly skipped.
