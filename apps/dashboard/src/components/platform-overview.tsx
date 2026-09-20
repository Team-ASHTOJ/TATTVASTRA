"use client";
import { useQuery } from "@tanstack/react-query";
import type { PlatformStatus } from "@jocky/contracts";
import { EmptyState, StatusBadge } from "@jocky/ui";
import Link from "next/link";
import { api } from "../lib/api";
import { Coverage } from "./coverage";

export function PlatformOverview({
  coverageOnly = false,
}: {
  coverageOnly?: boolean;
}) {
  const query = useQuery({
    queryKey: ["platform-status"],
    queryFn: () => api<PlatformStatus>("status"),
    refetchInterval: 30_000,
  });
  return (
    <>
      <div className="eyebrow">
        {coverageOnly
          ? "SYSTEM DESIGN / REQUIREMENT TRACEABILITY"
          : "OPERATIONS / PLATFORM OVERVIEW"}
      </div>
      <div className="page-heading">
        <div>
          <h1>{coverageOnly ? "Architecture & coverage" : "Command Center"}</h1>
          <p>From forensic intent to evidence you can verify.</p>
        </div>
        <StatusBadge tone="warning">FOUNDATION RELEASE</StatusBadge>
      </div>
      {query.isPending && (
        <div role="status" className="panel">
          Connecting to the control plane…
        </div>
      )}
      {query.isError && (
        <div role="alert" className="panel error-panel">
          <h2>Control plane unavailable</h2>
          <p>{query.error.message}</p>
          <button onClick={() => void query.refetch()}>Retry connection</button>
        </div>
      )}
      {query.data && (
        <>
          <div className="notice">
            <span className="status-dot" />
            <div>
              <strong>
                {query.data.mode === "DEMO"
                  ? "DEMO mode — backend fixtures are explicitly simulated"
                  : "REAL mode — persisted endpoint execution is available"}
              </strong>
              <p>
                Cases, endpoints, hunts, jobs, observations, findings,
                timelines, evidence, and reports are read from the control
                plane. Live updates appear in Live Investigation.
              </p>
            </div>
            <StatusBadge>API CONNECTED</StatusBadge>
          </div>
          {!coverageOnly && (
            <>
              <div className="split-grid">
                <section className="panel">
                  <div className="panel-heading">
                    <h2>Investigation activity</h2>
                    <StatusBadge tone="good">PERSISTED DATA</StatusBadge>
                  </div>
                  <EmptyState title="Open persisted investigations">
                    <p>
                      Review persisted cases, jobs, evidence, and live committed
                      events from the control-plane sections.
                    </p>
                    <Link href="/cases" className="text-link">
                      Open cases →
                    </Link>
                  </EmptyState>
                </section>
                <section className="panel">
                  <div className="panel-heading">
                    <h2>Engineering foundation</h2>
                    <StatusBadge tone="good">AVAILABLE</StatusBadge>
                  </div>
                  <ul className="foundation-list">
                    <li>
                      <span>01</span>
                      <div>
                        <strong>Versioned contracts</strong>
                        <p>
                          Source, JIR, variants, jobs, and evidence provenance.
                        </p>
                      </div>
                    </li>
                    <li>
                      <span>04</span>
                      <div>
                        <strong>Native compiler workbench</strong>
                        <p>
                          Validate source and inspect tokens, AST, typed JIR,
                          plans, LLVM IR, and deterministic fixture execution.
                        </p>
                        <Link href="/workbench" className="text-link">
                          Open Workbench →
                        </Link>
                      </div>
                    </li>
                    <li>
                      <span>02</span>
                      <div>
                        <strong>Integrity verification</strong>
                        <p>Recompute a submitted observation’s SHA-256 hash.</p>
                        <Link href="/evidence" className="text-link">
                          Open verifier →
                        </Link>
                      </div>
                    </li>
                    <li>
                      <span>03</span>
                      <div>
                        <strong>Requirement traceability</strong>
                        <p>
                          {query.data.capabilities.length} requirements with
                          explicit implementation status.
                        </p>
                      </div>
                    </li>
                  </ul>
                </section>
              </div>
            </>
          )}
          <div className="pipeline" aria-label="Planned compiler pipeline">
            {[
              ".jky source",
              "C++ frontend",
              "Typed JIR",
              "Build diversity",
              "LLVM",
              "Agent runtime",
              "Evidence",
            ].map((stage, index) => (
              <div key={stage}>
                <small>{String(index + 1).padStart(2, "0")}</small>
                <span>{stage}</span>
              </div>
            ))}
          </div>
          {coverageOnly && <Coverage items={query.data.capabilities} />}
        </>
      )}
    </>
  );
}
