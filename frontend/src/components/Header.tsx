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
    <header className="sticky top-0 z-30 border-b border-line/10 bg-bg/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-[88rem] items-center justify-between gap-4 px-6 py-3">
        <Link href="/" className="flex items-center gap-2.5 transition-opacity hover:opacity-80">
          <Mark />
          <div className="leading-none">
            <span className="font-serif text-[1.2rem] tracking-tight text-text">Achilles</span>
            <div className="mt-0.5 hidden text-[0.68rem] text-muted sm:block">
              AMR evidence console
            </div>
          </div>
        </Link>

        <div className="flex items-center gap-2.5">
          {onToggleDemo && <DemoToggle demo={!!demo} onToggle={onToggleDemo} />}
          <StatusLabel status={status} demo={demo} />
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
        "inline-flex items-center gap-2 rounded-md border px-2.5 py-1 text-[0.72rem] font-medium transition " +
        (demo
          ? "border-accent/30 bg-accent/10 text-accentStrong"
          : "border-line/15 bg-surface/70 text-muted hover:text-text")
      }
      title="Load the public Burkholderia multivorans example graph"
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
      Demo graph
    </button>
  );
}

function StatusLabel({ status, demo }: { status: LineageStatus; demo?: boolean }) {
  if (!demo) {
    return (
      <span className="hidden items-center gap-2 rounded-md border border-line/12 bg-surface/70 px-2.5 py-1 text-[0.72rem] text-muted sm:inline-flex">
        <span className="h-1.5 w-1.5 rounded-full bg-faint" />
        No dataset
      </span>
    );
  }
  const map = {
    loading: { label: "Loading", cls: "text-amber", dot: "bg-amber" },
    ready: { label: "B. multivorans · live", cls: "text-accentStrong", dot: "bg-accent" },
    empty: { label: "Empty — run seed", cls: "text-muted", dot: "bg-faint" },
    error: { label: "API offline", cls: "text-danger", dot: "bg-danger" },
  }[status];

  return (
    <span
      className={`hidden items-center gap-2 rounded-md border border-line/12 bg-surface/70 px-2.5 py-1 text-[0.72rem] font-medium sm:inline-flex ${map.cls}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${map.dot}`} />
      {map.label}
    </span>
  );
}

function Mark() {
  return (
    <span className="grid h-8 w-8 place-items-center rounded-md border border-line/15 bg-surface/80">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
        <path
          d="M5 12 H11 M11 12 L17 6 M11 12 L17 18"
          stroke="rgb(var(--muted))"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
        <circle cx="4.5" cy="12" r="1.6" fill="rgb(var(--muted))" />
        <circle cx="17.5" cy="6" r="1.6" fill="rgb(var(--muted))" />
        <circle cx="17.6" cy="18" r="2.2" fill="rgb(var(--accent))" />
      </svg>
    </span>
  );
}
