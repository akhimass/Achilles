"use client";
// The "prove-it" panel — the edge a search box can't match. The engine is run against
// independent PUBLIC ground truth: it must RECOVER known resistance relationships from
// grounded evidence (recall) and REFUSE planted false ones (precision, 0 fabrications).
// Both are computed and cited, live — not asserted.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { clsx } from "@/lib/clsx";
import { Panel, Badge } from "./ui";
import type { ValidationReport, ValidationItem, RedTeamVerdict } from "@/lib/types";

export function ValidationPanel() {
  const [data, setData] = useState<ValidationReport | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let live = true;
    api
      .validation()
      .then((d) => {
        if (!live) return;
        setData(d);
        setStatus("ready");
      })
      .catch(() => live && setStatus("error"));
    return () => {
      live = false;
    };
  }, []);

  const m = data?.metrics;

  return (
    <Panel
      title="Self-validation"
      aside={
        m ? (
          <Badge tone={m.clean ? "accent" : "danger"}>
            {m.clean ? "0 fabricated" : `${m.fabricated} fabricated`}
          </Badge>
        ) : (
          <span className="font-mono text-[0.68rem] text-faint">public ground truth</span>
        )
      }
    >
      {status === "loading" && (
        <div className="space-y-2">
          <div className="skeleton h-16 rounded-xl" />
          <div className="skeleton h-24 rounded-xl" />
        </div>
      )}
      {status === "error" && (
        <p className="text-xs text-muted">Validation offline — start the API and retry.</p>
      )}
      {status === "ready" && data && m && (
        <div className="animate-fade">
          <p className="mb-3 text-[0.8rem] leading-relaxed text-muted">
            A retrieval tool returns whatever is in its index. Achilles is held to{" "}
            <span className="text-text">{m.positives + m.negatives} independent, publicly-cited
            controls</span>: it must <span className="text-text">recover</span> known resistance
            biology from grounded evidence and <span className="text-text">refuse</span> an
            adversarial battery of {m.negatives} plausible-but-false claims — the traps a
            hallucinating model falls for. Computed live, every recovery cited.
          </p>

          <div className="grid grid-cols-3 gap-2.5">
            <Metric
              label="Known recovered"
              value={`${m.recovered}/${m.positives}`}
              sub={`${Math.round(m.recovery_rate * 100)}% recall`}
              tone="accent"
            />
            <Metric
              label="Adversarial refused"
              value={`${m.refused}/${m.negatives}`}
              sub="traps, all declined"
              tone="accent"
            />
            <Metric
              label="Fabricated"
              value={`${m.fabricated}`}
              sub={m.clean ? "clean on controls" : "review needed"}
              tone={m.clean ? "accent" : "danger"}
            />
          </div>

          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[0.7rem] text-faint">
            <span>
              <span className="font-mono text-accentStrong">
                {Math.round(m.recovery_rate * 100)}%
              </span>{" "}
              recall
            </span>
            <span className="text-line/20">·</span>
            <span>
              <span className="font-mono text-accentStrong">
                {m.fabricated === 0
                  ? "100%"
                  : `${Math.round((100 * m.recovered) / (m.recovered + m.fabricated))}%`}
              </span>{" "}
              precision
            </span>
            <span className="text-line/20">·</span>
            <span>
              <span className="font-mono text-accentStrong">{m.negatives}</span> adversarial
              claims refused
            </span>
            <span className="text-line/20">·</span>
            <span>
              <span className="font-mono text-accentStrong">{m.positives + m.negatives}</span>{" "}
              public controls
            </span>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <Controls
              title="Known-true → recovered"
              items={data.items.filter((i) => i.kind === "positive")}
            />
            <Controls
              title="Adversarial battery → refused"
              items={data.items.filter((i) => i.kind === "negative")}
            />
          </div>

          <RedTeam />
        </div>
      )}
    </Panel>
  );
}

const PRESETS: { gene: string; target: string; label: string; truth: "true" | "false" }[] = [
  { gene: "MarR", target: "ciprofloxacin", label: "MarR → ciprofloxacin", truth: "true" },
  { gene: "MarR", target: "vancomycin", label: "MarR → vancomycin", truth: "false" },
  { gene: "AraC/MarA", target: "tigecycline", label: "AraC/MarA → tigecycline", truth: "true" },
  { gene: "LysR", target: "tetracycline", label: "LysR → tetracycline", truth: "false" },
];

// Live precision test: a judge types (or picks) a claim; the engine adjudicates it
// against grounded evidence and refuses anything it can't ground — watched in real time.
function RedTeam() {
  const [gene, setGene] = useState("MarR");
  const [target, setTarget] = useState("");
  const [result, setResult] = useState<RedTeamVerdict | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  const run = (g: string, t: string) => {
    setGene(g);
    setTarget(t);
    setCopied(false);
    if (!g.trim() || !t.trim()) return;
    setBusy(true);
    api
      .redteam(g.trim(), t.trim())
      .then((v) => setResult(v))
      .catch(() => setResult(null))
      .finally(() => setBusy(false));
  };

  // Shareable permalink: ?rt_gene=&rt_target= auto-runs the same claim on load, so a
  // judge's verdict is a copyable URL.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const p = new URLSearchParams(window.location.search);
    const g = p.get("rt_gene");
    const t = p.get("rt_target");
    if (g && t) run(g, t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const copyLink = () => {
    if (typeof window === "undefined" || !gene.trim() || !target.trim()) return;
    const url = `${window.location.origin}${window.location.pathname}?rt_gene=${encodeURIComponent(
      gene.trim(),
    )}&rt_target=${encodeURIComponent(target.trim())}`;
    navigator.clipboard?.writeText(url).then(
      () => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      },
      () => {},
    );
  };

  return (
    <div className="mt-4 rounded-xl border border-line/12 bg-surface2/40 p-3">
      <div className="mb-1 text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-faint">
        Red-team it — inject a claim, watch the verdict
      </div>
      <p className="mb-2 text-[0.72rem] leading-relaxed text-muted">
        Type a resistance claim. The engine only says <span className="text-text">supported</span>{" "}
        if grounded evidence backs it — otherwise it <span className="text-text">refuses</span>,
        rather than fabricate. Try a true one and a false one.
      </p>
      <div className="flex flex-wrap items-center gap-1.5">
        <input
          value={gene}
          onChange={(e) => setGene(e.target.value)}
          placeholder="gene (e.g. MarR)"
          className="w-28 rounded-md border border-line/15 bg-surface/60 px-2 py-1 text-[0.74rem] text-text outline-none focus:border-accent/40"
        />
        <span className="text-[0.7rem] text-faint">confers resistance to</span>
        <input
          value={target}
          onChange={(e) => setTarget(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run(gene, target)}
          placeholder="drug (e.g. vancomycin)"
          className="w-36 rounded-md border border-line/15 bg-surface/60 px-2 py-1 text-[0.74rem] text-text outline-none focus:border-accent/40"
        />
        <button
          type="button"
          onClick={() => run(gene, target)}
          disabled={busy}
          className="rounded-md bg-accent/12 px-2.5 py-1 text-[0.72rem] font-medium text-accentStrong ring-1 ring-inset ring-accent/25 transition hover:bg-accent/20 disabled:opacity-50"
        >
          {busy ? "checking…" : "Test claim"}
        </button>
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {PRESETS.map((p) => (
          <button
            key={p.label}
            type="button"
            onClick={() => run(p.gene, p.target)}
            className={clsx(
              "rounded-md px-1.5 py-0.5 font-mono text-[0.62rem] ring-1 ring-inset transition",
              p.truth === "true"
                ? "bg-line/6 text-muted ring-line/15 hover:text-text"
                : "bg-amber/8 text-amber ring-amber/20 hover:bg-amber/15",
            )}
          >
            {p.label} {p.truth === "false" ? "· planted" : ""}
          </button>
        ))}
      </div>
      {result && (
        <>
          <Verdict v={result} />
          <button
            type="button"
            onClick={copyLink}
            className="mt-1.5 inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 font-mono text-[0.6rem] text-muted ring-1 ring-inset ring-line/15 transition hover:text-text hover:ring-line/30"
          >
            {copied ? "link copied ✓" : "copy this verdict as a link"}
          </button>
        </>
      )}
    </div>
  );
}

function Verdict({ v }: { v: RedTeamVerdict }) {
  const tone =
    v.verdict === "supported"
      ? { cls: "border-accent/30 bg-accent/[0.06] text-accentStrong", label: "SUPPORTED" }
      : v.verdict === "weak"
        ? { cls: "border-amber/30 bg-amber/[0.06] text-amber", label: "WEAK — abstract-only" }
        : v.verdict === "unknown_gene"
          ? { cls: "border-line/20 bg-surface2/50 text-muted", label: "UNKNOWN GENE" }
          : { cls: "border-amber/30 bg-amber/[0.06] text-amber", label: "REFUSED" };
  const p = v.provenance || {};
  const cite = p.acc ? `${p.db} ${p.acc}` : p.pmid ? `PMID ${p.pmid}` : null;
  const href = p.ref_url || p.pubmed_url || undefined;
  return (
    <div className={clsx("animate-fade mt-2.5 rounded-lg border p-2.5", tone.cls)}>
      <div className="flex items-center gap-2">
        <span className="font-mono text-[0.7rem] font-semibold uppercase tracking-wide">
          {tone.label}
        </span>
        <span className="font-mono text-[0.66rem] text-muted">
          {v.claim.gene} → {v.claim.target}
        </span>
      </div>
      <p className="mt-1 text-[0.72rem] leading-relaxed text-muted">{v.reason}</p>
      {cite && (
        <div className="mt-1">
          {href ? (
            <a href={href} target="_blank" rel="noopener noreferrer" className="font-mono text-[0.62rem] text-accentStrong hover:underline">
              {cite}
            </a>
          ) : (
            <span className="font-mono text-[0.62rem] text-faint">{cite}</span>
          )}
        </div>
      )}
    </div>
  );
}

function Metric({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string;
  sub: string;
  tone: "accent" | "danger";
}) {
  return (
    <div className="rounded-xl border border-line/10 bg-surface2/40 p-3">
      <div className="text-[0.6rem] uppercase tracking-wide text-faint">{label}</div>
      <div
        className={clsx(
          "mt-0.5 font-mono text-2xl tabular-nums",
          tone === "danger" ? "text-danger" : "text-accentStrong",
        )}
      >
        {value}
      </div>
      <div className="mt-0.5 text-[0.62rem] text-muted">{sub}</div>
    </div>
  );
}

const STATUS_TONE: Record<string, string> = {
  recovered: "bg-accent/10 text-accentStrong ring-accent/25",
  refused: "bg-accent/10 text-accentStrong ring-accent/25",
  literature_only: "bg-amber/10 text-amber ring-amber/25",
  weakly_asserted: "bg-amber/10 text-amber ring-amber/25",
  missing: "bg-line/8 text-muted ring-line/15",
  fabricated: "bg-danger/12 text-danger ring-danger/25",
};

function Controls({ title, items }: { title: string; items: ValidationItem[] }) {
  return (
    <div>
      <div className="mb-1.5 text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-faint">
        {title}
      </div>
      <ul className="space-y-1.5">
        {items.map((i, idx) => {
          const cite = i.grounded
            ? i.provenance.acc
              ? `${i.provenance.db} ${i.provenance.acc}`
              : i.provenance.pmid
                ? `PMID ${i.provenance.pmid}`
                : null
            : i.expected_citation;
          const href = i.provenance.ref_url || i.provenance.pubmed_url || undefined;
          return (
            <li key={idx} className="rounded-lg border border-line/10 bg-surface2/30 p-2">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 text-[0.74rem] text-text">
                  <span className="font-mono">{i.gene}</span>{" "}
                  <span className="text-muted">{i.relation.replace(/_/g, " ")}</span>{" "}
                  <span className="font-medium">{i.target_terms[0]}</span>
                </div>
                <span
                  className={clsx(
                    "shrink-0 rounded px-1 py-px font-mono text-[0.54rem] uppercase tracking-wide ring-1 ring-inset",
                    STATUS_TONE[i.status] ?? "bg-line/8 text-muted ring-line/15",
                  )}
                >
                  {i.status.replace(/_/g, " ")}
                </span>
              </div>
              {cite && (
                <div className="mt-1">
                  {href ? (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-mono text-[0.6rem] text-accentStrong hover:underline"
                    >
                      {cite}
                    </a>
                  ) : (
                    <span className="font-mono text-[0.6rem] text-faint">{cite}</span>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
