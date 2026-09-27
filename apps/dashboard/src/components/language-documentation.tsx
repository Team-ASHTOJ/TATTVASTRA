"use client";
import Link from "next/link";
import { useState } from "react";
import { languageExamples } from "../lib/language-examples";
import { documentationSections } from "../lib/documentation";
const anchor = (name: string) => name.toLowerCase().replaceAll(" ", "-");
export function LanguageDocumentation() {
  const [notice, setNotice] = useState("");
  const example = (name: string, source: string) => (
    <>
      <pre className="compiler-output">{source}</pre>
      <div className="workbench-actions">
        <button
          className="secondary"
          onClick={async () => {
            await navigator.clipboard.writeText(source);
            setNotice(`${name} copied ✓`);
          }}
        >
          Copy
        </button>
        <Link
          className="button"
          href="/workbench"
          onClick={() =>
            sessionStorage.setItem("jocky-source-transfer", source)
          }
        >
          Open in Workbench
        </Link>
      </div>
    </>
  );
  return (
    <div className="docs-layout">
      <nav className="docs-nav" aria-label="Documentation sections">
        <strong>JOCKY Documentation</strong>
        {[...documentationSections.map((s) => s.title), "Examples"].map(
          (name) => (
            <a href={`#${anchor(name)}`} key={name}>
              {name}
            </a>
          ),
        )}
      </nav>
      <div className="operator-presentation">
        <section className="panel">
          <h1>Documentation</h1>
          <p>
            JOCKY language reference · implemented syntax and compile-valid
            programs.
          </p>
          {notice && <p role="status">{notice}</p>}
        </section>
        {documentationSections.map((s) => (
          <section className="panel" id={anchor(s.title)} key={s.title}>
            <h2>{s.title}</h2>
            <p>{s.purpose}</p>
            {example(s.title, s.source)}
            {s.title === "Collectors" && (
              <p>
                Compiler-supported aliases:
                system/hostname/endpoints/environment/packages; users/sessions;
                processes/process_metadata/process_hash/process_signatures;
                connections/ports/interfaces/routes/dns;
                files/file_metadata/directories/hash/file_hash/file_content;
                logs/events; services/startup/scheduled_tasks;
                drivers/driver_hash/driver_signatures/modules. Path collectors
                require typed path options. Hash/content reads require
                filesystem.content. Adapter availability is reported by
                endpoints.
              </p>
            )}
          </section>
        ))}
        <section className="panel" id="examples">
          <h2>Examples</h2>
          {languageExamples.map((e) => (
            <article className="language-construct" key={e.name}>
              <h3>{e.name}</h3>
              {example(e.name, e.source)}
            </article>
          ))}
        </section>
      </div>
    </div>
  );
}
