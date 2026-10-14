"""Measure pipeline quality on a fixed idea set, without touching the database.

    python -m eval.run_eval --label baseline --model llama3.1 --n 5

One JSON line per idea is appended to eval/results/<label>__<model>.jsonl, so an interrupted run resumes where it stopped.
Metrics per idea: pm_ok, final approval, iterations used, QA parse failures, architect fallbacks, fabricated-content flags,
LLM calls and seconds. `python -m eval.report` aggregates the files.
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

from src.agents.utils.tech_diff import TechDiffApplier
from src.llm.ollama_client import OllamaClient
from src.services.run_service import RunService

ROOT = Path(__file__).parent
MAX_ITERATIONS = 3


def fabricated_flags(spec: dict) -> list[str]:
    """Content the pipeline invents instead of getting it from the model."""
    flags = []
    for api in spec.get("api_design", []):
        if api.get("name") == "Base API":
            flags.append("base_api")
        if any(e.get("path") == "/health" and e.get("description") == "Health check" for e in api.get("endpoints", [])):
            flags.append("default_health_endpoint")
    if not spec.get("components"):
        flags.append("no_components")
    return sorted(set(flags))


def run_one(svc: RunService, idea: str) -> dict:
    rec = {"idea": idea, "pm_ok": False, "approved": False, "iterations": 0, "qa_parse_failures": 0, "qa_gate_blocks": 0,
           "fallbacks": 0, "fabricated": [], "scores": [], "blocking": [], "error": None}
    clients = [svc.pm.llm, svc.tech.llm, svc.qa.llm]
    calls0 = sum(c.calls for c in clients)
    secs0 = sum(c.seconds for c in clients)
    fb0 = svc.tech.fallback_count
    t0 = time.time()
    try:
        product = svc.pm.run(idea)
        rec["pm_ok"] = True
        tech_state = None
        for it in range(1, MAX_ITERATIONS + 1):
            rec["iterations"] = it
            tech_dict = svc.tech.run(product.model_dump(), tech_state).model_dump()
            qa = svc.qa.run(product.model_dump(), tech_dict)
            rec["scores"].append(round(qa.score, 2))
            ids = [i.get("id") for i in qa.issues if isinstance(i, dict)]
            rec["qa_parse_failures"] += ids.count("parser")
            rec["qa_gate_blocks"] += ids.count("qa_gate")
            rec["fabricated"] = fabricated_flags(tech_dict)
            rec["final_spec"] = tech_dict
            rec["final_product"] = product.model_dump()
            rec["blocking"] = [str(i.get("description"))[:140] for i in qa.issues
                               if isinstance(i, dict) and str(i.get("severity", "")).lower() == "critical"]
            rec["is_valid"] = qa.is_valid
            if svc._qa_approved(qa):
                rec["approved"] = True
                break
            patch = svc._extract_patch(qa)
            patched = TechDiffApplier.apply_patch(tech_dict, patch) if patch else tech_dict
            tech_state = svc._build_tech_context(patched, qa)
    except Exception as e:  # a run that crashes counts as a failure, with the reason kept
        rec["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    rec["fallbacks"] = svc.tech.fallback_count - fb0
    rec["llm_calls"] = sum(c.calls for c in clients) - calls0
    rec["llm_seconds"] = round(sum(c.seconds for c in clients) - secs0, 1)
    rec["wall_seconds"] = round(time.time() - t0, 1)
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--model", default="llama3.1")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--start", type=int, default=0)
    a = ap.parse_args()
    logging.disable(logging.CRITICAL)

    ideas = json.loads((ROOT / "ideas.json").read_text())[a.start:a.start + a.n]
    out = ROOT / "results" / f"{a.label}__{a.model.replace(':', '-')}.jsonl"
    done = {json.loads(line)["idea"] for line in out.read_text().splitlines()} if out.exists() else set()

    svc = RunService()
    for agent in (svc.pm, svc.tech, svc.qa):
        agent.llm = OllamaClient(model=a.model)
    for i, idea in enumerate(ideas, a.start):
        if idea in done:
            continue
        rec = run_one(svc, idea)
        rec["model"], rec["label"] = a.model, a.label
        with out.open("a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[{i}] approved={rec['approved']} it={rec['iterations']} fb={rec['fallbacks']} "
              f"qa_fail={rec['qa_parse_failures']} {rec['wall_seconds']}s {rec['error'] or ''}", flush=True)


if __name__ == "__main__":
    main()
