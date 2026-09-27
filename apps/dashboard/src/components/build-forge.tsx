"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { object, shortHash } from "../lib/product-data";

type Row = Record<string, unknown> & { id: string };
const string = (v: unknown) => (v == null ? "Not measured" : String(v));
const milliseconds = (v: unknown) =>
  typeof v === "number" ? `${v.toFixed(2)} ms` : "Not measured";
function Hash({ value }: { value: unknown }) {
  return (
    <span className="hash-value">
      <code title={string(value)}>{shortHash(value)}</code>
      {typeof value === "string" && (
        <button
          className="secondary"
          aria-label="Copy hash"
          onClick={() => void navigator.clipboard.writeText(value)}
        >
          Copy
        </button>
      )}
    </span>
  );
}
export function BuildForge() {
  const client = useQueryClient();
  const [compilation, setCompilation] = useState(() =>
    typeof window === "undefined"
      ? ""
      : (new URLSearchParams(window.location.search).get("compilation") ?? ""),
  );
  const [count, setCount] = useState(3);
  const [seed, setSeed] = useState("");
  const [selected, setSelected] = useState(() =>
    typeof window === "undefined"
      ? ""
      : (new URLSearchParams(window.location.search).get("build") ?? ""),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [verification, setVerification] = useState<Record<
    string,
    unknown
  > | null>(null);
  const comp = useQuery({
    queryKey: ["forge-compilations"],
    queryFn: () => api<Row[]>("domain/compilations"),
  });
  const caps = useQuery({
    queryKey: ["forge-capabilities"],
    queryFn: () => api<Record<string, unknown>>("domain/build-capabilities"),
  });
  const runs = useQuery({
    queryKey: ["build-runs"],
    queryFn: () => api<Row[]>("domain/build-runs"),
    refetchInterval: 2000,
  });
  const run = useQuery({
    queryKey: ["build-run", selected],
    enabled: !!selected,
    queryFn: () => api<Row>(`domain/build-runs/${selected}`),
    refetchInterval: (q) =>
      ["QUEUED", "RUNNING"].includes(String(q.state.data?.status))
        ? 1000
        : false,
  });
  const chosen =
    compilation ||
    (typeof window !== "undefined"
      ? sessionStorage.getItem("jocky-compilation")
      : "") ||
    comp.data?.at(-1)?.id ||
    "";
  const current = run.data;
  const stages = (current?.stages ?? []) as Record<string, unknown>[];
  const manifest = object(current?.manifest);
  const variants = (manifest.variants ?? []) as Record<string, unknown>[];
  const results = object(current?.results);
  return (
    <>
      <div className="eyebrow">BUILD / CONTINUOUS DELIVERY</div>
      <div className="page-heading">
        <div>
          <h1>Build Forge</h1>
          <p>One forensic intent → multiple fixture-verified builds.</p>
        </div>
        <Link className="button secondary" href="/workbench">
          Open Workbench
        </Link>
      </div>
      <section className="panel">
        <h2>Build a delivery set</h2>
        <p>
          Validated source and typed JIR feed seeded LLVM lowering. Real object
          bytes must pass deterministic fixture and equivalence gates before
          signed provenance is published.
        </p>
        <div className="forge-inputs">
          <label>
            Compilation
            <select
              aria-label="Build compilation"
              value={chosen}
              onChange={(e) => setCompilation(e.target.value)}
            >
              <option value="">Choose a successful compilation</option>
              {[...(comp.data ?? [])]
                .reverse()
                .filter((c) => c.status === "SUCCESS")
                .map((c) => (
                  <option key={c.id} value={c.id}>
                    {new Date(String(c.created_at)).toLocaleString()} ·{" "}
                    {String(object(object(c.outputs).llvm).kind ?? "LLVM")} ·{" "}
                    {c.id.slice(0, 8)}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Variants
            <input
              aria-label="Variant count"
              type="number"
              min={1}
              max={8}
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
            />
          </label>
          <label>
            Target
            <select aria-label="Build target">
              <option value="host">
                Compiler host · actual triple recorded
              </option>
            </select>
          </label>
          <label>
            Execution
            <select aria-label="Build execution">
              <option value="memory">Memory · ORC worker object</option>
            </select>
          </label>
          <label>
            Base seed (optional)
            <input
              aria-label="Build seed"
              placeholder="New seed, or 16 hex digits to replay"
              value={seed}
              onChange={(e) => setSeed(e.target.value)}
            />
          </label>
        </div>
        <p className="muted">
          Native worker packaging and cross-target delivery are not gates in
          this sprint. Timings come from measured compiler stages; no endpoint
          execution occurs here.
        </p>
        <button
          disabled={
            busy ||
            !chosen ||
            !caps.data?.available ||
            count < 1 ||
            count > 8 ||
            (seed !== "" && !/^[0-9a-f]{16}$/.test(seed))
          }
          onClick={async () => {
            setBusy(true);
            setError("");
            setVerification(null);
            try {
              const r = await api<Row>("domain/build-runs", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  compilation_id: chosen,
                  count,
                  target: "host",
                  execution_mode: "memory",
                  ...(seed ? { seed } : {}),
                }),
              });
              setSelected(r.id);
              window.history.replaceState(
                window.history.state,
                "",
                `/forge?compilation=${chosen}&build=${r.id}`,
              );
              await client.invalidateQueries({ queryKey: ["build-runs"] });
            } catch (e) {
              setError(
                e instanceof Error ? e.message : "Build could not start",
              );
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? "Starting…" : `BUILD ${count} VARIANTS`}
        </button>
        {(error || comp.error || caps.error || runs.error || run.error) && (
          <p role="alert">
            {error ||
              comp.error?.message ||
              caps.error?.message ||
              runs.error?.message ||
              run.error?.message}
          </p>
        )}
      </section>
      {current && (
        <section className="panel" aria-label="Build detail">
          <div className="panel-heading">
            <h2>
              {current.status === "READY"
                ? "Build ready ✓"
                : `Build ${string(current.status)}`}
            </h2>
            <Link
              className="text-link"
              href={`/compiler?id=${current.compilation_id}`}
            >
              Compilation →
            </Link>
          </div>
          <p>
            Build {current.id} · Seed {string(current.seed)} ·{" "}
            {string(current.target)}
          </p>
          {Boolean(current.error) && (
            <p role="alert">{string(current.error)}</p>
          )}
          <div className="forge-pipeline">
            {stages.map((s) => (
              <div
                key={string(s.name)}
                className={`forge-stage ${s.status === "SUCCESS" ? "complete" : ""}`}
              >
                <strong>{string(s.name)}</strong>
                <span>{string(s.status)}</span>
                <small>{milliseconds(s.duration_ms)}</small>
              </div>
            ))}
          </div>
          {stages.map((s) => (
            <details key={string(s.name)} className="forge-stage-details">
              <summary>
                {string(s.name)} · {string(s.status)} · output details
              </summary>
              <p>
                {string(
                  object(s.details).note ??
                    object(s.details).error ??
                    "Persisted stage result",
                )}
              </p>
              <pre className="code-view">
                {JSON.stringify(s.details, null, 2)}
              </pre>
            </details>
          ))}
          <h3>
            Fixture equivalence ·{" "}
            {string(results.equivalence_status ?? "NOT_TESTED")}
          </h3>
          <p>
            <span className="badge">SIMULATED FIXTURE INPUT</span>{" "}
            {string(results.scope ?? caps.data?.fixture_scope)}
          </p>
          {Boolean(results.reference_hash) && (
            <p>
              Reference result <Hash value={results.reference_hash} />
            </p>
          )}
          {variants.length > 0 && (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    {[
                      "Variant",
                      "Seed",
                      "JIR",
                      "LLVM",
                      "Artifact",
                      "Structure",
                      "Bytes",
                      "AOT",
                      "Equivalence",
                    ].map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {variants.map((v, i) => (
                    <tr key={string(v.id)}>
                      <td>
                        <Link
                          href={`/variants?compilation=${current.compilation_id}&build=${current.id}`}
                        >
                          Variant {String.fromCharCode(65 + i)}
                        </Link>
                      </td>
                      <td>{string(v.variant_seed)}</td>
                      <td>
                        <Hash value={v.jir_hash} />
                      </td>
                      <td>
                        <Hash value={v.llvm_ir_hash} />
                      </td>
                      <td>
                        <Hash value={v.artifact_hash} />
                      </td>
                      <td>
                        <Hash value={v.structural_fingerprint} />
                      </td>
                      <td>{string(v.artifact_size_bytes)}</td>
                      <td>{milliseconds(object(v.profile).aot_ms)}</td>
                      <td>{string(v.equivalence_status)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {current.status === "READY" && (
            <>
              <p className="success">
                {variants.length} real objects published · Ed25519 provenance
                signed ✓
              </p>
              <button
                className="secondary"
                onClick={async () => {
                  setBusy(true);
                  try {
                    setVerification(
                      await api<Record<string, unknown>>(
                        `domain/build-runs/${current.id}/verify`,
                        { method: "POST" },
                      ),
                    );
                  } catch (e) {
                    setError(
                      e instanceof Error ? e.message : "Verification failed",
                    );
                  } finally {
                    setBusy(false);
                  }
                }}
                disabled={busy}
              >
                {busy ? "VERIFYING…" : "Verify build manifest & bytes"}
              </button>
              {verification && (
                <dl className="property-grid">
                  {Object.entries(verification).map(([key, value]) => (
                    <div key={key}>
                      <dt>{key.replaceAll("_", " ")}</dt>
                      <dd>{value ? "VALID" : "INVALID"}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </>
          )}
        </section>
      )}
      <section className="panel">
        <h2>Protected configuration</h2>
        <p>
          AES-256-GCM literal pools are implemented by the compiler. Use{" "}
          <code>
            runtime &#123; backend llvm execution memory protect_literals true
            &#125;
          </code>{" "}
          only with an externally provisioned key.
        </p>
        <p>
          {caps.data?.literal_key_configured
            ? "External key configured; protected sources can pass fixture gates."
            : "No external literal key configured. Protected builds fail explicitly; keys are never embedded in artifacts or displayed here."}
        </p>
        <p className="muted">
          Compiler environment: JOCKY_LITERAL_KEY_HEX / JOCKY_LITERAL_KEY_ID.
          Endpoint key distribution remains PARTIAL. Keys are provisioned
          separately from generated artifacts.
        </p>
      </section>
      <section className="panel">
        <h2>Build history</h2>
        {!runs.data?.length ? (
          <p>
            No builds yet. Compile a program in Workbench, then build its
            variants here.
          </p>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Build</th>
                  <th>Created</th>
                  <th>Status</th>
                  <th>Variants</th>
                  <th>Target</th>
                  <th>Seed</th>
                </tr>
              </thead>
              <tbody>
                {[...runs.data].reverse().map((r) => (
                  <tr key={r.id}>
                    <td>
                      <button
                        className="secondary"
                        onClick={() => {
                          setCompilation(String(r.compilation_id));
                          setSelected(r.id);
                          window.history.replaceState(
                            window.history.state,
                            "",
                            `/forge?compilation=${r.compilation_id}&build=${r.id}`,
                          );
                          setVerification(null);
                        }}
                      >
                        {r.id.slice(0, 8)}
                      </button>
                    </td>
                    <td>{new Date(String(r.created_at)).toLocaleString()}</td>
                    <td>{string(r.status)}</td>
                    <td>{string(r.variant_count)}</td>
                    <td>{string(r.target)}</td>
                    <td>{string(r.seed)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
