"use client";
// Small shared primitives so every surface shares one visual language.
import { clsx } from "@/lib/clsx";

export function Panel({
  title,
  aside,
  children,
  className,
  bodyClassName,
}: {
  title?: string;
  aside?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section
      className={clsx(
        "rounded-lg border border-line/12 bg-surface/80 shadow-card",
        className,
      )}
    >
      {title && (
        <header className="flex items-center justify-between gap-3 border-b border-line/10 px-4 py-2.5">
          <h2 className="text-[0.7rem] font-semibold uppercase tracking-[0.12em] text-faint">
            {title}
          </h2>
          {aside}
        </header>
      )}
      <div className={clsx("p-4", bodyClassName)}>{children}</div>
    </section>
  );
}

export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: React.ReactNode;
  tone?: "neutral" | "accent" | "danger" | "amber" | "live";
  className?: string;
}) {
  const tones: Record<string, string> = {
    neutral: "bg-line/6 text-muted ring-line/12",
    accent: "bg-accent/12 text-accentStrong ring-accent/25",
    danger: "bg-danger/12 text-danger ring-danger/25",
    amber: "bg-amber/12 text-amber ring-amber/25",
    live: "bg-accent/12 text-accentStrong ring-accent/25",
  };
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded px-1.5 py-0.5 text-[0.68rem] font-medium ring-1 ring-inset",
        tones[tone],
        className,
      )}
    >
      {tone === "live" && (
        <span className="relative flex h-1.5 w-1.5">
          <span className="pulse-dot absolute inline-flex h-1.5 w-1.5 rounded-full bg-accent" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-accent" />
        </span>
      )}
      {children}
    </span>
  );
}

export function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-faint">
      {children}
    </div>
  );
}

export function RoadmapPanel({
  title,
  phase,
  blurb,
  illustration,
  active,
}: {
  title: string;
  phase: string;
  blurb: React.ReactNode;
  illustration: React.ReactNode;
  active?: boolean;
}) {
  return (
    <Panel
      title={title}
      aside={
        <Badge tone={active ? "accent" : "neutral"}>{active ? "primed" : phase}</Badge>
      }
      className="h-full"
    >
      <div className="flex h-full flex-col">
        <div
          className={clsx(
            "grid flex-1 place-items-center rounded-xl border border-dashed border-line/12 bg-surface2/40 px-3 py-6 transition",
            active ? "opacity-100" : "opacity-90",
          )}
        >
          {illustration}
        </div>
        <p className="mt-3 text-xs leading-relaxed text-muted">{blurb}</p>
      </div>
    </Panel>
  );
}

export function Empty({
  title,
  children,
  icon,
}: {
  title?: string;
  children: React.ReactNode;
  icon?: React.ReactNode;
}) {
  return (
    <div className="flex min-h-[9rem] flex-col items-center justify-center rounded-xl border border-dashed border-line/15 bg-surface2/40 px-4 py-6 text-center">
      {icon && <div className="mb-2 text-faint">{icon}</div>}
      {title && <div className="mb-1 text-sm font-medium text-text">{title}</div>}
      <div className="max-w-xs text-xs leading-relaxed text-muted">{children}</div>
    </div>
  );
}
