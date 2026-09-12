# Security model

## Present security boundary

P0 is a local development scaffold. It has no authenticated remote enrollment, dispatch, tenant persistence, signing service, encrypted spool or production relay. Settings reject production and TRUSTED_RELAY, the API/dashboard bind to loopback by default, and readiness remains 503. A valid schema, signature-shaped field, or matching hash is **not** evidence of a trusted endpoint. The stateless verifier checks only a submitted observation's content hash.

## Target trust and authorization

Each endpoint has an enrolled asymmetric identity and organization binding. Enrollment consumes a short-lived, single-use operator-issued token and signs a CSR after authorization. mTLS authenticates ongoing transport; certificates rotate and can be revoked. API sessions use short-lived identity-provider credentials and server-enforced viewer/analyst/operator/administrator roles. Organization and case scope apply to every read, mutation, stream, report and object download; UI checks are never authorization.

A signed job binds schema version, organization, case, endpoint, plan, source/JIR/artifact hashes, variant, execution mode, granted capabilities, budget, nonce, issuance/expiry and simulation state. Agent admission verifies canonical bytes and Ed25519 signature against its trust store, certificate/audience bindings, clock skew and expiry, durable replay ledger, capability intersection, artifact provenance and resource enforceability. Replayed/expired/mismatched work is rejected before opening a worker. Schema `signature.status` is descriptive only; it cannot establish cryptographic trust.

Nonces are cryptographically random 256-bit values. Consume a nonce transactionally in the persistent ledger before execution; store the resulting job receipt for idempotent delivery acknowledgements. Restart cannot reset replay history. Retain ledger entries through expiry plus maximum skew/retry grace. Retry creates a new job, nonce and signature; a duplicate delivery of the same job returns the existing receipt rather than executing again.

## Execution boundary and governor

Compile only the restricted JOCKY grammar and typed JIR. No arbitrary native payload, shell execution, foreign function import or user-selected DLL symbol is accepted. Native artifacts require compiler provenance and verified signatures. ORC resolves only the runtime ABI symbols registered by the Agent host. Worker isolation, executable-memory policy and lack of arbitrary pointer operations constrain the JIT trust boundary; JIT alone is not a sandbox.

CPU quotas, memory ceilings and deadline termination are applied to an Agent-owned worker. Linux uses cgroup v2 where delegated; Windows uses Job Objects and documented limits. Collector read wrappers account I/O and check cancellation/deadlines. Scope includes hashing bytes and bounded evidence output; telemetry states sampling windows and possible overshoot. Without enforceable hard limits, strict policy rejects the plan; an operator may select an explicitly documented monitored policy only when supported. No silently advisory enforcement.

OS collectors are read-only and least-privileged. Permission failure is evidence about availability, not proof of an empty process/driver inventory. File access checks approved roots, symlinks and file identity before/after reads. Executable hashes/signature status preserve unknown and changed-during-read cases. No kernel modification, callback removal, injection into unrelated processes, escalation or installed persistence.

## Canonical evidence and signatures

The wire content is schema-normalized JSON with RFC 8785 canonicalization and SHA-256. Parse with strict contract validation, reject unknown fields, normalize timestamps via the schema serializer, include schema/simulation/provenance fields, and exclude only the object's own `integrity_hash` when hashing observations or audit events. UTF-8, JSON number limits, nulls and timezone representation are part of the versioned contract. Cross-language hosts must pass golden byte/digest vectors; direct protobuf encoding is never signed.

Manifests include exact ordered observation hashes, source/JIR/LLVM/artifact identity and collection times. Signing signs canonical manifest bytes excluding the signature object, with a versioned domain separator such as `JOCKY:manifest:v1\n`. Jobs use a different domain separator. Signing implementation and vectors are P4/P5 work. A client-provided VERIFIED status cannot bypass verification.

Audit hashes bind organization, sequence, previous hash, actor/action/time/resource/data and simulation state. Genesis previous hash is 64 zero hex characters. The P0 chain primitive rejects gaps, reorderings, mixed organizations and content edits. An empty list does not verify. Hash chains alone cannot detect tail truncation or wholesale attacker recomputation; production needs signed externally stored checkpoints and a trusted expected sequence/head. Durable append transactions and checkpoint verification are P7/P10 work.

## Encrypted literal pool and local spool

Use AES-256-GCM or ChaCha20-Poly1305 from established libraries. A manifest records algorithm, key ID, encrypted pool digest and nonce policy, never key bytes. Separate literal-pool and spool keys using independent random keys or standard context-separated KDFs. Runtime tokens are injected through the trusted configuration channel and never placed in source or generated artifacts.

Each encryption under a given key uses a unique nonce. Never derive an AEAD nonce from the variant seed alone. Associated data binds schema, source/JIR identity, case scope, pool ID and algorithm. A new pool gets a fresh nonce and random key or unique per-key nonce; persist the immutable encrypted pool as a build input. Rebuilding the same full inputs (including pool bytes/key ID) is reproducible. Fresh encryption creates different input bytes, so source+seed equality alone cannot promise identical encrypted artifacts. This explicit exception prevents insecure deterministic encryption from being used to satisfy reproducibility.

Decrypt only approved forensic constants in worker memory; minimize lifetime, redact logs/errors, and zeroize owned secret buffers where libraries permit. Scan stored artifacts for known sensitive test literals when enabled; wrong key, nonce/AAD alteration and tag tampering must fail closed. This feature protects forensic configuration; it is not payload concealment. P0 provides metadata validation only, not encryption.

SQLite spools encrypted record payloads and minimal non-sensitive routing metadata, with per-agent quotas and durable upload receipts. Keys live in OS credential storage or operator-provisioned files with restricted ACLs, outside SQLite. Offline expiry/cancellation is checked before reconnect execution. Evidence retention/erasure policies account for backups and spool copies.

## Transport, fixtures and compatibility

DIRECT uses declared TLS endpoints. TRUSTED_RELAY uses a legitimate reverse proxy/API gateway with correct host/certificate identity and authenticated upstream transport. Do not use domain-fronting or covert SOCKS. Reject unauthenticated forwarded identity headers. The local nginx template demonstrates routing only until end-to-end identity tests pass.

Fixture services emit `simulation=true` plus a label for every synthetic datum; derived findings/timeline/report/graph entries inherit simulation. Isolation is enforced at ingestion and job policy, not merely by color. Driver Intelligence displays REAL DRIVER ANALYSIS separately from LAB SIMULATION. Compatibility Lab records operator observations without optimizing code against security product outcomes.
