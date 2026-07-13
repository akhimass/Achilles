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
import { TrustBar } from "@/components/TrustBar";
import { HowItWorks } from "@/components/HowItWorks";
import { AskPanel } from "@/components/AskPanel";
import { BridgePanel } from "@/components/BridgePanel";
import { ConsoleNav, PERSONAS, type Persona, type NavSection } from "@/components/ConsoleNav";

// The one bundled example dataset. The console itself is domain-agnostic; this is loaded
// only when the user turns on "Demo data".
const DEMO_ORGANISM = "Burkholderia multivorans";
const DEFAULT_GENE: GeneSelection = {
  locus: "A8H40_RS07590",
  label: "MarR (A8H40_RS07590)",
};

// Chapters tagged with the audiences they serve and whether they need a loaded dataset
// (`demoOnly`). Blank console shows only the always-on chapters; loading the demo reveals
// the data-backed ones.
const SECTIONS: (NavSection & { demoOnly?: boolean })[] = [
  { id: "overview", label: "Overview", group: "Start", personas: ["researcher", "physician", "computational"] },
  { id: "ask", label: "Ask", group: "Start", personas: ["researcher", "physician", "computational"] },
  { id: "yourdata", label: "Your data", group: "Start", personas: ["researcher", "physician", "computational"] },
  { id: "prove", label: "Validation", group: "Trust layer", personas: ["computational", "physician"], demoOnly: true },
  { id: "lineage", label: "Strains & lineage", group: "Evidence", personas: ["researcher"], demoOnly: true },
  { id: "evidence", label: "Search & claims", group: "Evidence", personas: ["researcher", "computational"], demoOnly: true },
  { id: "targets", label: "Target identification", group: "Discovery", personas: ["researcher", "computational"], demoOnly: true },
  { id: "treatment", label: "Treatment optimization", group: "Discovery", personas: ["physician", "researcher"], demoOnly: true },
  { id: "how", label: "How it works", group: "About", personas: ["researcher", "physician", "computational"] },
];

const CHAPTERS: Record<string, { kicker: string; title: string }> = {
  overview: { kicker: "Start", title: "Overview" },
  ask: { kicker: "Ask", title: "Ask the evidence graph" },
  yourdata: { kicker: "Start", title: "Your data" },
  prove: { kicker: "Trust", title: "Validation & foresight" },
  lineage: { kicker: "Evidence", title: "Strains & lineage" },
  evidence: { kicker: "Evidence graph", title: "Search & grounded claims" },
  targets: { kicker: "Analysis", title: "Target identification" },
  treatment: { kicker: "Analysis", title: "Treatment optimization" },
  how: { kicker: "Methods", title: "How this works" },
};

export default function Page() {
  const [demo, setDemo] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedGene, setSelectedGene] = useState<GeneSelection>(DEFAULT_GENE);
  const [persona, setPersona] = useState<Persona>("all");
  const [active, setActive] = useState<string>("overview");

  const activeOrganism = demo ? DEMO_ORGANISM : null;
  const { graph, status, error, byId, overview } = useLineage(activeOrganism);

  const selectedNode = selectedId ? (byId.get(selectedId) ?? null) : null;
  const maxFlip = overview?.maxFlip ?? 1;

  // Read/write the demo flag from the URL so a populated console is shareable.
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
    () =>
      SECTIONS.filter(
        (s) =>
          (persona === "all" || s.personas.includes(persona)) && (demo || !s.demoOnly),
      ),
    [persona, demo],
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

  const personaBlurb = persona !== "all" ? PERSONAS.find((p) => p.id === persona)?.blurb : null;

  return (
    <div className="min-h-screen">
      <Header status={status} demo={demo} onToggleDemo={toggleDemo} />

      <div className="mx-auto flex max-w-[88rem] gap-8 px-6 pb-20 pt-9">
        <ConsoleNav
          sections={visible}
          active={active}
          persona={persona}
          onPersona={setPersona}
          onJump={jump}
        />

        <main className="min-w-0 flex-1 space-y-10">
          {personaBlurb && (
            <div className="animate-fade rounded-xl border border-accent/25 bg-accent/[0.06] px-4 py-2.5 text-[0.82rem] text-text">
              <span className="font-semibold text-accentStrong">
                {PERSONAS.find((p) => p.id === persona)?.label}:
              </span>{" "}
              {personaBlurb}
            </div>
          )}

          <Chapter id="overview" visible={visible}>
            {demo ? (
              <>
                <Hero overview={overview} status={status} />
                <TrustBar />
              </>
            ) : (
              <GenericOverview onLoadDemo={() => toggleDemo(true)} />
            )}
          </Chapter>

          <Chapter id="ask" visible={visible}>
            <AskPanel
              persona={persona}
              dataset={activeOrganism}
              onLoadDemo={() => toggleDemo(true)}
            />
          </Chapter>

          <Chapter id="yourdata" visible={visible}>
            <UploadPanel />
          </Chapter>

          <Chapter id="prove" visible={visible}>
            <ValidationPanel />
            <RetrodictionPanel />
          </Chapter>

          <Chapter id="lineage" visible={visible}>
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
            <div className="flex justify-end">
              <button
                onClick={() => jump("treatment")}
                className="rounded-full border border-accent/25 bg-accent/10 px-3.5 py-1.5 text-[0.75rem] font-medium text-accentStrong transition hover:bg-accent/20"
              >
                Clinical translation for {selectedGene?.label ?? "the target"} →
              </button>
            </div>
            <DockingPanel />
          </Chapter>

          <Chapter id="treatment" visible={visible}>
            <Panel
              title="Research → clinic bridge"
              aside={
                <span className="font-mono text-[0.68rem] text-faint">
                  {selectedGene?.label ?? "select a target"}
                </span>
              }
            >
              <BridgePanel gene={selectedGene?.locus ?? "A8H40_RS07590"} />
            </Panel>
            <TrajectoryPanel strainId={selectedId} onSelectStrainLabel={selectStrainByLabel} />
            <CyclingView
              organism={DEMO_ORGANISM}
              strainId={selectedId}
              strainLabel={selectedNode?.label ?? null}
            />
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
  const meta = visible.find((s) => s.id === id);
  if (!meta) return null; // filtered out for the current persona / blank console
  const c = CHAPTERS[id];
  return (
    <section id={id} className="scroll-mt-24 space-y-5">
      <div className="flex items-end justify-between gap-3 border-b border-line/8 pb-2.5">
        <div>
          <div className="text-[0.62rem] font-semibold uppercase tracking-[0.16em] text-accentStrong">
            {c.kicker}
          </div>
          <h2 className="mt-0.5 text-lg font-semibold tracking-tight text-text">{c.title}</h2>
        </div>
        <div className="hidden gap-1 sm:flex">
          {meta.personas.map((p) => (
            <span
              key={p}
              className="rounded-full border border-line/12 bg-surface2/40 px-2 py-0.5 text-[0.6rem] capitalize text-faint"
            >
              {p}
            </span>
          ))}
        </div>
      </div>
      {children}
    </section>
  );
}

function Footer() {
  const sources = ["PubMLST", "Europe PMC", "CARD", "UniProt", "ChEMBL", "NCBI", "Tamarind Bio", "RCSB"];
  return (
    <footer className="border-t border-line/8 pt-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[0.7rem] text-faint">
          <span className="text-muted">Example dataset sources:</span>
          {sources.map((s) => (
            <span key={s} className="rounded-md bg-line/6 px-1.5 py-0.5 font-mono">
              {s}
            </span>
          ))}
          <span className="rounded-md border border-line/12 px-1.5 py-0.5 font-mono text-faint">
            AMR demo: Burkholderia (one example)
          </span>
        </div>
        <div className="text-[0.7rem] text-faint">
          Deterministic core · provenance on every edge ·{" "}
          <a
            href="https://github.com/akhimass/Achilles/blob/main/PRIVACY.md"
            target="_blank"
            rel="noreferrer"
            className="text-muted underline decoration-line/30 underline-offset-2 transition-colors hover:text-accentStrong"
          >
            Your data stays yours →
          </a>{" "}
          · <span className="text-muted">MIT</span>
        </div>
      </div>
    </footer>
  );
}
