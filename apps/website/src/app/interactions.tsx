"use client";

import { useEffect, useState } from "react";

const navigation = [
  ["Overview", "overview"],
  ["JOCKY", "jocky"],
  ["Compiler", "compiler"],
  ["Build Forge", "forge"],
  ["Execution", "execution"],
  ["Evidence", "evidence"],
  ["Intelligence", "intelligence"],
  ["Developers", "developers"],
] as const;

export function SiteHeader() {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState("overview");

  useEffect(() => {
    const sections = navigation
      .map(([, id]) => document.getElementById(id))
      .filter((section): section is HTMLElement => Boolean(section));
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible) setActive(visible.target.id);
      },
      { rootMargin: "-22% 0px -62%", threshold: [0, 0.15, 0.5] },
    );
    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, []);

  return (
    <header className="site-header">
      <a className="nav-brand" href="#overview" aria-label="TATTVASTRA home">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/tattvastra-mark.png" alt="" />
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/tattvastra-wordmark.png" alt="TATTVASTRA" />
      </a>
      <button
        className="menu-toggle"
        type="button"
        aria-expanded={open}
        aria-controls="primary-navigation"
        onClick={() => setOpen((value) => !value)}
      >
        <span />
        <span />
        <span />
        <b className="sr-only">Toggle navigation</b>
      </button>
      <nav
        id="primary-navigation"
        className={open ? "nav-links is-open" : "nav-links"}
        aria-label="Primary navigation"
      >
        {navigation.map(([label, id]) => (
          <a
            key={id}
            href={`#${id}`}
            aria-current={active === id ? "location" : undefined}
            onClick={() => setOpen(false)}
          >
            {label}
          </a>
        ))}
      </nav>
      <div className="nav-actions">
        <a
          href="https://github.com/Team-ASHTOJ/TATTVASTRA"
          target="_blank"
          rel="noreferrer"
          className="nav-github"
        >
          GitHub ↗
        </a>
        <a className="button button-small" href="#jocky">
          Explore JOCKY
        </a>
      </div>
    </header>
  );
}

export function PageEnhancements() {
  useEffect(() => {
    const nodes = Array.from(
      document.querySelectorAll<HTMLElement>("[data-reveal]"),
    );
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      nodes.forEach((node) => node.classList.add("is-visible"));
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { rootMargin: "0px 0px -9%", threshold: 0.08 },
    );
    nodes.forEach((node) => observer.observe(node));

    const handleVisibility = () => {
      document
        .querySelectorAll<SVGSVGElement>(".fabric-lines")
        .forEach((svg) => {
          if (document.visibilityState === "visible") {
            svg.unpauseAnimations?.();
          } else {
            svg.pauseAnimations?.();
          }
        });
    };
    document.addEventListener("visibilitychange", handleVisibility);
    handleVisibility();
    return () => {
      observer.disconnect();
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, []);
  return null;
}

export function CodePanel() {
  const [tab, setTab] = useState<"source" | "jir">("source");
  const [copied, setCopied] = useState(false);
  const source = `hunt "endpoint-triage" {
  targets { group "AUTHORIZED" os windows | linux }
  runtime {
    backend llvm
    execution memory
    variant { enabled true seed auto profile balanced }
  }
  capabilities {
    system.read process.read network.read drivers.read
  }
  budget { cpu <= 20% memory <= 256MB duration <= 120s }
  collect system as system_info
  collect processes as processes
  collect connections as connections
  collect drivers as drivers
}`;
  const jir = `JIR_VERSION 1
HUNT endpoint-triage
TARGET_OS windows | linux
CAP_REQUIRE system.read, process.read, network.read, drivers.read
BUDGET cpu=20% memory=268435456 duration=120s
COLLECT_SYSTEM -> dataset<system>
COLLECT_PROCESSES -> dataset<process>
COLLECT_CONNECTIONS -> dataset<connection>
COLLECT_DRIVERS -> dataset<driver>`;

  async function copy() {
    await navigator.clipboard.writeText(tab === "source" ? source : jir);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  }

  return (
    <div className="code-window">
      <div className="window-bar">
        <div className="window-dots" aria-hidden="true">
          <i />
          <i />
          <i />
        </div>
        <div
          className="code-tabs"
          role="tablist"
          aria-label="Code representation"
        >
          <button
            className={tab === "source" ? "active" : ""}
            type="button"
            onClick={() => setTab("source")}
          >
            source.jky
          </button>
          <button
            className={tab === "jir" ? "active" : ""}
            type="button"
            onClick={() => setTab("jir")}
          >
            typed.jir
          </button>
        </div>
        <button className="copy-button" type="button" onClick={copy}>
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre aria-live="polite">
        <code>{tab === "source" ? source : jir}</code>
      </pre>
      <div className="code-status">
        <span>● VALID</span>
        <span>
          {tab === "source" ? "JOCKY SOURCE" : "PLATFORM-INDEPENDENT IR"}
        </span>
      </div>
    </div>
  );
}
