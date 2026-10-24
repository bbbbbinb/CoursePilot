from langchain_core.documents import Document

from app.services.retrieval import retrieve_documents


def make_document(content: str, chunk_index: int) -> Document:
    return Document(
        page_content=content,
        metadata={
            "doc_id": "doc-test",
            "chunk_id": f"doc-test:{chunk_index:04d}",
            "chunk_index": chunk_index,
            "file_name": "递归讲义.md",
            "Header 1": "第一章 递归",
        },
    )


class FakeVectorStore:
    def similarity_search_with_score(self, query: str, k: int):
        assert query == "递归和迭代有什么区别？"
        assert k == 3
        return [
            (make_document("迭代使用循环推进状态。", 1), 0.62),
            (make_document("递归函数需要基准情形。", 0), 0.21),
            (make_document("杭州明天有雨。", 2), 1.82),
        ]


def test_retrieve_documents_filters_and_builds_aligned_context() -> None:
    result = retrieve_documents(
        "递归和迭代有什么区别？",
        top_k=3,
        max_distance=1.1,
        vector_store=FakeVectorStore(),
    )

    assert result.is_sufficient is True
    assert [hit.index for hit in result.hits] == [1, 2]
    assert [hit.distance for hit in result.hits] == [0.21, 0.62]
    assert [source["index"] for source in result.sources] == [1, 2]
    assert result.sources[0]["file_name"] == "递归讲义.md"
    assert result.sources[0]["page"] == 1
    assert result.sources[0]["snippet"] == "递归函数需要基准情形。"
    assert result.context.startswith("[1] 文件：递归讲义.md；章节：第一章 递归")
    assert "[2] 文件：递归讲义.md；章节：第一章 递归" in result.context


class IrrelevantVectorStore:
    def similarity_search_with_score(self, query: str, k: int):
        return [
            (make_document("递归函数需要基准情形。", 0), 1.5),
            (make_document("迭代使用循环推进状态。", 1), 1.8),
        ]


def test_retrieve_documents_refuses_when_all_candidates_are_too_distant() -> None:
    result = retrieve_documents(
        "杭州明天天气怎么样？",
        top_k=2,
        max_distance=1.1,
        vector_store=IrrelevantVectorStore(),
    )

    assert result.is_sufficient is False
    assert result.hits == []
    assert result.sources == []
    assert result.context == ""
    assert result.reason == "检索到的课程片段相关性不足，无法据此回答。"


class EmptyVectorStore:
    def similarity_search_with_score(self, query: str, k: int):
        return []


def test_retrieve_documents_refuses_empty_knowledge_base() -> None:
    result = retrieve_documents(
        "递归是什么？",
        top_k=2,
        vector_store=EmptyVectorStore(),
    )

    assert result.is_sufficient is False
    assert result.reason == "课程资料中没有找到相关内容。"
