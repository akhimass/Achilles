"use client";
// The blank-console overview — the product as a general, indication-agnostic discovery
// console. It makes NO domain claim: you bring data (or load an example), and every
// answer stays grounded and cited. The AMR/Burkholderia work is one loadable dataset,
// surfaced only behind "Load the example dataset", never as the product's identity.
import { Badge } from "./ui";

export function GenericOverview({ onLoadDemo }: { onLoadDemo: () => void }) {
  return (
    <section>
      <div className="grid gap-8 lg:grid-cols-[1.1fr_1fr] lg:items-center">
        <div>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Badge tone="accent">upload or demo</Badge>
            <Badge tone="neutral">
              <span className="font-mono">provenance required</span>
            </Badge>
          </div>
          <h1 className="text-[2rem] font-semibold leading-[1.08] tracking-tightest text-text sm:text-[2.6rem]">
            Load a cohort into the <span className="text-gradient-green">evidence graph</span>.
          </h1>
          <p className="mt-4 max-w-xl text-[0.95rem] leading-relaxed text-muted">
            Point Achilles at strains, variants, and literature — every claim carries a
            citation, a deterministic core does the math, and the model only extracts and
            narrates grounded claims. Run a demo, or use it on your own.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              onClick={onLoadDemo}
              className="group inline-flex items-center gap-2 rounded-full bg-accent px-5 py-2.5 text-[0.9rem] font-semibold text-[rgb(var(--bg))] shadow-glow-sm transition hover:shadow-glow"
            >
              Load the example dataset
              <span className="transition-transform group-hover:translate-x-0.5">→</span>
            </button>
            <a
              href="#yourdata"
              className="inline-flex items-center gap-2 rounded-full border border-line/15 px-5 py-2.5 text-[0.9rem] font-medium text-text transition hover:border-line/30 hover:bg-surface2/50"
            >
              Bring your own data
            </a>
          </div>
        </div>

        <div className="glass rounded-2xl border border-line/10 p-5 shadow-card">
          <div className="text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-faint">
            What holds for any dataset
          </div>
          <ul className="mt-3 space-y-3">
            <Guarantee title="Deterministic core">
              Parsing, lineage, scoring, and optimization are plain, testable code — same
              input, same output. The model never computes a number.
            </Guarantee>
            <Guarantee title="Provenance on every edge">
              No claim is shown as validated without a source; grounded vs. abstract-only is
              visually distinct everywhere.
            </Guarantee>
            <Guarantee title="Cited or refused">
              Ask answers only from grounded evidence — or declines when nothing supports
              the question.
            </Guarantee>
          </ul>
        </div>
      </div>

      <Pipeline />
    </section>
  );
}

function Guarantee({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <li className="flex gap-2.5">
      <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
      <div>
        <div className="text-[0.82rem] font-medium text-text">{title}</div>
        <div className="mt-0.5 text-[0.74rem] leading-relaxed text-muted">{children}</div>
      </div>
    </li>
  );
}

function Pipeline() {
  // A generic, indication-agnostic pipeline — the shape holds for any domain.
  const stages = [
    { label: "Entities", sub: "your data in" },
    { label: "Relationships", sub: "extracted · typed" },
    { label: "Evidence", sub: "grounded · cited" },
    { label: "Candidates", sub: "ranked · scored" },
    { label: "Optimization", sub: "cited hypothesis" },
  ];
  return (
    <div className="mt-8 overflow-x-auto pb-1">
      <ol className="flex min-w-[720px] items-stretch gap-2">
        {stages.map((s, i) => (
          <li key={s.label} className="flex flex-1 items-center gap-2">
            <div className="hover-lift flex-1 rounded-xl border border-line/12 bg-surface2/40 px-3.5 py-3">
              <span className="text-sm font-semibold text-text">{s.label}</span>
              <div className="mt-0.5 text-[0.68rem] text-faint">{s.sub}</div>
            </div>
            {i < stages.length - 1 && (
              <svg width="26" height="12" viewBox="0 0 26 12" className="shrink-0" aria-hidden>
                <line x1="1" y1="6" x2="25" y2="6" stroke="rgb(var(--line))" strokeWidth="1.5" strokeLinecap="round" strokeDasharray="1 4" />
              </svg>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
