import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Achilles for Claude — MCP tools",
  description:
    "Achilles as tools any Claude agent can call in Claude Code and Cowork: ask, ground_claim, rank_targets, validate, bridge. Grounded science that cites, or refuses.",
};

const TOOLS = [
  {
    name: "ask",
    sig: "ask(question, persona)",
    body: "Plain-language question → a cited answer built only from grounded evidence, or an honest refusal. Persona sets the lens (researcher / physician / computational).",
  },
  {
    name: "ground_claim",
    sig: "ground_claim(gene, target)",
    body: "Adjudicate a claim. MarR → ciprofloxacin returns supported with a citation; MarR → vancomycin returns refused. It never fabricates support.",
  },
  {
    name: "rank_targets",
    sig: "rank_targets(organism)",
    body: "Top candidate targets by deterministic rank score, with grounded-edge counts and ChEMBL tractability.",
  },
  {
    name: "validate",
    sig: "validate()",
    body: "The live self-validation: recall on known biology, refusal of an adversarial battery, and the fabrication count (must be 0).",
  },
  {
    name: "bridge",
    sig: "bridge(gene)",
    body: "Translate one grounded finding researcher → physician: mechanism + target on one side, drugs it drives resistance to + a cited cycle on the other. Not medical advice.",
  },
];

const CONFIG = `{
  "mcpServers": {
    "achilles": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "env": { "ACHILLES_API_BASE": "https://achilles-science…" }
    }
  }
}`;

export default function McpPage() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-line/8 bg-bg/60 backdrop-blur-xl">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-3">
          <Link href="/" className="text-[1.2rem] font-semibold tracking-tightest text-gradient-green">
            Achilles
          </Link>
          <Link
            href="/explore?demo=1"
            className="rounded-full bg-accent px-4 py-1.5 text-[0.8rem] font-semibold text-[rgb(var(--bg))] shadow-glow-sm transition hover:shadow-glow"
          >
            Open console
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-14">
        <p className="text-[0.7rem] font-semibold uppercase tracking-[0.16em] text-accentStrong">
          Achilles for Claude · MCP
        </p>
        <h1 className="mt-2 text-[2rem] font-semibold tracking-tightest text-text sm:text-[2.5rem]">
          Grounded science Claude can <span className="text-gradient-green">call</span>.
        </h1>
        <p className="mt-3 max-w-2xl text-[0.95rem] leading-relaxed text-muted">
          Achilles isn&apos;t only an app — it&apos;s a tool. The MCP server exposes the
          grounded evidence graph to any Claude agent in <b className="text-text">Claude
          Code</b> and <b className="text-text">Cowork</b>. The agent inherits the guarantee:
          it <b className="text-text">cites, or it refuses</b> — no ungrounded claim, every
          fact with a source.
        </p>

        {/* Tools */}
        <div className="mt-8 grid gap-3 sm:grid-cols-2">
          {TOOLS.map((t) => (
            <div key={t.name} className="rounded-2xl border border-line/12 bg-surface2/30 p-4">
              <code className="font-mono text-[0.82rem] text-accentStrong">{t.sig}</code>
              <p className="mt-1.5 text-[0.8rem] leading-relaxed text-muted">{t.body}</p>
            </div>
          ))}
          <div className="flex items-center justify-center rounded-2xl border border-dashed border-line/15 bg-surface2/20 p-4 text-center">
            <p className="text-[0.78rem] text-faint">
              Same discipline, wherever Claude works — the tools call the live API and
              return cited results.
            </p>
          </div>
        </div>

        {/* Connect */}
        <h2 className="mt-12 text-[1.1rem] font-semibold text-text">Connect in one step</h2>
        <p className="mt-1.5 text-[0.85rem] text-muted">
          A <code className="rounded bg-surface2/60 px-1 font-mono text-[0.82em]">.mcp.json</code>{" "}
          at the repo root — Claude Code discovers it automatically:
        </p>
        <pre className="mt-3 overflow-x-auto rounded-xl border border-line/12 bg-[#081210] p-4 font-mono text-[0.78rem] leading-relaxed text-[#cfe]">
{CONFIG}
        </pre>

        {/* Transcript */}
        <h2 className="mt-12 text-[1.1rem] font-semibold text-text">In a session</h2>
        <div className="mt-3 space-y-2.5">
          <Bubble who="You">
            Is MarR → ciprofloxacin resistance grounded? And what re-sensitizes after
            meropenem, as a physician?
          </Bubble>
          <Bubble who="Claude" accent>
            <span className="text-faint">calls</span>{" "}
            <code className="font-mono text-accentStrong">ground_claim(&quot;MarR&quot;, &quot;ciprofloxacin&quot;)</code>{" "}
            → <b className="text-accentStrong">supported</b>{" "}
            <span className="font-mono text-[0.9em] text-muted">CARD:ARO:3003378</span>
            <br />
            <span className="text-faint">calls</span>{" "}
            <code className="font-mono text-accentStrong">ask(&quot;what re-sensitizes after meropenem&quot;, &quot;physician&quot;)</code>{" "}
            → a cited answer, flagged <i>research evidence, not medical advice</i>.
          </Bubble>
          <Bubble who="Claude">
            &quot;Grounded: yes — MarR derepression drives fluoroquinolone resistance
            (CARD:ARO:3003378). After meropenem, the reported reciprocal opening is
            trimethoprim-sulfamethoxazole (PMID 32335276). This is research decision-support,
            not medical advice.&quot;
          </Bubble>
        </div>

        <p className="mt-8 text-[0.9rem] leading-relaxed text-text">
          That&apos;s the point of Achilles as a platform: <b>Claude doing trustworthy
          science through a tool that can&apos;t hallucinate.</b>
        </p>

        <div className="mt-10 flex flex-wrap items-center gap-3 border-t border-line/8 pt-6 text-[0.8rem]">
          <a
            href="https://github.com/akhimass/Achilles/tree/main/mcp_server"
            target="_blank"
            rel="noopener noreferrer"
            className="text-accentStrong hover:underline"
          >
            MCP server on GitHub →
          </a>
          <span className="text-line/25">·</span>
          <Link href="/methods" className="text-muted hover:text-text">Methods</Link>
          <span className="text-line/25">·</span>
          <Link href="/explore?demo=1" className="text-muted hover:text-text">Console</Link>
        </div>
      </main>
    </div>
  );
}

function Bubble({
  who,
  accent,
  children,
}: {
  who: string;
  accent?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div
      className={
        "rounded-xl border p-3 " +
        (accent
          ? "border-accent/20 bg-accent/[0.05]"
          : who === "You"
            ? "border-line/12 bg-surface2/40"
            : "border-line/12 bg-surface2/25")
      }
    >
      <div className="mb-1 text-[0.6rem] font-semibold uppercase tracking-[0.14em] text-faint">
        {who}
      </div>
      <div className="text-[0.82rem] leading-relaxed text-muted">{children}</div>
    </div>
  );
}
