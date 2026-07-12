"use client";
// Docking / druggability beat — the tractability → structure → inhibitor tie. Each
// ligand is a known inhibitor traced to a grounded evidence edge (never invented);
// Tamarind Bio folds the target (AlphaFold), predicts ADMET drug properties, and docks
// the inhibitor into the structure. Pose/score/props appear only when a real Tamarind
// job returns them — otherwise the ligand is shown "ready to dock".
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Panel, Badge } from "./ui";
import type { DockingResponse, DockingTarget } from "@/lib/types";

export function DockingPanel() {
  const [data, setData] = useState<DockingResponse | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "empty" | "error">("loading");

  useEffect(() => {
    let live = true;
    api
      .docking()
      .then((d) => {
        if (!live) return;
        setData(d);
        setStatus(d.targets.length ? "ready" : "empty");
      })
      .catch(() => live && setStatus("error"));
    return () => {
      live = false;
    };
  }, []);

  return (
    <Panel
      title="Docking · druggability"
      aside={
        data ? (
          <Badge tone="accent">{data.counts.docked} docked · Tamarind</Badge>
        ) : (
          <span className="font-mono text-[0.68rem] text-faint">cited inhibitors</span>
        )
      }
    >
      {status === "loading" && <div className="skeleton h-24 rounded-xl" />}
      {status === "error" && (
        <p className="text-xs text-muted">Docking service offline — start the API and retry.</p>
      )}
      {status === "empty" && (
        <p className="text-xs text-muted">No cited inhibitor for the current targets.</p>
      )}
      {status === "ready" && data && (
        <div className="animate-fade space-y-2.5">
          <p className="text-[0.78rem] leading-relaxed text-muted">
            Each ligand is a <span className="text-text">known inhibitor traced to a grounded
            edge</span> — not an invented molecule. Tamarind Bio folds the target, predicts{" "}
            <span className="text-text">ADMET</span> drug properties, and docks the inhibitor into
            the AlphaFold structure.
          </p>
          {data.targets.map((t) => (
            <TargetRow key={t.locus} t={t} />
          ))}
        </div>
      )}
    </Panel>
  );
}

function TargetRow({ t }: { t: DockingTarget }) {
  const lig = t.ligands[0];
  const tone =
    t.status === "docked" ? "accent" : t.status === "properties_only" ? "amber" : "neutral";
  const label =
    t.status === "docked"
      ? "docked"
      : t.status === "properties_only"
        ? "ADMET ready"
        : "ready to dock";
  return (
    <div className="rounded-xl border border-line/10 bg-surface2/30 p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <span className="font-mono text-[0.8rem] text-text">{lig?.name}</span>
          <span className="ml-1.5 font-mono text-[0.62rem] text-faint">{t.locus}</span>
          {lig?.role && <div className="mt-0.5 text-[0.7rem] text-muted">{lig.role}</div>}
        </div>
        <Badge tone={tone as "accent" | "amber" | "neutral"}>{label}</Badge>
      </div>

      <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
        {lig?.citation && (
          <span className="rounded-md bg-accent/10 px-1.5 py-0.5 font-mono text-[0.6rem] text-accentStrong ring-1 ring-inset ring-accent/25">
            {lig.citation}
          </span>
        )}
        {lig?.pubchem_url && (
          <a
            href={lig.pubchem_url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-md bg-line/6 px-1.5 py-0.5 font-mono text-[0.6rem] text-muted ring-1 ring-inset ring-line/15 hover:text-text"
          >
            PubChem {lig.pubchem_cid}
          </a>
        )}
        {t.docking?.score != null && (
          <span className="font-mono text-[0.62rem] text-accentStrong">
            dock score {t.docking.score}
          </span>
        )}
      </div>

      {t.admet?.properties && Object.keys(t.admet.properties).length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {Object.entries(t.admet.properties)
            .slice(0, 6)
            .map(([k, v]) => (
              <span
                key={k}
                className="rounded-md border border-line/12 bg-surface/40 px-1.5 py-0.5 font-mono text-[0.6rem] text-muted"
              >
                {k}: {String(v)}
              </span>
            ))}
        </div>
      )}

      {lig?.note && <p className="mt-2 text-[0.68rem] leading-relaxed text-faint">{lig.note}</p>}

      {t.status === "ready" && (
        <p className="mt-2 text-[0.66rem] text-faint">
          Run <span className="font-mono text-muted">make dock-targets</span> (with a Tamarind key)
          to compute the pose + ADMET.
        </p>
      )}
    </div>
  );
}
