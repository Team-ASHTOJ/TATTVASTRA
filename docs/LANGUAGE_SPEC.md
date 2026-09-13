# JOCKY language specification — compiler 0.3.0

The C++20 compiler implements this language through typed JIR, a static execution plan, LLVM lowering, host AOT objects and compiler-owned ORC fixture execution. Fixture execution is explicitly SIMULATED and is not an endpoint hunt. LLVM remains mandatory at build time; real endpoint collectors and Agent admission are P2–P6 work. The parser lives in `native/compiler/src/parser.cpp`; editor metadata is not a compiler.

## Lexical and source rules

Source is UTF-8, at most 262144 bytes and 32768 non-EOF tokens. Hashing uses the exact input bytes, including comments and line endings; no normalization option is implemented. Identifiers match `[A-Za-z_][A-Za-z0-9_]*`. Binding names cannot be keywords; field and option names may be keywords. Keywords are enumerated in `source.cpp`. Double-quoted strings use JSON escapes, including Unicode escapes. Literal newlines/control characters in strings are invalid. Comments are `//` through newline or non-nesting `/* ... */`.

Decimal integers have signed 64-bit range; a minus sign is a unary operator and negative literal folding accepts INT64_MIN. Floats require leading digits, optional fractional digits after a dot, and optional signed exponent; values must be finite and representable. `0x` integers are accepted as variant seeds only. `true` and `false` are booleans. Units may immediately follow a number or be whitespace-separated. `%` is a budget unit, not a modulo operator. No interpolation, native imports, shell commands, mutation loops or dynamic evaluation exist.

Positions use zero-based UTF-8 byte offsets and one-based lines/byte columns; spans are half-open. LF increments the line; CR is whitespace. Editors must convert byte columns for UTF-16/LSP display. The CLI reports the first fatal diagnostic, source line, caret span and help where available. Expression recursion/tree height and nested statement blocks are bounded to 64. Record depth is at most 16, one result schema at most 1024 type nodes, and a module at most 65536 result type nodes and instructions. Whitespace is insignificant. A single semicolon is optional after leaf clauses and statements; semicolons after declaration blocks are not accepted.

## Accepted grammar

The following describes accepted productions; semantic restrictions below are additional requirements. Braces and brackets in quotes are literal syntax. Settings inside runtime/budget/variant may appear in any order and may be omitted; duplicate keys are errors.

```ebnf
program       = hunt | "case", string, hunt | "case", string, "{", hunt, "}" ;
hunt          = "hunt", string, "{", {declaration}, {statement}, "}" ;
declaration   = selectors | selector | runtime | capabilities | budget ;
selectors     = ("target" | "targets"), "{", {selector}, "}" ;
selector      = ("group" | "host" | "target"), string
              | "os", os_name, {"|", os_name} ;
runtime       = "runtime", "{", {"backend", "llvm" | "execution", mode | "protect_literals", bool | variant}, "}" ;
variant       = "variant", "{", {"enabled", bool | "seed", seed | "profile", profile}, "}" ;
capabilities  = "capabilities", "{", {qualified_name}, "}" ;
budget        = "budget", "{", {resource, "<=", quantity}, "}" ;
statement     = collect | let | correlate | finding | timeline | report | analyze ;
collect       = "collect", collector, ["{", {option}, "}"], "as", identifier ;
option        = "fields", field_list | option_name, expression ;
let           = "let", identifier, "=", expression, {"|", operation} ;
operation     = "where", expression | "select", field_list
              | "sort", qualified_name, ["asc" | "desc"] | "limit", integer
              | "group", "by", field_list ;
field_list    = "[", [qualified_name, {",", qualified_name}, [","]], "]" ;
correlate     = "correlate", qualified_name, "with", qualified_name, "as", identifier ;
finding       = "finding", string, "{", finding_clauses, "}" ;
finding_clauses = "when", expression, "severity", severity, "evidence", identifier ;
timeline      = "timeline", "{", {"source", identifier}, "}" ;
report        = ["export"], "report", "{", {"format", report_format
              | "include", report_part | "integrity", bool}, "}" ;
analyze       = "analyze", identifier, ["as", identifier], ["{", {let | finding}, "}"] ;
```

Finding clauses can appear in any order, exactly once each. There is exactly one hunt per compilation unit, optionally associated with a case label. Hunt labels must be nonempty. All declarations precede all statements. Runtime, capabilities, budget and target-selector blocks are singleton declarations. Standalone selectors can repeat with distinct values. `os` accepts `windows` and `linux`; repeated OS values are deduplicated. No OS declaration means both, sorted as linux/windows. `target` is an enrolled endpoint selector, `host` a hostname selector, and `group` a named group selector. Values remain unresolved in the plan: repeated values within a kind form alternatives; selector kinds and the OS constraint intersect during future authorized resolution. Empty selectors never authorize a fleet-wide run. The case label is not a trusted case identifier.

## Types and expression rules

Primitive types are `int`, `float`, `bool`, `string`, `time`, `duration`, `hash`, `ip`, `path`, `pid`, and `bytes`. Domain fields are listed below. Dataset variables infer `Dataset<Domain>`; projections retain the domain and narrow the structural schema. `Option<T>` represents nullable fields. No implicit string-to-PID/path/IP/hash conversion exists. `bytes` is a byte count in this frontend, not an arbitrary byte-array or native-payload literal.

Typed literal constructors accept exactly one literal: `pid(42)` (0 through 2^32−1), `bytes(42)` (nonnegative signed-64-bit count), `path("...")` (nonempty, no NUL), `ip("1.2.3.4")` (IPv4/IPv6, no zone suffix), `hash("64 lowercase hex digits")` (SHA-256), `time("2026-09-13T00:00:00Z")` (valid UTC calendar timestamp, optional 1–9 fractional digits, no leap seconds), and `duration("5s")` or `duration(5s)`. Path literals retain spelling; normalization and approved-root checks require endpoint policy and are not performed on the development host. Hash algorithm identity is SHA-256 in version 1; general algorithm-tagged hashes remain a future extension.

Precedence, lowest first: `or`, `and`, `== !=`, `< <= > >=`, `+ -`, `* /`, unary `not -`, parentheses/member access/calls. `not`, `and`, `or` require booleans. Arithmetic accepts int/float, promotes mixed operands to float, and carries checked overflow/division policy. Integer division truncates toward zero at lowering. Literal division by zero is rejected now; nonliteral overflow/division checks are required at lowering. Comparisons require the same scalar type, except int/float may compare. Boolean ordering is disallowed; scalar string/path/hash/IP/time/duration/PID/bytes ordering is defined by their type at future lowering (Unicode scalar order for text, unsigned network-byte order for IP, numeric order for quantities). Datasets/records cannot be compared directly.

`count(dataset)` infers nonnullable int; the frontend emits its typed expression without reading rows. `remote.is_public` infers `Option<bool>` from an optional IP; a versioned address-range policy must be supplied by the later runtime, with no implicit network lookup. Nullable operations propagate nullability and use three-valued logic. `where` keeps true only; unknown signature status never becomes unsigned. Field access requires a row context (`where`, projection, sorting, grouping, or correlation keys). A field name shadows a scalar binding in row context; qualified references to another dataset require explicit correlation.

`let` bindings are immutable and cannot be duplicated or referenced before declaration. A pipeline requires a dataset. `select`/collector fields must be nonempty, distinct and available in the incoming schema. `sort` uses one scalar field, defaults to ascending, is stable and places nulls last. `limit` is an integer literal from 1 to 1000000. `group by [fields]` groups scalar keys, groups null keys together, and yields those keys plus `count: int` in `Dataset<Group>`. A grouping key named count is rejected.

`correlate a.key with b.key as result` requires two dataset field references of identical scalar kind. It describes a same-endpoint inner equijoin, excludes null keys and yields nested `left`/`right` records in `Dataset<Correlation>`. Projections such as `[left.name, right.remote]` preserve dotted names and remain queryable. Correlation emits a warning about causality/PID reuse; process start identity and timestamps must be reviewed. Joins/sorts/groups remain subject to the enclosing resource budget at runtime.

## Collector and capability registry

All collectors accept `fields`, `where`, and `limit`. Extra options are listed here. `fields` determines the available collector schema before `where`; predicates cannot implicitly fetch omitted fields. This deliberately requires an explicit field request for expensive hashes. Options are constant typed expressions: `pid` uses `pid(...)`, `path` uses `path(...)`, `recursive` is bool, `since`/`until` use `time(...)`, other options are strings. Protocol is exactly `"tcp"` or `"udp"`. Path-scoped collectors require `path`.

| Collector names                                               | Dataset domain                               | Required base capability | Extra options                       |
| ------------------------------------------------------------- | -------------------------------------------- | ------------------------ | ----------------------------------- |
| system, hostname                                              | SystemInfo                                   | system.read              | —                                   |
| endpoints                                                     | Endpoint                                     | system.read              | —                                   |
| users                                                         | User                                         | users.read               | —                                   |
| sessions                                                      | Session                                      | users.read               | —                                   |
| environment                                                   | Environment                                  | system.read              | pattern                             |
| packages                                                      | Package                                      | system.read              | —                                   |
| processes, process_metadata, process_hash, process_signatures | Process                                      | process.read             | pid                                 |
| connections                                                   | Connection                                   | network.read             | protocol, pid                       |
| ports                                                         | Connection                                   | network.read             | protocol                            |
| interfaces, routes, dns                                       | Interface, Route, DNS respectively           | network.read             | —                                   |
| files                                                         | File                                         | filesystem.metadata      | path (required), recursive, pattern |
| file_metadata                                                 | File                                         | filesystem.metadata      | path (required)                     |
| directories                                                   | File                                         | filesystem.metadata      | path (required), recursive          |
| hash, file_hash, file_content                                 | File                                         | filesystem.content       | path (required)                     |
| logs, events                                                  | Event                                        | logs.read                | since, until, channel               |
| services, startup, scheduled_tasks                            | Service, Startup, ScheduledTask respectively | persistence.read         | —                                   |
| drivers, driver_hash, driver_signatures                       | Driver                                       | drivers.read             | —                                   |
| modules                                                       | Module                                       | drivers.read             | —                                   |

`scheduled tasks` is an alias for `scheduled_tasks`. A requested `sha256` field additionally requires `filesystem.content`; process_hash, driver_hash and file_content require it even when projection omits sha256. Hash fields are omitted by default for processes, process_metadata, process_signatures, files, file_metadata, directories, drivers, driver_signatures and modules. File hash/content and dedicated process/driver hash collectors include hash by default. Missing grants produce E241. Compatibility aliases preserve older examples: `filesystem.read` grants content reading; `services.read` grants services collection only, never startup or scheduled tasks. Alias use warns W241. Content permission does not implicitly grant metadata permission. Unknown/duplicate capabilities are errors; unused grants warn W240. Actual endpoint policy still intersects declarations, path scopes and collector availability.

The registry describes both Windows and Linux semantic targets. Optional fields carry nullability; no collector support, privilege, signature, endpoint state or risk match is inferred from compiling on macOS. Every runtime dataset must carry the observation envelope (provenance, clock basis, variant, integrity and simulation state) independently of visible projected fields. The frontend creates no observation or fixture result.

## Frozen field schemas

`?` means nullable. Unless noted, fields are strings. These are static expected schemas, not a claim that an endpoint adapter exists.

| Domain        | Fields                                                                                                                                   |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Endpoint      | endpoint_id, hostname, os, arch                                                                                                          |
| SystemInfo    | hostname, os, arch, kernel?, boot_time:time?, uptime:duration?, memory_total:bytes?, cpu_count:int?, ip:ip?                              |
| Process       | pid:pid, parent_pid:pid?, name, path:path?, user?, start_time:time?, signed:bool?, sha256:hash?, cpu_percent:float?, memory_bytes:bytes? |
| Connection    | pid:pid?, process_start_time:time?, protocol, local:ip, local_port:int, remote:ip?, remote_port:int?, state?                             |
| Interface     | name, address:ip?, mac?, mtu:int?, up:bool?                                                                                              |
| Route         | destination:ip, prefix_length:int, gateway:ip?, interface, metric:int?                                                                   |
| File          | path:path, name, size:bytes?, modified_at:time?, created_at:time?, is_directory:bool?, sha256:hash?                                      |
| Event         | event_id, timestamp:time?, source, channel?, message, severity?, pid:pid?                                                                |
| User          | name, uid, home:path?, active:bool?                                                                                                      |
| Service       | name, state, path:path?, pid:pid?, start_type?                                                                                           |
| Driver        | name, vendor?, version?, path:path?, signed:bool?, signature_status?, sha256:hash?                                                       |
| Module        | name, version?, path:path?, size:bytes?, sha256:hash?                                                                                    |
| Artifact      | artifact_id, content_hash:hash?, size:bytes?, path:path?                                                                                 |
| Observation   | observation_id, timestamp:time, source_time:time?, type, integrity_hash:hash                                                             |
| Finding       | finding_id, title, severity, timestamp:time?                                                                                             |
| TimelineEvent | event_id, timestamp:time?, source, severity?                                                                                             |
| Session       | id, user, started_at:time?, remote:ip?                                                                                                   |
| Environment   | name, value?                                                                                                                             |
| DNS           | name, address:ip?, ttl:duration?                                                                                                         |
| Startup       | name, path:path?, user?, source                                                                                                          |
| ScheduledTask | name, command?, user?, enabled:bool?                                                                                                     |
| Package       | name, version, vendor?                                                                                                                   |

## Investigation statements

Findings require a nonempty unique title, a boolean `when`, one dataset as evidence, and severity `info`, `low`, `medium`, `high`, or `critical`. Only true conditions emit at runtime. A timeline is optional, unique per hunt, and requires at least one distinct dataset source. It preserves source/collection time and explicit unknown timestamps.

`analyze drivers` means analyze the variable named drivers; it must be `Dataset<Driver>`. The instruction adds nullable `known_vulnerable:bool`, `blocklist_match:bool`, `risk:string`, `cve:string`, and `risk_source:string`. With `as`, it creates a new binding. Without `as`, it advances the existing driver binding to a new SSA value; earlier derived bindings retain their original value. This is the sole binding-update form. Its optional body accepts let and finding statements with hunt scope. It requires drivers.read and emits W227: no matches exist until a versioned authenticated risk dataset is supplied. Missing metadata remains unknown.

Report is optional and must be the final statement. Format defaults to json and accepts json/pdf. Includes accept evidence/timeline/audit once each; absent includes default to evidence/audit. Including timeline requires a prior timeline. Integrity defaults to true; false is rejected. Static report planning emits artifact store/hash, manifest and report instructions; evidence membership contains collections and findings, and producer authentication is required at execution. It does not create files, hashes of nonexistent evidence, signatures or reports. Real jobs must reject synthetic evidence.

## Budget and runtime settings

Budget defaults are cpu 20%, memory 256000000 bytes, I/O 150000000 bytes, duration 120000 ms. Missing settings warn W232. CPU is an integer 1–100; memory is positive; I/O permits zero; duration is 1–86400000 ms. Quantities are integers with explicit units: `%`, `B`, `KB`, `MB`, `GB`, `KiB`, `MiB`, `GiB`, `ms`, `s`, `m`, `h`. Decimal/binary sizes never alias. Converted quantities must fit 9007199254740991. CPU means a fraction of one logical core, duration a monotonic wall deadline, and I/O accounts collector reads; evidence transmission is separately measured later. Budgets are validated and carried, not enforced by this phase.

Runtime defaults to backend llvm, execution memory, variant disabled, seed auto, profile balanced, and literal protection disabled. Only native/memory and minimal/balanced are accepted; VM and other backends/profiles are errors. Seeds accept auto, unsigned-64-bit decimal, 0x hexadecimal, or a quoted hexadecimal string; explicit seeds normalize to 16 lowercase hex digits. Auto is resolved deterministically by the backend from the source hash. `protect_literals true` requires an external AES-256 key and key ID at build/execution; keys never enter JIR, LLVM IR, objects, manifests, or logs. Fresh encryption uses a random unique nonce and therefore becomes an additional immutable reproducibility input.

## Diagnostics, CLI and acceptance

Implemented commands are `jockyc check|tokens|ast|jir|plan <file> [--json]`; `--json` can appear anywhere in the argument list. Tokens/AST are syntax-debug commands and do not perform semantic validation. Check/JIR/plan run the whole frontend. Default check output is a concise result and highlighted warnings; other default outputs are indented JSON. Machine JSON is deterministic and contains no measured compiler timings. Exit 0 means the requested stage succeeded, 1 means a user/source error, and 70 means an internal/toolchain failure. `--version`, `--help`, and the real ORC `--self-test` remain available.

| Code                               | Meaning                                                                                                                                              |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| E001/E002/E003/E999                | CLI usage / LLVM probe / file I/O / unexpected internal failure                                                                                      |
| E100–E106                          | source/token bounds, UTF-8, comment/string/escape/exponent/character errors                                                                          |
| E120–E129                          | expected token, statement, depth, duplicate clause, selector, pipeline, finding/report syntax, declaration ordering, extra hunt                      |
| E210/E211/E212                     | unknown collector / undefined binding / duplicate binding                                                                                            |
| E213/E214                          | missing field / invalid or cross-dataset field access                                                                                                |
| E220–E226                          | literal, operand types, predicate, pipeline, aggregate/row context, division, constructor                                                            |
| E227/E228/E229                     | driver analysis / correlation / finding semantics                                                                                                    |
| E230–E235                          | collector option or hunt label / target OS / budget / backend / mode / variant                                                                       |
| E238/E239/E240/E241/E250           | timeline / report / capability declaration / missing grant / invalid JIR                                                                             |
| W227/W228/W232/W240/W241/W250/W251 | unresolved risk metadata / correlation caveat / budget defaults / unused grant / alias / unresolved authorization / unavailable lowering and runtime |

All valid examples reach JIR; invalid examples and their expected codes are in `examples/invalid/expected.json`. Native unit tests cover both endpoint OS semantics, limits, malformed mutations, types, effects and plan barriers. Reviewed exact-byte AST/JIR/plan snapshots live in `fixtures/compiler`. `scripts/test_frontend.py` invokes the real C++ CLI; Python never interprets JOCKY.
