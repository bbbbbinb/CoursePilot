import json

from fastapi.testclient import TestClient
from langchain_core.documents import Document

from app.api import routes
from app.main import app


client = TestClient(app)


def parse_sse(text: str) -> list[tuple[str, dict]]:
    """解析测试响应中的 SSE 帧，返回事件名和 JSON 数据。"""
    events: list[tuple[str, dict]] = []
    for block in text.split("\n\n"):
        if not block.strip():
            continue

        event_name = "message"
        data_lines: list[str] = []
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                data_lines.append(line.removeprefix("data:").lstrip())

        if data_lines:
            events.append((event_name, json.loads("\n".join(data_lines))))
    return events


def test_health_returns_ok_without_api_key() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_api_does_not_return_frontend_html() -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert "text/html" not in response.headers["content-type"]
    assert response.json()["detail"].startswith("API endpoint not found")


def test_root_serves_frontend() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<html" in response.text.lower()


def test_document_upload_indexes_chunks(monkeypatch) -> None:
    captured: dict = {}

    class FakeVectorStore:
        def add_documents(self, documents, ids):
            captured["documents"] = documents
            captured["ids"] = ids

    monkeypatch.setattr(
        routes,
        "split_markdown",
        lambda markdown: [
            Document(
                page_content=markdown.strip(),
                metadata={"Header 1": "课程讲义"},
            )
        ],
    )
    monkeypatch.setattr(routes, "get_vector_store", lambda: FakeVectorStore())

    response = client.post(
        "/api/v1/documents",
        files={
            "file": (
                "lecture.txt",
                "# 课程讲义\n递归需要基准情形。".encode(),
                "text/plain",
            )
        },
    )

    assert response.status_code == 201
    assert response.json()["file_name"] == "lecture.txt"
    assert response.json()["chunks"] == 1
    assert len(captured["documents"]) == 1
    assert captured["documents"][0].metadata["doc_id"] == response.json()["doc_id"]
    assert captured["ids"] == [
        f"{response.json()['doc_id']}:0000",
    ]


def test_document_upload_rejects_unsupported_file_type() -> None:
    response = client.post(
        "/api/v1/documents",
        files={"file": ("archive.zip", b"not-a-course-document", "application/zip")},
    )

    assert response.status_code == 415
    assert "仅支持 PDF、Markdown 和 TXT" in response.json()["detail"]


def test_chat_streams_sources_tokens_and_done(monkeypatch) -> None:
    captured: dict = {}

    async def fake_stream(question: str, top_k: int):
        captured["question"] = question
        captured["top_k"] = top_k
        yield "sources", {
            "sources": [
                {
                    "index": 1,
                    "file_name": "递归讲义.md",
                    "page": 1,
                    "snippet": "递归函数需要基准情形。",
                }
            ]
        }
        yield "token", {"text": "递归需要基准情形 [1]。"}
        yield "token", {"text": "否则会无限调用。"}

    monkeypatch.setattr(routes, "stream_rag_answer", fake_stream)

    response = client.post(
        "/api/v1/chat",
        json={
            "session_id": "test-session",
            "question": "递归为什么需要基准情形？",
            "top_k": 2,
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(response.content.decode("utf-8"))
    event_names = [name for name, _ in events]
    token_text = "".join(
        payload["text"] for name, payload in events if name == "token"
    )
    sources = next(payload for name, payload in events if name == "sources")
    done = next(payload for name, payload in events if name == "done")

    assert captured == {
        "question": "递归为什么需要基准情形？",
        "top_k": 2,
    }
    assert event_names == ["meta", "sources", "token", "token", "done"]
    assert events[0][1] == {"session_id": "test-session"}
    assert sources["sources"][0]["index"] == 1
    assert token_text == "递归需要基准情形 [1]。否则会无限调用。"
    assert done["latency_ms"] >= 0


def test_chat_streams_refusal_and_done(monkeypatch) -> None:
    async def fake_stream(question: str, top_k: int):
        yield "sources", {"sources": []}
        yield "refusal", {"reason": "课程资料不足以回答该问题。"}

    monkeypatch.setattr(routes, "stream_rag_answer", fake_stream)

    response = client.post(
        "/api/v1/chat",
        json={
            "session_id": "test-session",
            "question": "明天杭州天气怎么样？",
            "top_k": 4,
        },
    )
    events = parse_sse(response.content.decode("utf-8"))

    assert [name for name, _ in events] == [
        "meta",
        "sources",
        "refusal",
        "done",
    ]
    assert events[2][1] == {"reason": "课程资料不足以回答该问题。"}


def test_chat_returns_error_without_done_when_generation_fails(
    monkeypatch,
) -> None:
    async def fake_stream(question: str, top_k: int):
        yield "sources", {"sources": []}
        raise RuntimeError("模型请求失败")

    monkeypatch.setattr(routes, "stream_rag_answer", fake_stream)

    response = client.post(
        "/api/v1/chat",
        json={
            "session_id": "test-session",
            "question": "递归是什么？",
            "top_k": 4,
        },
    )
    events = parse_sse(response.content.decode("utf-8"))

    assert [name for name, _ in events] == ["meta", "sources", "error"]
    assert events[-1][1] == {"message": "回答生成失败，请稍后重试。"}
