# ====================================================================
# FILE: agent.py - Logic Xử lý AI (RAG) (ĐÃ SỬA LỖI PROMPT)
# ====================================================================
import os
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import Chroma 
# >>> IMPORT CẦN THIẾT <<<
from langchain.prompts import PromptTemplate, ChatPromptTemplate 
# >>>>>>>>>>>>>>>>>>>>>>>>

# Khởi tạo mô hình ngôn ngữ lớn (LLM) chỉ một lần
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# TẠO PROMPT TEMPLATE TÙY CHỈNH (GLOBAL)
RAG_PROMPT_TEMPLATE = """
Bạn là trợ lý AI thân thiện và chuyên nghiệp cho Page Yêu Công Nghệ - bacninhtech.
Nhiệm vụ của bạn là **TÓM TẮT** và **CHỈ TRẢ LỜI** dựa trên ngữ cảnh được cung cấp dưới đây, tuyệt đối không bịa ra thông tin.
Nếu thông tin trong ngữ cảnh không đủ để trả lời, hãy nói một cách lịch sự rằng bạn sẽ kiểm tra lại hoặc đề nghị khách hàng liên hệ trực tiếp.

NGỮ CẢNH:
{context}

CÂU HỎI:
{question}
"""

def get_answer(query: str, vectorstore: Chroma) -> str:
    """
    Sử dụng RetrievalQA Chain với Prompt Tùy chỉnh để trả lời câu hỏi.
    """
    
    # 1. Tạo đối tượng truy vấn (Retriever)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5}) # Thử tăng k lên 5 để lấy nhiều ngữ cảnh hơn

    # 2. Định nghĩa Prompt Tùy chỉnh
    custom_prompt = PromptTemplate(
        template=RAG_PROMPT_TEMPLATE,
        input_variables=["context", "question"],
    )

    # 3. Tạo RetrievalQA Chain với custom_prompt
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=False,
        # >>> THÊM THAM SỐ CẤU HÌNH PROMPT TẠI ĐÂY <<<
        chain_type_kwargs={"prompt": custom_prompt}
        # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    )
    
    # 4. Thực thi truy vấn
    result = qa_chain.invoke({"query": query})

    # 5. Trả về kết quả
    return result['result']