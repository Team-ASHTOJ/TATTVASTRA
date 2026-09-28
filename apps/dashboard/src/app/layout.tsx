import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import { Navigation } from "../components/navigation";
import { Providers } from "../components/providers";
import "./globals.css";
import { AccountMenu } from "../components/account-menu";
import { AtmosphereField } from "../components/atmosphere-field";
import { ModeIndicator } from "../components/demo-presentation";

export const metadata: Metadata = {
  title: "Tattvastra | Forensic Operations",
  description: "Precision investigation across every endpoint.",
  icons: { icon: "/icon.svg" },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <AtmosphereField />
        <Providers>
          <a className="skip-link" href="#main">
            Skip to content
          </a>
          <aside className="sidebar">
            <Link href="/" className="brand">
              <Image
                className="brand-mark"
                src="/tattvastra-mark.png"
                alt=""
                width={824}
                height={907}
                unoptimized
                priority
              />
              <span className="brand-copy">
                <Image
                  className="brand-wordmark"
                  src="/tattvastra-wordmark.png"
                  alt="Tattvastra"
                  width={1355}
                  height={146}
                  unoptimized
                  priority
                />
                <small>
                  JOCKY Framework · Cross-Platform Forensic Scripting Language
                </small>
              </span>
            </Link>
            <Navigation />
            <div className="sidebar-footer">
              v0.1.0 <span>OPERATOR CONSOLE</span>
            </div>
          </aside>
          <div className="workspace">
            <header className="topbar">
              <span>Precision investigation across every endpoint.</span>
              <ModeIndicator />
              <AccountMenu />
            </header>
            <main id="main">{children}</main>
            <footer className="workspace-footer">
              TATTVASTRA / FORENSIC OPERATIONS
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
