"use client";
import Link from "next/link";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useControlEvents } from "../lib/use-control-events";
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
        <h2>Sign in to JOCKY</h2>
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
  const d = data.data;
  const refresh = async () => {
    await client.invalidateQueries({ queryKey: ["resources"] });
  };
  const host = (id: unknown) =>
    str(d.endpoints.find((e) => e.id === id)?.hostname);
  const program = (h: Row) => {
    const c = d.compilations.find((r) => r.id === h.compilation_id);
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
          <section className="panel command-hero">
            <div>
              <h1>Command Center</h1>
              <p>
                Connect endpoints. Compile forensic programs. Investigate and
                verify evidence.
              </p>
            </div>
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
            ].map(([v, k]) => (
              <section className="panel metric" key={String(k)}>
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
              "Agent state",
              "Last seen",
              "Current investigation",
              "Trust",
              "Source",
            ]}
            rows={d.endpoints.map((e) => [
              <button
                key={e.id}
                className="secondary"
                onClick={() => setSelected(e)}
              >
                {str(e.hostname)}
              </button>,
              str(e.target_os),
              str(e.target_arch),
              str(e.status),
              date(e.last_seen),
              d.jobs
                .filter(
                  (j) =>
                    j.endpoint_id === e.id &&
                    ["QUEUED", "DISPATCHED", "RUNNING"].includes(str(j.status)),
                )
                .map((j) => program(d.hunts.find((h) => h.id === j.hunt_id)!))
                .join(" · ") || "None",
              e.simulation
                ? "Fixture identity"
                : e.status === "REVOKED"
                  ? "Revoked"
                  : "Enrolled identity",
              provenance(e),
            ])}
          />
          {(enroll ||
            (typeof window !== "undefined" &&
              new URLSearchParams(window.location.search).has("connect"))) && (
            <Enrollment
              endpoints={d.endpoints}
              close={() => {
                setEnroll(false);
                history.replaceState(null, "", "/endpoints");
              }}
              refresh={refresh}
            />
          )}{" "}
          {selected && (
            <EndpointDetail
              endpoint={selected}
              d={d}
              close={() => setSelected(null)}
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
              hunt={d.hunts.find(
                (h) =>
                  h.id ===
                  (selected?.id ??
                    new URLSearchParams(window.location.search).get("id")),
              )!}
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
  close,
  refresh,
}: {
  endpoints: Row[];
  close: () => void;
  refresh: () => Promise<void>;
}) {
  const [token, setToken] = useState<Row | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const enrollment = useQuery({
    queryKey: ["enrollment-status", token?.id],
    enabled: !!token,
    refetchInterval: 3000,
    queryFn: () => api<Row>(`domain/endpoints/enrollments/${token!.id}`),
  });
  const connected = enrollment.data?.state === "ONLINE";
  const command = `jocky-agent --state-dir .jocky-agent init\njocky-agent --state-dir .jocky-agent enroll --enrollment-server https://localhost:15052 --server https://localhost:15051 --ca control-plane-ca.pem --token-file enrollment.token --worker /usr/local/bin/jocky-worker\njocky-agent --state-dir .jocky-agent connect`;
  return (
    <Drawer title="Endpoint Enrollment" close={close}>
      <p>
        Generate a one-time token, save it to enrollment.token on the authorized
        endpoint, and provide the control plane CA certificate. Tokens expire in
        ten minutes.
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
        <button
          disabled={busy}
          onClick={async () => {
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
          }}
        >
          Create enrollment
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
            Windows. Use the CA from the control plane; never replace it with an
            untrusted certificate.
          </p>
          <pre className="compiler-output">{command}</pre>
          <button
            className="secondary"
            onClick={() => void navigator.clipboard.writeText(command)}
          >
            Copy command
          </button>
          <p>
            Local container support uses the existing agent-runtime Dockerfile.
            Mount your CA and enrollment.token in /endpoint, then run the same
            init, enroll, and connect commands inside that image. On the local
            Compose network use https://agent-control:50052 and
            https://agent-control:50051. Browser-driven host process launch is
            unavailable; the native agent supplies every heartbeat.
          </p>
          <small>
            Expires {date(token.expires_at)}. Endpoint inventory refreshes every
            five seconds.
          </small>
        </>
      )}
      {error && <p role="alert">{error}</p>}
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
            status: endpoint.status,
            last_seen: date(endpoint.last_seen),
            trust: endpoint.simulation
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
  close,
  refresh,
  created,
}: {
  d: Data;
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
      <div className="eyebrow">STEP {step} / 4</div>
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
                  {r.id} · {provenance(r)}
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
          {d.endpoints.map((e) => (
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
              <span>
                {str(e.hostname)} · {provenance(e)} · {str(e.status)}
              </span>
            </label>
          ))}
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
            <option value="memory">Memory · dedicated LLVM worker</option>
            <option value="native">Native · compiler executable</option>
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
          "Status",
          "Progress",
          "Observations",
          "Evidence",
          "Reason",
        ]}
        rows={jobs.map((j) => [
          str(d.endpoints.find((e) => e.id === j.endpoint_id)?.hostname),
          str(j.variant_id),
          str(obj(j.envelope).execution_mode ?? hunt.execution_mode),
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
  return (
    <>
      <section className="panel">
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
      </section>
      <Table
        headers={[
          "Driver/module",
          "Vendor",
          "Version",
          "Path",
          "Signed",
          "Hash",
          "Risk",
          "Source",
        ]}
        rows={drivers.map((o) => {
          const p = payload(o);
          return [
            <button
              key={o.id}
              className="secondary"
              onClick={() => setSelected(o)}
            >
              {str(p.name)}
            </button>,
            str(p.vendor),
            str(p.version),
            str(p.path),
            p.signed === true
              ? "Signed"
              : p.signed === false
                ? "Unsigned"
                : "Unknown",
            str(p.sha256),
            p.risk === "REVIEW"
              ? "REVIEW"
              : p.risk === "KNOWN RISK"
                ? "KNOWN RISK"
                : "UNKNOWN",
            provenance(o),
          ];
        })}
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
  const profile = obj(
    obj(obj(d.compilations.find((c) => c.id === comp)?.outputs).llvm).profile,
  );
  const timings = Object.entries(profile).filter(
    ([key, value]) => key.endsWith("_ms") && typeof value === "number",
  ) as [string, number][];
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
                await submit("benchmarks", {
                  compilation_id: comp,
                  repetitions: 3,
                });
                await refresh();
              } catch (e) {
                setError(e instanceof Error ? e.message : "Measurement failed");
              } finally {
                setBusy(false);
              }
            }}
          >
            {busy ? "Measuring…" : "Measure Compiler"}
          </button>
        </div>
      </section>
      {error && <p role="alert">{error}</p>}
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
        <h2>Investigations</h2>
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
function EvidenceView({ d }: { d: Data }) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return (
    <>
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
          a.id,
          str(
            d.endpoints.find(
              (e) =>
                e.id === d.jobs.find((j) => j.id === a.job_id)?.endpoint_id,
            )?.hostname,
          ),
          str(a.size_bytes),
          date(a.created_at),
          str(a.content_hash),
          provenance(a),
          <button
            key={a.id}
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                setResult({
                  artifact_id: a.id,
                  endpoint: d.endpoints.find(
                    (e) =>
                      e.id ===
                      d.jobs.find((j) => j.id === a.job_id)?.endpoint_id,
                  )?.hostname,
                  job: a.job_id,
                  created: date(a.created_at),
                  size_bytes: a.size_bytes,
                  manifest_present: d.manifests.some(
                    (m) => m.job_id === a.job_id,
                  ),
                  ...(await submit<Record<string, unknown>>(
                    `artifacts/${a.id}/verify`,
                  )),
                });
              } catch (e) {
                setError(
                  e instanceof Error ? e.message : "Verification failed",
                );
              } finally {
                setBusy(false);
              }
            }}
          >
            VERIFY INTEGRITY
          </button>,
        ])}
      />
      {error && <p role="alert">{error}</p>}
      {result && (
        <section className="panel">
          <h2>Integrity result</h2>
          <Fields
            data={{
              "Artifact ID": result.artifact_id,
              Endpoint: result.endpoint,
              Job: result.job,
              Created: result.created,
              Bytes: result.size_bytes,
              "Stored SHA-256": result.expected_hash,
              "Recomputed SHA-256": result.computed_hash,
              Integrity:
                result.available && result.expected_hash && result.computed_hash
                  ? result.integrity_valid
                    ? "VALID"
                    : "INVALID"
                  : "NOT VERIFIED / CONTENT UNAVAILABLE",
              "Manifest signature":
                result.signature_valid === undefined
                  ? result.manifest_present
                    ? "NOT CHECKED"
                    : "NOT PRESENT"
                  : result.signature_valid
                    ? "VALID"
                    : "INVALID",
            }}
          />
        </section>
      )}
      <Table
        headers={["Manifest", "Job", "Signature", "Action"]}
        rows={d.manifests.map((m) => [
          m.id,
          str(m.job_id),
          m.signature_verified ? "Verified at ingestion" : "Not verified",
          <button
            key={m.id}
            onClick={async () => {
              try {
                setResult(await submit(`manifests/${m.id}/verify`));
              } catch (e) {
                setError(
                  e instanceof Error
                    ? e.message
                    : "Manifest verification failed",
                );
              }
            }}
          >
            Verify manifest
          </button>,
        ])}
      />
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
  const [comp, setComp] = useState(
    d.compilations.filter((c) => c.status === "SUCCESS").at(-1)?.id ?? "",
  );
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [comparison, setComparison] = useState<Record<string, unknown> | null>(
    null,
  );
  const variants = d.variants.filter((v) => v.compilation_id === comp);
  return (
    <>
      <section className="panel action-heading">
        <div>
          <h2>Same forensic intent · distinct compiled variants</h2>
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
              await submit(`compilations/${comp}/variants`, { count: 3 });
              await refresh();
            } catch (e) {
              setError(e instanceof Error ? e.message : "Build failed");
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? "Building…" : "Generate 3 Variants"}
        </button>
      </section>
      {error && <p role="alert">{error}</p>}
      <Table
        headers={[
          "Variant",
          "Seed",
          "Target",
          "Execution",
          "Artifact SHA-256",
          "LLVM identity",
        ]}
        rows={variants.map((v, i) => [
          `Variant ${String.fromCharCode(65 + i)}`,
          str(v.seed),
          str(obj(v.manifest).target_triple),
          str(obj(v.manifest).execution_mode),
          str(v.content_hash),
          str(obj(v.manifest).llvm_ir_hash),
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
        <Fields
          data={{
            same_source: comparison.same_source,
            distinct_artifacts: comparison.distinct_artifacts,
            semantic_equivalence: comparison.semantic_equivalence,
          }}
        />
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
  const graph = query.data ?? { nodes: [], edges: [] };
  const label = (n: Record<string, unknown>) => {
    const observed = payload(
      d.observations.find((o) => o.id === n.observation_id) ?? { id: "" },
    );
    return str(
      n.name ??
        n.address ??
        n.hostname ??
        d.endpoints.find((e) => str(n.id) === e.id)?.hostname ??
        observed.name ??
        observed.path ??
        observed.remote_address ??
        (n.pid ? `PID ${n.pid}` : n.type),
    );
  };
  const nodes = graph.nodes.filter(
    (n) =>
      (!kind || n.type === kind) &&
      label(n).toLowerCase().includes(search.toLowerCase()),
  );
  const positions = new Map(
    nodes.map((n, i) => [
      str(n.id),
      { x: 105 + (i % 4) * 210, y: 75 + Math.floor(i / 4) * 120 },
    ]),
  );
  return (
    <section className="panel">
      <div className="timeline-filters">
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
      </div>
      <svg
        className="forensic-graph"
        viewBox={`0 0 950 ${Math.max(280, Math.ceil(nodes.length / 4) * 120 + 40)}`}
        aria-label="Forensic relationships"
      >
        {graph.edges.map((e, i) => {
          const a = positions.get(e.source),
            b = positions.get(e.target);
          return a && b ? (
            <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y}>
              <title>{e.relationship}</title>
            </line>
          ) : null;
        })}
        {nodes.map((n) => {
          const p = positions.get(str(n.id))!;
          return (
            <g
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
          <RelatedLinks />
        </Drawer>
      )}
    </section>
  );
}
