"use client";
// Blank-console overview — instrument start state, not a marketing pitch.

export function GenericOverview({ onLoadDemo }: { onLoadDemo: () => void }) {
  return (
    <section className="grid gap-8 lg:grid-cols-[1.15fr_1fr] lg:items-start">
      <div>
        <p className="text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-faint">
          Console
        </p>
        <h1 className="mt-1.5 font-serif text-[1.75rem] font-medium tracking-tight text-text sm:text-[2.1rem]">
          Load a cohort to begin
        </h1>
        <p className="mt-3 max-w-xl text-[0.9rem] leading-relaxed text-muted">
          Achilles reconstructs lineage and reversible loci, grounds literature claims,
          ranks targets, and surfaces collateral-sensitivity structure. Start from the
          public Burkholderia example, or upload your own genotype CSV.
        </p>
        <div className="mt-6 flex flex-wrap items-center gap-2.5">
          <button
            onClick={onLoadDemo}
            className="rounded-md bg-accent px-4 py-2 text-[0.88rem] font-semibold text-[rgb(var(--bg))] transition hover:brightness-110"
          >
            Load B. multivorans demo
          </button>
          <a
            href="#yourdata"
            className="rounded-md border border-line/20 px-4 py-2 text-[0.88rem] font-medium text-text transition hover:border-line/35 hover:bg-surface/50"
          >
            Upload strains
          </a>
        </div>
      </div>

      <div className="rounded-lg border border-line/12 bg-surface/60 p-4">
        <p className="text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-faint">
          Guarantees
        </p>
        <ul className="mt-3 space-y-3 text-[0.82rem] leading-relaxed text-muted">
          <li>
            <span className="font-medium text-text">Deterministic core.</span> Lineage,
            scoring, and cycling math are plain code — not LLM output.
          </li>
          <li>
            <span className="font-medium text-text">Cited edges only.</span> Claims without
            PMID or reference-DB accession never enter the graph.
          </li>
          <li>
            <span className="font-medium text-text">Refusal over fabrication.</span> Ask
            answers from grounded evidence, or declines.
          </li>
        </ul>
      </div>
    </section>
  );
}
