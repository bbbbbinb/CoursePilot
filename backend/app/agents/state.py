from typing import Annotated, Any, Literal, TypedDict
from urllib.parse import urlsplit

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field, field_validator


class SupervisorDecision(BaseModel):
    """Supervisor 的结构化路由结果。"""

    route: Literal["direct", "clarify", "refuse", "course_query"]
    resolved_query: str = Field(default="", description="独立、可检索的问题")
    reason: str | None = Field(default=None, description="路由原因")


class WebEvidence(BaseModel):
    title: str
    url: str
    snippet: str

    @field_validator("title", "snippet")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("网页证据字段不能为空")
        return value

    @field_validator("url")
    @classmethod
    def validate_http_url(cls, value: str) -> str:
        parsed = urlsplit(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("网页证据必须使用 http 或 https URL")
        return value.strip()


class WebResearchDecision(BaseModel):
    """网页研究 Agent 的最终结构化结果。"""

    status: Literal["sufficient", "insufficient"]
    evidence: list[WebEvidence] = Field(default_factory=list)
    reason: str | None = None


class CourseTutorState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]

    question: str
    resolved_query: str
    top_k: int
    route: str
    route_reason: str | None
    allow_web: bool

    context: str
    sources: list[dict[str, Any]]

    course_context: str
    course_sources: list[dict[str, Any]]
    course_status: str
    course_reason: str | None

    web_context: str
    web_evidence: list[dict[str, Any]]
    web_sources: list[dict[str, Any]]
    web_status: str
    web_reason: str | None

    evidence_sufficient: bool
    answer: str
    citation_errors: list[str]
    repair_attempts: int
    refusal_reason: str | None
