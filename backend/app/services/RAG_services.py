from langchain_text_splitters import CharacterTextSplitter,MarkdownHeaderTextSplitter
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from mineru import MinerU
from pathlib import Path
import numpy as np
from dotenv import load_dotenv
import os
load_dotenv()

from app.core.config import get_settings

def loader(file_path: str | Path) -> str:
    """文档加载器"""
    path = Path(file_path).expanduser().resolve()

    if not path.is_file():
        raise FileNotFoundError(f"文件不存在：{path}")

    client = MinerU(token=os.getenv("MINERU_TOKEN"))
    result = client.flash_extract(str(path))

    if not isinstance(result, str):
        raise TypeError(f"MinerU 返回类型异常：{type(result)}")

    return result


def split_markdown(markdown: str) -> list[Document]:
    """把 Markdown 文本切分成带标题元数据的 Document。"""
    #==========文档切分==========　
    #text_splitter = CharacterTextSplitter(
    #    separator=" ",
    #    chunk_size = 200,
    #    chunk_overlap = 40
    #)
    #chunk = text_splitter.split_text()  #括号里面放文本　str

    # markdown切分依据，这里是按照三级标题
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    Markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on,
        strip_headers=True
    )
    # 切分文档，接收str，返回值是list[Document]
    chunks = Markdown_splitter.split_text(markdown)
    #texts = [chunk.page_content for chunk in chunks]
    return chunks   #list[Document] ->下一步：ids = vector_store.add_documents(docs)

#    def embed_chunks(chunks:list[Document]) -> list[list[float]]:
#        """文本嵌入模型向量化"""
#        texts = [chunk.page_content for chunk in chunks]
#        embeddings = DashScopeEmbeddings(
#            model="text-embedding-v4",
#        )
#        vectors = embeddings.embed_documents(texts)
#        return vectors

def cosine_similarity(vec1, vec2):
    """余弦相似度函数"""
    dot = np.dot(vec1, vec2)
    return dot / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

settings = get_settings()
embeddings = DashScopeEmbeddings(
    model=settings.embedding_model,
    dashscope_api_key=settings.dashscope_api_key,
)
vector_store = InMemoryVectorStore(embedding=embeddings)
#    # 保存文档到向量数据库
#    ids = vector_store.add_documents(docs)
#    # 删除旧文档
#    vector_store.delete(["doc_1", "doc_2"])
