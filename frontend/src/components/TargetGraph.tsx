"use client";
// Ranked candidate targets for the selected strain. The rank_score is computed
// deterministically server-side (ingestion/scoring.py); this panel only renders it as
// a bar, alongside the gene's mechanism, ChEMBL tractability signal, a citation-backed
// rationale, and a link to fold/view its structure. Selecting nothing still shows the
// organism-level ranking so the panel never dead-ends.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { clsx } from "@/lib/clsx";
import { Panel, Badge } from "./ui";
import type { GeneSelection } from "./StrainDetail";
import type { RankedTarget, TargetsResponse } from "@/lib/types";

const ORGANISM = "Burkholderia multivorans";

export function TargetGraph({
  strainId,
  selectedLocus,
  onViewStructure,
}: {
  strainId: string | null;
  selectedLocus?: string | null;
  onViewStructure?: (sel: GeneSelection) => void;
}) {
  const [data, setData] = useState<TargetsResponse | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "empty" | "error">("loading");

  useEffect(() => {
    let live = true;
    setStatus("loading");
    setData(null);
    api
      .targets(strainId, ORGANISM)
      .then((d) => {
        if (!live) return;
        setData(d);
        setStatus(d.targets.length ? "ready" : "empty");
      })
      .catch(() => live && setStatus("error"));
    return () => {
      live = false;
    };
  }, [strainId]);

  const counts = data?.counts;

  return (
    <Panel
      title="Targets"
      aside={
        counts ? (
          <span className="flex items-center gap-1.5">
            <Badge tone="accent">{counts.targets} ranked</Badge>
            {counts.with_structure > 0 && (
              <Badge tone="neutral">{counts.with_structure} with structure</Badge>
            )}
          </span>
        ) : (
          <span className="font-mono text-[0.68rem] text-faint">deterministic rank · cited</span>
        )
      }
    >
      {status === "loading" && (
        <div className="space-y-2">
          <div className="skeleton h-24 rounded-xl" />
          <div className="skeleton h-24 rounded-xl" />
          <div className="skeleton h-24 rounded-xl" />
        </div>
      )}
      {status === "error" && (
        <Empty>Target service offline — start the API (`make backend`) and retry.</Empty>
      )}
      {status === "empty" && (
        <Empty>
          No ranked targets yet. Seed the evidence graph (`make seed`) so genes with
          grounded literature support can be promoted to candidate targets.
        </Empty>
      )}
      {status === "ready" && data && (
        <div className="animate-fade">
          <p className="mb-3 text-[0.72rem] leading-relaxed text-muted">
            Candidate targets for{" "}
            <span className="text-text">{data.strain ? `strain ${data.strain.label}` : data.organism}</span>
            , ranked by a deterministic 0–1 score over grounded evidence and flipper
            strength. Chips carried by the strain are marked.
          </p>
          <ul className="space-y-2.5">
            {data.targets.map((t) => (
              <TargetCard
                key={t.id ?? t.locus_tag}
                t={t}
                selected={!!selectedLocus && selectedLocus === t.locus_tag}
                onViewStructure={onViewStructure}
              />
            ))}
          </ul>
        </div>
      )}
    </Panel>
  );
}

function TargetCard({
  t,
  selected,
  onViewStructure,
}: {
  t: RankedTarget;
  selected: boolean;
  onViewStructure?: (sel: GeneSelection) => void;
}) {
  const score = t.rank_score ?? 0;
  const label = t.name ? `${t.name} (${t.locus_tag})` : (t.locus_tag ?? "gene");
  return (
    <li
      className={clsx(
        "rounded-xl border p-3 transition",
        selected ? "border-accent/40 bg-accent/[0.05]" : "border-line/10 bg-surface2/30",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="font-mono text-sm text-text">{t.name ?? t.locus_tag}</span>
            {t.name && <span className="font-mono text-[0.66rem] text-faint">{t.locus_tag}</span>}
            {t.strain_flipper ? (
              <Badge tone="accent">flipper here</Badge>
            ) : t.in_strain ? (
              <Badge tone="neutral">carried</Badge>
            ) : null}
          </div>
          {t.mechanism && (
            <div className="mt-0.5 truncate text-[0.72rem] text-muted">{t.mechanism}</div>
          )}
        </div>
        <TractabilityChip t={t} />
      </div>

      <ScoreBar value={score} components={t.score_components} />

      <p className="mt-2 text-[0.74rem] leading-relaxed text-muted">{t.rationale}</p>

      {(t.rationale_citations?.length ?? 0) > 0 && (
        <div className="mt-1.5 flex flex-wrap items-center gap-1">
          {t.rationale_citations.map((c) => (
            <Citation key={c} id={c} />
          ))}
          <span className="ml-0.5 text-[0.6rem] uppercase tracking-wide text-faint">
            {t.rationale_source === "llm" ? "narrated" : "computed"}
          </span>
        </div>
      )}

      <div className="mt-2.5 flex items-center justify-between gap-2">
        <span className="text-[0.66rem] text-faint">
          {t.evidence_counts.grounded}/{t.evidence_counts.total} edges grounded
        </span>
        {t.structure.available && onViewStructure && (
          <button
            type="button"
            onClick={() => onViewStructure({ locus: t.locus_tag as string, label })}
            className="inline-flex items-center gap-1 rounded-md bg-accent/10 px-2 py-1 text-[0.66rem] font-medium text-accentStrong ring-1 ring-inset ring-accent/25 transition hover:bg-accent/20"
          >
            <Cube /> View structure
          </button>
        )}
      </div>
    </li>
  );
}

function ScoreBar({
  value,
  components,
}: {
  value: number;
  components: RankedTarget["score_components"];
}) {
  const ev = components?.evidence ?? null;
  const fl = components?.flipper ?? null;
  const title = ev !== null || fl !== null ? `evidence ${ev ?? 0} · flipper ${fl ?? 0}` : undefined;
  return (
    <div className="mt-2 flex items-center gap-2" title={title}>
      <span className="w-14 shrink-0 text-[0.6rem] uppercase tracking-wide text-faint">rank</span>
      <span className="relative h-2 flex-1 overflow-hidden rounded-full bg-line/10">
        <span
          className="absolute inset-y-0 left-0 rounded-full"
          style={{
            width: `${Math.round(value * 100)}%`,
            background: `color-mix(in oklab, rgb(var(--accent)) ${45 + value * 55}%, rgb(var(--surface-3)))`,
          }}
        />
      </span>
      <span className="w-8 shrink-0 text-right font-mono text-[0.68rem] text-text">
        {value.toFixed(2)}
      </span>
    </div>
  );
}

function TractabilityChip({ t }: { t: RankedTarget }) {
  const tr = t.tractability;
  if (!tr || !tr.assessed) {
    return <Badge tone="neutral">tractability n/a</Badge>;
  }
  if (tr.has_target === false) {
    return (
      <Badge tone="amber" className="shrink-0">
        novel target
      </Badge>
    );
  }
  if (tr.bucket === "precedented") {
    return (
      <Badge tone="accent" className="shrink-0">
        drugged
      </Badge>
    );
  }
  return (
    <Badge tone="neutral" className="shrink-0">
      {tr.n_bioactivities ? `${tr.n_bioactivities} bioactivities` : "ChEMBL"}
    </Badge>
  );
}

function Citation({ id }: { id: string }) {
  const pmid = id.startsWith("PMID:") ? id.slice(5) : null;
  const isRef = id.includes(":") && !pmid;
  const href = pmid ? `https://pubmed.ncbi.nlm.nih.gov/${pmid}/` : undefined;
  const cls =
    "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 font-mono text-[0.6rem] ring-1 ring-inset " +
    (isRef
      ? "bg-accent/10 text-accentStrong ring-accent/25"
      : "bg-line/6 text-muted ring-line/15 hover:text-text");
  if (href) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className={cls}>
        {id}
      </a>
    );
  }
  return <span className={cls}>{id}</span>;
}

function Empty({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-[9rem] items-center justify-center rounded-xl border border-dashed border-line/15 bg-surface2/40 px-4 text-center">
      <p className="max-w-sm text-xs leading-relaxed text-muted">{children}</p>
    </div>
  );
}

function Cube() {
  return (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
      <path d="m3.3 7 8.7 5 8.7-5M12 22V12" />
    </svg>
  );
}
