import json
import logging

from src.agents.utils.qa_gate import QAGate
from src.llm.json_utils import extract_json
from src.llm.ollama_client import OllamaClient
from src.schemas.qa_report import QAReport, QAReportOut

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class QAAgent(BaseAgent):

    def __init__(self):
        self.llm = OllamaClient()

    # =====================================================
    # EMPTY REPORT
    # =====================================================
    def _empty(self):
        return {
            "score": 0.0,
            "is_valid": False,
            "issues": [],
            "suggestions": [],
            "patch": {}
        }

    # =====================================================
    # SANITIZER
    # =====================================================
    def _sanitize(self, data: dict) -> dict:
        if not isinstance(data, dict):
            return self._empty()

        safe = self._empty()
        safe.update(data)

        safe["score"] = float(safe.get("score", 0.0))
        safe["is_valid"] = bool(safe.get("is_valid", False))

        # -------------------------
        # Issues
        # -------------------------
        cleaned_issues = []
        issues = safe.get("issues", [])

        if isinstance(issues, list):
            for issue in issues:
                # Caso 1: LLM devuelve un string
                if isinstance(issue, str):
                    cleaned_issues.append({
                        "id": "",
                        "type": "general",
                        "description": issue,
                        "severity": "warning"
                    })
                # Caso 2: LLM devuelve un objeto
                # (llama3.1 a veces usa "message" en vez de "description")
                elif isinstance(issue, dict):
                    cleaned_issues.append({
                        "id": issue.get("id", ""),
                        "type": issue.get("type", "general"),
                        "description": (
                            issue.get("description")
                            or issue.get("message", "")
                        ),
                        "severity": issue.get("severity", "warning")
                    })
        safe["issues"] = cleaned_issues

        # -------------------------
        # Suggestions
        # -------------------------
        cleaned_suggestions = []
        suggestions = safe.get("suggestions", [])

        if isinstance(suggestions, list):
            for suggestion in suggestions:
                if isinstance(suggestion, dict):
                    # normalizar "message" → "description"
                    if "description" not in suggestion and "message" in suggestion:
                        suggestion = {
                            **suggestion,
                            "description": suggestion["message"],
                        }
                    cleaned_suggestions.append(suggestion)
                else:
                    cleaned_suggestions.append({
                        "description": str(suggestion)
                    })
        safe["suggestions"] = cleaned_suggestions

        # -------------------------
        # Patch
        # -------------------------
        patch = safe.get("patch", {})
        if not isinstance(patch, dict):
            patch = {}

        # Eliminar listas vacías para evitar borrar información
        for key in list(patch.keys()):
            if isinstance(patch[key], list) and len(patch[key]) == 0:
                del patch[key]

        # Normalizar stack: el formato canónico del patch es SIEMPRE
        # una lista plana de strings (QAPatch.stack y TechDiffApplier
        # no entienden otra cosa).
        if "stack" in patch:
            stack = patch["stack"]

            # El LLM a veces devuelve {"operation": "replace", "value": [...]}
            if isinstance(stack, dict):
                stack = stack.get("value", [])

            if isinstance(stack, list):
                normalized = []
                for item in stack:
                    if isinstance(item, str):
                        if item.strip():
                            normalized.append(item)
                    elif isinstance(item, dict):
                        name = str(item.get("name", "")).strip()
                        if name:
                            normalized.append(name)

                patch["stack"] = normalized
            else:
                del patch["stack"]
        safe["patch"] = patch
        return safe

    # =====================================================
    # PROMPT
    # =====================================================
    def _build_prompt(self, product_spec: dict, tech_spec: dict) -> str:
        return f"""
Eres un Software Architecture QA Lead.

Tu misión es revisar un Tech Specification.

NO debes rediseñar el sistema.

NO debes devolver el documento completo.

Devuelve únicamente correcciones mínimas.

RESPONDE EXCLUSIVAMENTE JSON.

Formato:

{{
    "score": 0.0,
    "is_valid": false,

    "issues": [],

    "suggestions": [],

    "patch": {{}}
}}

Reglas:

- Si todo está correcto:
    score >= 0.95
    is_valid = true
    patch = {{}}

- Si encuentras problemas:
    devuelve únicamente las diferencias.

Nunca copies el documento entero.

PRODUCT SPEC:

{json.dumps(product_spec, indent=2, ensure_ascii=False)}

TECH SPEC:

{json.dumps(tech_spec, indent=2, ensure_ascii=False)}

Responde SOLO JSON.
"""

    # =====================================================
    # RUN
    # =====================================================
    def run(self, product_spec: dict, tech_spec: dict) -> QAReport:
        response = self.llm.generate(
            self._build_prompt(
                product_spec,
                tech_spec,
            ),
            schema=QAReportOut.model_json_schema(),
        )

        logger.debug("QA raw response:\n%s", response)

        try:
            data = extract_json(response)
            data = self._sanitize(data)
        except Exception as e:
            logger.warning("QA parse failed: %s", e)
            data = {
                "score": 0.0,
                "is_valid": False,
                "issues": [
                    {
                        "id": "parser",
                        "type": "parser",
                        "description": str(e),
                        "severity": "critical"
                    }
                ],
                "suggestions": [],
                "patch": {}
            }

        # =====================================================
        # HARD VALIDATION
        # =====================================================
        gate_ok, gate_issues = QAGate.validate(
            product_spec,
            tech_spec,
        )

        if not gate_ok:
            data["is_valid"] = False
            data["score"] = min(
                float(data.get("score", 0.0)),
                0.5
            )
            existing = {
                issue.get("description")
                for issue in data.get("issues", [])
                if isinstance(issue, dict)
            }

            for issue in gate_issues:
                if issue not in existing:
                    data["issues"].append({
                        "id": "qa_gate",
                        "type": "validation",
                        "description": issue,
                        "severity": "critical"
                    })

        logger.debug(
            "QA parsed data:\n%s",
            json.dumps(data, indent=2, ensure_ascii=False),
        )

        try:
            return QAReport(**data)
        except Exception as e:
            # Un patch malformado no debe tumbar el pipeline:
            # lo descartamos y conservamos score/issues.
            logger.warning("QA patch inválido, descartado: %s", e)
            data["patch"] = {}
            return QAReport(**data)