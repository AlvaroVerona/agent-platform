"""
Regresión del bug §3.1 del HANDOVER:

el sanitizador de QA producía patches con formato
{"operation": "replace", "value": [...]} que no validaban
contra QAPatch (Pydantic) y tumbaban el pipeline.

El formato canónico del patch es una lista plana de strings.
"""

from src.agents.qa_agent import QAAgent
from src.agents.utils.tech_diff import TechDiffApplier
from src.schemas.qa_report import QAReport


def _sanitize(data):
    # _sanitize no usa self ni el LLM
    return QAAgent._sanitize(QAAgent.__new__(QAAgent), data)


def test_stack_replace_operation_becomes_flat_list():
    data = _sanitize({
        "score": 0.7,
        "is_valid": False,
        "patch": {
            "stack": {
                "operation": "replace",
                "value": ["Python", "FastAPI", ""],
            }
        },
    })

    assert data["patch"]["stack"] == ["Python", "FastAPI"]

    # Y el resultado debe validar contra QAReport sin excepciones
    report = QAReport(**data)
    assert report.patch.stack == ["Python", "FastAPI"]


def test_stack_list_of_dicts_normalized():
    data = _sanitize({
        "patch": {
            "stack": [{"name": "Python"}, {"name": " "}, "Docker"],
        },
    })

    assert data["patch"]["stack"] == ["Python", "Docker"]
    QAReport(**data)


def test_stack_garbage_dropped():
    data = _sanitize({"patch": {"stack": "PostgreSQL"}})

    assert "stack" not in data["patch"]
    QAReport(**data)


def test_sanitized_patch_applies_cleanly():
    data = _sanitize({
        "patch": {
            "stack": {"operation": "replace", "value": ["Python", "Redis"]},
        },
    })

    base = {"stack": ["Python", "FastAPI"], "components": [{"name": "API"}]}
    result = TechDiffApplier.apply_patch(base, data["patch"])

    assert result["stack"] == ["Python", "Redis"]
    # el patch no debe borrar lo que no toca
    assert result["components"] == [{"name": "API"}]


def test_issue_strings_become_dicts():
    data = _sanitize({"issues": ["falta auth", {"description": "x"}]})

    assert data["issues"][0]["description"] == "falta auth"
    assert data["issues"][0]["severity"] == "warning"
    assert data["issues"][1]["description"] == "x"


def test_issue_message_key_normalized_to_description():
    # Regresión: llama3.1 devuelve issues/suggestions con clave "message";
    # antes acababan como description="" y el feedback de QA se perdía.
    data = _sanitize({
        "issues": [{"message": "falta auth", "location": "api"}],
        "suggestions": [{"message": "usar JWT"}],
    })

    assert data["issues"][0]["description"] == "falta auth"
    assert data["suggestions"][0]["description"] == "usar JWT"
