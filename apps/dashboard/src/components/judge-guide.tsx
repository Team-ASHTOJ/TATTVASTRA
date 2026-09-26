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
    "Start with the persisted lab workspace, then follow one JOCKY program across endpoints, analysis, and evidence.",
  ],
  [
    "/workbench",
    "Workbench",
    "Load an example or write a .jky program, then check and compile it with the native compiler.",
  ],
  [
    "/compiler",
    "Compile and inspect AST / JIR / LLVM",
    "Inspect a persisted compilation: source, tokens, AST, typed JIR, LLVM, and execution plan.",
  ],
  [
    "/variants",
    "Variants",
    "Compare compiler-generated variants and their durable build identity.",
  ],
  [
    "/endpoints",
    "Endpoints",
    "See how real agents enroll and how this workspace labels its deterministic lab endpoints.",
  ],
  [
    "/investigations",
    "Investigation",
    "The saved investigation is PARTIAL: two successes and one permission failure. Successful endpoint evidence is preserved.",
  ],
  [
    "/findings",
    "Finding",
    "Open the correlated finding. An unsigned process and external connection share a process identity and endpoint.",
  ],
  [
    "/graph",
    "Forensic Graph",
    "Select a graph node to inspect the same observation-derived relationships that support the finding.",
  ],
  [
    "/timeline",
    "Timeline",
    "Filter the normalized investigation story by endpoint, event type, or severity.",
  ],
  [
    "/drivers",
    "Driver Intelligence",
    "Review real inventory when collected and the separate, safe lab-risk metadata in this workspace.",
  ],
  [
    "/evidence",
    "Evidence Verify",
    "Recompute stored hashes and verify signed manifests. Lab evidence content remains labeled as simulated.",
  ],
  [
    "/performance",
    "Performance",
    "Run measured native compiler samples. Values unavailable from the backend stay unavailable.",
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
    if (pathname === "/judge") move(0);
    // `move` intentionally uses current router and transition state.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);
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
    <section className="judge-guide panel" aria-label="Guided workflow">
      <div className="eyebrow">
        GUIDED WORKFLOW · {current + 1} / {chapters.length} · GUIDE POSITION,
        NOT COMPLETION
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
          {busy ? "Restoring scenario…" : "Reset sandbox"}
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
