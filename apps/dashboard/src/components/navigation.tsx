"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { sections } from "../lib/sections";
import { Icon, type IconName } from "./icons";

const sectionIcons: Record<string, IconName> = {
  "": "dashboard",
  workbench: "code",
  language: "book",
  compiler: "workflow",
  forge: "hammer",
  variants: "branch",
  endpoints: "monitor",
  investigations: "search",
  findings: "triangle",
  graph: "network",
  timeline: "clock",
  evidence: "shield",
  drivers: "cpu",
  compatibility: "shield",
  performance: "activity",
  architecture: "database",
};

export function Navigation() {
  const pathname = usePathname();
  const focused = sections;
  return (
    <nav aria-label="Main navigation">
      {focused.map((section, index) => (
        <div key={section.slug}>
          {focused[index - 1]?.group !== section.group && (
            <div className="nav-group">{section.group}</div>
          )}
          <Link
            href={`/${section.slug}`}
            aria-current={pathname === `/${section.slug}` ? "page" : undefined}
          >
            <Icon name={sectionIcons[section.slug] ?? "activity"} />
            {section.slug === "architecture"
              ? "Requirement Coverage"
              : section.name}
          </Link>
        </div>
      ))}
    </nav>
  );
}
