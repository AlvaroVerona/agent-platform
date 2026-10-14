"""MCP server for agent-platform: turn an idea into a validated tech spec, from any MCP client (Claude Desktop, Claude Code...).

Run (stdio):  python -m src.mcp_server.server
Everything runs on the local Ollama model; no data leaves the machine.
Logs go to stderr: on stdio transport, stdout belongs to the protocol.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from mcp.server.mcpserver import MCPServer

from src.agents.qa_agent import QAAgent
from src.agents.utils.qa_gate import QAGate
from src.database.database import SessionLocal
from src.database.init_db import init_db
from src.database.repository import RunRepository
from src.schemas.qa_report import QAReport
from src.services.run_service import RunService

logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")

mcp = MCPServer(
    "agent-platform",
    instructions=(
        "Turns a product idea into a technical spec and reviews it. generate_tech_spec runs the whole local pipeline "
        "(product manager, architect, QA loop) and can take one to three minutes. check_tech_spec is instant and "
        "deterministic; review_tech_spec adds an LLM review on top of it."
    ),
)

init_db()  # creates the tables on a fresh database
_service = RunService()


def _run_summary(run) -> dict:
    return {"run_id": run.id, "created_at": run.created_at.isoformat(), "idea": run.idea, "status": run.status,
            "approved": run.final_tech_spec is not None}


def _generate(idea: str) -> dict:
    try:
        tech_spec = _service.execute(idea)
    except Exception as e:
        return {"approved": False, "run_id": _service.last_run_id, "error": f"{type(e).__name__}: {e}"}
    return {"approved": tech_spec is not None, "run_id": _service.last_run_id, "tech_spec": tech_spec}


@mcp.tool()
async def generate_tech_spec(idea: str) -> dict:
    """Run the full pipeline on an idea (product spec, tech spec, QA loop of up to 3 iterations).

    Returns {approved, run_id, tech_spec}; tech_spec is null when QA never approved it, and `error` is set if the
    pipeline failed. The run is stored and can be read later with get_run. Takes one to three minutes.
    """
    return await asyncio.to_thread(_generate, idea)


@mcp.tool()
def check_tech_spec(product_spec: dict, tech_spec: dict) -> dict:
    """Deterministic coherence check, no LLM: endpoints valid and unique, components consistent with the stack, risks mitigated.

    Returns {ok, issues}. Instant.
    """
    ok, issues = QAGate.validate(product_spec, tech_spec)
    return {"ok": ok, "issues": issues}


def _review(product_spec: dict, tech_spec: dict) -> dict:
    report: QAReport = QAAgent().run(product_spec, tech_spec)
    return {"approved": _service._qa_approved(report), **report.model_dump(exclude_none=True)}


@mcp.tool()
async def review_tech_spec(product_spec: dict, tech_spec: dict) -> dict:
    """Review a tech spec with the local LLM plus the deterministic gate. Returns score, issues, suggestions, patch and approved."""
    return await asyncio.to_thread(_review, product_spec, tech_spec)


@mcp.tool()
def list_runs(limit: int = 20) -> list[dict]:
    """Most recent pipeline runs (newest first) with their status and whether QA approved a final spec."""
    return [_run_summary(r) for r in _service.get_all_runs()[: max(1, min(limit, 100))]]


@mcp.tool()
def get_run(run_id: int) -> dict:
    """Full detail of one run: idea, product spec, final tech spec and the QA score of each iteration."""
    with SessionLocal() as db:  # one session for the run and its iterations (lazy loading needs it open)
        run = RunRepository(db).get_run(run_id)
        if run is None:
            return {"error": f"run {run_id} not found"}
        its = [{"index": i.index, "approved": i.approved, "qa_score": (i.qa_report or {}).get("score")} for i in run.iterations]
        return {**_run_summary(run), "product_spec": run.product_spec, "final_tech_spec": run.final_tech_spec, "iterations": its}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
