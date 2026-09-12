# Benchmark plan

Status: plan only. P0 has no forensic benchmark measurements and publishes no fabricated benchmark charts. The HTTP counter and native toolchain test are real diagnostics, not product performance benchmarks.

## Measurement protocol

Use monotonic clocks for durations, UTC for event provenance. Record source/JIR/artifact/variant hashes, seed, compiler/LLVM versions, target OS/architecture, CPU/RAM, OS/security-product versions, power mode, execution mode, runtime/collector policy, warmup count, repetition count and raw samples. Keep simulation flags and DEMO DATA labels where fixtures are used. Distinguish synthetic workload input from actual measured timing of that workload.

Start with 5 warmups and at least 30 measured repetitions for short local compiler/runtime workloads; these are protocol targets, not completed runs. Long distributed trials use a documented smaller repetition count with raw uncertainty. Report median/p95/min/max and sample count; do not overinterpret p99 from tiny samples. Record failed/cancelled/timed-out runs separately rather than dropping them to improve averages. Compare on the same pinned environment; normalize by workload only when the normalization is explicit.

| Layer         | Metrics                                                                                                             | Instrumentation / correctness oracle                                                         |
| ------------- | ------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Compiler      | lex_ms, parse_ms, semantic_ms, jir_ms, llvm_generation_ms, optimize_ms, aot_compile_ms, jit_compile_ms, peak_memory | Stage timers and worker peak RSS; source corpus and verified IR                              |
| Variant       | uniqueness, artifact bytes, semantic equality, compile/runtime overhead, wrapper/functions/blocks metrics           | SHA-256 of actual artifact; immutable fixture expected results; no guessed structural scores |
| Agent         | idle/active CPU/RAM, bytes read/transmitted, collector duration, job latency                                        | Worker/supervisor resource samples, read accounting, acknowledged transport bytes            |
| Distributed   | time to dispatch/first result/completion, results/sec, evidence bytes/sec, failure rate                             | Committed event timestamps and payload accounting with clock-skew caveat                     |
| Compatibility | completion, correctness, manually observed alerts, runtime, CPU/RAM, notes                                          | Operator-provided product/environment label; no optimization feedback loop                   |

## Workloads and matrix

- **Compiler corpus:** minimal system hunt, process/network projection/filter, bounded join, large allowed literal pool, invalid-source diagnostics. Same source+seed is rebuilt twice; three seeds test diversity.
- **Collectors:** fixed temp-file sizes, controlled localhost sockets, benign helper process, supplied event fixtures, supplied driver-risk metadata. Live host inventories are measured but never used as a deterministic equivalence oracle.
- **Modes/platforms:** native versus ORC on actual Windows and Ubuntu. Record architecture independently; container arm64 results cannot stand in for Windows x86_64.
- **Resource governor:** CPU saturation within permitted wrappers, quota-bound hashing, memory ceilings and deadline/cancel interruption. Measure overshoot and whether enforcement is hard or monitored.
- **Distributed scale:** target 1, 2, 10, 50 simultaneous endpoints, then stress if resources permit. Separate real agents from explicitly simulated load generators. Include 10% disconnect/retry and delayed storage trials.
- **Evidence:** ingest/verify varying observation and artifact sizes, corrupt a copy, measure verification latency and throughput; original evidence remains unchanged.

No fabricated acceptance thresholds: first collect a baseline, propose workload-specific budgets from it, record operator acceptance, then gate regression (initial suggested alert at >10% median regression requires sufficient samples). Language-declared budgets are enforced independent of performance goals. No automatically choosing variants based on AV/EDR alerts.

## Artifacts and implementation order

`benchmark/` owns the runner methodology, `examples/benchmarks/` owns language inputs, `BenchmarkRun`/`CompatibilityRun` own typed metadata. Future runner writes raw JSONL samples and a content-hashed summary/manifest; UI reads persisted records. Charts must link to raw samples. Until runner/collectors/dispatch exist, CLI benchmark returns unavailable and the Performance page shows no measurements.
