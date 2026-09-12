"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { sections } from "../lib/sections";

export function Navigation() {
  const pathname = usePathname();
  return (
    <nav aria-label="Main navigation">
      {sections.map((section, index) => (
        <div key={section.slug}>
          {sections[index - 1]?.group !== section.group && (
            <div className="nav-group">{section.group}</div>
          )}
          <Link
            href={`/${section.slug}`}
            aria-current={pathname === `/${section.slug}` ? "page" : undefined}
          >
            <span className="nav-dot" aria-hidden="true" />
            {section.name}
          </Link>
        </div>
      ))}
    </nav>
  );
}
