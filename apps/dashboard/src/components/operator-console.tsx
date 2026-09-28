"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import {
  connectionState,
  sortedEndpoints,
  aggregateConnections,
  executionLabel,
  shortHash,
  stageTotal,
} from "../lib/product-data";
import { useControlEvents } from "../lib/use-control-events";
import { Icon, type IconName } from "./icons";
import { GlobeCdn } from "./globe-cdn";
import { EndpointLifecycleTrace } from "./endpoint-lifecycle-trace";
type Row = { id: string; [key: string]: unknown };
type Data = {
  cases: Row[];
  endpoints: Row[];
  hunts: Row[];
  jobs: Row[];
  compilations: Row[];
  scripts: Row[];
  versions: Row[];
  observations: Row[];
  findings: Row[];
  timeline: Row[];
  artifacts: Row[];
  manifests: Row[];
  variants: Row[];
  benchmarks: Row[];
};
const obj = (v: unknown): Record<string, unknown> =>
  v && typeof v === "object" ? (v as Record<string, unknown>) : {};
const str = (v: unknown) => (v == null ? "Not available" : String(v));
const date = (v: unknown) =>
  v ? new Date(String(v)).toLocaleString() : "Never";
const items = (v: unknown): string[] => (Array.isArray(v) ? v.map(String) : []);
const provenance = (r: Row) => (r.simulation ? "SANDBOX" : "REAL");
/**
 * The demo Windows sandbox is a persisted simulated endpoint, never a real agent.
 * It is identified by its transport so real endpoints keep their existing labels.
 */
const sandboxRow = (r: Row) => !!r.simulation && r.transport_mode === "SANDBOX";
const capabilityLabel = (mode: string) =>
  mode === "sandbox"
    ? "SANDBOX / PREVIEW"
    : mode === "memory"
      ? "MEMORY / JIT"
      : "NATIVE / AOT";
const title = (r?: Row) =>
  r?.description === "JOCKY_VIDEO_V2_READY" ||
  (r?.simulation && /SIH|demo/i.test(str(r?.title)))
    ? "Failure Isolation Scenario"
    : str(r?.title);
const payload = (r: Row) => obj(obj(r.document).data);
const submit = <T,>(path: string, body?: unknown) =>
  api<T>(`domain/${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });

export function OperatorConsole({ section }: { section: string }) {
  const client = useQueryClient();
  const refresh = useCallback(async () => {
    await client.invalidateQueries({ queryKey: ["resources"] });
  }, [client]);
  const user = useQuery({
    queryKey: ["operator"],
    queryFn: () => api<Row>("domain/auth/me"),
    retry: false,
  });
  const data = useQuery({
    queryKey: ["resources", "console"],
    enabled: !!user.data,
    refetchInterval:
      section === "endpoints" || section === "investigations" ? 5000 : false,
    queryFn: async (): Promise<Data> => {
      const [
        cases,
        endpoints,
        hunts,
        compilations,
        scripts,
        artifacts,
        manifests,
        variants,
        benchmarks,
      ] = await Promise.all(
        [
          "cases",
          "endpoints",
          "hunts",
          "compilations",
          "scripts",
          "artifacts",
          "manifests",
          "variants",
          "benchmarks",
        ].map((path) => api<Row[]>(`domain/${path}`)),
      );
      const [jobs, observations, findings, timeline, versions] =
        await Promise.all([
          Promise.all(
            hunts!.map((r) => api<Row[]>(`domain/hunts/${r.id}/jobs`)),
          ).then((r) => r.flat()),
          Promise.all(
            cases!.map((r) =>
              api<Row[]>(`domain/observations?case_id=${r.id}`),
            ),
          ).then((r) => r.flat()),
          Promise.all(
            cases!.map((r) => api<Row[]>(`domain/findings?case_id=${r.id}`)),
          ).then((r) => r.flat()),
          Promise.all(
            cases!.map((r) => api<Row[]>(`domain/timeline?case_id=${r.id}`)),
          ).then((r) => r.flat()),
          Promise.all(
            scripts!.map((r) => api<Row[]>(`domain/scripts/${r.id}/versions`)),
          ).then((r) => r.flat()),
        ]);
      return {
        cases: cases!,
        endpoints: endpoints!,
        hunts: hunts!,
        compilations: compilations!,
        scripts: scripts!,
        artifacts: artifacts!,
        manifests: manifests!,
        variants: variants!,
        benchmarks: benchmarks!,
        jobs,
        observations,
        findings,
        timeline,
        versions,
      };
    },
  });
  const local = useQuery({
    queryKey: ["local-agent"],
    enabled: !!user.data && user.data.role === "ADMIN",
    refetchInterval: 2000,
    retry: false,
    queryFn: () => api<Row[]>("domain/local-agents"),
  });
  const [selected, setSelected] = useState<Row | null>(null);
  const [enroll, setEnroll] = useState(false);
  const [wizard, setWizard] = useState(false);
  const feed = useControlEvents(
    !!user.data && (section === "investigations" || section === "endpoints"),
  );
  if (user.isPending) return <p role="status">Checking session…</p>;
  if (user.error)
    return (
      <section className="panel">
        <h2>Sign in to Tattvastra</h2>
        <Link className="button" href="/login">
          Operator sign in
        </Link>
      </section>
    );
  if (data.error)
    return (
      <section className="panel error-panel">
        <h2>Resources unavailable</h2>
        <p>{data.error.message}</p>
        <button onClick={() => void data.refetch()}>Retry</button>
      </section>
    );
  if (!data.data) return <p role="status">Loading persisted resources…</p>;
  const d: Data = {
    ...data.data,
    endpoints: data.data.endpoints.map((e) => ({
      ...e,
      status: connectionState(
        e,
        local.data?.find((r) => r.endpoint_id === e.id),
      ),
    })),
  };
  const host = (id: unknown) =>
    str(d.endpoints.find((e) => e.id === id)?.hostname);
  const program = (h?: Row) => {
    const c = d.compilations.find((r) => r.id === h?.compilation_id);
    const v = d.versions.find((r) => r.id === c?.script_version_id);
    return str(d.scripts.find((r) => r.id === v?.script_id)?.name);
  };
  const artifactFor = (endpoint: unknown) =>
    d.artifacts.filter((a) =>
      d.jobs.some((j) => j.id === a.job_id && j.endpoint_id === endpoint),
    );
  return (
    <div className="operator-presentation">
      {section === "home" && (
        <>
          <section className="panel brand-hero">
            <div className="brand-hero-copy">
              <div className="eyebrow">TATTVASTRA // FORENSIC OPERATIONS</div>
              <h1>
                Script once.{" "}
                <span>Diversify everywhere.</span>
              </h1>
              <p>
                A JOCKY-based cross-platform forensic scripting language built
                for compilation, diversified execution, investigation, and
                verification across endpoints.
              </p>
              <ul className="brand-hero-pills">
                <li>Native compiler pipeline</li>
                <li>Variant generation</li>
                <li>Cross-platform endpoints</li>
              </ul>
            </div>
            <div className="brand-hero-visual">
              <span className="command-globe-label">GLOBAL ENDPOINT MESH</span>
              <GlobeCdn />
            </div>
          </section>
          <section className="panel command-hero command-center-hero">
            <div className="command-hero-copy">
              <div className="eyebrow">CONTROL / FORENSIC OPERATIONS</div>
              <h2>Command Center</h2>
              <p>
                Connect endpoints. Compile forensic programs. Investigate and
                verify evidence.
              </p>
              <div className="workbench-actions">
                <Link className="button" href="/investigations?new=1">
                  New Investigation
                </Link>
                <Link className="button secondary" href="/workbench">
                  Open Workbench
                </Link>
                <Link className="button secondary" href="/endpoints?connect=1">
                  Connect Endpoint
                </Link>
              </div>
            </div>
          </section>
          <section className="panel">
            <h2>Operation flow</h2>
            <p className="eyebrow">
              CONNECT → WRITE → COMPILE → DIVERSIFY → RUN → INVESTIGATE → VERIFY
            </p>
            <div className="operation-flow">
              {(() => {
                const h = d.hunts.at(-1),
                  c =
                    d.compilations.find((c) => c.id === h?.compilation_id) ??
                    d.compilations.at(-1),
                  v = d.versions.find((v) => v.id === c?.script_version_id),
                  script = d.scripts.find((s) => s.id === v?.script_id);
                return [
                  [
                    "Endpoints",
                    `${d.endpoints.filter((e) => e.status === "ONLINE" && !e.simulation).length} online`,
                    "/endpoints",
                  ],
                  [
                    "Program",
                    script?.name ?? "Write a .jky program",
                    "/workbench",
                  ],
                  [
                    "Compilation",
                    c?.status ?? "Not compiled",
                    c ? `/compiler?id=${c.id}` : "/compiler",
                  ],
                  [
                    "Variants",
                    `${d.variants.filter((v) => v.compilation_id === c?.id).length} generated`,
                    "/variants",
                  ],
                  [
                    "Investigation",
                    h?.status ?? "Start a new operation",
                    "/investigations",
                  ],
                  [
                    "Findings",
                    String(
                      d.findings.filter((f) => !h || f.case_id === h.case_id)
                        .length,
                    ),
                    "/findings",
                  ],
                  [
                    "Evidence",
                    `${d.manifests.filter((m) => m.signature_verified).length} manifests verified`,
                    "/evidence",
                  ],
                ].map(([label, value, url], index) => (
                  <Link key={str(label)} href={str(url)}>
                    <Icon
                      name={
                        (
                          [
                            "monitor",
                            "code",
                            "workflow",
                            "branch",
                            "search",
                            "triangle",
                            "shield",
                          ] as IconName[]
                        )[index]!
                      }
                    />
                    <small>{str(label)}</small>
                    <strong>{str(value)}</strong>
                    <span>→</span>
                  </Link>
                ));
              })()}
            </div>
          </section>
          <div className="metric-grid">
            {[
              [
                d.endpoints.filter((r) => r.status === "ONLINE").length,
                "Online endpoints",
              ],
              [d.hunts.length, "Investigations"],
              [d.findings.length, "Findings"],
              [
                d.manifests.filter((r) => r.signature_verified).length,
                "Verified manifests",
              ],
            ].map(([v, k], index) => (
              <section className="panel metric" key={String(k)}>
                <Icon
                  name={
                    (["monitor", "search", "triangle", "shield"] as IconName[])[
                      index
                    ]!
                  }
                />
                <strong>{v}</strong>
                <span>{k}</span>
              </section>
            ))}
          </div>
          <section className="panel">
            <h2>Recent investigations</h2>
            <Table
              headers={[
                "Investigation",
                "Status",
                "Program",
                "Endpoints",
                "Started",
                "Findings",
              ]}
              rows={d.hunts
                .slice()
                .reverse()
                .slice(0, 8)
                .map((h) => [
                  <Link
                    key={h.id}
                    className="text-link"
                    href={`/investigations?id=${h.id}`}
                  >
                    {title(d.cases.find((r) => r.id === h.case_id))}
                  </Link>,
                  str(h.status),
                  program(h),
                  items(h.endpoint_ids).length,
                  date(h.created_at),
                  d.findings.filter((f) => f.case_id === h.case_id).length,
                ])}
            />
          </section>
        </>
      )}
      {section === "endpoints" && (
        <>
          <section className="panel action-heading">
            <div>
              <h2>Endpoint inventory</h2>
              <p>
                Online state comes from authenticated agent heartbeats. Sandbox
                inventory remains offline until a real agent connects.
              </p>
            </div>
            <button onClick={() => setEnroll(true)}>Connect Endpoint</button>
          </section>
          <Table
            headers={[
              "Hostname",
              "Platform",
              "Architecture",
              "Execution capability",
              "Transport",
              "Connection",
              "Last seen",
              "Current investigation",
              "Last Run",
              "Trust",
              "Source",
            ]}
            rows={sortedEndpoints(d.endpoints).map((e) => {
              return [
                <span key={e.id} className="workbench-actions">
                  <button className="secondary" onClick={() => setSelected(e)}>
                    {str(e.hostname)}
                  </button>
                  {sandboxRow(e) && <span className="badge">SANDBOX</span>}
                </span>,
                str(e.target_os),
                str(e.target_arch),
                items(e.execution_modes).map(capabilityLabel).join(" · ") ||
                  "Not reported",
                str(e.transport_mode ?? "UNKNOWN").replaceAll("_", " "),
                <span
                  key="connection"
                  className={e.status === "ONLINE" ? "connection-online" : ""}
                >
                  {str(e.status)}
                </span>,
                date(e.last_seen),
                d.jobs
                  .filter(
                    (j) =>
                      j.endpoint_id === e.id &&
                      ["QUEUED", "DISPATCHED", "RUNNING"].includes(
                        str(j.status),
                      ),
                  )
                  .map((j) => program(d.hunts.find((h) => h.id === j.hunt_id)!))
                  .join(" · ") || "None",
                str(
                  d.jobs.filter((j) => j.endpoint_id === e.id).at(-1)?.status ??
                    "NONE",
                ),
                sandboxRow(e)
                  ? "SANDBOX"
                  : e.simulation
                    ? "Fixture identity"
                    : e.status === "REVOKED"
                      ? "Revoked"
                      : "Enrolled identity",
                e.simulation
                  ? "SANDBOX"
                  : local.data?.find((l) => l.endpoint_id === e.id)
                    ? "LOCAL"
                    : "EXTERNAL",
              ];
            })}
          />
          {(enroll ||
            (typeof window !== "undefined" &&
              new URLSearchParams(window.location.search).has("connect"))) && (
            <Enrollment
              endpoints={d.endpoints}
              openEndpoint={(endpoint) => {
                setSelected(endpoint);
                setEnroll(false);
                history.replaceState(null, "", "/endpoints");
              }}
              close={() => {
                setEnroll(false);
                history.replaceState(null, "", "/endpoints");
              }}
              refresh={refresh}
            />
          )}{" "}
          {(selected ||
            (typeof window !== "undefined" &&
              d.endpoints.find(
                (e) =>
                  e.id ===
                  new URLSearchParams(window.location.search).get("id"),
              ))) && (
            <EndpointDetail
              endpoint={
                selected ??
                d.endpoints.find(
                  (e) =>
                    e.id ===
                    new URLSearchParams(window.location.search).get("id"),
                )!
              }
              d={d}
              close={() => {
                setSelected(null);
                history.replaceState(null, "", "/endpoints");
              }}
            />
          )}
        </>
      )}
      {section === "investigations" && (
        <>
          <section className="panel action-heading">
            <div>
              <h2>Investigations</h2>
              <p>
                Choose a compiled program and authorized endpoints to start an
                investigation.
              </p>
            </div>
            <button onClick={() => setWizard(true)}>New Investigation</button>
          </section>
          <Table
            headers={[
              "Investigation",
              "Program",
              "Endpoints",
              "Status",
              "Started",
              "Findings",
            ]}
            rows={d.hunts
              .slice()
              .reverse()
              .map((h) => [
                <button
                  key={h.id}
                  className="secondary"
                  onClick={() => setSelected(h)}
                >
                  {title(d.cases.find((r) => r.id === h.case_id))}
                </button>,
                program(h),
                items(h.endpoint_ids).length,
                str(h.status),
                date(h.created_at),
                d.findings.filter((f) => f.case_id === h.case_id).length,
              ])}
          />
          {(wizard ||
            (typeof window !== "undefined" &&
              new URLSearchParams(window.location.search).has("new"))) && (
            <InvestigationWizard
              d={d}
              localIds={local.data?.map((r) => str(r.endpoint_id)) ?? []}
              close={() => {
                setWizard(false);
                history.replaceState(null, "", "/investigations");
              }}
              refresh={refresh}
              created={(h) => {
                setSelected(h);
                setWizard(false);
                history.replaceState(null, "", "/investigations");
              }}
            />
          )}
          {(selected ||
            (typeof window !== "undefined" &&
              d.hunts.find(
                (h) =>
                  h.id ===
                  new URLSearchParams(window.location.search).get("id"),
              ))) && (
            <InvestigationDetail
              hunt={
                d.hunts.find(
                  (h) =>
                    h.id ===
                    (selected?.id ??
                      new URLSearchParams(window.location.search).get("id")),
                ) ?? selected!
              }
              d={d}
              events={feed.events}
              close={() => {
                setSelected(null);
                history.replaceState(null, "", "/investigations");
              }}
            />
          )}
        </>
      )}
      {section === "findings" && (
        <>
          <Table
            headers={[
              "Severity",
              "Title",
              "Endpoint",
              "Rule",
              "First observed",
              "Observations",
              "Evidence",
              "Status",
            ]}
            rows={d.findings.map((f) => {
              const observations = d.observations.filter((o) =>
                items(f.observation_ids).includes(o.id),
              );
              return [
                str(f.severity),
                <button
                  key={f.id}
                  className="secondary"
                  onClick={() => setSelected(f)}
                >
                  {str(f.title)}
                </button>,
                host(observations[0]?.endpoint_id),
                str(f.rule_key),
                date(f.created_at),
                observations.length,
                artifactFor(observations[0]?.endpoint_id).length,
                "Derived",
              ];
            })}
          />
          {selected && (
            <FindingDetail
              finding={selected}
              d={d}
              close={() => setSelected(null)}
            />
          )}
        </>
      )}
      {section === "timeline" && <TimelineView d={d} />}
      {section === "drivers" && <DriverView d={d} />}
      {section === "performance" && <PerformanceView d={d} refresh={refresh} />}
      {section === "evidence" && <EvidenceView d={d} />}
      {section === "variants" && <VariantView d={d} refresh={refresh} />}
      {section === "graph" && <GraphView d={d} />}
    </div>
  );
}
function Table({
  headers,
  rows,
}: {
  headers: string[];
  rows: React.ReactNode[][];
}) {
  return (
    <section className="panel table-scroll">
      <table>
        <thead>
          <tr>
            {headers.map((h) => (
              <th key={h}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {r.map((v, j) => (
                <td key={j}>{v}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {!rows.length && (
        <p className="empty-state">
          No collected records yet. Connect an endpoint and run an authorized
          program.
        </p>
      )}
    </section>
  );
}
function Drawer({
  title,
  close,
  children,
}: {
  title: string;
  close: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="drawer-backdrop">
      <section
        className="operator-drawer"
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="panel-heading">
          <h2>{title}</h2>
          <button className="secondary" onClick={close}>
            Close
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}
function Fields({ data }: { data: Record<string, unknown> }) {
  return (
    <dl className="structured-fields">
      {Object.entries(data)
        .filter(([, v]) => typeof v !== "object" || v === null)
        .map(([k, v]) => (
          <div key={k}>
            <dt>{k.replaceAll("_", " ")}</dt>
            <dd>{str(v)}</dd>
          </div>
        ))}
    </dl>
  );
}
function Enrollment({
  endpoints,
  close,
  refresh,
  openEndpoint,
}: {
  endpoints: Row[];
  openEndpoint: (endpoint: Row) => void;
  close: () => void;
  refresh: () => Promise<void>;
}) {
  const queryClient = useQueryClient();
  const [path, setPath] = useState<"local" | "external" | "sandbox" | null>(
    null,
  );
  const [slot, setSlot] = useState(1);
  const [lifecycleMode, setLifecycleMode] = useState<"start" | "stop" | null>(
    null,
  );
  const [lifecycleStartedAt, setLifecycleStartedAt] = useState(0);
  const [lifecycleError, setLifecycleError] = useState("");
  const [token, setToken] = useState<Row | null>(null);
  const [sandbox, setSandbox] = useState<Row | null>(
    endpoints.find(
      (endpoint) =>
        endpoint.simulation && endpoint.transport_mode === "SANDBOX",
    ) ?? null,
  );
  const [sandboxStartedAt, setSandboxStartedAt] = useState(0);
  const [sandboxError, setSandboxError] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const pool = useQuery({
    queryKey: ["local-agent"],
    queryFn: () => api<Row[]>("domain/local-agents"),
    refetchInterval: path === "local" ? 1500 : false,
    retry: false,
  });
  const local = { ...pool, data: pool.data?.find((r) => r.slot === slot) };
  const active =
    pool.data?.filter((r) =>
      [
        "STARTING",
        "ENROLLING",
        "WAITING_FOR_HEARTBEAT",
        "ONLINE",
        "STALE",
      ].includes(str(r.state)),
    ) ?? [];
  async function localAction(action: "start" | "stop", targetSlot = slot) {
    setSlot(targetSlot);
    setBusy(true);
    setError("");
    setPath("local");
    setLifecycleMode(action);
    setLifecycleStartedAt((version) => version + 1);
    setLifecycleError("");
    try {
      const state = await submit<Row>(
        `local-agent/${action}?slot=${targetSlot}`,
      );
      queryClient.setQueryData(["local-agent"], (old: Row[] | undefined) =>
        old?.map((r) => (r.slot === targetSlot ? state : r)),
      );
      await pool.refetch();
      await refresh();
    } catch (failure) {
      const message =
        failure instanceof Error
          ? failure.message
          : "Local runtime operation failed";
      setError(message);
      setLifecycleError(message);
    } finally {
      setBusy(false);
    }
  }
  async function sandboxAction() {
    setPath("sandbox");
    setError("");
    setSandboxError("");
    setSandboxStartedAt((version) => version + 1);
    setBusy(true);
    try {
      // The backend persists WINDOWS-SANDBOX-01 and reuses it on repeat starts.
      // The floor only paces the transition: success still comes from the API.
      const [row] = await Promise.all([
        submit<Row>("endpoints/sandbox/windows"),
        new Promise((resolve) => setTimeout(resolve, 700)),
      ]);
      setSandbox(row);
      await refresh();
    } catch (e) {
      const message = e instanceof Error ? e.message : "Sandbox start failed";
      setError(message);
      setSandboxError(message);
    } finally {
      setBusy(false);
    }
  }
  const enrollment = useQuery({
    queryKey: ["enrollment-status", token?.id],
    enabled: !!token,
    refetchInterval: 3000,
    queryFn: () => api<Row>(`domain/endpoints/enrollments/${token!.id}`),
  });
  async function externalAction() {
    setPath("external");
    setError("");

    setBusy(true);
    try {
      setToken(
        await submit<Row>("endpoints/enrollments", {
          simulation: false,
          capabilities: [
            "system.read",
            "users.read",
            "process.read",
            "network.read",
            "persistence.read",
            "logs.read",
            "drivers.read",
          ],
          validity_seconds: 600,
        }),
      );
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Enrollment failed");
    } finally {
      setBusy(false);
    }
  }
  const connected = enrollment.data?.state === "ONLINE";
  const command = `jocky-agent --state-dir .jocky-agent init\njocky-agent --state-dir .jocky-agent enroll --enrollment-server https://localhost:15052 --server https://localhost:15051 --ca control-plane-ca.pem --token-file enrollment.token --worker /usr/local/bin/jocky-worker\njocky-agent --state-dir .jocky-agent connect`;
  return (
    <Drawer title="Endpoint Enrollment" close={close}>
      <div className="metric-grid enrollment-grid">
        <section className="panel">
          <h3>Local Endpoint</h3>
          <p>Local endpoints: {active.length} / 3 running</p>
          <p>Start a JOCKY agent locally using the bundled runtime.</p>
          <div className="enrollment-actions">
            <button disabled={busy} onClick={() => void localAction("start")}>
              Start Local Endpoint
            </button>
            {active.length > 0 && active.length < 3 && (
              <button
                className="secondary"
                disabled={busy}
                onClick={() => {
                  const next = pool.data?.find(
                    (r) =>
                      ![
                        "STARTING",
                        "ENROLLING",
                        "WAITING_FOR_HEARTBEAT",
                        "ONLINE",
                        "STALE",
                      ].includes(str(r.state)),
                  );
                  if (!next) return;
                  void localAction("start", Number(next.slot));
                }}
              >
                Start Another Local Endpoint
              </button>
            )}
          </div>
          {pool.data && (
            <div className="endpoint-lifecycle-stack">
              {pool.data.map((row) => {
                const rowSlot = Number(row.slot);
                const current = rowSlot === slot;
                const rowState = str(row.state);
                const inferredMode = rowState === "STOPPED" ? "stop" : "start";
                const mode =
                  current && lifecycleMode ? lifecycleMode : inferredMode;
                const rowError =
                  current && path === "local"
                    ? lifecycleError || local.error?.message || ""
                    : "";
                return (
                  <EndpointLifecycleTrace
                    key={`${rowSlot}-${mode}-${lifecycleStartedAt}`}
                    mode={mode}
                    endpoint={{
                      name: `Endpoint ${rowSlot}`,
                      ...obj(row.endpoint),
                    }}
                    state={rowState}
                    error={rowError}
                    operationPending={current && path === "local" && busy}
                    startedAt={current ? lifecycleStartedAt : 0}
                    onActivate={() => {
                      setSlot(rowSlot);
                      setPath("local");
                      setLifecycleMode(mode);
                      setLifecycleError("");
                    }}
                    onRetry={() => void localAction(mode, rowSlot)}
                  />
                );
              })}
            </div>
          )}
        </section>
        <section className="panel">
          <h3>Windows Sandbox</h3>
          <p>
            Launch a simulated Windows endpoint for cross-platform
            demonstration.
          </p>
          <button
            className="secondary"
            disabled={busy}
            onClick={() => void sandboxAction()}
          >
            {busy && path === "sandbox"
              ? "Starting Windows Sandbox…"
              : "Start Windows Sandbox"}
          </button>
          {(sandbox || sandboxError || (busy && path === "sandbox")) && (
            <EndpointLifecycleTrace
              key={`sandbox-${sandboxStartedAt}`}
              kind="windows-sandbox"
              mode="start"
              endpoint={{ name: "WINDOWS-SANDBOX-01", ...(sandbox ?? {}) }}
              state={str(sandbox?.status ?? "PENDING")}
              error={sandboxError}
              operationPending={busy && path === "sandbox"}
              startedAt={sandboxStartedAt}
              onActivate={() => setPath("sandbox")}
              onRetry={() => void sandboxAction()}
            />
          )}
        </section>
        <section className="panel">
          <h3>External Endpoint</h3>
          <p>Connect a Windows or Linux machine running the JOCKY Agent.</p>
          <button
            className="secondary"
            disabled={busy}
            onClick={() => void externalAction()}
          >
            Generate Enrollment
          </button>
        </section>
      </div>
      {path === "local" && !busy && (
        <section className="panel" aria-label="Local endpoint connection">
          <h3>Local endpoint connection</h3>
          <p role="status">
            {busy
              ? "Starting local runtime…"
              : local.data?.state === "ONLINE"
                ? "Endpoint connected"
                : local.data?.state === "ENROLLING"
                  ? "Enrolling JOCKY Agent…"
                  : local.data?.state === "WAITING_FOR_HEARTBEAT"
                    ? "Waiting for authenticated heartbeat…"
                    : local.data?.state === "STARTING"
                      ? "Starting JOCKY Agent…"
                      : str(local.data?.state ?? "Runtime unavailable")}
          </p>
          {!!local.data?.endpoint && (
            <Fields
              data={{
                hostname: obj(local.data.endpoint).hostname,
                connection: local.data.state,
                platform: obj(local.data.endpoint).target_os,
                architecture: obj(local.data.endpoint).target_arch,
                agent_version: obj(local.data.endpoint).agent_version,
                last_heartbeat: date(obj(local.data.endpoint).last_seen),
                source: "LOCAL",
              }}
            />
          )}
          {local.data?.state === "ONLINE" && (
            <button onClick={() => openEndpoint(local.data!.endpoint as Row)}>
              Open Endpoint
            </button>
          )}
          {["ONLINE", "STALE", "WAITING_FOR_HEARTBEAT"].includes(
            str(local.data?.state),
          ) && (
            <button
              className="secondary"
              disabled={busy}
              onClick={() => void localAction("stop")}
            >
              Stop Local Endpoint
            </button>
          )}
          {!!(error || local.error || local.data?.error) && (
            <>
              <p role="alert">
                {error || local.error?.message || str(local.data?.error)}
              </p>
              <button disabled={busy} onClick={() => void localAction("start")}>
                Retry
              </button>
            </>
          )}
        </section>
      )}
      {path === "external" && (
        <>
          <p>
            Generate a one-time token, save it to enrollment.token on the
            authorized endpoint, and provide the control plane CA certificate.
            Tokens expire in ten minutes.
          </p>
          <p className="resource-label">
            {connected
              ? "ONLINE · Agent connected"
              : token
                ? enrollment.data?.state === "EXPIRED"
                  ? "EXPIRED"
                  : enrollment.data?.state === "STALE"
                    ? "STALE · Agent enrolled, heartbeat overdue"
                    : "WAITING FOR AGENT"
                : "WAITING FOR ENROLLMENT"}
          </p>
          {!token && (
            <button disabled={busy} onClick={() => void externalAction()}>
              Retry Enrollment
            </button>
          )}
          {token && (
            <>
              <p>Enrollment created. Waiting for an authenticated heartbeat.</p>
              <label>
                One-time enrollment token
                <input readOnly value={str(token.one_time_token)} />
              </label>
              <button
                className="secondary"
                onClick={() =>
                  void navigator.clipboard.writeText(str(token.one_time_token))
                }
              >
                Copy token
              </button>
              <a
                className="button secondary"
                href={`/api/control/domain/endpoints/enrollments/${token.id}/ca`}
              >
                Download control plane CA
              </a>
              <p>
                Install the existing JOCKY Agent and compiler worker on Linux or
                Windows. Use the CA from the control plane; never replace it
                with an untrusted certificate.
              </p>
              <pre className="compiler-output">{command}</pre>
              <button
                className="secondary"
                onClick={() => void navigator.clipboard.writeText(command)}
              >
                Copy command
              </button>
              <small>
                Expires {date(token.expires_at)}. Endpoint inventory refreshes
                every five seconds.
              </small>
            </>
          )}
          {error && <p role="alert">{error}</p>}
        </>
      )}
      {path === "sandbox" && (
        <section className="panel" aria-label="Windows sandbox endpoint">
          <h3>Windows sandbox connection</h3>
          <p role="status">
            {busy
              ? "STARTING SANDBOX"
              : sandbox
                ? "Sandbox endpoint online"
                : str(error || "Sandbox unavailable")}
          </p>
          {sandbox && (
            <>
              <Fields
                data={{
                  hostname: sandbox.hostname,
                  connection: sandbox.status,
                  platform: sandbox.target_os,
                  architecture: sandbox.target_arch,
                  transport: str(sandbox.transport_mode).replaceAll("_", " "),
                  last_seen: date(sandbox.last_seen),
                  trust: "SANDBOX",
                  source: "SANDBOX",
                }}
              />
              <p className="resource-label">SIMULATED · SANDBOX</p>
              <p>
                Simulated endpoint. No Windows agent, TLS identity or execution
                worker is involved, and no job can be dispatched to it.
              </p>
              <button onClick={() => openEndpoint(sandbox)}>
                Open Endpoint
              </button>
            </>
          )}
        </section>
      )}
    </Drawer>
  );
}
function EndpointDetail({
  endpoint,
  d,
  close,
}: {
  endpoint: Row;
  d: Data;
  close: () => void;
}) {
  const [tab, setTab] = useState("Overview");
  const jobs = d.jobs.filter((j) => j.endpoint_id === endpoint.id);
  const observations = d.observations.filter(
    (o) => o.endpoint_id === endpoint.id,
  );
  const artifacts = d.artifacts.filter((a) =>
    jobs.some((j) => j.id === a.job_id),
  );
  const mapping: Record<string, string[]> = {
    Processes: ["processes", "process_metadata"],
    Network: ["connections", "interfaces", "routes"],
    Users: ["users", "sessions"],
    Services: ["services", "startup"],
    Drivers: ["drivers", "modules"],
  };
  return (
    <Drawer title={str(endpoint.hostname)} close={close}>
      <div className="output-tabs">
        {[
          "Overview",
          ...Object.keys(mapping),
          "Observations",
          "Jobs",
          "Evidence",
        ].map((name) => (
          <button
            className={tab === name ? "active" : "secondary"}
            key={name}
            onClick={() => setTab(name)}
          >
            {name}
          </button>
        ))}
      </div>
      {tab === "Overview" ? (
        <Fields
          data={{
            hostname: endpoint.hostname,
            OS: endpoint.target_os,
            architecture: endpoint.target_arch,
            transport: str(endpoint.transport_mode ?? "UNKNOWN").replaceAll(
              "_",
              " ",
            ),
            execution_capability: sandboxRow(endpoint)
              ? "SANDBOX / PREVIEW"
              : items(endpoint.execution_modes).join(" / "),
            status: endpoint.status,
            last_seen: date(endpoint.last_seen),
            trust: sandboxRow(endpoint)
              ? "SANDBOX"
              : endpoint.simulation
                ? "Fixture identity"
                : "Enrolled transport identity",
            source: provenance(endpoint),
            current_investigation: jobs[0]?.status,
          }}
        />
      ) : tab === "Jobs" ? (
        <Table
          headers={["Job", "Status", "Failure reason"]}
          rows={jobs.map((j) => [j.id, str(j.status), str(j.reason)])}
        />
      ) : tab === "Evidence" ? (
        <Table
          headers={["Artifact", "Bytes", "SHA-256"]}
          rows={artifacts.map((a) => [
            a.id,
            str(a.size_bytes),
            str(a.content_hash),
          ])}
        />
      ) : (
        <>
          {observations
            .filter(
              (o) =>
                tab === "Observations" ||
                mapping[tab]?.includes(str(o.collector)),
            )
            .map((o) => (
              <section className="panel" key={o.id}>
                <h3>{str(o.collector)}</h3>
                <Fields data={payload(o)} />
              </section>
            ))}
          {!observations.some(
            (o) =>
              tab === "Observations" ||
              mapping[tab]?.includes(str(o.collector)),
          ) && (
            <p className="empty-state">
              No {tab.toLowerCase()} data has been collected for this endpoint.
            </p>
          )}
        </>
      )}
    </Drawer>
  );
}
function InvestigationWizard({
  d,
  localIds,
  close,
  refresh,
  created,
}: {
  d: Data;
  localIds: string[];
  close: () => void;
  refresh: () => Promise<void>;
  created: (h: Row) => void;
}) {
  const [step, setStep] = useState(1);
  const [comp, setComp] = useState(
    () => sessionStorage.getItem("jocky-compilation") ?? "",
  );
  const [endpoints, setEndpoints] = useState<string[]>([]);
  const [mode, setMode] = useState("memory");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const c = d.compilations.find((r) => r.id === comp);
  const v = d.versions.find((r) => r.id === c?.script_version_id);
  const script = d.scripts.find((r) => r.id === v?.script_id);
  const plan = obj(obj(c?.outputs).plan);
  const required = items(plan.required_capabilities);
  const warnings = (e: Row) =>
    [
      e.simulation !== c?.simulation ? "Source provenance mismatch" : "",
      !items(e.execution_modes).includes(mode)
        ? "Execution mode unavailable"
        : "",
      required.some((cap) => !items(e.capabilities).includes(cap))
        ? "Required capability unavailable"
        : "",
      e.status !== "ONLINE" ? "Heartbeat is offline or stale" : "",
    ].filter(Boolean);
  return (
    <Drawer title="New Investigation" close={close}>
      <div className="wizard-steps">
        {["Program", "Endpoints", "Execution", "Review"].map((label, i) => (
          <span key={label} className={step === i + 1 ? "active" : ""}>
            {i + 1}. {label}
          </span>
        ))}
      </div>
      {step === 1 && (
        <>
          <h3>Choose compiled program</h3>
          <select
            aria-label="Investigation compilation"
            value={comp}
            onChange={(e) => setComp(e.target.value)}
          >
            <option value="">Choose compilation</option>
            {d.compilations
              .filter((r) => r.status === "SUCCESS")
              .map((r) => (
                <option key={r.id} value={r.id}>
                  {str(
                    d.scripts.find(
                      (s) =>
                        s.id ===
                        d.versions.find((v) => v.id === r.script_version_id)
                          ?.script_id,
                    )?.name,
                  )}{" "}
                  · {date(r.created_at)} ·{" "}
                  {str(
                    obj(obj(obj(r.outputs).llvm).manifest).target_triple ??
                      "Target not reported",
                  )}{" "}
                  · {str(r.status)}
                </option>
              ))}
          </select>
          <Link className="text-link" href="/workbench">
            Create a program in Workbench →
          </Link>
        </>
      )}
      {step === 2 && (
        <>
          <h3>Choose endpoints</h3>
          {sortedEndpoints(d.endpoints).map((e) => {
            // Only an endpoint that is currently ONLINE can accept a job. The rest
            // stay listed so the limitation is visible, but they are not selectable:
            // dispatching to a lapsed heartbeat just produces a failed job.
            const label = (
              <>
                {str(e.hostname)} · {str(e.target_os)} ·{" "}
                {e.simulation
                  ? "SANDBOX"
                  : localIds.includes(e.id)
                    ? "LOCAL"
                    : "EXTERNAL"}{" "}
                · {str(e.status)} ·{" "}
                {str(e.transport_mode ?? "UNKNOWN").replaceAll("_", " ")} · Last
                seen {date(e.last_seen)}
              </>
            );
            return e.status === "ONLINE" ? (
              <label className="endpoint-choice" key={e.id}>
                <input
                  type="checkbox"
                  checked={endpoints.includes(e.id)}
                  onChange={(ev) =>
                    setEndpoints(
                      ev.target.checked
                        ? [...endpoints, e.id]
                        : endpoints.filter((id) => id !== e.id),
                    )
                  }
                />
                <span>{label}</span>
              </label>
            ) : (
              <p className="endpoint-choice muted" key={e.id}>
                <span>{label} · Not selectable while not ONLINE</span>
              </p>
            );
          })}
        </>
      )}
      {step === 3 && (
        <>
          <h3>Execution options</h3>
          <select
            aria-label="Execution mode"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
          >
            <option value="memory">
              MEMORY / JIT · JOCKY-owned LLVM worker
            </option>
            <option value="native">NATIVE / AOT · compiler executable</option>
          </select>
          <p>
            MONITORED resource budgets. Endpoint-specific compiler variants are
            generated during start. Strict enforcement is unavailable in the
            current agent.
          </p>
        </>
      )}
      {step === 4 && (
        <>
          <h3>Review investigation</h3>
          <Fields
            data={{
              program: script?.name,
              compilation: comp,
              execution: mode,
              endpoints: endpoints.length,
              variants:
                "One compiler-generated variant per compatible endpoint",
            }}
          />
          <p>
            Required capabilities:{" "}
            {required.join(", ") || "No capability metadata available"}
          </p>
          {d.endpoints
            .filter((e) => endpoints.includes(e.id))
            .map((e) => (
              <section key={e.id}>
                <strong>{str(e.hostname)}</strong>
                <p>
                  {warnings(e).join(" · ") ||
                    "Compatible with endpoint capabilities and execution mode"}
                </p>
              </section>
            ))}
          <p>
            Incompatible endpoints receive an explicit persisted INCOMPATIBLE
            outcome; no collection is fabricated.
          </p>
        </>
      )}
      {error && <p role="alert">{error}</p>}
      <div className="workbench-actions">
        <button
          className="secondary"
          disabled={step === 1 || busy}
          onClick={() => setStep(step - 1)}
        >
          Back
        </button>
        {step < 4 ? (
          <button
            disabled={
              (step === 1 && !comp) || (step === 2 && !endpoints.length)
            }
            onClick={() => setStep(step + 1)}
          >
            Next
          </button>
        ) : (
          <button
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                const h = await submit<Row>("hunts", {
                  case_id: script?.case_id,
                  compilation_id: comp,
                  endpoint_ids: endpoints,
                  execution_mode: mode,
                  enforcement_mode: "MONITORED",
                  diverse: true,
                  retry_limit: 0,
                });
                const started = await submit<Row>(`hunts/${h.id}/start`);
                await refresh();
                created(started);
              } catch (e) {
                setError(
                  e instanceof Error ? e.message : "Investigation failed",
                );
              } finally {
                setBusy(false);
              }
            }}
          >
            {busy ? "Starting…" : "Start Investigation"}
          </button>
        )}
      </div>
    </Drawer>
  );
}
function InvestigationDetail({
  hunt,
  d,
  events,
  close,
}: {
  hunt: Row;
  d: Data;
  events: Record<string, unknown>[];
  close: () => void;
}) {
  const jobs = d.jobs.filter((j) => j.hunt_id === hunt.id);
  const compilation = d.compilations.find((c) => c.id === hunt.compilation_id);
  const version = d.versions.find(
    (v) => v.id === compilation?.script_version_id,
  );
  const program = d.scripts.find((s) => s.id === version?.script_id);
  return (
    <Drawer title="Investigation Detail" close={close}>
      <h3>{title(d.cases.find((r) => r.id === hunt.case_id))}</h3>
      <Fields
        data={{
          program: program?.name,
          compilation: hunt.compilation_id,
          status: hunt.status,
          started: date(hunt.created_at),
          elapsed: "Not measured",
          endpoints: items(hunt.endpoint_ids).length,
          findings: d.findings.filter((f) => f.case_id === hunt.case_id).length,
          evidence: d.artifacts.filter((a) =>
            jobs.some((j) => j.id === a.job_id),
          ).length,
        }}
      />
      <Table
        headers={[
          "Endpoint",
          "Variant",
          "Mode",
          "Transport",
          "Worker / duration",
          "Status",
          "Progress",
          "Observations",
          "Evidence",
          "Reason",
        ]}
        rows={jobs.map((j) => [
          str(d.endpoints.find((e) => e.id === j.endpoint_id)?.hostname),
          str(j.variant_id),
          `${str(obj(j.envelope).execution_mode ?? hunt.execution_mode)} · ${executionLabel(obj(j.progress).execution_engine)}`,
          str(obj(j.envelope).transport_mode ?? "UNKNOWN").replaceAll("_", " "),
          `${str(obj(j.progress).execution_engine ?? "Not reported")} · PID ${str(obj(j.progress).worker_pid ?? "Not reported")} · ${typeof obj(j.progress).execution_duration_ms === "number" ? Number(obj(j.progress).execution_duration_ms).toFixed(2) + " ms" : "Not measured"}`,
          str(j.status),
          Object.entries(obj(j.progress))
            .map(([k, v]) => `${k}: ${str(v)}`)
            .join(" · ") || "Not reported",
          d.observations.filter((o) => o.job_id === j.id).length,
          d.artifacts.filter((a) => a.job_id === j.id).length,
          str(j.reason),
        ])}
      />
      <h3>Committed activity</h3>
      <ol className="activity-list">
        {events
          .filter(
            (e) =>
              e.resource_id === hunt.id ||
              jobs.some((j) => j.id === e.resource_id),
          )
          .slice(0, 20)
          .map((e) => (
            <li key={str(e.id)}>
              <strong>{str(e.topic).replaceAll(".", " ")}</strong>
              <span>{date(e.created_at)}</span>
            </li>
          ))}
      </ol>
      <p>Only persisted jobs and committed events appear here.</p>
    </Drawer>
  );
}
function FindingDetail({
  finding,
  d,
  close,
}: {
  finding: Row;
  d: Data;
  close: () => void;
}) {
  const observations = d.observations.filter((o) =>
    items(finding.observation_ids).includes(o.id),
  );
  const process = payload(
    observations.find((o) => o.collector === "processes") ?? { id: "" },
  );
  const connection = payload(
    observations.find((o) => o.collector === "connections") ?? { id: "" },
  );
  return (
    <Drawer title="Finding Detail" close={close}>
      <h3>{str(finding.title)}</h3>
      <p>
        JOCKY matched stored observations through the correlation rule{" "}
        {str(finding.rule_key)}. Process and network data share the same
        endpoint and PID; review process identity and timestamps before drawing
        causal conclusions.
      </p>
      <Fields
        data={{
          severity: finding.severity,
          endpoint: d.endpoints.find(
            (e) => e.id === observations[0]?.endpoint_id,
          )?.hostname,
          user: process.user,
          process: process.name,
          PID: process.pid,
          connection: connection.remote_address ?? connection.remote,
          port: connection.remote_port,
          first_observed: date(finding.created_at),
        }}
      />
      <h3>Supporting observations</h3>
      {observations.map((o) => (
        <section className="panel" key={o.id}>
          <h3>{str(o.collector)}</h3>
          <Fields data={payload(o)} />
        </section>
      ))}
      <h3>Timeline context</h3>
      {d.timeline
        .filter((t) =>
          items(finding.observation_ids).includes(str(t.observation_id)),
        )
        .map((t) => (
          <p key={t.id}>
            {date(t.timestamp)} · {str(t.type)}
          </p>
        ))}
      <h3>Related evidence</h3>
      {d.artifacts
        .filter((a) => observations.some((o) => o.job_id === a.job_id))
        .map((a) => (
          <p className="hash" key={a.id}>
            {str(a.content_hash)}
          </p>
        ))}
      <div className="workbench-actions">
        <Link
          href={`/investigations?id=${str(d.jobs.find((j) => j.id === observations[0]?.job_id)?.hunt_id)}`}
        >
          Investigation →
        </Link>
        <Link href={`/endpoints?id=${str(observations[0]?.endpoint_id)}`}>
          Endpoint →
        </Link>
        <Link href={`/graph?finding=${finding.id}`}>Related graph →</Link>
      </div>
      <RelatedLinks />
      <details>
        <summary>Advanced / Raw Data</summary>
        <pre className="control-json">{JSON.stringify(finding, null, 2)}</pre>
      </details>
    </Drawer>
  );
}
function RelatedLinks() {
  return (
    <div className="workbench-actions">
      <Link className="button secondary" href="/findings">
        View Finding
      </Link>
      <Link className="button secondary" href="/graph">
        View in Graph
      </Link>
      <Link className="button secondary" href="/timeline">
        View in Timeline
      </Link>
      <Link className="button secondary" href="/evidence">
        View Evidence
      </Link>
    </div>
  );
}
function TimelineView({ d }: { d: Data }) {
  const [endpoint, setEndpoint] = useState("");
  const [type, setType] = useState("");
  const [severity, setSeverity] = useState("");
  const [search, setSearch] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [selected, setSelected] = useState<Row | null>(null);
  const rows = d.timeline
    .filter(
      (t) =>
        (!endpoint || t.endpoint_id === endpoint) &&
        (!type || t.type === type) &&
        (!severity || t.severity === severity) &&
        (!start || new Date(str(t.timestamp)) >= new Date(start)) &&
        (!end || new Date(str(t.timestamp)) <= new Date(end)) &&
        `${str(t.collector)} ${JSON.stringify(payload(d.observations.find((o) => o.id === t.observation_id) ?? { id: "" }))}`
          .toLowerCase()
          .includes(search.toLowerCase()),
    )
    .sort((a, b) => str(a.timestamp).localeCompare(str(b.timestamp)));
  return (
    <>
      <section className="panel">
        <div className="timeline-filters">
          <input
            aria-label="Search timeline"
            placeholder="Search process, file, IP…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select
            aria-label="Filter endpoint"
            value={endpoint}
            onChange={(e) => setEndpoint(e.target.value)}
          >
            <option value="">All endpoints</option>
            {d.endpoints.map((e) => (
              <option key={e.id} value={e.id}>
                {str(e.hostname)}
              </option>
            ))}
          </select>
          <select
            aria-label="Filter type"
            value={type}
            onChange={(e) => setType(e.target.value)}
          >
            <option value="">All types</option>
            {[...new Set(d.timeline.map((t) => str(t.type)))].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
          <select
            aria-label="Filter severity"
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
          >
            <option value="">All severities</option>
            {[...new Set(d.timeline.map((t) => str(t.severity)))].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
          <label>
            From
            <input
              type="datetime-local"
              value={start}
              onChange={(e) => setStart(e.target.value)}
            />
          </label>
          <label>
            Until
            <input
              type="datetime-local"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
            />
          </label>
          <button
            className="secondary"
            onClick={() => {
              setEndpoint("");
              setType("");
              setSeverity("");
              setSearch("");
              setStart("");
              setEnd("");
            }}
          >
            Clear filters
          </button>
        </div>
      </section>
      <section className="panel">
        <ol className="forensic-timeline">
          {rows.map((t) => {
            const observation = d.observations.find(
              (o) => o.id === t.observation_id,
            );
            const fields = payload(observation ?? { id: "" });
            const related = d.findings.some((f) =>
              items(f.observation_ids).includes(str(t.observation_id)),
            );
            return (
              <li key={t.id}>
                <time>{date(t.timestamp)}</time>
                <button
                  className="timeline-event"
                  onClick={() => setSelected(t)}
                >
                  <strong>
                    {str(
                      d.endpoints.find((e) => e.id === t.endpoint_id)?.hostname,
                    )}{" "}
                    ·{" "}
                    {str(
                      fields.name ??
                        fields.remote_address ??
                        fields.path ??
                        t.type,
                    )}
                  </strong>
                  <span>
                    {str(t.collector)} · {str(t.severity)}{" "}
                    {related ? "· Related finding" : ""}
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
        {!rows.length && <p>No events match these filters.</p>}
      </section>
      {selected && (
        <Drawer title="Timeline Event" close={() => setSelected(null)}>
          <Fields
            data={{
              timestamp: selected.timestamp,
              endpoint: d.endpoints.find((e) => e.id === selected.endpoint_id)
                ?.hostname,
              collector: selected.collector,
              severity: selected.severity,
              time_basis: selected.time_basis,
            }}
          />
          <Fields
            data={payload(
              d.observations.find((o) => o.id === selected.observation_id) ?? {
                id: "",
              },
            )}
          />
          <p>
            Related finding:{" "}
            {d.findings
              .filter((f) =>
                items(f.observation_ids).includes(str(selected.observation_id)),
              )
              .map((f) => str(f.title))
              .join(", ") || "None"}
          </p>
          <RelatedLinks />
        </Drawer>
      )}
    </>
  );
}
function DriverView({ d }: { d: Data }) {
  const [endpoint, setEndpoint] = useState("");
  const [selected, setSelected] = useState<Row | null>(null);
  const drivers = d.observations.filter(
    (o) =>
      ["drivers", "modules", "driver_hash", "driver_signatures"].includes(
        str(o.collector),
      ) &&
      (!endpoint || o.endpoint_id === endpoint),
  );
  const platform = (o: Row) =>
    d.endpoints.find((e) => e.id === o.endpoint_id)?.target_os;
  const linux = drivers.filter((o) => platform(o) === "linux"),
    windows = drivers.filter((o) => platform(o) !== "linux");
  const known = drivers.filter((o) => typeof payload(o).signed === "boolean");
  return (
    <>
      <div className="metric-grid">
        {[
          ["Modules / drivers", drivers.length],
          [
            "Endpoints reporting",
            new Set(drivers.map((o) => o.endpoint_id)).size,
          ],
          [
            "Unsigned signatures",
            known.filter((o) => payload(o).signed === false).length,
          ],
          [
            "Review items",
            drivers.filter((o) =>
              ["REVIEW", "KNOWN RISK"].includes(str(payload(o).risk)),
            ).length,
          ],
        ].map(([label, value]) => (
          <section className="panel metric" key={str(label)}>
            <strong>{str(value)}</strong>
            <span>{str(label)}</span>
          </section>
        ))}
      </div>
      <p>
        Signature metadata reported for {known.length} of {drivers.length}{" "}
        items; unavailable signatures are unknown, not unsigned.
      </p>
      <label>
        Endpoint
        <select
          aria-label="Driver endpoint"
          value={endpoint}
          onChange={(e) => setEndpoint(e.target.value)}
        >
          <option value="">All endpoints</option>
          {d.endpoints.map((e) => (
            <option key={e.id} value={e.id}>
              {str(e.hostname)}
            </option>
          ))}
        </select>
      </label>
      <h2>Linux module inventory</h2>
      <Table
        headers={["Module", "Path", "Size (bytes)", "Endpoint", "Source"]}
        rows={linux.map((o) => [
          <button
            key={o.id}
            className="secondary"
            onClick={() => setSelected(o)}
          >
            {str(payload(o).name)}
          </button>,
          str(payload(o).path),
          str(payload(o).size ?? "Unreported"),
          str(d.endpoints.find((e) => e.id === o.endpoint_id)?.hostname),
          provenance(o),
        ])}
      />
      <h2>Windows driver inventory</h2>
      <Table
        headers={["Driver", "Path", "Signature", "Endpoint", "Source"]}
        rows={windows.map((o) => [
          <button
            key={o.id}
            className="secondary"
            onClick={() => setSelected(o)}
          >
            {str(payload(o).name)}
          </button>,
          str(payload(o).path),
          payload(o).signed === true
            ? "Signed"
            : payload(o).signed === false
              ? "Unsigned"
              : "Unknown",
          str(d.endpoints.find((e) => e.id === o.endpoint_id)?.hostname),
          provenance(o),
        ])}
      />
      {selected && (
        <Drawer title="Driver Detail" close={() => setSelected(null)}>
          <Fields
            data={{
              endpoint: d.endpoints.find((e) => e.id === selected.endpoint_id)
                ?.hostname,
              source: provenance(selected),
              observation: selected.id,
              ...payload(selected),
            }}
          />
          <p>
            Risk is unknown unless explicitly supported by collected metadata.
            No CVE or exploitation claim is inferred.
          </p>
          <RelatedLinks />
        </Drawer>
      )}
    </>
  );
}
function numbers(value: unknown, prefix = ""): [string, number][] {
  return Object.entries(obj(value)).flatMap(([k, v]) =>
    typeof v === "number"
      ? [[`${prefix}${k}`, v] as [string, number]]
      : v && typeof v === "object" && !Array.isArray(v)
        ? numbers(v, `${prefix}${k}.`)
        : [],
  );
}
function PerformanceView({
  d,
  refresh,
}: {
  d: Data;
  refresh: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [comp, setComp] = useState(
    d.compilations.filter((c) => c.status === "SUCCESS").at(-1)?.id ?? "",
  );
  const samples = d.benchmarks.flatMap((b) => {
    const measured = obj(b.measurements);
    return (Array.isArray(measured.samples) ? measured.samples : []).flatMap(
      (sample, i) =>
        numbers(sample).map(([metric, value]) => [
          date(b.created_at),
          i + 1,
          metric,
          value,
        ]),
    );
  });
  const [view, setView] = useState("latest");
  const [latestRun, setLatestRun] = useState("");
  const [notice, setNotice] = useState("");
  const runs = d.benchmarks.filter((b) => b.compilation_id === comp);
  const profiles = runs.flatMap((b) => {
    const samples = obj(b.measurements).samples;
    return Array.isArray(samples)
      ? samples.map((s) => obj(obj(s).profile))
      : [];
  });
  const fallback = obj(
    obj(obj(d.compilations.find((c) => c.id === comp)?.outputs).llvm).profile,
  );
  const current = profiles.at(-1) ?? fallback;
  const median = (values: number[]) => {
    const sorted = [...values].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2
      ? sorted[mid]!
      : (sorted[mid - 1]! + sorted[mid]!) / 2;
  };
  const profile: Record<string, unknown> =
    view === "median" && profiles.length > 1
      ? Object.fromEntries(
          Object.keys(current).map((k) => {
            const values = profiles
              .map((p) => p[k])
              .filter((v): v is number => typeof v === "number");
            return [k, values.length ? median(values) : null];
          }),
        )
      : current;
  const timings = Object.entries(profile).filter(
    ([key, value]) => key.endsWith("_ms") && typeof value === "number",
  ) as [string, number][];
  const total = stageTotal(profile),
    totals = profiles.map(stageTotal).filter((v): v is number => v !== null);
  const sum = (keys: string[]) => {
    const values = keys.map((k) => profile[k]);
    return values.every((v) => typeof v === "number")
      ? (values as number[]).reduce((a, b) => a + b, 0)
      : null;
  };
  const maximum = Math.max(...timings.map(([, value]) => value), 0.001);
  return (
    <>
      <section className="panel action-heading">
        <div>
          <h2>Compiler measurements</h2>
          <p>
            Measured native compiler fixture timings. Endpoint performance is
            shown only when reported by the actual agent.
          </p>
        </div>
        <div>
          <select
            aria-label="Benchmark compilation"
            value={comp}
            onChange={(e) => setComp(e.target.value)}
          >
            {d.compilations
              .filter((c) => c.status === "SUCCESS")
              .map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id}
                </option>
              ))}
          </select>
          <button
            disabled={busy || !comp}
            onClick={async () => {
              setBusy(true);
              try {
                const measured = await submit<Row>("benchmarks", {
                  compilation_id: comp,
                  repetitions: 3,
                });
                setLatestRun(measured.id);
                setNotice(
                  measured.status === "SUCCESS"
                    ? "Benchmark complete ✓"
                    : "Benchmark did not complete; inspect its saved status.",
                );
                await refresh();
              } catch (e) {
                setError(e instanceof Error ? e.message : "Measurement failed");
              } finally {
                setBusy(false);
              }
            }}
          >
            {busy ? "RUNNING…" : "Measure Compiler"}
          </button>
        </div>
      </section>
      {error && <p role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
      <div className="metric-grid">
        {[
          ["Compile stage sum", total],
          [
            "Frontend time",
            sum(["lex_ms", "parse_ms", "semantic_ms", "jir_ms"]),
          ],
          [
            "LLVM / optimization",
            sum(["llvm_generation_ms", "optimization_ms"]),
          ],
          ["Variant time", profile.variant_ms],
        ].map(([label, value]) => (
          <section className="panel metric" key={str(label)}>
            <strong>
              {typeof value === "number"
                ? `${value.toFixed(3)} ms`
                : "Not measured"}
            </strong>
            <span>{str(label)}</span>
          </section>
        ))}
      </div>
      <p>
        Total is the sum of available non-overlapping recorded compile stages,
        not wall-clock request latency. Latest run:{" "}
        {date(runs.at(-1)?.created_at)} · {profiles.length} samples.
      </p>
      {totals.length > 1 && (
        <Fields
          data={{
            "Minimum stage sum (ms)": Math.min(...totals),
            "Median stage sum (ms)": median(totals),
            "Maximum stage sum (ms)": Math.max(...totals),
          }}
        />
      )}
      <label>
        Timing view
        <select
          aria-label="Timing view"
          value={view}
          onChange={(e) => setView(e.target.value)}
        >
          <option value="latest">Latest</option>
          <option value="median" disabled={profiles.length < 2}>
            Median
          </option>
        </select>
      </label>
      <section className="panel">
        <h2>Recent Measurements</h2>
        <Table
          headers={[
            "Run",
            "Measured",
            "Samples",
            "Compile stage sum (ms)",
            "Status",
          ]}
          rows={runs
            .slice()
            .reverse()
            .slice(0, 8)
            .map((b) => {
              const values = Array.isArray(obj(b.measurements).samples)
                ? (obj(b.measurements).samples as unknown[])
                    .map((s) => stageTotal(obj(obj(s).profile)))
                    .filter((v): v is number => v !== null)
                : [];
              return [
                <strong
                  key={b.id}
                  className={latestRun === b.id ? "measurement-new" : ""}
                >
                  {latestRun === b.id ? "✓ New measurement" : shortHash(b.id)}
                </strong>,
                date(b.created_at),
                values.length,
                values.length ? median(values).toFixed(3) : "Not measured",
                str(b.status),
              ];
            })}
        />
      </section>
      <section className="panel">
        <h2>Selected compilation stage latency</h2>
        {timings.length ? (
          timings.map(([stage, milliseconds]) => (
            <div key={stage} className="latency-row">
              <span>{stage.replaceAll("_", " ")}</span>
              <meter
                min={0}
                max={maximum}
                value={milliseconds}
                aria-label={stage}
              />
              <strong>{milliseconds.toFixed(3)} ms</strong>
            </div>
          ))
        ) : (
          <p>Stage durations: Not measured.</p>
        )}
        <h3>Variant measurements</h3>
        <Table
          headers={["Variant", "Seed", "Build measurements"]}
          rows={d.variants
            .filter((v) => v.compilation_id === comp)
            .map((v) => [
              v.id,
              str(v.seed),
              numbers(obj(v.manifest).profile)
                .filter(([key]) => key.endsWith("_ms"))
                .map(([key, value]) => `${key}: ${value} ms`)
                .join(" · ") || "Not measured",
            ])}
        />
      </section>
      <Table
        headers={["Measured", "Sample", "Metric / unit", "Value"]}
        rows={samples}
      />
      <section className="panel">
        <h2>Investigation Performance</h2>
        <p>
          Dispatch latency, execution duration, and evidence throughput: not
          measured unless explicitly reported below.
        </p>
        <Table
          headers={[
            "Job",
            "Status",
            "Observations",
            "Evidence",
            "Reported measurements",
          ]}
          rows={d.jobs.map((j) => [
            j.id,
            str(j.status),
            d.observations.filter((o) => o.job_id === j.id).length,
            d.artifacts.filter((a) => a.job_id === j.id).length,
            numbers(j.progress)
              .map(([k, v]) => `${k}: ${v}`)
              .join(" · ") || "Not measured",
          ])}
        />
      </section>
      <section className="panel">
        <h2>Endpoint health</h2>
        <Table
          headers={[
            "Endpoint",
            "State",
            "Last seen",
            "CPU / memory / heartbeat latency",
          ]}
          rows={d.endpoints.map((e) => [
            str(e.hostname),
            str(e.status),
            date(e.last_seen),
            "Not measured",
          ])}
        />
      </section>
      <section className="panel">
        <h2>Collectors</h2>
        <Table
          headers={["Collector", "Records produced", "Duration"]}
          rows={[...new Set(d.observations.map((o) => str(o.collector)))].map(
            (c) => [
              c,
              d.observations.filter((o) => o.collector === c).length,
              "Not measured",
            ],
          )}
        />
      </section>
    </>
  );
}
function HashValue({ value }: { value: unknown }) {
  return (
    <span className="hash-value" title={str(value)}>
      {shortHash(value)}
      {typeof value === "string" && (
        <button
          className="secondary compact"
          aria-label="Copy hash"
          onClick={() => void navigator.clipboard.writeText(value)}
        >
          Copy
        </button>
      )}
    </span>
  );
}
function EvidenceView({ d }: { d: Data }) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [states, setStates] = useState<Record<string, string>>({});
  async function verify(row: Row, kind: "artifact" | "manifest") {
    setResult({ kind, row, pending: true });
    setStates((old) => ({ ...old, [row.id]: "VERIFYING…" }));
    try {
      const checked = await submit<Record<string, unknown>>(
        `${kind === "artifact" ? "artifacts" : "manifests"}/${row.id}/verify`,
      );
      const valid =
        kind === "artifact"
          ? checked.available &&
            checked.expected_hash &&
            checked.computed_hash &&
            checked.integrity_valid
          : checked.signature_valid && checked.integrity_valid;
      setStates((old) => ({
        ...old,
        [row.id]: valid ? "✓ VERIFIED" : "✕ FAILED",
      }));
      setResult({ kind, row, checked, pending: false });
    } catch (error) {
      setResult({
        kind,
        row,
        error: error instanceof Error ? error.message : "Verification failed",
      });
      setStates((old) => ({ ...old, [row.id]: "✕ FAILED" }));
    }
  }
  const row = obj(result?.row),
    checked = obj(result?.checked),
    job = d.jobs.find((j) => j.id === row.job_id),
    endpoint = d.endpoints.find((e) => e.id === job?.endpoint_id),
    hunt = d.hunts.find((h) => h.id === job?.hunt_id),
    manifest = d.manifests.find((m) => m.job_id === row.job_id);
  return (
    <>
      <section className="panel">
        <h2>Forensic artifacts</h2>
        <p>
          Verify stored bytes independently from signed manifest provenance.
        </p>
      </section>
      <Table
        headers={[
          "Artifact",
          "Endpoint",
          "Bytes",
          "Created",
          "SHA-256",
          "Source",
          "Integrity",
        ]}
        rows={d.artifacts.map((a) => [
          <Link
            key={a.id}
            href={`/investigations?id=${str(d.jobs.find((j) => j.id === a.job_id)?.hunt_id)}`}
          >
            {shortHash(a.id)}
          </Link>,
          str(
            d.endpoints.find(
              (e) =>
                e.id === d.jobs.find((j) => j.id === a.job_id)?.endpoint_id,
            )?.hostname,
          ),
          str(a.size_bytes),
          date(a.created_at),
          <HashValue key={a.id} value={a.content_hash} />,
          provenance(a),
          <button
            key={a.id}
            disabled={states[a.id] === "VERIFYING…"}
            onClick={() => void verify(a, "artifact")}
          >
            {states[a.id] ?? "VERIFY INTEGRITY"}
          </button>,
        ])}
      />
      <h2>Signed evidence manifests</h2>
      <Table
        headers={["Manifest", "Job", "Signature", "Action"]}
        rows={d.manifests.map((m) => [
          shortHash(m.id),
          shortHash(m.job_id),
          m.signature_verified ? "Verified at ingestion" : "Not checked",
          <button
            key={m.id}
            disabled={states[m.id] === "VERIFYING…"}
            onClick={() => void verify(m, "manifest")}
          >
            {states[m.id] ?? "Verify manifest"}
          </button>,
        ])}
      />
      {result && (
        <Drawer
          title={
            result.kind === "artifact"
              ? "Integrity result"
              : "Manifest verification"
          }
          close={() => setResult(null)}
        >
          {!!result.pending && <p role="status">VERIFYING…</p>}
          {!!result.error && <p role="alert">{str(result.error)}</p>}
          {result.kind === "artifact" ? (
            <>
              <Fields
                data={{
                  "Artifact ID": row.id,
                  Endpoint: endpoint?.hostname,
                  Job: row.job_id,
                  Created: date(row.created_at),
                  Bytes: row.size_bytes,
                  Variant: job?.variant_id,
                  Integrity: result.pending
                    ? "VERIFYING"
                    : checked.available &&
                        checked.expected_hash &&
                        checked.computed_hash
                      ? checked.integrity_valid
                        ? "VALID"
                        : "INVALID"
                      : "NOT VERIFIED / CONTENT UNAVAILABLE",
                  Manifest: manifest ? "NOT CHECKED" : "NOT PRESENT",
                }}
              />
              <h3>Stored SHA-256</h3>
              <HashValue value={row.content_hash} />
              <h3>Recomputed SHA-256</h3>
              <HashValue
                value={checked.computed_hash ?? "Awaiting content verification"}
              />
              {manifest && (
                <button onClick={() => void verify(manifest, "manifest")}>
                  Verify related manifest
                </button>
              )}
            </>
          ) : (
            <>
              <Fields
                data={{
                  "Manifest ID": row.id,
                  Signature: result.pending
                    ? "VERIFYING"
                    : checked.signature_valid
                      ? "VALID"
                      : "INVALID",
                  "Signing agent": endpoint?.hostname,
                  "Signing identity": obj(row.document).agent_identity,
                  "Execution mode": obj(row.document).execution_mode,
                  "Execution engine": obj(row.document).execution_engine,
                  "Worker PID": obj(row.document).worker_pid,
                  "Worker duration (ms)": obj(row.document)
                    .execution_duration_ms,
                  Transport: obj(row.document).transport_mode,
                  Endpoint: endpoint?.hostname,
                  Job: row.job_id,
                  "Artifact count": d.artifacts.filter(
                    (a) => a.job_id === row.job_id,
                  ).length,
                  "Provenance / integrity": result.pending
                    ? "VERIFYING"
                    : checked.integrity_valid
                      ? "VALID"
                      : "INVALID",
                  Completed: date(obj(row.document).completed_at),
                  Variant: job?.variant_id,
                }}
              />
              <p>
                A valid signature authenticates manifest provenance. It does not
                replace independent artifact-byte verification.
              </p>
              <Fields data={checked} />
            </>
          )}
          <div className="workbench-actions">
            {hunt && (
              <Link href={`/investigations?id=${hunt.id}`}>
                Investigation →
              </Link>
            )}
            {endpoint && (
              <Link href={`/endpoints?id=${endpoint.id}`}>Endpoint →</Link>
            )}
          </div>
        </Drawer>
      )}
    </>
  );
}
function VariantView({
  d,
  refresh,
}: {
  d: Data;
  refresh: () => Promise<void>;
}) {
  // Read deep links from the router, not from window.location: a client-side
  // navigation commits the address bar after this component can first render,
  // so the window would still report the URL we navigated away from.
  const params = useSearchParams();
  const [comp, setComp] = useState(
    () =>
      (typeof window === "undefined" ? null : params.get("compilation")) ??
      d.compilations.filter((c) => c.status === "SUCCESS").at(-1)?.id ??
      "",
  );
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [comparison, setComparison] = useState<Record<string, unknown> | null>(
    null,
  );
  const router = useRouter();
  // The console resources are a single shared snapshot, cached for ten seconds.
  // A build can finish inside that window, so entering this view would otherwise
  // render "no collected records" for variants that already exist.
  useEffect(() => {
    void refresh();
  }, [refresh]);
  const buildFilter =
    typeof window === "undefined" ? null : params.get("build");
  const variants = d.variants.filter(
    (v) =>
      v.compilation_id === comp &&
      (!buildFilter || v.build_run_id === buildFilter),
  );
  return (
    <>
      <section className="panel action-heading">
        <div>
          <h2>One forensic intent → multiple verified builds</h2>
          <Link className="text-link" href="/forge">
            Build Forge →
          </Link>
          <select
            aria-label="Variant compilation"
            value={comp}
            onChange={(e) => setComp(e.target.value)}
          >
            {d.compilations
              .filter((c) => c.status === "SUCCESS")
              .map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id}
                </option>
              ))}
          </select>
        </div>
        <button
          disabled={busy || !comp}
          onClick={async () => {
            setBusy(true);
            try {
              const built = await submit<Row>("build-runs", {
                compilation_id: comp,
                count: 3,
              });
              setNotice("Delivery build started ✓");
              router.push(`/forge?compilation=${comp}&build=${built.id}`);
            } catch (e) {
              setError(e instanceof Error ? e.message : "Build failed");
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? "Starting…" : "Build 3 Verified Variants"}
        </button>
      </section>
      {notice && <p role="status">{notice}</p>}
      <Link href={`/compiler?id=${comp}`}>Compilation →</Link>
      {error && <p role="alert">{error}</p>}
      <Table
        headers={[
          "Variant",
          "Seed",
          "Target",
          "Execution",
          "Artifact SHA-256",
          "LLVM identity",
          "Build / structure",
        ]}
        rows={variants.map((v, i) => [
          `Variant ${String.fromCharCode(65 + i)}`,
          str(v.seed),
          str(obj(v.manifest).target_triple),
          str(obj(v.manifest).execution_mode),
          <HashValue key={v.id} value={v.content_hash} />,
          <HashValue key={v.id} value={obj(v.manifest).llvm_ir_hash} />,
          <Fields
            key={v.id}
            data={{
              variant_ms:
                obj(obj(v.manifest).profile).variant_ms ?? "Not measured",
              aot_ms: obj(obj(v.manifest).profile).aot_ms ?? "Not measured",
              bytes: obj(v.manifest).artifact_size_bytes ?? "Not measured",
              equivalence: obj(v.manifest).equivalence_status ?? "NOT TESTED",
              artifact_format: obj(v.manifest).artifact_format,
              link_status: obj(v.manifest).link_status ?? "Not reported",
              structural_fingerprint: obj(v.manifest).structural_fingerprint,
              jir_identity: obj(v.manifest).jir_hash,
              ...obj(obj(v.manifest).structural_metrics),
            }}
          />,
        ])}
      />
      <button
        disabled={variants.length < 2}
        onClick={async () => {
          try {
            setComparison(
              await submit("variants/compare", {
                variant_ids: variants.slice(0, 3).map((v) => v.id),
              }),
            );
          } catch (e) {
            setError(e instanceof Error ? e.message : "Comparison failed");
          }
        }}
      >
        Compare variants
      </button>
      {comparison && (
        <Drawer title="Variant comparison" close={() => setComparison(null)}>
          <h3>Same forensic intent → distinct compiled variants</h3>
          <Fields
            data={{
              "Source identity": comparison.same_source ? "SAME" : "DIFFERENT",
              "Artifact identities":
                Number(comparison.distinct_artifacts) > 1
                  ? "DIFFERENT"
                  : "IDENTICAL",
              "LLVM identities": variants
                .slice(0, 3)
                .some((v) => !obj(v.manifest).llvm_ir_hash)
                ? "NOT REPORTED"
                : new Set(
                      variants
                        .slice(0, 3)
                        .map((v) => obj(v.manifest).llvm_ir_hash),
                    ).size > 1
                  ? "DIFFERENT"
                  : "IDENTICAL",
              "Semantic equivalence": str(
                comparison.semantic_equivalence,
              ).replaceAll("_", " "),
            }}
          />
          <Table
            headers={[
              "Variant",
              "Artifact",
              "LLVM",
              "Variant build (ms)",
              "AOT (ms)",
              "Bytes / delta from A",
              "Structure",
            ]}
            rows={variants.slice(0, 3).map((v, i) => [
              `Variant ${String.fromCharCode(65 + i)}`,
              <HashValue key={v.id} value={v.content_hash} />,
              <HashValue key={v.id} value={obj(v.manifest).llvm_ir_hash} />,
              str(obj(obj(v.manifest).profile).variant_ms ?? "Not measured"),
              str(obj(obj(v.manifest).profile).aot_ms ?? "Not measured"),
              typeof obj(v.manifest).artifact_size_bytes === "number" &&
              typeof obj(variants[0]?.manifest).artifact_size_bytes === "number"
                ? `${obj(v.manifest).artifact_size_bytes} B / ${Number(obj(v.manifest).artifact_size_bytes) - Number(obj(variants[0]?.manifest).artifact_size_bytes)} B`
                : "Not measured",
              Object.entries(obj(obj(v.manifest).structural_metrics))
                .filter(([, value]) => typeof value === "number")
                .map(([k, value]) => `${k}: ${value}`)
                .join(" · "),
            ])}
          />
          <p>
            {comparison.semantic_equivalence === "VERIFIED"
              ? "Equivalent source/JIR/plan and deterministic compiler fixture results verified. This is not universal or endpoint equivalence."
              : "Structural diversity is proven by generated artifacts. Semantic equivalence has not been evaluated for this compilation."}
          </p>
          <p>
            Stage timings are compiler measurements. They exclude control-plane
            dispatch and native worker linking; a total wall-clock build latency
            is not reported. Older builds may lack stored measurements.
          </p>
        </Drawer>
      )}
    </>
  );
}
function GraphView({ d }: { d: Data }) {
  const [kind, setKind] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Record<string, unknown> | null>(
    null,
  );
  const query = useQuery({
    queryKey: ["graph", d.cases.map((c) => c.id)],
    queryFn: async () => {
      const graphs = await Promise.all(
        d.cases.map((c) =>
          api<{
            nodes: Record<string, unknown>[];
            edges: { source: string; target: string; relationship: string }[];
          }>(`domain/graph?case_id=${c.id}`),
        ),
      );
      return {
        nodes: graphs.flatMap((g) => g.nodes),
        edges: graphs.flatMap((g) => g.edges),
      };
    },
  });
  const raw = query.data ?? { nodes: [], edges: [] };
  const graph = aggregateConnections(raw.nodes, raw.edges, d.observations);
  const [finding, setFinding] = useState(() =>
    typeof window !== "undefined"
      ? (new URLSearchParams(window.location.search).get("finding") ??
        d.findings[0]?.id ??
        "")
      : "",
  );
  const related = new Set<string>();
  const focus = d.findings.find((f) => f.id === finding);
  if (focus) {
    for (const node of graph.nodes)
      if (
        items(focus.observation_ids).some((id) =>
          items(node.observation_ids).includes(id),
        ) ||
        items(focus.observation_ids).includes(str(node.id)) ||
        node.finding_id === focus.id ||
        node.id === `finding:${focus.id}`
      )
        related.add(str(node.id));
    for (let step = 0; step < 2; step++)
      for (const edge of graph.edges)
        if (related.has(edge.target)) related.add(edge.source);
  }

  const label = (n: Record<string, unknown>) => {
    const observed = payload(
      d.observations.find((o) => o.id === (n.observation_id ?? n.id)) ?? {
        id: "",
      },
    );
    if (n.type === "Finding")
      return str(
        d.findings.find((f) => `finding:${f.id}` === n.id)?.title ?? "Finding",
      );
    if (n.type === "Process") {
      const process = d.observations.find(
        (o) =>
          o.collector === "processes" &&
          str(payload(o).pid) === str(n.pid) &&
          str(n.id).includes(str(o.endpoint_id)) &&
          str(n.id).includes(str(o.job_id)),
      );
      return process
        ? `${str(payload(process).name)} / PID ${str(n.pid)}`
        : `PID ${str(n.pid)}`;
    }
    if (n.type === "Connection")
      return `${str(observed.remote_address ?? observed.remote_ip ?? observed.remote ?? observed.local_address ?? "Connection")}${observed.remote_port != null ? `:${observed.remote_port}` : ""}`;
    return str(
      n.name ??
        n.address ??
        n.hostname ??
        d.endpoints.find((e) => str(n.id) === e.id)?.hostname ??
        observed.name ??
        observed.path ??
        observed.remote_address ??
        observed.remote_ip ??
        observed.remote ??
        (n.pid ? `PID ${n.pid}` : n.type),
    );
  };
  const nodes = graph.nodes.filter(
    (n) =>
      (!kind || n.type === kind) &&
      (!focus || related.has(str(n.id))) &&
      label(n).toLowerCase().includes(search.toLowerCase()),
  );
  const levels = [
    ["Endpoint"],
    ["User", "Finding"],
    ["Process"],
    ["File", "Service", "Driver", "Connection"],
    ["IP", "Observation"],
  ];
  const positions = new Map(
    nodes.map((n) => {
      const level = Math.max(
        0,
        levels.findIndex((types) => types.includes(str(n.type))),
      );
      const siblings = nodes.filter((other) =>
        levels[level]!.includes(str(other.type)),
      );
      return [
        str(n.id),
        {
          x: 115 + level * 205,
          y: 65 + siblings.findIndex((other) => other.id === n.id) * 105,
        },
      ];
    }),
  );
  const xs = [...positions.values()].map((p) => p.x),
    left = xs.length ? Math.min(...xs) - 110 : 0,
    width = xs.length ? Math.max(...xs) - left + 110 : 1000;
  return (
    <section className="panel">
      <p>
        Connections with matching endpoint, job, process and socket identity are
        visually grouped; raw observations remain unchanged.
      </p>
      <div className="timeline-filters">
        <select
          aria-label="Related finding"
          value={finding}
          onChange={(e) => setFinding(e.target.value)}
        >
          <option value="">All relationships</option>
          {d.findings.map((f) => (
            <option key={f.id} value={f.id}>
              Related to {str(f.title)}
            </option>
          ))}
        </select>
        <input
          aria-label="Search graph"
          placeholder="Search node…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          aria-label="Node type"
          value={kind}
          onChange={(e) => setKind(e.target.value)}
        >
          <option value="">All node types</option>
          {[...new Set(graph.nodes.map((n) => str(n.type)))].map((v) => (
            <option key={v}>{v}</option>
          ))}
        </select>
        <button
          className="secondary"
          onClick={() => {
            setKind("");
            setSearch("");
          }}
        >
          Fit to view
        </button>
        <button
          className="secondary"
          onClick={() => {
            setKind("");
            setSearch("");
            setFinding("");
            setSelected(null);
          }}
        >
          Reset view
        </button>
      </div>
      <svg
        className="forensic-graph"
        viewBox={`${left} 0 ${width} ${Math.max(280, ...[...positions.values()].map((p) => p.y + 80))}`}
        aria-label="Forensic relationships"
      >
        {graph.edges.map((e, i) => {
          const a = positions.get(e.source),
            b = positions.get(e.target);
          return a && b ? (
            <line
              className={
                selected &&
                (e.source === selected.id || e.target === selected.id)
                  ? "selected-edge"
                  : ""
              }
              key={i}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
            >
              <title>{e.relationship}</title>
            </line>
          ) : null;
        })}
        {nodes.map((n) => {
          const p = positions.get(str(n.id))!;
          return (
            <g
              data-node-type={str(n.type).toLowerCase()}
              className={selected?.id === n.id ? "selected-node" : ""}
              key={str(n.id)}
              role="button"
              tabIndex={0}
              aria-label={`Inspect ${str(n.type)}`}
              transform={`translate(${p.x},${p.y})`}
              onClick={() => setSelected(n)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") setSelected(n);
              }}
            >
              <rect x={-85} y={-28} width={170} height={60} rx={9} />
              <text textAnchor="middle" y={-3}>
                {str(n.type)}
                {n.type === "Connection" && Number(n.count) > 1
                  ? ` × ${n.count}`
                  : ""}
              </text>
              <text textAnchor="middle" y={18} className="graph-detail">
                {label(n).slice(0, 25)}
              </text>
            </g>
          );
        })}
      </svg>
      {selected && (
        <Drawer title="Node Detail" close={() => setSelected(null)}>
          <Fields data={{ label: label(selected), ...selected }} />
          <h3>Supporting observations</h3>
          {d.observations
            .filter((o) => items(selected.observation_ids).includes(o.id))
            .map((o) => (
              <section key={o.id} className="panel">
                <Fields data={{ collector: o.collector, ...payload(o) }} />
              </section>
            ))}
          <RelatedLinks />
        </Drawer>
      )}
    </section>
  );
}
