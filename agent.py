# ====================================================================
# FILE: agent.py - Logic Xử lý AI (RAG)
# ====================================================================
import os
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import Chroma # Giữ lại cho Type Hinting
# Bạn không cần Langchain Embeddings nếu bạn đã tạo Vectorstore xong
# từ drive.py và chỉ cần sử dụng nó.

# Khởi tạo mô hình ngôn ngữ lớn (LLM) chỉ một lần
# Giả định bạn đã có biến môi trường OPENAI_API_KEY
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# XÓA/COMMENT TOÀN BỘ LOGIC TẠO VECTORSTORE TẠI ĐÂY:
# # load tài liệu đã train vào vectorDB (ví dụ Chroma)
# embeddings = OpenAIEmbeddings()
# vectordb = Chroma(persist_directory="./db", embedding_function=embeddings)
# qa = RetrievalQA.from_chain_type(
#     llm=ChatOpenAI(model="gpt-4o-mini"),
#     retriever=vectordb.as_retriever()
# )


def get_answer(query: str, vectorstore: Chroma) -> str:
    """
    Sử dụng RetrievalQA Chain để trả lời câu hỏi dựa trên Vectorstore được cung cấp.
    """
    
    # 1. Tạo RAG Chain MỖI KHI CÓ CÂU HỎI (để đảm bảo tính linh hoạt)
    # hoặc bạn có thể tạo Chain một lần ở main.py và truyền vào nếu cần tối ưu
    
    # Tạo đối tượng truy vấn (Retriever) từ vectorstore được truyền vào
    retriever = vectorstore.as_retriever()

    # Tạo RetrievalQA Chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=False 
    )
    
    # Thực thi truy vấn
    result = qa_chain.invoke({"query": query}) # Thay qa.run(query) bằng qa.invoke({"query": query})

    # Trả về kết quả
    return result['result']