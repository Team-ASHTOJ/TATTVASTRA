# Harmless adversary fixture lifecycle — planned

P8 will supply a bounded helper process that creates a temporary test file, binds a localhost socket, emits a clearly synthetic event and cleans up on cancellation. It must run under the operator's existing privileges, with no persistence, credential access, packet payload interception or malware. Its generated records carry simulation=true when used as DEMO evidence.

For the external-IP example, use supplied synthetic connection records with explicit public/test address classification metadata. Do not make external connections merely to satisfy the example. A separate real localhost workflow can demonstrate a benign process-to-socket correlation without claiming public Internet communication.
