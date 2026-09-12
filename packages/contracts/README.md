# Contract authority

Edit Pydantic modules in `src/jocky_contracts`, then run `make contracts`. The generated JSON Schema and TypeScript declarations are committed and checked for drift. Proto framing is independently versioned in `proto/jocky/v1/agent.proto`; its canonical JSON documents use these schemas.

Pydantic conditional refinements (simulation labels, signature material, encryption metadata, collection chronology, job issuance/expiry and semantic-test state) are not fully represented by structural TypeScript declarations. A consumer must not treat static typing as validation. Rust admission must implement schema/refinement/identity/signature checks and pass cross-language golden vectors before any dispatch feature is enabled. Current Rust support verifies protobuf framing only.

`fixtures/evidence/simulated-observation.canonical.json` contains the exact RFC 8785 bytes used to compute the fixture observation hash, excluding integrity_hash. It is deliberately excluded from formatting. Hashing includes explicit nulls, schema_version, provenance and normalized timestamps. The fixture is SIMULATED and its hashes do not claim compiler execution.
