from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agents.build import build_course_tutor_graph
from app.core.config import get_settings


@asynccontextmanager
async def create_course_tutor() -> AsyncIterator[object]:
    """为一次图执行创建可异步持久化的 SQLite Checkpointer。"""
    settings = get_settings()
    settings.session_db_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(settings.session_db_path) as connection:
        await connection.execute("PRAGMA journal_mode=WAL")
        await connection.execute("PRAGMA busy_timeout=5000")
        checkpointer = AsyncSqliteSaver(connection)
        await checkpointer.setup()
        yield build_course_tutor_graph(checkpointer=checkpointer)
