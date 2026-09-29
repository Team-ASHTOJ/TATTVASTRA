import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://tattvastra.vercel.app"),
  title: "TATTVASTRA | JOCKY Forensic Platform",
  description:
    "A language-first cross-platform forensic platform combining typed JIR, LLVM compilation, controlled endpoint execution and verifiable evidence.",
  icons: { icon: "/icon.svg", apple: "/tattvastra-mark.png" },
  openGraph: {
    title: "TATTVASTRA | JOCKY Forensic Platform",
    description:
      "A language-first forensic platform from source code to verifiable evidence.",
    type: "website",
    images: [
      {
        url: "/tattvastra-logo.png.png",
        width: 1387,
        height: 1134,
        alt: "TATTVASTRA",
      },
    ],
  },
};

export const viewport: Viewport = {
  colorScheme: "dark",
  themeColor: "#05080c",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
