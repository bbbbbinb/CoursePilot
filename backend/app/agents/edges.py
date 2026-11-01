from typing import Literal

from app.agents.state import CourseTutorState


SupervisorRoute = Literal["direct", "clarify", "refuse", "retrieve_course"]
CourseRoute = Literal["merge_evidence", "web_research", "refuse"]
WebRoute = Literal["merge_evidence", "refuse"]
MergeRoute = Literal["answer", "refuse"]
CitationRoute = Literal["finalize", "repair_answer", "refuse"]


def route_after_supervisor(state: CourseTutorState) -> SupervisorRoute:
    if state.get("route") == "course_query":
        return "retrieve_course"
    if state.get("route") in {"direct", "clarify", "refuse"}:
        return state["route"]
    return "refuse"


def route_after_course_evidence(state: CourseTutorState) -> CourseRoute:
    if state.get("evidence_sufficient"):
        return "merge_evidence"
    if state.get("allow_web"):
        return "web_research"
    return "refuse"


def route_after_web_research(state: CourseTutorState) -> WebRoute:
    if state.get("web_status") == "sufficient" and state.get("web_evidence"):
        return "merge_evidence"
    return "refuse"


def route_after_merge(state: CourseTutorState) -> MergeRoute:
    return "answer" if state.get("evidence_sufficient") else "refuse"


def route_after_citation_check(state: CourseTutorState) -> CitationRoute:
    if not state.get("citation_errors"):
        return "finalize"
    if state.get("repair_attempts", 0) < 1:
        return "repair_answer"
    return "refuse"
