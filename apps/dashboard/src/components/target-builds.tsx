"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { object, shortHash } from "../lib/product-data";
type Row = Record<string, unknown> & { id: string };
function Hash({ value }: { value: unknown }) {
  return (
    <span className="hash-value">
      <code title={String(value)}>{shortHash(value)}</code>
      <button
        className="secondary"
        onClick={() => navigator.clipboard.writeText(String(value))}
      >
        Copy
      </button>
    </span>
  );
}
export function TargetBuilds({ compilation }: { compilation: string }) {
  const [targets, setTargets] = useState(["linux-x86_64", "windows-x86_64"]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const variants = useQuery({
    queryKey: ["target-builds", compilation],
    queryFn: () => api<Row[]>("domain/variants"),
  });
  const rows = (variants.data ?? []).filter(
    (v) =>
      v.compilation_id === compilation &&
      object(v.manifest).link_status === "ENVIRONMENT DEPENDENT",
  );
  return (
    <section className="panel">
      <h2>One JIR → Windows and Linux</h2>
      <p>
        Emit genuine target-specific LLVM objects from the same forensic
        program. Cross-target final linking and execution require the
        corresponding worker SDK and host; they are not tested by the host
        fixture gate.
      </p>
      <div className="forge-inputs">
        {["linux-x86_64", "linux-aarch64", "windows-x86_64"].map((target) => (
          <label key={target}>
            <input
              type="checkbox"
              checked={targets.includes(target)}
              onChange={(e) =>
                setTargets(
                  e.target.checked
                    ? [...targets, target]
                    : targets.filter((t) => t !== target),
                )
              }
            />
            {target}
          </label>
        ))}
      </div>
      <button
        disabled={!compilation || !targets.length || busy}
        onClick={async () => {
          setBusy(true);
          setError("");
          try {
            await api(`domain/compilations/${compilation}/target-builds`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ targets }),
            });
            await variants.refetch();
          } catch (e) {
            setError(e instanceof Error ? e.message : "Target build failed");
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "Compiling targets…" : "Build selected targets"}
      </button>
      {(error || variants.error) && (
        <p role="alert">{error || variants.error?.message}</p>
      )}
      {rows.length > 0 && (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                {[
                  "Target",
                  "JIR identity",
                  "LLVM identity",
                  "Object SHA-256",
                  "Bytes",
                  "Final link",
                ].map((t) => (
                  <th key={t}>{t}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((v) => {
                const m = object(v.manifest);
                return (
                  <tr key={v.id}>
                    <td>
                      <Link href={`/variants?compilation=${compilation}`}>
                        {String(m.target_triple)}
                      </Link>
                    </td>
                    <td>
                      <Hash value={m.jir_hash} />
                    </td>
                    <td>
                      <Hash value={m.llvm_ir_hash} />
                    </td>
                    <td>
                      <Hash value={v.content_hash} />
                    </td>
                    <td>{String(m.artifact_size_bytes)}</td>
                    <td>ENVIRONMENT DEPENDENT</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
