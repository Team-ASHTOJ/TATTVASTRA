export type CompatibilityRun = {
  id: string;
  created_at: string;
  variant_id: string;
  endpoint_id: string | null;
  recorded_by: string;
  simulation: boolean;
  simulation_label: string | null;
  observations: Record<string, unknown>;
};

const comparable = [
  "compilation_id",
  "jir_sha256",
  "environment",
  "os_name",
  "os_version",
  "architecture",
  "security_product_label",
  "security_product_version",
  "realtime_protection",
] as const;

export function equivalentRuns(
  runs: CompatibilityRun[],
  selected: CompatibilityRun,
): CompatibilityRun[] {
  const baseline = selected.observations;
  // A missing identity is not evidence that two environments are equivalent.
  if (comparable.some((key) => baseline[key] == null || baseline[key] === ""))
    return [];
  const byVariant = new Map<string, CompatibilityRun>();
  for (const run of [...runs].sort((a, b) =>
    a.created_at.localeCompare(b.created_at),
  )) {
    if (run.simulation !== selected.simulation) continue;
    if (comparable.some((key) => run.observations[key] !== baseline[key]))
      continue;
    byVariant.set(run.variant_id, run);
  }
  const peers = [...byVariant.values()].filter(
    (run) => run.variant_id !== selected.variant_id,
  );
  return [selected, ...peers.slice(-2)];
}
