# JOCKY runtime ABI v2

`include/jocky/runtime.h` is a versioned C ABI: opaque context, fixed-width dataset handles,
status/error views, and explicit retain/release ownership. The host supplies a v1 callback table;
no STL, exception, arbitrary symbol, OS handle, or native payload crosses the boundary.

The fixed collector surface covers system information, users, processes, interfaces,
connections, routes, file metadata/hash, services, events, and drivers. Analysis/evidence work
uses one closed opcode allowlist. The runtime copies encrypted-pool/key inputs, cleanses owned key
and decrypted buffers, and authenticates AES-256-GCM before exposing one instruction's canonical
configuration to the host callback.

The built-in fixture host is deterministic and always reports `simulation=true` through its
fixture API. It exists for compiler equivalence tests and local `jockyc run`; it is not a REAL
endpoint collector. Production collectors remain Rust-hosted behind the same callback contract.
