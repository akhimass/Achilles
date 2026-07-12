"use client";
import { Panel, SectionLabel } from "./ui";
import type { Overview } from "@/lib/useLineage";

export function Insights({ overview }: { overview: Overview | null }) {
  if (!overview) {
    return (
      <Panel title="Cohort insights">
        <div className="space-y-3">
          <div className="skeleton h-16 rounded-lg" />
          <div className="skeleton h-16 rounded-lg" />
        </div>
      </Panel>
    );
  }

  const { flipperHistogram, countries, lineages, founders, yearMin, yearMax, strains } = overview;
  const maxBar = Math.max(1, ...flipperHistogram);
  // BurkData exposes experimental lineages; the PubMLST source exposes geography.
  const useLineages = lineages.length > 0;
  const groups = useLineages ? lineages : countries.slice(0, 8);
  const maxGroup = Math.max(1, ...groups.map((g) => g.count));

  return (
    <Panel title="Cohort insights">
      <div className="space-y-5">
        <div>
          <div className="mb-2 flex items-center justify-between">
            <SectionLabel>Flipper distribution</SectionLabel>
            <span className="text-[0.68rem] text-faint">strains by flipper count</span>
          </div>
          <div className="flex items-end gap-1.5" style={{ height: 64 }}>
            {flipperHistogram.map((count, i) => (
              <div key={i} className="group flex flex-1 flex-col items-center justify-end gap-1">
                <span className="text-[0.6rem] tabular-nums text-faint opacity-0 transition group-hover:opacity-100">
                  {count}
                </span>
                <div
                  className="w-full rounded-t-[3px] transition"
                  style={{
                    height: `${(count / maxBar) * 46 + 2}px`,
                    background:
                      i === 0
                        ? "rgb(var(--line) / 0.18)"
                        : `color-mix(in oklab, rgb(var(--accent)) ${40 + (i / flipperHistogram.length) * 60}%, rgb(var(--surface-3)))`,
                  }}
                />
                <span className="font-mono text-[0.6rem] text-faint">{i}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="h-px bg-line/8" />

        <div>
          <div className="mb-2 flex items-center justify-between">
            <SectionLabel>{useLineages ? "Lineages" : "Geography"}</SectionLabel>
            <span className="text-[0.68rem] text-faint">
              {useLineages ? `${lineages.length} paths · ${founders} founders` : `${countries.length} countries`}
            </span>
          </div>
          <ul className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
            {groups.map((g) => (
              <li key={g.name} className="flex items-center gap-2">
                <span className="w-10 shrink-0 truncate font-mono text-[0.68rem] text-muted">{g.name}</span>
                <span className="relative h-2 flex-1 overflow-hidden rounded-full bg-line/8">
                  <span
                    className="absolute inset-y-0 left-0 rounded-full bg-accent/70"
                    style={{ width: `${(g.count / maxGroup) * 100}%` }}
                  />
                </span>
                <span className="w-5 shrink-0 text-right font-mono text-[0.68rem] text-faint">
                  {g.count}
                </span>
              </li>
            ))}
          </ul>
        </div>

        <div className="h-px bg-line/8" />

        <div className="flex items-center justify-between text-sm">
          <SectionLabel>{useLineages ? "Design" : "Temporal span"}</SectionLabel>
          <span className="font-mono text-text">
            {useLineages ? `${founders} → ${strains}` : `${yearMin ?? "—"} – ${yearMax ?? "—"}`}
          </span>
        </div>
        <p className="-mt-3 text-[0.68rem] text-faint">
          {useLineages
            ? `${founders} founders evolved into ${strains} isolates across ${lineages.length} lineages.`
            : `${strains} isolates spanning ${yearMin && yearMax ? `${yearMax - yearMin} years` : "the record"}.`}
        </p>
      </div>
    </Panel>
  );
}
