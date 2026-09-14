import { notFound } from "next/navigation";
import Link from "next/link";
import { EmptyState, StatusBadge } from "@jocky/ui";
import { sections } from "../../lib/sections";
import { PlatformOverview } from "../../components/platform-overview";
import { EvidenceVerifier } from "../../components/evidence-verifier";
import { CompilerWorkbench } from "../../components/compiler-workbench";
import { ControlResources } from "../../components/control-resources";

export function generateStaticParams() {
  return [
    ...sections.filter((s) => s.slug).map((s) => ({ section: s.slug })),
    { section: "judge" },
  ];
}

export default async function SectionPage({
  params,
}: {
  params: Promise<{ section: string }>;
}) {
  const { section } = await params;
  if (section === "architecture") return <PlatformOverview coverageOnly />;
  if (section === "workbench" || section === "compiler") {
    const explorer = section === "compiler";
    return (
      <>
        <div className="eyebrow">BUILD / NATIVE COMPILER</div>
        <div className="page-heading">
          <div>
            <h1>{explorer ? "Compiler Explorer" : "JOCKY Workbench"}</h1>
            <p>
              {explorer
                ? "Inspect each real frontend, JIR, LLVM, and fixture-execution stage."
                : "Edit a hunt, validate it, inspect its representations, and run the deterministic compiler fixture."}
            </p>
          </div>
          <StatusBadge tone="good">IMPLEMENTED</StatusBadge>
        </div>
        <CompilerWorkbench explorer={explorer} />
      </>
    );
  }
  if (section === "judge")
    return (
      <>
        <div className="eyebrow">PRESENTATION / READINESS</div>
        <h1>Judge Mode</h1>
        <div className="notice">
          <StatusBadge tone="warning">NOT READY</StatusBadge>
          <p>
            The compiler and local Agent slices are available. The end-to-end
            distributed demonstration still requires control-plane enrollment,
            dispatch, and durable evidence.
          </p>
        </div>
        <section className="panel">
          <h2>Available foundation walkthrough</h2>
          <ol className="judge-steps">
            <li>
              <Link href="/workbench">
                Validate a hunt and inspect native compiler output
              </Link>
            </li>
            <li>
              <Link href="/compiler">Walk through each compiler stage</Link>
            </li>
            <li>
              <Link href="/architecture">
                Inspect architecture and requirement coverage
              </Link>
            </li>
            <li>
              <Link href="/evidence">
                Recompute a submitted observation’s integrity hash
              </Link>
            </li>
            <li>
              <Link href="/">Review platform availability</Link>
            </li>
          </ol>
          <p>
            The full 3–5 minute execution sequence is specified in
            docs/DEMO_FLOW.md.
          </p>
        </section>
      </>
    );
  const definition = sections.find((s) => s.slug === section);
  if (!definition) notFound();
  if (
    [
      "cases",
      "endpoints",
      "jobs",
      "findings",
      "timeline",
      "evidence",
      "reports",
      "variants",
      "forge",
      "compatibility",
      "performance",
      "graph",
      "live",
    ].includes(section)
  )
    return (
      <>
        <div className="eyebrow">{definition.group} / CONTROL PLANE</div>
        <div className="page-heading">
          <div>
            <h1>{definition.name}</h1>
            <p>{definition.description}</p>
          </div>
          <StatusBadge tone="good">PERSISTED API</StatusBadge>
        </div>
        <ControlResources key={section} section={section} />
        {section === "evidence" && <EvidenceVerifier />}
      </>
    );
  return (
    <>
      <div className="eyebrow">
        {definition.group} / {definition.phase}
      </div>
      <div className="page-heading">
        <div>
          <h1>{definition.name}</h1>
          <p>{definition.description}</p>
        </div>
        <StatusBadge tone="warning">
          {section === "evidence" ? "PARTIAL FOUNDATION" : "PLANNED"}
        </StatusBadge>
      </div>
      {section === "evidence" ? (
        <EvidenceVerifier />
      ) : (
        <section className="panel">
          <EmptyState title="Implementation pending">
            <p>{definition.description}</p>
            <p>
              Acceptance is tracked in phase {definition.phase}. No operational
              data is available.
            </p>
            <Link href="/architecture" className="text-link">
              View requirement coverage →
            </Link>
          </EmptyState>
        </section>
      )}
    </>
  );
}
