# JOCKY

**One Language. Every Endpoint. No Noise.**

JOCKY is an independent forensic DSL, typed JIR, mandatory LLVM compiler, build-diversity system, and distributed evidence platform for Windows and Ubuntu.

This repository includes the engineering foundation, C++20 JOCKY frontend/JIR/LLVM AOT+ORC compiler, and a local standalone Rust endpoint runtime. On supported hosts the Agent performs real read-only collection, signed-job admission, normalized signed evidence, resource supervision and encrypted offline spooling. Remote enrollment/transport, control-plane ingestion, compiler-artifact execution inside the Agent, persistent evidence vault, and full Judge Mode remain incomplete. An available route or contract does not imply the corresponding subsystem works.

## Start locally

Requires Python 3.12+, uv, Node 22+, and npm. Rust 1.90, protobuf, CMake 3.25+, LLVM 18 development files, and GoogleTest are required for host native/agent builds. Docker provides isolated alternatives.

```sh
make bootstrap
make dev-api
# In another terminal:
make dev-dashboard
```

Open <http://127.0.0.1:3000>. API documentation: <http://127.0.0.1:8000/docs>. The dashboard fetches actual capability status. An unavailable API displays a connection error and retry; it never falls back to synthetic endpoints.

The default is REAL mode with **no operational endpoint inventory**. `JOCKY_MODE=DEMO make dev-api` declares intended demo mode but does not manufacture fixtures or make execution available. No remote authentication is implemented; the scaffold binds to loopback and refuses production/relay environment settings.

## Run a hunt from the terminal

```sh
make jockey-install   # builds jockyc, links scripts/jockey into ~/.local/bin
jockey hunt.jky       # compile and execute the hunt file
jockey check hunt.jky # frontend validation only
jockey --help         # full jockyc command list
```

A first argument naming a `.jky` file is run; any other argument is passed straight through to `jockyc` (`check`, `tokens`, `ast`, `jir`, `llvm`, `plan`, `compile`, `run`, `variants`, `variant-info`, `benchmark`). Local execution uses the deterministic SIMULATED fixture collector: the hunt file is compiled and JIT-executed in process, and is not endpoint evidence. Set `JOCKYC` to point at a different compiler binary. For other machines and platforms, see [installing JOCKY](docs/INSTALL.md).

## Verify

```sh
make verify-foundation  # Python/TS, format/lint, schemas, tests, packages, Next build
make test-e2e          # actual API + browser; install Chromium with make browser-install
make verify-native-container
make verify-agent-container
make configure-local  # unique credentials in ignored .env; never overwrites existing .env
make infra-check
```

`make verify` requires all host toolchains and fails when they are missing. `make verify-containers` uses Docker for native/Rust and local tooling for web/Python. See [BUILD_STATUS](docs/BUILD_STATUS.md) for the exact checks run and what remains unverified. `make help` lists operational commands. `make infra-up` starts only local backing services; `make stack-up` adds the scaffold API and dashboard. Neither starts an operational forensic fleet.

For an honest local endpoint run, see [Agent runtime](docs/AGENT_RUNTIME.md). The shortest flow is `jocky-agent init`, `jocky-agent doctor`, then `jocky-agent collect system` (or `processes` / `connections`).

## Repository

| Path                                         | Responsibility                                                                 |
| -------------------------------------------- | ------------------------------------------------------------------------------ |
| `native/compiler`                            | C++20 frontend, typed JIR/static plans; real ORC toolchain probe               |
| `native/runtime`                             | Versioned C ABI; collector calls explicitly unavailable                        |
| `services/agent`                             | Rust identity/policy, real collectors, worker governor, signed evidence/spool  |
| `services/control-plane`                     | FastAPI status, error boundaries, stateless verification, persistence baseline |
| `apps/dashboard`                             | Next.js console shell, coverage browser, observation verifier                  |
| `packages/contracts`                         | Pydantic source of truth; generated JSON Schema and TypeScript                 |
| `packages/jocky-language`, `packages/ui`     | Editor vocabulary and shared UI primitives                                     |
| `proto`                                      | Agent transport schema; no active remote gRPC client/server yet                |
| `infra`                                      | Local Compose, reverse-proxy template, monitoring, native/Rust builds          |
| `examples`, `fixtures`, `benchmark`, `tests` | Language acceptance inputs, labeled fixture data, validation                   |

Start with [AGENTS.md](AGENTS.md), [architecture](docs/ARCHITECTURE.md), [traceability](docs/REQUIREMENT_TRACEABILITY.md), and [definition of done](docs/DEFINITION_OF_DONE.md).
