import logging

from src.llm.json_utils import extract_json
from src.llm.ollama_client import OllamaClient
from src.schemas.product_spec import ProductSpec

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ProductManagerAgent(BaseAgent):

    def __init__(self):
        self.llm = OllamaClient()
        self.max_retries = 2

    def _build_prompt(self, idea: str, error: str = "") -> str:
        return f"""
Eres un Product Manager senior especializado en diseño de productos de IA.

REGLAS ESTRICTAS:
- Devuelve SOLO JSON válido
- No uses markdown
- No incluyas explicaciones
- Debe ser coherente y minimalista (MVP real)
- Máximo 5 technical_constraints, solo si la idea las implica (si no, lista vacía)

IDEA:
{idea}

{f"ERROR PREVIO (corrígelo): {error}" if error else ""}

IMPORTANTE:
Define un MVP realista. Evita sobre-ingeniería.

FORMATO EXACTO:

{{
  "project_name": "string",
  "goal": "string",
  "target_users": ["string"],
  "main_features": ["string"],
  "mvp_scope": ["string"],
  "assumptions": ["string"],
  "technical_constraints": ["string"]
}}
"""

    def run(self, idea: str) -> ProductSpec:

        last_error = ""

        for attempt in range(self.max_retries + 1):

            logger.info(
                "PM attempt %d/%d", attempt + 1, self.max_retries + 1
            )

            response = self.llm.generate(
                self._build_prompt(idea, last_error),
                schema=ProductSpec.model_json_schema(),
            )

            logger.debug("PM raw response:\n%s", response)

            try:
                data = extract_json(response)
                return ProductSpec(**data)

            except Exception as e:
                logger.warning("PM parse error: %s", e)
                last_error = str(e)

        raise ValueError(f"Failed after retries. Last error: {last_error}")