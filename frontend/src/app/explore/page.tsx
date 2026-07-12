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
import { DockingPanel } from "@/components/DockingPanel";
import { TrajectoryPanel } from "@/components/TrajectoryPanel";
import { SearchPanel } from "@/components/SearchPanel";
import { UploadPanel } from "@/components/UploadPanel";
import { ValidationPanel } from "@/components/ValidationPanel";
import { RetrodictionPanel } from "@/components/RetrodictionPanel";
import { TrustBar } from "@/components/TrustBar";
import { HowItWorks } from "@/components/HowItWorks";

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

  // Resolve a backing-strain label (external id) from the trajectory beat back to a
  // lineage node so a judge can click a real backing strain and select it.
  const selectStrainByLabel = (label: string) => {
    for (const [id, node] of byId) {
      if (node.label === label) {
        setSelectedId(id);
        return;
      }
    }
  };

  return (
    <div className="min-h-screen">
      <Header status={status} />

      <main className="mx-auto max-w-7xl space-y-6 px-6 pb-20 pt-9">
        <Hero overview={overview} status={status} />

        <TrustBar />

        <ValidationPanel />

        <RetrodictionPanel />

        <SearchPanel />

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

        <UploadPanel />

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

        <TrajectoryPanel strainId={selectedId} onSelectStrainLabel={selectStrainByLabel} />

        <section className="grid gap-5 md:grid-cols-2">
          <TargetGraph
            strainId={selectedId}
            selectedLocus={selectedGene?.locus ?? null}
            onViewStructure={setSelectedGene}
          />
          <CyclingView
            organism={ORGANISM}
            strainId={selectedId}
            strainLabel={selectedNode?.label ?? null}
          />
        </section>

        <DockingPanel />

        <HowItWorks />

        <Footer />
      </main>
    </div>
  );
}

function Footer() {
  // Public sources power the deployed app. BurkData (private experimental evolution)
  // is used only in the local demo and never reaches the public deployment.
  const sources = ["PubMLST", "Europe PMC", "CARD", "UniProt", "ChEMBL", "NCBI", "Tamarind Bio", "RCSB"];
  return (
    <footer className="border-t border-line/8 pt-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[0.7rem] text-faint">
          <span className="text-muted">Public sources:</span>
          {sources.map((s) => (
            <span key={s} className="rounded-md bg-line/6 px-1.5 py-0.5 font-mono">
              {s}
            </span>
          ))}
          <span className="rounded-md border border-line/12 px-1.5 py-0.5 font-mono text-faint">
            BurkData — local demo only
          </span>
        </div>
        <div className="text-[0.7rem] text-faint">
          Deterministic core · AlphaFold on top · provenance on every edge ·{" "}
          <span className="text-muted">MIT</span>
        </div>
      </div>
    </footer>
  );
}
