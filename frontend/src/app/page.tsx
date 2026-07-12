"use client";
import { useState } from "react";
import { useLineage } from "@/lib/useLineage";
import { Header } from "@/components/Header";
import { Hero } from "@/components/Hero";
import { Panel } from "@/components/ui";
import { LineageTree } from "@/components/LineageTree";
import { StructureViewer } from "@/components/StructureViewer";
import { StrainDetail, type GeneSelection } from "@/components/StrainDetail";
import { Insights } from "@/components/Insights";
import { TargetGraph } from "@/components/TargetGraph";
import { EvidencePanel } from "@/components/EvidencePanel";
import { CyclingView } from "@/components/CyclingView";

const ORGANISM = "Burkholderia multivorans";
// Default the structure view to the MarR regulator — a real flipper gene with a
// real AlphaFold (Tamarind) model — so the 3D beat is live on first load.
const DEFAULT_GENE: GeneSelection = {
  locus: "A8H40_RS07590",
  label: "MarR (A8H40_RS07590)",
};

export default function Page() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedGene, setSelectedGene] = useState<GeneSelection>(DEFAULT_GENE);
  const { graph, status, error, byId, overview } = useLineage(ORGANISM);

  const selectedNode = selectedId ? (byId.get(selectedId) ?? null) : null;
  const maxFlip = overview?.maxFlip ?? 1;

  return (
    <div className="min-h-screen">
      <Header status={status} />

      <main className="mx-auto max-w-7xl space-y-6 px-6 pb-20 pt-9">
        <Hero overview={overview} status={status} />

        <section className="grid gap-5 lg:grid-cols-[1.55fr_1fr]">
          <Panel
            title="Lineage"
            aside={
              <span className="font-mono text-[0.68rem] text-faint">
                real experimental evolution
              </span>
            }
          >
            <LineageTree
              graph={graph}
              status={status}
              error={error}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          </Panel>

          <StructureViewer locus={selectedGene?.locus ?? null} label={selectedGene?.label} />
        </section>

        <section className="grid gap-5 lg:grid-cols-[1fr_1fr]">
          <StrainDetail
            node={selectedNode}
            maxFlip={maxFlip}
            onClear={() => setSelectedId(null)}
            selectedGene={selectedGene}
            onSelectGene={setSelectedGene}
          />
          <Insights overview={overview} />
        </section>

        <EvidencePanel gene={selectedGene} />

        <section className="stagger grid gap-5 md:grid-cols-2">
          <TargetGraph strainId={selectedId} />
          <CyclingView organism={ORGANISM} />
        </section>

        <Footer />
      </main>
    </div>
  );
}

function Footer() {
  const sources = ["BurkData", "PubMLST", "NCBI", "Tamarind Bio", "RCSB", "CARD"];
  return (
    <footer className="border-t border-line/8 pt-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[0.7rem] text-faint">
          <span className="text-muted">Sources:</span>
          {sources.map((s) => (
            <span key={s} className="rounded-md bg-line/6 px-1.5 py-0.5 font-mono">
              {s}
            </span>
          ))}
        </div>
        <div className="text-[0.7rem] text-faint">
          Deterministic core · AlphaFold on top · provenance on every edge ·{" "}
          <span className="text-muted">MIT</span>
        </div>
      </div>
    </footer>
  );
}
