"use client";
// Evidence for the selected flipper gene: every edge with its provenance (a PMID
// and, where corroborated, a CARD/UniProt accession) and a confidence gradient —
// the "provenance on every edge" promise made visible. Grounded edges look solid;
// abstract-only edges are clearly weaker and honestly labelled.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { clsx } from "@/lib/clsx";
import { Panel, Badge, SectionLabel } from "./ui";
import type { GeneSelection } from "./StrainDetail";
import type { EvidenceSubgraph, EvidenceEdgeView, Relation } from "@/lib/types";

const RELATION_LABEL: Record<Relation, string> = {
  confers_resistance: "confers resistance to",
  sensitizes_to: "sensitizes to",
  is_target_of: "is target of",
  implicates: "implicates",
  reverts_with: "reverts with",
};

export function EvidencePanel({ gene }: { gene: GeneSelection }) {
  const [data, setData] = useState<EvidenceSubgraph | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "empty" | "error">("idle");

  useEffect(() => {
    if (!gene) {
      setStatus("idle");
      setData(null);
      return;
    }
    let live = true;
    setStatus("loading");
    setData(null);
    api
      .geneEvidence(gene.locus)
      .then((d) => {
        if (!live) return;
        setData(d);
        setStatus(d.edges.length ? "ready" : "empty");
      })
      .catch(() => live && setStatus("error"));
    return () => {
      live = false;
    };
  }, [gene]);

  const counts = data?.counts;

  return (
    <Panel
      title="Evidence"
      aside={
        counts ? (
          <span className="flex items-center gap-1.5">
            <Badge tone="accent">{counts.grounded} grounded</Badge>
            {counts.total - counts.grounded > 0 && (
              <Badge tone="amber">{counts.total - counts.grounded} abstract-only</Badge>
            )}
          </span>
        ) : (
          <span className="font-mono text-[0.68rem] text-faint">provenance on every edge</span>
        )
      }
    >
      {status === "idle" && (
        <Empty>Select a flipper gene to see grounded resistance evidence.</Empty>
      )}
      {status === "loading" && (
        <div className="space-y-2">
          <div className="skeleton h-14 rounded-lg" />
          <div className="skeleton h-14 rounded-lg" />
          <div className="skeleton h-14 rounded-lg" />
        </div>
      )}
      {status === "error" && <Empty>Evidence service offline — start the API and retry.</Empty>}
      {status === "empty" && (
        <Empty>
          No grounded literature evidence for{" "}
          <span className="font-mono text-text">{gene?.label ?? gene?.locus}</span> yet. The
          corpus is scoped to a handful of resistance-relevant families.
        </Empty>
      )}
      {status === "ready" && data && (
        <div className="animate-fade">
          <div className="mb-3 flex items-baseline gap-2">
            <span className="font-mono text-sm text-text">
              {data.gene.symbol ?? data.gene.locus_tag}
            </span>
            {data.gene.product && (
              <span className="truncate text-xs text-muted">{data.gene.product}</span>
            )}
          </div>
          <ul className="max-h-[26rem] space-y-2 overflow-y-auto pr-1">
            {data.edges.map((e, i) => (
              <EdgeRow key={e.id ?? i} edge={e} />
            ))}
          </ul>
        </div>
      )}
    </Panel>
  );
}

function EdgeRow({ edge }: { edge: EvidenceEdgeView }) {
  const p = edge.provenance;
  return (
    <li
      className={clsx(
        "rounded-xl border p-3 transition",
        edge.grounded ? "border-accent/25 bg-accent/[0.04]" : "border-line/10 bg-surface2/30",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm leading-snug text-text">
            <span className="text-muted">{RELATION_LABEL[edge.relation] ?? edge.relation}</span>{" "}
            <span className="font-medium">{edge.target}</span>
          </div>
          {edge.subject && (
            <div className="mt-0.5 text-[0.68rem] text-faint">
              as <span className="font-mono">{edge.subject}</span>
              {edge.target_type ? ` · ${edge.target_type}` : ""}
            </div>
          )}
        </div>
        {edge.grounded ? (
          <Badge tone="accent">
            <Check /> grounded
          </Badge>
        ) : (
          <Badge tone="amber">abstract-only</Badge>
        )}
      </div>

      <ConfidenceBar value={edge.confidence} grounded={edge.grounded} />

      {edge.evidence_span && (
        <p className="mt-2 border-l-2 border-line/15 pl-2 text-[0.72rem] italic leading-snug text-muted">
          &ldquo;{edge.evidence_span}&rdquo;
        </p>
      )}

      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        {p.pmid && (
          <ProvChip href={p.pubmed_url} title={p.paper_title ?? undefined} tone="pmid">
            PMID {p.pmid}
            {p.paper_year ? ` · ${p.paper_year}` : ""}
          </ProvChip>
        )}
        {p.acc && (
          <ProvChip href={p.ref_url} tone="ref">
            {p.db} {p.acc}
          </ProvChip>
        )}
      </div>
    </li>
  );
}

function ConfidenceBar({ value, grounded }: { value: number; grounded: boolean }) {
  return (
    <div className="mt-2 flex items-center gap-2">
      <span className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-line/10">
        <span
          className="absolute inset-y-0 left-0 rounded-full"
          style={{
            width: `${Math.round(value * 100)}%`,
            background: grounded
              ? `color-mix(in oklab, rgb(var(--accent)) ${55 + value * 45}%, rgb(var(--surface-3)))`
              : "rgb(var(--amber) / 0.6)",
          }}
        />
      </span>
      <span className="w-8 shrink-0 text-right font-mono text-[0.66rem] text-faint">
        {value.toFixed(2)}
      </span>
    </div>
  );
}

function ProvChip({
  href,
  title,
  tone,
  children,
}: {
  href?: string | null;
  title?: string;
  tone: "pmid" | "ref";
  children: React.ReactNode;
}) {
  const cls = clsx(
    "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 font-mono text-[0.62rem] ring-1 ring-inset transition",
    tone === "ref"
      ? "bg-accent/10 text-accentStrong ring-accent/25 hover:bg-accent/20"
      : "bg-line/6 text-muted ring-line/15 hover:text-text hover:ring-line/30",
  );
  if (!href) return <span className={cls}>{children}</span>;
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" title={title} className={cls}>
      {children}
      <External />
    </a>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-[8rem] items-center justify-center rounded-xl border border-dashed border-line/15 bg-surface2/40 px-4 text-center">
      <p className="max-w-sm text-xs leading-relaxed text-muted">{children}</p>
    </div>
  );
}

function Check() {
  return (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}

function External() {
  return (
    <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="opacity-60">
      <path d="M7 17 17 7M8 7h9v9" />
    </svg>
  );
}
