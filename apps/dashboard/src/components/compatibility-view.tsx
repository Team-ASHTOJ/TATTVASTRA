"use client";

import { FormEvent, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { CompatibilityRun, equivalentRuns } from "../lib/compatibility";

type Row = Record<string, unknown> & { id: string };
type Preview = {
  execution_status: string;
  runtime_ms: number | null;
  cpu_percent: number | null;
  peak_memory_bytes: number | null;
  collector_counts: Record<string, number> | null;
  endpoint_id: string;
  endpoint_hostname: string;
  measurement_source: string;
};
const shown = (value: unknown) =>
  value == null || value === "" ? "UNAVAILABLE" : String(value);
const hash = (value: unknown) =>
  typeof value === "string" && value.length > 12
    ? `${value.slice(0, 12)}…`
    : shown(value);
const duration = (value: unknown) =>
  typeof value === "number" ? `${value.toLocaleString()} ms` : "UNAVAILABLE";
const memory = (value: unknown) =>
  typeof value === "number"
    ? `${(value / 1048576).toFixed(1)} MB`
    : "UNAVAILABLE";
const tone = (value: unknown) =>
  value === "PASS" || value === "SUCCESS"
    ? "good"
    : value === "FAIL" || value === "FAILED"
      ? "danger"
      : value === "YES" || value === "ALERT OBSERVED"
        ? "warning"
        : value === "NOT MEASURED" || value === "NOT_MEASURED"
          ? "muted"
          : "info";

function Datum({
  label,
  value,
  status = false,
}: {
  label: string;
  value: unknown;
  status?: boolean;
}) {
  return (
    <div className="compat-datum">
      <span>{label}</span>
      <strong className={status ? `compat-status ${tone(value)}` : ""}>
        {shown(value)}
      </strong>
    </div>
  );
}

export function CompatibilityView() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState("");
  const [variantId, setVariantId] = useState("");
  const [endpointId, setEndpointId] = useState("");
  const [jobId, setJobId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const runs = useQuery({
    queryKey: ["compatibility-runs"],
    queryFn: () => api<CompatibilityRun[]>("domain/compatibility-runs"),
  });
  const variants = useQuery({
    queryKey: ["compatibility-variants"],
    queryFn: () => api<Row[]>("domain/variants"),
  });
  const endpoints = useQuery({
    queryKey: ["compatibility-endpoints"],
    queryFn: () => api<Row[]>("domain/endpoints"),
  });
  const hunts = useQuery({
    queryKey: ["compatibility-hunts"],
    queryFn: () => api<Row[]>("domain/hunts"),
  });
  const jobs = useQuery({
    queryKey: ["compatibility-jobs", hunts.data?.map((h) => h.id).join(",")],
    enabled: !!hunts.data,
    queryFn: async () =>
      (
        await Promise.all(
          (hunts.data ?? []).map((h) =>
            api<Row[]>(`domain/hunts/${h.id}/jobs`),
          ),
        )
      ).flat(),
  });
  const user = useQuery({
    queryKey: ["auth-me"],
    queryFn: () => api<Row>("domain/auth/me"),
  });
  const preview = useQuery({
    queryKey: ["compatibility-job-preview", jobId, variantId],
    enabled: !!jobId && !!variantId,
    queryFn: () =>
      api<Preview>(
        `domain/compatibility-runs/job-preview?job_id=${encodeURIComponent(jobId)}&variant_id=${encodeURIComponent(variantId)}`,
      ),
  });
  const selected =
    runs.data?.find((run) => run.id === selectedId) ?? runs.data?.at(-1);
  const o = selected?.observations ?? {};
  const comparison = selected ? equivalentRuns(runs.data ?? [], selected) : [];
  const canRecord =
    user.data?.role === "ADMIN" || user.data?.role === "ANALYST";

  async function record(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    const data = new FormData(event.currentTarget);
    const field = (key: string) => String(data.get(key) ?? "").trim();
    const optional = (key: string) => field(key) || null;
    const number = (key: string) => (field(key) ? Number(field(key)) : null);
    const counts: Record<string, number> = {};
    for (const key of ["processes", "connections", "drivers"])
      if (field(key)) counts[key] = Number(field(key));
    const payload: Record<string, unknown> = {
      variant_id: variantId,
      endpoint_id: endpointId || null,
      job_id: jobId || null,
      environment: field("environment"),
      os_name: optional("os_name"),
      os_version: optional("os_version"),
      architecture: optional("architecture"),
      security_product_label: field("security_product_label"),
      security_product_version: optional("security_product_version"),
      realtime_protection: field("realtime_protection"),
      correctness: field("correctness"),
      alert_observed: field("alert_observed"),
      notes: field("notes"),
      measured_at: optional("measured_at")
        ? new Date(field("measured_at")).toISOString()
        : null,
    };
    if (!jobId)
      Object.assign(payload, {
        measurement_source: "OPERATOR_RECORDED",
        execution_status: field("execution_status"),
        runtime_ms: number("runtime_ms"),
        cpu_percent: number("cpu_percent"),
        peak_memory_bytes: number("peak_memory_bytes"),
        collector_counts: Object.keys(counts).length ? counts : null,
      });
    try {
      const created = await api<CompatibilityRun>("domain/compatibility-runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      await queryClient.invalidateQueries({ queryKey: ["compatibility-runs"] });
      setSelectedId(created.id);
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to record measurement",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="eyebrow">VALIDATE / COMPATIBILITY LAB</div>
      <div className="page-heading">
        <div>
          <h1>Compatibility Lab</h1>
          <p>
            Measured execution compatibility under explicitly recorded security
            environments.
          </p>
          <small>
            Compatibility measurements are environment-specific. No universal
            bypass claim.
          </small>
        </div>
      </div>
      {runs.isError && (
        <p role="alert">
          Unable to load compatibility runs. Sign in or check the control plane.
        </p>
      )}
      {selected ? (
        <>
          <section
            className="panel compat-panel"
            aria-label="Security compatibility run"
          >
            <div className="compat-panel-head">
              <div>
                <div className="eyebrow">SECURITY COMPATIBILITY RUN</div>
                <h2>Recorded measurement</h2>
              </div>
              <label>
                Selected run{" "}
                <select
                  aria-label="Selected compatibility run"
                  value={selected.id}
                  onChange={(e) => setSelectedId(e.target.value)}
                >
                  {[...(runs.data ?? [])].reverse().map((run) => (
                    <option key={run.id} value={run.id}>
                      {new Date(run.created_at).toLocaleString()} ·{" "}
                      {run.id.slice(0, 8)}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {selected.simulation && (
              <span className="compat-simulation">
                DEMO/SIMULATED · {shown(selected.simulation_label)}
              </span>
            )}
            <div className="compat-grid">
              <div>
                <h3>Environment</h3>
                <p>
                  {[o.os_name, o.os_version, o.architecture]
                    .filter(Boolean)
                    .join(" · ") || shown(o.environment)}
                </p>
                <Datum label="Recorded environment" value={o.environment} />
                <Datum label="Endpoint platform" value={o.endpoint_platform} />
              </div>
              <div>
                <h3>Security Product</h3>
                <p>{shown(o.security_product_label)}</p>
                <Datum label="Version" value={o.security_product_version} />
                <Datum
                  label="Realtime Protection"
                  value={o.realtime_protection}
                />
              </div>
              <div>
                <h3>JOCKY Variant</h3>
                <p>{selected.variant_id.slice(0, 8)}</p>
                <Datum label="Seed" value={o.variant_seed} />
                <Datum
                  label="Artifact SHA-256"
                  value={hash(o.artifact_sha256)}
                />
                <Datum label="JIR SHA-256" value={hash(o.jir_sha256)} />
                <Datum label="Structure" value={o.structural_fingerprint} />
                <Datum label="LLVM identity" value={hash(o.llvm_ir_hash)} />
                <Datum label="Source SHA-256" value={hash(o.source_sha256)} />
                <Datum label="Target triple" value={o.target_triple} />
                <Datum label="Execution mode" value={o.execution_mode} />
              </div>
              <div>
                <h3>Execution</h3>
                <Datum label="Execution" value={o.execution_status} status />
                <Datum
                  label="Semantic Correctness"
                  value={o.correctness}
                  status
                />
                <Datum
                  label="Alert Observed"
                  value={
                    o.alert_observed === "NO"
                      ? "NO ALERT OBSERVED"
                      : o.alert_observed === "YES"
                        ? "ALERT OBSERVED"
                        : "NOT MEASURED"
                  }
                  status
                />
                {o.alert_observed === "NO" && (
                  <p className="compat-disclaimer">
                    Compatibility measurement: no alert observed in this tested
                    environment.
                  </p>
                )}
              </div>
              <div>
                <h3>Runtime measurements</h3>
                <Datum label="Execution Time" value={duration(o.runtime_ms)} />
                <Datum
                  label="CPU"
                  value={
                    typeof o.cpu_percent === "number"
                      ? `${o.cpu_percent}%`
                      : null
                  }
                />
                <Datum label="Peak RSS" value={memory(o.peak_memory_bytes)} />
              </div>
              <div>
                <h3>Collector Result</h3>
                {o.collector_counts &&
                Object.keys(o.collector_counts as object).length ? (
                  Object.entries(
                    o.collector_counts as Record<string, number>,
                  ).map(([name, count]) => (
                    <Datum key={name} label={name} value={count} />
                  ))
                ) : (
                  <p>UNAVAILABLE</p>
                )}
              </div>
            </div>
            <div className="compat-provenance">
              <h3>Provenance</h3>
              <Datum label="Measurement source" value={o.measurement_source} />
              <Datum
                label="Measured at"
                value={
                  o.measured_at
                    ? new Date(String(o.measured_at)).toLocaleString()
                    : null
                }
              />
              <Datum label="Endpoint" value={o.endpoint_hostname} />
              <Datum label="Job" value={o.job_id} />
              <Datum
                label="State"
                value={selected.simulation ? "DEMO/SIMULATED" : "REAL"}
              />
              <Datum
                label="Recorded by"
                value={o.recorded_by_username ?? selected.recorded_by}
              />
              <Datum label="Notes" value={o.notes} />
            </div>
          </section>
          <section className="panel compat-panel">
            <div className="eyebrow">VARIANT COMPARISON</div>
            <h2>Same build and recorded environment</h2>
            {comparison.length >= 2 ? (
              <div className="table-scroll">
                <table className="compat-table">
                  <thead>
                    <tr>
                      <th>Measurement</th>
                      {comparison.map((run, index) => (
                        <th key={run.id}>
                          Variant {String.fromCharCode(65 + index)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(
                      [
                        ["Artifact", "artifact_sha256", hash],
                        ["Structure", "structural_fingerprint", shown],
                        ["Correctness", "correctness", shown],
                        ["Executed", "execution_status", shown],
                        ["Alert", "alert_observed", shown],
                        ["Runtime", "runtime_ms", duration],
                      ] as const
                    ).map(([label, key, format]) => (
                      <tr key={key}>
                        <th>{label}</th>
                        {comparison.map((run) => (
                          <td key={run.id}>{format(run.observations[key])}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p>
                Comparable runs require distinct variants with the same
                compilation, JIR, OS, architecture, security product, version,
                and realtime state.
              </p>
            )}
          </section>
        </>
      ) : runs.isSuccess ? (
        <section className="panel compat-panel">
          <h2>No compatibility measurements recorded</h2>
          <p>
            Record a real, environment-specific measurement to populate this
            lab. No default security-product result is assumed.
          </p>
        </section>
      ) : runs.isLoading ? (
        <p>Loading recorded compatibility measurements…</p>
      ) : null}
      <section className="panel compat-panel">
        <div className="eyebrow">WHAT THIS MEANS</div>
        <p>
          Compatibility Lab records whether a JOCKY build executed correctly and
          what the tested security environment observed. Results apply only to
          the exact recorded product, version, policy and environment.
        </p>
      </section>
      {canRecord && (
        <section className="panel compat-panel">
          <div className="eyebrow">RECORD MEASUREMENT</div>
          <h2>Record Compatibility Measurement</h2>
          <form
            className="compat-form"
            onSubmit={(event) => void record(event)}
          >
            <label>
              Variant
              <select
                required
                aria-label="Compatibility variant"
                value={variantId}
                onChange={(e) => {
                  setVariantId(e.target.value);
                  setJobId("");
                }}
              >
                <option value="">Choose variant</option>
                {(variants.data ?? []).map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.id.slice(0, 8)}
                    {row.simulation ? " · DEMO/SIMULATED" : ""}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Endpoint (optional)
              <select
                aria-label="Compatibility endpoint"
                value={
                  jobId && preview.data ? preview.data.endpoint_id : endpointId
                }
                disabled={!!jobId}
                onChange={(e) => setEndpointId(e.target.value)}
              >
                <option value="">Not linked</option>
                {(endpoints.data ?? []).map((row) => (
                  <option key={row.id} value={row.id}>
                    {shown(row.hostname)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Job (optional)
              <select
                aria-label="Compatibility job"
                value={jobId}
                onChange={(e) => setJobId(e.target.value)}
              >
                <option value="">Operator recorded</option>
                {(jobs.data ?? [])
                  .filter(
                    (row) =>
                      row.variant_id === variantId &&
                      (!endpointId || row.endpoint_id === endpointId),
                  )
                  .map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.id.slice(0, 8)} · {shown(row.status)}
                    </option>
                  ))}
              </select>
            </label>
            <p className="compat-source">
              {jobId
                ? "JOB DERIVED — execution metrics are read-only"
                : "OPERATOR RECORDED — enter only observed measurements"}
            </p>
            <label>
              Environment description
              <input
                name="environment"
                required
                placeholder="Tested environment and policy"
              />
            </label>
            <label>
              OS
              <input
                name="os_name"
                placeholder="Exact OS name or leave unavailable"
              />
            </label>
            <label>
              OS version
              <input name="os_version" placeholder="Exact version" />
            </label>
            <label>
              Architecture
              <input name="architecture" placeholder="Architecture" />
            </label>
            <label>
              Security product
              <input
                name="security_product_label"
                required
                placeholder="Product name or NOT_MEASURED"
              />
            </label>
            <label>
              Exact product version
              <input
                name="security_product_version"
                placeholder="Leave blank if unavailable"
              />
            </label>
            <label>
              Realtime Protection
              <select name="realtime_protection" defaultValue="UNKNOWN">
                <option>UNKNOWN</option>
                <option>ENABLED</option>
                <option>DISABLED</option>
              </select>
            </label>
            <label>
              Execution
              {jobId ? (
                <input
                  readOnly
                  value={preview.data?.execution_status ?? "UNAVAILABLE"}
                  aria-label="Job-derived execution status"
                />
              ) : (
                <select name="execution_status" defaultValue="NOT_MEASURED">
                  <option>NOT_MEASURED</option>
                  <option>SUCCESS</option>
                  <option>FAILED</option>
                </select>
              )}
            </label>
            <label>
              Correctness
              <select name="correctness" defaultValue="NOT_MEASURED">
                <option>NOT_MEASURED</option>
                <option>PASS</option>
                <option>FAIL</option>
              </select>
            </label>
            <label>
              Alert observed
              <select name="alert_observed" defaultValue="NOT_OBSERVED">
                <option value="NOT_OBSERVED">NOT MEASURED</option>
                <option value="NO">NO</option>
                <option value="YES">YES</option>
              </select>
            </label>
            <label>
              Runtime (ms)
              <input
                name="runtime_ms"
                type="number"
                min="0"
                step="any"
                readOnly={!!jobId}
                value={jobId ? (preview.data?.runtime_ms ?? "") : undefined}
                placeholder={
                  jobId ? "UNAVAILABLE" : "Leave blank if unavailable"
                }
              />
            </label>
            <label>
              CPU (%)
              <input
                name="cpu_percent"
                type="number"
                min="0"
                max="100"
                step="any"
                readOnly={!!jobId}
                value={jobId ? (preview.data?.cpu_percent ?? "") : undefined}
                placeholder="UNAVAILABLE"
              />
            </label>
            <label>
              Peak RSS (bytes)
              <input
                name="peak_memory_bytes"
                type="number"
                min="0"
                readOnly={!!jobId}
                value={
                  jobId ? (preview.data?.peak_memory_bytes ?? "") : undefined
                }
                placeholder="UNAVAILABLE"
              />
            </label>
            {!jobId ? (
              <>
                <label>
                  Processes
                  <input
                    name="processes"
                    type="number"
                    min="0"
                    placeholder="Not measured"
                  />
                </label>
                <label>
                  Connections
                  <input
                    name="connections"
                    type="number"
                    min="0"
                    placeholder="Not measured"
                  />
                </label>
                <label>
                  Drivers
                  <input
                    name="drivers"
                    type="number"
                    min="0"
                    placeholder="Not measured"
                  />
                </label>
              </>
            ) : (
              <p>
                Collector counts:{" "}
                {preview.data?.collector_counts
                  ? JSON.stringify(preview.data.collector_counts)
                  : "UNAVAILABLE"}{" "}
                · JOB DERIVED
              </p>
            )}
            <label>
              Measured at
              <input name="measured_at" type="datetime-local" />
            </label>
            <label className="compat-notes">
              Notes
              <textarea name="notes" rows={3} />
            </label>
            {preview.isError && (
              <p role="alert">The selected job does not match this variant.</p>
            )}
            {error && <p role="alert">{error}</p>}
            <button type="submit" disabled={busy || (!!jobId && !preview.data)}>
              {busy ? "Recording…" : "Record Compatibility Measurement"}
            </button>
          </form>
        </section>
      )}
    </>
  );
}
