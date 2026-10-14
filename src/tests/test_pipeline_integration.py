"""
Test de integración del pipeline completo (PM -> Tech -> QA -> persistencia)
sin Ollama: se mockea OllamaClient.generate y se usa una BD SQLite temporal.
"""

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import src.services.run_service as run_service_module
from src.database.database import Base
from src.database.models import Iteration, Run
from src.llm.ollama_client import OllamaClient
from src.services.run_service import RunService

PRODUCT_JSON = json.dumps({
    "project_name": "Test Platform",
    "goal": "diseñar agentes",
    "target_users": ["developers"],
    "main_features": ["crear agentes"],
    "mvp_scope": ["core"],
    "assumptions": ["backend python"],
    "technical_constraints": ["Python", "FastAPI"],
})

# Satisface QAGate: api_design con method/path, components, Python en stack
TECH_JSON = json.dumps({
    "architecture": {
        "description": "monolito modular",
        "type": "monolith",
        "services": ["api"],
    },
    "stack": ["Python", "FastAPI"],
    "components": [
        {
            "name": "API",
            "description": "backend",
            "technology_stack": ["Python"],
        }
    ],
    "api_design": [
        {
            "name": "Core API",
            "description": "",
            "endpoints": [
                {"method": "GET", "path": "/health", "description": ""}
            ],
        }
    ],
    "risks": [],
    "integrations": [],
})

QA_APPROVES = json.dumps({
    "score": 0.9,
    "is_valid": True,
    "issues": [],
    "suggestions": [],
    "patch": {},
})

QA_REJECTS = json.dumps({
    "score": 0.4,
    "is_valid": False,
    "issues": [
        {
            "severity": "critical",
            "message": "falta autenticacion en la api",
        }
    ],
    "suggestions": [{"message": "añadir JWT"}],
    "patch": {"stack": ["Python", "FastAPI", "JWT"]},
})


@pytest.fixture()
def db_session_factory(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(bind=engine)

    factory = sessionmaker(bind=engine)

    # RunService usa SessionLocal importado en su módulo
    monkeypatch.setattr(run_service_module, "SessionLocal", factory)

    return factory


def _fake_llm(monkeypatch, qa_response: str):
    """
    Mockea OllamaClient.generate enrutando por el contenido del prompt.
    Devuelve la lista de prompts recibidos, por orden.
    """

    prompts = []

    def fake_generate(self, prompt: str, schema=None) -> str:
        prompts.append(prompt)

        if "Product Manager" in prompt:
            return PRODUCT_JSON

        if "Arquitecto de Software" in prompt:
            return TECH_JSON

        if "QA Lead" in prompt:
            return qa_response

        raise AssertionError(f"Prompt inesperado:\n{prompt[:200]}")

    monkeypatch.setattr(OllamaClient, "generate", fake_generate)

    return prompts


def test_pipeline_approves_first_iteration(db_session_factory, monkeypatch):
    _fake_llm(monkeypatch, QA_APPROVES)

    result = RunService().execute("una idea de prueba")

    assert result is not None
    assert result["stack"] == ["Python", "FastAPI"]

    db = db_session_factory()
    runs = db.query(Run).all()
    iterations = db.query(Iteration).all()

    assert len(runs) == 1
    assert runs[0].status == "QA_APPROVED"
    assert runs[0].product_spec["project_name"] == "Test Platform"
    assert runs[0].final_tech_spec["stack"] == ["Python", "FastAPI"]

    assert len(iterations) == 1
    assert iterations[0].approved is True
    db.close()


def test_pipeline_exhausts_iterations_on_rejection(
    db_session_factory, monkeypatch
):
    prompts = _fake_llm(monkeypatch, QA_REJECTS)

    result = RunService().execute("una idea de prueba")

    assert result is None

    db = db_session_factory()
    runs = db.query(Run).all()
    iterations = db.query(Iteration).all()

    assert len(runs) == 1
    assert runs[0].status == "QA_FAILED"
    assert runs[0].final_tech_spec is None

    assert len(iterations) == 3
    assert [it.index for it in iterations] == [1, 2, 3]
    assert not any(it.approved for it in iterations)
    db.close()

    # §3.3: a partir de la 2ª iteración, el arquitecto debe recibir
    # el feedback real de QA en su prompt
    tech_prompts = [p for p in prompts if "Arquitecto de Software" in p]

    assert len(tech_prompts) == 3
    assert "falta autenticacion" not in tech_prompts[0]
    assert "falta autenticacion" in tech_prompts[1]
    assert "añadir JWT" in tech_prompts[1]
    # y el patch de QA se aplicó al spec previo
    assert "JWT" in tech_prompts[1]
