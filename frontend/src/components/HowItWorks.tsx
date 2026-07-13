"use client";
import { Panel, Badge } from "./ui";

const REPO = "https://github.com/akhimass/Achilles";

export function HowItWorks() {
  return (
    <Panel title="Methods & reproducibility">
      <div className="space-y-4 text-[0.85rem] leading-relaxed text-muted">
        <p>
          A <span className="text-text">deterministic Python core</span> computes lineage,
          flippers, target <span className="font-mono text-text">rank_score</span>, and
          collateral-sensitivity structure. The language model extracts typed claims from
          literature and narrates already-computed results with citations — it never invents
          a number or schedule.
        </p>
        <p>
          Every edge carries provenance (PMID and, where corroborated, CARD / UniProt /
          ChEMBL). Ungrounded claims do not become edges.
        </p>
      </div>

      <div className="mt-4 rounded-lg border border-line/10 bg-surface2/40 p-3">
        <div className="mb-2 text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-faint">
          Provenance legend
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[0.75rem] text-muted">
          <span className="flex items-center gap-1.5">
            <Badge tone="accent">grounded</Badge> PMID + reference-DB
          </span>
          <span className="flex items-center gap-1.5">
            <Badge tone="amber">abstract-only</Badge> PMID, not yet corroborated
          </span>
        </div>
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-[1.3fr_1fr]">
        <div>
          <div className="mb-1.5 text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-faint">
            Reproduce
          </div>
          <pre className="overflow-x-auto rounded-md border border-line/10 bg-surface2/50 p-2.5 font-mono text-[0.7rem] leading-relaxed text-muted">
{`make db
make seed-public
make backend
make frontend`}
          </pre>
        </div>
        <div>
          <div className="mb-1.5 text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-faint">
            Sources
          </div>
          <div className="flex flex-wrap gap-1.5">
            {["PubMLST", "Europe PMC", "CARD", "UniProt", "ChEMBL", "NCBI", "AlphaFold"].map(
              (s) => (
                <span key={s} className="font-mono text-[0.64rem] text-muted">
                  {s}
                </span>
              ),
            )}
          </div>
          <a
            href={REPO}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-3 inline-block text-[0.75rem] font-medium text-accentStrong hover:underline"
          >
            Source on GitHub · MIT
          </a>
        </div>
      </div>
    </Panel>
  );
}
