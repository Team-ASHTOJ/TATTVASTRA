# Runtime ABI foundation

`include/jocky/runtime.h` declares ABI version 1, opaque context and dataset handles, status codes and required collector boundaries. ABI version reporting is implemented. Collector functions are explicit unavailable boundaries; null contexts/outputs are invalid and no evidence handles are produced.

The next phase supplies the Rust-owned context/collector table, cancellation/resource ledger and observation sink. Memory ownership, schema IDs, per-call policy and cross-language layout tests must be fixed before lowering collector instructions. Do not confuse an exported symbol with an implemented collector.
