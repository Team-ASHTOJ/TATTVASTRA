# JOCKY native compiler

The C++20 frontend lowers typed JIR to verified LLVM IR. LLVM 18+ is mandatory. Generated code
calls only the JOCKY runtime ABI: eleven fixed collector functions and a closed analysis/evidence
dispatcher. There is no native payload loader or fallback interpreter.

```sh
jockyc check examples/basic/system.jky
jockyc llvm examples/basic/system.jky
jockyc compile examples/basic/system.jky --target host --execution native --output system.o
jockyc run examples/basic/system.jky --execution memory --json
jockyc variants examples/basic/system.jky --count 3 --json
jockyc variant-info system.o
jockyc benchmark examples/basic/system.jky --count 3 --json
```

`compile` emits a host TargetMachine object plus `<output>.manifest.json`; unsupported targets are
rejected. `run` uses LLVM ORC in the current JOCKY process and requires no temporary executable.
Until an authorized Agent host is integrated, CLI execution uses the explicitly labeled
deterministic SIMULATED fixture collector. `variants` emits actual objects, verifies each through
ORC against the same fixture, and fails if normalized semantic hashes differ.

`runtime { protect_literals true }` encrypts compiler configuration with AES-256-GCM. Provide
`JOCKY_LITERAL_KEY_HEX` (64 hex digits) and `JOCKY_LITERAL_KEY_ID`; key bytes never enter the IR,
object, manifest, or logs. Fresh encryption uses a random 96-bit nonce, so reproducibility requires
reusing the immutable encrypted pool input as described in the security model.

Run `ctest --test-dir build/native --output-on-failure`. The backend suite covers fixed ABI calls,
same-seed reproduction, distinct variants/objects, real ORC execution, fixture equivalence,
authenticated literal decryption, and tag tampering.
