# Bundled real Rust agent plus the existing LLVM execution worker/runtime.
ARG RUNTIME_IMAGE=jocky-control-plane:latest
FROM rust:1.90.0-bookworm AS agent
RUN apt-get update && apt-get install -y --no-install-recommends protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY Cargo.toml Cargo.lock rust-toolchain.toml ./
COPY services/agent/ services/agent/
COPY proto/ proto/
RUN cargo build --locked --workspace

FROM ${RUNTIME_IMAGE}
USER root
RUN apt-get update && apt-get install -y --no-install-recommends openssl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=agent /src/target/debug/jocky-agent /usr/local/bin/jocky-agent
RUN mkdir -p /endpoint && chown 10001:10001 /endpoint
USER 10001
WORKDIR /endpoint
ENTRYPOINT ["jocky-agent"]
CMD ["doctor"]
