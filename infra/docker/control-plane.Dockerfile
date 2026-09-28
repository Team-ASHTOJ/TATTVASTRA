FROM ghcr.io/astral-sh/uv:0.7.16 AS uv
FROM ubuntu:24.04 AS native
ENV DEBIAN_FRONTEND=noninteractive CC=clang-18 CXX=clang++-18
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates cmake ninja-build clang-18 llvm-18-dev libssl-dev libzstd-dev \
    libedit-dev zlib1g-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY CMakeLists.txt ./
COPY native/ native/
RUN cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF \
    -DLLVM_DIR=/usr/lib/llvm-18/lib/cmake/llvm && cmake --build build --parallel 2

FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates python3.12 python3.12-venv libssl3t64 libzstd1 libedit2 \
    zlib1g libxml2 libz3-4 libffi8 libtinfo6 g++ libssl-dev && rm -rf /var/lib/apt/lists/*
COPY --from=uv /uv /usr/local/bin/uv
COPY --from=native /src/build/native/compiler/jockyc /usr/local/bin/jockyc
# LLVM_LINK_LLVM_DYLIB makes jockyc depend on this exact monolithic runtime
# library. Copy only the shared object required by the CLI into the loader's
# default search path; the native build stage retains the full LLVM toolchain.
COPY --from=native /usr/lib/llvm-18/lib/libLLVM.so.18.1 /usr/lib/libLLVM.so.18.1
COPY --from=native /src/build/native/compiler/jocky-worker /usr/local/bin/jocky-worker
COPY --from=native /src/build/native/runtime/libjocky_worker_host.a /opt/jocky-worker/libjocky_worker_host.a
COPY --from=native /src/build/native/runtime/libjocky_runtime.a /opt/jocky-worker/libjocky_runtime.a
COPY native/runtime/include/ /opt/jocky-worker/include/
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY packages/contracts/ packages/contracts/
COPY services/control-plane/ services/control-plane/
RUN uv sync --frozen --all-packages --no-dev --no-editable \
    && useradd --system --uid 10001 jocky \
    && mkdir -p /app/.local && chown -R 10001:10001 /app/.local
USER 10001
ENV JOCKY_COMPILER_PATH=/usr/local/bin/jockyc
ENV JOCKY_WORKER_SDK_PATH=/opt/jocky-worker
EXPOSE 8000
CMD ["/app/.venv/bin/python", "-m", "jocky_control_plane.entrypoint"]
