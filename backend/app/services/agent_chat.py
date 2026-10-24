import asyncio
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage

from app.agents.course_tutor import CourseTutorContext, create_course_tutor
from app.services.retrieval import retrieve_documents


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""

    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict) and isinstance(item.get("text"), str):
            parts.append(item["text"])
    return "".join(parts)


async def stream_agent_answer(
    question: str,
    top_k: int,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """执行课程 Agent，并把消息流转换为 sources/token/refusal 事件。"""
    retrieval = await asyncio.to_thread(
        retrieve_documents,
        question,
        top_k=top_k,
    )
    context = CourseTutorContext(top_k=top_k)

    if not retrieval.is_sufficient:
        yield "sources", {"sources": []}
        yield "refusal", {
            "reason": retrieval.reason or "课程资料不足以回答该问题。"
        }
        return

    initial_context = context.register_retrieval(retrieval)
    agent = create_course_tutor()
    sources_sent = False
    has_text = False

    async for item in agent.astream(
        {
            "messages": [
                HumanMessage(
                    content=(
                        "以下是初始检索到的课程片段：\n\n"
                        f"{initial_context}\n\n"
                        f"用户问题：\n{question}"
                    )
                )
            ]
        },
        context=context,
        stream_mode="messages",
        config={"recursion_limit": 8},
    ):
        if not isinstance(item, tuple) or len(item) != 2:
            continue

        chunk, _metadata = item
        if not isinstance(chunk, (AIMessage, AIMessageChunk)):
            continue

        text = _content_to_text(chunk.content)
        if not text:
            continue

        if not sources_sent:
            if not context.source_list:
                yield "sources", {"sources": []}
                yield "refusal", {"reason": context.refusal_reason}
                return

            yield "sources", {"sources": context.source_list}
            sources_sent = True

        has_text = True
        yield "token", {"text": text}

    if not sources_sent:
        yield "sources", {"sources": []}
        yield "refusal", {"reason": context.refusal_reason}
        return

    if not has_text:
        raise RuntimeError("Agent 未返回有效文本")
