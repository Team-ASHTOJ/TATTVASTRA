"use client";

import {
  useEffect,
  useState,
  useSyncExternalStore,
  useTransition,
} from "react";
import { usePathname, useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

const chapters = [
  [
    "/",
    "Command Center",
    "A persisted three-endpoint DEMO scenario. Real compilation and verification surround explicitly simulated observations.",
  ],
  [
    "/workbench",
    "Workbench",
    "Load the prepared .jky source and press Check. One typed source describes the investigation.",
  ],
  [
    "/compiler",
    "Compile and inspect AST / JIR / LLVM",
    "Load the prepared source here, then inspect AST, Typed JIR and LLVM IR. Each action invokes the native compiler; prepared native builds appear next.",
  ],
  [
    "/variants",
    "Variants",
    "Three stored host-built artifacts have real SHA-256 identities. Different hashes alone do not establish semantic equivalence.",
  ],
  [
    "/endpoints",
    "Endpoints",
    "WIN-01, WIN-02 and UBUNTU-01 are synthetic inventory. Their independent outcomes explain the partial-success story.",
  ],
  [
    "/live",
    "Live Investigation",
    "The saved hunt is PARTIAL: two successes and one permission failure. Persisted events preserve the successful evidence.",
  ],
  [
    "/findings",
    "Finding",
    "Open the correlated finding to inspect its source observations. An unsigned process and external connection share the same PID and endpoint.",
  ],
  [
    "/graph",
    "Forensic Graph",
    "Select a process node to inspect provenance. Relationships come from the same stored observations as the finding.",
  ],
  [
    "/timeline",
    "Timeline",
    "Filter by drivers to inspect the scenario sequence. Fixture source timestamps are fixed; ingestion times remain actual backend times.",
  ],
  [
    "/drivers",
    "Driver Intelligence",
    "Read-only synthetic driver inventory carries explicit risk explanations. This does not assess a live Windows host or exploit a driver.",
  ],
  [
    "/evidence",
    "Evidence Verify",
    "Verify stored bytes, then a signed manifest. SHA-256 and Ed25519 checks are real, while the evidence contents are simulated.",
  ],
  [
    "/performance",
    "Performance",
    "Run three measured compiler-fixture samples. These are actual local timings, not endpoint or fleet benchmarks.",
  ],
  [
    "/architecture",
    "Requirement Coverage",
    "Inspect implemented requirements and safe mappings. Deferred final-build acceptance remains visible.",
  ],
] as const;
const key = "jocky-judge-step";
function subscribe(callback: () => void) {
  window.addEventListener("jocky-judge-change", callback);
  return () => window.removeEventListener("jocky-judge-change", callback);
}
function snapshot() {
  const value = sessionStorage.getItem(key);
  const index = value === null ? -1 : Number(value);
  return Number.isInteger(index) && index >= 0 && index < chapters.length
    ? index
    : -1;
}

export function JudgeGuide() {
  const pathname = usePathname();
  const router = useRouter();
  const client = useQueryClient();
  const step = useSyncExternalStore(subscribe, snapshot, () => -1);
  const [busy, setBusy] = useState(false);
  const [navigating, startTransition] = useTransition();
  const [error, setError] = useState("");
  const mode = useQuery({
    queryKey: ["platform-status"],
    queryFn: () => api<{ mode: string }>("status"),
  });
  function move(index: number) {
    sessionStorage.setItem(key, String(index));
    window.dispatchEvent(new Event("jocky-judge-change"));
    startTransition(() => router.push((chapters[index] ?? chapters[0])[0]));
  }
  const screenStep = chapters.findIndex((chapter) => chapter[0] === pathname);
  useEffect(() => {
    if (step >= 0 && screenStep >= 0 && step !== screenStep && !navigating) {
      sessionStorage.setItem(key, String(screenStep));
      window.dispatchEvent(new Event("jocky-judge-change"));
    }
  }, [step, screenStep, navigating]);
  async function restart() {
    setBusy(true);
    setError("");
    try {
      await api("domain/demo", { method: "POST" });
      await client.invalidateQueries({ queryKey: ["resources"] });
      move(0);
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "Scenario preparation failed",
      );
    } finally {
      setBusy(false);
    }
  }
  if (
    mode.data?.mode !== "DEMO" ||
    (step < 0 && pathname !== "/judge") ||
    pathname === "/login"
  )
    return null;
  const current = Math.max(0, screenStep >= 0 && step >= 0 ? screenStep : step);
  const chapter = chapters[current] ?? chapters[0];
  return (
    <section className="judge-guide panel" aria-label="Judge walkthrough">
      <div className="eyebrow">
        JUDGE MODE · {current + 1} / {chapters.length} · GUIDE POSITION, NOT
        COMPLETION
      </div>
      <strong>{chapter[1]}</strong>
      <p>{chapter[2]}</p>
      <div className="judge-controls">
        <button
          disabled={busy || navigating || current === 0}
          onClick={() => move(current - 1)}
        >
          Back
        </button>
        {pathname !== chapter[0] && (
          <button disabled={busy || navigating} onClick={() => move(current)}>
            Open current screen
          </button>
        )}
        <button
          disabled={busy || navigating || current === chapters.length - 1}
          onClick={() => move(current + 1)}
        >
          Next
        </button>
        <button disabled={busy || navigating} onClick={() => void restart()}>
          {busy ? "Restoring scenario…" : "Restart Demo"}
        </button>
        <button
          disabled={busy || navigating}
          onClick={() => {
            sessionStorage.removeItem(key);
            window.dispatchEvent(new Event("jocky-judge-change"));
            router.push("/");
          }}
        >
          Exit guide
        </button>
      </div>
      {error && <p role="alert">{error}</p>}
      <small>
        Restart restores the persisted backend scenario; it does not claim a new
        endpoint run.
      </small>
    </section>
  );
}
