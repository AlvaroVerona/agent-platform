import copy
import logging

from src.agents.utils.tech_patch_validator import TechPatchValidator
from src.agents.utils.tech_spec_hard_validator import TechSpecHardValidator
from src.agents.utils.tech_spec_parser import TechSpecParser
from src.llm.ollama_client import OllamaClient
from src.schemas.tech_spec import TechSpec

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class TechSpecError(Exception):
    """The architect could not produce a valid spec; the run must fail visibly."""


class TechArchitectAgent(BaseAgent):

    def __init__(self):
        self.llm = OllamaClient()
        self.fallback_count = 0  # kept for the eval harness; now always 0 (failures raise)
        self.max_retries = 1

    # =====================================================
    # PROMPT
    # =====================================================

    def _build_prompt(
        self,
        product_spec: dict,
        context: dict | None = None,
    ) -> str:

        return f"""
Eres un Arquitecto de Software Senior.

REGLAS OBLIGATORIAS:

- Devuelve SOLO JSON válido.
- No markdown.
- No explicaciones.
- No comentarios.
- Todos los campos deben existir.

El objetivo NO es diseñar un sistema perfecto.
El objetivo es diseñar un MVP técnicamente consistente.

STACK

- Respeta las technical_constraints del producto si las hay.
- Si no hay restricciones, elige el stack mínimo adecuado para el MVP y justifica la elección en "assumptions".
- "stack" es una lista de nombres de tecnología sin etiquetas (por ejemplo "Python", "Flask", "PostgreSQL").
- Todos los componentes deben usar únicamente tecnologías presentes en "stack".

PRODUCT:

{product_spec}

PREVIOUS VERSION / QA FEEDBACK:

{context or {}}

IMPORTANTE:

Si CONTEXT está vacío,
genera una especificación técnica desde cero.

Si CONTEXT contiene una especificación previa o un patch generado por QA:

- conserva todo lo que ya sea correcto;
- modifica únicamente los elementos necesarios;
- NO elimines componentes existentes;
- NO reduzcas funcionalidades;
- mejora únicamente los puntos señalados por QA;
- mantén la consistencia de toda la arquitectura.

RESPONDE EXACTAMENTE CON ESTE FORMATO:

{{
  "project_name": "",
  "goal": "",

  "target_users": [],

  "main_features": [],

  "mvp_scope": [],

  "assumptions": [],

  "technical_constraints": [],

  "architecture": {{
      "description": "",
      "type": "microservices",
      "services": []
  }},

  "stack": [],

  "components": [
      {{
          "name": "",
          "description": "",
          "technology_stack": []
      }}
  ],

  "api_design": [
      {{
          "name": "",
          "description": "",
          "endpoints": [
              {{
                  "method": "",
                  "path": "",
                  "description": ""
              }}
          ]
      }}
  ],

  "risks": [
      {{
          "name": "",
          "description": "",
          "mitigation_strategy": ""
      }}
  ],

  "integrations": []
}}
"""

    # =====================================================
    # BASE SPEC
    # =====================================================

    def _base_spec(self):

        return {
            "project_name": "",
            "goal": "",
            "target_users": [],
            "main_features": [],
            "mvp_scope": [],
            "assumptions": [],
            "technical_constraints": [],

            "architecture": {
                "description": "",
                "type": "",
                "services": []
            },

            "stack": [],

            "components": [],

            "api_design": [],

            "risks": [],

            "integrations": []
        }

    # =====================================================
    # MERGE
    # =====================================================

    def _deep_merge(
        self,
        base: dict,
        update: dict,
    ) -> dict:

        for key, value in update.items():

            if (
                isinstance(value, dict)
                and isinstance(base.get(key), dict)
            ):

                base[key] = self._deep_merge(
                    base[key],
                    value,
                )

            else:

                base[key] = value

        return base

    # =====================================================
    # RUN
    # =====================================================

    def run(
        self,
        product_spec: dict,
        context: dict | None = None,
    ) -> TechSpec:

        base = self._base_spec()

        base.update({

            "project_name": product_spec.get("project_name", ""),
            "goal": product_spec.get("goal", ""),
            "target_users": product_spec.get("target_users", []),
            "main_features": product_spec.get("main_features", []),
            "mvp_scope": product_spec.get("mvp_scope", []),
            "assumptions": product_spec.get("assumptions", []),
            "technical_constraints": product_spec.get(
                "technical_constraints",
                [],
            ),
        })

        prompt = self._build_prompt(
            product_spec,
            context,
        )

        last_error = ""

        for attempt in range(self.max_retries + 1):

            retry_hint = (
                f"\n\nERROR PREVIO (corrígelo): {last_error}" if last_error else ""
            )

            response = self.llm.generate(
                prompt + retry_hint,
                schema=TechSpec.model_json_schema(),
            )

            logger.debug("Tech raw response:\n%s", response)

            try:

                parsed = TechSpecParser.extract_json(response)
                parsed = TechSpecParser.sanitize(parsed)
                parsed = TechPatchValidator.validate(parsed)

                merged = self._deep_merge(copy.deepcopy(base), parsed)
                merged = TechSpecHardValidator.validate(merged)

                return TechSpec(**merged)

            except Exception as e:

                logger.warning(
                    "Tech attempt %d/%d failed: %s",
                    attempt + 1, self.max_retries + 1, e,
                )
                last_error = str(e)[:300]

        raise TechSpecError(
            f"Tech Architect failed after retries: {last_error}"
        )
