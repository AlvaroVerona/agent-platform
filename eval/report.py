"""Aggregate eval/results/<version>-repN__<model>.jsonl: per version, mean and range across repetitions (markdown)."""

import json
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean

from src.agents.utils.qa_gate import QAGate

groups = defaultdict(list)
for f in sorted((Path(__file__).parent / "results").glob("*.jsonl")):
    m = re.match(r"(.+)-rep(\d+)__(.+)\.jsonl", f.name)
    recs = [json.loads(line) for line in f.read_text().splitlines() if line.strip()]
    if m and recs:
        groups[(m[1], m[3])].append((int(m[2]), recs))


def rep_metrics(recs):
    n = len(recs)
    gate_ok = sum(QAGate.validate(r["final_product"], r["final_spec"])[0] for r in recs)
    return {"approved": sum(r["approved"] for r in recs) / n, "strict_gate": gate_ok / n,
            "iters": mean(r["iterations"] for r in recs), "secs": mean(r["wall_seconds"] for r in recs)}


def span(vals, pct=True):
    f = (lambda v: f"{v:.0%}") if pct else (lambda v: f"{v:.2f}")
    return f"{f(mean(vals))} ({f(min(vals))} to {f(max(vals))})"


head = ("version", "model", "reps", "approved", "passes strict gate", "mean iterations")
print("| " + " | ".join(head) + " |\n|" + "---|" * len(head))
for (ver, model), reps in sorted(groups.items()):
    ms = [rep_metrics(r) for _, r in sorted(reps)]
    print(f"| {ver} | {model} | {len(ms)} | {span([m['approved'] for m in ms])} | "
          f"{span([m['strict_gate'] for m in ms])} | {span([m['iters'] for m in ms], False)} |")
