"use client";
// Antibiotic-cycling suggestion. The cycle is computed server-side (deterministic
// collateral-sensitivity math); the model only narrates it with citations. Phase 4
// wires the computation — this previews the reciprocal-sensitivity loop it yields.
import { RoadmapPanel } from "./ui";

export function CyclingView({ organism }: { organism: string }) {
  void organism;
  return (
    <RoadmapPanel
      title="Cycling"
      phase="Phase 4"
      illustration={<ReciprocalLoop />}
      blurb={
        <>
          Reversible (&ldquo;flipper&rdquo;) structure yields reciprocal
          collateral-sensitivity pairs — the basis for an alternating regimen that
          keeps resistance from fixing. Always a{" "}
          <span className="text-text">research hypothesis</span>, never a treatment
          plan.
        </>
      }
    />
  );
}

function ReciprocalLoop() {
  return (
    <div className="flex items-center gap-3 font-mono text-xs">
      <span className="rounded-md border border-line/15 bg-surface px-2.5 py-1 text-text">MEM</span>
      <svg width="52" height="30" viewBox="0 0 52 30" aria-hidden>
        <path d="M4 9 H44 M40 5.5 L46 9 L40 12.5" stroke="rgb(var(--accent))" strokeWidth="1.3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M48 21 H8 M12 17.5 L6 21 L12 24.5" stroke="rgb(var(--danger))" strokeWidth="1.3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        <text x="26" y="5" textAnchor="middle" fontSize="6" fill="rgb(var(--faint))">sensitizes</text>
        <text x="26" y="30" textAnchor="middle" fontSize="6" fill="rgb(var(--faint))">sensitizes</text>
      </svg>
      <span className="rounded-md border border-line/15 bg-surface px-2.5 py-1 text-text">CHL</span>
    </div>
  );
}
