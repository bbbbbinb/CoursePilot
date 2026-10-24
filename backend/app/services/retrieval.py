from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

from app.core.config import get_settings
from app.services.RAG_services import get_vector_store


@dataclass(frozen=True)
class RetrievalHit:
    """一条通过相关性过滤的检索结果。"""

    index: int
    document: Document
    distance: float


@dataclass(frozen=True)
class RetrievalResult:
    """一次检索的结构化结果，供 RAG 回答和拒答逻辑使用。"""

    question: str
    hits: list[RetrievalHit]
    reason: str | None = None

    @property
    def is_sufficient(self) -> bool:
        return bool(self.hits)

    @property
    def documents(self) -> list[Document]:
        return [hit.document for hit in self.hits]

    @property
    def sources(self) -> list[dict[str, Any]]:
        return build_sources(self.documents)

    @property
    def context(self) -> str:
        """生成带稳定编号的课程上下文。"""
        blocks: list[str] = []

        for hit in self.hits:
            metadata = hit.document.metadata
            heading = _heading(metadata)
            header = f"[{hit.index}] 文件：{_file_name(metadata)}"
            if heading:
                header += f"；章节：{heading}"

            blocks.append(f"{header}\n{hit.document.page_content.strip()}")

        return "\n\n".join(blocks)


def _file_name(metadata: dict[str, Any]) -> str:
    return str(metadata.get("file_name") or metadata.get("source") or "未知文件")


def _page(metadata: dict[str, Any]) -> int:
    value = metadata.get("page")
    try:
        page = int(value)
    except (TypeError, ValueError):
        return 1
    return page if page > 0 else 1


def _heading(metadata: dict[str, Any]) -> str:
    """优先使用最具体的标题层级。"""
    for key in ("Header 3", "Header 2", "Header 1"):
        value = metadata.get(key)
        if value:
            return str(value)
    return ""


def build_sources(documents: list[Document]) -> list[dict[str, Any]]:
    """把 Document 转换成前端 sources 契约，并保持从 1 开始的编号。"""
    sources: list[dict[str, Any]] = []

    for index, document in enumerate(documents, start=1):
        metadata = document.metadata
        snippet = " ".join(document.page_content.split())
        if len(snippet) > 160:
            snippet = f"{snippet[:160]}…"

        sources.append(
            {
                "index": index,
                "file_name": _file_name(metadata),
                "page": _page(metadata),
                "snippet": snippet,
            }
        )

    return sources


def retrieve_documents(
    question: str,
    *,
    top_k: int | None = None,
    max_distance: float | None = None,
    vector_store: VectorStore | None = None,
) -> RetrievalResult:
    """检索课程片段，并按距离过滤掉明显不相关的候选。"""
    question = question.strip()
    if not question:
        raise ValueError("检索问题不能为空")

    settings = get_settings()
    effective_top_k = top_k if top_k is not None else settings.top_k
    effective_max_distance = (
        max_distance
        if max_distance is not None
        else settings.retrieval_max_distance
    )

    if not 1 <= effective_top_k <= 20:
        raise ValueError("top_k 必须在 1 到 20 之间")
    if effective_max_distance <= 0:
        raise ValueError("max_distance 必须大于 0")

    store = vector_store or get_vector_store()
    candidates = store.similarity_search_with_score(
        question,
        k=effective_top_k,
    )

    qualified = sorted(
        (
            (document, distance)
            for document, distance in candidates
            if distance <= effective_max_distance
        ),
        key=lambda item: item[1],
    )

    hits = [
        RetrievalHit(index=index, document=document, distance=distance)
        for index, (document, distance) in enumerate(qualified, start=1)
    ]

    reason = None
    if not hits:
        reason = (
            "课程资料中没有找到相关内容。"
            if not candidates
            else "检索到的课程片段相关性不足，无法据此回答。"
        )

    return RetrievalResult(question=question, hits=hits, reason=reason)
