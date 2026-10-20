"""Local preview server for the CoursePilot frontend.

It serves the static files in this folder and implements the MVP API contract
with canned data, so the UI can be developed independently of the backend.

Run:
    python frontend/mock_server.py
Open:
    http://127.0.0.1:8765
"""

from __future__ import annotations

import json
import re
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
PORT = 8765

DEMO_SOURCES = [
    {
        "index": 1,
        "file_name": "数据结构_第08章_递归.pdf",
        "page": 12,
        "snippet": "递归函数通过调用自身来分解问题，每一层调用的局部变量保存在调用栈中。",
    },
    {
        "index": 2,
        "file_name": "数据结构_第08章_递归.pdf",
        "page": 15,
        "snippet": "迭代使用循环和显式状态推进，避免调用栈开销，适合处理大规模数据。",
    },
]

DEMO_ANSWER = """递归和迭代都是重复执行逻辑的方式，区别在于**由谁保存中间状态**。

- **递归**：函数调用自身，每一层的局部变量和返回位置保存在调用栈里 [1]。写法贴近数学定义，但深度受限，空间开销是 O(n)。
- **迭代**：用循环变量和可变状态推进 [2]。没有额外调用栈，通常更适合大规模数据。

所以判断标准不是“谁更高级”，而是问题是否能自然分解成同构子问题。"""


class Handler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/v1/health":
            self._json({"status": "ok", "service": "coursepilot-mock", "version": "0.1.0"})
            return
        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/v1/documents":
            self._handle_upload()
            return
        if path == "/api/v1/chat":
            self._handle_chat()
            return
        self._json({"detail": "Not found"}, status=404)

    def _handle_upload(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        match = re.search(rb'filename="([^"]*)"', body)
        filename = match.group(1).decode("utf-8", "replace") if match else "upload.pdf"
        size = max(len(body), 1)
        pages = max(3, min(60, size // 12000))

        self._json(
            {
                "doc_id": f"mock-{int(time.time() * 1000)}",
                "file_name": filename,
                "pages": pages,
                "chunks": pages * 3,
                "status": "ready",
            }
        )

    def _handle_chat(self):
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json({"detail": "请求体不是合法 JSON"}, status=400)
            return

        question = str(payload.get("question", ""))
        session_id = payload.get("session_id") or f"mock-{int(time.time())}"
        refusal = bool(re.search(r"天气|股票|新闻|房价", question))

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True

        started = time.perf_counter()
        try:
            self._emit("meta", {"session_id": session_id, "top_k": payload.get("top_k", 4)})
            time.sleep(0.25)

            if refusal:
                self._emit(
                    "refusal",
                    {
                        "reason": "这类问题不在已索引的课程资料中。当前知识库只包含数据结构相关的讲义与复习提纲。"
                    },
                )
                self._emit("done", {"latency_ms": int((time.perf_counter() - started) * 1000)})
                return

            self._emit("sources", {"sources": DEMO_SOURCES})
            time.sleep(0.2)

            for index in range(0, len(DEMO_ANSWER), 3):
                self._emit("token", {"text": DEMO_ANSWER[index:index + 3]})
                time.sleep(0.018)

            self._emit("done", {"latency_ms": int((time.perf_counter() - started) * 1000)})
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _emit(self, event: str, data: dict):
        frame = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        self.wfile.write(frame.encode("utf-8"))
        self.wfile.flush()

    def _json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f"[mock] {fmt % args}")


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"CoursePilot mock server: http://127.0.0.1:{PORT}")
    print("Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
