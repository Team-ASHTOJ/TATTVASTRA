# Threat model

Status: design review baseline. Mitigations below are required targets; current implementation coverage is in BUILD_STATUS.md. P0 does not claim production hardening.

## Assets and boundaries

Assets: endpoint identities, forensic source/configuration, signing and AEAD keys, job authorization, source/JIR/artifact lineage, raw evidence, case privacy, audit checkpoints, availability and measured benchmark correctness.

Boundaries: browser → API; API → database/object store/queue; Forge → compiler worker; control plane → direct/relay transport → agent; agent supervisor → native/JIT worker → OS collectors; offline spool → ingestion; fixture namespace → real evidence namespace; imported risk metadata → driver findings.

Adversaries include unauthenticated network clients, malicious or compromised operators, a compromised endpoint, tampered build/storage dependencies, malformed JOCKY source, untrusted evidence/imported metadata and accidental lab/demo misuse. A compromised kernel can falsify user-space collection; JOCKY must preserve that limitation rather than promise complete visibility.

| Threat                                           | Impact                               | Required mitigation / acceptance                                                                           |
| ------------------------------------------------ | ------------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| Endpoint impersonation / rogue enrollment        | Fabricated trusted evidence          | One-time enrollment, mTLS, CSR/organization binding, revocation; reject wrong identity                     |
| Job replay / stale queued work                   | Duplicate or unauthorized collection | Durable nonce receipt, expiry/skew, signed audience; restart/replay tests                                  |
| Operator crosses tenant or case                  | Evidence disclosure/tampering        | RBAC and database/object/stream scoping; negative authorization matrix                                     |
| Native payload disguised as variant              | Arbitrary endpoint execution         | Compiler-only registry, hash/signature and JIR/ABI validation; reject arbitrary binaries                   |
| Malformed source stresses compiler               | Resource exhaustion or memory fault  | Input/token/depth bounds, worker limits, sanitizer/fuzz corpus; predictable errors                         |
| Generated JIT code escapes policy                | Excessive OS access                  | Restricted DSL, no arbitrary pointers/imports, ABI allowlist, OS worker isolation; denied capability tests |
| Runtime budget bypass                            | Endpoint instability                 | Enforced worker CPU/RAM/deadline, accounted I/O, kill escalation; bounded-overshoot tests                  |
| Artifact/configuration tamper                    | Wrong collection or secret leakage   | Signed digest lineage, AEAD AAD/tag verification, plaintext scan; corruption tests                         |
| Nonce reuse in encryption                        | Disclosure or forgery                | Unique per-key nonce allocation, immutable encrypted pool inputs; collision/reuse negative tests           |
| Spool theft / lost acknowledgements              | Case disclosure / evidence loss      | AEAD encrypted payloads, restricted key storage, quotas, durable idempotent receipts                       |
| Evidence hash rewritten by attacker              | False authenticity claim             | Signature and identity verification in addition to hash; UI scopes verification explicitly                 |
| Audit tail removed or history recomputed         | Undetected rollback                  | Signed external sequence/head checkpoints; demonstrate tail-truncation detection                           |
| Forwarded identity/header spoofing through relay | Endpoint impersonation               | mTLS passthrough or authenticated protected identity assertion; strip public spoofed headers               |
| PID reuse, symlinks, changing files              | Incorrect process/file relationships | Boot ID/PID/start identity, approved-path opening, before/after metadata; race fixtures                    |
| Permission-denied inventory treated as empty     | False negative findings              | Availability/status per collector and field; unknown != unsigned/absent                                    |
| Simulated data reaches real investigation        | False judge/operator claims          | Required provenance bit/label, namespace/job-mode checks, derived propagation tests                        |
| Imported driver/CVE metadata is stale or hostile | Wrong risk verdicts / parser DoS     | Bounded import, source digest/version/date, unknown status, no executable import                           |
| Benchmark or compatibility metric fabricated     | Misleading product claim             | Raw samples and environment labels, null for absent data, manual observed alert state                      |
| Evidence rendered as HTML or executable content  | Browser compromise                   | Text escaping, no raw HTML rendering, bounded JSON, scoped downloads and CSP hardening                     |
| Dependency/build image compromise                | Supply-chain execution               | Lockfiles, release image digests/SBOM/signature review, minimum CI permissions                             |

## Residual risks and release gates

An authorized collector can encounter sensitive file paths, usernames and connections; case policy must minimize collection and control retention. Endpoint root/kernel compromise defeats absolute completeness claims. Clock skew changes source chronology; retain source time, collection time and basis instead of inventing precision. JIT compatibility varies with platform executable-memory policy and security products; record observed behavior without bypass promises.

P0 local API has no authentication/rate limiting for remote use and no persistent trust store. Its stateless hash utility permits an attacker to recompute a digest, by design; it cannot authenticate a producer. Production is blocked until negative mTLS/RBAC/replay tests, signed artifact checks, budget enforcement, encrypted spool, tenant/object isolation, externally anchored audits and independent Windows/Ubuntu execution pass. No hypothetical attack requirement justifies operational exploitation code.
