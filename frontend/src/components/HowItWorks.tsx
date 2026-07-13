"use client";
// "How this works · reproducibility" — the trust surface. Makes the machinery legible
// to anyone who opens the URL: a deterministic core computes every number, the LLM
// only extracts typed claims and narrates with citations, provenance is on every edge,
// and the whole public graph reproduces from one command. Never hides the machinery.
import { Panel, Badge } from "./ui";

const REPO = "https://github.com/akhimass/Achilles";

export function HowItWorks() {
  return (
    <Panel
      title="How this works · reproducibility"
      aside={
        <span className="font-mono text-[0.68rem] text-faint">deterministic core</span>
      }
    >
      <p className="mb-3 text-[0.82rem] leading-relaxed text-text">
        Achilles surfaces the <span className="text-accentStrong">reversible target</span> —
        the opening resistance creates through collateral sensitivity — and every
        counterfactual (&ldquo;what happened next&rdquo;) is{" "}
        <span className="text-accentStrong">retrieved from evolved lineages</span>, never
        generated.
      </p>
      <p className="text-[0.82rem] leading-relaxed text-muted">
        A <span className="text-text">deterministic Python core</span> computes everything you
        see — lineage and flipper detection, the target{" "}
        <span className="font-mono text-text">rank_score</span>, and the collateral-sensitivity
        cycle math. The language model does exactly two things: it extracts{" "}
        <span className="text-text">typed claims</span> from public literature and{" "}
        <span className="text-text">narrates</span> already-computed results with citations. It
        never invents a number, a score, or a schedule. Every edge in the graph carries{" "}
        <span className="text-text">provenance</span> — a PubMed PMID and, where corroborated, a
        CARD / UniProt / ChEMBL accession. If a claim can&rsquo;t be grounded, it doesn&rsquo;t
        become an edge.
      </p>
      <p className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[0.8rem]">
        <a href="/methods" className="font-medium text-accentStrong hover:underline">
          Read the full methods, validation, and limitations →
        </a>
        <a href="/bridge" className="font-medium text-accentStrong hover:underline">
          See the research ⇄ clinic bridge →
        </a>
      </p>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <Pillar
          title="Deterministic core"
          body="Parsing, lineage, flippers, scoring, and cycling are plain Python — same input, same output. Unit-tested."
        />
        <Pillar
          title="Provenance on every edge"
          body="No ungrounded claim is shown as validated. Grounded vs. abstract-only is visually distinct everywhere."
        />
        <Pillar
          title="Reproducible"
          body="The public evidence graph rebuilds offline from a committed corpus — no live API needed to seed."
        />
      </div>

      <div className="mt-4 rounded-xl border border-line/10 bg-surface2/40 p-3">
        <div className="mb-2 text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-faint">
          Provenance legend
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[0.72rem] text-muted">
          <span className="flex items-center gap-1.5">
            <Badge tone="accent">grounded</Badge> PMID + reference-DB accession
          </span>
          <span className="flex items-center gap-1.5">
            <Badge tone="amber">abstract-only</Badge> stated in a PMID, not yet corroborated
          </span>
          <span className="flex items-center gap-1.5">
            <Badge tone="amber">novel target</Badge> no known ChEMBL chemical matter
          </span>
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-[1.3fr_1fr]">
        <div>
          <div className="mb-1.5 text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-faint">
            Reproduce the public graph
          </div>
          <pre className="overflow-x-auto rounded-lg border border-line/10 bg-surface2/50 p-2.5 font-mono text-[0.7rem] leading-relaxed text-muted">
{`make db          # Postgres + pgvector
make seed-public # PubMLST + committed public caches
make backend     # FastAPI  :8000
make frontend    # Next.js  :3000`}
          </pre>
        </div>
        <div>
          <div className="mb-1.5 text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-faint">
            Public data only
          </div>
          <div className="flex flex-wrap gap-1.5">
            {["PubMLST", "Europe PMC", "CARD / ARO", "UniProt", "ChEMBL", "NCBI", "AlphaFold (Tamarind)", "RCSB"].map(
              (s) => (
                <span
                  key={s}
                  className="rounded-md bg-line/6 px-1.5 py-0.5 font-mono text-[0.64rem] text-muted"
                >
                  {s}
                </span>
              ),
            )}
          </div>
          <a
            href={REPO}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-3 inline-flex items-center gap-1.5 rounded-md bg-accent/10 px-2.5 py-1 text-[0.72rem] font-medium text-accentStrong ring-1 ring-inset ring-accent/25 transition hover:bg-accent/20"
          >
            <GitHub /> Source on GitHub · MIT
          </a>
        </div>
      </div>
    </Panel>
  );
}

function Pillar({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-xl border border-line/10 bg-surface2/30 p-3">
      <div className="text-[0.8rem] font-medium text-text">{title}</div>
      <div className="mt-1 text-[0.72rem] leading-relaxed text-muted">{body}</div>
    </div>
  );
}

function GitHub() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M12 .5C5.73.5.5 5.73.5 12a11.5 11.5 0 0 0 7.86 10.92c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.54-3.88-1.54-.53-1.34-1.29-1.7-1.29-1.7-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.2 1.77 1.2 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.73-1.55-2.56-.29-5.26-1.28-5.26-5.7 0-1.26.45-2.29 1.19-3.1-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.18 1.18a11 11 0 0 1 5.8 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.84 1.19 3.1 0 4.43-2.7 5.4-5.28 5.69.42.36.79 1.06.79 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 23.5 12C23.5 5.73 18.27.5 12 .5z" />
    </svg>
  );
}
