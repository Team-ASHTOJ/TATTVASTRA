"use client";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import type { IntegrityResult } from "@jocky/contracts";
import { StatusBadge } from "@jocky/ui";
import { api } from "../lib/api";

export function EvidenceVerifier() {
  const [source, setSource] = useState("");
  const mutation = useMutation({
    mutationFn: async () => {
      const payload: unknown = JSON.parse(source);
      return api<IntegrityResult>("evidence/verify-observation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    },
  });
  return (
    <section className="panel verifier">
      <div className="panel-heading">
        <h2>Verify a submitted observation</h2>
        <StatusBadge>STATELESS VERIFIER</StatusBadge>
      </div>
      <p>
        This recomputes the observation hash. Storage provenance, producer
        signatures, and manifest completeness are not checked.
      </p>
      <label htmlFor="observation">Observation JSON (contract v1.0.0)</label>
      <textarea
        id="observation"
        spellCheck={false}
        value={source}
        onChange={(event) => {
          setSource(event.target.value);
          mutation.reset();
        }}
        placeholder="Paste an observation with its provenance and integrity_hash"
        rows={12}
      />
      <button
        disabled={!source.trim() || mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        {mutation.isPending ? "Verifying…" : "VERIFY INTEGRITY"}
      </button>
      {mutation.isError && (
        <p role="alert" className="error-text">
          {mutation.error.message}
        </p>
      )}
      {mutation.data && (
        <div role="status" className="verification-result">
          <StatusBadge
            tone={mutation.data.integrity_valid ? "good" : "warning"}
          >
            {mutation.data.simulation ? "SANDBOX" : "REAL-LABELED SUBMISSION"}
          </StatusBadge>
          <h3>
            {mutation.data.integrity_valid
              ? "Hash matches submitted observation"
              : "Integrity mismatch"}
          </h3>
          <p>Signature: NOT CHECKED · Scope: submitted observation only</p>
          <dl>
            <dt>Expected SHA-256</dt>
            <dd>{mutation.data.expected_hash}</dd>
            <dt>Recomputed SHA-256</dt>
            <dd>{mutation.data.computed_hash}</dd>
          </dl>
        </div>
      )}
    </section>
  );
}
