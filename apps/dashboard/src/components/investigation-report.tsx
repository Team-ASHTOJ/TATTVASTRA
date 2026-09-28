"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "../lib/api";

type Value = Record<string, unknown>;
type ReportResponse = {
  report: Value;
  artifact: Value;
  document: Value;
  download_url: string;
};

const object = (value: unknown): Value =>
  value && typeof value === "object" && !Array.isArray(value)
    ? (value as Value)
    : {};
const list = (value: unknown): Value[] =>
  Array.isArray(value) ? value.map(object) : [];
const strings = (value: unknown): string[] =>
  Array.isArray(value) ? value.map(String) : [];
const shown = (value: unknown) =>
  value == null || value === "" ? null : String(value);
const date = (value: unknown) =>
  value ? new Date(String(value)).toLocaleString() : null;
const words = (value: unknown) => String(value ?? "").replaceAll("_", " ");

function FieldList({ values }: { values: Value }) {
  const entries = Object.entries(values).filter(([, value]) => shown(value));
  if (!entries.length) return null;
  return (
    <dl className="report-fields">
      {entries.map(([label, value]) => (
        <div key={label}>
          <dt>{words(label)}</dt>
          <dd>
            {typeof value === "boolean"
              ? value
                ? "Yes"
                : "No"
              : String(value)}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function ReportTable({
  headers,
  rows,
}: {
  headers: string[];
  rows: React.ReactNode[][];
}) {
  if (!rows.length) return null;
  return (
    <div className="report-table">
      <table>
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {row.map((cell, cellIndex) => (
                <td key={cellIndex}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Section({
  title,
  children,
  className = "",
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`report-section ${className}`}>
      <h2>{title}</h2>
      {children}
    </section>
  );
}

export function InvestigationReport({ huntId }: { huntId: string }) {
  const report = useQuery({
    queryKey: ["investigation-report", huntId],
    queryFn: () => api<ReportResponse>(`domain/hunts/${huntId}/report`),
    retry: false,
  });
  if (report.isPending)
    return <p role="status">Loading investigation report…</p>;
  if (report.error)
    return (
      <section className="panel">
        <h1>Investigation report unavailable</h1>
        <p>{report.error.message}</p>
        <Link className="button" href={`/investigations?id=${huntId}`}>
          Return to investigation
        </Link>
      </section>
    );

  const root = report.data.document;
  const investigation = object(root.investigation);
  const summary = object(root.executive_summary);
  const metrics = object(summary.metrics);
  const intent = object(root.intent);
  const semantic = object(root.semantic_plan);
  const findings = list(root.findings);
  const endpoints = list(root.endpoint_results);
  const observed = list(root.observation_summary);
  const timeline = list(root.timeline);
  const compiler = object(root.compiler_provenance);
  const executions = list(compiler.executions);
  const integrity = object(root.evidence_integrity);
  const manifests = list(integrity.manifests);
  const artifacts = list(integrity.artifacts);
  const audit = object(integrity.audit_chain_verification);
  const source = object(root.source);
  const identity = object(root.report_identity);
  const limitations = strings(root.limitations);
  const simulation = Boolean(root.simulation);

  return (
    <article className="forensic-report">
      <header className="report-masthead">
        <div>
          <div className="eyebrow">JOCKY / DFIR REPORT</div>
          <h1>Forensic Investigation Report</h1>
          <p>
            {shown(investigation.case_title)} · Investigation {huntId}
          </p>
        </div>
        <div className="report-actions">
          <span className={simulation ? "badge severity" : "badge badge-good"}>
            {simulation ? "SANDBOX" : "REAL"}
          </span>
          <button
            className="secondary print-control"
            onClick={() => window.print()}
          >
            Print / Save PDF
          </button>
          <a
            className="button print-control"
            href={`/api/control/domain/artifacts/${String(report.data.artifact.id)}/content`}
          >
            Download canonical JSON
          </a>
        </div>
      </header>

      <Section title="Executive Summary" className="report-summary">
        <p className="report-lead">{shown(summary.text)}</p>
        <div className="report-metrics">
          {[
            ["Endpoints", metrics.endpoints],
            [
              "Successful jobs",
              `${metrics.successful_jobs ?? 0}/${metrics.jobs ?? 0}`,
            ],
            ["Observations", metrics.observations],
            ["Findings", metrics.findings],
            ["Evidence artifacts", metrics.evidence_artifacts],
            ["Verified manifests", metrics.verified_manifests],
          ].map(([label, value]) => (
            <div key={String(label)}>
              <strong>{String(value ?? 0)}</strong>
              <span>{String(label)}</span>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Findings" className="report-findings">
        {!findings.length && (
          <p className="zero-findings">
            No persisted findings were produced by this investigation. This does
            not establish the absence of suspicious activity.
          </p>
        )}
        {findings.map((finding) => (
          <article className="finding-card" key={String(finding.id)}>
            <div className="finding-heading">
              <span className="severity">{String(finding.severity)}</span>
              <h3>{String(finding.title)}</h3>
            </div>
            <FieldList
              values={{
                rule_key: finding.rule_key,
                affected_endpoints: strings(finding.affected_endpoints).join(
                  ", ",
                ),
                supporting_observations: finding.supporting_observation_count,
                created_at: date(finding.created_at),
              }}
            />
            {!!strings(finding.observation_ids).length && (
              <details>
                <summary>Supporting observations and linked evidence</summary>
                <ul className="hash-list">
                  {strings(finding.observation_ids).map((identifier) => (
                    <li key={identifier}>
                      <code>{identifier}</code>
                    </li>
                  ))}
                  {strings(finding.timestamps).map((timestamp) => (
                    <li key={timestamp}>Observed: {date(timestamp)}</li>
                  ))}
                  {strings(finding.observation_integrity_hashes).map((hash) => (
                    <li key={hash}>
                      Observation SHA-256: <code>{hash}</code>
                    </li>
                  ))}
                  {strings(finding.linked_artifact_hashes).map((hash) => (
                    <li key={hash}>
                      Evidence artifact SHA-256: <code>{hash}</code>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </article>
        ))}
      </Section>

      <Section title="Investigation Intent">
        <FieldList
          values={{
            program: intent.program,
            execution_mode: words(intent.execution_mode),
            enforcement: intent.enforcement,
            target_endpoints: strings(intent.target_endpoint_ids).length,
          }}
        />
        <ReportTable
          headers={[
            "Target endpoint",
            "Platform",
            "Architecture",
            "Endpoint ID",
          ]}
          rows={list(intent.endpoints).map((endpoint) => [
            String(endpoint.hostname),
            String(endpoint.platform),
            String(endpoint.architecture),
            <code key="endpoint">{String(endpoint.id)}</code>,
          ])}
        />
        {!!strings(intent.declared_capabilities).length && (
          <>
            <h3>Declared capabilities</h3>
            <ul className="capability-list">
              {strings(intent.declared_capabilities).map((capability) => (
                <li key={capability}>✓ {capability}</li>
              ))}
            </ul>
          </>
        )}
        <FieldList values={object(intent.variant)} />
        <FieldList values={object(intent.budget)} />
      </Section>

      <Section title="Semantic Execution">
        {semantic.available ? (
          <ol className="semantic-steps">
            {list(semantic.operations).map((operation, index) => (
              <li key={`${operation.operation}-${index}`}>
                <strong>{String(operation.description)}</strong>
                {shown(operation.collector) && (
                  <code>{String(operation.collector)}</code>
                )}
              </li>
            ))}
          </ol>
        ) : (
          <p>
            A structured semantic plan was unavailable. The exact executed
            source is included below.
          </p>
        )}
      </Section>

      <Section title="Endpoint Results">
        <ReportTable
          headers={[
            "Endpoint",
            "Platform",
            "Status",
            "Transport",
            "Execution",
            "Variant",
            "Worker / duration",
            "Observations",
            "Evidence",
          ]}
          rows={endpoints.map((endpoint) => [
            <>
              <strong>{String(endpoint.hostname)}</strong>
              <small>{String(endpoint.endpoint_id)}</small>
            </>,
            [endpoint.platform, endpoint.architecture]
              .filter(Boolean)
              .join(" / "),
            <span className="badge">{String(endpoint.status)}</span>,
            words(endpoint.transport),
            [words(endpoint.execution_mode), endpoint.execution_engine]
              .filter(Boolean)
              .join(" / "),
            shown(endpoint.variant_id) ? (
              <code>{String(endpoint.variant_id)}</code>
            ) : null,
            [
              shown(endpoint.worker_pid) ? `PID ${endpoint.worker_pid}` : null,
              typeof endpoint.duration_ms === "number"
                ? `${Number(endpoint.duration_ms).toFixed(2)} ms`
                : null,
            ]
              .filter(Boolean)
              .join(" · "),
            String(endpoint.observation_count ?? 0),
            String(endpoint.artifact_count ?? 0),
          ])}
        />
        {!!list(integrity.observation_integrity_hashes).length && (
          <details className="observation-hashes">
            <summary>
              Observation integrity hashes (
              {list(integrity.observation_integrity_hashes).length})
            </summary>
            <ul className="hash-list">
              {list(integrity.observation_integrity_hashes).map(
                (observation) => (
                  <li key={String(observation.observation_id)}>
                    <code>{String(observation.observation_id)}</code>
                    <code>{String(observation.integrity_hash)}</code>
                  </li>
                ),
              )}
            </ul>
          </details>
        )}
      </Section>

      <Section title="What JOCKY Observed">
        <ReportTable
          headers={["Endpoint", "Collector", "Count", "Representative records"]}
          rows={observed.map((group) => [
            String(group.hostname),
            String(group.collector),
            String(group.count),
            <details key={String(group.collector)}>
              <summary>Inspect samples</summary>
              {list(group.representative_records).map((record) => (
                <div
                  className="observation-sample"
                  key={String(record.observation_id)}
                >
                  <code>{String(record.observation_id)}</code>
                  <pre>{JSON.stringify(object(record.data), null, 2)}</pre>
                </div>
              ))}
            </details>,
          ])}
        />
        {!observed.length && (
          <p>No persisted observations belong to this investigation.</p>
        )}
      </Section>

      <Section title="Timeline">
        <ol className="report-timeline">
          {timeline.map((event, index) => (
            <li key={`${event.timestamp}-${index}`}>
              <time>{date(event.timestamp)}</time>
              <strong>{String(event.event)}</strong>
              <code>{String(event.resource_id)}</code>
            </li>
          ))}
        </ol>
      </Section>

      <Section title="Compiler Provenance">
        <FieldList values={{ compilation_id: compiler.compilation_id }} />
        {executions.map((execution) => (
          <article className="provenance-block" key={String(execution.job_id)}>
            <FieldList
              values={Object.fromEntries(
                Object.entries(execution).filter(([, value]) => shown(value)),
              )}
            />
          </article>
        ))}
      </Section>

      <Section title="Evidence Integrity & Chain of Custody">
        <div className="integrity-callout">
          <strong>
            Audit chain: {audit.integrity_valid ? "VERIFIED" : "NOT VERIFIED"}
          </strong>
          <span>
            Signature verification and hash integrity are reported separately.
          </span>
        </div>
        <ReportTable
          headers={[
            "Job",
            "Signature",
            "Signing endpoint",
            "Transport",
            "Provenance",
          ]}
          rows={manifests.map((manifest) => [
            <code key="job">{String(manifest.job_id)}</code>,
            String(manifest.signature_verification),
            shown(manifest.signing_endpoint_identity) ? (
              <code>{String(manifest.signing_endpoint_identity)}</code>
            ) : null,
            words(manifest.transport),
            manifest.simulation ? "SANDBOX" : "REAL",
          ])}
        />
        <ReportTable
          headers={["Artifact", "SHA-256", "Bytes", "Stored bytes"]}
          rows={artifacts.map((artifact) => [
            <code key="artifact">{String(artifact.id)}</code>,
            <code key="hash">{String(artifact.content_hash)}</code>,
            String(artifact.size_bytes),
            artifact.integrity_valid ? "VERIFIED" : "NOT VERIFIED",
          ])}
        />
      </Section>

      <Section title="Executed JOCKY Source" className="report-source">
        <FieldList
          values={{
            source_version: source.version,
            source_hash: source.source_hash,
          }}
        />
        <details open>
          <summary>Exact ScriptVersion source</summary>
          <pre className="compiler-output">{String(source.text ?? "")}</pre>
        </details>
      </Section>

      <Section title="Limitations">
        {limitations.length ? (
          <ul className="limitations-list">
            {limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        ) : (
          <p>
            No report limitations were derived from the persisted investigation
            data.
          </p>
        )}
      </Section>

      <Section title="Report Identity" className="report-identity">
        <FieldList
          values={{
            report_id: identity.report_id,
            investigation_id: identity.investigation_id,
            case_id: identity.case_id,
            generated_at: date(identity.generated_at),
            generated_by: identity.generated_by,
            report_artifact_hash: identity.report_artifact_hash,
            schema_version: identity.schema_version ?? root.schema_version,
          }}
        />
      </Section>
    </article>
  );
}
