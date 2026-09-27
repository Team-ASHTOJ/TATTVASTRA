import { BuildForge } from "../../components/build-forge";
import { notFound, redirect } from "next/navigation";
import { StatusBadge } from "@jocky/ui";
import { sections } from "../../lib/sections";
import { PlatformOverview } from "../../components/platform-overview";
import { EvidenceVerifier } from "../../components/evidence-verifier";
import { CompilerWorkbench } from "../../components/compiler-workbench";
import { LanguageDocumentation } from "../../components/language-documentation";
import { DemoScreen } from "../../components/demo-presentation";

export function generateStaticParams() {
  return [
    ...sections.filter((s) => s.slug).map((s) => ({ section: s.slug })),
    { section: "judge" },
    { section: "live" },
  ];
}

export default async function SectionPage({
  params,
}: {
  params: Promise<{ section: string }>;
}) {
  const { section } = await params;
  if (section === "forge") return <BuildForge />;
  if (section === "language") return <LanguageDocumentation />;
  if (section === "live") redirect("/investigations");
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
                ? "Inspect persisted frontend, JIR, LLVM, and execution-plan outputs."
                : "Write a program, validate and compile it, generate variants, then investigate."}
            </p>
          </div>
          <StatusBadge tone="good">IMPLEMENTED</StatusBadge>
        </div>
        <CompilerWorkbench explorer={explorer} />
      </>
    );
  }
  if (section === "judge") redirect("/");
  const definition = sections.find((s) => s.slug === section);
  if (!definition) notFound();
  if (
    [
      "endpoints",
      "investigations",
      "findings",
      "timeline",
      "evidence",
      "variants",
      "performance",
      "graph",
      "drivers",
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
        <DemoScreen section={section}>
          {section === "evidence" && <EvidenceVerifier />}
        </DemoScreen>
      </>
    );
  return notFound();
}
