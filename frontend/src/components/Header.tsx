"use client";
import { ThemeToggle } from "./ThemeToggle";
import type { LineageStatus } from "@/lib/useLineage";

export function Header({ status }: { status: LineageStatus }) {
  return (
    <header className="animate-fade sticky top-0 z-30 border-b border-line/8 bg-bg/60 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-3">
        <div className="flex items-center gap-3">
          <Mark />
          <div className="leading-none">
            <div className="flex items-center gap-2">
              <span className="text-[1.35rem] font-semibold tracking-tightest text-gradient-green">
                Achilles
              </span>
              <span className="rounded-full border border-line/12 px-1.5 py-0.5 font-mono text-[0.6rem] uppercase tracking-wider text-faint">
                v1 · Phases 1–5
              </span>
            </div>
            <div className="mt-1 hidden text-[0.7rem] text-muted sm:block">
              Antimicrobial-resistance target &amp; treatment intelligence
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <ConnectionPill status={status} />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}

function ConnectionPill({ status }: { status: LineageStatus }) {
  const map = {
    loading: { label: "Connecting", cls: "text-amber", dot: "bg-amber" },
    ready: { label: "Live · seeded demo", cls: "text-accentStrong", dot: "bg-accent" },
    empty: { label: "No data — run seed", cls: "text-muted", dot: "bg-faint" },
    error: { label: "API offline", cls: "text-danger", dot: "bg-danger" },
  }[status];

  return (
    <span
      className={`hidden items-center gap-2 rounded-full border border-line/10 bg-surface/70 px-2.5 py-1 text-[0.7rem] font-medium sm:inline-flex ${map.cls}`}
    >
      <span className="relative flex h-1.5 w-1.5">
        {status === "ready" && (
          <span className={`pulse-dot absolute inline-flex h-1.5 w-1.5 rounded-full ${map.dot}`} />
        )}
        <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${map.dot}`} />
      </span>
      {map.label}
    </span>
  );
}

// A quiet geometric mark: a lineage fork whose leaf is the exposed "heel" node.
function Mark() {
  return (
    <span className="grid h-9 w-9 place-items-center rounded-xl border border-accent/20 bg-surface/70 shadow-glow-sm transition-transform duration-300 hover:-rotate-6 hover:scale-110">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path
          d="M5 12 H11 M11 12 L17 6 M11 12 L17 18"
          stroke="rgb(var(--muted))"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
        <circle cx="4.5" cy="12" r="1.7" fill="rgb(var(--muted))" />
        <circle cx="17.5" cy="6" r="1.7" fill="rgb(var(--muted))" />
        <circle cx="17.6" cy="18" r="2.4" fill="rgb(var(--accent))" />
      </svg>
    </span>
  );
}
