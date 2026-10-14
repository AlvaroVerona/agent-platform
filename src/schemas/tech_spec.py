from pydantic import BaseModel, Field

# =====================================================
# API
# =====================================================

class APIEndpoint(BaseModel):
    method: str = "GET"
    path: str = "/"
    description: str | None = None


class APIGroup(BaseModel):
    name: str
    description: str | None = None
    endpoints: list[APIEndpoint] = Field(default_factory=list)


# =====================================================
# COMPONENTS
# =====================================================

class Component(BaseModel):
    name: str
    description: str | None = None
    technology_stack: list[str] = Field(default_factory=list)


# =====================================================
# RISKS
# =====================================================

class Risk(BaseModel):
    name: str
    description: str | None = None
    mitigation_strategy: str | None = None


# =====================================================
# TECH SPEC
# =====================================================

class TechSpec(BaseModel):

    # -----------------------------------------
    # PRODUCT IDENTITY
    # -----------------------------------------

    project_name: str = ""
    goal: str = ""

    target_users: list = Field(default_factory=list)

    main_features: list = Field(default_factory=list)

    mvp_scope: list = Field(default_factory=list)

    assumptions: list = Field(default_factory=list)

    technical_constraints: list = Field(default_factory=list)

    # -----------------------------------------
    # TECHNICAL DESIGN
    # -----------------------------------------

    architecture: dict = Field(default_factory=dict)

    stack: list[str] = Field(default_factory=list)

    components: list[Component] = Field(default_factory=list)

    api_design: list[APIGroup] = Field(default_factory=list)

    risks: list[Risk] = Field(default_factory=list)

    integrations: list[dict] = Field(default_factory=list)

    # -----------------------------------------
    # Pydantic Config
    # -----------------------------------------

    model_config = {
        "extra": "allow"
    }