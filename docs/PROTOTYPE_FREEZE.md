# Submission prototype freeze

Base commit: `232eb3d4b1276bc942ade8ebefa9efd774fe6b37`.
Freeze commit: the commit containing this document, resolved by
`git rev-parse prototype-submission-freeze^{commit}` after acceptance and tagging.
Prototype status: **READY** within the documented simulated recording scope.
Desktop and mobile rehearsals passed. The freeze commit itself is authoritative;
the annotated tag resolves its exact hash without a second documentation commit.

## Submission features

Existing three-endpoint backend scenario, native compiler and persisted builds,
partial-success hunt, correlated finding, graph, timeline, driver inventory,
evidence verification, measured compiler-fixture samples and requirement coverage.
Focused stabilization adds persistent Judge Mode navigation/restart, Workbench
compile access, fixed source timestamps, critical dependency checks, missing icon,
loading/error feedback and durable login tokens before the response is emitted.
Replay events are retained while refresh requests are batched to keep mobile
navigation responsive; only Live Investigation opens the demo event feed.
The pre-existing Windows Makefile interpreter changes are retained for demo use;
generated next-env declarations return to the normal production build form.

## Truth boundary

REAL: native compiler stage output, actual host artifact hashes, backend
persistence/correlation, SHA-256 byte checks and Ed25519 manifest verification.
DEMO/SIMULATED: endpoint inventory/outcomes, process/network/file/driver inputs,
fixture source timestamps and evidence content. No endpoint code runs in replay.
MEASURED: actual persisted timings of the local compiler fixture. No fleet or
physical endpoint performance claim. Unmeasured data remains unavailable.

## Known nonblocking limitations

Host-target artifacts do not prove Windows execution or semantic equivalence.
Driver annotations are training metadata, not sourced vulnerability intelligence.
Compiler inspection uses textarea/JSON output. Reset restores rather than deletes
history. Fresh database loads have genuine new UUIDs and signatures, while repeated
restores preserve identities. Fixture source time is fixed; collection and manifest
signing times reflect actual loading. The Windows foundation aggregate retains
POSIX-only tool paths; scoped submission checks run directly and are recorded in
BUILD_STATUS.md. Upstream test deprecation/color warnings remain visible.

## Deferred final-project work

Full Forge and Compatibility Lab, external integrations, production infrastructure,
Windows live acceptance, certificate lifecycle, hard resource limits, externally
anchored audits, distributed fault/load trials and reporting. No offensive driver,
kernel-tampering, injection or evasion capability is part of the roadmap.

## Exact next step after submission

In a separate post-submission change, run the existing bounded collector/worker
acceptance on an authorized Windows lab endpoint and record actual collector
permission/limitation evidence. Do not begin that work in this freeze.

Recording instructions: [VIDEO_RECORDING_GUIDE.md](VIDEO_RECORDING_GUIDE.md).
