"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { clsx } from "@/lib/clsx";
import { Panel, SectionLabel, Badge } from "./ui";
import type { LineageNode, StrainGene, StrainDetail as StrainDetailData } from "@/lib/types";

export type GeneSelection = { locus: string; label: string } | null;

export function StrainDetail({
  node,
  maxFlip,
  onClear,
  selectedGene,
  onSelectGene,
}: {
  node: LineageNode | null;
  maxFlip: number;
  onClear: () => void;
  selectedGene: GeneSelection;
  onSelectGene: (g: GeneSelection) => void;
}) {
  const [detail, setDetail] = useState<StrainDetailData | null>(null);

  useEffect(() => {
    if (!node) {
      setDetail(null);
      return;
    }
    let live = true;
    setDetail(null);
    api.strain(node.id).then((d) => live && setDetail(d)).catch(() => {});
    return () => {
      live = false;
    };
  }, [node]);

  if (!node) {
    return (
      <Panel title="Selection">
        <div className="flex min-h-[9rem] flex-col items-center justify-center text-center">
          <Cursor />
          <div className="mt-2 text-sm font-medium text-text">No strain selected</div>
          <p className="mt-1 max-w-[15rem] text-xs leading-relaxed text-muted">
            Click a node in the lineage to inspect its lineage, collateral profile, and
            flipper genes.
          </p>
        </div>
      </Panel>
    );
  }

  const meta = (detail?.strain?.metadata ?? {}) as Record<string, unknown>;
  const resistance = (meta.resistance as string[]) ?? [];
  const sensitivity = (meta.sensitivity as string[]) ?? [];
  const genes = detail?.genes ?? [];
  const flipperGenes = genes.filter((g) => g.is_flipper);
  const fc = node.flipper_count;
  const segments = Math.max(maxFlip, 1);

  return (
    <Panel
      title="Selection"
      aside={
        <button onClick={onClear} className="rounded-md px-1.5 py-0.5 text-[0.68rem] text-faint transition hover:text-text">
          clear
        </button>
      }
    >
      <div className="animate-fade">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-mono text-lg font-medium text-text">{node.label}</span>
            {node.founder && <Badge tone="accent">founder</Badge>}
          </div>
          {node.lineage && (
            <span className="rounded-md bg-line/6 px-1.5 py-0.5 font-mono text-xs text-muted">
              {node.lineage}
            </span>
          )}
        </div>

        {(resistance.length > 0 || sensitivity.length > 0) && (
          <div className="mt-4">
            <SectionLabel>Collateral profile</SectionLabel>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {resistance.map((d) => (
                <span key={d} className="rounded-md bg-danger/12 px-1.5 py-0.5 font-mono text-[0.68rem] text-danger ring-1 ring-inset ring-danger/25" title="resistant to">
                  R·{d}
                </span>
              ))}
              {sensitivity.map((d) => (
                <span key={d} className="rounded-md bg-accent/12 px-1.5 py-0.5 font-mono text-[0.68rem] text-accentStrong ring-1 ring-inset ring-accent/25" title="sensitive to">
                  S·{d}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="mt-4">
          <div className="flex items-center justify-between">
            <SectionLabel>Flipper load</SectionLabel>
            <span className="font-mono text-sm text-text">
              {fc}
              <span className="text-faint">/{segments}</span>
            </span>
          </div>
          <div className="mt-2 flex gap-[3px]">
            {Array.from({ length: Math.min(segments, 30) }).map((_, i) => {
              const filled = i < Math.round((fc / segments) * Math.min(segments, 30));
              return (
                <div
                  key={i}
                  className="h-2 flex-1 rounded-full"
                  style={{
                    background: filled
                      ? `color-mix(in oklab, rgb(var(--accent)) ${45 + (i / 30) * 55}%, rgb(var(--surface-3)))`
                      : "rgb(var(--line) / 0.1)",
                  }}
                />
              );
            })}
          </div>
        </div>

        <div className="mt-4">
          <div className="mb-1.5 flex items-center justify-between">
            <SectionLabel>Flipper genes</SectionLabel>
            <span className="text-[0.68rem] text-faint">{flipperGenes.length} · click to fold</span>
          </div>
          {detail === null ? (
            <div className="space-y-1.5">
              <div className="skeleton h-8 rounded-lg" />
              <div className="skeleton h-8 rounded-lg" />
            </div>
          ) : (
            <ul className="max-h-56 space-y-1 overflow-y-auto pr-1">
              {flipperGenes.slice(0, 24).map((g) => (
                <GeneRow
                  key={g.locus_tag}
                  gene={g}
                  selected={selectedGene?.locus === g.locus_tag}
                  onClick={() =>
                    onSelectGene({
                      locus: g.locus_tag,
                      label: g.gene_symbol ? `${g.gene_symbol} (${g.locus_tag})` : g.locus_tag,
                    })
                  }
                />
              ))}
            </ul>
          )}
        </div>
      </div>
    </Panel>
  );
}

function GeneRow({ gene, selected, onClick }: { gene: StrainGene; selected: boolean; onClick: () => void }) {
  return (
    <li>
      <button
        onClick={onClick}
        className={clsx(
          "flex w-full items-center gap-2 rounded-lg border px-2 py-1.5 text-left transition",
          selected
            ? "border-accent/40 bg-accent/[0.08]"
            : "border-transparent hover:border-line/12 hover:bg-surface2/60",
        )}
      >
        <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
        <span className="min-w-0 flex-1">
          <span className="font-mono text-xs text-text">
            {gene.gene_symbol ?? gene.locus_tag}
          </span>
          {gene.product && (
            <span className="block truncate text-[0.68rem] text-muted">{gene.product}</span>
          )}
        </span>
        {gene.effect === "frameshift" && (
          <span className="shrink-0 rounded bg-amber/12 px-1 py-0.5 font-mono text-[0.56rem] text-amber">
            fs
          </span>
        )}
        <span className="shrink-0 font-mono text-[0.66rem] text-faint">
          {gene.indel_delta != null && gene.indel_delta > 0 ? `+${gene.indel_delta}` : gene.indel_delta}
        </span>
      </button>
    </li>
  );
}

function Cursor() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="rgb(var(--faint))" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 3l6 18 2-7 7-2z" />
    </svg>
  );
}
