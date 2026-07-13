# Achilles MCP server

Achilles as **tools any Claude agent can call** — in Claude Code, Cowork, or the API. The
grounded evidence graph becomes callable primitives, and the agent inherits the guarantee:
**it cites, or it refuses.** No ungrounded claim, every fact with a source.

## Tools

| Tool | What it does |
|---|---|
| `ask(question, persona)` | Plain-language question → a cited answer built only from grounded evidence, or an honest refusal. `persona`: researcher \| physician \| computational. |
| `ground_claim(gene, target, relation)` | Adjudicate a claim. `MarR / ciprofloxacin` → **supported** (cited); `MarR / vancomycin` → **refused**. Never fabricates. |
| `rank_targets(organism, limit)` | Top candidate targets by deterministic rank score, with grounded-edge counts + ChEMBL tractability. |
| `validate()` | The live self-validation: recall, adversarial refusal, fabrication count (must be 0). |
| `bridge(gene)` | Translate one gene's grounded finding researcher → physician (mechanism + target ⟶ drugs + cited cycle). Research decision-support, not medical advice. |

All tools hit the live API (`ACHILLES_API_BASE`, default the public deployment). No key needed.

## Run it

```bash
cd mcp_server && pip install -r requirements.txt
# points at the public deployment by default; override for a local backend:
ACHILLES_API_BASE=http://localhost:8000 python -m mcp_server.server   # run from the repo root
```

## Add to Claude Code

```bash
# from the repo root
claude mcp add achilles -- python -m mcp_server.server
```

or in `.mcp.json`:

```json
{
  "mcpServers": {
    "achilles": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "env": { "ACHILLES_API_BASE": "https://achilles-production-2565.up.railway.app" }
    }
  }
}
```

Then, in a Claude Code / Cowork session:

> **You:** Is MarR → ciprofloxacin resistance grounded? And what are the top targets?
> **Claude:** *(calls `ground_claim` → supported, CARD:ARO:3003378; `rank_targets` → …)*
> **You:** Ask Achilles what re-sensitizes after meropenem, as a physician.
> **Claude:** *(calls `ask` → cited answer + the research-not-advice caveat)*

## Add to Cowork

Run the server (above), then add it as a local MCP connector in Cowork's connector settings
(command `python -m mcp_server.server`, run from the repo root, with `ACHILLES_API_BASE`
set). Cowork's Claude can then call the Achilles tools directly from any workflow.

## Why this matters

This is the point of Achilles as a **platform**, not an app: any Claude agent can reach for
grounded, provenance-checked science and get a cited answer or an honest refusal — the same
discipline, wherever Claude works. Tool shapers are pure and unit-tested (`test_tools.py`);
the network call is a thin wrapper.
