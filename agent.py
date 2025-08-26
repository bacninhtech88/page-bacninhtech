# Langchain Agent xử dụng các tools
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings

# load tài liệu đã train vào vectorDB (ví dụ Chroma)
embeddings = OpenAIEmbeddings()
vectordb = Chroma(persist_directory="./db", embedding_function=embeddings)

qa = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(model="gpt-4o-mini"),
    retriever=vectordb.as_retriever()
)

def get_answer(query: str) -> str:
    result = qa.run(query)
    return result

