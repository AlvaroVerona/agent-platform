from typing import Any

from src.llm.json_utils import extract_json


class TechSpecParser:

    @staticmethod
    def extract_json(text: str) -> dict[str, Any]:
        return extract_json(text)

    # =====================================================
    # OPTIONAL SANITIZER (SI LO USAS EN TECH ARCHITECT)
    # =====================================================
    @staticmethod
    def sanitize(data: dict[str, Any]) -> dict[str, Any]:

        if not isinstance(data, dict):
            return {}

        # defaults seguros
        data.setdefault("architecture", {})
        data.setdefault("stack", [])
        data.setdefault("components", [])
        data.setdefault("api_design", [])
        data.setdefault("risks", [])
        data.setdefault("integrations", [])

        # ==========================
        # NORMALIZE LIST TYPES
        # ==========================
        for key in ["stack", "components", "api_design", "risks", "integrations"]:
            if key in data and not isinstance(data[key], list):
                data[key] = [data[key]]

        return data