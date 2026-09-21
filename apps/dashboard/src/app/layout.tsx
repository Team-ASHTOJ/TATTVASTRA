import type { Metadata } from "next";
import Link from "next/link";
import { Navigation } from "../components/navigation";
import { Providers } from "../components/providers";
import "./globals.css";
import { ModeIndicator } from "../components/demo-presentation";

export const metadata: Metadata = {
  title: "JOCKY | Forensic Operations",
  description: "One Language. Every Endpoint. No Noise.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <a className="skip-link" href="#main">
            Skip to content
          </a>
          <aside className="sidebar">
            <Link href="/" className="brand">
              <span className="brand-mark">J</span>
              <span>
                JOCKY<small>FORENSIC OPERATIONS</small>
              </span>
            </Link>
            <Navigation />
            <div className="sidebar-footer">
              v0.1.0 <span>IDEA PROTOTYPE</span>
            </div>
          </aside>
          <div className="workspace">
            <header className="topbar">
              <span>One Language. Every Endpoint. No Noise.</span>
              <ModeIndicator />
              <Link href="/login">Operator sign in</Link>
              <Link href="/judge" className="button secondary">
                Judge Mode ↗
              </Link>
            </header>
            <main id="main">{children}</main>
            <footer className="workspace-footer">
              JOCKY / ENGINEERING PREVIEW
              <span>
                Capability status is explicit. Measurements require execution.
              </span>
            </footer>
          </div>
        </Providers>
      </body>
    </html>
  );
}
