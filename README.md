# agent-platform

[![CI](https://github.com/AlvaroVerona/agent-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/AlvaroVerona/agent-platform/actions/workflows/ci.yml)

A small multi-agent pipeline that turns a product idea into a **validated technical spec**, running entirely on a local
[Ollama](https://ollama.com) model (no paid API, no data leaving the machine). It can be used from the command line or as an
**MCP server** from Claude Code, Claude Desktop or any MCP client.

```
idea ─▶ Product Manager ─▶ Tech Architect ─▶ QA (LLM review + deterministic gate) ─┐
                               ▲                                                   │ not approved:
                               └──────────── patch + QA feedback, up to 3 rounds ◀─┘
```

Every run and each iteration (spec, QA report, approval) is stored in SQLite.

## What is different from a plain "prompt chain"

- **Structured outputs.** Each agent asks Ollama for JSON that matches a pydantic schema, so decoding is constrained instead of
  parsed out of free text.
- **Failing loudly.** If the architect cannot produce a valid spec it retries once and then raises. It does not return a canned
  spec, and the validators do not invent endpoints.
- **A deterministic gate next to the LLM reviewer.** `QAGate` checks things a model should not be trusted with: valid and unique
  endpoints, components that only use technologies listed in the stack, spec identity matching the product, risks with a
  mitigation. When it fails, the score is capped and a critical issue is added.
- **Measured, not assumed.** `eval/` runs the pipeline on 20 fixed ideas and reports approval rate, iterations and coherence.

## Quick start

Requires Python 3.12 and a running Ollama with the `llama3.1` model (`ollama pull llama3.1`).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,mcp]"
python -m src.main "Booking app for padel courts with online payments"
pytest -q
```

The database is `agent_platform.db` in the project root; set `AGENT_PLATFORM_DB` to use another file.
The agent prompts are written in Spanish and the specs come out in Spanish.

## MCP server

Five tools, all local:

| Tool | What it does |
|---|---|
| `generate_tech_spec(idea)` | Runs the whole pipeline (1 to 3 minutes). Returns `{approved, run_id, tech_spec}` |
| `check_tech_spec(product_spec, tech_spec)` | Deterministic gate, instant, no LLM |
| `review_tech_spec(product_spec, tech_spec)` | LLM review plus the gate: score, issues, suggestions, patch |
| `list_runs(limit)` | Recent runs and whether QA approved a final spec |
| `get_run(run_id)` | One run with its product spec, final spec and the QA score of each iteration |

Register it in Claude Code:

```bash
claude mcp add agent-platform --scope user -- \
  /path/to/agent-platform/.venv/bin/python /path/to/agent-platform/scripts/run_mcp.py
```

`scripts/run_mcp.py` works from any directory. Some clients time out before a long `generate_tech_spec` call returns;
`check_tech_spec` and `review_tech_spec` are fast.

## Evaluation

20 fixed ideas (`eval/ideas.json`), `llama3.1`, 3 repetitions per version (`python -m eval.run_eval`, `python -m eval.report`):

| version | approved | final specs passing the strict gate | mean iterations |
|---|---|---|---|
| original pipeline | 53% (50% to 55%) | 88% (85% to 90%) | 2.38 |
| this version | 95% (95% to 95%) | 95% (95% to 95%) | 1.20 |

Read it with care (details in [`eval/RESULTS.md`](eval/RESULTS.md)):

- The approval gain mixes three changes that were not measured separately: temperature 0, approval that no longer uses the
  reviewer's own `is_valid` flag, and the rest (structured outputs, gate, neutral prompts).
- Temperature 0 makes this version's three repetitions nearly identical, so they say nothing about its variability.
- The gap in final-spec coherence (88% vs 95%) is much smaller than the gap in approval.
- Silent fallbacks and invented content never occurred in the 120 runs, so those safeguards were not exercised.
- One model, one idea set.

## Layout

```
src/agents/        product manager, tech architect, QA agent and their validators
src/schemas/       pydantic schemas used both for validation and as the JSON schema sent to Ollama
src/services/      RunService: the pipeline loop and approval rule
src/database/      SQLAlchemy models and repository (SQLite)
src/mcp_server/    the MCP server
eval/              idea set, runner, report and results
```

## Known limits

- Only Ollama is supported, and the package is imported as `src` (not yet a proper installable package name).
- Approval is score >= 0.8 with no critical issue; that threshold is not calibrated against human judgement.
- The one idea that is never approved (the financial KPI dashboard, in all three repetitions) fails the same way every time:
  a component uses D3.js, which is missing from the stack, and the architect does not fix it in three rounds. The gate catches
  it correctly; the repair loop does not resolve it.

## License

MIT
