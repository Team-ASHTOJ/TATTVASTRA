export const sections = [
  {
    slug: "",
    name: "Command Center",
    group: "OVERVIEW",
    phase: "P0",
    description: "The current operating picture across Tattvastra.",
  },
  {
    slug: "workbench",
    name: "Tattvastra Workbench",
    group: "BUILD",
    phase: "P1–P3",
    description:
      "Write a forensic program, validate it, and compile it through JIR and LLVM.",
  },
  {
    slug: "language",
    name: "Docs",
    group: "BUILD",
    phase: "P1–P3",
    description: "Language reference and working forensic programs.",
  },
  {
    slug: "compiler",
    name: "Compiler Explorer",
    group: "BUILD",
    phase: "P1–P3",
    description: "Inspect an existing persisted compilation stage by stage.",
  },
  {
    slug: "forge",
    name: "Build Forge",
    group: "BUILD",
    phase: "P4",
    description:
      "Seeded LLVM builds, fixture equivalence and signed delivery provenance.",
  },
  {
    slug: "variants",
    name: "Variant Explorer",
    group: "BUILD",
    phase: "P4",
    description:
      "Compare compiler-generated variants and their build provenance.",
  },
  {
    slug: "endpoints",
    name: "Endpoints",
    group: "OPERATE",
    phase: "P5–P6",
    description: "Connect and inspect Windows and Linux Tattvastra agents.",
  },
  {
    slug: "investigations",
    name: "Investigations",
    group: "OPERATE",
    phase: "P5–P7",
    description: "Launch and follow multi-endpoint Tattvastra investigations.",
  },
  {
    slug: "findings",
    name: "Findings",
    group: "ANALYZE",
    phase: "P7",
    description: "Evidence-backed conclusions derived from observations.",
  },
  {
    slug: "graph",
    name: "Forensic Graph",
    group: "ANALYZE",
    phase: "P7",
    description: "Relationships derived from stored forensic observations.",
  },
  {
    slug: "timeline",
    name: "Timeline",
    group: "ANALYZE",
    phase: "P7",
    description: "A normalized chronological investigation record.",
  },
  {
    slug: "evidence",
    name: "Evidence Vault",
    group: "EVIDENCE",
    phase: "P7",
    description:
      "Artifacts, manifests, provenance, and integrity verification.",
  },
  {
    slug: "drivers",
    name: "Driver Intelligence",
    group: "EVIDENCE",
    phase: "P8",
    description:
      "Collected driver inventory and clearly separated lab-risk metadata.",
  },
  {
    slug: "performance",
    name: "Performance",
    group: "VALIDATE",
    phase: "P9",
    description: "Measured compiler and control-plane execution timings.",
  },
  {
    slug: "architecture",
    name: "Requirement Coverage",
    group: "VALIDATE",
    phase: "P0",
    description: "Technical traceability and prototype capability status.",
  },
] as const;
