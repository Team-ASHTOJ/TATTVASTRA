# Agent foundation

`cargo run -p jocky-agent -- doctor` reports actual build host OS/architecture and the absence of operational collectors/execution. Tokio runtime, tonic/prost generation, structured tracing, SQLite and target-specific dependencies are established. No endpoint is enrolled, no heartbeat is fabricated and no job listener is started.

Rust builds require the pinned toolchain and protoc. `make verify-agent-container` supplies them on hosts lacking Rust. Docker Linux arm64 tests do not establish Windows execution; the Windows CI job is configured but must run independently. The protocol method is Exchange to avoid tonic's generated transport constructor name `connect`.
