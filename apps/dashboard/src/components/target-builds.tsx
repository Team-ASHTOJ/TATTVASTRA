"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { object, shortHash } from "../lib/product-data";
import { Icon } from "./icons";

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
    <section className="panel forge-module target-builder">
      <div className="module-heading">
        <Icon name="monitor" />
        <div>
          <div className="eyebrow">TARGET BUILDER</div>
          <h2>Cross-platform targets</h2>
          <p>
            Emit genuine target-specific LLVM objects from the same forensic
            program.
          </p>
        </div>
      </div>
      <div className="target-options">
        {(
          [
            ["linux-x86_64", "Linux x86_64", "64-bit Intel / AMD"],
            ["linux-aarch64", "Linux ARM64", "64-bit ARM"],
            ["windows-x86_64", "Windows x86_64", "64-bit Intel / AMD"],
          ] as const
        ).map(([target, name, architecture]) => (
          <label
            key={target}
            className={`target-card ${targets.includes(target) ? "selected" : ""}`}
          >
            <input
              type="checkbox"
              checked={targets.includes(target)}
              onChange={(event) =>
                setTargets(
                  event.target.checked
                    ? [...targets, target]
                    : targets.filter((item) => item !== target),
                )
              }
            />
            <span>
              <strong>{name}</strong>
              <small>{architecture}</small>
            </span>
          </label>
        ))}
      </div>
      <p className="module-note">
        Final linking and execution require the corresponding worker SDK and
        host; they are not tested by the host fixture gate.
      </p>
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
          } catch (failure) {
            setError(
              failure instanceof Error
                ? failure.message
                : "Target build failed",
            );
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "Compiling targetsâ€¦" : "Build selected targets"}
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
                ].map((title) => (
                  <th key={title}>{title}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((variant) => {
                const manifest = object(variant.manifest);
                return (
                  <tr key={variant.id}>
                    <td>
                      <Link href={`/variants?compilation=${compilation}`}>
                        {String(manifest.target_triple)}
                      </Link>
                    </td>
                    <td>
                      <Hash value={manifest.jir_hash} />
                    </td>
                    <td>
                      <Hash value={manifest.llvm_ir_hash} />
                    </td>
                    <td>
                      <Hash value={variant.content_hash} />
                    </td>
                    <td>{String(manifest.artifact_size_bytes)}</td>
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
