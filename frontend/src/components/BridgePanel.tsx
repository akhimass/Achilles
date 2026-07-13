"use client";
// The bridge — one grounded finding, shown to a researcher and a physician at once.
// LEFT is target identification (mechanism, ranked target, structure); RIGHT is the
// clinical translation (drugs it drives resistance to, the cited collateral-sensitivity
// opening, a cycling hypothesis). The connector in the middle IS the point: the same
// provenance carries from bench to bedside. Nothing here is generated — every chip links
// to a PMID or reference-DB accession, and the clinical side always wears its caveats.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { BridgeResponse, BridgeCitation } from "@/lib/types";

export function BridgePanel({ gene }: { gene: string }) {
  const [data, setData] = useState<BridgeResponse | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let live = true;
    setStatus("loading");
    setData(null);
    api
      .bridge(gene)
      .then((d) => {
        if (!live) return;
        setData(d);
        setStatus("ready");
      })
      .catch(() => live && setStatus("error"));
    return () => {
      live = false;
    };
  }, [gene]);

  if (status === "loading") return <div className="skeleton h-72 rounded-2xl" />;
  if (status === "error")
    return (
      <div className="rounded-2xl border border-line/12 bg-surface2/40 p-5 text-sm text-muted">
        Bridge offline — load the demo dataset (or start the API) and retry.
      </div>
    );
  if (!data || !data.found || !data.research || !data.clinic)
    return (
      <div className="rounded-2xl border border-line/12 bg-surface2/40 p-5 text-sm text-muted">
        {data?.reason ?? "No grounded finding to translate for this gene."}
      </div>
    );

  const { research, clinic } = data;

  return (
    <div className="animate-fade">
      <div className="grid gap-4 lg:grid-cols-[1fr_auto_1fr] lg:items-stretch">
        {/* Researcher lens */}
        <div className="rounded-2xl border border-line/12 bg-surface2/30 p-4">
          <LensHead label={research.lens} who="Researcher" />
          <div className="mt-2">
            <span className="font-mono text-[0.9rem] text-text">{research.gene.name}</span>
            {research.gene.locus && (
              <span className="ml-1.5 font-mono text-[0.62rem] text-faint">
                {research.gene.locus}
              </span>
            )}
            <p className="mt-1 text-[0.78rem] leading-relaxed text-muted">{research.summary}</p>
          </div>

          {research.target && (
            <div className="mt-3 rounded-xl border border-accent/20 bg-accent/[0.05] p-2.5">
              <div className="flex items-center justify-between">
                <span className="text-[0.62rem] uppercase tracking-wide text-faint">
                  Ranked target
                </span>
                {typeof research.target.rank_score === "number" && (
                  <span className="font-mono text-sm text-accentStrong">
                    {research.target.rank_score.toFixed(2)}
                  </span>
                )}
              </div>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {research.target.tractability_bucket && (
                  <Tag>{research.target.tractability_bucket}</Tag>
                )}
                {research.target.structure_available && <Tag>AlphaFold structure</Tag>}
              </div>
            </div>
          )}

          <div className="mt-3">
            <div className="mb-1 text-[0.62rem] uppercase tracking-wide text-faint">
              Grounded evidence
            </div>
            <ul className="space-y-1.5">
              {research.grounded_claims.map((c, i) => (
                <li key={i} className="flex items-start justify-between gap-2 text-[0.74rem]">
                  <span className="text-muted">
                    <span className="text-faint">{c.relation.replace(/_/g, " ")}</span>{" "}
                    <span className="text-text">{c.target}</span>
                  </span>
                  <Cite c={c.citation} />
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Handoff connector */}
        <div className="flex flex-row items-center justify-center gap-2 lg:flex-col">
          <div className="hidden h-full w-px bg-gradient-to-b from-accent/10 via-accent/50 to-accent/10 lg:block" />
          <div className="grid place-items-center rounded-full border border-accent/30 bg-accent/10 p-2 text-accentStrong">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M4 12h16M14 6l6 6-6 6" />
            </svg>
          </div>
          <div className="hidden h-full w-px bg-gradient-to-b from-accent/10 via-accent/50 to-accent/10 lg:block" />
        </div>

        {/* Physician lens */}
        <div className="rounded-2xl border border-line/12 bg-surface2/30 p-4">
          <LensHead label={clinic.lens} who="Physician" />

          <div className="mt-2">
            <div className="text-[0.62rem] uppercase tracking-wide text-faint">
              Drives resistance to
            </div>
            <div className="mt-1 flex flex-wrap gap-1.5">
              {clinic.drives_resistance_to.length ? (
                clinic.drives_resistance_to.map((d) => <Tag key={d}>{d}</Tag>)
              ) : (
                <span className="text-[0.74rem] text-faint">no grounded drug link yet</span>
              )}
            </div>
          </div>

          {clinic.cited_cycle && (
            <div className="mt-3 rounded-xl border border-accent/20 bg-accent/[0.05] p-2.5">
              <div className="mb-1 flex items-center justify-between">
                <span className="text-[0.62rem] uppercase tracking-wide text-faint">
                  Collateral-sensitivity strategy
                </span>
                <span className="rounded-full bg-amber/15 px-1.5 py-0.5 text-[0.56rem] font-semibold uppercase text-amber">
                  hypothesis
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-1">
                {clinic.cited_cycle.cycle.map((d, i) => (
                  <span key={`${d}-${i}`} className="flex items-center gap-1">
                    <span className="rounded-md border border-accent/25 bg-accent/[0.06] px-1.5 py-0.5 font-mono text-[0.66rem] text-text">
                      {d}
                    </span>
                    {i < clinic.cited_cycle!.cycle.length - 1 && (
                      <span className="text-faint">→</span>
                    )}
                  </span>
                ))}
                <span className="ml-0.5 font-mono text-[0.58rem] text-faint">↻</span>
              </div>
              {clinic.collateral_opening && (
                <div className="mt-1.5 flex items-center gap-1.5 text-[0.68rem] text-muted">
                  reciprocal opening: {clinic.collateral_opening.drug_a} ⇄{" "}
                  {clinic.collateral_opening.drug_b}
                  <Cite c={clinic.collateral_opening.citation} />
                </div>
              )}
            </div>
          )}

          <p className="mt-3 text-[0.76rem] leading-relaxed text-muted">{clinic.actionable}</p>
        </div>
      </div>

      {/* Handoff line + caveats */}
      <div className="mt-4 rounded-xl border border-accent/20 bg-accent/[0.04] px-4 py-2.5">
        <div className="flex items-center gap-2 text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-accentStrong">
          Handoff · {data.provenance_carried} citations carried
        </div>
        <p className="mt-1 text-[0.8rem] leading-relaxed text-text">{data.handoff}</p>
      </div>

      <div className="mt-2 rounded-lg border border-amber/25 bg-amber/[0.06] p-2.5">
        <ul className="space-y-1">
          {clinic.caveats.map((c, i) => (
            <li key={i} className="flex gap-1.5 text-[0.7rem] leading-relaxed text-muted">
              <span className="mt-[0.34rem] h-1 w-1 shrink-0 rounded-full bg-amber/60" />
              {c}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function LensHead({ label, who }: { label: string; who: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-accentStrong">
        {label}
      </span>
      <span className="rounded-full border border-line/12 bg-surface/60 px-2 py-0.5 text-[0.58rem] text-faint">
        {who}
      </span>
    </div>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-md border border-line/12 bg-surface/50 px-1.5 py-0.5 font-mono text-[0.62rem] text-muted">
      {children}
    </span>
  );
}

function Cite({ c }: { c: BridgeCitation }) {
  if (!c) return null;
  return c.url ? (
    <a
      href={c.url}
      target="_blank"
      rel="noopener noreferrer"
      className="shrink-0 rounded-md bg-accent/10 px-1.5 py-0.5 font-mono text-[0.58rem] text-accentStrong ring-1 ring-inset ring-accent/25 hover:brightness-110"
    >
      {c.label}
    </a>
  ) : (
    <span className="shrink-0 rounded-md bg-line/8 px-1.5 py-0.5 font-mono text-[0.58rem] text-muted">
      {c.label}
    </span>
  );
}
