"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useControlEvents } from "../lib/use-control-events";

type Row = { id: string; [key: string]: unknown };
type Node = {
  id: string;
  type: string;
  name?: string;
  pid?: number;
  address?: string;
};
type Graph = {
  nodes: Node[];
  edges: { source: string; target: string; relationship: string }[];
};
const object = (value: unknown): Record<string, unknown> =>
  value && typeof value === "object" ? (value as Record<string, unknown>) : {};
const text = (value: unknown) =>
  value == null ? "Unavailable" : String(value);
export function DemoPresentation({ section = "home" }: { section?: string }) {
  const client = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [selected, setSelected] = useState<unknown>(null);
  const [filter, setFilter] = useState("");
  const mode = useQuery({
    queryKey: ["platform-status"],
    queryFn: () => api<{ mode: string }>("status"),
  });
  const user = useQuery({
    queryKey: ["operator"],
    queryFn: () => api<{ role: string }>("domain/auth/me"),
    retry: false,
  });
  const demo = mode.data?.mode === "DEMO";
  const feed = useControlEvents(demo && !!user.data && section === "live");
  const data = useQuery({
    queryKey: ["resources", "video"],
    enabled: demo && !!user.data,
    retry: false,
    queryFn: async () => {
      const cases = await api<Row[]>("domain/cases");
      const scenario = cases.find(
        (row) =>
          row.simulation === true && row.description === "JOCKY_VIDEO_V1_READY",
      );
      if (!scenario) return null;
      const [
        endpoints,
        hunts,
        variants,
        findings,
        timeline,
        artifacts,
        manifests,
        observations,
        graph,
        benchmarks,
      ] = await Promise.all([
        api<Row[]>("domain/endpoints"),
        api<Row[]>("domain/hunts"),
        api<Row[]>("domain/variants"),
        api<Row[]>(`domain/findings?case_id=${scenario.id}`),
        api<Row[]>(`domain/timeline?case_id=${scenario.id}`),
        api<Row[]>("domain/artifacts"),
        api<Row[]>("domain/manifests"),
        api<Row[]>(`domain/observations?case_id=${scenario.id}`),
        api<Graph>(`domain/graph?case_id=${scenario.id}`),
        api<Row[]>("domain/benchmarks"),
      ]);
      const hunt = hunts.find((row) => row.case_id === scenario.id);
      const jobs = hunt ? await api<Row[]>(`domain/hunts/${hunt.id}/jobs`) : [];
      return {
        scenario,
        hunt,
        jobs,
        findings,
        timeline,
        observations,
        graph,
        endpoints: endpoints.filter((row) =>
          jobs.some((job) => job.endpoint_id === row.id),
        ),
        variants: variants.filter(
          (row) => row.compilation_id === hunt?.compilation_id,
        ),
        artifacts: artifacts.filter((row) => row.case_id === scenario.id),
        manifests: manifests.filter((row) =>
          jobs.some((job) => row.job_id === job.id),
        ),
        benchmarks: benchmarks.filter(
          (row) => row.compilation_id === hunt?.compilation_id,
        ),
      };
    },
  });
  async function action(path: string, body?: unknown) {
    setBusy(true);
    setNotice("");
    try {
      const result = await api<unknown>(`domain/${path}`, {
        method: "POST",
        ...(body ? { body: JSON.stringify(body) } : {}),
      });
      setSelected(result);
      setNotice(
        path === "demo"
          ? "Scenario ready. Compiler outputs are real; endpoint observations are simulated."
          : "Backend operation completed. Inspect the result below.",
      );
      await client.invalidateQueries({ queryKey: ["resources"] });
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }
  if (mode.isPending)
    return <p role="status">Checking recording environment…</p>;
  if (mode.error)
    return <p role="alert">Environment unavailable: {mode.error.message}</p>;
  if (!demo)
    return section === "home" ? null : (
      <section className="panel">
        <h2>REAL environment</h2>
        <p>
          The video scenario runs in a separate DEMO stack. No simulated
          endpoints are substituted here.
        </p>
        <Link href="/">Open Command Center →</Link>
        <p>
          Start with <code>make demo-up</code>, then open
          http://localhost:13000.
        </p>
      </section>
    );
  const d = data.data;
  return (
    <div className="video-presentation">
      <div className="demo-banner">
        <span className="demo-label">DEMO / SIMULATED</span>
        <span>
          Real compiler. Simulated endpoint scenario. No endpoint code is
          executed by this replay.
        </span>
      </div>
      {!user.data ? (
        <section className="panel">
          <h2>Sign in to the demo workspace</h2>
          <p>
            Use the local administrator created by the demo startup command.
          </p>
          <Link className="button" href="/login">
            Operator sign in
          </Link>
        </section>
      ) : (
        <>
          {(section === "home" || section === "judge" || !d) && (
            <section className="panel video-hero">
              <div className="eyebrow">JOCKY / SIH IDEA SUBMISSION</div>
              <h2>
                One hunt. Every endpoint.
                <br />
                <span>Evidence you can explain.</span>
              </h2>
              <p>
                Follow source through LLVM, unique artifacts, endpoint outcomes
                and a verifiable evidence chain.
              </p>
              <button
                className="button"
                disabled={busy || user.data.role === "VIEWER"}
                onClick={() => void action("demo")}
              >
                {busy
                  ? "Preparing with the native compiler…"
                  : d
                    ? "Restore prepared scenario"
                    : "Prepare demo scenario"}
              </button>{" "}
              <Link
                className="button secondary"
                href={section === "judge" ? "/workbench" : "/judge"}
              >
                {section === "judge"
                  ? "Open Workbench"
                  : "Start guided walkthrough"}
              </Link>
            </section>
          )}
          {notice && <p role="status">{notice}</p>}
          {data.isFetching && <p role="status">Loading persisted scenario?</p>}
          {data.error && <p role="alert">{data.error.message}</p>}
          {d && (
            <>
              {(section === "home" ||
                section === "live" ||
                section === "judge") && (
                <div className="video-metrics">
                  {[
                    [d.endpoints.length, "simulated endpoints"],
                    [d.variants.length, "real compiler artifacts"],
                    [d.findings.length, "derived findings"],
                    [d.artifacts.length, "stored evidence objects"],
                  ].map(([count, label]) => (
                    <div className="panel" key={label}>
                      <strong>{count}</strong>
                      <span>{label}</span>
                    </div>
                  ))}
                </div>
              )}
              {(section === "endpoints" ||
                section === "live" ||
                section === "home") && (
                <>
                  <div className="panel-heading">
                    <h2>One source · independent outcomes</h2>
                    <span className="demo-label">{text(d.hunt?.status)}</span>
                  </div>
                  <div className="video-grid">
                    {d.endpoints.map((endpoint) => {
                      const job = d.jobs.find(
                        (row) => row.endpoint_id === endpoint.id,
                      );
                      return (
                        <button
                          className="panel video-card"
                          key={endpoint.id}
                          onClick={() => setSelected({ endpoint, job })}
                        >
                          <span className="eyebrow">
                            {text(endpoint.target_os)} / SIMULATED
                          </span>
                          <h3>{text(endpoint.hostname)}</h3>
                          <strong
                            className={
                              job?.status === "SUCCESS"
                                ? "positive"
                                : "warning-text"
                            }
                          >
                            {text(job?.status)}
                          </strong>
                          <p>{text(job?.reason)}</p>
                          <small>
                            Fixture inventory • not an enrolled live host
                          </small>
                        </button>
                      );
                    })}
                  </div>
                </>
              )}
              {section === "live" && (
                <section className="panel">
                  <h2>Committed backend event feed</h2>
                  <p>
                    {feed.status} This is a saved scenario, not live endpoint
                    execution.
                  </p>
                  <ol className="video-timeline">
                    {feed.events.slice(0, 12).map((event) => (
                      <li key={text(event.id)}>
                        <strong>{text(event.topic)}</strong>
                        <small>
                          Sequence {text(event.sequence)} ·{" "}
                          {text(event.created_at)}
                        </small>
                      </li>
                    ))}
                  </ol>
                </section>
              )}
              {section === "variants" && (
                <>
                  <p>
                    Actual host-compiled artifacts with fixed seeds. Windows
                    inventory is simulated; these are not claimed to be Windows
                    executables. Semantic equivalence is not asserted by hash
                    diversity.
                  </p>
                  <div className="video-grid">
                    {d.variants.map((variant, index) => (
                      <button
                        className="panel video-card"
                        key={variant.id}
                        onClick={() => setSelected(variant)}
                      >
                        <span className="eyebrow">
                          VARIANT {index + 1} / REAL BUILD
                        </span>
                        <h3>Seed {text(variant.seed)}</h3>
                        <p>{text(object(variant.manifest).target_triple)}</p>
                        <code className="hash">
                          {text(variant.content_hash)}
                        </code>
                        <small>SHA-256 of actual stored compiler bytes</small>
                      </button>
                    ))}
                  </div>
                </>
              )}
              {section === "findings" && (
                <div className="video-grid">
                  {d.findings.map((finding) => (
                    <button
                      className="panel video-card"
                      key={finding.id}
                      onClick={() =>
                        setSelected({
                          finding,
                          observations: d.observations.filter((row) =>
                            (finding.observation_ids as string[]).includes(
                              row.id,
                            ),
                          ),
                        })
                      }
                    >
                      <span className="demo-label">
                        {text(finding.severity)} / SIMULATED INPUT
                      </span>
                      <h3>{text(finding.title ?? finding.rule_key)}</h3>
                      <p>
                        Derived from stored process and network observations.
                        Click to inspect the source evidence.
                      </p>
                    </button>
                  ))}
                </div>
              )}
              {section === "graph" && (
                <ForensicGraph graph={d.graph} inspect={setSelected} />
              )}
              {section === "timeline" && (
                <section className="panel">
                  <label>
                    Filter collector{" "}
                    <input
                      value={filter}
                      onChange={(event) => setFilter(event.target.value)}
                      placeholder="processes, connections, drivers…"
                    />
                  </label>
                  <ol className="video-timeline">
                    {d.timeline
                      .filter((row) => text(row.collector).includes(filter))
                      .map((row) => (
                        <li key={row.id}>
                          <button
                            className="button secondary"
                            onClick={() => setSelected(row)}
                          >
                            {text(row.collector)}
                          </button>
                          <strong>
                            {text(row.type)} · {text(row.severity)}
                          </strong>
                          <small>
                            {text(row.timestamp)} / {text(row.time_basis)} time
                          </small>
                        </li>
                      ))}
                  </ol>
                </section>
              )}
              {section === "drivers" && (
                <>
                  <p>
                    Read-only driver inventory. Risk explanations are synthetic
                    training metadata, not vulnerability or exploit findings.
                  </p>
                  <div className="video-grid">
                    {d.observations
                      .filter((row) => row.collector === "drivers")
                      .map((row) => {
                        const driver = object(object(row.document).data);
                        return (
                          <button
                            className="panel video-card"
                            key={row.id}
                            onClick={() => setSelected(row)}
                          >
                            <span className="demo-label">
                              SIMULATED / {text(driver.risk)}
                            </span>
                            <h3>{text(driver.name)}</h3>
                            <p>{text(driver.risk_basis)}</p>
                            <small>
                              Signature:{" "}
                              {driver.signed === true
                                ? "signed fixture"
                                : "unsigned fixture"}
                            </small>
                          </button>
                        );
                      })}
                  </div>
                </>
              )}
              {section === "evidence" && (
                <div className="video-grid">
                  {d.artifacts.map((row) => (
                    <section className="panel" key={row.id}>
                      <span className="demo-label">
                        SIMULATED CONTENT / REAL HASH
                      </span>
                      <h3>Evidence object</h3>
                      <code className="hash">{text(row.content_hash)}</code>
                      <p>
                        {text(row.size_bytes)} bytes · {text(row.media_type)}
                      </p>
                      <button
                        disabled={busy}
                        onClick={() =>
                          void action(`artifacts/${row.id}/verify`)
                        }
                      >
                        Verify stored bytes
                      </button>{" "}
                      <a
                        className="text-link"
                        href={`/api/control/domain/artifacts/${row.id}/content`}
                      >
                        Download
                      </a>
                    </section>
                  ))}
                  {d.manifests.map((row) => (
                    <section className="panel" key={row.id}>
                      <h3>Signed evidence manifest</h3>
                      <p>
                        Ed25519 signature over simulated evidence and real build
                        provenance.
                      </p>
                      <button
                        disabled={busy}
                        onClick={() =>
                          void action(`manifests/${row.id}/verify`)
                        }
                      >
                        Verify manifest
                      </button>
                    </section>
                  ))}
                </div>
              )}
              {section === "performance" && (
                <section className="panel">
                  <h2>Measure the compiler fixture</h2>
                  <p>
                    Actual timings from the native compiler on this host.
                    Fixture execution is SIMULATED; these measurements are not
                    endpoint or fleet benchmarks.
                  </p>
                  <button
                    disabled={busy || user.data.role === "VIEWER"}
                    onClick={() =>
                      void action("benchmarks", {
                        compilation_id: d.hunt?.compilation_id,
                        repetitions: 3,
                      })
                    }
                  >
                    Run 3 measured samples
                  </button>
                  {d.benchmarks.map((row) => (
                    <details key={row.id}>
                      <summary>
                        {text(row.status)} · {text(row.created_at)}
                      </summary>
                      <pre className="control-json">
                        {JSON.stringify(row.measurements, null, 2)}
                      </pre>
                    </details>
                  ))}
                </section>
              )}
            </>
          )}
          {selected != null && (
            <section className="panel" aria-label="Selected evidence">
              <div className="panel-heading">
                <h2>Evidence & provenance</h2>
                <button
                  className="button secondary"
                  onClick={() => setSelected(null)}
                >
                  Close details
                </button>
              </div>
              <pre className="control-json">
                {JSON.stringify(selected, null, 2)}
              </pre>
            </section>
          )}
        </>
      )}
    </div>
  );
}

function ForensicGraph({
  graph,
  inspect,
}: {
  graph: Graph;
  inspect: (node: unknown) => void;
}) {
  const [kind, setKind] = useState("");
  const nodes = graph.nodes.filter((node) => !kind || node.type === kind);
  const locations = new Map(
    nodes.map((node, index) => [
      node.id,
      { x: 110 + (index % 5) * 170, y: 70 + Math.floor(index / 5) * 125 },
    ]),
  );
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Observation-derived relationships</h2>
        <select
          aria-label="Node type"
          value={kind}
          onChange={(event) => setKind(event.target.value)}
        >
          <option value="">All node types</option>
          {[...new Set(graph.nodes.map((node) => node.type))].map((type) => (
            <option key={type}>{type}</option>
          ))}
        </select>
      </div>
      <p>
        Select a node to inspect its provenance. {nodes.length} nodes; edges
        come from backend correlation.
      </p>
      <svg
        className="forensic-graph"
        viewBox={`0 0 950 ${Math.max(280, Math.ceil(nodes.length / 5) * 125 + 20)}`}
        role="img"
        aria-label="Forensic relationships from simulated observations"
      >
        {graph.edges.map((edge, index) => {
          const a = locations.get(edge.source),
            b = locations.get(edge.target);
          return a && b ? (
            <line key={index} x1={a.x} y1={a.y} x2={b.x} y2={b.y}>
              <title>{edge.relationship}</title>
            </line>
          ) : null;
        })}
        {nodes.map((node) => {
          const p = locations.get(node.id)!;
          return (
            <g
              key={node.id}
              transform={`translate(${p.x},${p.y})`}
              role="button"
              tabIndex={0}
              aria-label={`Inspect ${node.type}`}
              onClick={() => inspect(node)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  inspect(node);
                }
              }}
            >
              <rect x={-68} y={-27} width={136} height={58} rx={10} />
              <text textAnchor="middle" y={-3}>
                {node.type}
              </text>
              <text className="graph-detail" textAnchor="middle" y={16}>
                {(
                  node.address ??
                  node.name ??
                  String(node.pid ?? node.id.slice(0, 12))
                ).slice(0, 20)}
              </text>
            </g>
          );
        })}
      </svg>
    </section>
  );
}

export function DemoScreen({
  section,
  children,
}: {
  section: string;
  children: React.ReactNode;
}) {
  const mode = useQuery({
    queryKey: ["platform-status"],
    queryFn: () => api<{ mode: string }>("status"),
  });
  const presentation = [
    "home",
    "endpoints",
    "live",
    "variants",
    "findings",
    "graph",
    "timeline",
    "evidence",
    "performance",
  ].includes(section);
  return mode.data?.mode === "DEMO" && presentation ? (
    <DemoPresentation section={section} />
  ) : (
    children
  );
}
export function ModeIndicator() {
  const mode = useQuery({
    queryKey: ["platform-status"],
    queryFn: () => api<{ mode: string }>("status"),
  });
  return (
    <span className="demo-label">
      {mode.data
        ? mode.data.mode === "DEMO"
          ? "DEMO / SIMULATED"
          : "REAL"
        : "MODE UNAVAILABLE"}
    </span>
  );
}
