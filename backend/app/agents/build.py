from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.edges import route_after_citation_check, route_after_evidence
from app.agents.nodes import (
    finalize_node,
    generate_node,
    grade_evidence_node,
    normalize_question_node,
    refuse_node,
    repair_answer_node,
    retrieve_node,
    rewrite_query_node,
    verify_citations_node,
)
from app.agents.state import CourseTutorState


def build_course_tutor_graph(*, checkpointer: Any = None):
    """构建可编排的 CoursePilot Agent 图。"""
    builder = StateGraph(CourseTutorState)

    builder.add_node("normalize_question", normalize_question_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("grade_evidence", grade_evidence_node)
    builder.add_node("rewrite_query", rewrite_query_node)
    builder.add_node("generate", generate_node)
    builder.add_node("verify_citations", verify_citations_node)
    builder.add_node("repair_answer", repair_answer_node)
    builder.add_node("refuse", refuse_node)
    builder.add_node("finalize", finalize_node)

    builder.add_edge(START, "normalize_question")
    builder.add_edge("normalize_question", "retrieve")
    builder.add_edge("retrieve", "grade_evidence")
    builder.add_conditional_edges(
        "grade_evidence",
        route_after_evidence,
        {
            "generate": "generate",
            "rewrite_query": "rewrite_query",
            "refuse": "refuse",
        },
    )

    builder.add_edge("rewrite_query", "retrieve")
    builder.add_edge("generate", "verify_citations")
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
