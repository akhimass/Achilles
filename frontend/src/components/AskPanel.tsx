"use client";
// Ask Achilles — the grounded question box, built to be the OPPOSITE of a chatbot.
// It answers ONLY from cited evidence retrieved from the graph: every claim is a numbered
// card with its provenance and an evidence-strength bar, the optional model synthesis may
// only phrase those numbered claims, and when nothing is grounded it REFUSES rather than
// fabricate. Persona (researcher / physician / computational) sets the lens and caveats.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Panel, Badge } from "./ui";
import type {
  AskResponse,
  AskClaim,
  AskPersona,
  CycleResponse,
  TargetsResponse,
  RankedTarget,
} from "@/lib/types";

const ORGANISM = "Burkholderia multivorans";

const PERSONA_LABEL: Record<AskPersona, string> = {
  researcher: "Researcher",
  physician: "Physician",
  computational: "Computational",
};

const EXAMPLES: Record<AskPersona, string[]> = {
  researcher: [
    "How does MarR drive efflux?",
    "What confers ciprofloxacin resistance?",
    "Is AraC/MarA a good target?",
  ],
  physician: [
    "What can follow meropenem resistance?",
    "Is cycling supported here?",
    "What re-sensitizes after ceftazidime?",
  ],
  computational: [
    "What's the provenance for MarR → efflux?",
    "Which claims are reference-corroborated?",
    "How is tigecycline resistance grounded?",
  ],
};

export function AskPanel({
  persona: pagePersona,
  dataset,
  onLoadDemo,
}: {
  persona?: string;
  dataset?: string | null;
  onLoadDemo?: () => void;
}) {
  const seed: AskPersona =
    pagePersona === "physician" || pagePersona === "computational"
      ? pagePersona
      : "researcher";
  const [persona, setPersona] = useState<AskPersona>(seed);
  const [q, setQ] = useState("");
  const [data, setData] = useState<AskResponse | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");

  // Follow the sidebar persona when it changes to a concrete one.
  useEffect(() => {
    if (pagePersona === "physician" || pagePersona === "computational" || pagePersona === "researcher")
      setPersona(pagePersona);
  }, [pagePersona]);

  const run = (question: string) => {
    const text = question.trim();
    if (!text) return;
    setQ(text);
    setStatus("loading");
    api
      .ask(text, persona)
      .then((d) => {
        setData(d);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  };

  return (
    <Panel
      title="Ask Achilles"
      aside={<span className="font-mono text-[0.68rem] text-faint">grounded only</span>}
    >
      <p className="mb-3 text-[0.8rem] leading-relaxed text-muted">
        Ask in plain language. Answers are built <span className="text-text">only from
        grounded evidence</span> in the graph — every claim numbered and cited — and the
        engine <span className="text-text">refuses</span> when nothing supports it.
      </p>

      {dataset === null ? (
        <BlankAsk onLoadDemo={onLoadDemo} />
      ) : (
        <>
      {/* Persona lens */}
      <div className="mb-2.5 inline-flex rounded-lg border border-line/12 bg-surface2/40 p-0.5">
        {(Object.keys(PERSONA_LABEL) as AskPersona[]).map((p) => (
          <button
            key={p}
            onClick={() => setPersona(p)}
            className={
              "rounded-md px-2.5 py-1 text-[0.72rem] font-medium transition " +
              (persona === p ? "bg-accent/15 text-accentStrong" : "text-muted hover:text-text")
            }
          >
            {PERSONA_LABEL[p]}
          </button>
        ))}
      </div>

      {/* Query box */}
      <div className="flex gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run(q)}
          placeholder={`Ask as a ${PERSONA_LABEL[persona].toLowerCase()}…`}
          className="min-w-0 flex-1 rounded-lg border border-line/15 bg-surface/60 px-3 py-2 text-sm text-text outline-none placeholder:text-faint focus:border-accent/40"
        />
        <button
          onClick={() => run(q)}
          disabled={status === "loading" || !q.trim()}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-[rgb(var(--bg))] transition hover:shadow-glow-sm disabled:opacity-40"
        >
          {status === "loading" ? "…" : "Ask"}
        </button>
      </div>

      {/* Examples */}
      <div className="mt-2 flex flex-wrap gap-1.5">
        {EXAMPLES[persona].map((ex) => (
          <button
            key={ex}
            onClick={() => run(ex)}
            className="rounded-full border border-line/12 bg-surface2/40 px-2.5 py-1 text-[0.68rem] text-muted transition hover:border-accent/30 hover:text-text"
          >
            {ex}
          </button>
        ))}
      </div>

      {status === "error" && (
        <p className="mt-3 text-xs text-muted">Ask service offline — start the API and retry.</p>
      )}
      {status === "loading" && <div className="mt-3 skeleton h-24 rounded-xl" />}
      {status === "ready" && data && <Answer data={data} />}
        </>
      )}
    </Panel>
  );
}

function BlankAsk({ onLoadDemo }: { onLoadDemo?: () => void }) {
  return (
    <div className="rounded-xl border border-dashed border-line/15 bg-surface2/40 p-5 text-center">
      <p className="mx-auto max-w-md text-[0.82rem] leading-relaxed text-muted">
        No dataset is loaded. Ask answers <span className="text-text">only from grounded
        evidence</span>, so it needs data first — load the example dataset, or bring your own
        below and it becomes queryable.
      </p>
      <div className="mt-3 flex items-center justify-center gap-2">
        {onLoadDemo && (
          <button
            onClick={onLoadDemo}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-[rgb(var(--bg))] transition hover:shadow-glow-sm"
          >
            Load the demo dataset
          </button>
        )}
        <a
          href="#yourdata"
          className="rounded-lg border border-line/15 px-4 py-2 text-sm text-muted transition hover:border-line/30 hover:text-text"
        >
          Bring your own data
        </a>
      </div>
    </div>
  );
}

function Answer({ data }: { data: AskResponse }) {
  if (data.refused) {
    return (
      <div className="mt-3 animate-fade rounded-xl border border-amber/25 bg-amber/[0.06] p-3">
        <div className="mb-1 flex items-center gap-1.5 text-[0.66rem] font-semibold uppercase tracking-[0.12em] text-amber">
          Refused — no grounded evidence
        </div>
        <p className="text-[0.8rem] leading-relaxed text-muted">{data.deterministic_summary}</p>
      </div>
    );
  }
  return (
    <div className="mt-3 animate-fade space-y-3">
      {/* Grounded answer (LLM synthesis if present, else the deterministic summary) */}
      <div className="rounded-xl border border-accent/25 bg-accent/[0.05] p-3">
        <div className="mb-1 flex items-center justify-between gap-2">
          <span className="text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-accentStrong">
            {data.answer ? "Answer · synthesized from cited claims" : "Answer · grounded retrieval"}
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
                className="rounded-md bg-line/8 px-1.5 py-0.5 font-mono text-[0.6rem] text-muted ring-1 ring-inset ring-line/15"
              >
                {c}
              </span>
            ))}
          </div>
        )}
        {!data.answer && (
          <p className="mt-1.5 text-[0.66rem] text-faint">
            Model narration is off (no key set) — showing the retrieved cited evidence
            directly. The claims below are the answer.
          </p>
        )}
      </div>

      {/* Intent-routed viz — a real, grounded object for the question's intent */}
      {data.intent === "treatment" && <RoutedCycle />}
      {data.intent === "target" && <RoutedTarget />}

      {/* Evidence cards — the real, cited output */}
      <div>
        <div className="mb-1.5 text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-faint">
          Evidence · {data.counts.claims} grounded claim{data.counts.claims === 1 ? "" : "s"}
        </div>
        <div className="space-y-2">
          {data.claims.map((c, i) => (
            <ClaimCard key={i} n={i + 1} c={c} />
          ))}
        </div>
      </div>

      {data.caveats.length > 0 && (
        <div className="rounded-lg border border-amber/25 bg-amber/[0.06] p-2.5">
          <ul className="space-y-1">
            {data.caveats.map((cv, i) => (
              <li key={i} className="flex gap-1.5 text-[0.7rem] leading-relaxed text-muted">
                <span className="mt-[0.34rem] h-1 w-1 shrink-0 rounded-full bg-amber/60" />
                {cv}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── Intent-routed grounded viz ───────────────────────────────────────────────
// These pull from the SAME real endpoints as the console panels, so the "answer"
// to a treatment/target question is a live cited object, not generated text.

function RoutedShell({
  kicker,
  children,
}: {
  kicker: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-line/12 bg-surface2/30 p-3">
      <div className="mb-2 text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-accentStrong">
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
  if (err) return null;
  if (!data) return <div className="skeleton h-16 rounded-xl" />;
  if (!data.cycle.length) return null;
  const cited = data.rcs_pairs.find((p) => p.provenance)?.provenance;
  return (
    <RoutedShell kicker="Because you asked about treatment · the cited cycle">
      <div className="flex flex-wrap items-center gap-1.5">
        {data.cycle.map((drug, i) => (
          <span key={`${drug}-${i}`} className="flex items-center gap-1.5">
            <span className="rounded-md border border-accent/25 bg-accent/[0.06] px-2 py-1 font-mono text-[0.7rem] text-text">
              {drug}
            </span>
            {i < data.cycle.length - 1 && <span className="text-faint">→</span>}
          </span>
        ))}
        <span className="ml-0.5 font-mono text-[0.6rem] text-faint">↻ repeat</span>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        <Badge tone="amber">research hypothesis</Badge>
        {cited?.pmid && (
          <a
            href={cited.pubmed_url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-md bg-accent/10 px-1.5 py-0.5 font-mono text-[0.6rem] text-accentStrong ring-1 ring-inset ring-accent/25 hover:brightness-110"
          >
            PMID {cited.pmid}
          </a>
        )}
        <span className="font-mono text-[0.6rem] text-faint">
          {data.counts.reciprocal} RCS pairs
        </span>
      </div>
    </RoutedShell>
  );
}

function RoutedTarget() {
  const [top, setTop] = useState<RankedTarget | null>(null);
  const [err, setErr] = useState(false);
  useEffect(() => {
    let live = true;
    api
      .targets(null)
      .then((d: TargetsResponse) => {
        if (!live) return;
        const best = [...d.targets].sort(
          (a, b) => (b.rank_score ?? 0) - (a.rank_score ?? 0),
        )[0];
        setTop(best ?? null);
      })
      .catch(() => live && setErr(true));
    return () => {
      live = false;
    };
  }, []);
  if (err) return null;
  if (!top) return <div className="skeleton h-16 rounded-xl" />;
  const pct = Math.round((top.rank_score ?? 0) * 100);
  return (
    <RoutedShell kicker="Because you asked about targets · top ranked">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <span className="font-mono text-[0.82rem] text-text">{top.name ?? top.locus_tag}</span>
          {top.locus_tag && (
            <span className="ml-1.5 font-mono text-[0.6rem] text-faint">{top.locus_tag}</span>
          )}
          {top.mechanism && <div className="mt-0.5 text-[0.72rem] text-muted">{top.mechanism}</div>}
        </div>
        <span className="font-mono text-sm text-accentStrong">{(top.rank_score ?? 0).toFixed(2)}</span>
      </div>
      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-line/10">
        <div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
      </div>
      <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
        <span className="font-mono text-[0.6rem] text-faint">
          {top.evidence_counts.grounded}/{top.evidence_counts.total} edges grounded
        </span>
        {top.tractability?.bucket && (
          <span className="rounded-md bg-line/8 px-1.5 py-0.5 font-mono text-[0.58rem] uppercase text-muted">
            {top.tractability.bucket}
          </span>
        )}
        {top.rationale_citations.slice(0, 2).map((a) => (
          <span
            key={a}
            className="rounded-md bg-accent/10 px-1.5 py-0.5 font-mono text-[0.58rem] text-accentStrong ring-1 ring-inset ring-accent/25"
          >
            {a}
          </span>
        ))}
      </div>
    </RoutedShell>
  );
}

function ClaimCard({ n, c }: { n: number; c: AskClaim }) {
  const href = c.provenance?.ref_url || c.provenance?.pubmed_url || undefined;
  const conf = typeof c.confidence === "number" ? Math.max(0, Math.min(1, c.confidence)) : null;
  return (
    <div className="rounded-xl border border-line/10 bg-surface2/30 p-3">
      <div className="flex items-start gap-2.5">
        <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-md bg-accent/12 font-mono text-[0.62rem] text-accentStrong">
          {n}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <span className="text-[0.82rem] leading-snug text-text">{c.title}</span>
            <span className="shrink-0 rounded-md bg-line/8 px-1.5 py-0.5 font-mono text-[0.56rem] uppercase text-faint">
              {c.kind}
            </span>
          </div>

          {/* Evidence-strength bar — real, per-claim confidence (edges) */}
          {conf !== null ? (
            <div className="mt-1.5 flex items-center gap-2">
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-line/10">
                <div
                  className="h-full rounded-full bg-accent"
                  style={{ width: `${Math.round(conf * 100)}%`, opacity: c.grounded ? 1 : 0.5 }}
                />
              </div>
              <span className="font-mono text-[0.6rem] text-faint">{conf.toFixed(2)}</span>
            </div>
          ) : (
            <div className="mt-1 text-[0.6rem] text-faint">reference annotation</div>
          )}

          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            {c.relation && (
              <span className="rounded-md bg-line/6 px-1.5 py-0.5 font-mono text-[0.58rem] text-muted">
                {c.relation.replace(/_/g, " ")}
              </span>
            )}
            {c.citation &&
              (href ? (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-md bg-accent/10 px-1.5 py-0.5 font-mono text-[0.58rem] text-accentStrong ring-1 ring-inset ring-accent/25 hover:brightness-110"
                >
                  {c.citation}
                </a>
              ) : (
                <span className="rounded-md bg-line/6 px-1.5 py-0.5 font-mono text-[0.58rem] text-muted">
                  {c.citation}
                </span>
              ))}
            <span
              className={
                "rounded-md px-1.5 py-0.5 text-[0.56rem] font-semibold uppercase " +
                (c.grounded ? "bg-accent/10 text-accentStrong" : "bg-line/8 text-faint")
              }
            >
              {c.grounded ? "grounded" : "abstract"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
