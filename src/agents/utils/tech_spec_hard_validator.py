class TechSpecHardValidator:

    REQUIRED_TOP_LEVEL = [
        "architecture",
        "stack",
        "components",
        "api_design",
        "risks",
        "integrations"
    ]

    @staticmethod
    def validate(spec: dict) -> dict:

        if not isinstance(spec, dict):
            return {}

        # ----------------------------
        # 1. ENSURE REQUIRED FIELDS
        # ----------------------------
        for field in TechSpecHardValidator.REQUIRED_TOP_LEVEL:
            spec.setdefault(field, [])

        # ----------------------------
        # 2. API DESIGN FIX
        # ----------------------------
        fixed_api = []

        for api in spec.get("api_design", []):
            if not isinstance(api, dict):
                continue

            api.setdefault("name", "Base API")
            api.setdefault("description", "")
            api.setdefault("endpoints", [])

            # Un grupo sin endpoints se descarta (no se inventa un /health)
            if not api["endpoints"]:
                continue

            fixed_api.append(api)

        spec["api_design"] = fixed_api

        # ----------------------------
        # 3. COMPONENTS FIX
        # ----------------------------
        fixed_components = []

        for c in spec.get("components", []):
            if not isinstance(c, dict):
                continue

            c.setdefault("name", "Service")
            c.setdefault("description", "")
            c.setdefault("technology_stack", [])

            fixed_components.append(c)

        spec["components"] = fixed_components

        # ----------------------------
        # 4. RISKS FIX
        # ----------------------------
        fixed_risks = []

        for r in spec.get("risks", []):
            if not isinstance(r, dict):
                continue

            r.setdefault("name", "Unknown risk")
            r.setdefault("description", "")
            r.setdefault("mitigation_strategy", "TBD")

            fixed_risks.append(r)

        spec["risks"] = fixed_risks

        # ----------------------------
        # 5. INTEGRATIONS FIX
        # ----------------------------
        fixed_integrations = []

        for i in spec.get("integrations", []):
            if not isinstance(i, dict):
                continue

            i.setdefault("name", "Integration")
            i.setdefault("description", "")
            i.setdefault("technology_stack", [])

            fixed_integrations.append(i)

        spec["integrations"] = fixed_integrations

        return spec