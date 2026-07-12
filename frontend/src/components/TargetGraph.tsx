"use client";
// Candidate-target graph for the selected strain. Phase 3 ranks targets with
// evidence chains (variant → mechanism → target); until then this previews the
// chain the panel will populate, and reacts to the current selection.
import { RoadmapPanel } from "./ui";

export function TargetGraph({ strainId }: { strainId: string | null }) {
  return (
    <RoadmapPanel
      title="Targets"
      phase="Phase 3"
      active={!!strainId}
      illustration={<ChainSchematic active={!!strainId} />}
      blurb={
        strainId ? (
          <>
            A strain is selected — Phase 3 will rank druggable targets for it and
            trace each back through the{" "}
            <span className="text-text">variant → mechanism → target</span> chain.
          </>
        ) : (
          <>
            Select a strain in the lineage. Phase 3 ranks candidate targets with a
            0–1 confidence and an evidence chain for each.
          </>
        )
      }
    />
  );
}

function ChainSchematic({ active }: { active: boolean }) {
  const nodeCls = active ? "text-text border-line/20 bg-surface" : "text-muted border-line/12 bg-surface";
  return (
    <div className="flex items-center gap-1.5 font-mono text-[0.66rem]">
      <span className={`rounded-md border px-2 py-1 ${nodeCls}`}>variant</span>
      <Link active={active} />
      <span className={`rounded-md border px-2 py-1 ${nodeCls}`}>mechanism</span>
      <Link active={active} />
      <span
        className={`rounded-md border px-2 py-1 ${
          active ? "border-accent/30 bg-accent/10 text-accentStrong" : "border-line/12 bg-surface text-muted"
        }`}
      >
        target
      </span>
    </div>
  );
}

function Link({ active }: { active: boolean }) {
  return (
    <svg width="26" height="8" viewBox="0 0 26 8" aria-hidden>
      <line
        x1="1"
        y1="4"
        x2="25"
        y2="4"
        stroke={active ? "rgb(var(--accent))" : "rgb(var(--line) / 0.28)"}
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeDasharray="1 3.5"
        style={active ? { animation: "dash 0.8s linear infinite" } : undefined}
      />
    </svg>
  );
}
