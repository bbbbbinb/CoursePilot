from langchain.agents import create_agent
from langchain.tools import tool
from app.services.RAG_services import vector_store
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
load_dotenv()

@tool
def retrieve_docs(query: str):
    """检索知识库，返回相关结果"""
    # 1.根据问题检索知识片段
    documents = vector_store.similarity_search(query)
    # 2.拼接知识片段
    context = "\n".join([doc.page_content for doc in documents])
    return context

"""系统提示词"""
system_prompt = "你是一个课程助教专家，回答与学习资料相关问题时，必须调用工具检索文档，根据文档回答用户的问题，不能自己编造答案。答案要简短，直接引用原文。"

model = init_chat_model(
    "deepseek-flash",
    extra_body = {"thinking": {"type": "disabled"}}
)

course_tutor = create_agent(
    model=model,
    tools=[retrieve_docs],
    system_prompt=system_prompt
)
