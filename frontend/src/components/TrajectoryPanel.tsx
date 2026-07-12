"use client";
// "What real evolution did next" — the counterfactual beat. This is RETRIEVAL over real
// evolved lineages, never prediction: for a strain's resistance event, it shows which
// drugs became viable again in real lineages, backed by specific real strains. The
// OBSERVED data and any NARRATED text are visibly separated. When the real data can't
// support an answer (e.g. the public PubMLST path), it shows an honest "insufficient
// real evidence" state — that honesty is the feature.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Panel, Badge } from "./ui";
import type { TrajectoryEvidence } from "@/lib/types";

export function TrajectoryPanel({
  strainId,
  onSelectStrainLabel,
}: {
  strainId: string | null;
  onSelectStrainLabel?: (label: string) => void;
}) {
  const [data, setData] = useState<TrajectoryEvidence | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "insufficient" | "error">(
    "idle",
  );

  useEffect(() => {
    if (!strainId) {
      setStatus("idle");
      setData(null);
      return;
    }
    let live = true;
    setStatus("loading");
    setData(null);
    api
      .trajectory(strainId)
      .then((d) => {
        if (!live) return;
        setData(d);
        setStatus(d.sufficient && d.observed_next.length > 0 ? "ready" : "insufficient");
      })
      .catch(() => live && setStatus("error"));
    return () => {
      live = false;
    };
  }, [strainId]);

  return (
    <Panel
      title="What real evolution did next"
      aside={
        <span className="flex items-center gap-1.5">
          <Badge tone="accent">retrieved, not predicted</Badge>
        </span>
      }
    >
      {status === "idle" && (
        <Empty>
          Select a strain with a recorded resistance event to see what real evolved
          lineages did next — retrieved from the data, never predicted.
        </Empty>
      )}
      {status === "loading" && (
        <div className="space-y-2">
          <div className="skeleton h-12 rounded-lg" />
          <div className="skeleton h-16 rounded-xl" />
          <div className="skeleton h-16 rounded-xl" />
        </div>
      )}
      {status === "error" && (
        <Empty>Trajectory service offline — start the API (`make backend`) and retry.</Empty>
      )}
      {status === "insufficient" && data && <Insufficient data={data} />}
      {status === "ready" && data && (
        <Ready data={data} onSelectStrainLabel={onSelectStrainLabel} />
      )}
    </Panel>
  );
}

function Ready({
  data,
  onSelectStrainLabel,
}: {
  data: TrajectoryEvidence;
  onSelectStrainLabel?: (label: string) => void;
}) {
  return (
    <div className="animate-fade">
      <div className="rounded-xl border border-line/10 bg-surface2/40 p-3">
        <div className="text-[0.78rem] leading-relaxed text-text">
          {data.event_strain ? (
            <>
              After strain <span className="font-mono">{data.event_strain}</span> acquired
              resistance to <span className="font-mono text-accentStrong">{data.resisted}</span>
              , real lineages did this next:
            </>
          ) : (
            <>
              Across real lineages that acquired resistance to{" "}
              <span className="font-mono text-accentStrong">{data.resisted}</span>:
            </>
          )}
        </div>
        <div className="mt-1 text-[0.64rem] uppercase tracking-wide text-faint">
          observed across {data.support_lineages} lineage
          {data.support_lineages === 1 ? "" : "s"} · {data.backing_strains.length} strains
        </div>
      </div>

      <ul className="mt-2.5 space-y-2">
        {data.observed_next.map((o) => (
          <li key={o.sensitized_to} className="rounded-xl border border-accent/20 bg-accent/[0.04] p-3">
            <div className="flex items-center justify-between gap-2">
              <div className="text-[0.82rem] text-text">
                <span className="font-mono text-accentStrong">{o.sensitized_to}</span> became
                viable again
              </div>
              <Badge tone="accent">observed</Badge>
            </div>
            <div className="mt-1 text-[0.66rem] text-muted">
              in {o.n_lineages} real lineage{o.n_lineages === 1 ? "" : "s"} ({o.n_strains} strain
              {o.n_strains === 1 ? "" : "s"}) — {o.lineages.join(", ")}
            </div>
            <div className="mt-1.5 flex flex-wrap items-center gap-1">
              <span className="text-[0.6rem] uppercase tracking-wide text-faint">backing</span>
              {o.backing_strains.slice(0, 10).map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => onSelectStrainLabel?.(s)}
                  title={`Select strain ${s} in the lineage`}
                  className="rounded-md bg-line/6 px-1.5 py-0.5 font-mono text-[0.6rem] text-muted ring-1 ring-inset ring-line/15 transition hover:text-text hover:ring-line/30"
                >
                  {s}
                </button>
              ))}
              {o.backing_strains.length > 10 && (
                <span className="text-[0.6rem] text-faint">+{o.backing_strains.length - 10}</span>
              )}
            </div>
          </li>
        ))}
      </ul>

      {data.narrative?.summary && (
        <div className="mt-3 rounded-xl border border-line/12 bg-surface2/40 p-3">
          <div className="mb-1 flex items-center gap-2">
            <span className="text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-faint">
              Narrated
            </span>
            <span className="rounded bg-amber/10 px-1 py-px font-mono text-[0.54rem] uppercase tracking-wide text-amber ring-1 ring-inset ring-amber/25">
              LLM · describes the observed data
            </span>
          </div>
          <p className="text-[0.76rem] leading-relaxed text-muted">{data.narrative.summary}</p>
        </div>
      )}

      <Provenance data={data} />
    </div>
  );
}

function Insufficient({ data }: { data: TrajectoryEvidence }) {
  return (
    <div className="animate-fade">
      <div className="rounded-xl border border-dashed border-amber/30 bg-amber/[0.05] p-4">
        <div className="mb-1 flex items-center gap-2 text-[0.72rem] font-semibold text-amber">
          <Info /> Insufficient real evidence
        </div>
        <p className="text-[0.76rem] leading-relaxed text-muted">
          {data.note ||
            "No real lineage in the dataset supports a trajectory for this event."}{" "}
          Rather than fabricate a plausible-looking path, the counterfactual is left
          empty — a gap is shown, not filled. This beat only reports what real evolved
          lineages actually did.
        </p>
        {data.backing_strains.length > 0 && (
          <div className="mt-2 text-[0.66rem] text-faint">
            The resistance event is real (strains {data.backing_strains.slice(0, 8).join(", ")}
            ), but no collateral outcome followed it in the record.
          </div>
        )}
      </div>
      <Provenance data={data} />
    </div>
  );
}

function Provenance({ data }: { data: TrajectoryEvidence }) {
  const method = (data.provenance?.method as string) ?? "deterministic retrieval — no prediction";
  return (
    <div className="mt-3 flex items-start gap-1.5 border-t border-line/8 pt-2 text-[0.64rem] leading-relaxed text-faint">
      <Lock />
      <span>
        Retrieved from real experimental-evolution lineages. {method}. The observed
        outcomes above trace to specific real strains; nothing here is generated.
      </span>
    </div>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-[9rem] items-center justify-center rounded-xl border border-dashed border-line/15 bg-surface2/40 px-4 text-center">
      <p className="max-w-sm text-xs leading-relaxed text-muted">{children}</p>
    </div>
  );
}

function Info() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-4M12 8h.01" />
    </svg>
  );
}

function Lock() {
  return (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mt-0.5 shrink-0 opacity-70" aria-hidden>
      <rect x="3" y="11" width="18" height="11" rx="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  );
}
