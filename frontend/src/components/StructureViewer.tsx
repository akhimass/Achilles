"use client";
// The AI/ML beat: a flipper gene's protein, folded by AlphaFold (Tamarind Bio) or
// pulled from RCSB, rendered in 3D. AlphaFold models are colored by per-residue
// pLDDT confidence — the same gradient philosophy as the rest of the app.
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useIsDark } from "@/lib/useIsDark";
import { Panel, Badge, Empty } from "./ui";
import type { StructureResult } from "@/lib/types";

export function StructureViewer({
  locus,
  label,
}: {
  locus: string | null;
  label?: string | null;
}) {
  const [result, setResult] = useState<StructureResult | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "empty" | "error">("idle");
  const mountRef = useRef<HTMLDivElement | null>(null);
  const viewerRef = useRef<{ clear?: () => void } | null>(null);
  const isDark = useIsDark();

  useEffect(() => {
    if (!locus) {
      setResult(null);
      setStatus("idle");
      return;
    }
    let live = true;
    setStatus("loading");
    setResult(null);
    api
      .structure(locus, undefined, false)
      .then((r) => {
        if (!live) return;
        setResult(r);
        setStatus(r.pdb ? "ready" : "empty");
      })
      .catch(() => live && setStatus("error"));
    return () => {
      live = false;
    };
  }, [locus]);

  async function fold() {
    if (!locus) return;
    setStatus("loading");
    try {
      const r = await api.structure(locus, undefined, true);
      setResult(r);
      setStatus(r.pdb ? "ready" : "empty");
    } catch {
      setStatus("error");
    }
  }

  // Render the PDB with 3Dmol (dynamic import — WebGL, client only).
  useEffect(() => {
    if (status !== "ready" || !result?.pdb || !mountRef.current) return;
    let disposed = false;
    const el = mountRef.current;

    (async () => {
      const $3Dmol = await import("3dmol");
      if (disposed) return;
      el.innerHTML = "";
      const viewer = $3Dmol.createViewer(el, { backgroundColor: "white", backgroundAlpha: 0 });
      viewerRef.current = viewer;
      viewer.addModel(result.pdb, "pdb");

      if (result.source === "alphafold") {
        // AlphaFold pLDDT lives in the B-factor column; high = confident = blue.
        viewer.setStyle(
          {},
          { cartoon: { colorscheme: { prop: "b", gradient: "roygb", min: 50, max: 90 } } },
        );
      } else {
        viewer.setStyle({}, { cartoon: { color: "spectrum" } });
      }
      viewer.zoomTo();
      viewer.render();
      // gentle idle spin
      viewer.spin("y", 0.4);
    })();

    return () => {
      disposed = true;
      try {
        viewerRef.current?.clear?.();
      } catch {}
      el.innerHTML = "";
    };
  }, [status, result, isDark]);

  return (
    <Panel
      title="Structure"
      aside={result?.source ? <SourceBadge result={result} /> : <Badge tone="neutral">AlphaFold · Tamarind</Badge>}
    >
      {status === "idle" && (
        <Empty title="No gene selected" icon={<Cube />}>
          Pick a flipper gene from a selected strain to fold its protein with AlphaFold
          (Tamarind Bio) and inspect the 3D structure.
        </Empty>
      )}
      {status === "loading" && <div className="skeleton h-64 rounded-xl" />}
      {status === "error" && (
        <Empty title="Structure service offline" icon={<Cube />}>
          Start the API and retry.
        </Empty>
      )}
      {status === "empty" && (
        <Empty title={result?.source === "alphafold_pending" ? "Folding in progress" : "No structure yet"} icon={<Cube />}>
          {result?.note ?? "No cached or experimental structure for this protein."}
          {result?.source === "alphafold_pending" ? (
            <span className="mt-1 block text-faint">
              AlphaFold job submitted to Tamarind — reselect this gene shortly.
            </span>
          ) : (
            <button
              onClick={fold}
              className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-accent/30 bg-accent/10 px-3 py-1.5 text-xs font-medium text-accentStrong transition hover:bg-accent/20"
            >
              Fold with AlphaFold →
            </button>
          )}
        </Empty>
      )}
      {status === "ready" && result && (
        <div className="animate-fade">
          <div className="relative h-64 overflow-hidden rounded-xl border border-line/10 bg-surface2/40">
            <div ref={mountRef} className="absolute inset-0" />
            {result.source === "alphafold" && <PlddtLegend />}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
            <span className="font-mono text-text">{label ?? result.name ?? result.locus_tag}</span>
            {result.product && <span className="truncate">{result.product}</span>}
          </div>
          <dl className="mt-2 grid grid-cols-3 gap-2 text-xs">
            {result.plddt != null && <Metric label="mean pLDDT" value={result.plddt.toFixed(1)} />}
            {result.ptm != null && <Metric label="pTM" value={result.ptm.toFixed(2)} />}
            {result.residue_count != null && <Metric label="residues" value={String(result.residue_count)} />}
            {result.pdb_id && <Metric label="PDB" value={result.pdb_id} />}
          </dl>
        </div>
      )}
    </Panel>
  );
}

function SourceBadge({ result }: { result: StructureResult }) {
  if (result.source === "alphafold")
    return <Badge tone="accent">AlphaFold · Tamarind</Badge>;
  if (result.source === "rcsb") return <Badge tone="neutral">RCSB · experimental</Badge>;
  return <Badge tone="amber">pending</Badge>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line/8 bg-surface2/40 px-2 py-1.5">
      <div className="font-mono text-sm text-text">{value}</div>
      <div className="text-[0.62rem] text-faint">{label}</div>
    </div>
  );
}

function PlddtLegend() {
  return (
    <div className="pointer-events-none absolute bottom-2 left-2 rounded-md border border-line/10 bg-surface/80 px-2 py-1 backdrop-blur">
      <div className="mb-1 text-[0.58rem] uppercase tracking-wide text-faint">pLDDT</div>
      <div className="flex items-center gap-1">
        <span className="text-[0.58rem] text-faint">50</span>
        <span
          className="inline-block h-1.5 w-16 rounded-full"
          style={{ background: "linear-gradient(90deg, #d9534f, #f0ad4e, #5cb85c, #2b8cbe, #2b3a9e)" }}
        />
        <span className="text-[0.58rem] text-faint">90</span>
      </div>
    </div>
  );
}

function Cube() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2 20 7v10l-8 5-8-5V7z" />
      <path d="M12 22V12M12 12l8-5M12 12L4 7" />
    </svg>
  );
}
