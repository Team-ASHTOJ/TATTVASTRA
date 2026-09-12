# Demo flow and Judge Mode

## Current foundation walkthrough

The full judge sequence is **not available**. Start `make dev-api` and `make dev-dashboard`, open Command Center, review explicit unavailable operational metrics, open Architecture / Coverage and filter safe mappings, then open Evidence Vault and paste `fixtures/evidence/simulated-observation.json`. VERIFY INTEGRITY calls the real backend hash utility. The result displays SIMULATED / DEMO and signature NOT CHECKED. Edit one data field without updating the hash and verify again to demonstrate a real mismatch.

The supplied fixture is synthetic data, never endpoint telemetry. Hash recomputation is real functionality performed on labeled synthetic input. Judge Mode currently links only these available states and declares the end-to-end sequence not ready. The ORC toolchain proof is separately available through `make verify-native-container`; it is not a memory-JIT hunt.

## Target 3–5 minute application sequence

| Time budget | Actual state/action                              | Required evidence                                                             | Gate     |
| ----------- | ------------------------------------------------ | ----------------------------------------------------------------------------- | -------- |
| 0:00–0:20   | Problem, architecture, REAL/DEMO selection       | Capability catalog and connected environment labels                           | P0/P9    |
| 0:20–0:40   | Open SIH hunt in Workbench                       | Immutable source version and source hash                                      | P1/P7    |
| 0:40–1:00   | CHECK/COMPILE; inspect AST/JIR/LLVM              | Real diagnostics and stage output/timings                                     | P1–P3    |
| 1:00–1:35   | Generate three variants                          | Distinct actual artifacts, seeds, constant source/JIR hashes                  | P4       |
| 1:35–1:50   | Prove equivalence                                | Pairwise fixture result hashes and PASS/FAIL matrix                           | P4       |
| 1:50–2:25   | PLAN/RUN memory hunt on Windows + Ubuntu         | Approved capabilities/budget; signed per-endpoint jobs; ORC worker mode       | P3/P5/P6 |
| 2:25–2:55   | Live observations and benign fixture finding     | Actual stream, process/socket/file relationships, independent endpoint states | P7       |
| 2:55–3:15   | Timeline and graph                               | Timestamp basis and click-through to evidence                                 | P7       |
| 3:15–3:35   | Driver risk and separate visibility simulator    | REAL DRIVER ANALYSIS versus LAB SIMULATION                                    | P8       |
| 3:35–4:00   | Verify evidence and demonstrate tamper detection | Re-read stored artifact, recompute hash, verify manifest/signature            | P7       |
| 4:00–4:20   | Performance and compatibility                    | Measured samples; operator-observed alert state                               | P8/P9    |
| 4:20–4:40   | Requirement coverage and export                  | Traceable implementation statuses and report                                  | P7/P9    |

## Preconditions and recovery

Before enabling the full sequence: green compiler/semantic tests, three trusted variants, approved lab case, enrolled Windows/Ubuntu endpoints, scoped capability policy, working direct/relay TLS and evidence store, harmless observable fixture lifecycle, valid certificates/signatures, and timing budget rehearsed from raw samples.

If an endpoint disconnects, show partial success and retry with a fresh signed job. If LLVM is unavailable, stop compilation and show the missing toolchain; never emit example IR as if built. If verification fails, preserve the failure in the report. Demo fallback is an explicit switch to a separate simulation namespace, never an automatic substitution. Prebuilt artifacts may be used only when labeled with their actual prior build timestamps and source/toolchain provenance; do not pretend to compile them live.
