FROM rust:1.90.0-bookworm AS build
RUN apt-get update && apt-get install -y --no-install-recommends protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY Cargo.toml Cargo.lock rust-toolchain.toml ./
COPY services/agent/ services/agent/
COPY proto/ proto/
RUN cargo fmt --all -- --check && cargo build --locked --workspace \
    && cargo test --locked --workspace \
    && cargo clippy --locked --workspace --all-targets -- -D warnings \
    && cargo run --locked -p jocky-agent -- doctor
CMD ["/src/target/debug/jocky-agent", "doctor"]
