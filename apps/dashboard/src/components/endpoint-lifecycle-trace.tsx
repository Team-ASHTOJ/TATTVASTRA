"use client";

import { useEffect, useMemo, useState, type CSSProperties } from "react";

export type LifecycleKind = "local" | "windows-sandbox";
export type LifecycleMode = "start" | "stop";
type TraceStatus = "pending" | "active" | "complete" | "failed";

type LifecycleStep = {
  tag: string;
  title: string;
  detail: string;
};

const localStartSteps: LifecycleStep[] = [
  {
    tag: "RUN",
    title: "Launch Runtime",
    detail: "Starting bundled Tattvastra/JOCKY endpoint runtime",
  },
  {
    tag: "INIT",
    title: "Initialize Agent",
    detail: "Loading agent configuration and identity",
  },
  {
    tag: "LINK",
    title: "Establish Control Link",
    detail: "Connecting to the Tattvastra control plane",
  },
  {
    tag: "REG",
    title: "Register Endpoint",
    detail: "Registering endpoint identity and hostname",
  },
  {
    tag: "SYNC",
    title: "Sync Capabilities",
    detail: "Platform, architecture and agent/runtime capabilities",
  },
  {
    tag: "HB",
    title: "Start Heartbeat",
    detail: "Establishing endpoint liveness",
  },
  {
    tag: "READY",
    title: "Endpoint Online",
    detail: "Ready for investigation dispatch",
  },
];

// The local API exposes no intermediate shutdown states. Keep only the two
// events the frontend can actually observe: the request and confirmed STOPPED.
const localStopSteps: LifecycleStep[] = [
  {
    tag: "STOP",
    title: "Stop Requested",
    detail: "Request sent to the local endpoint controller",
  },
  {
    tag: "DONE",
    title: "Endpoint Stopped",
    detail: "Local endpoint state confirmed stopped",
  },
];

const sandboxStartSteps: LifecycleStep[] = [
  {
    tag: "SANDBOX",
    title: "Prepare Windows Sandbox",
    detail: "Preparing the simulated Windows demonstration endpoint",
  },
  {
    tag: "BOOT",
    title: "Start Simulated Agent",
    detail: "Starting the bounded sandbox presentation",
  },
  {
    tag: "REG",
    title: "Register Sandbox Endpoint",
    detail: "Persisting the simulated endpoint identity",
  },
  {
    tag: "SYNC",
    title: "Publish Capabilities",
    detail: "Publishing sandbox platform and collector capabilities",
  },
  {
    tag: "HB",
    title: "Start Heartbeat",
    detail: "Deriving simulated endpoint liveness",
  },
  {
    tag: "READY",
    title: "Sandbox Online",
    detail: "Cross-platform demonstration endpoint ready",
  },
];

function stepsFor(kind: LifecycleKind, mode: LifecycleMode) {
  if (kind === "windows-sandbox") return sandboxStartSteps;
  return mode === "start" ? localStartSteps : localStopSteps;
}

function completedForState(
  kind: LifecycleKind,
  mode: LifecycleMode,
  state: string,
  stepCount: number,
) {
  if (kind === "windows-sandbox") return state === "ONLINE" ? stepCount : 0;
  if (mode === "stop") return state === "STOPPED" ? stepCount : 0;
  if (state === "ONLINE") return stepCount;
  if (state === "STALE") return Math.max(0, stepCount - 1);
  if (state === "WAITING_FOR_HEARTBEAT") return 5;
  if (state === "ENROLLING") return 3;
  return 0;
}

function value(endpoint: Record<string, unknown> | undefined, key: string) {
  const result = endpoint?.[key];
  return result == null ? "" : String(result);
}

export function EndpointLifecycleTrace({
  kind = "local",
  mode,
  endpoint,
  state,
  error,
  operationPending = false,
  startedAt,
  collapsible = true,
  onActivate,
  onRetry,
}: {
  kind?: LifecycleKind;
  mode: LifecycleMode;
  endpoint?: Record<string, unknown>;
  state: string;
  error?: string;
  operationPending?: boolean;
  startedAt: number;
  collapsible?: boolean;
  onActivate?: () => void;
  onRetry?: () => void;
}) {
  const steps = stepsFor(kind, mode);
  const failed = Boolean(error) || state === "ERROR";
  const completed =
    operationPending || failed
      ? 0
      : completedForState(kind, mode, state, steps.length);
  const successful = completed === steps.length;
  const [expanded, setExpanded] = useState(!successful || operationPending);
  const [visibleCount, setVisibleCount] = useState(1);
  const activeIndex = Math.min(completed, steps.length - 1);
  const endpointName =
    value(endpoint, "hostname") ||
    value(endpoint, "name") ||
    (kind === "windows-sandbox" ? "Windows Sandbox" : "Local endpoint");
  const endpointMetadata = ["target_os", "target_arch", "agent_version"]
    .map((key) => value(endpoint, key))
    .filter(Boolean)
    .join(" / ");

  useEffect(() => {
    const interval = window.setInterval(() => {
      setVisibleCount((count) => {
        if (count >= steps.length) {
          window.clearInterval(interval);
          return count;
        }
        return count + 1;
      });
    }, 260);
    return () => window.clearInterval(interval);
  }, [kind, mode, startedAt, steps.length]);

  useEffect(() => {
    if (!successful || failed || operationPending) return;
    const timer = window.setTimeout(() => setExpanded(false), 900);
    return () => window.clearTimeout(timer);
  }, [failed, operationPending, successful]);

  const statuses = useMemo(
    () =>
      steps.map((_, index): TraceStatus => {
        if (index < completed) return "complete";
        if (index === activeIndex) return failed ? "failed" : "active";
        return "pending";
      }),
    [activeIndex, completed, failed, steps],
  );

  const statusLabel = failed
    ? "FAILED"
    : successful
      ? kind === "windows-sandbox" || mode === "start"
        ? "ONLINE"
        : "STOPPED"
      : state === "STALE"
        ? "STALE"
        : kind === "windows-sandbox"
          ? "PREPARING"
          : mode === "start"
            ? "STARTING"
            : "STOPPING";
  const completionLabel =
    kind === "windows-sandbox"
      ? "Sandbox ready"
      : mode === "start"
        ? "Bootstrap complete"
        : "Endpoint stopped";

  function toggleExpanded() {
    onActivate?.();
    if (collapsible && !operationPending) setExpanded((current) => !current);
  }

  return (
    <div
      className={`endpoint-lifecycle ${expanded ? "expanded" : "collapsed"} lifecycle-${kind}`}
      role="status"
      aria-live="polite"
    >
      <span className="lifecycle-corner lifecycle-corner-top" />
      <span className="lifecycle-corner lifecycle-corner-bottom" />
      <header className="lifecycle-header">
        <button
          type="button"
          className="lifecycle-summary"
          onClick={toggleExpanded}
          aria-expanded={expanded}
        >
          <span className="lifecycle-identity">
            <span className="lifecycle-kicker">
              {kind === "windows-sandbox"
                ? "WINDOWS SANDBOX"
                : mode === "start"
                  ? "ENDPOINT BOOTSTRAP"
                  : "ENDPOINT SHUTDOWN"}
            </span>
            <strong>{endpointName}</strong>
            {!expanded && (
              <small>
                {completionLabel}
                {endpointMetadata ? ` / ${endpointMetadata}` : ""}
              </small>
            )}
          </span>
          <span className="lifecycle-summary-end">
            {kind === "windows-sandbox" && (
              <span className="lifecycle-badge">SIMULATED</span>
            )}
            <span className={`lifecycle-state ${failed ? "failed" : ""}`}>
              {statusLabel}
            </span>
            {collapsible && (
              <span className="lifecycle-chevron" aria-hidden="true">
                {expanded ? "−" : "+"}
              </span>
            )}
          </span>
        </button>
      </header>

      {expanded && (
        <>
          <ol className="lifecycle-steps">
            {steps.map((step, index) => (
              <li
                key={step.tag}
                data-stage={step.tag.toLowerCase()}
                className={`lifecycle-step ${statuses[index]} ${index < visibleCount ? "visible" : ""}`}
                style={{ "--step-delay": `${index * 35}ms` } as CSSProperties}
              >
                <span className="lifecycle-dot" aria-hidden="true" />
                <span className="lifecycle-tag">{step.tag}</span>
                <span className="lifecycle-copy">
                  <strong>{step.title}</strong>
                  <small>{step.detail}</small>
                </span>
              </li>
            ))}
          </ol>

          {successful && (
            <div className="lifecycle-result success">
              <strong>
                {kind === "windows-sandbox"
                  ? "Sandbox lifecycle complete"
                  : mode === "start"
                    ? "Bootstrap complete"
                    : "Endpoint stopped"}
              </strong>
              {endpoint && (
                <small>
                  {endpointName}
                  {endpointMetadata ? ` / ${endpointMetadata}` : ""}
                </small>
              )}
            </div>
          )}

          {failed && (
            <div className="lifecycle-result failure" role="alert">
              <strong>FAILED</strong>
              <small>
                {error || "The endpoint operation did not complete."}
              </small>
              {onRetry && (
                <button className="secondary compact" onClick={onRetry}>
                  Retry
                </button>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
