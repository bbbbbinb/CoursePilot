import asyncio
import json
import logging
import time
import shutil
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

from fastapi.concurrency import run_in_threadpool
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.schemas import ChatRequest, DocumentUploadResponse, HealthResponse
from app.services.RAG_services import loader, split_markdown,get_vector_store
from app.services.rag_chat import stream_rag_answer

router = APIRouter(prefix="/api/v1")
logger = logging.getLogger(__name__)

ALLOWED_SUFFIXES = {".pdf", ".md", ".txt"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def sse_event(event: str, payload: dict) -> str:
    """把事件编码为浏览器 EventSource 可直接解析的 SSE 帧。"""
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {data}\n\n"


async def validate_upload(file: UploadFile) -> None:
    """只做骨架阶段需要的文件类型、空文件和大小校验。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="缺少文件名")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="仅支持 PDF、Markdown 和 TXT 文件",
        )

    total_bytes = 0
    while chunk := await file.read(1024 * 1024):
        total_bytes += len(chunk)
        if total_bytes > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="文件不能超过 20MB")

    # 校验会读取文件；复位游标，方便后续真正实现入库逻辑时继续使用。
    await file.seek(0)
    if total_bytes == 0:
        raise HTTPException(status_code=400, detail="不能上传空文件")

async def save_upload_to_temp(file: UploadFile) -> Path:
    """把上传文件保存到系统临时目录，并返回临时路径。"""
    if not file.filename:
        raise ValueError("缺少文件名")

    suffix = Path(file.filename).suffix.lower()

    # delete=False 表示文件关闭后仍保留，后续交给 MinerU/Chroma 处理
    with tempfile.NamedTemporaryFile(
        prefix="coursepilot-",
        suffix=suffix,
        delete=False,
    ) as temp_file:
        temp_path = Path(temp_file.name)

        # validate_upload() 已经 seek(0)，这里再复位一次更稳妥
        await file.seek(0)

        # copyfileobj 是同步文件操作，放到线程池中执行
        await run_in_threadpool(
            shutil.copyfileobj,
            file.file,
            temp_file,
        )

    return temp_path

def extract_document(file_path: Path) -> str:
    if file_path.suffix.lower() == ".pdf":
        return loader(file_path)

    if file_path.suffix.lower() in {".md", ".txt"}:
        return file_path.read_text(encoding="utf-8-sig")

    raise ValueError(f"不支持的文件类型：{file_path.suffix}")



@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """健康检查不依赖模型 API Key。"""
    return HealthResponse(status="ok")


@router.post("/documents",
            response_model=DocumentUploadResponse,
            status_code=201,)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    """文档上传接口"""
    temp_path: Path | None = None
    try:
        await validate_upload(file)
        #1 将文件保存tmp文件夹
        temp_path = await save_upload_to_temp(file)
        #2 文档加载
        markdown = await run_in_threadpool(extract_document, temp_path)
        #3 文本切分
        chunks = split_markdown(markdown)
        if not chunks:
            raise HTTPException(status_code=400, detail="文档没有可入库内容")
        #4 向量化并存入数据库
        doc_id = uuid4().hex
        chunk_ids = [
            f"{doc_id}:{index:04d}"
            for index in range(len(chunks))
        ]

        for index, chunk in enumerate(chunks):
            chunk.metadata.update(
                {
                    "doc_id": doc_id,
                    "chunk_id": chunk_ids[index],
                    "chunk_index": index,
                    "file_name": file.filename,
                    "source": file.filename,
                }
            )
        vector_store = await run_in_threadpool(get_vector_store)
        await run_in_threadpool(
            vector_store.add_documents,
            chunks,
            ids=chunk_ids,
        )

        return DocumentUploadResponse(
            doc_id=doc_id,
            file_name=file.filename,
            chunks=len(chunks),
            status="ready",
        )
    finally:
        # 5. 删除临时文件
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

        await file.close()


@router.post("/chat")
async def chat(body: ChatRequest) -> StreamingResponse:
    """基于课程知识库流式生成回答。"""
    settings = get_settings()
    effective_top_k = body.top_k or settings.top_k

    async def generate() -> AsyncIterator[str]:
        started_at = time.perf_counter()

        yield sse_event("meta", {"session_id": body.session_id})

        try:
            async for event, payload in stream_rag_answer(
                body.question,
                effective_top_k,
            ):
                yield sse_event(event, payload)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "RAG chat failed for session %s",
                body.session_id,
            )
            yield sse_event(
                "error",
                {"message": "回答生成失败，请稍后重试。"},
            )
            return

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        yield sse_event("done", {"latency_ms": latency_ms})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
