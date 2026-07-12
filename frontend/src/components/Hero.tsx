"use client";
import { Badge } from "./ui";
import type { LineageStatus, Overview } from "@/lib/useLineage";

const ORGANISM = "Burkholderia multivorans";

export function Hero({
  overview,
  status,
}: {
  overview: Overview | null;
  status: LineageStatus;
}) {
  return (
    <section className="animate-rise">
      <div className="grid gap-8 lg:grid-cols-[1.1fr_1fr] lg:items-end">
        <div>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Badge tone="accent">Nextstrain, continued</Badge>
            <Badge tone="neutral">
              <span className="font-mono">provenance on every edge</span>
            </Badge>
          </div>
          <h1 className="text-[2rem] font-semibold leading-[1.08] tracking-tightest text-text sm:text-[2.7rem]">
            Collateral sensitivity is the pathogen&apos;s{" "}
            <span className="text-accentStrong">Achilles&apos; heel</span>.
          </h1>
          <p className="mt-4 max-w-xl text-[0.95rem] leading-relaxed text-muted">
            Trace resistance along the real experimental record — strain → flipper →
            structure → target → evidence — and turn reversible
            (&ldquo;flipper&rdquo;) mutation structure into evidence-backed
            antibiotic-cycling hypotheses. A deterministic core does the math;
            AlphaFold folds the targets; the model only reads and cites.
          </p>
        </div>

        <div className="rounded-2xl border border-line/10 bg-surface/60 p-5 shadow-card">
          <div className="flex items-center justify-between">
            <div className="text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-faint">
              Active cohort
            </div>
            <Badge tone={status === "ready" ? "live" : "neutral"}>
              {status === "ready" ? "loaded" : status}
            </Badge>
          </div>
          <div className="mt-2 text-xl font-medium italic text-text">{ORGANISM}</div>
          <p className="mt-1 text-xs text-muted">
            Real experimental-evolution record: isolates evolved along parallel
            lineages, with per-gene indel flippers vs the reference genome and
            per-lineage resistance/sensitivity.
          </p>
          <dl className="mt-4 grid grid-cols-3 gap-3">
            <MiniStat label="Isolates" value={overview?.strains} />
            <MiniStat label="Flipper-carrying" value={overview?.flipperCarriers} tone="accent" />
            <MiniStat label="Lineages" value={overview?.lineages.length} />
          </dl>
        </div>
      </div>

      <PipelineChain overview={overview} />
    </section>
  );
}

function MiniStat({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value?: number;
  tone?: "neutral" | "accent";
}) {
  return (
    <div>
      <div
        className={`font-mono text-2xl tabular-nums ${
          tone === "accent" ? "text-accentStrong" : "text-text"
        }`}
      >
        {value == null ? "—" : value}
      </div>
      <div className="mt-0.5 text-[0.68rem] leading-tight text-faint">{label}</div>
    </div>
  );
}

type Stage = {
  key: string;
  label: string;
  sub: string;
  phase: string;
  live: boolean;
  value?: number | string | null;
};

function PipelineChain({ overview }: { overview: Overview | null }) {
  const stages: Stage[] = [
    { key: "strain", label: "Strains", sub: "isolates + lineage", phase: "Phase 1", live: true, value: overview?.strains },
    { key: "variant", label: "Flippers", sub: "reversible indels", phase: "Phase 1", live: true, value: overview?.flipperCarriers },
    { key: "structure", label: "Structure", sub: "AlphaFold · Tamarind", phase: "Phase 5", live: true, value: "3D" },
    { key: "evidence", label: "Evidence", sub: "grounded claims", phase: "Phase 2", live: false },
    { key: "cycle", label: "Cycling", sub: "CS / RCS schedule", phase: "Phase 4", live: false },
  ];

  return (
    <div className="mt-8 overflow-x-auto">
      <ol className="flex min-w-[720px] items-stretch gap-2">
        {stages.map((s, i) => (
          <li key={s.key} className="flex flex-1 items-center gap-2">
            <StageCard stage={s} />
            {i < stages.length - 1 && <Connector active={s.live && stages[i + 1].live} />}
          </li>
        ))}
      </ol>
    </div>
  );
}

function StageCard({ stage }: { stage: Stage }) {
  return (
    <div
      className={`flex-1 rounded-xl border px-3.5 py-3 transition ${
        stage.live
          ? "border-accent/25 bg-accent/[0.06]"
          : "border-line/10 bg-surface/50"
      }`}
    >
      <div className="flex items-center justify-between">
        <span className={`text-sm font-semibold ${stage.live ? "text-text" : "text-muted"}`}>
          {stage.label}
        </span>
        {stage.live ? (
          <span className="font-mono text-base tabular-nums text-accentStrong">
            {stage.value ?? "—"}
          </span>
        ) : (
          <span className="rounded-full bg-line/8 px-1.5 py-0.5 font-mono text-[0.58rem] uppercase tracking-wide text-faint">
            {stage.phase}
          </span>
        )}
      </div>
      <div className="mt-0.5 text-[0.68rem] text-faint">{stage.sub}</div>
    </div>
  );
}

function Connector({ active }: { active: boolean }) {
  return (
    <svg width="26" height="12" viewBox="0 0 26 12" className="shrink-0" aria-hidden>
      <line
        x1="1"
        y1="6"
        x2="25"
        y2="6"
        stroke={active ? "rgb(var(--accent))" : "rgb(var(--line) / 0.25)"}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeDasharray="1 4"
        style={active ? { animation: "dash 0.8s linear infinite" } : undefined}
      />
    </svg>
  );
}
