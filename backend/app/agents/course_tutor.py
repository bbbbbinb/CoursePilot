from langchain.agents import create_agent
from langchain.tools import tool
from app.services.RAG_services import get_vector_store
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
load_dotenv()

@tool
def retrieve_docs(query: str):
    """检索知识库，返回相关结果"""
    # 1.根据问题检索知识片段
    vector_store = get_vector_store()
    documents = vector_store.similarity_search(query)
    # 2.拼接知识片段
    context = "\n".join([doc.page_content for doc in documents])
    return context

"""系统提示词"""
system_prompt = """你是课程助教。

只能依据用户消息中提供的课程片段回答，不得使用课程片段之外的知识。

每个事实性结论后必须标注来源编号，例如 [1]、[2]。
引用编号只能使用给定片段中存在的编号。

如果课程片段没有直接、充分的依据，必须只回答：
“当前课程资料不足以回答该问题。”

不要尝试推测，不要补充外部知识。"""

model = init_chat_model(
    "deepseek-flash",
    extra_body = {"thinking": {"type": "disabled"}}
)

course_tutor = create_agent(
    model=model,
    tools=[retrieve_docs],
    system_prompt=system_prompt
)
