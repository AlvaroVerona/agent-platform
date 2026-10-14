from src.schemas.qa_report import QAReport
from src.services.run_service import RunService


def _service():
    # No necesitamos los agentes (ni Ollama) para la lógica pura
    return RunService.__new__(RunService)


def test_approved_with_warnings_and_decent_score():
    report = QAReport(
        score=0.85,
        is_valid=True,
        issues=[{"severity": "warning", "description": "mejorable"}],
    )
    assert _service()._qa_approved(report) is True


def test_rejected_below_threshold():
    report = QAReport(score=0.7, is_valid=True)
    assert _service()._qa_approved(report) is False


def test_rejected_on_critical_issue():
    report = QAReport(
        score=0.99,
        is_valid=True,
        issues=[{"severity": "critical", "description": "falta api"}],
    )
    assert _service()._qa_approved(report) is False


def test_llm_is_valid_flag_is_ignored():
    # approval rests on score + absence of critical issues; the gate lowers the score when it fails
    assert _service()._qa_approved(QAReport(score=0.9, is_valid=False)) is True
    assert _service()._qa_approved(QAReport(score=0.5, is_valid=True)) is False


def test_tech_context_includes_qa_feedback():
    report = QAReport(
        score=0.5,
        is_valid=False,
        issues=[
            {"severity": "critical", "description": "no hay auth"},
            {"severity": "warning", "description": ""},  # sin descripción: fuera
        ],
        suggestions=[{"description": "añadir JWT"}],
    )

    spec = {"stack": ["Python"]}
    context = _service()._build_tech_context(spec, report)

    assert context["previous_tech_spec"] == spec
    assert len(context["qa_issues"]) == 1
    assert context["qa_issues"][0]["description"] == "no hay auth"
    assert context["qa_suggestions"] == [{"description": "añadir JWT"}]


def test_tech_context_without_report():
    context = _service()._build_tech_context({"stack": []}, None)

    assert context == {"previous_tech_spec": {"stack": []}}
