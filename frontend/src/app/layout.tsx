import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Source_Serif_4 } from "next/font/google";
import { Aurora } from "@/components/Aurora";
import "./globals.css";

const sourceSerif = Source_Serif_4({
  subsets: ["latin"],
  variable: "--font-source-serif",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://achilles-science.vercel.app"),
  title: "Achilles — AMR evidence graph",
  description:
    "Evidence-grounded antimicrobial resistance target identification and treatment optimization. Deterministic lineage and collateral-sensitivity math, literature grounded to CARD and UniProt, provenance on every edge.",
  applicationName: "Achilles",
  openGraph: {
    title: "Achilles — AMR evidence graph",
    description:
      "Strain → variant → target → cycling hypothesis, with provenance on every link. Deterministic core; reproducible from public data.",
    siteName: "Achilles",
    url: "https://achilles-science.vercel.app",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Achilles — AMR evidence graph",
    description:
      "Evidence-grounded AMR target identification and treatment optimization. Provenance on every edge.",
  },
};

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
      className={`${GeistSans.variable} ${GeistMono.variable} ${sourceSerif.variable}`}
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
