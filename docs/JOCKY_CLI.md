# The `jocky` command reference

`jocky` is the terminal entry point for this checkout. It invokes `jockyc`, the C++20 compiler in
`native/compiler`, and adds no compiler behaviour of its own: every composed command below runs an
existing `jockyc` subcommand and re-presents the fields that subcommand already emits. Nothing here
parses `.jky` source, infers a type, resolves a capability or hashes a source file on the
compiler's behalf.

For installing the compiler and the launcher, see [INSTALL.md](INSTALL.md).

## What runs where

|                         | Local compiler / fixture                                               | Real endpoint / control plane                                    |
| ----------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------------- |
| What it is              | `jockyc` lowering, AOT objects and in-process LLVM ORC execution       | The Rust agent on an enrolled host and the FastAPI control plane |
| Which commands reach it | Everything in this document                                            | Nothing in this document                                         |
| Evidence status         | `SIMULATED` deterministic compiler fixture — **not endpoint evidence** | Not reachable from `jocky` today                                 |

`jocky run` executes compiler-generated code in this process against a clearly labelled
deterministic fixture collector. It does not contact an endpoint, does not enlist an agent, and its
result hash is not evidence about any real machine. The control-plane routes that do produce real
endpoint evidence exist under `/api/v1` in `services/control-plane`, but they require an
authenticated tenant session the launcher does not carry — see
[NOT EXPOSED YET](#not-exposed-yet).

## Status table

| Command                                               | Purpose                                            | Backend / source                | Status                |
| ----------------------------------------------------- | -------------------------------------------------- | ------------------------------- | --------------------- |
| `jocky <file.jky>`                                    | Compile and run a hunt file                        | `jockyc run --execution memory` | AVAILABLE             |
| `jocky doctor`                                        | Report environment readiness                       | local probes only               | AVAILABLE             |
| `jocky check <file.jky>`                              | Frontend validation                                | `jockyc check`                  | AVAILABLE             |
| `jocky tokens <file.jky>`                             | Token stream                                       | `jockyc tokens`                 | AVAILABLE             |
| `jocky ast <file.jky>`                                | Parsed program                                     | `jockyc ast`                    | AVAILABLE             |
| `jocky jir <file.jky>`                                | Typed JIR module                                   | `jockyc jir`                    | AVAILABLE             |
| `jocky plan <file.jky>`                               | Static execution plan                              | `jockyc plan`                   | AVAILABLE             |
| `jocky llvm <file.jky>`                               | Lowered LLVM IR + manifest                         | `jockyc llvm`                   | AVAILABLE             |
| `jocky compile <file.jky> --output <p>`               | Emit an AOT object + manifest                      | `jockyc compile`                | AVAILABLE             |
| `jocky run <file.jky>`                                | Lower and execute in process                       | `jockyc run`                    | AVAILABLE             |
| `jocky variants <file.jky> --count N`                 | Persist N variants and manifests                   | `jockyc variants`               | AVAILABLE             |
| `jocky variant-info <path>`                           | Read an artifact's manifest                        | `jockyc variant-info`           | AVAILABLE             |
| `jocky benchmark <file.jky> --count N`                | Bounded fixture benchmark                          | `jockyc benchmark`              | AVAILABLE             |
| `jocky caps <file.jky>`                               | Declared capabilities                              | `jockyc jir`                    | COMPOSED              |
| `jocky budget <file.jky>`                             | Effective budgets, marked declared/default         | `jockyc jir` + `jockyc ast`     | COMPOSED              |
| `jocky types <file.jky>`                              | Declared result schema per instruction             | `jockyc plan`                   | COMPOSED              |
| `jocky metrics <file.jky>`                            | Structural lowering metrics                        | `jockyc llvm`                   | COMPOSED              |
| `jocky fingerprint <file.jky>`                        | Compiler-emitted hashes and structural fingerprint | `jockyc llvm`                   | COMPOSED              |
| `jocky diverge <file.jky> --count N`                  | N variants with the evidence they differ           | `jockyc variants`               | COMPOSED              |
| `jocky diff <file.jky> --seed-a A --seed-b B`         | Two seeds compared structurally                    | `jockyc llvm` ×2                | COMPOSED              |
| `jocky equivalence <file.jky> --count N`              | Fixture semantic-equivalence evidence              | `jockyc variants`               | COMPOSED              |
| `jocky forge <file.jky> --count N`                    | One AOT object per deterministic seed              | `jockyc compile` ×N             | COMPOSED              |
| `jocky pipeline <file.jky> --count N`                 | End-to-end demo sequence                           | composition                     | COMPOSED              |
| `jocky verify <path>`                                 | Artifact bytes against the manifest SHA-256        | `jockyc variant-info`           | COMPOSED              |
| `jocky manifest <path>`                               | Print a variant manifest                           | `jockyc variant-info`           | ALIAS                 |
| `--execution jit`                                     | Spelled alias of `memory`                          | `jockyc` option                 | ALIAS                 |
| `--dry-run`                                           | Maps `run` onto the existing `plan` stage          | `jockyc plan`                   | ALIAS                 |
| `--target linux\|windows\|arm64`                      | Target aliases                                     | `jockyc` option                 | ALIAS                 |
| `--target all`                                        | Both cross targets (`forge`, `pipeline`)           | composition                     | COMPOSED              |
| `jocky compile --target <cross>`                      | Cross-target object emission                       | `jockyc compile`                | ENVIRONMENT DEPENDENT |
| `jocky pipeline --target <cross>`                     | Cross-target compilation stages                    | composition                     | ENVIRONMENT DEPENDENT |
| `jocky cfg <file.jky>`                                | Control-flow graph                                 | —                               | NOT EXPOSED YET       |
| `jocky symbols <file.jky>`                            | Symbol table                                       | —                               | NOT EXPOSED YET       |
| `jocky seal <path>`                                   | Sign a manifest                                    | —                               | NOT EXPOSED YET       |
| `jocky endpoints\|findings\|timeline\|drivers\|relay` | Control-plane inspection                           | —                               | NOT EXPOSED YET       |
| `jocky hunt\|collect`                                 | Endpoint dispatch and collection                   | —                               | NOT EXPOSED YET       |
| `--endpoint`, `--transport`                           | Endpoint and relay execution                       | —                               | NOT EXPOSED YET       |

## Backend selection

Exactly one backend is used, in this order and nothing else:

1. the `JOCKYC` environment variable, when it names an executable file;
2. a compiler built in a JOCKY checkout (`build/native/native/compiler/jockyc`);
3. `jockyc` on `PATH`;
4. Docker, using the `jockey-native:foundation` image.

`jocky doctor` prints which one was selected and why the others were not. jocky never builds,
pulls or installs anything, including the fallback image.

## Exit status

| Status | Meaning                                                           |
| ------ | ----------------------------------------------------------------- |
| 0      | Success                                                           |
| 1      | jockyc ran and rejected the program or the stage (its own status) |
| 2      | Bad arguments, or a command documented as NOT EXPOSED YET         |
| 70     | No usable compiler backend                                        |
| 130    | Interrupted                                                       |

## Forwarded commands

A first argument naming a `.jky` file is run; any other argument is forwarded to `jockyc` untouched
along with the rest. The compiler's stdout, stderr and exit status pass through unchanged.

```sh
jocky hunt.jky                    # same as: jockyc run hunt.jky --execution memory
jocky check hunt.jky
jocky ast hunt.jky
jocky jir hunt.jky
jocky plan hunt.jky
jocky llvm hunt.jky --json
jocky compile hunt.jky --target host --execution native --output build/hunt.o
jocky run hunt.jky --execution memory
jocky variants hunt.jky --count 3
jocky variant-info hunt.variants/<variant-id>.o
jocky benchmark hunt.jky --count 3
```

Paths may be relative or absolute, may contain spaces, and may be used from outside the checkout.
Under the Docker backend a source outside the working directory narrows the bind mount to that
file's own directory, and an `--output` outside it gets its own mount, so the compiler sees the
same files it would natively.

## Composed commands

These re-present `jockyc` output. Add `--json` for a deterministic JSON document; without it they
print a short text summary.

### caps

Declared capabilities from the compiler's validated JIR, with the instruction that requires each.

```sh
jocky caps examples/basic/system.jky
```

### budget

The resolved budget integers the compiler will use, from JIR, each labelled `declared` or `default`
and paired with the literal the program actually wrote (from the AST) — `20%`, `256MB`, `120s`. A
`default` row means the program omitted that budget and jockyc's conservative default applies.

```sh
jocky budget examples/basic/system.jky
```

### types

The result schema the compiler's plan expects for each JIR instruction
(`expected_result_schemas`). This is the compiler's declared JIR schema, not a symbol or type
table.

```sh
jocky types examples/basic/system.jky
```

### metrics

Structural lowering metrics from the variant manifest: basic-block count, function count,
generated-helper count, selected lowering-strategy ids, and the structural fingerprint.

```sh
jocky metrics examples/basic/system.jky
jocky metrics examples/basic/system.jky --seed 0x64
```

### fingerprint

The compiler's own hashes for one lowering — `source_hash`, `jir_hash`, `llvm_ir_hash`, the
structural fingerprint and the variant id. jocky hashes nothing, so this is a compiled identity
rather than a hash of the source text. The `llvm` stage emits no object, so no artifact hash is
shown; use `forge` or `compile` for one.

```sh
jocky fingerprint examples/basic/system.jky
jocky fingerprint examples/basic/system.jky --target linux-x86_64
```

### diverge

Generates `--count` variants through the compiler's deterministic variant generation, writes their
AOT objects and manifests to the output directory, and prints what proves they differ: variant ids,
artifact hashes and structural fingerprints, with how many of each are distinct.

```sh
jocky diverge examples/basic/system.jky --count 3
```

Default output directory: `<stem>.variants` in the current directory. Exits non-zero if fewer than
`--count` artifact hashes are distinct — a variant set that is not distinct is reported as a
failure, not smoothed over.

### diff

Compares the same program lowered under two deterministic seeds, field by field, from the two
`jockyc llvm` manifests. This is a structural comparison of compiler-reported identity and metrics.
jocky does not diff LLVM IR text and makes no semantic claim.

```sh
jocky diff examples/basic/system.jky --seed-a 0x64 --seed-b 0x65
```

### equivalence

Reports the compiler's own fixture semantic-equivalence result: whether every variant's in-process
execution produced the same result hash. This is `SIMULATED` fixture evidence from the local ORC
runtime, not execution on an endpoint.

```sh
jocky equivalence examples/basic/system.jky --count 3
```

Requires the host target; jockyc refuses variant generation and fixture execution for a cross
target (E263).

### verify

Verifies stored integrity by running jockyc's `variant-info`, which recomputes an artifact's
SHA-256 and rejects a mismatch (E265). Given a manifest (`.json`) instead of an artifact, it
reports that the manifest was parsed and validated and that **no digest was compared**.

```sh
jocky verify hunt.variants/<variant-id>.o
jocky verify hunt.variants/<variant-id>.o.manifest.json
```

Local manifests are unsigned, so no signature is checked and none is claimed.

### manifest

Prints a variant manifest by forwarding to `jockyc variant-info`, output untouched.

```sh
jocky manifest hunt.variants/<variant-id>.o
jocky manifest hunt.variants/<variant-id>.o --json
```

### forge

Emits one AOT object and one manifest per deterministic seed for each requested target.

```sh
jocky forge examples/basic/system.jky --count 3 --target linux-x86_64
jocky forge examples/basic/system.jky --count 3 --target all
```

Default output directory: `<stem>.forge`. With `--target all` each target gets its own
subdirectory.

The base seed is jockyc's own: an explicit `variant { seed ... }` declaration in the program if
there is one, otherwise the first 16 hexadecimal characters of the compiler's source hash — both
read back from the compiler's JIR output. `--seed` overrides it. The resolved base seed and its
origin are printed.

`forge` is a jocky-side composition of `jockyc compile`. **It is not the control-plane Build
Forge**, which is a separate pipeline in `services/control-plane` with signing, equivalence gating
and persisted run history.

### pipeline

The judge/demo sequence. It runs only the stages jockyc supports and names the source of each one:

```
CHECK          jockyc check
JIR            jockyc jir
LLVM           jockyc llvm
VARIANTS       jockyc variants            (host target only)
DISTINCTNESS   distinct artifact hashes
COMPILE        the AOT objects variants emitted (host) / jockyc compile (cross)
MEMORY/JIT     the fixture ORC executions  (host target only)
RESULT         compiled identity from the manifests
```

```sh
jocky pipeline examples/basic/system.jky --count 3
jocky pipeline examples/basic/system.jky --count 3 --target linux-x86_64
jocky pipeline examples/basic/system.jky --count 3 --verbose
```

Stages a target cannot support are printed as `SKIP` with the reason rather than fabricated. The
command exits non-zero when a required stage genuinely fails, including a variant set that is not
distinct. `--verbose` also prints each stage's jockyc JSON; without it, no large AST or LLVM dump
is printed.

## Aliases

Aliases translate an argument onto an existing compiler capability. They add no new target, mode or
behaviour.

| Alias                                    | Becomes                   | Notes                                                                  |
| ---------------------------------------- | ------------------------- | ---------------------------------------------------------------------- |
| `--execution jit`                        | `--execution memory`      | only for `run`; the existing ORC in-process mode                       |
| `--dry-run`                              | `plan <file.jky>`         | only for `jocky <file.jky>` and `jocky run <file.jky>`; never executes |
| `--target linux`                         | `--target linux-x86_64`   |                                                                        |
| `--target windows`                       | `--target windows-x86_64` |                                                                        |
| `--target arm64`, `--target linux-arm64` | `--target linux-aarch64`  |                                                                        |
| `--target all`                           | both cross targets        | `forge` and `pipeline` only                                            |

`--dry-run` with any other command is rejected with exit status 2 rather than silently ignored.

## Environment-dependent behaviour

- **Cross-target linking and execution.** `jockyc compile --target linux-x86_64` and
  `--target windows-x86_64` emit real ELF and COFF objects, and `jocky forge --target all` drives
  both. Linking or running those objects needs a toolchain for the target, which this host may not
  have. Compilation is claimed; linking and execution are not. `pipeline` prints the same caveat.
- **Windows.** The repo has never built or run the compiler natively on Windows, and this launcher
  reaches it through Docker Desktop or WSL2 on that platform. `scripts/jockey` and `jocky` are POSIX
  entry points.
- **Fixture vs endpoint.** `jocky run`, `diverge`, `equivalence` and `pipeline` execute against the
  deterministic compiler fixture in this process. They are labelled as such in their own output.

## NOT EXPOSED YET

Each of these is a real capability of the JOCKY platform that `jocky` cannot back with authoritative
data today. Invoking one prints the reason and exits 2. None of them is stubbed with placeholder
output.

| Command                                                 | Why it is not here                                                                                                                                                                                                                                                                                                                                                                   |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `cfg`                                                   | No `jockyc` command emits control-flow-graph edges. The compiler reports basic-block counts only, and the launcher invokes `jockyc` alone rather than external LLVM tooling. A `cfg` built from a hand-written parse of LLVM IR text would be a guess, not compiler data.                                                                                                            |
| `symbols`                                               | No `jockyc` command emits a symbol table or name-binding structure. `jocky types` reports the declared JIR result schema per instruction, which is not the same thing.                                                                                                                                                                                                               |
| `seal`                                                  | No local artifact signing exists. The compiler writes unsigned manifests; signing lives in the control-plane evidence service and the Rust agent's evidence key. `jocky verify` therefore checks integrity only and says so.                                                                                                                                                         |
| `endpoints`, `findings`, `timeline`, `drivers`, `relay` | The control plane serves these under `/api/v1` (`/endpoints`, `/findings`, `/timeline`, `/artifacts/{id}/verify`, …), but every domain route requires a bearer session obtained by logging in with a user, password and organization. The launcher has no HTTP client, no credential source and no session, and this task explicitly forbids changing the backend routes to suit it. |
| `hunt`, `collect`                                       | Mutating operations over enrolled endpoints, gated the same way. `--endpoint` and `--transport relay` are refused for the same reason.                                                                                                                                                                                                                                               |

Adding any of these requires either a new authoritative compiler output, or an authenticated
control-plane client with credentials the operator supplies — not a change to the compiler or the
backend contract.

## See also

- [INSTALL.md](INSTALL.md) — building the compiler and installing the launcher
- [JIR_SPEC.md](JIR_SPEC.md) — the JIR document the composed commands read
- [LANGUAGE_SPEC.md](LANGUAGE_SPEC.md) — the `.jky` grammar
- [BUILD_STATUS.md](BUILD_STATUS.md) — what is verified where, and on which toolchain
- [API.md](API.md) — the control-plane contracts the launcher does not yet reach
