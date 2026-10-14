from pydantic import BaseModel


class ProductSpec(BaseModel):
    project_name: str
    goal: str

    target_users: list[str]

    main_features: list[str]

    mvp_scope: list[str]

    assumptions: list[str]

    technical_constraints: list[str]