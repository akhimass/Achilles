"use client";
// Landing page — the cinematic front door that leads into the working console (/explore).
// Reuses the shared design system (aurora is global in layout; glass / hover-lift /
// reveal / text-gradient-green from globals.css) so it's one continuous world.
import Link from "next/link";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function Landing() {
  return (
    <div className="min-h-screen">
      <Nav />
      <main>
        <Hero />
        <Idea />
        <Capabilities />
        <ProveIt />
        <Pipeline />
        <FinalCta />
      </main>
      <Footer />
    </div>
  );
}

/* ─── Nav ─────────────────────────────────────────────────────────────────── */

function Nav() {
  return (
    <header className="animate-fade sticky top-0 z-40 border-b border-line/8 bg-bg/55 backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3.5">
        <Link href="/" className="flex items-center gap-2.5 transition-opacity hover:opacity-80">
          <Mark />
          <span className="text-[1.3rem] font-semibold tracking-tightest text-gradient-green">
            Achilles
          </span>
        </Link>
        <nav className="hidden items-center gap-6 text-[0.82rem] text-muted md:flex">
          <a href="#idea" className="transition hover:text-text">The idea</a>
          <a href="#capabilities" className="transition hover:text-text">What it does</a>
          <a href="#proof" className="transition hover:text-text">Proof</a>
          <a
            href="https://github.com/akhimass/Achilles"
            target="_blank"
            rel="noopener noreferrer"
            className="transition hover:text-text"
          >
            GitHub
          </a>
        </nav>
        <div className="flex items-center gap-2.5">
          <ThemeToggle />
          <Link
            href="/explore"
            className="group inline-flex items-center gap-1.5 rounded-full bg-accent px-4 py-2 text-[0.82rem] font-semibold text-[rgb(var(--bg))] shadow-glow-sm transition hover:shadow-glow"
          >
            Open console
            <Arrow />
          </Link>
        </div>
      </div>
    </header>
  );
}

/* ─── Hero ────────────────────────────────────────────────────────────────── */

function Hero() {
  return (
    <section className="relative mx-auto max-w-6xl px-6 pb-16 pt-20 sm:pt-28">
      <div className="grid items-center gap-12 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="stagger">
          <div className="mb-5 flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-accent/25 bg-accent/10 px-2.5 py-1 text-[0.7rem] font-medium text-accentStrong">
              <Dot /> antimicrobial resistance
            </span>
            <span className="rounded-full border border-line/12 px-2.5 py-1 font-mono text-[0.68rem] text-muted">
              provenance on every edge
            </span>
          </div>

          <h1 className="text-[2.7rem] font-semibold leading-[1.02] tracking-tightest text-text sm:text-[4rem]">
            Evidence graph for
            <br />
            <span className="text-gradient-green">antimicrobial resistance</span>.
          </h1>

          <p className="mt-6 max-w-xl text-[1.02rem] leading-relaxed text-muted">
            Achilles links strain → variant → mechanism → target → literature with a
            citation on every edge. Lineage, flippers, and collateral-sensitivity math are
            computed deterministically; the model only extracts and narrates grounded claims.
            Built for AMR researchers tracking resistance across bacterial strains.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link
              href="/explore"
              className="group inline-flex items-center gap-2 rounded-full bg-accent px-6 py-3 text-[0.95rem] font-semibold text-[rgb(var(--bg))] shadow-glow-sm transition hover:shadow-glow"
            >
              Open console
              <Arrow />
            </Link>
            <a
              href="#idea"
              className="inline-flex items-center gap-2 rounded-full border border-line/15 px-6 py-3 text-[0.95rem] font-medium text-text transition hover:border-line/30 hover:bg-surface2/50"
            >
              See how it works
            </a>
          </div>

          <div className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-2 text-[0.78rem] text-faint">
            <Stat n="100%" label="edges cited" />
            <span className="text-line/20">·</span>
            <Stat n="0" label="ungrounded claims" />
            <span className="text-line/20">·</span>
            <Stat n="public" label="data only" />
          </div>
        </div>

        <div className="animate-rise">
          <HeroGraphic />
        </div>
      </div>
    </section>
  );
}

function Stat({ n, label }: { n: string; label: string }) {
  return (
    <span className="inline-flex items-baseline gap-1.5">
      <span className="font-mono text-sm font-semibold text-accentStrong">{n}</span>
      <span>{label}</span>
    </span>
  );
}

// Animated "evidence spine": strain → flipper → structure → target → cycle, with a
// flowing connector and a pulsing grounded node. Pure SVG/CSS, theme-aware.
function HeroGraphic() {
  const stages = [
    { x: 60, label: "strain" },
    { x: 175, label: "flipper" },
    { x: 290, label: "structure" },
    { x: 405, label: "target" },
    { x: 520, label: "cycle" },
  ];
  return (
    <div className="glass hover-lift rounded-2xl border border-line/10 p-5 shadow-card">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-faint">
          the evidence graph · AMR example
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-accent/10 px-2 py-0.5 text-[0.62rem] font-medium text-accentStrong">
          <Dot /> live
        </span>
      </div>
      <svg viewBox="0 0 580 260" className="w-full" role="img" aria-label="Achilles evidence graph">
        <defs>
          <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="rgb(var(--accent))" stopOpacity="0.15" />
            <stop offset="50%" stopColor="rgb(var(--accent))" stopOpacity="0.9" />
            <stop offset="100%" stopColor="rgb(var(--accent-2))" stopOpacity="0.4" />
          </linearGradient>
        </defs>

        {/* connectors */}
        <path
          d="M60 90 H520"
          fill="none"
          stroke="url(#edge)"
          strokeWidth="2"
          strokeDasharray="2 6"
          strokeLinecap="round"
          style={{ animation: "dash 1s linear infinite" }}
        />
        {/* branch to a second lineage row */}
        <path
          d="M175 90 C 230 90, 240 170, 290 170 H 520"
          fill="none"
          stroke="rgb(var(--line) / 0.18)"
          strokeWidth="1.5"
          strokeDasharray="2 6"
          strokeLinecap="round"
          style={{ animation: "dash 1.4s linear infinite" }}
        />

        {/* main spine nodes */}
        {stages.map((s, i) => (
          <g key={s.label}>
            <circle
              cx={s.x}
              cy={90}
              r={i === 3 ? 10 : 6.5}
              fill={i === 3 ? "rgb(var(--accent))" : "rgb(var(--surface))"}
              stroke="rgb(var(--accent))"
              strokeWidth="2"
            />
            {i === 3 && (
              <circle cx={s.x} cy={90} r={10} fill="none" stroke="rgb(var(--accent))" strokeWidth="2" className="pulse-dot" />
            )}
            <text x={s.x} y={118} textAnchor="middle" fontSize="10" fontFamily="var(--font-geist-mono)" fill="rgb(var(--muted))">
              {s.label}
            </text>
          </g>
        ))}

        {/* secondary lineage leaf nodes */}
        {[290, 405, 520].map((x, i) => (
          <circle key={x} cx={x} cy={170} r={5} fill="rgb(var(--surface))" stroke={i === 2 ? "rgb(var(--accent))" : "rgb(var(--tree-neutral))"} strokeWidth="1.8" />
        ))}

        {/* floating provenance chips */}
        <g>
          <rect x={355} y={205} width={110} height={26} rx={6} fill="rgb(var(--accent) / 0.1)" stroke="rgb(var(--accent) / 0.3)" />
          <text x={410} y={222} textAnchor="middle" fontSize="9.5" fontFamily="var(--font-geist-mono)" fill="rgb(var(--accent-strong))">
            CARD ARO:3003378
          </text>
        </g>
        <g>
          <rect x={60} y={205} width={92} height={26} rx={6} fill="rgb(var(--line) / 0.06)" stroke="rgb(var(--line) / 0.15)" />
          <text x={106} y={222} textAnchor="middle" fontSize="9.5" fontFamily="var(--font-geist-mono)" fill="rgb(var(--muted))">
            PMID 42106608
          </text>
        </g>

        {/* headline edge label */}
        <text x={290} y={40} textAnchor="middle" fontSize="12" fontFamily="var(--font-geist-mono)" fill="rgb(var(--faint))">
          MarR —confers→ ciprofloxacin
        </text>
      </svg>
      <div className="mt-2 grid grid-cols-3 gap-2 text-center">
        {[
          ["47", "isolates"],
          ["61", "grounded edges"],
          ["88", "pLDDT · AlphaFold"],
        ].map(([n, l]) => (
          <div key={l} className="rounded-lg border border-line/8 bg-surface2/40 py-2">
            <div className="font-mono text-base tabular-nums text-text">{n}</div>
            <div className="text-[0.6rem] text-faint">{l}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── The idea ────────────────────────────────────────────────────────────── */

function Idea() {
  return (
    <section id="idea" className="mx-auto max-w-6xl px-6 py-20">
      <SectionHeading eyebrow="the idea" title="From association to collateral sensitivity." />
      <div className="reveal mt-10 grid gap-5 md:grid-cols-2">
        <div className="rounded-2xl border border-line/10 bg-surface2/30 p-6">
          <div className="text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-faint">
            Typical target ID
          </div>
          <p className="mt-3 text-lg leading-snug text-muted">
            &ldquo;This gene is <em>associated</em> with resistance.&rdquo;
          </p>
          <p className="mt-3 text-sm leading-relaxed text-faint">
            A correlation from a screen — often without mechanism, directionality, or a
            clear next experiment.
          </p>
        </div>
        <div className="glass rounded-2xl border border-accent/25 p-6 shadow-glow-sm">
          <div className="text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-accentStrong">
            Achilles
          </div>
          <p className="mt-3 text-lg leading-snug text-text">
            &ldquo;Resistance to <span className="text-gradient-green">A</span> opens a{" "}
            <span className="text-gradient-green">reversible target</span> that
            re-sensitizes to <span className="text-gradient-green">B</span>.&rdquo;
          </p>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            Collateral-sensitivity structure computed from the graph, structures folded in
            3D, and every claim grounded to literature (PMID + CARD/UniProt). No edge
            without provenance.
          </p>
        </div>
      </div>
    </section>
  );
}

/* ─── Capabilities ────────────────────────────────────────────────────────── */

function Capabilities() {
  const items = [
    { icon: <IconTree />, title: "Lineage & flippers", body: "Reconstruct the evolutionary tree and detect reversible (flipper) loci along it — deterministically." },
    { icon: <IconCube />, title: "AlphaFold structures", body: "Fold any flipper gene's protein via Tamarind Bio, colored by per-residue pLDDT confidence." },
    { icon: <IconDoc />, title: "Grounded evidence", body: "Every edge cites a PMID and, where corroborated, a reference-DB accession (CARD/UniProt/ChEMBL)." },
    { icon: <IconTarget />, title: "Ranked targets", body: "Evidence-supported genes promoted to targets with a deterministic score + ChEMBL tractability." },
    { icon: <IconCycle />, title: "Cycling hypotheses", body: "A reciprocal-CS antibiotic cycle with a concrete next-experiment call — a hypothesis, never advice." },
    { icon: <IconUpload />, title: "Bring your own strains", body: "Drop a genotype CSV; the same core reconstructs your lineage and flippers. Nothing stored." },
  ];
  return (
    <section id="capabilities" className="mx-auto max-w-6xl px-6 py-20">
      <SectionHeading eyebrow="capabilities" title="Six steps on one continuous graph." />
      <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((it) => (
          <div
            key={it.title}
            className="reveal hover-lift group rounded-2xl border border-line/10 bg-surface/70 p-5 backdrop-blur-sm transition hover:border-accent/25 hover:shadow-glow-sm"
          >
            <div className="grid h-10 w-10 place-items-center rounded-xl border border-accent/20 bg-accent/10 text-accentStrong">
              {it.icon}
            </div>
            <h3 className="mt-4 text-[0.98rem] font-semibold text-text">{it.title}</h3>
            <p className="mt-1.5 text-[0.85rem] leading-relaxed text-muted">{it.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ─── Prove it ────────────────────────────────────────────────────────────── */

function ProveIt() {
  const stats = [
    { n: "100%", label: "edges cited", sub: "provenance required" },
    { n: "12/12", label: "known biology recovered", sub: "positive controls" },
    { n: "17/17", label: "adversarial claims refused", sub: "the traps a hallucinator falls for" },
    { n: "0", label: "fabricated edges", sub: "on the demo graph" },
  ];
  return (
    <section id="proof" className="mx-auto max-w-6xl px-6 py-20">
      <div className="glass reveal rounded-3xl border border-line/10 p-8 shadow-card sm:p-12">
        <SectionHeading
          eyebrow="validation"
          title="Held to public ground-truth controls."
          center
        />
        <p className="mx-auto mt-3 max-w-2xl text-center text-sm leading-relaxed text-muted">
          On the demo dataset, Achilles is scored against independent public controls:
          recover known relationships from grounded evidence, and refuse planted false
          claims. Computed live; every recovery carries a citation.
        </p>
        <div className="mt-10 grid grid-cols-2 gap-5 lg:grid-cols-4">
          {stats.map((s) => (
            <div key={s.label} className="text-center">
              <div className="text-gradient-green font-mono text-4xl font-semibold tabular-nums sm:text-5xl">
                {s.n}
              </div>
              <div className="mt-2 text-sm font-medium text-text">{s.label}</div>
              <div className="text-[0.72rem] text-faint">{s.sub}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── Pipeline strip ──────────────────────────────────────────────────────── */

function Pipeline() {
  const steps = ["Public data", "Deterministic core", "Grounded graph", "AlphaFold", "Cited answer"];
  return (
    <section className="mx-auto max-w-6xl px-6 py-14">
      <div className="reveal flex flex-wrap items-center justify-center gap-2 text-center">
        {steps.map((s, i) => (
          <span key={s} className="flex items-center gap-2">
            <span className="rounded-full border border-line/12 bg-surface2/40 px-3.5 py-1.5 text-[0.8rem] text-muted">
              {s}
            </span>
            {i < steps.length - 1 && <span className="text-accent">→</span>}
          </span>
        ))}
      </div>
      <p className="mt-4 text-center text-[0.8rem] text-faint">
        The core computes; the model only reads, retrieves, and cites — it never invents a number.
      </p>
    </section>
  );
}

/* ─── Final CTA ───────────────────────────────────────────────────────────── */

function FinalCta() {
  return (
    <section className="mx-auto max-w-6xl px-6 py-24">
      <div className="glass reveal relative overflow-hidden rounded-3xl border border-accent/20 p-12 text-center shadow-card">
        <div className="bg-grid pointer-events-none absolute inset-0 opacity-40" aria-hidden />
        <div className="relative">
          <h2 className="text-3xl font-semibold tracking-tightest text-text sm:text-[2.6rem]">
            Explore the live <span className="text-gradient-green">evidence graph</span>.
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-[0.95rem] leading-relaxed text-muted">
            Open the console blank and upload strains, or load the Burkholderia multivorans
            demo — lineage, structures, grounded targets, and a cited cycling hypothesis,
            reproducible from public data.
          </p>
          <Link
            href="/explore"
            className="group mt-8 inline-flex items-center gap-2 rounded-full bg-accent px-7 py-3.5 text-[1rem] font-semibold text-[rgb(var(--bg))] shadow-glow-sm transition hover:shadow-glow"
          >
            Open console
            <Arrow />
          </Link>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="mx-auto max-w-6xl border-t border-line/8 px-6 py-8">
      <div className="flex flex-col items-center justify-between gap-3 text-[0.72rem] text-faint sm:flex-row">
        <span>
          <span className="text-gradient-green font-semibold">Achilles</span> · deterministic
          core · provenance on every edge
        </span>
        <span>
          Public data · AMR ·{" "}
          <a href="https://github.com/akhimass/Achilles" target="_blank" rel="noopener noreferrer" className="hover:text-text">
            MIT
          </a>
        </span>
      </div>
    </footer>
  );
}

/* ─── Shared bits ─────────────────────────────────────────────────────────── */

function SectionHeading({ eyebrow, title, center }: { eyebrow: string; title: string; center?: boolean }) {
  return (
    <div className={center ? "text-center" : ""}>
      <div className="text-[0.7rem] font-semibold uppercase tracking-[0.16em] text-accentStrong">
        {eyebrow}
      </div>
      <h2 className={`mt-2 text-2xl font-semibold tracking-tightest text-text sm:text-[2rem] ${center ? "mx-auto max-w-2xl" : "max-w-2xl"}`}>
        {title}
      </h2>
    </div>
  );
}

function Mark() {
  return (
    <span className="grid h-9 w-9 place-items-center rounded-xl border border-accent/20 bg-surface/70 shadow-glow-sm">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path d="M5 12 H11 M11 12 L17 6 M11 12 L17 18" stroke="rgb(var(--muted))" strokeWidth="1.6" strokeLinecap="round" />
        <circle cx="4.5" cy="12" r="1.7" fill="rgb(var(--muted))" />
        <circle cx="17.5" cy="6" r="1.7" fill="rgb(var(--muted))" />
        <circle cx="17.6" cy="18" r="2.4" fill="rgb(var(--accent))" />
      </svg>
    </span>
  );
}

function Arrow() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="transition-transform group-hover:translate-x-0.5">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}

function Dot() {
  return (
    <span className="relative flex h-1.5 w-1.5">
      <span className="pulse-dot absolute inline-flex h-1.5 w-1.5 rounded-full bg-accent" />
      <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-accent" />
    </span>
  );
}

const ic = "rgb(var(--accent-strong))";
function IconTree() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={ic} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h6m0 0 6-5m-6 5 6 5" /><circle cx="4" cy="12" r="1.6" fill={ic} /><circle cx="18" cy="7" r="1.6" fill={ic} /><circle cx="18" cy="17" r="1.6" fill={ic} /></svg>; }
function IconCube() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={ic} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2 20 7v10l-8 5-8-5V7z" /><path d="M12 22V12M12 12l8-5M12 12 4 7" /></svg>; }
function IconDoc() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={ic} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M6 2h8l4 4v16H6z" /><path d="M14 2v4h4M9 13h6M9 17h6" /></svg>; }
function IconTarget() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={ic} strokeWidth="1.7"><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="4" /><circle cx="12" cy="12" r="1" fill={ic} /></svg>; }
function IconCycle() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={ic} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M17 2.1 21 6l-4 3.9" /><path d="M3 12a9 9 0 0 1 9-9h9" /><path d="M7 21.9 3 18l4-3.9" /><path d="M21 12a9 9 0 0 1-9 9H3" /></svg>; }
function IconUpload() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={ic} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M12 15V3m0 0 4 4m-4-4L8 7" /><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" /></svg>; }
