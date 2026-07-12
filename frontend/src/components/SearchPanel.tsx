"use client";
// Grounded search over the whole evidence graph — papers, genes, and evidence edges —
// the retrieval DB the LLM (and a judge) can query. Every result carries its provenance
// (PMID / CARD / UniProt), so search returns sourced nodes, never an unsourced blob.
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { clsx } from "@/lib/clsx";
import { Panel, Badge } from "./ui";
import type { SearchResponse, SearchResult } from "@/lib/types";

const EXAMPLES = ["efflux regulation", "ciprofloxacin resistance", "MarR", "collateral sensitivity"];

export function SearchPanel() {
  const [q, setQ] = useState("");
  const [data, setData] = useState<SearchResponse | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "empty" | "error">("idle");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    const query = q.trim();
    if (!query) {
      setStatus("idle");
      setData(null);
      return;
    }
    setStatus("loading");
    timer.current = setTimeout(() => {
      let live = true;
      api
        .search(query)
        .then((d) => {
          if (!live) return;
          setData(d);
          setStatus(d.results.length ? "ready" : "empty");
        })
        .catch(() => live && setStatus("error"));
      return () => {
        live = false;
      };
    }, 220);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [q]);

  return (
    <Panel
      title="Search the evidence graph"
      aside={
        data ? (
          <span className="flex items-center gap-1.5">
            <Badge tone="accent">{data.counts.grounded} grounded</Badge>
            <Badge tone="neutral">{data.mode}</Badge>
          </span>
        ) : (
          <span className="font-mono text-[0.68rem] text-faint">grounded retrieval</span>
        )
      }
    >
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search papers, genes, and grounded claims…"
        className="w-full rounded-lg border border-line/15 bg-surface2/50 px-3 py-2 text-sm text-text outline-none transition placeholder:text-faint focus:border-accent/40"
      />

      {status === "idle" && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <span className="text-[0.66rem] text-faint">try:</span>
          {EXAMPLES.map((e) => (
            <button
              key={e}
              type="button"
              onClick={() => setQ(e)}
              className="rounded-md bg-line/6 px-1.5 py-0.5 font-mono text-[0.64rem] text-muted ring-1 ring-inset ring-line/15 transition hover:text-text hover:ring-line/30"
            >
              {e}
            </button>
          ))}
        </div>
      )}
      {status === "loading" && (
        <div className="mt-2 space-y-1.5">
          <div className="skeleton h-10 rounded-lg" />
          <div className="skeleton h-10 rounded-lg" />
        </div>
      )}
      {status === "error" && (
        <p className="mt-2 text-xs text-muted">Search offline — start the API and retry.</p>
      )}
      {status === "empty" && (
        <p className="mt-2 text-xs text-muted">
          No grounded match for <span className="font-mono text-text">{q}</span>. The corpus is
          scoped to resistance-relevant families.
        </p>
      )}
      {status === "ready" && data && (
        <ul className="animate-fade mt-2.5 max-h-[22rem] space-y-1.5 overflow-y-auto pr-1">
          {data.results.map((r, i) => (
            <ResultRow key={`${r.kind}-${r.id ?? i}`} r={r} />
          ))}
        </ul>
      )}
    </Panel>
  );
}

const KIND_TONE: Record<string, string> = {
  paper: "bg-line/8 text-muted ring-line/15",
  gene: "bg-accent/10 text-accentStrong ring-accent/25",
  edge: "bg-amber/10 text-amber ring-amber/25",
};

function ResultRow({ r }: { r: SearchResult }) {
  const p = r.provenance;
  const href = p.pubmed_url || p.ref_url || undefined;
  return (
    <li className="rounded-lg border border-line/10 bg-surface2/30 p-2.5">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <span
            className={clsx(
              "mr-1.5 rounded px-1 py-px align-middle font-mono text-[0.54rem] uppercase tracking-wide ring-1 ring-inset",
              KIND_TONE[r.kind],
            )}
          >
            {r.kind}
          </span>
          <span className="text-[0.8rem] text-text">{r.title}</span>
          {r.snippet && r.snippet !== r.title && (
            <div className="mt-0.5 truncate text-[0.7rem] text-muted">{r.snippet}</div>
          )}
        </div>
        <span className="shrink-0 font-mono text-[0.6rem] text-faint">{r.score.toFixed(1)}</span>
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-1.5">
        {p.pmid && (
          <Chip href={p.pubmed_url}>PMID {p.pmid}</Chip>
        )}
        {p.acc && <Chip href={p.ref_url}>{p.db} {p.acc}</Chip>}
        {!p.pmid && !p.acc && href === undefined && (
          <span className="font-mono text-[0.58rem] text-faint">
            {String(r.extra?.locus_tag ?? "")}
          </span>
        )}
        {r.semantic_similarity != null && (
          <span className="font-mono text-[0.58rem] text-accentStrong">
            sim {r.semantic_similarity.toFixed(2)}
          </span>
        )}
      </div>
    </li>
  );
}

function Chip({ href, children }: { href?: string | null; children: React.ReactNode }) {
  const cls =
    "inline-flex items-center gap-1 rounded-md bg-line/6 px-1.5 py-0.5 font-mono text-[0.6rem] text-muted ring-1 ring-inset ring-line/15 transition hover:text-text hover:ring-line/30";
  return href ? (
    <a href={href} target="_blank" rel="noopener noreferrer" className={cls}>
      {children}
    </a>
  ) : (
    <span className={cls}>{children}</span>
  );
}
