from langchain_text_splitters import CharacterTextSplitter,MarkdownHeaderTextSplitter
from langchain_community.embeddings import DashScopeEmbeddings
from mineru import MinerU
import numpy as np
from dotenv import load_dotenv
import os
load_dotenv()

#==========文档加载==========
client = MinerU(token=os.getenv("MINERU_TOKEN"))
result = client.flash_extract("./PDF文档")

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
chunks = Markdown_splitter.split_text(result)

# ==========文本嵌入模型向量化==========　
embeddings = DashScopeEmbeddings(
    model="text-embedding-v4",
)

vectors = embeddings.embed_documents(chunks)
print(f"\n批量向量化: {len(vectors)} 条, 维度: {len(vectors[0])}")

def cosine_similarity(vec1, vec2):
    """余弦相似度函数"""
    dot = np.dot(vec1, vec2)
    return dot / (np.linalg.norm(vec1) * np.linalg.norm(vec2))