"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";

type Evidence = { type: string; id: string; reason: string };
type Hypothesis = {
  rank: number;
  title: string;
  support: "LOW" | "MODERATE" | "HIGH";
  what_it_may_mean: string;
  likely_intent: string;
  success_assessment: { status: string; explanation: string };
  observed_weaknesses: string[];
  evidence: Evidence[];
  tattvastra_response: string[];
  recommended_actions: string[];
  uncertainty: string;
};
type Analysis = { overall_assessment: string; hypotheses: Hypothesis[] };
type Report = {
  id: string;
  hunt_id: string | null;
  created_at: string;
  analysis_status: "PENDING" | "READY" | "FAILED" | null;
  analysis_model: string | null;
  analysis_generated_at: string | null;
  analysis_error?: string | null;
  analysis_document: Analysis | null;
};

const safeFailureReasons = new Set([
  "Provider unavailable",
  "Authentication failed",
  "Rate limited",
  "Structured response invalid",
  "Report unavailable",
  "Analysis generation failed",
]);

function CompactList({ values }: { values: string[] }) {
  return values.length ? (
    <ul className="hypothesis-list">
      {values.map((value, index) => (
        <li key={`${index}-${value}`}>{value}</li>
      ))}
    </ul>
  ) : (
    <p className="muted">None established by this report.</p>
  );
}

export function HypothesisAnalysis() {
  const params = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const client = useQueryClient();
  const [retrying, setRetrying] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);
  const [reportUnavailable, setReportUnavailable] = useState(false);
  const reports = useQuery({
    queryKey: ["hypothesis-reports"],
    queryFn: () => api<Report[]>("domain/reports"),
    refetchInterval: (query) =>
      (query.state.data ?? []).some((row) => row.analysis_status === "PENDING")
        ? 4000
        : false,
  });
  const candidates = (reports.data ?? [])
    .filter((row) => row.hunt_id)
    .sort((a, b) => b.created_at.localeCompare(a.created_at));
  const requested = params.get("report");
  const current = candidates.find((row) => row.id === requested);
  const activeReportId = current?.id ?? null;
  const latestReportId = candidates[0]?.id ?? null;

  useEffect(() => {
    if (!reports.isSuccess || current || !latestReportId) return;
    const next = new URLSearchParams(params.toString());
    next.set("report", latestReportId);
    router.replace(`${pathname}?${next.toString()}`, { scroll: false });
  }, [reports.isSuccess, current, latestReportId, params, pathname, router]);

  function selectReport(id: string) {
    if (!candidates.some((row) => row.id === id)) return;
    setReportUnavailable(false);
    setRetryError(null);
    const next = new URLSearchParams(params.toString());
    next.set("report", id);
    router.replace(`${pathname}?${next.toString()}`, { scroll: false });
  }

  async function retry() {
    if (!activeReportId || !candidates.some((row) => row.id === activeReportId)) {
      await reports.refetch();
      return;
    }
    setRetrying(true);
    setRetryError(null);
    try {
      await api(`domain/reports/${activeReportId}/analysis/retry`, {
        method: "POST",
      });
      await client.invalidateQueries({ queryKey: ["hypothesis-reports"] });
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        setReportUnavailable(true);
        setRetryError("This investigation report is no longer available.");
        await reports.refetch();
      } else {
        setRetryError(error instanceof Error ? error.message : "Retry failed");
      }
    } finally {
      setRetrying(false);
    }
  }

  return (
    <section className="panel hypothesis-section">
      <div className="hypothesis-heading">
        <div>
          <span className="badge hypothesis-badge">AI ASSISTED</span>
          <h2>AI-Assisted Hypothesis Analysis</h2>
        </div>
        {current && (
          <label className="hypothesis-selector">
            Investigation report
            <select
              value={activeReportId ?? ""}
              onChange={(event) => selectReport(event.target.value)}
            >
              {candidates.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.hunt_id} · {new Date(row.created_at).toLocaleString()}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      <p>
        Generated from persisted investigation evidence. Hypotheses are
        analytical interpretations, not verified findings.
      </p>
      {reports.isPending && <p role="status">Loading hypothesis analysis…</p>}
      {reports.isError && <p role="alert">Analysis status unavailable.</p>}
      {reportUnavailable && (
        <p role="alert">This investigation report is no longer available.</p>
      )}
      {reports.isSuccess && requested && !current && !reportUnavailable && (
        <p role="status">This investigation report is no longer available.</p>
      )}
      {reports.isSuccess && !requested && latestReportId && (
        <p role="status">Selecting the latest investigation report…</p>
      )}
      {!reports.isPending && !reports.isError && candidates.length === 0 && (
        <p>No investigation report analysis is available yet.</p>
      )}
      {current && (
        <>
          <p className="hypothesis-meta">
            {current.analysis_status} ·{" "}
            {current.analysis_model ?? "Model unavailable"}
            {current.analysis_generated_at &&
              ` · ${new Date(current.analysis_generated_at).toLocaleString()}`}
          </p>
          {current.analysis_status === "PENDING" && (
            <p role="status">Generating hypothesis analysis…</p>
          )}
          {current.analysis_status === "FAILED" && (
            <div>
              <p role="status">
                Analysis unavailable. {safeFailureReasons.has(current.analysis_error ?? "")
                  ? current.analysis_error
                  : "Analysis generation failed"}
              </p>
              <button
                className="secondary"
                disabled={retrying}
                onClick={() => void retry()}
              >
                {retrying ? "Retrying…" : "Retry Analysis"}
              </button>
              {retryError && !reportUnavailable && <p role="alert">{retryError}</p>}
            </div>
          )}
          {current.analysis_status === "READY" && current.analysis_document && (
            <>
              <div className="hypothesis-assessment">
                <h3>Overall Assessment</h3>
                <p>{current.analysis_document.overall_assessment}</p>
              </div>
              <div className="hypothesis-cards">
                {current.analysis_document.hypotheses.map((hypothesis) => (
                  <article className="hypothesis-card" key={hypothesis.rank}>
                    <div className="hypothesis-card-head">
                      <span>
                        HYPOTHESIS {String(hypothesis.rank).padStart(2, "0")}
                      </span>
                      <span className="badge">
                        {hypothesis.support} SUPPORT
                      </span>
                    </div>
                    <h3>{hypothesis.title}</h3>
                    <div className="hypothesis-grid">
                      <div>
                        <h4>What this may mean</h4>
                        <p>{hypothesis.what_it_may_mean}</p>
                      </div>
                      <div>
                        <h4>Likely Intent</h4>
                        <p>{hypothesis.likely_intent}</p>
                      </div>
                      <div>
                        <h4>Success Assessment</h4>
                        <strong>
                          {hypothesis.success_assessment.status.replaceAll(
                            "_",
                            " ",
                          )}
                        </strong>
                        <p>{hypothesis.success_assessment.explanation}</p>
                      </div>
                      <div>
                        <h4>Observed Weaknesses</h4>
                        <CompactList values={hypothesis.observed_weaknesses} />
                      </div>
                      <div>
                        <h4>Evidence Basis</h4>
                        {hypothesis.evidence.length ? (
                          <ul className="hypothesis-list">
                            {hypothesis.evidence.map((item, index) => (
                              <li key={`${item.type}-${item.id}-${index}`}>
                                {item.reason}{" "}
                                <small>
                                  {item.type} · {item.id}
                                </small>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="muted">
                            No specific evidence reference established.
                          </p>
                        )}
                      </div>
                      <div>
                        <h4>Tattvastra Response</h4>
                        <CompactList values={hypothesis.tattvastra_response} />
                      </div>
                      <div>
                        <h4>Recommended Response</h4>
                        <CompactList values={hypothesis.recommended_actions} />
                      </div>
                      <div>
                        <h4>Uncertainty</h4>
                        <p>{hypothesis.uncertainty}</p>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </>
          )}
        </>
      )}
    </section>
  );
}
