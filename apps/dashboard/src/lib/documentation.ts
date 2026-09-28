import { languageExamples } from "./language-examples";

export type DocumentationSection = {
  title: string;
  purpose: string;
  syntax: string;
  source: string;
  support?: { compiler: string; endpoint: string };
};

export const documentationSections: DocumentationSection[] = [
  {
    title: "Overview / Quick Start",
    purpose:
      "A JOCKY source describes an authorized investigation. CHECK validates it before COMPILE lowers its typed plan through LLVM.",
    syntax: 'hunt "name" { declarations; statements; }',
    source: `hunt "quick-start" {
  targets { group "AUTHORIZED" os linux }
  runtime { backend llvm execution memory }
  capabilities { system.read }
  collect system as inventory
}`,
  },
  {
    title: "Program Structure",
    purpose:
      "A compilation unit contains one hunt, optionally wrapped in a human-readable case. Declarations always come before statements.",
    syntax: 'case "label" { hunt "name" { ... } }',
    source: `case "Authorized investigation" {
  hunt "program-structure" {
    targets { group "AUTHORIZED" os windows | linux }
    runtime { backend llvm execution memory }
    capabilities { users.read }
    collect users as accounts
  }
}`,
  },
  {
    title: "Targets & Selectors",
    purpose:
      "Group, host, target, and OS selectors narrow authorized endpoint resolution; they never authorize a fleet by themselves.",
    syntax: 'targets { group "name" host "name" os windows | linux }',
    source: `hunt "target-selectors" {
  target "endpoint-asset-42"
  host "authorized-linux"
  group "AUTHORIZED"
  os linux
  runtime { backend llvm execution memory }
  capabilities { system.read }
  collect system as host_inventory
}`,
  },
  {
    title: "Runtime & Execution",
    purpose:
      "LLVM is the required backend. Memory runs in the dedicated agent worker; native is compiler-generated AOT execution.",
    syntax:
      "runtime { backend llvm execution memory|native protect_literals <bool> }",
    source: `hunt "runtime-execution" {
  targets { group "AUTHORIZED" os linux }
  runtime { backend llvm execution native protect_literals false }
  capabilities { system.read }
  collect system as native_inventory
}`,
  },
  {
    title: "Variants",
    purpose:
      "Variants control deterministic compiler diversity without accepting arbitrary native payloads.",
    syntax:
      "variant { enabled <bool> seed auto|<seed> profile minimal|balanced }",
    source: `hunt "variant-control" {
  targets { group "AUTHORIZED" os windows | linux }
  runtime {
    backend llvm
    execution memory
    variant { enabled true seed 0x2a profile balanced }
  }
  capabilities { system.read }
  collect system as variant_inventory
}`,
  },
  {
    title: "Capabilities",
    purpose:
      "Capabilities declare the collector permissions required by the program and are intersected with endpoint policy.",
    syntax: "capabilities { system.read process.read network.read }",
    source: `hunt "capability-declaration" {
  targets { group "AUTHORIZED" os linux }
  runtime { backend llvm execution memory }
  capabilities { process.read network.read }
  collect processes as processes
  collect connections as connections
}`,
  },
  {
    title: "Budgets",
    purpose:
      "Budgets carry bounded CPU, memory, I/O, and duration limits into the execution plan.",
    syntax:
      "budget { cpu <= 20% memory <= 256MB io <= 150MB duration <= 120s }",
    source: `hunt "budgeted-inventory" {
  targets { group "AUTHORIZED" os linux }
  runtime { backend llvm execution memory }
  capabilities { system.read }
  budget { cpu <= 20% memory <= 256MB io <= 150MB duration <= 120s }
  collect system as bounded_inventory
}`,
  },
  {
    title: "Typed Values",
    purpose:
      "Typed constructors make paths, timestamps, addresses, hashes, PIDs, byte counts, and durations explicit rather than implicit strings.",
    syntax:
      'pid(42) bytes(42) path("/root") ip("192.0.2.10") hash("…") time("…") duration(5s)',
    source: `hunt "typed-values" {
  targets { group "AUTHORIZED" os linux }
  runtime { backend llvm execution memory }
  capabilities { process.read network.read filesystem.metadata filesystem.content logs.read system.read }
  collect processes { pid pid(42) } as process_42
  collect connections { pid pid(42) } as process_connections
  collect files { path path("/approved/evidence") fields [path, name, size, sha256] } as files
  collect logs { since time("2026-09-01T00:00:00Z") } as events
  collect system as system_info
  let matching_file = files | where sha256 == hash("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef") | select [path, size]
  let sized_system = system_info | where memory_total >= bytes(1024) | select [hostname, memory_total]
  let known_peer = process_connections | where remote == ip("192.0.2.10") | select [pid, remote]
  let recent_events = events | where timestamp >= time("2026-09-01T00:00:00Z") | select [event_id, timestamp]
  let short_uptime = system_info | where uptime <= duration(5s) | select [hostname, uptime]
}`,
    support: { compiler: "Supported", endpoint: "Collection bridge only" },
  },
  {
    title: "Collectors",
    purpose:
      "Collectors bind typed datasets. Options, field selection, and aliases are validated by the compiler.",
    syntax:
      'collect files { path path("/approved/evidence") fields [path, name, size] limit 100 } as files',
    source: `hunt "collector-options" {
  targets { group "AUTHORIZED" os linux }
  runtime { backend llvm execution memory }
  capabilities { filesystem.metadata logs.read }
  collect files {
    path path("/approved/evidence")
    fields [path, name, size]
    limit 100
  } as files
  collect logs {
    since time("2026-09-01T00:00:00Z")
    where severity == "error"
    limit 100
  } as events
}`,
    support: { compiler: "Supported", endpoint: "Collection bridge only" },
  },
  {
    title: "Dataset Pipelines",
    purpose:
      "let creates immutable datasets by composing a collector with pipeline operations.",
    syntax: "let name = dataset | operation | operation",
    source: `hunt "dataset-pipeline" {
  targets { group "AUTHORIZED" os linux }
  runtime { backend llvm execution memory }
  capabilities { network.read }
  collect connections as net
  let external = net
    | where remote.is_public == true
    | select [pid, remote, remote_port]
    | limit 25
}`,
    support: { compiler: "Supported", endpoint: "Collection bridge only" },
  },
  {
    title: "Filtering",
    purpose: "where retains only rows whose typed predicate evaluates true.",
    syntax: "dataset | where field == value",
    source: `hunt "filtering" {
  targets { group "AUTHORIZED" os linux }
  runtime { backend llvm execution memory }
  capabilities { process.read }
  collect processes { fields [pid, name, signed] } as proc
  let unsigned = proc | where signed == false
}`,
    support: { compiler: "Supported", endpoint: "Collection bridge only" },
  },
  {
    title: "Projection & Sorting",
    purpose:
      "select narrows fields and sort orders a dataset by one scalar field.",
    syntax: "dataset | select [field, ...] | sort field asc|desc",
    source: `hunt "projection-sorting" {
  targets { group "AUTHORIZED" os linux }
  runtime { backend llvm execution memory }
  capabilities { process.read }
  collect processes as proc
  let active = proc | select [pid, name, memory_bytes] | sort memory_bytes desc
}`,
    support: { compiler: "Supported", endpoint: "Collection bridge only" },
  },
  {
    title: "Grouping & Limits",
    purpose:
      "group by creates a count-bearing dataset; limit bounds returned rows.",
    syntax: "dataset | group by [field] | sort count desc | limit 10",
    source: `hunt "grouping-limits" {
  targets { group "AUTHORIZED" os linux }
  runtime { backend llvm execution memory }
  capabilities { network.read }
  collect connections as net
  let counts = net | group by [protocol] | sort count desc | limit 10
}`,
    support: { compiler: "Supported", endpoint: "Collection bridge only" },
  },
  {
    title: "Correlation",
    purpose:
      "correlate produces a same-endpoint inner join across matching typed keys.",
    syntax: "correlate left.key with right.key as result",
    source: `hunt "correlation" {
  targets { group "AUTHORIZED" os linux }
  runtime { backend llvm execution memory }
  capabilities { process.read network.read }
  collect processes as proc
  collect connections as net
  let external = net | where remote.is_public == true
  correlate proc.pid with external.pid as related
}`,
    support: { compiler: "Supported", endpoint: "Collection bridge only" },
  },
  {
    title: "Driver Analysis",
    purpose:
      "analyze enriches a Driver dataset with typed risk fields supplied by an authenticated risk source at execution.",
    syntax: "analyze drivers as risk",
    source: `hunt "driver-analysis" {
  targets { group "AUTHORIZED" os windows | linux }
  runtime { backend llvm execution memory }
  capabilities { drivers.read }
  collect drivers as drivers
  analyze drivers as risk
}`,
    support: { compiler: "Supported", endpoint: "Collection bridge only" },
  },
  {
    title: "Insight",
    purpose:
      "A finding declares its condition, severity, and evidence dataset together.",
    syntax:
      'finding "title" { when count(data) > 0 severity high evidence data }',
    source: `hunt "finding-declaration" {
  targets { group "AUTHORIZED" os linux }
  runtime { backend llvm execution memory }
  capabilities { process.read network.read }
  collect processes as proc
  collect connections as net
  correlate proc.pid with net.pid as related
  finding "External communication" {
    when count(related) > 0
    severity high
    evidence related
  }
}`,
    support: { compiler: "Supported", endpoint: "Collection bridge only" },
  },
  {
    title: "Timeline",
    purpose:
      "timeline combines declared dataset sources while preserving source and collection time.",
    syntax: "timeline { source sys source proc source net }",
    source: `hunt "timeline-sources" {
  targets { group "AUTHORIZED" os linux }
  runtime { backend llvm execution memory }
  capabilities { system.read process.read network.read }
  collect system as sys
  collect processes as proc
  collect connections as net
  timeline { source sys source proc source net }
}`,
    support: { compiler: "Supported", endpoint: "Collection bridge only" },
  },
  {
    title: "Reports / Export",
    purpose:
      "report is the final statement and defines a planned evidence-bearing output with integrity required.",
    syntax:
      "export report { format json|pdf include evidence include timeline include audit integrity true }",
    source: `hunt "report-export" {
  targets { group "AUTHORIZED" os linux }
  runtime { backend llvm execution memory }
  capabilities { system.read }
  collect system as sys
  timeline { source sys }
  export report {
    format json
    include evidence
    include timeline
    include audit
    integrity true
  }
}`,
    support: { compiler: "Supported", endpoint: "Collection bridge only" },
  },
  {
    title: "Compiler Pipeline",
    purpose:
      "Source passes through lexer, parser, semantic and capability validation, typed JIR, LLVM lowering, and a compiler-owned artifact.",
    syntax: "CHECK → Typed JIR → LLVM → COMPILE",
    source: `hunt "compiler-pipeline" {
  targets { group "AUTHORIZED" os linux }
  runtime { backend llvm execution memory variant { enabled true seed 0x44 profile minimal } }
  capabilities { drivers.read }
  budget { cpu <= 10% memory <= 128MB io <= 64MB duration <= 60s }
  collect drivers as inventory
}`,
  },
];

export const documentationExamples = [
  ...documentationSections.map((section) => ({
    name: section.title,
    source: section.source,
  })),
  ...languageExamples,
];
