"use client";
// The "prove-it" panel — the edge a search box can't match. The engine is run against
// independent PUBLIC ground truth: it must RECOVER known resistance relationships from
// grounded evidence (recall) and REFUSE planted false ones (precision, 0 fabrications).
// Both are computed and cited, live — not asserted.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { clsx } from "@/lib/clsx";
import { Panel, Badge } from "./ui";
import type { ValidationReport, ValidationItem } from "@/lib/types";

export function ValidationPanel() {
  const [data, setData] = useState<ValidationReport | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let live = true;
    api
      .validation()
      .then((d) => {
        if (!live) return;
        setData(d);
        setStatus("ready");
      })
      .catch(() => live && setStatus("error"));
    return () => {
      live = false;
    };
  }, []);

  const m = data?.metrics;

  return (
    <Panel
      title="Prove it — the engine checks itself"
      aside={
        m ? (
          <Badge tone={m.clean ? "accent" : "danger"}>
            {m.clean ? "0 fabricated" : `${m.fabricated} fabricated`}
          </Badge>
        ) : (
          <span className="font-mono text-[0.68rem] text-faint">public ground truth</span>
        )
      }
    >
      {status === "loading" && (
        <div className="space-y-2">
          <div className="skeleton h-16 rounded-xl" />
          <div className="skeleton h-24 rounded-xl" />
        </div>
      )}
      {status === "error" && (
        <p className="text-xs text-muted">Validation offline — start the API and retry.</p>
      )}
      {status === "ready" && data && m && (
        <div className="animate-fade">
          <p className="mb-3 text-[0.8rem] leading-relaxed text-muted">
            A retrieval tool returns whatever is in its index. Achilles is held to
            independent, publicly-cited ground truth — it must{" "}
            <span className="text-text">recover</span> known resistance biology from
            grounded evidence and <span className="text-text">refuse</span> planted false
            claims. Computed live, every recovery cited.
          </p>

          <div className="grid grid-cols-3 gap-2.5">
            <Metric
              label="Known recovered"
              value={`${m.recovered}/${m.positives}`}
              sub={`${Math.round(m.recovery_rate * 100)}% recall`}
              tone="accent"
            />
            <Metric
              label="False refused"
              value={`${m.refused}/${m.negatives}`}
              sub="precision controls"
              tone="accent"
            />
            <Metric
              label="Fabricated"
              value={`${m.fabricated}`}
              sub={m.clean ? "provably clean" : "review needed"}
              tone={m.clean ? "accent" : "danger"}
            />
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <Controls
              title="Known-true → recovered"
              items={data.items.filter((i) => i.kind === "positive")}
            />
            <Controls
              title="Known-false → refused"
              items={data.items.filter((i) => i.kind === "negative")}
            />
          </div>
        </div>
      )}
    </Panel>
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
  tone: "accent" | "danger";
}) {
  return (
    <div className="rounded-xl border border-line/10 bg-surface2/40 p-3">
      <div className="text-[0.6rem] uppercase tracking-wide text-faint">{label}</div>
      <div
        className={clsx(
          "mt-0.5 font-mono text-2xl tabular-nums",
          tone === "danger" ? "text-danger" : "text-accentStrong",
        )}
      >
        {value}
      </div>
      <div className="mt-0.5 text-[0.62rem] text-muted">{sub}</div>
    </div>
  );
}

const STATUS_TONE: Record<string, string> = {
  recovered: "bg-accent/10 text-accentStrong ring-accent/25",
  refused: "bg-accent/10 text-accentStrong ring-accent/25",
  literature_only: "bg-amber/10 text-amber ring-amber/25",
  weakly_asserted: "bg-amber/10 text-amber ring-amber/25",
  missing: "bg-line/8 text-muted ring-line/15",
  fabricated: "bg-danger/12 text-danger ring-danger/25",
};

function Controls({ title, items }: { title: string; items: ValidationItem[] }) {
  return (
    <div>
      <div className="mb-1.5 text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-faint">
        {title}
      </div>
      <ul className="space-y-1.5">
        {items.map((i, idx) => {
          const cite = i.grounded
            ? i.provenance.acc
              ? `${i.provenance.db} ${i.provenance.acc}`
              : i.provenance.pmid
                ? `PMID ${i.provenance.pmid}`
                : null
            : i.expected_citation;
          const href = i.provenance.ref_url || i.provenance.pubmed_url || undefined;
          return (
            <li key={idx} className="rounded-lg border border-line/10 bg-surface2/30 p-2">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 text-[0.74rem] text-text">
                  <span className="font-mono">{i.gene}</span>{" "}
                  <span className="text-muted">{i.relation.replace(/_/g, " ")}</span>{" "}
                  <span className="font-medium">{i.target_terms[0]}</span>
                </div>
                <span
                  className={clsx(
                    "shrink-0 rounded px-1 py-px font-mono text-[0.54rem] uppercase tracking-wide ring-1 ring-inset",
                    STATUS_TONE[i.status] ?? "bg-line/8 text-muted ring-line/15",
                  )}
                >
                  {i.status.replace(/_/g, " ")}
                </span>
              </div>
              {cite && (
                <div className="mt-1">
                  {href ? (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-mono text-[0.6rem] text-accentStrong hover:underline"
                    >
                      {cite}
                    </a>
                  ) : (
                    <span className="font-mono text-[0.6rem] text-faint">{cite}</span>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
