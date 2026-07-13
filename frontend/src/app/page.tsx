"use client";
// Landing — brand-first, scientific, no marketing theater.
import Link from "next/link";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function Landing() {
  return (
    <div className="min-h-screen">
      <header className="absolute inset-x-0 top-0 z-40">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-5">
          <Link href="/" className="flex items-center gap-2.5">
            <Mark />
            <span className="font-serif text-[1.35rem] tracking-tight text-text">Achilles</span>
          </Link>
          <div className="flex items-center gap-5">
            <nav className="hidden items-center gap-6 text-[0.8rem] text-muted md:flex">
              <a href="#method" className="transition hover:text-text">
                Method
              </a>
              <a
                href="https://github.com/akhimass/Achilles"
                target="_blank"
                rel="noopener noreferrer"
                className="transition hover:text-text"
              >
                Source
              </a>
            </nav>
            <ThemeToggle />
            <Link
              href="/explore"
              className="rounded-md bg-text px-3.5 py-2 text-[0.8rem] font-medium text-bg transition hover:opacity-90"
            >
              Open console
            </Link>
          </div>
        </div>
      </header>

      <main>
        {/* First viewport: brand, one headline, one sentence, CTA — nothing else */}
        <section className="relative flex min-h-[100svh] flex-col justify-end px-6 pb-16 pt-28 sm:pb-24 sm:pt-32">
          <div className="pointer-events-none absolute inset-0 bg-grid opacity-50" aria-hidden />
          <div className="relative mx-auto w-full max-w-6xl">
            <p className="font-serif text-[clamp(3.4rem,11vw,7.5rem)] font-medium leading-[0.92] tracking-tightest text-text">
              Achilles
            </p>
            <h1 className="mt-6 max-w-2xl text-[1.35rem] font-medium leading-snug tracking-tight text-text sm:text-[1.65rem]">
              An evidence graph for antimicrobial resistance —
              strain to target to cycling hypothesis, with provenance on every link.
            </h1>
            <p className="mt-4 max-w-xl text-[0.95rem] leading-relaxed text-muted">
              Deterministic lineage and collateral-sensitivity math, literature claims
              grounded to CARD and UniProt, and ranked targets you can inspect — not a
              chatbot wrapping a database.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link
                href="/explore?demo=1"
                className="rounded-md bg-accent px-5 py-2.5 text-[0.9rem] font-semibold text-[rgb(var(--bg))] transition hover:brightness-110"
              >
                Explore the B. multivorans graph
              </Link>
              <Link
                href="/explore"
                className="rounded-md border border-line/20 px-5 py-2.5 text-[0.9rem] font-medium text-text transition hover:border-line/35 hover:bg-surface/50"
              >
                Open blank console
              </Link>
            </div>
          </div>
        </section>

        <section id="method" className="border-t border-line/10 px-6 py-20">
          <div className="mx-auto max-w-6xl">
            <p className="text-[0.7rem] font-semibold uppercase tracking-[0.16em] text-faint">
              Method
            </p>
            <h2 className="mt-3 max-w-2xl font-serif text-[1.85rem] font-medium leading-snug tracking-tight text-text sm:text-[2.15rem]">
              The product is the graph, not the pipeline.
            </h2>
            <div className="mt-10 grid gap-10 md:grid-cols-3">
              <Method
                title="Deterministic core"
                body="Parsing, lineage reconstruction, flipper detection, and collateral-sensitivity structure are plain Python. Same input, same output. The model never invents a score or a schedule."
              />
              <Method
                title="Provenance or it doesn't exist"
                body="Every evidence edge cites a PMID or a reference-DB accession. Ungrounded claims stay out of the graph. Confidence is a gradient, not a hard yes/no."
              />
              <Method
                title="Reproducible from public data"
                body="PubMLST isolates, Europe PMC literature, CARD / UniProt / ChEMBL grounding. Seed offline from committed public caches. MIT-licensed."
              />
            </div>

            <div className="mt-14 grid gap-8 border-t border-line/10 pt-10 lg:grid-cols-[1fr_1.1fr]">
              <div>
                <h3 className="font-serif text-xl font-medium text-text">What you get in the console</h3>
                <ul className="mt-4 space-y-2.5 text-[0.9rem] leading-relaxed text-muted">
                  <li>Interactive lineage with reversible (flipper) loci</li>
                  <li>Grounded evidence chains for genes and targets</li>
                  <li>Ranked candidate targets with ChEMBL tractability</li>
                  <li>Collateral-sensitivity cycling as a cited hypothesis</li>
                  <li>Self-validation against public ground-truth controls</li>
                </ul>
              </div>
              <div>
                <h3 className="font-serif text-xl font-medium text-text">Built for AMR research</h3>
                <p className="mt-4 text-[0.9rem] leading-relaxed text-muted">
                  Primary users are academic and translational researchers tracking
                  resistance across bacterial strains. The live demo uses public{" "}
                  <em className="text-text not-italic">Burkholderia multivorans</em>{" "}
                  isolates — seventy strains, hundreds of variants, and sixty-one
                  grounded literature edges you can audit end to end.
                </p>
                <Link
                  href="/explore?demo=1"
                  className="mt-6 inline-flex items-center gap-1.5 text-[0.9rem] font-medium text-accentStrong transition hover:underline"
                >
                  Open the live graph
                  <span aria-hidden>→</span>
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-line/10 px-6 py-8">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 text-[0.75rem] text-faint sm:flex-row sm:items-center sm:justify-between">
          <span>
            <span className="font-serif text-muted">Achilles</span>
            {" · "}evidence graph for AMR
          </span>
          <span>
            Public data only ·{" "}
            <a
              href="https://github.com/akhimass/Achilles"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-text"
            >
              MIT
            </a>
          </span>
        </div>
      </footer>
    </div>
  );
}

function Method({ title, body }: { title: string; body: string }) {
  return (
    <div>
      <h3 className="text-[0.95rem] font-semibold text-text">{title}</h3>
      <p className="mt-2 text-[0.88rem] leading-relaxed text-muted">{body}</p>
    </div>
  );
}

function Mark() {
  return (
    <span className="grid h-8 w-8 place-items-center rounded-md border border-line/15 bg-surface/80">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
        <path
          d="M5 12 H11 M11 12 L17 6 M11 12 L17 18"
          stroke="rgb(var(--muted))"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
        <circle cx="4.5" cy="12" r="1.6" fill="rgb(var(--muted))" />
        <circle cx="17.5" cy="6" r="1.6" fill="rgb(var(--muted))" />
        <circle cx="17.6" cy="18" r="2.2" fill="rgb(var(--accent))" />
      </svg>
    </span>
  );
}
