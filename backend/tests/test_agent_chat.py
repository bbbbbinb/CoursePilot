import asyncio

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, AIMessageChunk

from app.services import agent_chat
from app.services.retrieval import RetrievalHit, RetrievalResult


def make_retrieval(*, sufficient: bool) -> RetrievalResult:
    if not sufficient:
        return RetrievalResult(
            question="明天杭州天气怎么样？",
            hits=[],
            reason="检索到的课程片段相关性不足，无法据此回答。",
        )

    document = Document(
        page_content="递归函数需要基准情形和递归关系。",
        metadata={
            "chunk_id": "doc-1:0000",
            "file_name": "递归讲义.md",
            "Header 1": "第一章 递归",
        },
    )
    return RetrievalResult(
        question="递归为什么需要基准情形？",
        hits=[RetrievalHit(index=1, document=document, distance=0.2)],
    )


class FakeAgent:
    def __init__(self, mode: str) -> None:
        self.mode = mode

    async def astream(
        self,
        input_data,
        *,
        context,
        stream_mode,
        config,
    ):
        prompt = input_data["messages"][0].content
        assert "测试问题" in prompt
        assert "[1] 文件：递归讲义.md" in prompt
        assert stream_mode == "messages"
        assert config == {"recursion_limit": 8}

        yield AIMessageChunk(content=""), {}
        yield AIMessage(content="递归需要基准情形 [1]。"), {}


async def collect_events():
    return [
        event
        async for event in agent_chat.stream_agent_answer("测试问题", 4)
    ]


def test_stream_agent_answer_emits_sources_before_tokens(monkeypatch) -> None:
    monkeypatch.setattr(
        agent_chat,
        "retrieve_documents",
        lambda question, top_k: make_retrieval(sufficient=True),
    )
    monkeypatch.setattr(
        agent_chat,
        "create_course_tutor",
        lambda: FakeAgent("sufficient"),
    )

    events = asyncio.run(collect_events())

    assert [name for name, _ in events] == ["sources", "token"]
    assert events[0][1]["sources"] == [
        {
            "index": 1,
            "file_name": "递归讲义.md",
            "page": 1,
            "snippet": "递归函数需要基准情形和递归关系。",
        }
    ]
    assert events[1][1] == {"text": "递归需要基准情形 [1]。"}


def test_stream_agent_answer_refuses_when_tool_finds_no_evidence(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        agent_chat,
        "retrieve_documents",
        lambda question, top_k: make_retrieval(sufficient=False),
    )
    monkeypatch.setattr(
        agent_chat,
        "create_course_tutor",
        lambda: (_ for _ in ()).throw(AssertionError("不应创建 Agent")),
    )

    events = asyncio.run(collect_events())

    assert [name for name, _ in events] == ["sources", "refusal"]
    assert events[0][1] == {"sources": []}
    assert events[1][1] == {
        "reason": "检索到的课程片段相关性不足，无法据此回答。"
    }


def test_stream_agent_answer_answers_from_initial_retrieval_when_model_skips_tool(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        agent_chat,
        "retrieve_documents",
        lambda question, top_k: make_retrieval(sufficient=True),
    )
    monkeypatch.setattr(
        agent_chat,
        "create_course_tutor",
        lambda: FakeAgent("skipped"),
    )

    events = asyncio.run(collect_events())

    assert [name for name, _ in events] == ["sources", "token"]
    assert events[0][1]["sources"][0]["index"] == 1
    assert events[1][1] == {"text": "递归需要基准情形 [1]。"}
