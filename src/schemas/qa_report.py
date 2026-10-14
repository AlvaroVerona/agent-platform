from typing import Any, Literal

from pydantic import BaseModel, Field


class QAItem(BaseModel):
    id: str | None = None
    type: str | None = None
    description: str | None = None
    severity: str | None = None
    raw: dict | None = None


class QAPatch(BaseModel):
    architecture: dict | None = None
    stack: list[str] | None = None
    components: list[dict] | None = None
    api_design: list[dict] | None = None
    risks: list[dict] | None = None
    integrations: list[dict] | None = None


class QAReport(BaseModel):
    score: float = 0.0
    is_valid: bool = False

    issues: list[Any] = Field(default_factory=list)
    suggestions: list[Any] = Field(default_factory=list)

    patch: QAPatch | None = None

class QAIssueOut(BaseModel):
    """Shape the reviewer LLM must follow (constrains decoding via Ollama structured outputs)."""
    id: str = ""
    type: str = "general"
    description: str
    severity: Literal["info", "warning", "critical"] = "warning"


class QAReportOut(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    is_valid: bool
    issues: list[QAIssueOut] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    patch: QAPatch = Field(default_factory=QAPatch)
