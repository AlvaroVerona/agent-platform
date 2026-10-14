import json
import re
from typing import Any


def extract_json(text: str) -> dict[str, Any]:
    """
    Extrae el primer objeto JSON de una respuesta de LLM.

    Tolera:
    - fences de markdown (```json ... ```)
    - texto antes/después del JSON
    - trailing commas
    """

    if not text or not isinstance(text, str):
        raise ValueError("Empty LLM response")

    cleaned = (
        text.replace("```json", "")
            .replace("```", "")
            .strip()
    )

    start = cleaned.find("{")

    if start == -1:
        raise ValueError(f"No JSON found in response:\n{cleaned}")

    # Balanceo de llaves para encontrar el cierre real
    depth = 0
    end = None

    for i in range(start, len(cleaned)):

        if cleaned[i] == "{":
            depth += 1

        elif cleaned[i] == "}":
            depth -= 1

            if depth == 0:
                end = i
                break

    if end is None:
        raise ValueError(f"Incomplete or malformed JSON:\n{cleaned}")

    json_str = cleaned[start:end + 1]

    # Errores comunes de LLM
    json_str = re.sub(r",\s*}", "}", json_str)   # trailing commas
    json_str = re.sub(r",\s*]", "]", json_str)

    try:
        return json.loads(json_str)

    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON extracted from LLM:\n{json_str}"
        ) from e
