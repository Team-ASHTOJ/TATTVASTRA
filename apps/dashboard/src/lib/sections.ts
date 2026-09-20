export const sections = [
  {
    slug: "",
    name: "Command Center",
    group: "OPERATIONS",
    phase: "P0",
    description: "Platform availability and implementation status.",
  },
  {
    slug: "cases",
    name: "Cases",
    group: "OPERATIONS",
    phase: "P5",
    description:
      "Scoped investigations, assigned operators, and evidence retention.",
  },
  {
    slug: "scripts",
    name: "Scripts / Versions",
    group: "BUILD",
    phase: "P5",
    description:
      "Persisted JOCKY source versions and their compiler lifecycle.",
  },
  {
    slug: "workbench",
    name: "JOCKY Workbench",
    group: "BUILD",
    phase: "P1–P3",
    description:
      "Monaco source editing, diagnostics, CHECK, COMPILE, PLAN, GENERATE VARIANTS, and RUN.",
  },
  {
    slug: "compiler",
    name: "Compiler Explorer",
    group: "BUILD",
    phase: "P1–P3",
    description:
      "Measured lexer, parser, AST, types, capabilities, JIR, LLVM, and AOT/JIT stages.",
  },
  {
    slug: "variants",
    name: "Variant Explorer",
    group: "BUILD",
    phase: "P4",
    description:
      "Real artifact comparisons, reproducible seeds, and semantic-equivalence matrices.",
  },
  {
    slug: "forge",
    name: "Build Forge",
    group: "BUILD",
    phase: "P4",
    description:
      "Compile, validate, test, sign, and register compiler-generated artifacts.",
  },
  {
    slug: "endpoints",
    name: "Endpoints",
    group: "INVESTIGATE",
    phase: "P5–P6",
    description:
      "Enrolled Windows and Ubuntu agents, actual health, trust, and collector availability.",
  },
  {
    slug: "jobs",
    name: "Hunts / Jobs",
    group: "INVESTIGATE",
    phase: "P5",
    description:
      "Signed, expiring multi-endpoint jobs with cancellation, retry, and partial success.",
  },
  {
    slug: "live",
    name: "Live Investigation",
    group: "INVESTIGATE",
    phase: "P7",
    description:
      "Collector progress, observations, findings, and failures streamed from running agents.",
  },
  {
    slug: "findings",
    name: "Findings",
    group: "INVESTIGATE",
    phase: "P7",
    description:
      "Evidence-backed suspicious relationships and operator-reviewed severity.",
  },
  {
    slug: "graph",
    name: "Forensic Graph",
    group: "INVESTIGATE",
    phase: "P7",
    description:
      "Endpoint, process, file, connection, user, driver, service, and finding relationships.",
  },
  {
    slug: "timeline",
    name: "Timeline",
    group: "INVESTIGATE",
    phase: "P7",
    description:
      "Normalized events with time basis, source, endpoint, severity, and evidence links.",
  },
  {
    slug: "evidence",
    name: "Evidence Vault",
    group: "ASSURANCE",
    phase: "P0 / P7",
    description:
      "Persisted artifacts, manifests, hashes, signatures, and verification status.",
  },
  {
    slug: "drivers",
    name: "Driver Intelligence",
    group: "ASSURANCE",
    phase: "P8",
    description:
      "REAL DRIVER ANALYSIS and a separately labeled LAB SIMULATION of visibility loss.",
  },
  {
    slug: "compatibility",
    name: "Compatibility Lab",
    group: "ASSURANCE",
    phase: "P8",
    description:
      "Operator-observed benign workload correctness, alerts, and resource use.",
  },
  {
    slug: "performance",
    name: "Performance",
    group: "ASSURANCE",
    phase: "P9",
    description:
      "Measured compiler, variant, agent, and distributed execution profiles.",
  },
  {
    slug: "reports",
    name: "Reports",
    group: "ASSURANCE",
    phase: "P7",
    description:
      "Persisted JSON exports with evidence verification and audit history.",
  },
  {
    slug: "architecture",
    name: "Architecture / Coverage",
    group: "ASSURANCE",
    phase: "P0",
    description:
      "Requirement coverage, implementation status, acceptance evidence, and safe mappings.",
  },
] as const;
