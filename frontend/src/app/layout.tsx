import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Aurora } from "@/components/Aurora";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://achilles-science.vercel.app"),
  title: "Achilles — evidence-grounded discovery console",
  description:
    "A domain-agnostic discovery console: point it at your data and it builds a provenance-checked evidence graph — every claim cited, or it refuses. Deterministic core, reproducible from public data. Shown end-to-end on antimicrobial resistance.",
  applicationName: "Achilles",
  openGraph: {
    title: "Achilles — evidence-grounded discovery console",
    description:
      "Point it at your data and it builds a provenance-checked evidence graph — every claim cited, or it refuses. Reproducible from public data. Shown end-to-end on antimicrobial resistance.",
    siteName: "Achilles",
    url: "https://achilles-science.vercel.app",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Achilles — evidence-grounded discovery console",
    description:
      "A provenance-checked evidence graph: every claim cited, or it refuses. Deterministic core, reproducible from public data.",
  },
};

// Set the theme before first paint so there is no flash of the wrong palette.
const themeScript = `
(function () {
  try {
    var stored = localStorage.getItem('achilles-theme');
    var dark = stored ? stored === 'dark'
      : window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (dark) document.documentElement.classList.add('dark');
  } catch (e) {}
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${GeistSans.variable} ${GeistMono.variable}`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="font-sans">
        <Aurora />
        {children}
      </body>
    </html>
  );
}
