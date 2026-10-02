"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { CompatibilityRun, equivalentRuns } from "../lib/compatibility";
import { Icon, type IconName } from "./icons";

type Row = Record<string, unknown> & { id: string };
type LabData = Record<string, unknown> & {
  job_id?: string;
  variant_id?: string;
  endpoint_id?: string;
  endpoint_hostname?: string;
  endpoint_platform?: string;
  endpoint_architecture?: string;
  transport_mode?: string;
  program?: string;
  execution_status?: string;
  runtime_ms?: number | null;
  cpu_percent?: number | null;
  peak_memory_bytes?: number | null;
  collector_counts?: Record<string, number> | null;
};
type Candidate = LabData & {
  job_id: string;
  variant_id: string;
  endpoint_id: string;
  created_at: string;
};
type InspectToken = "variant" | "endpoint" | "environment";

const shown = (value: unknown) =>
  value == null || value === "" ? "UNAVAILABLE" : String(value);
const short = (value: unknown, length = 10) => {
  const valueShown = shown(value);
  return valueShown.length > length
    ? `${valueShown.slice(0, length)}…`
    : valueShown;
};
const duration = (value: unknown) =>
  typeof value === "number" ? `${value.toLocaleString()} ms` : "UNAVAILABLE";
const memory = (value: unknown) =>
  typeof value === "number"
    ? `${(value / 1048576).toFixed(1)} MB`
    : "UNAVAILABLE";
const alertLabel = (value: unknown) =>
  value === "NO"
    ? "NO ALERT OBSERVED"
    : value === "YES"
      ? "ALERT OBSERVED"
      : "NOT MEASURED";
const tone = (value: unknown) =>
  value === "PASS" || value === "SUCCESS" || value === "NO"
    ? "good"
    : value === "FAIL" || value === "FAILED"
      ? "danger"
      : value === "YES"
        ? "warning"
        : "muted";
const displayDate = (value: unknown) =>
  value ? new Date(String(value)).toLocaleString() : "UNAVAILABLE";

function Datum({ label, value }: { label: string; value: unknown }) {
  const displayValue = shown(value);
  return (
    <div className="compat-datum">
      <span>{label}</span>
      <strong title={displayValue}>{displayValue}</strong>
    </div>
  );
}

function Signal({ data, variantId }: { data: LabData; variantId: string }) {
  const axes = [
    ["execution", data.execution_status ?? "NOT_MEASURED"],
    ["semantics", data.correctness ?? "NOT_MEASURED"],
    ["security", data.alert_observed ?? "NOT_MEASURED"],
  ] as const;
  return (
    <div className="compat-signal" aria-label="Compatibility Signal">
      <div className="compat-signal-title">COMPATIBILITY SIGNAL</div>
      <div
        className="compat-orbit"
        key={`${variantId}-${axes.map((axis) => axis[1]).join("-")}`}
      >
        <svg viewBox="0 0 220 220" aria-hidden="true">
          {axes.map(([name, value], index) => (
            <circle
              key={name}
              className={`compat-arc arc-${index} ${tone(value)}`}
              cx="110"
              cy="110"
              r={86 - index * 17}
            />
          ))}
        </svg>
        <div className="compat-signal-center">
          <small>VARIANT</small>
          <strong>{short(variantId, 8)}</strong>
        </div>
      </div>
      <div className="compat-axis-list">
        <span>
          EXECUTION{" "}
          <strong className={tone(data.execution_status)}>
            {shown(data.execution_status)}
          </strong>
        </span>
        <span>
          SEMANTICS{" "}
          <strong className={tone(data.correctness)}>
            {shown(data.correctness ?? "NOT_MEASURED")}
          </strong>
        </span>
        <span>
          SECURITY OBSERVATION{" "}
          <strong className={tone(data.alert_observed)}>
            {alertLabel(data.alert_observed)}
          </strong>
        </span>
      </div>
    </div>
  );
}

function ProvenanceToken({
  kind,
  title,
  onInspect,
}: {
  kind: InspectToken;
  title: string;
  onInspect: (kind: InspectToken) => void;
}) {
  return (
    <button
      type="button"
      className="compat-token"
      draggable
      onClick={() => onInspect(kind)}
      onFocus={() => onInspect(kind)}
      onDragStart={(event) => {
        event.dataTransfer.setData("application/x-compat-token", kind);
        event.dataTransfer.effectAllowed = "copy";
      }}
    >
      <span>{kind.toUpperCase()}</span>
      <strong>{title}</strong>
    </button>
  );
}

function Inspection({ kind, data }: { kind: InspectToken; data: LabData }) {
  const rows =
    kind === "variant"
      ? [
          ["Artifact", short(data.artifact_sha256, 18)],
          ["JIR", short(data.jir_sha256, 18)],
          ["Seed", data.variant_seed],
        ]
      : kind === "endpoint"
        ? [
            ["Hostname", data.endpoint_hostname],
            [
              "Platform",
              `${shown(data.endpoint_platform)} · ${shown(data.endpoint_architecture)}`,
            ],
            ["Transport", data.transport_mode],
          ]
        : [
            ["Product", data.security_product_label ?? "NOT MEASURED"],
            [
              "Version / policy",
              data.security_product_version ?? data.environment,
            ],
            ["Fingerprint", data.environment_fingerprint ?? "NOT MEASURED"],
          ];
  return (
    <div className="compat-inspection" role="status">
      <span>{kind.toUpperCase()} PROVENANCE</span>
      {rows.map(([label, value]) => (
        <Datum key={String(label)} label={String(label)} value={value} />
      ))}
    </div>
  );
}

export function CompatibilityView() {
  const queryClient = useQueryClient();
  const [activeJobId, setActiveJobId] = useState("");
  const [analyzedJobId, setAnalyzedJobId] = useState("");
  const [selectedRunId, setSelectedRunId] = useState("");
  const [inspect, setInspect] = useState<InspectToken>("variant");
  const [observationOpen, setObservationOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const runs = useQuery({
    queryKey: ["compatibility-runs"],
    queryFn: () => api<CompatibilityRun[]>("domain/compatibility-runs"),
  });
  const candidates = useQuery({
    queryKey: ["compatibility-candidates"],
    queryFn: () => api<Candidate[]>("domain/compatibility-runs/candidates"),
  });
  const user = useQuery({
    queryKey: ["auth-me"],
    queryFn: () => api<Row>("domain/auth/me"),
  });
  const preview = useQuery({
    queryKey: ["compatibility-job-preview", analyzedJobId],
    enabled: !!analyzedJobId,
    queryFn: () =>
      api<LabData>(
        `domain/compatibility-runs/job-preview?job_id=${encodeURIComponent(analyzedJobId)}`,
      ),
  });

  const newestRun = [...(runs.data ?? [])].sort((a, b) =>
    b.created_at.localeCompare(a.created_at),
  )[0];
  const selectedRun = selectedRunId
    ? runs.data?.find((run) => run.id === selectedRunId)
    : activeJobId
      ? undefined
      : newestRun;
  const data: LabData | undefined = preview.data ?? selectedRun?.observations;
  const variantId = shown(preview.data?.variant_id ?? selectedRun?.variant_id);
  const activeCandidate = candidates.data?.find(
    (candidate) => candidate.job_id === activeJobId,
  );
  const comparison = selectedRun
    ? equivalentRuns(runs.data ?? [], selectedRun)
    : [];
  const canRecord =
    user.data?.role === "ADMIN" || user.data?.role === "ANALYST";

  function chooseJob(jobId: string) {
    setActiveJobId(jobId);
    setAnalyzedJobId("");
    setSelectedRunId("");
    setError("");
  }

  async function recordMeasurement(
    fields: {
      product?: string;
      version?: string;
      realtime?: string;
      alert?: string;
      note?: string;
    } = {},
  ) {
    if (!preview.data || !analyzedJobId) return;
    const measured = !!fields.product;
    setBusy(true);
    setError("");
    try {
      const created = await api<CompatibilityRun>("domain/compatibility-runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          variant_id: preview.data.variant_id,
          job_id: analyzedJobId,
          environment:
            fields.note ||
            (measured
              ? "Operator-recorded security environment"
              : "No security-product measurement attached"),
          security_product_label: fields.product || "NOT_MEASURED",
          security_product_version: fields.version || null,
          realtime_protection: fields.realtime || "UNKNOWN",
          correctness: "NOT_MEASURED",
          alert_observed: fields.alert || "NOT_OBSERVED",
          notes: fields.note || "",
        }),
      });
      await queryClient.invalidateQueries({ queryKey: ["compatibility-runs"] });
      setSelectedRunId(created.id);
      setActiveJobId("");
      setAnalyzedJobId("");
      setObservationOpen(false);
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to save measurement",
      );
    } finally {
      setBusy(false);
    }
  }

  function submitObservation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fields = new FormData(event.currentTarget);
    void recordMeasurement({
      product: String(fields.get("product") ?? "").trim(),
      version: String(fields.get("version") ?? "").trim(),
      realtime: String(fields.get("realtime") ?? "UNKNOWN"),
      alert: String(fields.get("alert") ?? "NOT_OBSERVED"),
      note: String(fields.get("note") ?? "").trim(),
    });
  }

  const chain = data
    ? ([
        ["BUILD", short(variantId, 8), "branch"],
        ["ENDPOINT", shown(data.endpoint_hostname), "monitor"],
        [
          "SECURITY ENVIRONMENT",
          shown(data.security_product_label ?? "NOT MEASURED"),
          "shield",
        ],
        ["EXECUTION", shown(data.execution_status), "activity"],
        [
          "RESULT",
          `${shown(data.correctness ?? "NOT_MEASURED")} · ${alertLabel(data.alert_observed)}`,
          "check",
        ],
      ] as [string, string, IconName][])
    : [];

  return (
    <>
      <div className="eyebrow">VALIDATE / COMPATIBILITY LAB</div>
      <div className="page-heading compat-heading">
        <div>
          <h1>Compatibility Lab</h1>
          <p>
            Measured execution compatibility under explicitly recorded security
            environments.
          </p>
          <small>ENVIRONMENT-SPECIFIC · NO UNIVERSAL BYPASS CLAIM</small>
        </div>
      </div>

      <section className="panel compat-bench-panel">
        <div className="compat-panel-head">
          <div>
            <div className="eyebrow">COMPATIBILITY BENCH</div>
            <h2>Completed execution → measured environment</h2>
            {data && (
              <div className="compat-automation-counts">
                <span>
                  <strong>12</strong> AUTO-DERIVED FIELDS
                </span>
                <span>
                  <strong>3</strong> OPERATOR INPUT GROUPS
                </span>
              </div>
            )}
          </div>
        </div>
        <aside
          className="compat-candidates"
          aria-label="Recent completed executions"
        >
          <div className="compat-list-title">RECENT COMPLETED EXECUTIONS</div>
          <div className="compat-candidate-strip">
            {(candidates.data ?? []).map((candidate) => (
              <button
                type="button"
                draggable
                key={candidate.job_id}
                className={activeJobId === candidate.job_id ? "active" : ""}
                onClick={() => chooseJob(candidate.job_id)}
                onDragStart={(event) => {
                  event.dataTransfer.setData(
                    "application/x-compat-job",
                    candidate.job_id,
                  );
                  event.dataTransfer.effectAllowed = "copy";
                }}
              >
                <strong>{shown(candidate.program)}</strong>
                <span>{shown(candidate.endpoint_hostname)}</span>
                <small>
                  Variant {short(candidate.variant_id, 8)} ·{" "}
                  {shown(candidate.execution_status)} ·{" "}
                  {duration(candidate.runtime_ms)}
                </small>
                {candidate.simulation === true && <em>SIMULATED</em>}
              </button>
            ))}
          </div>
          {candidates.isSuccess && !candidates.data.length && (
            <div className="compat-no-jobs">
              <p>No completed executions are available yet.</p>
              <Link className="button secondary" href="/investigations">
                Open Investigations
              </Link>
            </div>
          )}
        </aside>

        <div
          className={`compat-bench ${data ? "loaded" : ""}`}
          onDragOver={(event) => {
            if (
              [...event.dataTransfer.types].some((type) =>
                type.startsWith("application/x-compat"),
              )
            )
              event.preventDefault();
          }}
          onDrop={(event) => {
            event.preventDefault();
            const jobId = event.dataTransfer.getData(
              "application/x-compat-job",
            );
            const token = event.dataTransfer.getData(
              "application/x-compat-token",
            ) as InspectToken;
            if (jobId) chooseJob(jobId);
            if (["variant", "endpoint", "environment"].includes(token))
              setInspect(token);
          }}
        >
          {!data && !activeCandidate ? (
            <div className="compat-drop-zone">
              <Icon name="activity" width={28} height={28} />
              <strong>Drop a completed job on the bench</strong>
              <span>or select one from the execution list</span>
            </div>
          ) : !data && activeCandidate ? (
            <div className="compat-analysis-ready">
              <Icon name="workflow" width={30} height={30} />
              <span>READY TO AUTO-RESOLVE</span>
              <h3>{shown(activeCandidate.program)}</h3>
              <p>
                {shown(activeCandidate.endpoint_hostname)} · Variant{" "}
                {short(activeCandidate.variant_id, 8)}
              </p>
              <button
                type="button"
                onClick={() => setAnalyzedJobId(activeCandidate.job_id)}
              >
                Analyze Execution
              </button>
            </div>
          ) : data ? (
            <>
              {selectedRun?.simulation || data.simulation === true ? (
                <span className="compat-simulation">
                  DEMO/SIMULATED ·{" "}
                  {shown(
                    selectedRun?.simulation_label ?? data.simulation_label,
                  )}
                </span>
              ) : (
                <span className="compat-real">REAL EXECUTION</span>
              )}
              <ol className="compat-chain">
                {chain.map(([label, value, icon]) => (
                  <li key={label}>
                    <Icon name={icon} width={17} height={17} />
                    <span>{label}</span>
                    <strong>{value}</strong>
                  </li>
                ))}
              </ol>
              <div className="compat-main-bench">
                <div
                  className="compat-stage-details"
                  aria-label="Auto-derived execution details"
                >
                  <div>
                    <h3>Build</h3>
                    <Datum label="Variant" value={short(variantId, 12)} />
                    <Datum label="Seed" value={data.variant_seed} />
                    <Datum
                      label="Artifact SHA-256"
                      value={short(data.artifact_sha256, 18)}
                    />
                    <Datum
                      label="JIR SHA-256"
                      value={short(data.jir_sha256, 18)}
                    />
                    <Datum
                      label="LLVM identity"
                      value={short(data.llvm_ir_hash, 18)}
                    />
                    <Datum
                      label="Structure"
                      value={data.structural_fingerprint}
                    />
                  </div>
                  <div>
                    <h3>Endpoint</h3>
                    <Datum label="Host" value={data.endpoint_hostname} />
                    <Datum
                      label="OS"
                      value={`${shown(data.endpoint_platform)} ${shown(data.os_version)}`}
                    />
                    <Datum
                      label="Architecture"
                      value={data.endpoint_architecture}
                    />
                    <Datum label="Transport" value={data.transport_mode} />
                    <Datum
                      label="Provenance"
                      value={
                        data.simulation === true || selectedRun?.simulation
                          ? "SIMULATED"
                          : "REAL"
                      }
                    />
                  </div>
                  <div>
                    <h3>Execution</h3>
                    <Datum label="Status" value={data.execution_status} />
                    <Datum label="Runtime" value={duration(data.runtime_ms)} />
                    <Datum
                      label="Peak RSS"
                      value={memory(data.peak_memory_bytes)}
                    />
                    {data.collector_counts ? (
                      Object.entries(data.collector_counts).map(
                        ([name, count]) => (
                          <Datum key={name} label={name} value={count} />
                        ),
                      )
                    ) : (
                      <Datum label="Collectors" value="UNAVAILABLE" />
                    )}
                  </div>
                </div>
                <div className="compat-center-console">
                  <div
                    className="compat-tokens"
                    aria-label="Movable provenance tokens"
                  >
                    <ProvenanceToken
                      kind="variant"
                      title={short(variantId, 8)}
                      onInspect={setInspect}
                    />
                    <ProvenanceToken
                      kind="endpoint"
                      title={shown(data.endpoint_hostname)}
                      onInspect={setInspect}
                    />
                    <ProvenanceToken
                      kind="environment"
                      title={short(
                        data.environment_fingerprint ?? "NOT MEASURED",
                        12,
                      )}
                      onInspect={setInspect}
                    />
                  </div>
                  <Signal data={data} variantId={variantId} />
                  <Inspection kind={inspect} data={data} />
                  {preview.data && canRecord && (
                    <div className="compat-inline-observation">
                      <div>
                        <span>SECURITY ENVIRONMENT</span>
                        <strong>Not measured for this execution.</strong>
                      </div>
                      <button
                        type="button"
                        onClick={() => setObservationOpen(true)}
                      >
                        Add Security Observation
                      </button>
                    </div>
                  )}
                </div>
              </div>
              {data.alert_observed === "NO" && (
                <p className="compat-disclaimer">
                  Compatibility measurement: no alert observed in this tested
                  environment.
                </p>
              )}
            </>
          ) : null}
        </div>
      </section>

      {!runs.isLoading && !runs.data?.length && (
        <section className="panel compat-empty">
          <h2>No compatibility measurements yet</h2>
          <p>
            Select a completed JOCKY execution to create the first
            environment-specific compatibility measurement.
          </p>
        </section>
      )}

      {!!runs.data?.length && (
        <section className="panel compat-history">
          <div className="eyebrow">MEASUREMENT HISTORY</div>
          <h2>Recorded environment-specific results</h2>
          <div className="compat-history-list">
            <div className="compat-history-head" aria-hidden="true">
              <span>Variant</span>
              <span>Endpoint</span>
              <span>Environment</span>
              <span>Execution</span>
              <span>Correctness</span>
              <span>Alert</span>
              <span>Measured at</span>
              <span>Source</span>
            </div>
            {[...runs.data]
              .sort((a, b) => b.created_at.localeCompare(a.created_at))
              .map((run) => {
                const observation = run.observations;
                return (
                  <button
                    type="button"
                    key={run.id}
                    className={selectedRun?.id === run.id ? "active" : ""}
                    onClick={() => {
                      setSelectedRunId(run.id);
                      setActiveJobId("");
                      setAnalyzedJobId("");
                    }}
                  >
                    <strong>Variant {short(run.variant_id, 8)}</strong>
                    <span>{shown(observation.endpoint_hostname)}</span>
                    <span>
                      {shown(
                        observation.environment_fingerprint ?? "NOT MEASURED",
                      )}
                    </span>
                    <span className={tone(observation.execution_status)}>
                      {shown(observation.execution_status)}
                    </span>
                    <span>{shown(observation.correctness)}</span>
                    <span>{alertLabel(observation.alert_observed)}</span>
                    <time>
                      {displayDate(observation.measured_at ?? run.created_at)}
                    </time>
                    <em>{run.simulation ? "SIMULATED" : "REAL"}</em>
                  </button>
                );
              })}
          </div>
        </section>
      )}

      {comparison.length >= 2 && (
        <section className="panel compat-comparison">
          <div className="eyebrow">SAME ENVIRONMENT COMPARISON</div>
          <h2>{shown(selectedRun?.observations.environment_fingerprint)}</h2>
          <div className="table-scroll">
            <table className="compat-table">
              <thead>
                <tr>
                  <th>Measurement</th>
                  {comparison.map((run, index) => (
                    <th key={run.id}>{String.fromCharCode(65 + index)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(
                  [
                    ["Artifact", "artifact_sha256", short],
                    ["Structure", "structural_fingerprint", shown],
                    ["Execution", "execution_status", shown],
                    ["Correctness", "correctness", shown],
                    ["Alert", "alert_observed", alertLabel],
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
        </section>
      )}

      <section className="panel compat-meaning">
        <div className="eyebrow">WHAT THIS MEANS</div>
        <p>
          Compatibility Lab records whether a specific JOCKY build executed
          correctly and what the exact recorded security environment observed.
          Results apply only to that product, version, policy and environment.
        </p>
      </section>

      {observationOpen && (
        <div
          className="compat-dialog-backdrop"
          onMouseDown={(event) => {
            if (event.currentTarget === event.target) setObservationOpen(false);
          }}
        >
          <section
            className="compat-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="compat-observation-title"
          >
            <div className="compat-dialog-head">
              <div>
                <div className="eyebrow">OPERATOR INPUT</div>
                <h2 id="compat-observation-title">Security Observation</h2>
              </div>
              <button
                type="button"
                className="secondary"
                onClick={() => setObservationOpen(false)}
              >
                Close
              </button>
            </div>
            <form
              className="compat-observation-form"
              onSubmit={submitObservation}
            >
              <label>
                Security Product
                <input
                  name="product"
                  required
                  autoFocus
                  placeholder="Exact observed product"
                />
              </label>
              <label>
                Exact Product Version
                <input
                  name="version"
                  required
                  placeholder="Exact observed version"
                />
              </label>
              <label>
                Realtime Protection
                <select name="realtime" defaultValue="UNKNOWN">
                  <option>UNKNOWN</option>
                  <option>ENABLED</option>
                  <option>DISABLED</option>
                </select>
              </label>
              <label>
                Alert Observed
                <select name="alert" defaultValue="NOT_OBSERVED">
                  <option value="NOT_OBSERVED">NOT MEASURED</option>
                  <option value="NO">NO</option>
                  <option value="YES">YES</option>
                </select>
              </label>
              <label className="wide">
                Environment / Policy Note
                <textarea name="note" rows={3} />
              </label>
              {error && <p role="alert">{error}</p>}
              <div className="compat-dialog-actions">
                <button type="submit" disabled={busy}>
                  {busy ? "Saving…" : "Save Measurement"}
                </button>
                <button
                  type="button"
                  className="secondary"
                  disabled={busy}
                  onClick={() => void recordMeasurement()}
                >
                  Record as Not Measured
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
      {error && !observationOpen && <p role="alert">{error}</p>}
    </>
  );
}
