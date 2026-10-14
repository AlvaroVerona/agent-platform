import re

VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


class QAGate:
    """Deterministic coherence checks. Everything returned here is a hard failure; none of it is an LLM opinion."""

    @staticmethod
    def validate(product_spec: dict, tech_spec: dict) -> tuple[bool, list[str]]:

        issues: list[str] = []

        # -------------------------
        # Existence
        # -------------------------
        components = tech_spec.get("components") or []
        api_design = tech_spec.get("api_design") or []
        stack = tech_spec.get("stack") or []

        if not api_design:
            issues.append("Missing api_design entirely")
        if not components:
            issues.append("No components defined")
        if not stack:
            issues.append("Empty stack")

        # -------------------------
        # Identity: the spec must be about the product that was asked for
        # -------------------------
        for field in ("project_name", "goal"):
            expected = (product_spec.get(field) or "").strip()
            if expected and (tech_spec.get(field) or "").strip() != expected:
                issues.append(f"{field} differs from the product spec")

        # -------------------------
        # Components
        # -------------------------
        names = [c.get("name", "").strip().lower() for c in components if isinstance(c, dict)]
        if len(names) != len(set(names)):
            issues.append("Duplicate component names")
        if any(not n for n in names):
            issues.append("Component without a name")

        stack_lower = {s.lower() for s in stack}
        for c in components:
            if not isinstance(c, dict):
                continue
            techs = c.get("technology_stack") or []
            if not techs:
                issues.append(f"Component '{c.get('name')}' declares no technology")
                continue
            missing = [t for t in techs if not any(t.lower() in s or s in t.lower() for s in stack_lower)]
            if stack_lower and missing:
                issues.append(f"Component '{c.get('name')}' uses technologies absent from the stack: {missing}")

        # -------------------------
        # Endpoints
        # -------------------------
        seen = set()
        n_endpoints = 0
        for api in api_design:
            for ep in api.get("endpoints", []):
                n_endpoints += 1
                method = str(ep.get("method", "")).upper()
                path = str(ep.get("path", ""))
                if method not in VALID_METHODS:
                    issues.append(f"Invalid HTTP method '{ep.get('method')}' on {path}")
                if not path.startswith("/") or re.search(r"\s", path):
                    issues.append(f"Invalid endpoint path '{path}'")
                if (method, path) in seen:
                    issues.append(f"Duplicate endpoint {method} {path}")
                seen.add((method, path))
        if api_design and n_endpoints == 0:
            issues.append("api_design has no endpoints")

        # -------------------------
        # Risks need an actual mitigation
        # -------------------------
        for r in tech_spec.get("risks") or []:
            if isinstance(r, dict) and not (r.get("mitigation_strategy") or "").strip():
                issues.append(f"Risk '{r.get('name')}' has no mitigation")

        return (len(issues) == 0), issues
