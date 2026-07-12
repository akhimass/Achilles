"use client";
// Retrodiction — the sharpest "prove-it" beat. A search box only tells you what a paper
// already says. Achilles is held to a harder test: freeze the evidence at a cutoff year,
// hide everything published after it, and ask whether the pre-cutoff graph already
// pointed at a relationship a LATER paper went on to confirm. Foresight in TIME, and —
// the invariant — never a false call: no fabricated claim is ever "anticipated".
// Slide the cutoff to 2019 and AraC/MarA anticipates its 2020 tigecycline confirmation.
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { Panel, Badge } from "./ui";
import type { RetrodictionReport, RetroPositive, RetroSignal, RetroStatus } from "@/lib/types";

const MIN_YEAR = 2013;
const MAX_YEAR = 2025;

export function RetrodictionPanel() {
  const [cutoff, setCutoff] = useState(2019);
  const [data, setData] = useState<RetrodictionReport | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let live = true;
    setStatus((s) => (data ? s : "loading"));
    api
      .retrodiction(cutoff)
      .then((d) => {
        if (!live) return;
        setData(d);
        setStatus("ready");
      })
      .catch(() => live && setStatus("error"));
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cutoff]);

  const m = data?.metrics;
  // Held-out confirmations, most-informative first: anticipated before honest misses.
  const heldOut = useMemo(
    () =>
      (data?.positives ?? [])
        .filter((p) => p.status.startsWith("anticipated") || p.status === "not_anticipable")
        .sort((a, b) => rank(a.status) - rank(b.status)),
    [data],
  );

  return (
    <Panel
      title="Retrodiction — would it have called it before the paper?"
      aside={
        m ? (
          <Badge tone={m.clean ? "accent" : "danger"}>
            {m.false_anticipations === 0
              ? "0 false calls"
              : `${m.false_anticipations} false calls`}
          </Badge>
        ) : (
          <span className="font-mono text-[0.68rem] text-faint">time-split hold-out</span>
        )
      }
    >
      {status === "error" && (
        <p className="text-xs text-muted">Retrodiction offline — start the API and retry.</p>
      )}
      {status !== "error" && (
        <div className="animate-fade">
          <p className="mb-3 text-[0.8rem] leading-relaxed text-muted">
            Recovering known biology proves consistency. This proves{" "}
            <span className="text-text">foresight</span>: freeze the literature at a cutoff,
            hide everything after it, and ask what the earlier graph already pointed at.
            Every &ldquo;anticipated&rdquo; call is backed by a pre-cutoff edge — and no false
            claim is ever anticipated.
          </p>

          <CutoffSlider cutoff={cutoff} onChange={setCutoff} />

          {m && (
            <div className="mt-3 grid grid-cols-3 gap-2.5">
              <Metric
                label="Anticipated"
                value={`${m.anticipated}/${m.held_out}`}
                sub={`${Math.round(m.anticipation_rate * 100)}% of held-out`}
                tone="accent"
              />
              <Metric
                label="Honest misses"
                value={`${m.not_anticipable}`}
                sub="no pre-cutoff signal"
                tone="neutral"
              />
              <Metric
                label="False calls"
                value={`${m.false_anticipations}`}
                sub="must be 0"
                tone={m.false_anticipations === 0 ? "accent" : "danger"}
              />
            </div>
          )}

          <p className="mt-2.5 text-[0.68rem] text-faint">
            {m ? (
              <>
                {m.known_by_cutoff} of {m.positives} controls were already grounded by{" "}
                {cutoff} (not counted as foresight). Held-out = confirmed only by a{" "}
                <span className="text-muted">post-{cutoff}</span> paper the frozen graph
                never saw.
              </>
            ) : (
              "Loading the frozen graph…"
            )}
          </p>

          <div className="mt-3 space-y-2">
            {heldOut.map((p, i) => (
              <ControlRow key={`${p.locus}-${p.relation}-${i}`} p={p} cutoff={cutoff} />
            ))}
            {status === "ready" && heldOut.length === 0 && (
              <p className="text-[0.72rem] text-faint">
                Nothing held out at {cutoff} — every control was already grounded by then.
                Slide the cutoff earlier.
              </p>
            )}
          </div>
        </div>
      )}
    </Panel>
  );
}

function rank(s: RetroStatus): number {
  return s === "anticipated_drug" ? 0 : s === "anticipated_mechanism" ? 1 : 2;
}

function CutoffSlider({ cutoff, onChange }: { cutoff: number; onChange: (y: number) => void }) {
  return (
    <div className="rounded-xl border border-line/12 bg-surface2/30 p-3">
      <div className="mb-1.5 flex items-baseline justify-between">
        <span className="text-[0.72rem] text-muted">Evidence cutoff</span>
        <span className="font-mono text-sm text-text">{cutoff}</span>
      </div>
      <input
        type="range"
        min={MIN_YEAR}
        max={MAX_YEAR}
        step={1}
        value={cutoff}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-[var(--accent,#6366f1)]"
        aria-label="Evidence cutoff year"
      />
      <div className="mt-0.5 flex justify-between font-mono text-[0.58rem] text-faint">
        <span>{MIN_YEAR}</span>
        <span>freeze the graph here →</span>
        <span>{MAX_YEAR}</span>
      </div>
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
  tone: "accent" | "neutral" | "danger";
}) {
  const ring =
    tone === "accent"
      ? "ring-accent/25"
      : tone === "danger"
        ? "ring-rose-500/30"
        : "ring-line/15";
  const val =
    tone === "accent" ? "text-accentStrong" : tone === "danger" ? "text-rose-400" : "text-text";
  return (
    <div className={`rounded-xl bg-surface2/40 p-2.5 ring-1 ring-inset ${ring}`}>
      <div className="text-[0.62rem] uppercase tracking-wide text-faint">{label}</div>
      <div className={`mt-0.5 font-mono text-lg leading-none ${val}`}>{value}</div>
      <div className="mt-1 text-[0.62rem] text-muted">{sub}</div>
    </div>
  );
}

const STATUS_LABEL: Record<RetroStatus, { text: string; tone: "accent" | "amber" | "neutral" }> = {
  anticipated_drug: { text: "anticipated · drug-level", tone: "accent" },
  anticipated_mechanism: { text: "anticipated · mechanism", tone: "accent" },
  not_anticipable: { text: "not anticipable", tone: "neutral" },
  known_by_cutoff: { text: "known by cutoff", tone: "neutral" },
  unconfirmed: { text: "unconfirmed", tone: "neutral" },
};

function ControlRow({ p, cutoff }: { p: RetroPositive; cutoff: number }) {
  const s = STATUS_LABEL[p.status];
  const anticipated = p.status.startsWith("anticipated");
  return (
    <div className="rounded-xl border border-line/10 bg-surface2/30 p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <span className="font-mono text-[0.8rem] text-text">{p.gene}</span>
          <span className="ml-1.5 text-[0.72rem] text-muted">
            {p.relation.replace(/_/g, " ")} → {p.target_terms.join(", ")}
          </span>
        </div>
        <Badge tone={s.tone}>{s.text}</Badge>
      </div>

      <div className="mt-1.5 text-[0.7rem] text-muted">
        Confirmed by a <span className="font-mono text-text">{p.confirm_year}</span> paper —{" "}
        {p.confirm_year && p.confirm_year > cutoff ? (
          <span className="text-faint">unseen by the {cutoff} graph.</span>
        ) : (
          <span className="text-faint">already visible.</span>
        )}
      </div>

      {anticipated && p.pre_cutoff_signal.length > 0 && (
        <div className="mt-2">
          <div className="text-[0.62rem] uppercase tracking-wide text-faint">
            pre-{cutoff} signal that pointed here
          </div>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {p.pre_cutoff_signal.map((sig, i) => (
              <SignalChip key={i} sig={sig} />
            ))}
          </div>
        </div>
      )}

      {p.status === "not_anticipable" && (
        <p className="mt-1.5 text-[0.66rem] text-faint">
          No pre-{cutoff} evidence on this gene — the engine correctly claims no foresight
          here rather than inventing one.
        </p>
      )}
    </div>
  );
}

function SignalChip({ sig }: { sig: RetroSignal }) {
  const href = sig.provenance?.ref_url || sig.provenance?.pubmed_url || undefined;
  const label = `${sig.year ?? "?"} · ${sig.grounded ? "grounded" : "abstract"}`;
  const body = (
    <span className="font-mono text-[0.6rem]">
      {label}
      {sig.target ? <span className="text-faint"> · {sig.target}</span> : null}
    </span>
  );
  const cls =
    "rounded-md px-1.5 py-0.5 ring-1 ring-inset " +
    (sig.grounded
      ? "bg-accent/10 text-accentStrong ring-accent/25"
      : "bg-line/6 text-muted ring-line/15");
  return href ? (
    <a href={href} target="_blank" rel="noopener noreferrer" className={`${cls} hover:brightness-110`}>
      {body}
    </a>
  ) : (
    <span className={cls}>{body}</span>
  );
}
