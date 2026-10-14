import json

import pytest

from src.agents.tech_architect_agent import TechArchitectAgent, TechSpecError
from src.agents.utils.qa_gate import QAGate
from src.agents.utils.tech_patch_validator import TechPatchValidator
from src.agents.utils.tech_spec_hard_validator import TechSpecHardValidator
from src.llm.ollama_client import OllamaClient

PRODUCT = {"project_name": "Reservas", "goal": "Gestionar reservas"}


def good_spec(**over):
    spec = {
        "project_name": "Reservas", "goal": "Gestionar reservas", "stack": ["Go", "SQLite"],
        "components": [{"name": "API", "technology_stack": ["Go"]}],
        "api_design": [{"name": "Reservas", "endpoints": [{"method": "POST", "path": "/reservas"}]}],
        "risks": [{"name": "Overbooking", "mitigation_strategy": "Bloqueo optimista"}],
    }
    spec.update(over)
    return spec


def test_gate_accepts_a_coherent_non_python_spec():
    assert QAGate.validate(PRODUCT, good_spec()) == (True, [])


@pytest.mark.parametrize("change, fragment", [
    ({"api_design": []}, "Missing api_design"),
    ({"components": []}, "No components"),
    ({"stack": []}, "Empty stack"),
    ({"project_name": "Otra cosa"}, "project_name differs"),
    ({"components": [{"name": "API", "technology_stack": ["Java"]}]}, "absent from the stack"),
    ({"components": [{"name": "API", "technology_stack": ["Go"]}, {"name": "api", "technology_stack": ["Go"]}]}, "Duplicate component"),
    ({"api_design": [{"name": "x", "endpoints": [{"method": "FETCH", "path": "/a"}]}]}, "Invalid HTTP method"),
    ({"api_design": [{"name": "x", "endpoints": [{"method": "GET", "path": "a"}]}]}, "Invalid endpoint path"),
    ({"api_design": [{"name": "x", "endpoints": [{"method": "GET", "path": "/a"}, {"method": "GET", "path": "/a"}]}]}, "Duplicate endpoint"),
    ({"risks": [{"name": "R", "mitigation_strategy": ""}]}, "no mitigation"),
])
def test_gate_rejects_incoherent_specs(change, fragment):
    ok, issues = QAGate.validate(PRODUCT, good_spec(**change))
    assert not ok
    assert any(fragment in i for i in issues), issues


def test_validators_do_not_invent_content():
    cleaned = TechPatchValidator.validate({"api_design": [], "stack": []})
    assert cleaned["api_design"] == [] and cleaned["stack"] == []
    out = TechSpecHardValidator.validate({"api_design": [{"name": "x", "endpoints": []}], "stack": ["Go"], "components": []})
    assert out["api_design"] == [] and out["stack"] == ["Go"]


def test_architect_fails_loudly_instead_of_returning_a_canned_spec(monkeypatch):
    monkeypatch.setattr(OllamaClient, "generate", lambda self, prompt, schema=None: "not json at all")
    agent = TechArchitectAgent()
    with pytest.raises(TechSpecError):
        agent.run({"project_name": "Reservas"})


def test_architect_requests_structured_output(monkeypatch):
    seen = {}

    def fake(self, prompt, schema=None):
        seen["schema"] = schema
        return json.dumps({"stack": ["Go"], "components": [{"name": "API"}],
                           "api_design": [{"name": "r", "endpoints": [{"method": "GET", "path": "/r"}]}]})

    monkeypatch.setattr(OllamaClient, "generate", fake)
    spec = TechArchitectAgent().run({"project_name": "Reservas"})
    assert seen["schema"]["type"] == "object"
    assert spec.stack == ["Go"]


def test_gate_matches_labelled_stack_entries():
    spec = good_spec(stack=["Lenguaje de programación: Go", "Base de datos: SQLite"])
    assert QAGate.validate(PRODUCT, spec)[0]
    spec["components"] = [{"name": "API", "technology_stack": ["Go", "Redis"]}]
    ok, issues = QAGate.validate(PRODUCT, spec)
    assert not ok and "Redis" in issues[0]
