import { notFound } from "next/navigation";
import Link from "next/link";
import { EmptyState, StatusBadge } from "@jocky/ui";
import { sections } from "../../lib/sections";
import { PlatformOverview } from "../../components/platform-overview";
import { EvidenceVerifier } from "../../components/evidence-verifier";

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
  if (section === "judge")
    return (
      <>
        <div className="eyebrow">PRESENTATION / READINESS</div>
        <h1>Judge Mode</h1>
        <div className="notice">
          <StatusBadge tone="warning">NOT READY</StatusBadge>
          <p>
            The end-to-end demonstration requires phases P1–P9. No hunt or build
            is simulated here.
          </p>
        </div>
        <section className="panel">
          <h2>Available foundation walkthrough</h2>
          <ol className="judge-steps">
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
