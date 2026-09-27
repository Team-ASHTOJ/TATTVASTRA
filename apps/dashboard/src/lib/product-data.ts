export type RecordData = Record<string, unknown>;
export const object = (value: unknown): RecordData =>
  value && typeof value === "object" ? (value as RecordData) : {};
export const shortHash = (value: unknown) =>
  typeof value === "string" && value.length > 20
    ? `${value.slice(0, 8)}…${value.slice(-4)}`
    : String(value ?? "Not measured");
export function sortedEndpoints<T extends RecordData>(rows: T[]) {
  const rank = (r: T) =>
    r.simulation
      ? 5
      : ((
          { ONLINE: 0, WAITING: 1, STALE: 2, OFFLINE: 3 } as Record<
            string,
            number
          >
        )[String(r.status)] ?? 4);
  return [...rows].sort(
    (a, b) =>
      rank(a) - rank(b) ||
      (Date.parse(String(b.last_seen)) || 0) -
        (Date.parse(String(a.last_seen)) || 0),
  );
}
export function aggregateConnections(
  nodes: RecordData[],
  edges: { source: string; target: string; relationship: string }[],
  observations: RecordData[],
) {
  const merged = new Map<string, RecordData>(),
    aliases = new Map<string, string>();
  for (const node of nodes) {
    const observation = observations.find((o) => o.id === node.observation_id);
    const data = object(object(observation?.document).data);
    const remote = data.remote_address ?? data.remote_ip ?? data.remote;
    // Preserve separate jobs, process identity and local socket; incomplete metadata never merges.
    const key =
      node.type === "Connection" &&
      remote != null &&
      (data.pid ?? data.process_id) != null
        ? JSON.stringify([
            observation?.endpoint_id,
            observation?.job_id,
            data.pid ?? data.process_id,
            data.process_start_time ?? null,
            remote,
            data.remote_port ?? null,
            data.protocol ?? null,
            data.local_address ?? null,
            data.local_port ?? null,
            node.simulation,
          ])
        : String(node.id);
    const previous = merged.get(key);
    if (previous) {
      aliases.set(String(node.id), String(previous.id));
      previous.observation_ids = [
        ...(previous.observation_ids as string[]),
        String(node.observation_id),
      ];
      previous.count = Number(previous.count) + 1;
    } else {
      const item = {
        ...node,
        count: 1,
        observation_ids: [
          String(
            node.observation_id ??
              (observations.some((o) => o.id === node.id) ? node.id : ""),
          ),
        ],
      };
      merged.set(key, item);
      aliases.set(String(node.id), String(node.id));
    }
  }
  const links = new Map<
    string,
    { source: string; target: string; relationship: string }
  >();
  for (const edge of edges) {
    const mapped = {
      ...edge,
      source: aliases.get(edge.source) ?? edge.source,
      target: aliases.get(edge.target) ?? edge.target,
    };
    links.set(JSON.stringify(mapped), mapped);
  }
  return { nodes: [...merged.values()], edges: [...links.values()] };
}
export function stageTotal(profile: RecordData) {
  const stages = [
    "lex_ms",
    "parse_ms",
    "semantic_ms",
    "jir_ms",
    "variant_ms",
    "llvm_generation_ms",
    "optimization_ms",
    "aot_ms",
    "jit_compile_ms",
  ];
  const values = stages
    .map((k) => profile[k])
    .filter((v): v is number => typeof v === "number");
  return values.length ? values.reduce((a, b) => a + b, 0) : null;
}
export function connectionState(endpoint: RecordData, runtime?: RecordData) {
  if (!runtime) return String(endpoint.status);
  if (runtime.state === "ONLINE") return "ONLINE";
  if (
    ["STARTING", "ENROLLING", "WAITING_FOR_HEARTBEAT"].includes(
      String(runtime.state),
    )
  )
    return "WAITING";
  return endpoint.status === "OFFLINE" || endpoint.status === "REVOKED"
    ? "OFFLINE"
    : "STALE";
}
