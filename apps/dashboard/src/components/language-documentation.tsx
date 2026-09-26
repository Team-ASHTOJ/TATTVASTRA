"use client";
import Link from "next/link";
import { useState } from "react";
import { languageExamples } from "../lib/language-examples";
const constructs = [
  [
    "Targets",
    "Select authorized endpoint groups, hosts, IDs, and operating systems. Selectors are resolved by the control plane.",
    'targets { group "AUTHORIZED" os windows | linux }',
  ],
  [
    "Runtime / Execution",
    "LLVM is mandatory. Memory execution uses the dedicated worker process; native execution uses a compiler-built executable. Endpoint availability is reviewed before dispatch.",
    "runtime { backend llvm execution memory }",
  ],
  [
    "Variants",
    "Declare reproducible compiler diversity. Artifact hashes identify actual builds; different hashes alone do not prove semantic equivalence.",
    "runtime { backend llvm execution memory variant { enabled true seed 0x01 profile balanced } }",
  ],
  [
    "Capabilities",
    "Declare required read permissions. Compilation validates them; endpoint policy must also authorize them.",
    "capabilities { system.read process.read network.read }",
  ],
  [
    "Budgets",
    "Set resource bounds. Current remote execution supports MONITORED enforcement; strict enforcement is unavailable.",
    "budget { cpu <= 20% memory <= 256MB io <= 150MB duration <= 120s }",
  ],
  [
    "Collectors",
    "Bind a typed dataset to a name. Actual collection depends on endpoint adapter availability.",
    "collect processes as procs",
  ],
  [
    "Filters",
    "Immutable pipelines filter, project, sort, limit, and group typed datasets. Rich query operations compile but are outside the current bounded remote inventory bridge.",
    "let unsigned = procs | where signed == false | select [pid, name] | limit 25",
  ],
  [
    "Correlation / Findings",
    "Join same-endpoint datasets by a compatible scalar field and define evidence-backed findings. Review process identity and timestamps when correlating PIDs.",
    'correlate procs.pid with conns.pid as related\nfinding "Process connection" { when count(related) > 0 severity HIGH evidence related }',
  ],
  [
    "Timeline / Export",
    "Combine previously bound datasets into a timeline and export a final report. Export must be the last statement.",
    "timeline { source procs source conns }\nexport report { format json include evidence include timeline integrity true }",
  ],
] as const;
export function LanguageDocumentation() {
  const [notice, setNotice] = useState("");
  return (
    <div className="operator-presentation">
      <section className="panel">
        <h1>JOCKY Language</h1>
        <p>
          A typed forensic language for authorized Windows and Linux endpoints.
          Python orchestrates; the C++ frontend and mandatory LLVM backend
          compile your source.
        </p>
        <h2>Quick Start</h2>
        <pre className="compiler-output">{languageExamples[0]!.source}</pre>
        <p>
          Source → Lexer → Parser / AST → Semantic and capability validation →
          Typed JIR → LLVM → Variant / artifact
        </p>
        <Link className="button" href="/workbench">
          Open Workbench
        </Link>
      </section>
      <section className="panel">
        <h2>Program Structure</h2>
        <p>
          One hunt per compilation unit. Declarations precede collection and
          analysis statements. Bindings are immutable. Comments use // or /* …
          */; strings use JSON escapes.
        </p>
        {constructs.map(([title, purpose, syntax]) => (
          <article className="language-construct" key={title}>
            <h3>{title}</h3>
            <p>{purpose}</p>
            <pre className="compiler-output">{syntax}</pre>
          </article>
        ))}
      </section>
      <section className="panel">
        <h2>Collector Registry</h2>
        <p>
          Compiler-supported names include
          system/hostname/endpoints/environment/packages; users/sessions;
          processes/process_metadata/process_hash/process_signatures;
          connections/ports/interfaces/routes/dns;
          files/file_metadata/directories/hash/file_hash/file_content;
          logs/events; services/startup/scheduled_tasks;
          drivers/driver_hash/driver_signatures/modules.
        </p>
        <p>
          Path collectors require a typed path option. Hash/content collection
          requires filesystem.content. Current remote execution admits bounded
          system, users, processes, interfaces, connections, routes, services,
          events, and drivers inventory without options. Optional tools and
          richer operations are unavailable unless explicitly supported by an
          endpoint.
        </p>
      </section>
      <section className="panel">
        <h2>Working Examples</h2>
        {notice && <p role="status">{notice}</p>}
        {languageExamples.map((example) => (
          <article className="language-construct" key={example.name}>
            <h3>{example.name}</h3>
            <pre className="compiler-output">{example.source}</pre>
            <div className="workbench-actions">
              <button
                className="secondary"
                onClick={async () => {
                  await navigator.clipboard.writeText(example.source);
                  setNotice(`${example.name} copied`);
                }}
              >
                Copy
              </button>
              <Link
                className="button"
                href="/workbench"
                onClick={() =>
                  sessionStorage.setItem(
                    "jocky-source-transfer",
                    example.source,
                  )
                }
              >
                Open in Workbench
              </Link>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
