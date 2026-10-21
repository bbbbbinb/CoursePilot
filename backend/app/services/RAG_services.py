from pydoc import cli
from langchain_text_splitters import CharacterTextSplitter
from unittest import result

from mineru import MinerU
from dotenv import load_dotenv
import os
load_dotenv()
#文档加载
client = MinerU(token=os.getenv("MINERU_TOKEN"))

#result = client.flash_extract("./PDF文档")
#print(result.markdown)

#文档切分　
text_splitter = CharacterTextSplitter(
    separator=" ",
    chunk_size = 200,
    chunk_overlap = 40
)
chunk = text_splitter.split_text()  #括号里面放文本　str