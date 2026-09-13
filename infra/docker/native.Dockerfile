FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates cmake ninja-build clang-18 clang-format-18 llvm-18-dev \
    libgtest-dev libzstd-dev libedit-dev zlib1g-dev && rm -rf /var/lib/apt/lists/*
ENV CC=clang-18 CXX=clang++-18
WORKDIR /src
COPY CMakeLists.txt .clang-format ./
COPY native/ native/
COPY examples/ examples/
COPY fixtures/compiler/ fixtures/compiler/
COPY scripts/test_frontend.py scripts/test_frontend.py
COPY scripts/format_native.py scripts/format_native.py
RUN python3 scripts/format_native.py --check \
    && cmake -S . -B build/native -G Ninja -DLLVM_DIR=/usr/lib/llvm-18/lib/cmake/llvm \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON \
    && cmake --build build/native --parallel 2 \
    && ctest --test-dir build/native --output-on-failure \
    && build/native/native/compiler/jockyc --self-test
CMD ["/src/build/native/native/compiler/jockyc", "--self-test"]
