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

## Remote (external endpoint) workflow

An external endpoint is a real agent process on a real host, enrolled against the control plane over mTLS. This is the same code path the three local demo agents use; only the host differs.

```sh
cargo build --locked --release -p jocky-agent

# 1. Stable endpoint identity plus encrypted spool, in a state dir you own.
target/release/jocky-agent --state-dir /var/lib/jocky init --organization-id <organization-uuid>

# 2. An ADMIN mints a one-time enrollment token over the HTTP API; the CA is
#    published alongside it. The token is single-use and short-lived.
#      POST /api/control/domain/endpoints/enrollments        {"simulation": false, "capabilities": ["system.read"]}
#      GET  /api/control/domain/endpoints/enrollments/{id}/ca
target/release/jocky-agent --state-dir /var/lib/jocky enroll \
  --enrollment-server <host>:<grpc-port> \
  --server <host>:<grpc-port> \
  --ca /etc/jocky/ca.pem \
  --token-file /etc/jocky/enrollment.token \
  --worker /usr/local/bin/jocky-worker

# 3. Heartbeat, replay durable frames and execute authorized compiler jobs.
target/release/jocky-agent --state-dir /var/lib/jocky connect
```

Enrollment generates a CSR locally and returns a short-lived certificate; the private key never leaves the endpoint. `connect` holds a mutual-TLS channel, sends authenticated heartbeats, and reconnects by replaying durable frames. The control plane records `endpoints.transport_mode` from that authenticated connection, so transport provenance is authoritative and is never inferred from a hostname.

CSR generation uses the OpenSSL CLI by default. Where that binary is absent — a stock Windows host, for example — pass the material instead of relying on it:

```sh
target/release/jocky-agent --state-dir "$env:ProgramData\JOCKY" enroll \
  --enrollment-server <host>:<grpc-port> \
  --server <host>:<grpc-port> \
  --ca control-plane-ca.pem \
  --token-file enrollment.token \
  --transport-key transport.key \
  --csr transport.csr \
  --worker "$env:ProgramData\JOCKY\jocky-worker.exe"
```

`--transport-key` and `--csr` must be supplied together; both must be PEM (an unencrypted private key, and a PKCS#10 request). The key is written into the state directory with the same protection as the generated one, and a key that does not match the request is rejected by the mTLS handshake, so nothing is verified less strictly than in the default path.

## Windows endpoint workflows

### Normal — preconfigured Windows VM

Set `JOCKY_AGENT_PUBLIC_HOST` on the control plane to the name or address the guest dials; the three agent addresses are composed from it and the server certificate is renewed to cover that host, so the guest validates the host it connects to rather than having verification relaxed. `make configure-local` records this machine's LAN address for you.

Extract the `jocky-windows-endpoint` CI bundle on the guest, put `jocky-bootstrap.json` — downloaded from **Endpoints → Connect Endpoint → Windows → Advanced Setup → Prepare** — beside `Install-JOCKY.cmd`, and run it as administrator. It installs the native `jocky-bootstrap.exe` and `jocky-agent.exe`, optionally includes `jocky-worker.exe`, stores the certificate-validated control-plane addresses and bootstrap credential in the protected `%ProgramData%\JOCKY` state directory, installs the CA beside them, and registers the bounded `JockyBootstrap` Windows service. Re-running it keeps the existing endpoint identity.

Normal operation then needs no terminal: **Endpoints → Connect Endpoint → Start Windows Endpoint**. The service polls outward over HTTPS, accepts only START/STOP/WAIT lifecycle responses, enrolls through the existing one-time mTLS flow when necessary, and starts only the colocated JOCKY agent. The dashboard shows ONLINE only after that agent's authenticated heartbeat is persisted.

### Advanced — new Windows machine

`scripts/windows/connect-jocky.ps1` remains the onboarding path for a machine without the preinstalled service. It creates a protected `%ProgramData%\JOCKY` state directory, resolves the CA from `-CaFile` or an HTTPS `-CaUrl`, reads a one-time token from a file, generates a P-256 key and PKCS#10 request with the Windows crypto provider, and runs `init`, `enroll` and `connect`. It never disables certificate verification. Use a control-plane DNS name or IP reachable from the guest and covered by the configured certificate; do not use guest `localhost` for a host-side JOCKY stack.

The agent needs `jocky-worker` on disk (default `/usr/local/bin/jocky-worker`) to execute memory-mode jobs. A missing worker no longer blocks enrollment: the endpoint still enrolls, heartbeats and reports ONLINE, and a compiler-artifact job sent to it is refused with `LLVM execution worker is unavailable`.

## Execution inside the JOCKY worker

Both execution modes run compiler output, and both are driven by the agent's own supervised worker rather than by any foreign process:

- `memory` — the agent spawns `jocky-worker <artifact> <entry_symbol>`. The artifact is LLVM IR text (`artifact_format = llvm-ir`); the worker parses it and adds it to an ORC LLJIT for execution inside that worker process. Reported as `execution_engine = LLVM_ORC_JIT`.
- `native` — the agent executes the linked standalone artifact directly (`artifact_format = native-worker`, `link_status = LINKED`). Reported as `execution_engine = NATIVE_AOT`.

In both modes the artifact hash is re-verified against the job before anything runs, and a mismatch is rejected as `ARTIFACT_HASH`. `worker_pid` and `execution_duration_ms` are measured from the real child process, not synthesized. No mode injects into, hollows, or takes over an unrelated process.

## Collector and evidence behavior

The fixed registry includes system, users/sessions, processes, interfaces/connections/routes, approved-path file metadata/hash, services/startup, events, software, and drivers/modules. Linux uses procfs/sysfs and fixed read-only system utilities where needed. Windows uses fixed non-interactive PowerShell/CIM/NetTCPIP commands. Windows code is cross-compile checked; live Windows acceptance is still required.

Every collected record becomes an `Observation` containing endpoint/job/case/collector identity, collection/source times, platform, data, RFC 8785/SHA-256 integrity hash, and `simulation=false`. An ordered evidence manifest is signed by the endpoint identity. Permission, missing-source and adapter errors are `PARTIAL`, `DENIED`, or `UNAVAILABLE`; they are never converted to an empty successful inventory.

YARA, Volatility 3 and osquery are optional. `collectors` detects their executables. Execution remains unavailable until an explicitly supplied policy-approved input is supported; Volatility will only accept supplied memory images. No memory acquisition or exploit path is present.

## Governor and storage limits

The supervisor enforces one worker at a time, monotonic timeout/cancellation, result bytes, file count, and file/read bytes. Child CPU time and peak RSS are sampled on Linux but not hard-limited; Windows CPU/memory controls and network bytes are unavailable. These fields report `OBSERVED_ONLY` or `UNSUPPORTED`, and `STRICT` admission fails when required hard controls cannot be honored.

Spool payloads use AES-256-GCM with random nonces and record-bound associated data. The SQLite database contains ciphertext plus minimal routing metadata. Linux secrets are created mode `0600`; Windows credential storage/DPAPI integration remains open. `flush-local` acknowledges a record only after its exact bytes are durably created or verified at the sink.

## Not yet operational

- Certificate rotation and production OS credential storage. One-time enrollment, revocation, mTLS heartbeats/jobs/cancellations and reconnect upload receipts are implemented.
- Live Windows lab acceptance (`AGT-01`). Windows CI builds and tests the agent and publishes `jocky-agent.exe`, the bootstrap drives the real enrollment flow, and the compiler emits genuine Windows COFF objects, but no Windows host has been enrolled or executed on.
- Hard CPU/memory/network governance, spool quotas, OpenTelemetry spans.
- Optional-adapter execution.

## Deployment targets

| Target                                | Status                     | Notes                                                                                                                                                                                                                                                                                                                      |
| ------------------------------------- | -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Linux x86_64 / aarch64, external host | Supported                  | `cargo build --locked --release -p jocky-agent`; enroll and connect as above. `cgroup` hard limits remain open, so `STRICT` admission fails where hard controls are required.                                                                                                                                              |
| Windows x86_64, external host         | Enrolls; execution blocked | `scripts/windows/connect-jocky.ps1` enrolls the host over mTLS and it reports ONLINE from its authenticated heartbeat. Compiler-artifact execution additionally needs `jocky-worker.exe`, which requires an LLVM 18+ toolchain, so Windows compiled-job execution is **ENVIRONMENT DEPENDENT** and no Windows job has run. |
| Docker demo agents                    | Supported                  | The prototype stack runs three isolated `jocky-agent` containers (`LOCAL-LINUX-01/02/03`) on Linux/aarch64, each with an independent state volume and its own enrollment. They are demo endpoints on a shared Docker network, not external hosts.                                                                          |

Local Docker demo agents and native external endpoints share the same Rust agent, protocol and evidence path. The difference is only where the process runs; do not read the demo fleet as evidence of external-host deployment.
