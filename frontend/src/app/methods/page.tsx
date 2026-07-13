import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Methods — Achilles",
  description:
    "How Achilles works: a deterministic core, an LLM bounded to extraction and cited narration, provenance on every edge, and a self-validation methodology (recall, adversarial refusal, time-split foresight) with stated limitations.",
};

export default function Methods() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-line/8 bg-bg/60 backdrop-blur-xl">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-3">
          <Link href="/" className="text-[1.2rem] font-semibold tracking-tightest text-gradient-green">
            Achilles
          </Link>
          <Link
            href="/explore"
            className="rounded-full bg-accent px-4 py-1.5 text-[0.8rem] font-semibold text-[rgb(var(--bg))] shadow-glow-sm transition hover:shadow-glow"
          >
            Open console
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-14">
        <p className="text-[0.7rem] font-semibold uppercase tracking-[0.16em] text-accentStrong">
          Methods
        </p>
        <h1 className="mt-2 text-[2rem] font-semibold tracking-tightest text-text sm:text-[2.5rem]">
          How Achilles works, and how to break it.
        </h1>
        <p className="mt-4 text-[0.95rem] leading-relaxed text-muted">
          Achilles builds a provenance-checked evidence graph from public data. The core
          principle: a <b className="text-text">deterministic engine</b> computes everything
          quantitative, and the language model is confined to two jobs — extracting typed
          claims from literature and narrating already-computed results with citations. It
          never invents a number, a score, or a schedule. If a claim can&apos;t be grounded,
          it does not become an edge.
        </p>

        <Section n="1" title="The object: the reversible target">
          Most target-ID tools name a gene <i>associated</i> with resistance. Achilles names
          the vulnerability resistance <i>creates</i> — the reversible (&ldquo;flipper&rdquo;)
          target that collateral sensitivity opens — and grounds it in what real evolved
          lineages did next. The core data object is an{" "}
          <b className="text-text">evidence edge</b>:{" "}
          <code className="rounded bg-surface2/60 px-1 py-0.5 font-mono text-[0.82em]">
            (source, relation, target, provenance, confidence)
          </code>
          . Provenance is never null.
        </Section>

        <Section n="2" title="Deterministic core (no LLM)">
          Lineage reconstruction (a minimum-spanning tree over allelic distance), flipper
          detection (allele-reversal along lineage paths), the target rank score, and the
          collateral-sensitivity / cycling math are plain, unit-tested Python — same input,
          same output. These never call a model. The pipeline is organism-agnostic: it runs
          on any genotype table (see the console&apos;s &ldquo;bring your own data&rdquo;),
          which is verified by a generalization test on a non-Burkholderia scheme.
        </Section>

        <Section n="3" title="The LLM&apos;s two bounded jobs">
          <b className="text-text">Extraction:</b> from a single public abstract, the model
          returns typed claims{" "}
          <code className="rounded bg-surface2/60 px-1 py-0.5 font-mono text-[0.82em]">
            (subject, relation, object, evidence_span, confidence)
          </code>{" "}
          using only that text. <b className="text-text">Narration:</b> given
          already-computed results, it writes a short, cited explanation. Every model call
          returns JSON validated against a Pydantic schema before use; prompts forbid outside
          knowledge and forbid computing numbers.
        </Section>

        <Section n="4" title="Grounding: cite or it doesn&apos;t exist">
          Each extracted claim is checked against reference-database facts (CARD/ARO for AMR
          determinants, UniProt for protein identity, ChEMBL for tractability). A claim
          becomes a <b className="text-text">grounded</b> edge only if a reference fact
          corroborates it, carrying that accession. A claim supported only by an abstract is
          kept as <b className="text-text">abstract-only</b> — visually distinct, never shown
          as validated. Accessions are never invented; only accessions present in the
          reference facts are cited.
        </Section>

        <Section n="5" title="Validation: recall, adversarial refusal, zero fabrication">
          The engine is held to an independent, publicly-cited control set (29 controls).
          It must <b className="text-text">recover</b> every established relationship from a
          grounded edge (recall), and <b className="text-text">refuse</b> an{" "}
          <b className="text-text">adversarial battery</b> of plausible-but-false claims —
          the traps a hallucinating model falls for (e.g. MarR&nbsp;&rarr;&nbsp;vancomycin,
          efflux&nbsp;&rarr;&nbsp;isoniazid, a regulator posed as a carbapenem target). The
          fabrication count — a grounded edge supporting a known-false control — must be{" "}
          <b className="text-text">zero</b>. This is computed live, and a{" "}
          <b className="text-text">red-team</b> box lets anyone type their own claim and watch
          it be supported (with a citation) or refused.
        </Section>

        <Section n="6" title="Retrodiction: foresight, not just recall">
          Recovering known biology proves consistency. The stronger test is foresight:
          freeze the literature at a cutoff year, hide everything after it, and measure how
          many later-confirmed relationships the pre-cutoff graph already pointed at.
          Anticipation is graded (drug-level &gt; mechanism-level), honest &ldquo;not
          anticipable&rdquo; is reported when there is no pre-cutoff signal, and — the
          invariant — <b className="text-text">no false claim is ever anticipated</b>.
        </Section>

        <Section n="7" title="Treatment optimization (a hypothesis, never advice)">
          The antibiotic-cycling suggestion is walked deterministically over a reciprocal
          collateral-sensitivity graph; the public pairs are cited to the literature
          (PMID&nbsp;32335276). The model only narrates it. It is framed everywhere as a{" "}
          <b className="text-text">research hypothesis</b> — no pharmacokinetics, dosing,
          toxicity, or in-vivo validation is modeled, and it is not a treatment
          recommendation.
        </Section>

        <Section n="8" title="Reproducibility">
          The public evidence graph rebuilds offline from a committed corpus — no live API
          needed to seed. All sources are public: PubMLST, Europe PMC, CARD/ARO, UniProt,
          ChEMBL, NCBI, AlphaFold (via Tamarind), RCSB. The repository is MIT.
          <pre className="mt-3 overflow-x-auto rounded-lg border border-line/12 bg-surface2/40 p-3 font-mono text-[0.78rem] text-muted">
{`make db            # Postgres + pgvector
make seed-public   # PubMLST + committed public caches (no private data)
make backend       # FastAPI  :8000
make frontend      # Next.js  :3000`}
          </pre>
        </Section>

        <Section n="9" title="Limitations (stated plainly)">
          <ul className="mt-1 space-y-1.5">
            <Li>
              The validation control set is small relative to a large-N benchmark; its
              strength is the <i>property</i> (recall + adversarial refusal + zero
              fabrication) and the live red-team, not the raw count.
            </Li>
            <Li>
              A second domain (Pseudomonas aeruginosa) is <i>scaffolded</i> — the pipeline is
              wired for it, but its grounded gene/literature data must be fetched, not
              assumed. &ldquo;Domain-agnostic&rdquo; is demonstrated on the deterministic core
              today; a second fully-grounded domain is in progress.
            </Li>
            <Li>
              Docking shows a cited inhibitor <i>ready to dock</i>; a computed pose requires a
              Tamarind run. No pose is fabricated.
            </Li>
            <Li>
              Lineage is a deterministic reconstruction from allelic distance, not a
              validated phylogeny; collateral sensitivity is frequently non-reciprocal and
              strain-specific.
            </Li>
          </ul>
        </Section>

        <div className="mt-12 flex flex-wrap items-center gap-3 border-t border-line/8 pt-6 text-[0.8rem]">
          <Link href="/explore" className="text-accentStrong hover:underline">
            Open the console →
          </Link>
          <span className="text-line/25">·</span>
          <a
            href="https://github.com/akhimass/Achilles"
            target="_blank"
            rel="noopener noreferrer"
            className="text-muted hover:text-text"
          >
            Source on GitHub · MIT
          </a>
        </div>
      </main>
    </div>
  );
}

function Section({ n, title, children }: { n: string; title: string; children: React.ReactNode }) {
  return (
    <section className="mt-8">
      <h2 className="flex items-center gap-2.5 text-[1.05rem] font-semibold text-text">
        <span className="grid h-6 w-6 shrink-0 place-items-center rounded-md bg-accent/12 font-mono text-[0.72rem] text-accentStrong">
          {n}
        </span>
        {title}
      </h2>
      <div className="mt-2 text-[0.9rem] leading-relaxed text-muted">{children}</div>
    </section>
  );
}

function Li({ children }: { children: React.ReactNode }) {
  return (
    <li className="flex gap-2">
      <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-accent/70" />
      <span>{children}</span>
    </li>
  );
}
