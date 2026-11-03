import asyncio
from typing import Any

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agents import nodes
from app.agents.build import build_course_tutor_graph
from app.agents.edges import (
    route_after_citation_check,
    route_after_course_evidence,
    route_after_merge,
    route_after_supervisor,
    route_after_web_research,
)
from app.agents.state import (
    SupervisorDecision,
    WebEvidence,
    WebResearchDecision,
)
from app.core.config import Settings
from app.services.retrieval import RetrievalHit, RetrievalResult


def make_retrieval(*, sufficient: bool) -> RetrievalResult:
    if not sufficient:
        return RetrievalResult(
            question="测试问题",
            hits=[],
            reason="企业资料不足以回答该问题。",
        )

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


class FakeStructuredModel:
    def __init__(self, decision: SupervisorDecision, calls: list[list[Any]]) -> None:
        self.decision = decision
        self.calls = calls

    async def ainvoke(self, messages: list[Any]) -> SupervisorDecision:
        self.calls.append(messages)
        return self.decision


class FakeChatModel:
    def __init__(
        self,
        decision: SupervisorDecision,
        answer: str,
    ) -> None:
        self.decision = decision
        self.answer = answer
        self.structured_calls: list[list[Any]] = []
        self.answer_calls: list[list[Any]] = []

    def with_structured_output(self, schema):
        return FakeStructuredModel(self.decision, self.structured_calls)

    async def astream(self, messages: list[Any]):
        self.answer_calls.append(messages)
        middle = max(1, len(self.answer) // 2)
        yield AIMessageChunk(content=self.answer[:middle])
        yield AIMessageChunk(content=self.answer[middle:])


class FakeWebAgent:
    def __init__(self, decision: WebResearchDecision) -> None:
        self.decision = decision

    async def ainvoke(self, input_data, *, config):
        return {"structured_response": self.decision}


def test_route_helpers() -> None:
    assert route_after_supervisor({"route": "course_query"}) == "retrieve_course"
    assert route_after_supervisor({"route": "direct"}) == "direct"
    assert (
        route_after_course_evidence(
            {"evidence_sufficient": False, "allow_web": True}
        )
        == "web_research"
    )
    assert (
        route_after_course_evidence(
            {"evidence_sufficient": False, "allow_web": False}
        )
        == "refuse"
    )
    assert (
        route_after_web_research(
            {"web_status": "sufficient", "web_evidence": [{"url": "x"}]}
        )
        == "merge_evidence"
    )
    assert route_after_merge({"evidence_sufficient": True}) == "answer"
    assert (
        route_after_citation_check(
            {"citation_errors": ["bad"], "repair_attempts": 0}
        )
        == "repair_answer"
    )


def test_direct_route_does_not_retrieve(monkeypatch) -> None:
    model = FakeChatModel(
        SupervisorDecision(route="direct", resolved_query="你好"),
        "你好，我是知衡。",
    )
    monkeypatch.setattr(nodes, "get_chat_model", lambda: model)
    monkeypatch.setattr(
        nodes,
        "retrieve_documents",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("direct 不应检索")
        ),
    )

    graph = build_course_tutor_graph()
    result = asyncio.run(
        graph.ainvoke(
            {
                "messages": [HumanMessage(content="你好")],
                "question": "你好",
                "top_k": 4,
                "allow_web": False,
            }
        )
    )

    assert result["answer"] == "你好，我是知衡。"
    assert isinstance(result["messages"][-1], AIMessage)
    assert result["messages"][-1].content == "你好，我是知衡。"
    assert "知衡" in model.answer_calls[0][0].content
    assert "不得自称 CoursePilot" in model.answer_calls[0][0].content


def test_clarify_route_streams_question_without_retrieval(monkeypatch) -> None:
    model = FakeChatModel(
        SupervisorDecision(
            route="clarify",
            resolved_query="删除什么？",
            reason="缺少删除对象",
        ),
        "你是在问二叉搜索树删除，还是链表删除？",
    )
    monkeypatch.setattr(nodes, "get_chat_model", lambda: model)
    monkeypatch.setattr(
        nodes,
        "retrieve_documents",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("clarify 不应检索")
        ),
    )

    queue = asyncio.Queue()
    graph = build_course_tutor_graph()
    result = asyncio.run(
        graph.ainvoke(
            {
                "messages": [HumanMessage(content="那删除呢？")],
                "question": "那删除呢？",
                "top_k": 4,
                "allow_web": False,
            },
            config={"configurable": {"event_queue": queue}},
        )
    )

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    assert [name for name, _ in events] == [
        "status",
        "status",
        "token",
        "token",
    ]
    assert result["answer"] == "你是在问二叉搜索树删除，还是链表删除？"


def test_course_route_uses_deterministic_retrieval(monkeypatch) -> None:
    model = FakeChatModel(
        SupervisorDecision(
            route="course_query",
            resolved_query="递归为什么需要基准情形？",
        ),
        "递归需要基准情形 [1]。",
    )
    calls: list[str] = []

    def retrieve(question: str, top_k: int) -> RetrievalResult:
        calls.append(question)
        return make_retrieval(sufficient=True)

    monkeypatch.setattr(nodes, "get_chat_model", lambda: model)
    monkeypatch.setattr(nodes, "retrieve_documents", retrieve)

    queue = asyncio.Queue()
    graph = build_course_tutor_graph()
    result = asyncio.run(
        graph.ainvoke(
            {
                "messages": [HumanMessage(content="测试问题")],
                "question": "测试问题",
                "top_k": 4,
                "allow_web": False,
            },
            config={"configurable": {"event_queue": queue}},
        )
    )

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    assert calls == ["递归为什么需要基准情形？"]
    assert result["sources"][0]["source_type"] == "course"
    assert result["answer"] == "递归需要基准情形 [1]。"
    assert [name for name, _ in events].count("sources") == 1


def test_insufficient_course_evidence_refuses_without_web(monkeypatch) -> None:
    model = FakeChatModel(
        SupervisorDecision(route="course_query", resolved_query="测试问题"),
        "不应生成",
    )
    monkeypatch.setattr(nodes, "get_chat_model", lambda: model)
    monkeypatch.setattr(
        nodes,
        "retrieve_documents",
        lambda question, top_k: make_retrieval(sufficient=False),
    )

    graph = build_course_tutor_graph()
    result = asyncio.run(
        graph.ainvoke(
            {
                "messages": [HumanMessage(content="测试问题")],
                "question": "测试问题",
                "top_k": 4,
                "allow_web": False,
            }
        )
    )

    assert result["answer"] == "企业资料不足以回答该问题。"
    assert model.answer_calls == []


def test_web_agent_result_is_merged_into_answer(monkeypatch) -> None:
    model = FakeChatModel(
        SupervisorDecision(route="course_query", resolved_query="测试问题"),
        "网页资料说明这是外部定义 [1]。",
    )
    decision = WebResearchDecision(
        status="sufficient",
        evidence=[
            WebEvidence(
                title="递归定义",
                url="https://example.com/recursion",
                snippet="递归通过自身调用分解问题。",
            )
        ],
    )

    monkeypatch.setattr(nodes, "get_chat_model", lambda: model)
    monkeypatch.setattr(
        nodes,
        "retrieve_documents",
        lambda question, top_k: make_retrieval(sufficient=False),
    )

    async def load_tools():
        return [object()]

    monkeypatch.setattr(nodes, "_load_web_tools", load_tools)
    monkeypatch.setattr(nodes, "create_agent", lambda **kwargs: FakeWebAgent(decision))

    graph = build_course_tutor_graph()
    result = asyncio.run(
        graph.ainvoke(
            {
                "messages": [HumanMessage(content="测试问题")],
                "question": "测试问题",
                "top_k": 4,
                "allow_web": True,
            }
        )
    )

    assert result["sources"] == [
        {
            "index": 1,
            "source_type": "web",
            "file_name": "递归定义",
            "title": "递归定义",
            "url": "https://example.com/recursion",
            "page": 1,
            "snippet": "递归通过自身调用分解问题。",
        }
    ]
    assert result["answer"] == "网页资料说明这是外部定义 [1]。"


def test_graph_repairs_invalid_citation_before_finalizing(monkeypatch) -> None:
    model = FakeChatModel(
        SupervisorDecision(route="course_query", resolved_query="测试问题"),
        "递归需要基准情形 [1][9]。",
    )
    monkeypatch.setattr(nodes, "get_chat_model", lambda: model)
    monkeypatch.setattr(
        nodes,
        "retrieve_documents",
        lambda question, top_k: make_retrieval(sufficient=True),
    )

    graph = build_course_tutor_graph()
    result = asyncio.run(
        graph.ainvoke(
            {
                "messages": [HumanMessage(content="测试问题")],
                "question": "测试问题",
                "top_k": 4,
                "allow_web": False,
            }
        )
    )

    assert result["answer"] == "递归需要基准情形 [1]。"
    assert result["citation_errors"] == []
    assert result["repair_attempts"] == 1


def test_sqlite_checkpointer_restores_message_history(
    monkeypatch,
    tmp_path,
) -> None:
    model = FakeChatModel(
        SupervisorDecision(route="direct", resolved_query="你好"),
        "你好，我是知衡。",
    )
    monkeypatch.setattr(nodes, "get_chat_model", lambda: model)

    config = {"configurable": {"thread_id": "session-1"}}

    async def run() -> None:
        async with AsyncSqliteSaver.from_conn_string(
            str(tmp_path / "session.sqlite")
        ) as checkpointer:
            await checkpointer.setup()
            graph = build_course_tutor_graph(checkpointer=checkpointer)

            await graph.ainvoke(
                {
                    "messages": [HumanMessage(content="你好")],
                    "question": "你好",
                    "top_k": 4,
                    "allow_web": False,
                },
                config=config,
            )
            await graph.ainvoke(
                {
                    "messages": [HumanMessage(content="谢谢")],
                    "question": "谢谢",
                    "top_k": 4,
                    "allow_web": False,
                },
                config=config,
            )

    asyncio.run(run())

    second_structured_prompt = model.structured_calls[-1][1].content
    assert "你好" in second_structured_prompt
    assert "你好，我是知衡。" in second_structured_prompt


def test_empty_mcp_config_is_treated_as_disabled() -> None:
    settings = Settings(
        _env_file=None,
        web_search_mcp_config="",
    )
    assert settings.web_search_mcp_config is None
