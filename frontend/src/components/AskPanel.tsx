"use client";
// Ask — grounded Q&A over the evidence graph. Not a chatbot: cited claims only, or refusal.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Panel, Badge } from "./ui";
import type {
  AskResponse,
  AskClaim,
  CycleResponse,
  TargetsResponse,
  RankedTarget,
} from "@/lib/types";

const ORGANISM = "Burkholderia multivorans";

const EXAMPLES = [
  "How does MarR drive efflux?",
  "What confers ciprofloxacin resistance?",
  "What can follow meropenem resistance?",
  "What's the provenance for MarR → efflux?",
];

export function AskPanel({
  dataset,
  onLoadDemo,
}: {
  dataset?: string | null;
  onLoadDemo?: () => void;
}) {
  const [q, setQ] = useState("");
  const [data, setData] = useState<AskResponse | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");

  const run = (question: string) => {
    const text = question.trim();
    if (!text) return;
    setQ(text);
    setStatus("loading");
    api
      .ask(text, "researcher")
      .then((d) => {
        setData(d);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  };

  return (
    <Panel
      title="Ask"
      aside={<span className="font-mono text-[0.68rem] text-faint">cited or refuses</span>}
    >
      <p className="mb-3 text-[0.82rem] leading-relaxed text-muted">
        Answers are built only from grounded evidence in the graph. Every claim is numbered
        and cited; if nothing supports the question, the engine refuses.
      </p>

      {dataset == null ? (
        <BlankAsk onLoadDemo={onLoadDemo} />
      ) : (
        <>
          <div className="flex gap-2">
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && run(q)}
              placeholder="Ask about a gene, drug, target, or mechanism…"
              className="min-w-0 flex-1 rounded-md border border-line/15 bg-surface/60 px-3 py-2 text-sm text-text outline-none placeholder:text-faint focus:border-accent/40"
            />
            <button
              onClick={() => run(q)}
              disabled={status === "loading" || !q.trim()}
              className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-[rgb(var(--bg))] transition hover:brightness-110 disabled:opacity-40"
            >
              {status === "loading" ? "…" : "Ask"}
            </button>
          </div>

          <div className="mt-2 flex flex-wrap gap-1.5">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                onClick={() => run(ex)}
                className="rounded-md border border-line/12 bg-surface2/40 px-2.5 py-1 text-[0.7rem] text-muted transition hover:border-line/25 hover:text-text"
              >
                {ex}
              </button>
            ))}
          </div>

          {status === "error" && (
            <p className="mt-3 text-xs text-muted">Ask service offline — start the API and retry.</p>
          )}
          {status === "loading" && <div className="mt-3 skeleton h-24 rounded-lg" />}
          {status === "ready" && data && <Answer data={data} />}
        </>
      )}
    </Panel>
  );
}

function BlankAsk({ onLoadDemo }: { onLoadDemo?: () => void }) {
  return (
    <div className="rounded-lg border border-dashed border-line/15 bg-surface2/40 p-5 text-center">
      <p className="mx-auto max-w-md text-[0.82rem] leading-relaxed text-muted">
        No dataset loaded. Ask needs grounded edges first — load the demo graph or upload strains.
      </p>
      <div className="mt-3 flex items-center justify-center gap-2">
        {onLoadDemo && (
          <button
            onClick={onLoadDemo}
            className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-[rgb(var(--bg))] transition hover:brightness-110"
          >
            Load demo graph
          </button>
        )}
        <a
          href="#yourdata"
          className="rounded-md border border-line/15 px-4 py-2 text-sm text-muted transition hover:border-line/30 hover:text-text"
        >
          Upload strains
        </a>
      </div>
    </div>
  );
}

function Answer({ data }: { data: AskResponse }) {
  if (data.refused) {
    return (
      <div className="mt-3 rounded-lg border border-amber/25 bg-amber/[0.06] p-3">
        <div className="mb-1 text-[0.66rem] font-semibold uppercase tracking-[0.12em] text-amber">
          Refused — no grounded evidence
        </div>
        <p className="text-[0.8rem] leading-relaxed text-muted">{data.deterministic_summary}</p>
      </div>
    );
  }
  return (
    <div className="mt-3 space-y-3">
      <div className="rounded-lg border border-line/12 bg-surface2/40 p-3">
        <div className="mb-1 flex items-center justify-between gap-2">
          <span className="text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-faint">
            {data.answer ? "Answer · from cited claims" : "Answer · grounded retrieval"}
          </span>
          <Badge tone="accent">
            {data.counts.claims} cited · {data.intent}
          </Badge>
        </div>
        <p className="text-[0.82rem] leading-relaxed text-text">
          {data.answer ? data.answer.summary : data.deterministic_summary}
        </p>
        {data.answer && data.answer.citations.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {data.answer.citations.map((c) => (
              <span
                key={c}
                className="rounded bg-line/8 px-1.5 py-0.5 font-mono text-[0.6rem] text-muted"
              >
                {c}
              </span>
            ))}
          </div>
        )}
      </div>

      {data.intent === "treatment" && <RoutedCycle />}
      {data.intent === "target" && <RoutedTarget />}

      <div>
        <div className="mb-1.5 text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-faint">
          Evidence · {data.counts.claims} claim{data.counts.claims === 1 ? "" : "s"}
        </div>
        <div className="space-y-2">
          {data.claims.map((c, i) => (
            <ClaimCard key={i} n={i + 1} c={c} />
          ))}
        </div>
      </div>

      {data.caveats.length > 0 && (
        <ul className="space-y-1 rounded-lg border border-amber/20 bg-amber/[0.04] p-2.5">
          {data.caveats.map((cv, i) => (
            <li key={i} className="text-[0.7rem] leading-relaxed text-muted">
              {cv}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function RoutedShell({ kicker, children }: { kicker: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-line/12 bg-surface2/30 p-3">
      <div className="mb-2 text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-faint">
        {kicker}
      </div>
      {children}
    </div>
  );
}

function RoutedCycle() {
  const [data, setData] = useState<CycleResponse | null>(null);
  const [err, setErr] = useState(false);
  useEffect(() => {
    let live = true;
    api.cycle(ORGANISM).then((d) => live && setData(d)).catch(() => live && setErr(true));
    return () => {
      live = false;
    };
  }, []);
  if (err || !data?.cycle.length) return null;
  if (!data) return <div className="skeleton h-16 rounded-lg" />;
  const cited = data.rcs_pairs.find((p) => p.provenance)?.provenance;
  return (
    <RoutedShell kicker="Cited cycle">
      <div className="flex flex-wrap items-center gap-1.5">
        {data.cycle.map((drug, i) => (
          <span key={`${drug}-${i}`} className="flex items-center gap-1.5">
            <span className="rounded border border-line/15 bg-surface px-2 py-1 font-mono text-[0.7rem] text-text">
              {drug}
            </span>
            {i < data.cycle.length - 1 && <span className="text-faint">→</span>}
          </span>
        ))}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        <Badge tone="amber">research hypothesis</Badge>
        {cited?.pmid && (
          <a
            href={cited.pubmed_url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-[0.6rem] text-accentStrong hover:underline"
          >
            PMID {cited.pmid}
          </a>
        )}
      </div>
    </RoutedShell>
  );
}

function RoutedTarget() {
  const [top, setTop] = useState<RankedTarget | null>(null);
  useEffect(() => {
    let live = true;
    api
      .targets(null)
      .then((d: TargetsResponse) => {
        if (!live) return;
        const best = [...d.targets].sort((a, b) => (b.rank_score ?? 0) - (a.rank_score ?? 0))[0];
        setTop(best ?? null);
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, []);
  if (!top) return null;
  const pct = Math.round((top.rank_score ?? 0) * 100);
  return (
    <RoutedShell kicker="Top ranked target">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <span className="font-mono text-[0.82rem] text-text">{top.name ?? top.locus_tag}</span>
          {top.mechanism && <div className="mt-0.5 text-[0.72rem] text-muted">{top.mechanism}</div>}
        </div>
        <span className="font-mono text-sm text-accentStrong">{(top.rank_score ?? 0).toFixed(2)}</span>
      </div>
      <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-line/10">
        <div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
      </div>
    </RoutedShell>
  );
}

function ClaimCard({ n, c }: { n: number; c: AskClaim }) {
  const href = c.provenance?.ref_url || c.provenance?.pubmed_url || undefined;
  const conf = typeof c.confidence === "number" ? Math.max(0, Math.min(1, c.confidence)) : null;
  return (
    <div className="rounded-lg border border-line/10 bg-surface2/30 p-3">
      <div className="flex items-start gap-2.5">
        <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded bg-line/10 font-mono text-[0.62rem] text-muted">
          {n}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <span className="text-[0.82rem] leading-snug text-text">{c.title}</span>
            <span className="shrink-0 font-mono text-[0.56rem] uppercase text-faint">{c.kind}</span>
          </div>
          {conf !== null && (
            <div className="mt-1.5 flex items-center gap-2">
              <div className="h-1 flex-1 overflow-hidden rounded-full bg-line/10">
                <div
                  className="h-full rounded-full bg-accent"
                  style={{ width: `${Math.round(conf * 100)}%`, opacity: c.grounded ? 1 : 0.5 }}
                />
              </div>
              <span className="font-mono text-[0.6rem] text-faint">{conf.toFixed(2)}</span>
            </div>
          )}
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            {c.citation &&
              (href ? (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-[0.58rem] text-accentStrong hover:underline"
                >
                  {c.citation}
                </a>
              ) : (
                <span className="font-mono text-[0.58rem] text-muted">{c.citation}</span>
              ))}
            <span className={`text-[0.56rem] uppercase ${c.grounded ? "text-accentStrong" : "text-faint"}`}>
              {c.grounded ? "grounded" : "abstract"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
