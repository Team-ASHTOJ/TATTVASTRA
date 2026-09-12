"use client";
import { useState } from "react";
import type { CapabilityStatus } from "@jocky/contracts";
import { StatusBadge } from "@jocky/ui";

export function Coverage({ items }: { items: CapabilityStatus[] }) {
  const [filter, setFilter] = useState("");
  const filtered = items.filter((item) =>
    `${item.id} ${item.title} ${item.subsystem} ${item.status}`
      .toLowerCase()
      .includes(filter.toLowerCase()),
  );
  return (
    <section className="panel coverage-panel">
      <div className="panel-heading">
        <h2>
          Requirement coverage{" "}
          <span className="subtle">
            {filtered.length} / {items.length}
          </span>
        </h2>
        <label>
          Filter requirements{" "}
          <input
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            placeholder="Search requirement, subsystem, status…"
          />
        </label>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Requirement / implementation</th>
              <th>Status</th>
              <th>Acceptance evidence</th>
              <th>Safety / environment</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((item) => (
              <tr key={item.id}>
                <td>
                  <small>
                    {item.id} / {item.subsystem} / {item.phase}
                  </small>
                  <strong>{item.title}</strong>
                  <p>{item.implementation}</p>
                </td>
                <td>
                  <StatusBadge
                    tone={item.status === "VERIFIED" ? "good" : "muted"}
                  >
                    {item.status.replaceAll("_", " ")}
                  </StatusBadge>
                </td>
                <td>{item.demo_evidence}</td>
                <td>{item.safety_environment_note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {filtered.length === 0 && (
        <p role="status">No requirements match this filter.</p>
      )}
    </section>
  );
}
