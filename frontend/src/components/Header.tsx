"use client";
import Link from "next/link";
import { ThemeToggle } from "./ThemeToggle";
import type { LineageStatus } from "@/lib/useLineage";

export function Header({
  status,
  demo,
  onToggleDemo,
}: {
  status: LineageStatus;
  demo?: boolean;
  onToggleDemo?: (next: boolean) => void;
}) {
  return (
    <header className="animate-fade sticky top-0 z-30 border-b border-line/8 bg-bg/60 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-3">
        <Link href="/" className="flex items-center gap-3 transition-opacity hover:opacity-80">
          <Mark />
          <div className="leading-none">
            <span className="text-[1.35rem] font-semibold tracking-tightest text-gradient-green">
              Achilles
            </span>
          </div>
        </Link>

        <div className="flex items-center gap-2.5">
          {onToggleDemo && <DemoToggle demo={!!demo} onToggle={onToggleDemo} />}
          <ConnectionPill status={status} demo={demo} />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}

function DemoToggle({ demo, onToggle }: { demo: boolean; onToggle: (n: boolean) => void }) {
  return (
    <button
      onClick={() => onToggle(!demo)}
      className={
        "inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-[0.7rem] font-medium transition " +
        (demo
          ? "border-accent/30 bg-accent/10 text-accentStrong"
          : "border-line/12 bg-surface/70 text-muted hover:text-text")
      }
      title="Load an example dataset (Burkholderia AMR) to populate the console"
    >
      <span
        className={
          "relative h-3.5 w-6 rounded-full transition-colors " +
          (demo ? "bg-accent/40" : "bg-line/20")
        }
      >
        <span
          className={
            "absolute top-0.5 h-2.5 w-2.5 rounded-full bg-surface shadow transition-all " +
            (demo ? "left-3" : "left-0.5")
          }
        />
      </span>
      Demo data
    </button>
  );
}

function ConnectionPill({ status, demo }: { status: LineageStatus; demo?: boolean }) {
  if (!demo) {
    return (
      <span className="hidden items-center gap-2 rounded-full border border-line/10 bg-surface/70 px-2.5 py-1 text-[0.7rem] font-medium text-muted sm:inline-flex">
        <span className="h-1.5 w-1.5 rounded-full bg-faint" />
        No dataset loaded
      </span>
    );
  }
  const map = {
    loading: { label: "Connecting", cls: "text-amber", dot: "bg-amber" },
    ready: { label: "Live · demo dataset", cls: "text-accentStrong", dot: "bg-accent" },
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
