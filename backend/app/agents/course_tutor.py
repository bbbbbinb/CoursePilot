from app.agents.build import build_course_tutor_graph
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
from app.core.config import PROJECT_ROOT


SESSION_DIR = PROJECT_ROOT / "data" / "session"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

connect = sqlite3.connect(SESSION_DIR / "table.db",check_same_thread=False)
checkpointer = SqliteSaver(connect)
checkpointer.setup()

def create_course_tutor():
    """兼容旧调用方，返回编译后的 CoursePilot Agent 图。"""
    return build_course_tutor_graph(checkpointer=checkpointer)
