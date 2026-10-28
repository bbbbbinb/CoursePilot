import asyncio

from app.services import agent_chat


SOURCE = {
    "index": 1,
    "file_name": "递归讲义.md",
    "page": 1,
    "snippet": "递归函数需要基准情形和递归关系。",
}


class FakeGraph:
    def __init__(self, *, sufficient: bool, invalid_citation: bool = False) -> None:
        self.sufficient = sufficient
        self.invalid_citation = invalid_citation

    async def ainvoke(self, input_data, *, config):
        assert input_data["question"] == "测试问题"
        assert input_data["top_k"] == 4
        assert config["recursion_limit"] == 20
        queue = config["configurable"]["event_queue"]

        if not self.sufficient:
            queue.put_nowait(("sources", {"sources": []}))
            queue.put_nowait(
                (
                    "refusal",
                    {"reason": "检索到的课程片段相关性不足，无法据此回答。"},
                )
            )
            return {"answer": "检索到的课程片段相关性不足，无法据此回答。"}

        queue.put_nowait(("sources", {"sources": [SOURCE]}))
        answer = (
            "递归需要基准情形 [9]。"
            if self.invalid_citation
            else "递归需要基准情形 [1]。"
        )
        queue.put_nowait(("token", {"text": answer}))

        if self.invalid_citation:
            queue.put_nowait(("replace", {"text": "递归需要基准情形。"}))
            queue.put_nowait(
                ("refusal", {"reason": "课程资料不足以回答该问题。"})
            )

        return {"answer": answer}


async def collect_events():
    return [
        event
        async for event in agent_chat.stream_agent_answer("测试问题", 4)
    ]


def test_stream_agent_answer_emits_sources_before_tokens(monkeypatch) -> None:
    monkeypatch.setattr(
        agent_chat,
        "build_course_tutor_graph",
        lambda: FakeGraph(sufficient=True),
    )

    events = asyncio.run(collect_events())

    assert [name for name, _ in events] == ["sources", "token"]
    assert events[0][1]["sources"] == [SOURCE]
    assert events[1][1] == {"text": "递归需要基准情形 [1]。"}


def test_stream_agent_answer_refuses_when_evidence_is_insufficient(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        agent_chat,
        "build_course_tutor_graph",
        lambda: FakeGraph(sufficient=False),
    )

    events = asyncio.run(collect_events())

    assert [name for name, _ in events] == ["sources", "refusal"]
    assert events[0][1] == {"sources": []}
    assert events[1][1] == {
        "reason": "检索到的课程片段相关性不足，无法据此回答。"
    }


def test_stream_agent_answer_replaces_invalid_citation_output(monkeypatch) -> None:
    monkeypatch.setattr(
        agent_chat,
        "build_course_tutor_graph",
        lambda: FakeGraph(sufficient=True, invalid_citation=True),
    )

    events = asyncio.run(collect_events())

    assert [name for name, _ in events] == [
        "sources",
        "token",
        "replace",
        "refusal",
    ]
    assert events[2][1] == {"text": "递归需要基准情形。"}
