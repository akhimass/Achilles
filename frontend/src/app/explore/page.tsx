"use client";
import { useEffect, useMemo, useState } from "react";
import { useLineage } from "@/lib/useLineage";
import { Header } from "@/components/Header";
import { Hero } from "@/components/Hero";
import { GenericOverview } from "@/components/GenericOverview";
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
import { HowItWorks } from "@/components/HowItWorks";
import { AskPanel } from "@/components/AskPanel";
import { ConsoleNav, type NavSection } from "@/components/ConsoleNav";

const DEMO_ORGANISM = "Burkholderia multivorans";
const DEFAULT_GENE: GeneSelection = {
  locus: "A8H40_RS07590",
  label: "MarR (A8H40_RS07590)",
};

const SECTIONS: (NavSection & { demoOnly?: boolean })[] = [
  { id: "overview", label: "Overview", group: "Start" },
  { id: "ask", label: "Ask", group: "Start" },
  { id: "yourdata", label: "Upload", group: "Start" },
  { id: "lineage", label: "Lineage", group: "Graph", demoOnly: true },
  { id: "evidence", label: "Evidence", group: "Graph", demoOnly: true },
  { id: "targets", label: "Targets", group: "Analysis", demoOnly: true },
  { id: "treatment", label: "Cycling", group: "Analysis", demoOnly: true },
  { id: "validate", label: "Validation", group: "Analysis", demoOnly: true },
  { id: "how", label: "Methods", group: "About" },
];

const CHAPTERS: Record<string, string> = {
  overview: "Overview",
  ask: "Ask the evidence graph",
  yourdata: "Upload strains",
  lineage: "Strains & lineage",
  evidence: "Search & grounded claims",
  targets: "Target identification",
  treatment: "Treatment optimization",
  validate: "Validation & retrodiction",
  how: "Methods & reproducibility",
};

export default function Page() {
  const [demo, setDemo] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedGene, setSelectedGene] = useState<GeneSelection>(DEFAULT_GENE);
  const [active, setActive] = useState("overview");

  const activeOrganism = demo ? DEMO_ORGANISM : null;
  const { graph, status, error, byId, overview } = useLineage(activeOrganism);

  const selectedNode = selectedId ? (byId.get(selectedId) ?? null) : null;
  const maxFlip = overview?.maxFlip ?? 1;

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("demo") === "1") setDemo(true);
  }, []);

  const toggleDemo = (next: boolean) => {
    setDemo(next);
    const url = new URL(window.location.href);
    if (next) url.searchParams.set("demo", "1");
    else url.searchParams.delete("demo");
    window.history.replaceState({}, "", url);
  };

  const selectStrainByLabel = (label: string) => {
    for (const [id, node] of byId) {
      if (node.label === label) {
        setSelectedId(id);
        return;
      }
    }
  };

  const visible = useMemo(
    () => SECTIONS.filter((s) => demo || !s.demoOnly),
    [demo],
  );

  useEffect(() => {
    const ids = visible.map((s) => s.id);
    const obs = new IntersectionObserver(
      (entries) => {
        const onscreen = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (onscreen[0]) setActive((onscreen[0].target as HTMLElement).id);
      },
      { rootMargin: "-96px 0px -62% 0px", threshold: 0 },
    );
    ids.forEach((id) => {
      const el = document.getElementById(id);
      if (el) obs.observe(el);
    });
    return () => obs.disconnect();
  }, [visible]);

  const jump = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
    setActive(id);
  };

  return (
    <div className="min-h-screen">
      <Header status={status} demo={demo} onToggleDemo={toggleDemo} />

      <div className="mx-auto flex max-w-[88rem] gap-8 px-6 pb-20 pt-8">
        <ConsoleNav sections={visible} active={active} onJump={jump} />

        <main className="min-w-0 flex-1 space-y-12">
          <Chapter id="overview" visible={visible}>
            {demo ? (
              <Hero overview={overview} status={status} />
            ) : (
              <GenericOverview onLoadDemo={() => toggleDemo(true)} />
            )}
          </Chapter>

          <Chapter id="ask" visible={visible}>
            <AskPanel dataset={activeOrganism} onLoadDemo={() => toggleDemo(true)} />
          </Chapter>

          <Chapter id="yourdata" visible={visible}>
            <UploadPanel />
          </Chapter>

          <Chapter id="lineage" visible={visible}>
            <section className="grid gap-5 lg:grid-cols-[1.55fr_1fr]">
              <Panel
                title="Lineage"
                aside={
                  <span className="font-mono text-[0.68rem] text-faint">
                    experimental evolution
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
          </Chapter>

          <Chapter id="evidence" visible={visible}>
            <SearchPanel />
            <EvidencePanel gene={selectedGene} />
          </Chapter>

          <Chapter id="targets" visible={visible}>
            <TargetGraph
              strainId={selectedId}
              selectedLocus={selectedGene?.locus ?? null}
              onViewStructure={setSelectedGene}
            />
            <DockingPanel />
          </Chapter>

          <Chapter id="treatment" visible={visible}>
            <TrajectoryPanel strainId={selectedId} onSelectStrainLabel={selectStrainByLabel} />
            <CyclingView
              organism={DEMO_ORGANISM}
              strainId={selectedId}
              strainLabel={selectedNode?.label ?? null}
            />
          </Chapter>

          <Chapter id="validate" visible={visible}>
            <ValidationPanel />
            <RetrodictionPanel />
          </Chapter>

          <Chapter id="how" visible={visible}>
            <HowItWorks />
          </Chapter>

          <Footer />
        </main>
      </div>
    </div>
  );
}

function Chapter({
  id,
  visible,
  children,
}: {
  id: string;
  visible: (NavSection & { demoOnly?: boolean })[];
  children: React.ReactNode;
}) {
  if (!visible.find((s) => s.id === id)) return null;
  return (
    <section id={id} className="scroll-mt-24 space-y-5">
      <h2 className="border-b border-line/10 pb-2 font-serif text-lg font-medium tracking-tight text-text">
        {CHAPTERS[id]}
      </h2>
      {children}
    </section>
  );
}

function Footer() {
  const sources = ["PubMLST", "Europe PMC", "CARD", "UniProt", "ChEMBL", "NCBI", "AlphaFold", "RCSB"];
  return (
    <footer className="border-t border-line/10 pt-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[0.7rem] text-faint">
          <span className="text-muted">Demo sources</span>
          {sources.map((s) => (
            <span key={s} className="font-mono text-faint">
              {s}
            </span>
          ))}
        </div>
        <div className="text-[0.7rem] text-faint">
          Deterministic core · provenance required · MIT
        </div>
      </div>
    </footer>
  );
}
