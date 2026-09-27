# Installing JOCKY

There is **no installer, no prebuilt binary and no published release**. The repository
publishes no artifacts: `.github/workflows/ci.yml` builds and tests, but pushes nothing to a
registry or release page. Installing JOCKY means building it on (or for) the machine you want to
run it on.

`jockey` is the terminal entry point; `jockyc` is the compiler it drives. Both come out of the
same build.

## What is verified where

| Route                           | Toolchain             | Status                                          |
| ------------------------------- | --------------------- | ----------------------------------------------- |
| Container (`native.Dockerfile`) | Ubuntu 24.04, LLVM 18 | CI-verified (`make verify-native-container`)    |
| Native Linux, Arch              | LLVM 22               | Verified 2026-09-28, 35/35 `ctest`              |
| Native Linux, Ubuntu/Debian     | LLVM 18               | Same source as the container; not run on a host |
| macOS                           | Homebrew LLVM 18+     | Not verified; historically a dev host only      |
| Windows native                  | —                     | Never built. Windows CI is Rust-agent only      |

The `.jky` compiler is the C++20 `native/compiler` tree. It requires LLVM 18 or newer, CMake
3.25+, OpenSSL, and GoogleTest when `BUILD_TESTING=ON`. It is verified on LLVM 18 and 22; the
`llvm_compat.h` shim bridges the `Triple` API change in LLVM 20.

## Route A — container (any PC running Docker)

The only path exercised by CI, and the one that behaves identically on Linux, macOS and Windows.

```sh
git clone https://github.com/Team-ASHTOJ/JOCKEY.git
cd JOCKEY
docker build -f infra/docker/native.Dockerfile -t jockey-native:foundation .
```

The image builds the compiler and runs its own test suite during `docker build`; a failing test
fails the build. The compiler lands at `/src/build/native/native/compiler/jockyc`. Run a hunt
file from the host by mounting its directory:

```sh
docker run --rm -v "$PWD:/work:ro" jockey-native:foundation \
  /src/build/native/native/compiler/jockyc run /work/hunt.jky --execution memory
```

`docker run --rm jockey-native:foundation` with no arguments runs `jockyc --self-test`.

## Route B — native Linux build

Ubuntu 24.04 / Debian, matching the container's LLVM 18:

```sh
sudo apt-get install -y cmake ninja-build clang-18 llvm-18-dev libgtest-dev \
  libssl-dev libzstd-dev libedit-dev zlib1g-dev
cmake -S . -B build/native -G Ninja -DLLVM_DIR=/usr/lib/llvm-18/lib/cmake/llvm \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
make jockey-install
```

Arch, using the distribution LLVM (this is what was verified on 2026-09-28):

```sh
sudo pacman -S --needed cmake clang llvm gtest openssl
make jockey-install
```

`make jockey-install` runs `make native-build` and then symlinks `scripts/jockey` into
`~/.local/bin/jockey`, which must be on your `PATH`. It overwrites an existing `jockey` symlink
there and nothing else. Run `make native-build` alone if you only want the compiler at
`build/native/native/compiler/jockyc`.

Set `JOCKYC` to point the wrapper at a different compiler binary. Point `LLVM_DIR` at your LLVM
CMake package if it is not the default: `-DLLVM_DIR=/usr/lib/llvm-18/lib/cmake/llvm`.

## Route C — Windows

The C++ compiler has never been built or tested on Windows; the `windows-agent` CI job covers the
Rust agent only, not `native/compiler`. `scripts/jockey` is POSIX `sh` and will not run under
`cmd.exe` or PowerShell.

Use Route A (Docker Desktop) or Route B inside WSL2. A native MSVC build is untested territory,
not a supported configuration.

## Using it

```sh
jockey hunt.jky        # compile and execute
jockey check hunt.jky  # frontend validation only
jockey --help          # full jockyc command list
```

A first argument naming a `.jky` file is run; any other argument passes straight through to
`jockyc` (`check`, `tokens`, `ast`, `jir`, `llvm`, `plan`, `compile`, `run`, `variants`,
`variant-info`, `benchmark`).

Local execution uses the deterministic **SIMULATED** fixture collector: the hunt file is compiled
and JIT-executed in process. It is not endpoint evidence, and no Agent host is involved.
