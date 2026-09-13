# Agent runtime

The Rust Agent supports an honest local standalone mode for endpoint development and acceptance. It never claims that a server is connected. All collector output comes from the current host and carries `simulation=false`.

## Local workflow

```sh
cargo build --locked -p jocky-agent
target/debug/jocky-agent --state-dir build/agent-state init
target/debug/jocky-agent --state-dir build/agent-state doctor
target/debug/jocky-agent --state-dir build/agent-state collectors
target/debug/jocky-agent --state-dir build/agent-state collect system
target/debug/jocky-agent --state-dir build/agent-state collect processes --limit 25
target/debug/jocky-agent --state-dir build/agent-state collect connections --limit 25
```

Create and execute a durable signed local fixture:

```sh
target/debug/jocky-agent --state-dir build/agent-state fixture-job \
  --output build/local-job.json --collectors system,processes,connections
target/debug/jocky-agent --state-dir build/agent-state run --job build/local-job.json
target/debug/jocky-agent --state-dir build/agent-state spool list
target/debug/jocky-agent --state-dir build/agent-state spool flush-local \
  --output build/exported-spool
```

The fixture contains a random 256-bit nonce and Ed25519 signature from the state directory's local-development authority. Re-delivering it returns `DUPLICATE` plus the original receipt. This fixture authority is for standalone development, not remote enrollment.

## Collector and evidence behavior

The fixed registry includes system, users/sessions, processes, interfaces/connections/routes, approved-path file metadata/hash, services/startup, events, software, and drivers/modules. Linux uses procfs/sysfs and fixed read-only system utilities where needed. Windows uses fixed non-interactive PowerShell/CIM/NetTCPIP commands. Windows code is cross-compile checked; live Windows acceptance is still required.

Every collected record becomes an `Observation` containing endpoint/job/case/collector identity, collection/source times, platform, data, RFC 8785/SHA-256 integrity hash, and `simulation=false`. An ordered evidence manifest is signed by the endpoint identity. Permission, missing-source and adapter errors are `PARTIAL`, `DENIED`, or `UNAVAILABLE`; they are never converted to an empty successful inventory.

YARA, Volatility 3 and osquery are optional. `collectors` detects their executables. Execution remains unavailable until an explicitly supplied policy-approved input is supported; Volatility will only accept supplied memory images. No memory acquisition or exploit path is present.

## Governor and storage limits

The supervisor enforces one worker at a time, monotonic timeout/cancellation, result bytes, file count, and file/read bytes. Child CPU time and peak RSS are sampled on Linux but not hard-limited; Windows CPU/memory controls and network bytes are unavailable. These fields report `OBSERVED_ONLY` or `UNSUPPORTED`, and `STRICT` admission fails when required hard controls cannot be honored.

Spool payloads use AES-256-GCM with random nonces and record-bound associated data. The SQLite database contains ciphertext plus minimal routing metadata. Linux secrets are created mode `0600`; Windows credential storage/DPAPI integration remains open. `flush-local` acknowledges a record only after its exact bytes are durably created or verified at the sink.

## Not yet operational

- Remote one-time enrollment, mTLS heartbeats/jobs/cancellations, certificate rotation, and reconnect upload receipts.
- Loading signed compiler-generated AOT objects or ORC modules in the Agent worker. The compiler's current ORC host remains a clearly labeled SIMULATED fixture and is never accepted as REAL evidence.
- Hard CPU/memory/network governance, spool quotas, OpenTelemetry spans, and production OS credential storage.
- Live Windows lab acceptance and optional-adapter execution.
