"use client";
// /bridge — a standalone surface for the researcher ⇄ physician handoff. Pick a gene and
// see one grounded finding translated across both lenses at once, provenance intact.
import { useState } from "react";
import Link from "next/link";
import { BridgePanel } from "@/components/BridgePanel";

const GENES = [
  { key: "MarR", label: "MarR" },
  { key: "AraC/MarA", label: "AraC/MarA" },
  { key: "efflux", label: "efflux (DMT)" },
];

export default function BridgePage() {
  const [gene, setGene] = useState("MarR");

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-line/8 bg-bg/60 backdrop-blur-xl">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
          <Link href="/" className="text-[1.2rem] font-semibold tracking-tightest text-gradient-green">
            Achilles
          </Link>
          <Link
            href="/explore?demo=1"
            className="rounded-full bg-accent px-4 py-1.5 text-[0.8rem] font-semibold text-[rgb(var(--bg))] shadow-glow-sm transition hover:shadow-glow"
          >
            Open console
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-12">
        <p className="text-[0.7rem] font-semibold uppercase tracking-[0.16em] text-accentStrong">
          Research ⇄ clinic bridge
        </p>
        <h1 className="mt-2 text-[2rem] font-semibold tracking-tightest text-text sm:text-[2.4rem]">
          One grounded finding, both lenses.
        </h1>
        <p className="mt-3 max-w-2xl text-[0.95rem] leading-relaxed text-muted">
          Researchers and physicians read the same resistance biology differently. Achilles
          takes a single gene&apos;s <span className="text-text">grounded evidence</span> and
          shows it as target identification <span className="text-faint">and</span> as a
          treatment translation at once — carrying the same citations across the handoff.
          Nothing is generated; every chip links to a source, and the clinical side always
          wears its caveats.
        </p>

        <div className="mt-6 inline-flex rounded-lg border border-line/12 bg-surface2/40 p-0.5">
          {GENES.map((g) => (
            <button
              key={g.key}
              onClick={() => setGene(g.key)}
              className={
                "rounded-md px-3 py-1.5 text-[0.78rem] font-medium transition " +
                (gene === g.key
                  ? "bg-accent/15 text-accentStrong"
                  : "text-muted hover:text-text")
              }
            >
              {g.label}
            </button>
          ))}
        </div>

        <div className="mt-5">
          <BridgePanel gene={gene} />
        </div>

        <div className="mt-10 flex flex-wrap items-center gap-3 border-t border-line/8 pt-6 text-[0.8rem]">
          <Link href="/explore?demo=1" className="text-accentStrong hover:underline">
            Open the full console →
          </Link>
          <span className="text-line/25">·</span>
          <Link href="/methods" className="text-muted hover:text-text">
            Methods
          </Link>
        </div>
      </main>
    </div>
  );
}
