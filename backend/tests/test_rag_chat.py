import asyncio

from langchain_core.documents import Document
from langchain_core.messages import AIMessageChunk

from app.services import rag_chat
from app.services.retrieval import RetrievalHit, RetrievalResult


def make_result(*, sufficient: bool) -> RetrievalResult:
    if not sufficient:
        return RetrievalResult(
            question="明天杭州天气怎么样？",
            hits=[],
            reason="检索到的课程片段相关性不足，无法据此回答。",
        )

    document = Document(
        page_content="递归函数需要基准情形和递归关系。",
        metadata={
            "file_name": "递归讲义.md",
            "Header 1": "第一章 递归",
        },
    )
    return RetrievalResult(
        question="递归为什么需要基准情形？",
        hits=[RetrievalHit(index=1, document=document, distance=0.21)],
    )


class FakeChatModel:
    def __init__(self) -> None:
        self.messages = []

    async def astream(self, messages):
        self.messages = messages
        yield AIMessageChunk(content="递归需要基准情形 [1]。")
        yield AIMessageChunk(content="")
        yield AIMessageChunk(content=["递归关系决定如何缩小问题。 [1]"])


async def collect_events(question: str, top_k: int = 4):
    return [
        event
        async for event in rag_chat.stream_rag_answer(question, top_k)
    ]


def test_stream_rag_answer_emits_sources_then_tokens(monkeypatch) -> None:
    retrieval = make_result(sufficient=True)
    model = FakeChatModel()

    monkeypatch.setattr(
        rag_chat,
        "retrieve_documents",
        lambda question, top_k: retrieval,
    )
    monkeypatch.setattr(rag_chat, "get_chat_model", lambda: model)

    events = asyncio.run(collect_events("递归为什么需要基准情形？"))

    assert [name for name, _ in events] == ["sources", "token", "token"]
    assert events[0][1]["sources"] == retrieval.sources
    answer = "".join(
        payload["text"] for name, payload in events if name == "token"
    )
    assert answer == (
        "递归需要基准情形 [1]。"
        "递归关系决定如何缩小问题。 [1]"
    )
    assert model.messages[0].type == "system"
    assert "只能依据" in model.messages[0].content
    assert "递归函数需要基准情形和递归关系。" in model.messages[1].content
    assert "递归为什么需要基准情形？" in model.messages[1].content


def test_stream_rag_answer_refuses_without_calling_model(monkeypatch) -> None:
    retrieval = make_result(sufficient=False)

    monkeypatch.setattr(
        rag_chat,
        "retrieve_documents",
        lambda question, top_k: retrieval,
    )
    monkeypatch.setattr(
        rag_chat,
        "get_chat_model",
        lambda: (_ for _ in ()).throw(AssertionError("不应调用模型")),
    )

    events = asyncio.run(collect_events("明天杭州天气怎么样？"))

    assert [name for name, _ in events] == ["sources", "refusal"]
    assert events[0][1] == {"sources": []}
    assert events[1][1]["reason"] == retrieval.reason
