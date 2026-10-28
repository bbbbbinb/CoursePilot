import asyncio
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage

from app.agents import nodes
from app.agents.build import build_course_tutor_graph
from app.agents.edges import route_after_citation_check, route_after_evidence
from app.services.retrieval import RetrievalHit, RetrievalResult


def make_retrieval(*, sufficient: bool) -> RetrievalResult:
    if not sufficient:
        return RetrievalResult(
            question="测试问题",
            hits=[],
            reason="课程资料不足以回答该问题。",
        )

    from langchain_core.documents import Document

    document = Document(
        page_content="递归函数需要基准情形。",
        metadata={
            "chunk_id": "doc-1:0000",
            "file_name": "递归讲义.md",
            "Header 1": "第一章 递归",
        },
    )
    return RetrievalResult(
        question="测试问题",
        hits=[RetrievalHit(index=1, document=document, distance=0.2)],
    )


class FakeChatModel:
    def __init__(self, text: str) -> None:
        self.text = text

    async def ainvoke(self, messages: list[Any]) -> AIMessage:
        return AIMessage(content="递归 基准情形")

    async def astream(self, messages: list[Any]):
        yield AIMessageChunk(content=self.text)


def test_edge_routes_stop_after_retry_and_repair_limits() -> None:
    assert route_after_evidence({"evidence_sufficient": True}) == "generate"
    assert (
        route_after_evidence(
            {"evidence_sufficient": False, "retrieval_attempts": 1}
        )
        == "rewrite_query"
    )
    assert (
        route_after_evidence(
            {"evidence_sufficient": False, "retrieval_attempts": 2}
        )
        == "refuse"
    )

    assert route_after_citation_check({"citation_errors": []}) == "finalize"
    assert (
        route_after_citation_check(
            {"citation_errors": ["bad"], "repair_attempts": 0}
        )
        == "repair_answer"
    )
    assert (
        route_after_citation_check(
            {"citation_errors": ["bad"], "repair_attempts": 1}
        )
        == "refuse"
    )


def test_graph_generates_answer_with_valid_sources(monkeypatch) -> None:
    monkeypatch.setattr(
        nodes,
        "retrieve_documents",
        lambda question, top_k: make_retrieval(sufficient=True),
    )
    monkeypatch.setattr(
        nodes,
        "get_chat_model",
        lambda: FakeChatModel("递归需要基准情形 [1]。"),
    )

    graph = build_course_tutor_graph()
    result = asyncio.run(
        graph.ainvoke(
            {
                "messages": [HumanMessage(content="测试问题")],
                "question": "测试问题",
                "top_k": 4,
            }
        )
    )

    assert result["answer"] == "递归需要基准情形 [1]。"
    assert result["sources"][0]["index"] == 1
    assert result["messages"][-1] == AIMessage(
        content="递归需要基准情形 [1]。"
    )


def test_graph_refuses_after_retrieval_rewrite_fails(monkeypatch) -> None:
    calls: list[str] = []

    def retrieve(question: str, top_k: int) -> RetrievalResult:
        calls.append(question)
        return make_retrieval(sufficient=False)

    monkeypatch.setattr(nodes, "retrieve_documents", retrieve)
    monkeypatch.setattr(nodes, "get_chat_model", lambda: FakeChatModel(""))

    graph = build_course_tutor_graph()
    result = asyncio.run(
        graph.ainvoke(
            {
                "messages": [HumanMessage(content="测试问题")],
                "question": "测试问题",
                "top_k": 4,
            }
        )
    )

    assert calls == ["测试问题", "递归 基准情形"]
    assert result["answer"] == "课程资料不足以回答该问题。"
    assert result["evidence_sufficient"] is False


def test_graph_repairs_invalid_citation_before_finalizing(monkeypatch) -> None:
    monkeypatch.setattr(
        nodes,
        "retrieve_documents",
        lambda question, top_k: make_retrieval(sufficient=True),
    )
    monkeypatch.setattr(
        nodes,
        "get_chat_model",
        lambda: FakeChatModel("递归需要基准情形 [1][9]。"),
    )

    graph = build_course_tutor_graph()
    result = asyncio.run(
        graph.ainvoke(
            {
                "messages": [HumanMessage(content="测试问题")],
                "question": "测试问题",
                "top_k": 4,
            }
        )
    )

    assert result["answer"] == "递归需要基准情形 [1]。"
    assert result["repair_attempts"] == 1
    assert result["citation_errors"] == []
