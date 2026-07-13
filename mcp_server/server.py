"""Achilles MCP server — grounded AMR/discovery evidence as tools for any Claude agent.

Run this and add it to Claude Code or Cowork (see README.md). Every tool answers only
from the grounded evidence graph — it cites or it refuses — so an agent using Achilles
inherits the same guarantee: no ungrounded claim, and every fact carries a source.

    pip install -r requirements.txt
    ACHILLES_API_BASE=https://achilles-production-2565.up.railway.app python server.py
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

try:  # works both as a module (`python -m mcp_server.server`) and a script
    from . import tools
except ImportError:  # pragma: no cover
    import tools  # type: ignore

mcp = FastMCP(
    "achilles",
    instructions=(
        "Achilles is a grounded evidence graph for antimicrobial-resistance target "
        "identification and treatment optimization. Use these tools to get CITED answers, "
        "check whether a claim is grounded (it refuses ungrounded claims rather than "
        "guessing), rank druggable targets, read the self-validation, and translate a "
        "finding from bench to bedside. Treatment content is research decision-support, "
        "never medical advice — surface its caveats."
    ),
)


@mcp.tool()
async def ask(question: str, persona: str = "researcher") -> dict:
    """Ask Achilles a question in plain language. Returns a cited answer built only from
    grounded evidence, or an honest refusal if nothing supports it. persona: researcher |
    physician | computational (sets the lens and caveats)."""
    return await tools.ask(question, persona)


@mcp.tool()
async def ground_claim(gene: str, target: str, relation: str = "") -> dict:
    """Check whether a resistance claim is grounded. e.g. gene='MarR', target='ciprofloxacin'
    → supported (with citation); gene='MarR', target='vancomycin' → refused. Never fabricates."""
    return await tools.ground_claim(gene, target, relation or None)


@mcp.tool()
async def rank_targets(organism: str = "Burkholderia multivorans", limit: int = 5) -> list:
    """Top candidate targets for an organism by deterministic rank score, with grounded-edge
    counts and ChEMBL tractability."""
    return await tools.rank_targets(organism, limit)


@mcp.tool()
async def validate() -> dict:
    """Achilles' live self-validation: recall on known biology, refusal of an adversarial
    battery of false claims, and the fabrication count (must be 0)."""
    return await tools.validate()


@mcp.tool()
async def bridge(gene: str) -> dict:
    """Translate one gene's grounded finding researcher → physician: mechanism + ranked
    target on one side, drugs it drives resistance to + the cited collateral-sensitivity
    strategy on the other. Research decision-support, not medical advice."""
    return await tools.bridge(gene)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
