from app.agents.build import build_course_tutor_graph


def create_course_tutor():
    """兼容旧调用方，返回编译后的 CoursePilot Agent 图。"""
    return build_course_tutor_graph()
