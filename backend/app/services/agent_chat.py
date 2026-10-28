import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress
from typing import Any

from langchain_core.messages import HumanMessage

from app.agents.build import build_course_tutor_graph
from app.agents.course_tutor import create_course_tutor


Event = tuple[str, dict[str, Any]]


async def stream_agent_answer(
    question: str,
    top_k: int,
    session_id: str,
) -> AsyncIterator[Event]:
    """执行 Agent 图，并通过节点事件队列持续输出 SSE 事件。"""
    event_queue: asyncio.Queue[Event | None] = asyncio.Queue()
    graph = create_course_tutor()
    config = {
        "recursion_limit": 20,
        "configurable": {"event_queue": event_queue,
                         "thread_id": session_id
                         },
    }
    inputs = {
        "messages": [HumanMessage(content=question)],
        "question": question,
        "top_k": top_k,
    }

    async def run_graph():
        try:
            return await graph.ainvoke(inputs, config=config)
        finally:
            event_queue.put_nowait(None)

    graph_task = asyncio.create_task(run_graph())
    saw_text = False
    saw_refusal = False
    try:
        while (event := await event_queue.get()) is not None:
            if event[0] == "token":
                saw_text = True
            elif event[0] == "refusal":
                saw_refusal = True
            yield event

        await graph_task
        if not saw_text and not saw_refusal:
            raise RuntimeError("Agent 图未返回有效回答")
    finally:
        if not graph_task.done():
            graph_task.cancel()
            with suppress(asyncio.CancelledError):
                await graph_task
