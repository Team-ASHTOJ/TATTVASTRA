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

export function equivalentRuns(
  runs: CompatibilityRun[],
  selected: CompatibilityRun,
): CompatibilityRun[] {
  const baseline = selected.observations;
  const fingerprint = baseline.environment_fingerprint;
  // An unknown environment is never evidence that two runs are equivalent.
  if (typeof fingerprint !== "string" || !fingerprint.startsWith("ENV-"))
    return [];
  const byVariant = new Map<string, CompatibilityRun>();
  for (const run of [...runs].sort((a, b) =>
    a.created_at.localeCompare(b.created_at),
  )) {
    if (run.simulation !== selected.simulation) continue;
    if (run.observations.environment_fingerprint !== fingerprint) continue;
    byVariant.set(run.variant_id, run);
  }
  const peers = [...byVariant.values()].filter(
    (run) => run.variant_id !== selected.variant_id,
  );
  return [selected, ...peers.slice(-2)];
}
