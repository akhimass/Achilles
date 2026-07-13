"use client";
import type { LineageStatus, Overview } from "@/lib/useLineage";

const ORGANISM = "Burkholderia multivorans";

export function Hero({
  overview,
  status,
}: {
  overview: Overview | null;
  status: LineageStatus;
}) {
  const hasLineages = (overview?.lineages.length ?? 0) > 0;

  return (
    <section className="grid gap-6 lg:grid-cols-[1.2fr_1fr] lg:items-end">
      <div>
        <p className="text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-faint">
          Active cohort
        </p>
        <h1 className="mt-1.5 font-serif text-[1.75rem] font-medium tracking-tight text-text sm:text-[2.1rem]">
          <em className="not-italic">{ORGANISM}</em>
        </h1>
        <p className="mt-3 max-w-xl text-[0.9rem] leading-relaxed text-muted">
          {hasLineages
            ? "Experimental-evolution record: isolates along parallel lineages, with per-gene indel flippers and per-lineage resistance / sensitivity."
            : "Public isolates from PubMLST, with reversible MLST loci and resistance-gene families grounded to literature (PMID + CARD / UniProt)."}
        </p>
      </div>

      <dl className="grid grid-cols-3 gap-4 rounded-lg border border-line/12 bg-surface/60 px-4 py-3.5">
        <Stat label="Isolates" value={overview?.strains} loading={status === "loading"} />
        <Stat
          label="Flipper-carrying"
          value={overview?.flipperCarriers}
          loading={status === "loading"}
          accent
        />
        <Stat
          label={hasLineages ? "Lineages" : "Countries"}
          value={hasLineages ? overview?.lineages.length : overview?.countries.length}
          loading={status === "loading"}
        />
      </dl>
    </section>
  );
}

function Stat({
  label,
  value,
  loading,
  accent,
}: {
  label: string;
  value?: number;
  loading?: boolean;
  accent?: boolean;
}) {
  return (
    <div>
      <dt className="text-[0.65rem] text-faint">{label}</dt>
      <dd
        className={`mt-0.5 font-mono text-xl tabular-nums ${
          accent ? "text-accentStrong" : "text-text"
        }`}
      >
        {loading || value == null ? "—" : value}
      </dd>
    </div>
  );
}
