# JOCKY recording guide

Target: 5 minutes 40 seconds. Record at 1366 × 768 or larger, browser zoom 100%.
The walkthrough uses actual product screens, backend persistence and a synthetic
three-endpoint scenario. Close unrelated tabs and notifications before recording.

## Start and reset

Start Docker Desktop, then run from the repository root:

```sh
make demo-up
make demo-prepare
make demo-check
```

Open http://localhost:13000/judge. Sign in as `admin` with the organization UUID
printed by preparation and `JOCKY_BOOTSTRAP_PASSWORD` in the local ignored `.env`.
Never record credentials. Sign in immediately before recording (one-hour session).
These commands operate the existing `jocky-video` Compose stack. Do not set the
historical `jocky-video-closure` project name on this Windows recording instance.

For every take, run `make demo-reset`, or press **Restart Demo** in Judge Mode.
Both invoke the existing idempotent backend seed/restore flow. Restart resets
the guide to Command Center and restores the persisted scenario; it does not
delete history, clear measurements, or claim fresh endpoint execution.
Use **Next / Back** throughout; the guide position survives reload in the same
browser tab. Position is not completion. Manual navigation to a recording screen updates the
chapter; on Judge Mode or other routes, **Open current screen** returns to the
remembered chapter. **Exit guide** returns to normal use.

`make demo-down` stops containers while preserving data. `make demo-up` restores
them. For an empty-database rehearsal, stop the current stack, set a new
`COMPOSE_PROJECT_NAME`, then run startup/preparation. In PowerShell use
`$env:COMPOSE_PROJECT_NAME = 'jocky-video-rehearsal'`; in POSIX shells use
`export COMPOSE_PROJECT_NAME=jocky-video-rehearsal`. Never delete REAL volumes.

Windows prerequisites: Docker Desktop with Linux containers, Node 22+, Python
3.12+, GNU Make, Git Bash, installed npm dependencies and `.venv/Scripts/python.exe`.
Use `npm.cmd` / `npx.cmd` in PowerShell if script execution policy blocks `.ps1`.

## Screen order and narration

| Time      | Screen / action                                                      | Expected visible result and narration                                                                                                                                                                                                              |
| --------- | -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0:00–0:25 | Command Center                                                       | Three simulated endpoints, three real artifacts, one derived finding. “One language links source to explainable evidence; endpoint input here is simulated.”                                                                                       |
| 0:25–1:05 | Workbench: Load prepared demo source, Check, Compile prepared source | `sih-triage` source; real compiler hashes; persisted compilation status SUCCESS. “The native frontend and LLVM backend process this source.” Compile is disabled for edited text; reload the prepared source, or use stage actions to check edits. |
| 1:05–1:35 | Compiler: Load prepared demo source again, AST, Typed JIR, LLVM IR   | Actual compiler JSON / LLVM runtime calls. “Each stage is generated on request.” Do not assume source carries across screens.                                                                                                                      |
| 1:35–1:55 | Variants                                                             | Three fixed seeds and distinct stored SHA-256 hashes. “Host-built artifacts; hashes do not prove Windows execution or semantic equivalence.”                                                                                                       |
| 1:55–2:15 | Endpoints                                                            | WIN-01 and UBUNTU-01 SUCCESS, WIN-02 FAILED. “These are explicit synthetic outcomes, not online agents.”                                                                                                                                           |
| 2:15–2:35 | Live Investigation                                                   | PARTIAL hunt and committed event feed. “One permission failure preserves evidence from the others; this is saved scenario history.”                                                                                                                |
| 2:35–2:55 | Finding: open the finding card                                       | Source observations for unsigned-demo-worker, PID 4100, and connection to 8.8.8.8:443 on WIN-01. “The backend correlates shared provenance.”                                                                                                       |
| 2:55–3:15 | Graph: select Process node                                           | Relationship graph and provenance detail from the same observations. “Follow the process, connection and file relationships.”                                                                                                                      |
| 3:15–3:30 | Timeline: filter `drivers`                                           | Two driver observations at the fixed fixture source time. “Source time is distinct from actual ingestion time.”                                                                                                                                    |
| 3:30–3:50 | Driver Intelligence                                                  | demo-legacy-driver.sys and demo-net-module with simulation/risk labels. “Read-only training inventory, not live CVE assessment or exploitation.”                                                                                                   |
| 3:50–4:25 | Evidence: Verify stored bytes, Verify manifest                       | Backend `integrity_valid: true` and `signature_valid: true` in detail. “Real SHA-256 and Ed25519 checks over explicitly simulated evidence.”                                                                                                       |
| 4:25–5:00 | Performance: Run 3 measured samples                                  | Persisted SUCCESS measurement record; expand details. “Actual compiler-fixture timings on this host, not fleet performance.”                                                                                                                       |
| 5:00–5:40 | Requirement Coverage: filter SAFE-01                                 | Implemented scope, safe mapping and deferred requirements. “The prototype proves this source-to-evidence workflow; production acceptance is separate.”                                                                                             |

## Recovery

- Failed startup: inspect `docker compose --env-file .env -f
infra/docker/prototype.compose.yaml logs --tail 80 control-plane dashboard`.
  Correct the reported prerequisite and rerun `make demo-up`.
- Failed seed, missing LLVM or compilation: stop the take, inspect the saved
  failure through `/forge` and service logs, then retry `make demo-prepare`.
  Never substitute sample output or label failure as success.
- Expired session / API error: stop the take, sign in again, run `make demo-check`,
  then Restart Demo. The prepared scenario is persisted.
- Missing graph/finding/evidence: do not narrate a successful scenario. Run
  `make demo-reset` and `make demo-check`; retry only after those succeed.
- Verification mismatch: retain the displayed failure, stop recording and inspect
  the stored object/manifest. Do not modify digests or disable verification.
- Slow measurements: wait for the actual result, or show an existing persisted
  sample and identify it as a prior run. No invented timing values.

## Truth boundary

- REAL: native compiler stages, host-built artifact identities, backend storage,
  correlation/graph/timeline generation, byte hashing and Ed25519 verification.
- DEMO/SIMULATED: endpoint inventory, job outcomes, process/network/file/driver
  observation inputs, fixture source timestamps and evidence contents.
- MEASURED: actual local compiler-fixture benchmark samples only. Missing
  measurements are unavailable; physical resource or fleet claims are excluded.
- Do not claim live endpoint execution during replay, Windows native acceptance,
  semantic equivalence based on distinct hashes, antivirus bypass, driver
  exploitation, production readiness, or producer authentication from hash alone.

## Rehearsal commands

```sh
make demo-reset
make demo-check
npx playwright test -c playwright.prototype.config.ts
```

On Windows use `npx.cmd`. The existing desktop/mobile walkthrough checks real
compiler actions, evidence, guide navigation/reload, overflow and runtime errors.
Login tracing/video capture stays disabled; post-login screenshots are ignored
under `.cache`. No manual database edits are needed between screens.
