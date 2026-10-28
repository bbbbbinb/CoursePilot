from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class CourseTutorState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]

    question: str
    rewritten_question: str
    top_k: int

    context: str
    sources: list[dict[str, Any]]

    retrieval_attempts: int
    evidence_sufficient: bool
    refusal_reason: str | None

    answer: str
    citation_errors: list[str]
    repair_attempts: int