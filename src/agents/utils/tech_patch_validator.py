class TechPatchValidator:

    @staticmethod
    def validate(data: dict) -> dict:
        """
        Normaliza cualquier patch o full spec del LLM
        para que sea compatible con TechSpec (Pydantic safe).
        """

        if not isinstance(data, dict):
            return {}

        data = TechPatchValidator._ensure_structure(data)

        data["stack"] = TechPatchValidator._clean_stack(data.get("stack"))
        data["components"] = TechPatchValidator._clean_components(data.get("components"))
        data["api_design"] = TechPatchValidator._clean_api_design(data.get("api_design"))
        data["risks"] = TechPatchValidator._clean_risks(data.get("risks"))
        data["integrations"] = TechPatchValidator._clean_integrations(data.get("integrations"))

        return data

    # =========================================================
    # STRUCTURE SAFETY
    # =========================================================
    @staticmethod
    def _ensure_structure(data: dict) -> dict:
        defaults = {
            "architecture": {},
            "stack": [],
            "components": [],
            "api_design": [],
            "risks": [],
            "integrations": []
        }

        for k, v in defaults.items():
            if k not in data or data[k] is None:
                data[k] = v

        return data

    # =========================================================
    # STACK FIX
    # =========================================================
    @staticmethod
    def _clean_stack(stack):
        if not isinstance(stack, list):
            return []

        clean = []

        for item in stack:
            if isinstance(item, str):
                clean.append(item)

            elif isinstance(item, dict):
                # soporta {"name": "..."} o {"technology": "..."}
                if "name" in item:
                    clean.append(item["name"])
                elif "technology" in item:
                    clean.append(item["technology"])

        return clean

    # =========================================================
    # COMPONENTS FIX
    # =========================================================
    @staticmethod
    def _clean_components(components):
        if not isinstance(components, list):
            return []

        clean = []

        for c in components:
            if not isinstance(c, dict):
                continue

            if "name" not in c:
                continue

            clean.append({
                "name": c.get("name"),
                "description": c.get("description", ""),
                "technology_stack": TechPatchValidator._clean_stack(
                    c.get("technology_stack", [])
                )
            })

        return clean

    # =========================================================
    # API DESIGN FIX (🔥 ESTE ERA TU ERROR PRINCIPAL)
    # =========================================================
    @staticmethod
    def _clean_api_design(api_design):
        if isinstance(api_design, dict):
            api_design = [api_design]

        if not isinstance(api_design, list):
            return []

        clean = []

        for api in api_design:
            if not isinstance(api, dict):
                continue

            endpoints = api.get("endpoints", [])

            # FIX: endpoints pueden venir como string → lo convertimos
            if isinstance(endpoints, str):
                endpoints = [{"method": "GET", "path": endpoints}]

            if isinstance(endpoints, dict):
                endpoints = [endpoints]

            clean_endpoints = []

            for e in endpoints:
                if isinstance(e, dict):
                    clean_endpoints.append({
                        "method": e.get("method", "GET"),
                        "path": e.get("path", "/"),
                        "description": e.get("description", "")
                    })

            clean.append({
                "name": api.get("name", "API"),
                "description": api.get("description", ""),
                "endpoints": clean_endpoints
            })

        # Un api_design vacío se queda vacío: QAGate lo rechaza en lugar de inventar un endpoint.
        return clean

    # =========================================================
    # RISKS FIX (🔥 te rompía Pydantic)
    # =========================================================
    @staticmethod
    def _clean_risks(risks):
        if not isinstance(risks, list):
            return []

        clean = []

        for r in risks:
            if isinstance(r, str):
                clean.append({
                    "name": r,
                    "description": r,
                    "mitigation_strategy": ""
                })

            elif isinstance(r, dict):
                clean.append({
                    "name": r.get("name") or r.get("risk_name") or "Unknown risk",
                    "description": r.get("description", ""),
                    "mitigation_strategy": r.get("mitigation_strategy", "")
                })

        return clean

    # =========================================================
    # INTEGRATIONS FIX
    # =========================================================
    @staticmethod
    def _clean_integrations(integrations):
        if not isinstance(integrations, list):
            return []

        clean = []

        for i in integrations:
            if isinstance(i, str):
                clean.append({
                    "name": i,
                    "description": i,
                    "technology_stack": []
                })

            elif isinstance(i, dict):
                clean.append({
                    "name": i.get("name", "integration"),
                    "description": i.get("description", ""),
                    "technology_stack": i.get("technology_stack", [])
                })

        return clean
        