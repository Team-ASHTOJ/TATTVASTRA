# JOCKY compiler frontend

C++20 owns source lexing, parsing, AST, type/capability checks, typed JIR and static plans. LLVM >=18 is mandatory; the reference toolchain is LLVM 18.1.3. The existing ORC self-test executes real machine code through the runtime ABI. Source-to-LLVM lowering and hunt execution remain unavailable.

```sh
make native-build LLVM_DIR=/path/to/llvm/lib/cmake/llvm
build/native/native/compiler/jockyc check examples/basic/system.jky
build/native/native/compiler/jockyc tokens examples/basic/processes.jky --json
build/native/native/compiler/jockyc ast examples/investigations/network-hunt.jky --json
build/native/native/compiler/jockyc jir examples/investigations/full-investigation.jky --json
build/native/native/compiler/jockyc plan examples/investigations/driver-audit.jky --json
ctest --test-dir build/native --output-on-failure
```

On a development host without LLVM headers/GoogleTest/clang-format, use the repository's Ubuntu toolchain:

```sh
make verify-native-container
docker run --rm --entrypoint /src/build/native/native/compiler/jockyc jocky-native:foundation check examples/basic/system.jky
docker run --rm --entrypoint /src/build/native/native/compiler/jockyc jocky-native:foundation plan examples/investigations/full-investigation.jky --json
```

`check`/`jir`/`plan` validate the full source pipeline. `tokens`/`ast` stop at their debugging stage. JSON is deterministic; plans have dispatchable=false and no fabricated runtime results. Unknown/unavailable commands and invalid source exit 1, internal failures exit 70. `--help`, `--version`, `--self-test` remain available. Python can package validated JIR in the existing protobuf document with `scripts/pack_jir.py`; it never interprets the DSL.

`frontend_test.cpp` covers lexer/parser/AST, types, capabilities, both endpoint OS semantics, JIR invariants, pushdown barriers, diagnostics and bounded malformed input. `scripts/test_frontend.py` invokes the actual CLI for every example and compares exact-byte snapshots in `fixtures/compiler`. To intentionally refresh snapshots after reviewing a semantic change, run it with `--compiler <jockyc-path> --update-goldens`; normal tests never rewrite them.

See [LANGUAGE_SPEC](../../docs/LANGUAGE_SPEC.md), [JIR_SPEC](../../docs/JIR_SPEC.md) and [BUILD_STATUS](../../docs/BUILD_STATUS.md) for supported syntax and recorded limits. No native payload loader or fallback interpreter exists.
