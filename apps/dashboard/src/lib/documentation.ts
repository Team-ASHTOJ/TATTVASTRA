import { languageExamples } from "./language-examples";
const declarations = `targets { group "AUTHORIZED" os windows | linux }
    runtime { backend llvm execution memory }
    capabilities { system.read users.read process.read network.read drivers.read }`;
const program = (name: string, body: string, config = declarations) =>
  `hunt "${name}" {\n    ${config}\n    ${body}\n}`;
export const documentationSections = [
  [
    "Overview",
    "One .jky program expresses authorized forensic intent. The control plane resolves endpoints and dispatches compiler-generated plans; Python does not interpret the language.",
    "collect system as inventory",
  ],
  [
    "Quick Start",
    "Load this minimal valid program, CHECK then COMPILE. Connect an endpoint before selecting it for execution.",
    "collect system as inventory",
  ],
  [
    "Program Structure",
    "Exactly one hunt per compilation unit. Declarations precede statements. Bindings are immutable; comments use // or /* … */.",
    "collect system as inventory",
  ],
  [
    "Targets",
    "group, host and target selectors are string values. os accepts windows | linux. Empty selectors do not authorize fleet-wide collection.",
    "collect system as inventory",
  ],
  [
    "Runtime",
    "LLVM is mandatory. Runtime settings configure lowering; they are not arbitrary native code imports.",
    "collect system as inventory",
  ],
  [
    "Execution",
    "memory runs in a dedicated agent worker process; native runs a compiler-generated executable. Supported endpoint modes are checked before dispatch.",
    "collect system as inventory",
  ],
  [
    "Variants",
    "enabled, seed and profile configure deterministic compiler diversity. Seeds accept hexadecimal integers. Hash differences alone do not establish semantic equivalence.",
    "collect system as inventory",
  ],
  [
    "Capabilities",
    "Read permissions are validated at compilation and checked against enrolled endpoint policy. Collectors cannot acquire permissions by declaration alone.",
    "collect processes as procs",
  ],
  [
    "Budgets",
    "cpu, memory, io and duration use <= limits with units. Remote execution currently supports MONITORED enforcement; strict limits are unavailable.",
    "collect system as inventory",
  ],
  [
    "Collectors",
    "collect binds a typed dataset. The remote bridge supports bounded system, users, processes, interfaces, connections, routes, services, events and drivers without options. Compiler registry aliases and optional adapters do not imply remote support.",
    "collect processes as procs\n    collect connections as conns",
  ],
  [
    "Filters",
    "Immutable pipelines support where, select, sort, limit and group by. where keeps true only; unavailable signature state never becomes unsigned. These operations compile but are outside the current remote inventory bridge.",
    "collect processes as procs\n    let unsigned = procs | where signed == false | select [pid, name] | limit 25",
  ],
  [
    "Correlation",
    "correlate joins same-endpoint typed scalar keys, excluding nulls. Review process start identity and timestamps when joining PIDs. Rich correlation is outside the bounded remote bridge.",
    "collect processes as procs\n    collect connections as conns\n    correlate procs.pid with conns.pid as related",
  ],
  [
    "Findings",
    "finding defines a conclusion with when, severity and evidence clauses. Severity is declared, not inferred from an arbitrary frontend label. Current backend findings derive from stored observations.",
    'collect processes as procs\n    collect connections as conns\n    correlate procs.pid with conns.pid as related\n    finding "Process connection" { when count(related) > 0 severity high evidence related }',
  ],
  [
    "Compiler Pipeline",
    "Source → Lexer → Parser/AST → semantic/capability validation → Typed JIR → LLVM → variant/artifact. Inspect persisted stage output in Compiler Explorer; missing LLVM is a build failure.",
    "collect system as inventory",
  ],
].map(([title, purpose, body]) => {
  let config = declarations;
  if (title === "Execution")
    config = config.replace("execution memory", "execution native");
  if (title === "Variants")
    config = config.replace(
      "execution memory }",
      "execution memory variant { enabled true seed 0x01 profile balanced } }",
    );
  if (title === "Budgets")
    config +=
      "\n    budget { cpu <= 20% memory <= 256MB io <= 150MB duration <= 120s }";
  return {
    title: title!,
    purpose: purpose!,
    source: program(title!.toLowerCase().replaceAll(" ", "-"), body!, config),
  };
});
export const documentationExamples = [
  ...documentationSections.map((s) => ({ name: s.title, source: s.source })),
  ...languageExamples,
];
