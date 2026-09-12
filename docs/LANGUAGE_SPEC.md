# JOCKY language specification — draft 0.1

Status: normative implementation target; **frontend not implemented in P0**. `.jky` is an independent forensic DSL. `packages/jocky-language` supplies editor vocabulary only.

## Lexical rules

UTF-8 source; LF-normalized source hashing is a compiler option recorded in the build input (default: exact supplied UTF-8 bytes). Identifiers match `[A-Za-z_][A-Za-z0-9_]*`; keywords are reserved. Strings use double quotes and JSON escapes. `//` line comments and non-nesting `/* */` block comments are permitted. Decimal integers, decimal floats, booleans, and unit-bearing numeric literals are tokens. No shell interpolation, imports of native code, dynamic evaluation, recursion or unbounded loops.

Diagnostics use one-based line/column with half-open source ranges, stable diagnostic codes and severity. Lexer/parser recovery may collect multiple errors; any error prevents executable output. Byte offsets are retained separately for UTF-8 editor conversion.

## Grammar sketch

```ebnf
program       = [case_decl], hunt_decl ;
case_decl     = "case", string ;
hunt_decl     = "hunt", string, "{", {declaration | statement}, "}" ;
declaration   = targets | runtime | capabilities | budget ;
targets       = "targets", "{", {"group", string | "target", string |
                "os", os_name, {"|", os_name}}, "}" ;
runtime       = "runtime", "{", "backend", "llvm", "execution", mode,
                ["variant", "{", "enabled", bool, "seed", seed,
                "profile", profile, "}"], "}" ;
capabilities  = "capabilities", "{", {qualified_name}, "}" ;
budget        = "budget", "{", "cpu", "<=", percentage,
                "memory", "<=", bytes_literal, "io", "<=", bytes_literal,
                "duration", "<=", duration_literal, "}" ;
statement     = collect | let | correlate | finding | timeline | export | analyze ;
collect       = "collect", collector, ["{", "fields", "[", field_list, "]", "}"],
                "as", identifier ;
let           = "let", identifier, "=", dataset, {"|", operation} ;
operation     = "where", expression | "select", "[", field_list, "]" |
                "sort", qualified_name, ["asc" | "desc"] | "limit", integer ;
correlate     = "correlate", qualified_name, "with", qualified_name,
                "as", identifier ;
finding       = "finding", string, "{", "when", expression,
                "severity", severity, "evidence", dataset, "}" ;
timeline      = "timeline", "{", {"source", dataset}, "}" ;
export        = "export", "report", "{", "format", ("pdf" | "json"),
                {"include", ("timeline" | "evidence" | "audit")}, "}" ;
analyze       = "analyze", dataset, "{", {"finding", string, "{", finding_body, "}"}, "}" ;
```

`collector`, `expression`, `finding_body`, OS/profile/mode/severity domains and qualified field resolution follow the rules below. This is a grammar sketch, not a claim that all productions are implemented. P1 must replace sketches with parser-tested productions. Top-level `case` binds a human case label; authorization resolves the API-provided case ID and rejects mismatches. `target` inside targets names an enrolled endpoint; `group` resolves at plan time to an explicit snapshot. Duplicate singleton declaration blocks are errors. Declarations precede statements; forward references and rebinding are rejected.

## Types and operators

Primitive types: int (signed 64-bit), float (finite IEEE-754 double), bool, string (UTF-8), time (UTC instant with source precision), duration (integer milliseconds), hash (algorithm-tagged digest; SHA-256 initially), ip (IPv4/IPv6), path (platform-normalized identity plus original spelling), pid (unsigned PID), bytes (bounded size or immutable byte value according to context).

Forensic row types: Endpoint, Process, Connection, File, Event, User, Service, Driver, Module, Artifact, Observation, Finding, TimelineEvent. Collections are `Dataset<T>`. Optional fields use `Option<T>` internally. Unknown Windows signatures/Linux signature absence remain unknown; `signed == false` matches only explicit false. Filters retain rows whose predicate is true; false and unknown do not match. No implicit string/int/path conversion.

Expression precedence from low to high: `or`, `and`, equality `== !=`, comparison `< <= > >=`, addition/subtraction, multiplication/division, unary `not -`, member access/calls. Boolean operators use three-valued logic for optional fields. `count(dataset)` returns nonnegative int. `remote.is_public` is a typed IP classification property with an explicit versioned address-range policy; no network lookup occurs implicitly. Integer overflow, division by zero and malformed IP/hash/time values are diagnostics or recorded runtime errors, never undefined behavior.

`select` projects a typed row; `sort` is stable with specified direction and missing values last; `limit` accepts a compile-time bounded nonnegative integer. `correlate a.key with b.key` is an inner equijoin of compatible key types with deterministic left/right row naming. Dataset ordering is not evidence identity unless explicitly sorted. Collectors create effects; filters and joins do not reorder collection.

## Collector and field registry

`system` → Dataset<Endpoint>; `processes` → Dataset<Process>; `connections`/`interfaces`/`ports`/`routes`/`dns` → defined network row schemas; `users`, `services`, `files`, `events`, `drivers`, `modules`, `startup`, `packages` map to their documented inventory rows. P1 freezes detailed field registries before type checking; field selection never authorizes extra capabilities.

Process core fields include pid, parent_pid, name, path, user, start_time, signed, sha256; unavailable optional fields remain null with availability detail. Connection core fields include protocol, local/remote IP and port, state and optional owning PID/start identity. Driver core fields include name, vendor, version, path, hash and signature status. JIR uses explicit record definitions for network subtypes rather than mislabeling them as TCP connections.

## Capabilities and budgets

Capability names include `system.read`, `process.read`, `network.read`, `filesystem.metadata`, `filesystem.read`, `logs.read`, `users.read`, `services.read`, `drivers.read`. Hashing file/executable bytes requires the read capability and path scope in addition to metadata. Missing declarations are compile errors; declared capabilities are still intersected with agent policy at plan/admission time. The long proposal example's process hash request therefore also requires an explicit readable executable scope under this specification.

`cpu <= 20%`, `memory <= 256MB`, `io <= 150MB`, `duration <= 120s` lower to Budget fields. MB is 1,000,000 bytes, MiB is 1,048,576 bytes; units never silently alias. CPU percent is a fraction of one logical CPU; 100% is one core. Duration is a monotonic wall deadline, not CPU time. I/O includes collector file bytes read, with evidence transmission measured separately. Unsupported enforceability is surfaced before dispatch. P0 validates numeric contracts only; P3/P6 implement enforcement.

## Runtime, variants and acceptance

Required modes: native and memory. `vm` is optional and explicitly unavailable until implemented. `backend llvm` is mandatory for required modes. `seed auto` resolves to a recorded unsigned 64-bit seed before compilation; hexadecimal contract strings avoid JavaScript precision loss. Same inputs/seed/toolchain produce identical unencrypted artifacts. Profiles minimal/balanced select allowed wrapper transforms only.

`examples/basic/system.jky` is the first vertical slice target. `examples/investigations/sih-demo.jky` exercises correlations and reports as a later acceptance program. Both are labeled specification inputs until the real parser and backend pass. Tests must cover malformed tokens, spans, type errors, capability denial, budget units, nullable filters, join keys and deterministic normalized JIR.
