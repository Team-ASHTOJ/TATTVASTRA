"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useControlEvents } from "../lib/use-control-events";
import type {
  CaseCreate,
  ScriptCreate,
  HuntCreate,
  ReportCreate,
} from "@jocky/contracts";

type RecordRow = {
  id: string;
  simulation: boolean;
  simulation_label?: string | null;
  [key: string]: unknown;
};
const collections: Record<string, string> = {
  cases: "cases",
  endpoints: "endpoints",
  jobs: "hunts",
  findings: "findings",
  timeline: "timeline",
  evidence: "artifacts",
  reports: "reports",
  variants: "variants",
  forge: "compilations",
  compatibility: "compatibility-runs",
  performance: "benchmarks",
  graph: "graph",
};
export const resourceSections = [...Object.keys(collections), "live"];
const scoped = new Set(["findings", "timeline", "graph"]);

export function ControlResources({ section }: { section: string }) {
  const [caseId, setCaseId] = useState("");
  const [selected, setSelected] = useState<RecordRow | null>(null);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const user = useQuery({
    queryKey: ["operator"],
    queryFn: () => api<{ role: string; username: string }>("domain/auth/me"),
    retry: false,
  });
  const cases = useQuery({
    queryKey: ["cases"],
    queryFn: () => api<RecordRow[]>("domain/cases"),
    enabled: !!user.data,
  });
  const effectiveCase = caseId || cases.data?.[0]?.id || "";
  const path = collections[section];
  const records = useQuery({
    queryKey: ["resources", section, effectiveCase],
    queryFn: () =>
      api<RecordRow[] | { nodes: unknown[]; edges: unknown[] }>(
        `domain/${path}${scoped.has(section) ? `?case_id=${effectiveCase}` : ""}`,
      ),
    enabled: !!user.data && !!path && (!scoped.has(section) || !!effectiveCase),
    retry: false,
  });
  const write = user.data?.role === "ADMIN" || user.data?.role === "ANALYST";
  const feed = useControlEvents(!!user.data);
  const childPaths = selected
    ? section === "endpoints" ? [`endpoints/${selected.id}/jobs`, `endpoints/${selected.id}/observations`]
    : section === "jobs" ? [`hunts/${selected.id}/jobs`]
    : section === "evidence" && selected.job_id ? [`manifests?job_id=${String(selected.job_id)}`]
    : [] : [];
  const children = useQuery({
    queryKey: ["children", section, selected?.id],
    queryFn: () => Promise.all(childPaths.map((path) => api<RecordRow[]>(`domain/${path}`))),
    enabled: !!user.data && childPaths.length > 0,
  });
  const current = Array.isArray(records.data) ? records.data.find((row) => row.id === selected?.id) : undefined;
  const inspected = current ?? selected;
  async function mutate(route: string, body?: unknown) {
    setBusy(true);
    setNotice("");
    try {
      const result = await api<RecordRow>(`domain/${route}`, {
        method: "POST",
        ...(body ? { body: JSON.stringify(body) } : {}),
      });
      if (result.id) setSelected(result);
      else if (selected) setSelected({ ...selected, result });
      setNotice("Saved by the control plane.");
      await Promise.all([records.refetch(), cases.refetch()]);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }
  if (user.isPending) return <p role="status">Checking operator session…</p>;
  if (!user.data)
    return (
      <section className="panel">
        <h2>Operator session required</h2>
        <p>{user.error?.message}</p>
        <Link href="/login" className="button">
          Sign in
        </Link>
        <p>
          These views read persisted control-plane records. No local fixture
          results are substituted.
        </p>
      </section>
    );
  if (section === "live") return <section className="panel"><h2>Live investigation events</h2><p role="status">{feed.status}</p><p>The latest 100 committed events are shown. Reconnects resume from the durable sequence cursor.</p><pre className="control-json">{JSON.stringify(feed.events, null, 2)}</pre></section>;
  const rows = Array.isArray(records.data) ? records.data : [];
  return (
    <>
      <div className="compiler-options">
        <span>
          {user.data.username} / {user.data.role}
        </span>
        <label>
          Case
          <select
            value={effectiveCase}
            onChange={(e) => {
              setCaseId(e.target.value);
              setSelected(null);
            }}
          >
            {!cases.data?.length && <option value="">No cases</option>}
            {cases.data?.map((item) => (
              <option key={item.id} value={item.id}>
                {String(item.title)}
                {item.simulation ? " [SIMULATED]" : ""}
              </option>
            ))}
          </select>
        </label>
        <button
          className="button secondary"
          onClick={() => void records.refetch()}
          disabled={records.isFetching}
        >
          Refresh
        </button>
      </div>
      {section === "cases" && write && (
        <form
          className="panel control-form"
          onSubmit={(event) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            const simulation = data.get("simulation") === "on";
            const body: CaseCreate = {
              title: String(data.get("title")),
              description: String(data.get("description")),
              simulation,
              simulation_label: simulation ? "DEMO" : null,
            };
            void mutate("cases", body);
          }}
        >
          <h2>Create case</h2>
          <label>
            Title
            <input name="title" required maxLength={200} />
          </label>
          <label>
            Description
            <textarea name="description" rows={2} />
          </label>
          <label>
            <input type="checkbox" name="simulation" /> Simulated case (requires
            backend DEMO mode)
          </label>
          <button className="button" disabled={busy}>
            Create case
          </button>
        </form>
      )}
      {section === "forge" && write && (
        <form
          className="panel control-form"
          onSubmit={async (event) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            const body: ScriptCreate = {
              case_id: effectiveCase,
              name: String(data.get("name")),
              source: String(data.get("source")),
            };
            setBusy(true);
            setNotice("");
            try {
              const script = await api<RecordRow>("domain/scripts", {
                method: "POST",
                body: JSON.stringify(body),
              });
              await mutate(`scripts/${script.id}/compile`);
            } catch (error) {
              setNotice(
                error instanceof Error ? error.message : "Compilation failed",
              );
            } finally {
              setBusy(false);
            }
          }}
        >
          <h2>Persist and compile a script</h2>
          <p>
            Native compiler outputs and failures are retained with the immutable
            source version.
          </p>
          <label>
            Script name
            <input name="name" required />
          </label>
          <label>
            JOCKY source
            <textarea name="source" rows={8} required spellCheck={false} />
          </label>
          <button className="button" disabled={busy || !effectiveCase}>
            {busy ? "Compiling…" : "Save and compile"}
          </button>
        </form>
      )}
      {section === "jobs" && write && (
        <form
          className="panel control-form"
          onSubmit={(event) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            const [firstEndpoint, ...otherEndpoints] = String(
              data.get("endpoints"),
            )
              .split(",")
              .map((v) => v.trim())
              .filter(Boolean);
            if (!firstEndpoint) {
              setNotice("Select at least one endpoint UUID.");
              return;
            }
            const body: HuntCreate = {
              case_id: effectiveCase,
              compilation_id: String(data.get("compilation")),
              endpoint_ids: [firstEndpoint, ...otherEndpoints],
              execution_mode:
                data.get("mode") === "native" ? "native" : "memory",
              diverse: true,
              retry_limit: 1,
              endpoint_modes: {},
              enforcement_mode: "MONITORED",
            };
            void mutate("hunts", body);
          }}
        >
          <h2>Create multi-endpoint hunt</h2>
          <p>
            Endpoints without compatible artifact execution support are marked
            INCOMPATIBLE, never shown as executed.
          </p>
          <label>
            Successful compilation UUID
            <input name="compilation" required />
          </label>
          <label>
            Endpoint UUIDs (comma-separated)
            <input name="endpoints" required />
          </label>
          <label>
            Execution mode
            <select name="mode">
              <option>memory</option>
              <option>native</option>
            </select>
          </label>
          <button className="button" disabled={busy || !effectiveCase}>
            Create hunt
          </button>
        </form>
      )}
      {section === "reports" && write && (
        <button
          className="button"
          disabled={busy || !effectiveCase}
          onClick={() => {
            const body: ReportCreate = {
              case_id: effectiveCase,
              format: "json",
            };
            void mutate("reports", body);
          }}
        >
          Generate case JSON report
        </button>
      )}
      {notice && <p role="status">{notice}</p>}
      {records.error && <p role="alert">{records.error.message}</p>}
      {records.isFetching && <p role="status">Reading persisted records…</p>}
      {section === "graph" && records.data && !Array.isArray(records.data) ? (
        <section className="panel">
          <h2>Evidence relationships</h2>
          <p>
            {records.data.nodes.length} nodes / {records.data.edges.length}{" "}
            edges from observations.
          </p>
          <pre className="control-json">
            {JSON.stringify(records.data, null, 2)}
          </pre>
        </section>
      ) : (
        <section className="panel resource-table">
          <table>
            <thead>
              <tr>
                <th>Record</th>
                <th>Status / type</th>
                <th>Provenance</th>
                <th>Inspect</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>
                    {String(row.title ?? row.hostname ?? row.name ?? row.id)}
                  </td>
                  <td>
                    {String(
                      row.status ?? row.type ?? row.severity ?? "Recorded",
                    )}
                  </td>
                  <td>
                    {row.simulation
                      ? `SIMULATED / ${row.simulation_label}`
                      : "REAL"}
                  </td>
                  <td>
                    <button
                      className="button secondary"
                      onClick={() => setSelected(row)}
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!rows.length && !records.isFetching && (
            <p>
              No persisted records{scoped.has(section) ? " for this case" : ""}.
              Create or ingest data through the control plane.
            </p>
          )}
        </section>
      )}
      {selected && (
        <section className="panel">
          <h2>Persisted record</h2>
          <div className="compiler-options">
            {section === "forge" && selected.status === "SUCCESS" && write && (
              <button
                className="button"
                disabled={busy}
                onClick={() =>
                  void mutate(`compilations/${selected.id}/variants`, {
                    count: 3,
                  })
                }
              >
                Generate 3 variants
              </button>
            )}
            {section === "jobs" && write && (
              <>
                <button
                  className="button"
                  disabled={busy || inspected?.status !== "CREATED"}
                  onClick={() => void mutate(`hunts/${selected.id}/start`)}
                >
                  Start hunt
                </button>
                <button
                  className="button secondary"
                  disabled={busy}
                  onClick={() => void mutate(`hunts/${selected.id}/cancel`)}
                >
                  Cancel hunt
                </button>
              </>
            )}
            {section === "evidence" && (
              <>
                <button
                  className="button"
                  disabled={busy}
                  onClick={() => void mutate(`artifacts/${selected.id}/verify`)}
                >
                  Recompute SHA-256
                </button>
                <a
                  className="button secondary"
                  href={`/api/control/domain/artifacts/${selected.id}/content`}
                >
                  Download bytes
                </a>
              </>
            )}
            {section === "reports" &&
              typeof selected.artifact_id === "string" && (
                <a
                  className="button"
                  href={`/api/control/domain/artifacts/${selected.artifact_id}/content`}
                >
                  Download JSON
                </a>
              )}
          </div>
          <pre className="control-json">
            {JSON.stringify(inspected, null, 2)}
          </pre>
          {children.error && <p role="alert">{children.error.message}</p>}
          {children.data?.map((rows, index) => <div key={childPaths[index]}><h3>{childPaths[index]?.split("/").at(-1)?.split("?")[0]}</h3>
            {section === "evidence" && rows.map((manifest) => <button key={manifest.id} className="button secondary" disabled={busy} onClick={() => void mutate(`manifests/${manifest.id}/verify`)}>Verify signed manifest</button>)}
            <pre className="control-json">{JSON.stringify(rows, null, 2)}</pre></div>)}
        </section>
      )}
    </>
  );
}
