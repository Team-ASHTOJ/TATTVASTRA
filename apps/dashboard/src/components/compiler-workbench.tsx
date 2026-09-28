"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { languageExamples } from "../lib/language-examples";
import { StatusBadge } from "@jocky/ui";
import { api } from "../lib/api";

type Stage = "check" | "tokens" | "ast" | "jir" | "llvm" | "plan";
type Compilation = {
  id: string;
  status: string;
  created_at?: string;
  outputs?: Record<string, unknown>;
  error?: string;
};
type Row = { id: string; [key: string]: unknown };

const examples = Object.fromEntries(
  languageExamples.map((example) => [example.name, example.source]),
);

const stages: { id: Stage; label: string; detail: string }[] = [
  { id: "check", label: "Lexer", detail: "Source validity" },
  { id: "tokens", label: "Tokens", detail: "Lexical stream" },
  { id: "ast", label: "Parser", detail: "Syntax tree" },
  { id: "jir", label: "Types / JIR", detail: "Typed capabilities" },
  { id: "llvm", label: "LLVM", detail: "Native lowering" },
  { id: "plan", label: "Ready", detail: "Execution plan" },
];

function asText(value: unknown) {
  return value == null
    ? "Not available"
    : typeof value === "string"
      ? value
      : JSON.stringify(value, null, 2);
}

export function CompilerWorkbench({
  explorer = false,
}: {
  explorer?: boolean;
}) {
  const router = useRouter();
  const client = useQueryClient();
  const [source, setSource] = useState("");
  const [active, setActive] = useState<string | null>(null);
  const [tab, setTab] = useState<Stage | "diagnostics">("diagnostics");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [selected, setSelected] = useState<Compilation | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const compilations = useQuery({
    queryKey: ["compilations"],
    queryFn: () => api<Compilation[]>("domain/compilations"),
  });
  const preferred =
    typeof window === "undefined"
      ? null
      : (new URLSearchParams(window.location.search).get("id") ??
        sessionStorage.getItem("jocky-compilation"));
  const history = [...(compilations.data ?? [])]
    .reverse()
    .sort((a, b) => Number(b.id === preferred) - Number(a.id === preferred));

  useEffect(() => {
    const transferred = sessionStorage.getItem("jocky-source-transfer");
    if (transferred) {
      queueMicrotask(() => setSource(transferred));
      sessionStorage.removeItem("jocky-source-transfer");
    }
  }, []);

  async function check() {
    if (!source.trim()) return;
    setActive("check");
    setError("");
    setMessage("");
    setTab("diagnostics");
    try {
      const output = await api<Record<string, unknown>>("compilations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          schema_version: "1.0.0",
          simulation: false,
          command: "check",
          source,
          target: { os: "linux", arch: "x86_64" },
          execution_mode: "native",
          variant_seed: "0000000000000000",
          profile: "balanced",
        }),
      });
      setResult(output);
      setMessage(
        output.valid === false
          ? "Validation found diagnostics."
          : "Source validated by the native JOCKY frontend.",
      );
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Check failed");
    } finally {
      setActive(null);
    }
  }
  async function compile() {
    if (!source.trim()) return;
    setActive("compile");
    setError("");
    setMessage("");
    try {
      const cases = await api<Row[]>("domain/cases");
      const scenario =
        cases.find(
          (row) => !row.simulation && row.title === "Operator Programs",
        ) ??
        (await api<Row>("domain/cases", {
          method: "POST",
          body: JSON.stringify({
            simulation: false,
            title: "Operator Programs",
            description: "Authorized operator programs",
          }),
        }));
      const script = await api<Row>("domain/scripts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          case_id: scenario.id,
          name: source.match(/hunt\s+"([^"]+)"/)?.[1] ?? "Forensic Program",
          source,
        }),
      });
      const output = await api<Compilation>(
        `domain/scripts/${script.id}/compile`,
        { method: "POST" },
      );
      setSelected(output);
      sessionStorage.setItem("jocky-compilation", output.id);
      setResult(output.outputs ?? {});
      setTab("diagnostics");
      if (output.status !== "SUCCESS")
        throw new Error(output.error ?? "Native compilation did not complete.");
      setMessage(`Compilation complete ✓ · ${output.id}`);
      await client.invalidateQueries({ queryKey: ["compilations"] });
    } catch (failure) {
      setError(
        failure instanceof Error ? failure.message : "Compilation failed",
      );
    } finally {
      setActive(null);
    }
  }
  async function output(stage: Stage) {
    const current = selected ?? (explorer ? history[0] : undefined);
    if (!current) return;
    setActive(stage);
    setError("");
    setTab(stage);
    try {
      const stageOutput = await api<Record<string, unknown>>(
        `domain/compilations/${current.id}/${stage}`,
      );
      const outputs = { ...current.outputs, [stage]: stageOutput };
      setSelected({ ...current, outputs });
      setResult(outputs);
    } catch (failure) {
      setError(
        failure instanceof Error ? failure.message : "Stage output unavailable",
      );
    } finally {
      setActive(null);
    }
  }
  async function variants() {
    if (!selected) return;
    setActive("variants");
    setError("");
    try {
      const built = await api<Row[]>(
        `domain/compilations/${selected.id}/variants`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ count: 3 }),
        },
      );
      setMessage(
        `${built.length} compiler-generated variants are ready to compare.`,
      );
      await client.invalidateQueries({ queryKey: ["resources"] });
      router.push("/variants");
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "Variant generation failed",
      );
    } finally {
      setActive(null);
    }
  }
  if (explorer)
    return (
      <Explorer
        compilations={history}
        selected={selected}
        onSelect={(item) => {
          setSelected(item);
          setResult(item.outputs ?? {});
          setTab("diagnostics");
        }}
        tab={tab}
        onTab={setTab}
        onOutput={output}
        result={result}
        active={active}
        error={error}
      />
    );
  return (
    <div className="workbench-shell">
      <section className="panel workbench-hero">
        <div>
          <div className="eyebrow">WRITE / COMPILE / RUN</div>
          <h2>Start with a JOCKY forensic program</h2>
          <p>
            Choose an example or write a .jky program. Nothing is compiled until
            you ask JOCKY to do it.
          </p>
        </div>
        <div className="workbench-actions">
          <button
            className="secondary"
            onClick={() => {
              setSource("");
              setSelected(null);
              setResult(null);
            }}
          >
            New Program
          </button>
          <Link className="button secondary" href="/language">
            Documentation
          </Link>
          <details>
            <summary className="button secondary">Load Example</summary>
            <div className="example-menu">
              {Object.entries(examples).map(([name, value]) => (
                <button
                  key={name}
                  onClick={() => {
                    setSource(value);
                    setSelected(null);
                    setResult(null);
                    setMessage("");
                  }}
                >
                  {name}
                </button>
              ))}
            </div>
          </details>
        </div>
      </section>
      <div className="compiler-grid">
        <section className="panel source-panel">
          <div className="panel-heading">
            <h2>Program.jky</h2>
            <StatusBadge tone={source ? "good" : "muted"}>
              {source ? `${source.length} BYTES` : "NEW PROGRAM"}
            </StatusBadge>
          </div>
          <textarea
            aria-label="JOCKY source"
            className="code-editor"
            spellCheck={false}
            value={source}
            placeholder={
              'hunt "endpoint-triage" {\n    targets { group "LAB" os windows | linux }\n    …\n}'
            }
            onChange={(event) => {
              setSource(event.target.value);
              setSelected(null);
              setResult(null);
            }}
          />
          <div className="workbench-actions">
            <button
              disabled={!source.trim() || active !== null}
              onClick={() => void check()}
            >
              {active === "check" ? "Checking…" : "CHECK"}
            </button>
            <button
              disabled={!source.trim() || active !== null}
              onClick={() => void compile()}
            >
              {active === "compile" ? "Compiling…" : "COMPILE"}
            </button>
            <button
              className="secondary"
              disabled={!selected || active !== null}
              onClick={() => void output("plan")}
            >
              PLAN
            </button>
            <button
              className="secondary"
              disabled={!selected || active !== null}
              onClick={() => void variants()}
            >
              BUILD VARIANTS
            </button>
            <Link
              className={`button ${selected ? "" : "secondary"}`}
              href="/investigations?new=1"
            >
              RUN INVESTIGATION
            </Link>
          </div>
        </section>
        <section className="panel output-panel">
          <div className="panel-heading">
            <div>
              <h2>Compilation lifecycle</h2>
              <small>
                {selected
                  ? `Persisted compilation ${selected.id}`
                  : "Check or compile a program to see compiler output."}
              </small>
            </div>
            <StatusBadge
              tone={
                error
                  ? "warning"
                  : selected?.status === "SUCCESS"
                    ? "good"
                    : "muted"
              }
            >
              {active ? "WORKING" : (selected?.status ?? "READY")}
            </StatusBadge>
          </div>
          <div className="build-pipeline">
            {stages.map((stage) => (
              <button
                key={stage.id}
                className={
                  tab === stage.id
                    ? "pipeline-stage active"
                    : selected
                      ? "pipeline-stage complete"
                      : "pipeline-stage"
                }
                disabled={!selected || active !== null}
                onClick={() => void output(stage.id)}
              >
                <strong>{stage.label}</strong>
                <small>{stage.detail}</small>
              </button>
            ))}
          </div>
          {message && (
            <p className="success-note" role="status">
              {message}
            </p>
          )}
          {error && (
            <p className="compiler-error" role="alert">
              {error}
            </p>
          )}
          <OutputTabs tab={tab} setTab={setTab} result={result} />
        </section>
      </div>
    </div>
  );
}

function OutputTabs({
  tab,
  setTab,
  result,
}: {
  tab: Stage | "diagnostics";
  setTab: (value: Stage | "diagnostics") => void;
  result: Record<string, unknown> | null;
}) {
  const labels: [Stage | "diagnostics", string][] = [
    ["diagnostics", "Diagnostics"],
    ["tokens", "Tokens"],
    ["ast", "AST"],
    ["jir", "Typed JIR"],
    ["llvm", "LLVM IR"],
    ["plan", "Execution Plan"],
  ];
  const nested = result?.outputs as Record<string, unknown> | undefined;
  const value = result?.[tab] ?? nested?.[tab] ?? result;
  return (
    <>
      <div className="output-tabs">
        {labels.map(([id, label]) => (
          <button
            key={id}
            className={tab === id ? "active" : "secondary"}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>
      <pre className="compiler-output" aria-label="Compiler output">
        {result
          ? asText(value)
          : "Compiler output will appear here after a real check or compilation."}
      </pre>
    </>
  );
}

function Explorer({
  compilations,
  selected,
  onSelect,
  tab,
  onTab,
  onOutput,
  result,
  active,
  error,
}: {
  compilations: Compilation[];
  selected: Compilation | null;
  onSelect: (item: Compilation) => void;
  tab: Stage | "diagnostics";
  onTab: (stage: Stage | "diagnostics") => void;
  onOutput: (stage: Stage) => Promise<void>;
  result: Record<string, unknown> | null;
  active: string | null;
  error: string;
}) {
  const current = selected ?? compilations[0];
  return (
    <div className="explorer-shell">
      <section className="panel explorer-selector">
        <div className="panel-heading">
          <div>
            <div className="eyebrow">RECENT / PERSISTED COMPILATIONS</div>
            <h2>Compilation selector</h2>
            <p>
              Choose a durable compilation record to inspect its actual outputs.
            </p>
          </div>
          <Link className="button secondary" href="/workbench">
            Open in Workbench
          </Link>
        </div>
        {current && (
          <div className="current-compilation">
            <StatusBadge
              tone={current.status === "SUCCESS" ? "good" : "warning"}
            >
              {current.status}
            </StatusBadge>
            <code title={current.id}>{current.id.slice(0, 12)}...</code>
            <time>
              {current.created_at
                ? new Date(current.created_at).toLocaleString()
                : "Timestamp unavailable"}
            </time>
          </div>
        )}
        <div className="compilation-list">
          {compilations.slice(0, 12).map((item) => (
            <button
              key={item.id}
              className={current?.id === item.id ? "active" : "secondary"}
              onClick={() => onSelect(item)}
            >
              <strong>
                <span aria-hidden="true" /> {item.status}
              </strong>
              <code title={item.id}>{item.id.slice(0, 12)}...</code>
              <small>
                {item.created_at
                  ? new Date(item.created_at).toLocaleString()
                  : "Timestamp unavailable"}
              </small>
            </button>
          ))}
        </div>
      </section>
      {current ? (
        <section className="panel explorer-detail">
          <div className="panel-heading">
            <div>
              <h2>Compiler Explorer</h2>
              <small>Compilation ID · {current.id}</small>
            </div>
            <StatusBadge
              tone={current.status === "SUCCESS" ? "good" : "warning"}
            >
              {current.status}
            </StatusBadge>
          </div>
          <div className="build-pipeline">
            {stages.map((stage) => (
              <button
                key={stage.id}
                className={
                  tab === stage.id
                    ? "pipeline-stage active"
                    : "pipeline-stage complete"
                }
                disabled={active !== null}
                onClick={() => void onOutput(stage.id)}
              >
                <strong>{stage.label}</strong>
                <small>{stage.detail}</small>
              </button>
            ))}
          </div>
          {error && <p className="compiler-error">{error}</p>}
          <OutputTabs
            tab={tab}
            setTab={onTab}
            result={result ?? current.outputs ?? null}
          />
        </section>
      ) : (
        <section className="panel">
          <p>
            No persisted compilations are available yet.{" "}
            <Link href="/workbench">Compile a program in the Workbench.</Link>
          </p>
        </section>
      )}
    </div>
  );
}
