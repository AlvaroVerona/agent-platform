"""End-to-end over stdio: spawn the real server process and talk to it with an MCP client. No LLM involved."""

import json
import sys

import anyio
import pytest

pytest.importorskip("mcp")

from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

PRODUCT = {"project_name": "Reservas", "goal": "Gestionar reservas"}
SPEC = {
    "project_name": "Reservas", "goal": "Gestionar reservas", "stack": ["Go"],
    "components": [{"name": "API", "technology_stack": ["Go"]}],
    "api_design": [{"name": "r", "endpoints": [{"method": "GET", "path": "/r"}]}],
}


def _payload(result):
    if getattr(result, "structured_content", None):
        sc = result.structured_content
        return sc.get("result", sc)
    return json.loads(result.content[0].text)


async def _session_run(tmp_path, fn):
    params = StdioServerParameters(command=sys.executable, args=["-m", "src.mcp_server.server"],
                                   env={"AGENT_PLATFORM_DB": str(tmp_path / "t.db")})
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            return await fn(s)


def test_server_lists_tools_and_runs_deterministic_check(tmp_path):
    async def go(s):
        names = {t.name for t in (await s.list_tools()).tools}
        good = _payload(await s.call_tool("check_tech_spec", {"product_spec": PRODUCT, "tech_spec": SPEC}))
        bad = _payload(await s.call_tool("check_tech_spec", {"product_spec": PRODUCT, "tech_spec": {**SPEC, "api_design": []}}))
        missing = _payload(await s.call_tool("get_run", {"run_id": 999}))
        return names, good, bad, missing

    names, good, bad, missing = anyio.run(_session_run, tmp_path, go)
    assert names == {"generate_tech_spec", "check_tech_spec", "review_tech_spec", "list_runs", "get_run"}
    assert good["ok"] is True
    assert bad["ok"] is False and any("api_design" in i for i in bad["issues"])
    assert "not found" in missing["error"]


def test_get_run_reads_iterations_of_a_stored_run(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from src.database.database import Base
    from src.database.repository import RunRepository

    engine = create_engine(f"sqlite:///{tmp_path}/t.db")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        repo = RunRepository(db)
        run = repo.create_run(idea="idea", status="CREATED")
        run_id = run.id
        repo.create_iteration(run_id=run_id, index=1, tech_spec={}, qa_report={"score": 0.8}, approved=True)

    async def go(s):
        return _payload(await s.call_tool("get_run", {"run_id": run_id}))

    d = anyio.run(_session_run, tmp_path, go)
    assert d["idea"] == "idea" and d["iterations"] == [{"index": 1, "approved": True, "qa_score": 0.8}]
