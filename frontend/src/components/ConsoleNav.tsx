"use client";
// Story-driven console navigation. A sticky rail that (1) lets a visitor read the app
// as one of three audiences — bench/AMR researcher, physician, computational researcher
// — and (2) scrollspy-tracks the pipeline chapters. Purely presentational: the page
// owns persona + active state and passes them down.
import type { ReactElement } from "react";

export type Persona = "all" | "researcher" | "physician" | "computational";

export interface NavSection {
  id: string;
  label: string;
  group: string;
  personas: Exclude<Persona, "all">[];
}

export const PERSONAS: { id: Persona; label: string; blurb: string }[] = [
  { id: "all", label: "Everything", blurb: "The full pipeline, end to end." },
  {
    id: "researcher",
    label: "Researcher",
    blurb: "Build lineage from your strains, trace every claim to source, rank reversible targets.",
  },
  {
    id: "physician",
    label: "Physician",
    blurb: "Treatment optimization grounded in what real evolved lineages did — a cited hypothesis, never advice.",
  },
  {
    id: "computational",
    label: "Computational",
    blurb: "A deterministic core + provenance-checked graph you can validate, retrodict, and reproduce offline.",
  },
];

export function ConsoleNav({
  sections,
  active,
  persona,
  onPersona,
  onJump,
}: {
  sections: NavSection[];
  active: string;
  persona: Persona;
  onPersona: (p: Persona) => void;
  onJump: (id: string) => void;
}) {
  const visible = sections.filter((s) => persona === "all" || s.personas.includes(persona));
  const groups = visible.reduce<Record<string, NavSection[]>>((acc, s) => {
    (acc[s.group] ??= []).push(s);
    return acc;
  }, {});

  return (
    <nav className="hidden w-60 shrink-0 lg:block">
      <div className="sticky top-24 max-h-[calc(100vh-7rem)] overflow-y-auto pr-1">
        {/* Persona switcher */}
        <div className="mb-5">
          <div className="mb-2 px-1 text-[0.6rem] font-semibold uppercase tracking-[0.16em] text-faint">
            Read this as
          </div>
          <div className="space-y-1">
            {PERSONAS.map((p) => {
              const on = persona === p.id;
              return (
                <button
                  key={p.id}
                  onClick={() => onPersona(p.id)}
                  className={
                    "group flex w-full items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-left transition " +
                    (on
                      ? "bg-accent/12 ring-1 ring-inset ring-accent/30"
                      : "hover:bg-surface2/60")
                  }
                >
                  <PersonaIcon id={p.id} on={on} />
                  <span
                    className={
                      "text-[0.82rem] font-medium " + (on ? "text-accentStrong" : "text-muted")
                    }
                  >
                    {p.label}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="mb-4 h-px bg-line/10" />

        {/* Chapter scrollspy */}
        <div className="space-y-4">
          {Object.entries(groups).map(([group, items]) => (
            <div key={group}>
              <div className="mb-1.5 px-1 text-[0.6rem] font-semibold uppercase tracking-[0.16em] text-faint">
                {group}
              </div>
              <ul className="space-y-0.5">
                {items.map((s) => {
                  const on = active === s.id;
                  return (
                    <li key={s.id}>
                      <button
                        onClick={() => onJump(s.id)}
                        className={
                          "relative flex w-full items-center gap-2.5 rounded-md py-1.5 pl-3 pr-2 text-left transition " +
                          (on ? "text-text" : "text-muted hover:text-text hover:bg-surface2/40")
                        }
                      >
                        <span
                          className={
                            "absolute left-0 top-1/2 h-4 w-[2px] -translate-y-1/2 rounded-full transition-all " +
                            (on ? "bg-accent opacity-100" : "opacity-0")
                          }
                        />
                        <SectionIcon id={s.id} on={on} />
                        <span className="text-[0.82rem]">{s.label}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-5 rounded-lg border border-line/10 bg-surface2/30 px-2.5 py-2">
          <div className="flex items-center gap-1.5 text-[0.62rem] text-faint">
            <Dot /> provenance on every edge
          </div>
        </div>
      </div>
    </nav>
  );
}

function PersonaIcon({ id, on }: { id: Persona; on: boolean }) {
  const cls = "h-4 w-4 shrink-0 " + (on ? "text-accentStrong" : "text-faint");
  const p = { fill: "none", stroke: "currentColor", strokeWidth: 1.7, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  if (id === "researcher")
    return (
      <svg viewBox="0 0 24 24" className={cls} {...p}>
        <path d="M9 3h6M10 3v6.5L5 18a2 2 0 0 0 1.8 3h10.4A2 2 0 0 0 19 18l-5-8.5V3" />
        <path d="M7.5 14h9" />
      </svg>
    );
  if (id === "physician")
    return (
      <svg viewBox="0 0 24 24" className={cls} {...p}>
        <path d="M19 14c-1.5 3-4.5 5-7 5s-5.5-2-7-5" />
        <path d="M5 14V8a3 3 0 0 1 3-3M12 19v2" />
        <circle cx="19" cy="12" r="2" />
      </svg>
    );
  if (id === "computational")
    return (
      <svg viewBox="0 0 24 24" className={cls} {...p}>
        <path d="M8 8l-4 4 4 4M16 8l4 4-4 4M13 5l-2 14" />
      </svg>
    );
  return (
    <svg viewBox="0 0 24 24" className={cls} {...p}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  );
}

function SectionIcon({ id, on }: { id: string; on: boolean }) {
  const cls = "h-3.5 w-3.5 shrink-0 " + (on ? "text-accentStrong" : "text-faint");
  const p = { fill: "none", stroke: "currentColor", strokeWidth: 1.7, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  const paths: Record<string, ReactElement> = {
    overview: <path d="M3 12l9-9 9 9M5 10v10h14V10" />,
    prove: <><path d="M9 12l2 2 4-4" /><path d="M12 3l7 3v6c0 4-3 7-7 9-4-2-7-5-7-9V6z" /></>,
    lineage: <><circle cx="6" cy="6" r="2" /><circle cx="6" cy="18" r="2" /><circle cx="18" cy="12" r="2" /><path d="M8 6h4a4 4 0 0 1 4 4M8 18h4a4 4 0 0 0 4-4" /></>,
    evidence: <><circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" /></>,
    targets: <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3" /></>,
    treatment: <><path d="M10.5 3.5a4 4 0 0 1 5.6 5.6l-8 8a4 4 0 0 1-5.6-5.6z" /><path d="M8 8l8 8" /></>,
    how: <><circle cx="12" cy="12" r="9" /><path d="M12 8v4l3 2" /></>,
  };
  return (
    <svg viewBox="0 0 24 24" className={cls} {...p}>
      {paths[id] ?? <circle cx="12" cy="12" r="3" />}
    </svg>
  );
}

function Dot() {
  return <span className="h-1.5 w-1.5 rounded-full bg-accent/70" />;
}
