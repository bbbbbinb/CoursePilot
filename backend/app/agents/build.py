from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.edges import (
    route_after_citation_check,
    route_after_course_evidence,
    route_after_merge,
    route_after_supervisor,
    route_after_web_research,
)
from app.agents.nodes import (
    answer_agent_node,
    clarify_node,
    course_evidence_gate,
    direct_answer_node,
    finalize_node,
    merge_evidence_node,
    prepare_turn_node,
    refusal_node,
    repair_answer_node,
    retrieve_course_node,
    supervisor_node,
    verify_citations_node,
    web_research_agent_node,
)
from app.agents.state import CourseTutorState


def build_course_tutor_graph(*, checkpointer: Any = None):
    """构建 Supervisor 编排的课程 Agent 图。"""
    builder = StateGraph(CourseTutorState)

    builder.add_node("prepare_turn", prepare_turn_node)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("direct_answer", direct_answer_node)
    builder.add_node("clarify", clarify_node)
    builder.add_node("retrieve_course", retrieve_course_node)
    builder.add_node("course_evidence_gate", course_evidence_gate)
    builder.add_node("web_research", web_research_agent_node)
    builder.add_node("merge_evidence", merge_evidence_node)
    builder.add_node("answer", answer_agent_node)
    builder.add_node("verify_citations", verify_citations_node)
    builder.add_node("repair_answer", repair_answer_node)
    builder.add_node("refuse", refusal_node)
    builder.add_node("finalize", finalize_node)

    builder.add_edge(START, "prepare_turn")
    builder.add_edge("prepare_turn", "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "direct": "direct_answer",
            "clarify": "clarify",
            "refuse": "refuse",
            "retrieve_course": "retrieve_course",
        },
    )

    builder.add_edge("direct_answer", "finalize")
    builder.add_edge("clarify", "finalize")
    builder.add_edge("retrieve_course", "course_evidence_gate")
    builder.add_conditional_edges(
        "course_evidence_gate",
        route_after_course_evidence,
        {
            "merge_evidence": "merge_evidence",
            "web_research": "web_research",
            "refuse": "refuse",
        },
    )
    builder.add_conditional_edges(
        "web_research",
        route_after_web_research,
        {
            "merge_evidence": "merge_evidence",
            "refuse": "refuse",
        },
    )
    builder.add_conditional_edges(
        "merge_evidence",
        route_after_merge,
        {
            "answer": "answer",
            "refuse": "refuse",
        },
    )

    builder.add_edge("answer", "verify_citations")
    builder.add_conditional_edges(
        "verify_citations",
        route_after_citation_check,
        {
            "finalize": "finalize",
            "repair_answer": "repair_answer",
            "refuse": "refuse",
        },
    )
    builder.add_edge("repair_answer", "verify_citations")
    builder.add_edge("refuse", "finalize")
    builder.add_edge("finalize", END)

    return builder.compile(checkpointer=checkpointer)
