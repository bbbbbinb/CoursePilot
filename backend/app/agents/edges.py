from typing import Literal

from app.agents.nodes import MAX_REPAIR_ATTEMPTS, MAX_RETRIEVAL_ATTEMPTS
from app.agents.state import CourseTutorState


EvidenceRoute = Literal["generate", "rewrite_query", "refuse"]
CitationRoute = Literal["finalize", "repair_answer", "refuse"]


def route_after_evidence(state: CourseTutorState) -> EvidenceRoute:
    """证据充分时生成，否则有限次改写查询后拒答。"""
    if state.get("evidence_sufficient"):
        return "generate"

    if state.get("retrieval_attempts", 0) < MAX_RETRIEVAL_ATTEMPTS:
        return "rewrite_query"

    return "refuse"


def route_after_citation_check(state: CourseTutorState) -> CitationRoute:
    """引用正确时结束，否则修复一次，仍失败则拒答。"""
    if not state.get("citation_errors"):
        return "finalize"

    if state.get("repair_attempts", 0) < MAX_REPAIR_ATTEMPTS:
        return "repair_answer"

    return "refuse"
