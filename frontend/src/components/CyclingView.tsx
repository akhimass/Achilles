"use client";
// Antibiotic-cycling suggestion. The cycle is computed server-side (deterministic
// collateral-sensitivity math over reciprocal 'flipper' pairs); the model only
// narrates it. Rendered as an alternating loop with its reciprocal-CS support and
// mandatory caveats. ALWAYS a research hypothesis — never a treatment recommendation.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Panel, Badge } from "./ui";
import type { CycleResponse } from "@/lib/types";

export function CyclingView({ organism }: { organism: string }) {
  const [data, setData] = useState<CycleResponse | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "empty" | "error">("loading");

  useEffect(() => {
    let live = true;
    setStatus("loading");
    setData(null);
    api
      .cycle(organism)
      .then((d) => {
        if (!live) return;
        setData(d);
        setStatus(d.cycle.length ? "ready" : "empty");
      })
      .catch(() => live && setStatus("error"));
    return () => {
      live = false;
    };
  }, [organism]);

  const counts = data?.counts;

  return (
    <Panel
      title="Cycling"
      aside={
        <span className="flex items-center gap-1.5">
          {counts && <Badge tone="neutral">{counts.reciprocal} RCS pairs</Badge>}
          <Badge tone="amber">research hypothesis</Badge>
        </span>
      }
    >
      {status === "loading" && (
        <div className="space-y-3">
          <div className="skeleton h-16 rounded-xl" />
          <div className="skeleton h-10 rounded-lg" />
          <div className="skeleton h-10 rounded-lg" />
        </div>
      )}
      {status === "error" && (
        <Empty>Treatment service offline — start the API (`make backend`) and retry.</Empty>
      )}
      {status === "empty" && <CyclingEmpty />}
      {status === "ready" && data && (
        <div className="animate-fade">
          <CycleLoop cycle={data.cycle} />

          <p className="mt-3 text-[0.78rem] leading-relaxed text-text">
            {data.narrative?.summary ?? data.summary}
          </p>

          {data.rcs_pairs.length > 0 && (
            <div className="mt-3">
              <div className="mb-1.5 text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-faint">
                Reciprocal collateral sensitivity
              </div>
              <p className="mb-1.5 text-[0.68rem] leading-relaxed text-muted">
                Each hop is a reversion <span className="text-text">observed in real
                lineages</span> (see &ldquo;What real evolution did next&rdquo; above) — the
                cycle is the actionable output of that retrieved reality, not a prediction.
              </p>
              <ul className="flex flex-wrap gap-1.5">
                {data.rcs_pairs.slice(0, 8).map((p) => (
                  <li
                    key={`${p.drug_a}-${p.drug_b}`}
                    className="inline-flex items-center gap-1 rounded-md border border-line/12 bg-surface2/40 px-1.5 py-0.5 font-mono text-[0.64rem] text-muted"
                    title={`${p.n_lineages ?? 0} lineages of support`}
                  >
                    <span className="text-text">{p.drug_a}</span>
                    <Swap />
                    <span className="text-text">{p.drug_b}</span>
                    {p.n_lineages ? <span className="text-faint">·{p.n_lineages}</span> : null}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <Caveats items={data.caveats} />

          {data.narrative?.citations && data.narrative.citations.length > 0 && (
            <div className="mt-2 flex flex-wrap items-center gap-1">
              <span className="text-[0.6rem] uppercase tracking-wide text-faint">cites</span>
              {data.narrative.citations.map((c) => (
                <span
                  key={c}
                  className="rounded-md bg-line/6 px-1.5 py-0.5 font-mono text-[0.6rem] text-muted ring-1 ring-inset ring-line/15"
                >
                  {c}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}

function CycleLoop({ cycle }: { cycle: string[] }) {
  return (
    <div className="rounded-xl border border-dashed border-line/12 bg-surface2/30 px-3 py-4">
      <div className="flex flex-wrap items-center justify-center gap-1.5">
        {cycle.map((drug, i) => (
          <span key={`${drug}-${i}`} className="flex items-center gap-1.5">
            <span className="rounded-md border border-accent/25 bg-accent/[0.06] px-2.5 py-1 font-mono text-xs font-medium text-text">
              {drug}
            </span>
            {i < cycle.length - 1 && <Arrow />}
          </span>
        ))}
        {cycle.length > 1 && (
          <span className="flex items-center gap-1.5">
            <Loop />
            <span className="font-mono text-[0.62rem] text-faint">repeat</span>
          </span>
        )}
      </div>
    </div>
  );
}

function Caveats({ items }: { items: string[] }) {
  if (!items?.length) return null;
  return (
    <div className="mt-3 rounded-lg border border-amber/25 bg-amber/[0.06] p-2.5">
      <div className="mb-1 flex items-center gap-1.5 text-[0.66rem] font-semibold text-amber">
        <Warn /> Caveats — hypothesis only
      </div>
      <ul className="space-y-1">
        {items.map((c, i) => (
          <li key={i} className="flex gap-1.5 text-[0.7rem] leading-relaxed text-muted">
            <span className="mt-[0.3rem] h-1 w-1 shrink-0 rounded-full bg-amber/60" />
            {c}
          </li>
        ))}
      </ul>
    </div>
  );
}

// Informative empty state for the public path — the cycle is computed from
// experimental-evolution resistance/sensitivity data (shown in the local demo), so on
// the public PubMLST deployment there's no cycle to draw. Explain the idea, don't blank.
function CyclingEmpty() {
  return (
    <div className="rounded-xl border border-dashed border-line/15 bg-surface2/40 p-4">
      <div className="grid place-items-center rounded-lg border border-dashed border-line/12 bg-surface/40 px-3 py-5">
        <div className="flex items-center gap-3 opacity-70">
          <span className="rounded-md border border-line/15 bg-surface px-2.5 py-1 font-mono text-xs text-text">A</span>
          <svg width="56" height="30" viewBox="0 0 56 30" aria-hidden>
            <path d="M6 9 H46 M42 5.5 L48 9 L42 12.5" stroke="rgb(var(--accent))" strokeWidth="1.3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M50 21 H10 M14 17.5 L8 21 L14 24.5" stroke="rgb(var(--accent))" strokeWidth="1.3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
            <text x="28" y="4.5" textAnchor="middle" fontSize="6" fill="rgb(var(--faint))">sensitizes</text>
            <text x="28" y="29" textAnchor="middle" fontSize="6" fill="rgb(var(--faint))">sensitizes</text>
          </svg>
          <span className="rounded-md border border-line/15 bg-surface px-2.5 py-1 font-mono text-xs text-text">B</span>
        </div>
      </div>
      <p className="mt-3 text-[0.78rem] leading-relaxed text-muted">
        Cycling walks a{" "}
        <span className="text-text">reciprocal collateral-sensitivity</span> graph:
        when resistance to drug A comes with sensitivity to B (and back), alternating
        them is hypothesized to keep resistance from fixing. That graph is computed —
        deterministically — from <span className="text-text">per-lineage
        resistance/sensitivity transitions</span> measured in an experimental-evolution
        record.
      </p>
      <p className="mt-2 text-[0.78rem] leading-relaxed text-muted">
        This public deployment is seeded from PubMLST, which carries no such
        resistance/sensitivity measurements — so there is no cycle to draw here, and
        that&rsquo;s shown honestly rather than filled with placeholder data. The full
        cycle (e.g. <span className="font-mono text-text">SXT → MEM → CAZ → CHL</span>)
        appears in the local demo, which loads the experimental record.
      </p>
    </div>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-[9rem] items-center justify-center rounded-xl border border-dashed border-line/15 bg-surface2/40 px-4 text-center">
      <p className="max-w-sm text-xs leading-relaxed text-muted">{children}</p>
    </div>
  );
}

function Arrow() {
  return (
    <svg width="20" height="10" viewBox="0 0 20 10" aria-hidden>
      <path
        d="M2 5 H16 M13 2 L18 5 L13 8"
        stroke="rgb(var(--accent))"
        strokeWidth="1.3"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function Loop() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgb(var(--faint))" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M17 2.1 21 6l-4 3.9" />
      <path d="M3 12a9 9 0 0 1 9-9h9" />
      <path d="M7 21.9 3 18l4-3.9" />
      <path d="M21 12a9 9 0 0 1-9 9H3" />
    </svg>
  );
}

function Warn() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <path d="M12 9v4M12 17h.01" />
    </svg>
  );
}

function Swap() {
  return (
    <svg width="12" height="8" viewBox="0 0 24 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className="opacity-60" aria-hidden>
      <path d="M4 5h16M17 2l3 3-3 3" />
      <path d="M20 11H4M7 8l-3 3 3 3" />
    </svg>
  );
}
