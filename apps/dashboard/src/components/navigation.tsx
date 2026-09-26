"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { sections } from "../lib/sections";

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
            <span className="nav-dot" aria-hidden="true" />
            {section.slug === "architecture"
              ? "Requirement Coverage"
              : section.name}
          </Link>
        </div>
      ))}
    </nav>
  );
}
