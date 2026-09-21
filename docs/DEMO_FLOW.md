# JOCKY idea-submission demo — 4–6 minutes

Current recording instructions and the revised Judge Mode order are in
[VIDEO_RECORDING_GUIDE.md](VIDEO_RECORDING_GUIDE.md). Historical acceptance below
is retained as evidence, not a claim that another host's containers are running.

## Prepare once, record repeatedly

```sh
make demo-up
make demo-prepare
```

This starts an **isolated DEMO** PostgreSQL/API/dashboard stack with separate
`jocky-video` volumes. Existing REAL data is untouched. The native compiler is
built into the API image; first startup needs network access for image/dependency
installation. Subsequent recordings use saved data and local images.

Open **http://localhost:13000/judge**. Sign in with the organization UUID printed
by `make demo-prepare`, username `admin`, and `JOCKY_BOOTSTRAP_PASSWORD` from the
ignored `.env`. Do not show the password or `.env` in the video. Sessions last one
hour; sign in immediately before recording.

“Prepare demo scenario” performs actual compilation and stores the backend
scenario. “Restore prepared scenario” reuses that persisted scenario; it does
not pretend to compile or execute it again. Fixtures use fixed variant seeds,
fixed endpoint names and fixed relationships. UUIDs, cryptographic signatures,
load timestamps and measured timings are genuine per-run values, not fabricated
constants. Reloading the page preserves data.

## Accepted recording instance

The 2026-09-21 closure used fresh volumes under `jocky-video-closure`. That
prepared instance is running on the same URLs above. To operate it, first run:

```sh
export COMPOSE_PROJECT_NAME=jocky-video-closure
```

Then use the ordinary `make demo-up`, `make demo-prepare`, and `make demo-down`
commands. Earlier `jocky-video` volumes remain preserved. Run only one project
on these ports at a time. `make demo-prepare` prints the correct organization ID.

## Recording script

| Time      | Screen/action                                                              | Say/show                                                                                                                                                                                                                                  |
| --------- | -------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0:00–0:30 | Command Center → Judge Mode                                                | “JOCKY: One Language. Every Endpoint. No Noise.” Point to DEMO/SIMULATED. Compilation is real; this repeatable endpoint scenario is synthetic.                                                                                            |
| 0:30–1:20 | Workbench → Load prepared demo source → Check; Compiler Explorer → LLVM IR | A real handwritten frontend, typed JIR and LLVM backend. Change invalid source to demonstrate a compiler diagnostic if time allows. Stage output is produced on request, never illustrative IR.                                           |
| 1:20–1:45 | Variant Explorer                                                           | Three actual stored hashes and fixed seeds. Builds target the local host; simulated Windows inventory does not claim Windows artifact execution. Different hashes alone do not prove semantic equivalence or antivirus bypass.            |
| 1:45–2:20 | Endpoints → Live Investigation                                             | WIN-01 and UBUNTU-01 succeed in the scenario; WIN-02 fails with an explicit limitation. Hunt is PARTIAL and other evidence survives. Events originate in the backend outbox; this is saved scenario history, not live endpoint execution. |
| 2:20–3:15 | Findings → Forensic Graph → Timeline                                       | Click the derived unsigned-process/external-connection finding and a Process graph node. Filter the timeline by `drivers`. Relationships and finding come from stored observations, not UI constants.                                     |
| 3:15–4:10 | Evidence Vault → Verify stored bytes → Verify manifest                     | Actual SHA-256 over stored fixture bytes; actual Ed25519 verification over a simulated manifest. Expand provenance. Optional: use the submitted-observation verifier below to demonstrate a tampered digest.                              |
| 4:10–4:35 | Driver Intelligence                                                        | Read-only simulated driver inventory with risk explanations; no exploitation or kernel modification.                                                                                                                                      |
| 4:35–5:10 | Performance → Run 3 measured samples                                       | Actual compiler-fixture timing samples, explicitly not distributed endpoint benchmarks. Expand the persisted measurement record.                                                                                                          |
| 5:10–5:40 | Requirement Coverage                                                       | Show safe mappings and the difference between the present prototype and final-build acceptance. Close with the unified source-to-evidence story.                                                                                          |

Judge Mode links each chapter. The 14 primary navigation entries are focused on
this walkthrough. Existing cases, scripts, hunts, Forge and reports remain
available by direct route; no working subsystem was removed.

## Recovery and honest boundaries

- If preparation fails, inspect the saved compilation via `/forge` and service
  logs. Fix the prerequisite and retry; failed builds are never labeled ready.
- If LLVM is missing, build fails. No fallback compiler or invented outputs.
- “Restore prepared scenario” is safe to repeat. To record from an empty state,
  use a new Compose project/volumes; do not delete the REAL database.
- `make demo-down` stops the video stack while preserving data. `make demo-up`
  restores it. Redis, MinIO and gRPC are not needed for the simulated recording
  path; their existing REAL-stack configuration is unchanged.
- REAL mode remains a different stack. There is no cosmetic mode switch that
  relabels telemetry. Mode is read from the connected backend on every screen.
- Driver risk annotations are training fixtures, not sourced CVE intelligence.
  Optional adapters, Windows live execution and production controls are deferred.

## Rehearsal checks

```sh
make demo-prepare
PLAYWRIGHT_BROWSERS_PATH=.cache/playwright npx playwright test -c playwright.prototype.config.ts
make verify-foundation
```

The prototype browser suite logs in and traverses the recording screens on
Chromium desktop/mobile, calls the real compiler, verifies evidence, runs the
measured fixture benchmark, and refreshes persisted resources. Traces and video
capture are disabled during automated login to avoid recording credentials.
