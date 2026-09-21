"use client";

import { useState } from "react";
import { StatusBadge } from "@jocky/ui";
import { api } from "../lib/api";

type CompilerCommand =
  "check" | "tokens" | "ast" | "jir" | "plan" | "llvm" | "run";

const commands: { command: CompilerCommand; label: string }[] = [
  { command: "check", label: "Check" },
  { command: "tokens", label: "Tokens" },
  { command: "ast", label: "AST" },
  { command: "jir", label: "Typed JIR" },
  { command: "plan", label: "Plan" },
  { command: "llvm", label: "LLVM IR" },
  { command: "run", label: "Run fixture" },
];

const starterSource = `hunt "system-baseline" {
    targets {
        group "SIH-LAB"
        os windows | linux
    }
    runtime {
        backend llvm
        execution memory
        variant {
            enabled true
            seed auto
            profile balanced
        }
    }
    capabilities {
        system.read
    }
    budget {
        cpu <= 20%
        memory <= 256MB
        io <= 150MB
        duration <= 120s
    }
    collect system as sys
    timeline {
        source sys
    }
    export report {
        format json
        include evidence
    }
}`;

export function CompilerWorkbench({
  explorer = false,
}: {
  explorer?: boolean;
}) {
  const [source, setSource] = useState(starterSource);
  const [seed, setSeed] = useState("0000000000000000");
  const [active, setActive] = useState<
    CompilerCommand | "compile" | "load" | null
  >(null);
  const [prepared, setPrepared] = useState<{
    id: string;
    source: string;
  } | null>(null);
  const [completed, setCompleted] = useState<CompilerCommand[]>([]);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadScenario() {
    setActive("load");
    try {
      const cases =
        await api<{ id: string; description: string }[]>("domain/cases");
      const scenario = cases.find(
        (row) => row.description === "JOCKY_VIDEO_V1_READY",
      );
      if (!scenario)
        throw new Error("Prepare the demo scenario in Judge Mode first.");
      const scripts =
        await api<{ id: string; case_id: string }[]>("domain/scripts");
      const script = scripts.find((row) => row.case_id === scenario.id);
      if (!script) throw new Error("Prepared scenario source is unavailable.");
      const versions = await api<{ source: string; version: number }[]>(
        `domain/scripts/${script.id}/versions`,
      );
      const latest = versions.sort((a, b) => b.version - a.version)[0];
      if (!latest) throw new Error("No persisted source version.");
      setSource(latest.source);
      setPrepared({ id: script.id, source: latest.source });
      setCompleted([]);
      setResult(null);
      setError(null);
    } catch (failure) {
      setError(
        failure instanceof Error ? failure.message : "Source loading failed",
      );
    } finally {
      setActive(null);
    }
  }

  async function compilePrepared() {
    if (!prepared || source !== prepared.source) return;
    setActive("compile");
    setError(null);
    setResult(null);
    try {
      const output = await api<Record<string, unknown>>(
        `domain/scripts/${prepared.id}/compile`,
        { method: "POST" },
      );
      setResult(output);
      if (output.status !== "SUCCESS")
        setError(
          String(
            output.error ?? "Compilation failed; inspect the persisted result.",
          ),
        );
    } catch (failure) {
      setError(
        failure instanceof Error ? failure.message : "Compilation failed",
      );
    } finally {
      setActive(null);
    }
  }

  async function invoke(command: CompilerCommand) {
    setActive(command);
    setError(null);
    try {
      const output = await api<Record<string, unknown>>("compilations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          schema_version: "1.0.0",
          simulation: command === "run",
          ...(command === "run"
            ? { simulation_label: "DETERMINISTIC_COMPILER_FIXTURE" }
            : {}),
          command,
          source,
          target: { os: "linux", arch: "x86_64" },
          execution_mode: command === "run" ? "memory" : "native",
          variant_seed: seed,
          profile: "balanced",
        }),
      });
      setResult(output);
      setCompleted((previous) =>
        previous.includes(command) ? previous : [...previous, command],
      );
    } catch (caught) {
      setResult(null);
      setError(
        caught instanceof Error ? caught.message : "Compiler request failed",
      );
    } finally {
      setActive(null);
    }
  }

  return (
    <div className="compiler-grid">
      <section className="panel source-panel">
        <div className="panel-heading">
          <h2>JOCKY source</h2>
          <StatusBadge>{source.length.toLocaleString()} BYTES</StatusBadge>
        </div>
        <label className="sr-only" htmlFor="jocky-source">
          JOCKY source
        </label>
        <textarea
          id="jocky-source"
          className="code-editor"
          spellCheck={false}
          value={source}
          onChange={(event) => {
            setSource(event.target.value);
            setCompleted([]);
            setResult(null);
          }}
        />
        <div className="compiler-options">
          <button
            className="button secondary"
            disabled={active !== null}
            onClick={() => void loadScenario()}
          >
            Load prepared demo source
          </button>
          <label>
            Variant seed
            <input
              aria-label="Variant seed"
              value={seed}
              pattern="[0-9a-f]{16}"
              maxLength={16}
              onChange={(event) => setSeed(event.target.value.toLowerCase())}
            />
          </label>
          <span>Target: host · Profile: balanced</span>
        </div>
      </section>

      <section className="panel output-panel">
        <div className="panel-heading">
          <h2>{explorer ? "Compiler pipeline" : "Build output"}</h2>
          <StatusBadge
            tone={error ? "warning" : completed.length ? "good" : "muted"}
          >
            {active
              ? "RUNNING"
              : error
                ? "ERROR"
                : completed.length
                  ? "RESULT"
                  : "READY"}
          </StatusBadge>
        </div>
        <div className="compiler-actions" aria-label="Compiler stages">
          <button
            disabled={
              active !== null || !prepared || source !== prepared.source
            }
            title="Load the prepared source first. Edited source can be checked with the individual stages."
            onClick={() => void compilePrepared()}
          >
            Compile prepared source
          </button>
          {commands.map(({ command, label }, index) => (
            <button
              key={command}
              className={
                completed.includes(command) ? "stage-complete" : "secondary"
              }
              disabled={
                active !== null ||
                !source.trim() ||
                !/^[0-9a-f]{16}$/.test(seed)
              }
              onClick={() => void invoke(command)}
            >
              <small>{String(index + 1).padStart(2, "0")}</small>
              {label}
            </button>
          ))}
        </div>
        {error && (
          <div role="alert" className="compiler-error">
            <strong>Compiler unavailable</strong>
            <p>{error}</p>
          </div>
        )}
        {!result && !error && (
          <div className="compiler-empty">
            Select a stage to run the native JOCKY compiler. Results shown here
            come from jockyc; the dashboard does not invent compiler output.
          </div>
        )}
        {result && (
          <pre className="compiler-output" aria-label="Compiler output">
            {JSON.stringify(result, null, 2)}
          </pre>
        )}
      </section>
    </div>
  );
}
