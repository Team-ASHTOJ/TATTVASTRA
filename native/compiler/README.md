# Compiler foundation

The only executable compiler behavior today is `--version`, `--help` and `--self-test`. The self-test creates a real LLVM IR function, verifies the module, compiles it with ORC and calls the machine code. It returns the runtime ABI version and proves the native toolchain is usable. It is not a JOCKY parser or hunt runner.

All source commands fail with JOCKY_E_FRONTEND_UNAVAILABLE (exit 69). Missing LLVM fails CMake configuration. No no-LLVM build option, Python interpreter, fabricated AST/JIR/LLVM dump or arbitrary native loader exists. Next phase is the handwritten lexer/parser and typed JIR specified in `docs/LANGUAGE_SPEC.md` and `docs/JIR_SPEC.md`.
