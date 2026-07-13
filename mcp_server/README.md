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

## Run it (one-time setup)

The `mcp` SDK needs Python **3.10+** (macOS system `python3` is 3.9), so use a dedicated
virtualenv — the repo's `.mcp.json` already points at it:

```bash
# from the repo root — creates mcp_server/.venv (gitignored) with the right Python + deps
python3 -m venv mcp_server/.venv          # use any Python >= 3.10 (e.g. python3.13)
mcp_server/.venv/bin/pip install -r mcp_server/requirements.txt
```

Smoke-test it (defaults to the public deployment; Ctrl-C to stop):

```bash
mcp_server/.venv/bin/python -m mcp_server.server                          # run from the repo root
ACHILLES_API_BASE=http://localhost:8000 mcp_server/.venv/bin/python -m mcp_server.server  # local backend
```

## Add to Claude Code

The root [`.mcp.json`](../.mcp.json) already points at `mcp_server/.venv/bin/python`, so once
the venv exists Claude Code **auto-discovers** the server — just run `claude` from the repo
root. To register it explicitly instead:

```bash
claude mcp add achilles -- "$(pwd)/mcp_server/.venv/bin/python" -m mcp_server.server
```

Then, in a session:

> **You:** Is MarR → ciprofloxacin resistance grounded? And what are the top targets?
> **Claude:** *(calls `ground_claim` → supported, CARD:ARO:3003378; `rank_targets` → …)*
> **You:** Ask Achilles what re-sensitizes after meropenem, as a physician.
> **Claude:** *(calls `ask` → cited answer + the research-not-advice caveat)*

## Add to Cowork (via the Claude Desktop bridge)

This is a **local stdio** server, so it is *not* added through Cowork's "Connectors" UI —
that flow is for remote servers reached by URL. Register it in **Claude Desktop**, which
bridges local servers into Cowork. Add to
`~/Library/Application Support/Claude/claude_desktop_config.json` (the `bash -c` wrapper sets
the working directory so `-m` can find the package):

```json
{
  "mcpServers": {
    "achilles": {
      "command": "bash",
      "args": ["-c", "cd /ABSOLUTE/PATH/TO/switchback && mcp_server/.venv/bin/python -m mcp_server.server"],
      "env": { "ACHILLES_API_BASE": "https://achilles-production-2565.up.railway.app" }
    }
  }
}
```

Fully quit and reopen Claude Desktop, start a new Cowork chat, then enable **achilles** via
the **+** (lower-left) → Connectors. No API key needed — every tool hits the public deployment.

## Why this matters

This is the point of Achilles as a **platform**, not an app: any Claude agent can reach for
grounded, provenance-checked science and get a cited answer or an honest refusal — the same
discipline, wherever Claude works. Tool shapers are pure and unit-tested (`test_tools.py`);
the network call is a thin wrapper.
