# ====================================================================
# FILE: drive.py - Xử lý tải tài liệu từ Google Drive và tạo Vectorstore
# ====================================================================

import os
import io
import requests
from dotenv import load_dotenv

# LangChain và Google Drive Imports
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Tải biến môi trường
load_dotenv()

# ==== Cấu hình API ====
# CREDENTIALS_URL = os.getenv("CREDENTIALS_URL_PHP")
# CREDENTIALS_TOKEN = os.getenv("CREDENTIALS_TOKEN")
# JSON_ACCOUNT_FILE = os.getenv("JSON_ACCOUNT_FILE")
JSON_CONTENT_CREDENTIALS= os.getenv("GCP_CREDENTIALS_JSON")
# Thay thế bằng ID thư mục Google Drive của bạn
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
TEMP_DATA_DIR = "/tmp/data"
CHROMA_DB_DIR = "/tmp/chroma_db"
SERVICE_ACCOUNT_FILE = "/tmp/drive-folder-temp.json" 

def setup_vectorstore():
    """
    Tải file xác thực từ Biến Môi trường, tải tài liệu từ Google Drive, xử lý chúng
    và trả về Vectorstore (ChromaDB) đã được khởi tạo.
    """
    
    # === BƯỚC 1: TẠO FILE CREDENTIALS TỪ BIẾN MÔI TRƯỜNG (Thay thế API) ===
    print("Bắt đầu: Tải file xác thực từ biến môi trường...")
    
    # 1a. Kiểm tra nội dung JSON
    if not JSON_CONTENT_CREDENTIALS:
        # Nếu biến môi trường bị thiếu, dừng ngay quá trình khởi tạo RAG
        raise Exception("LỖI FATAL: Không tìm thấy biến môi trường GCP_CREDENTIALS_JSON.")
        
    # 1b. Ghi nội dung JSON vào file tạm /tmp/drive-folder-temp.json
    try:
        # Ghi file ở chế độ 'w' (write) để ghi nội dung JSON (string)
        with open(SERVICE_ACCOUNT_FILE, "w") as f:
            f.write(JSON_CONTENT_CREDENTIALS) 
        print("Hoàn tất: Tạo file xác thực tạm thời thành công.")
    except Exception as e:
        # Nếu lỗi ghi file (ví dụ: lỗi I/O), dừng ngay
        print(f"LỖI FATAL: Không thể ghi nội dung credentials vào file tạm: {e}")
        raise e

    # === BƯỚC 2: Xác thực Google Drive ===
    print("Bắt đầu: Xác thực Google Drive...")
    # creds sẽ đọc file tạm /tmp/drive-folder-temp.json
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
    drive_service = build("drive", "v3", credentials=creds)
    print("Hoàn tất: Xác thực Google Drive thành công.")

    # === BƯỚC 3, 4, 5: TẢI TÀI LIỆU VÀ TẠO VECTORSTORE ===
    # 3. Tải tài liệu từ Drive
    os.makedirs(TEMP_DATA_DIR, exist_ok=True)
    print(f"Bắt đầu: Tải tài liệu từ Folder ID {DRIVE_FOLDER_ID}...")
    
    results = drive_service.files().list(
        q=f"'{DRIVE_FOLDER_ID}' in parents and trashed=false",
        fields="files(id, name)"
    ).execute()
    files = results.get("files", [])
    
    for file in files:
        file_path = os.path.join(TEMP_DATA_DIR, file["name"])
        if os.path.exists(file_path):
            continue
        
        request = drive_service.files().get_media(fileId=file["id"])
        with io.FileIO(file_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        print(f"   -> Đã tải: {file['name']}")
    
    print("Hoàn tất: Tải tài liệu Drive.")

    # 4. Tải và xử lý tài liệu (Load Documents)
    print("Bắt đầu: Xử lý và chia nhỏ tài liệu...")
    docs = []
    for filename in os.listdir(TEMP_DATA_DIR):
        filepath = os.path.join(TEMP_DATA_DIR, filename)
        # Bổ sung kiểm tra size 0 byte để tránh lỗi Loader
        if os.path.getsize(filepath) == 0: continue
        
        # Cần đảm bảo các loader (PyPDFLoader, Docx2txtLoader) đã được import
        if filename.endswith(".pdf"):
            docs.extend(PyPDFLoader(filepath).load())
        elif filename.endswith(".txt"):
            docs.extend(TextLoader(filepath).load())
        elif filename.endswith(".docx"):
            docs.extend(Docx2txtLoader(filepath).load())
            
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
    splits = text_splitter.split_documents(docs)
    
    print(f"Hoàn tất: Đã chia thành {len(splits)} đoạn văn.")

    # 5. Tạo Vectorstore (Chroma)
    print("Bắt đầu: Tạo Vectorstore (Embedding)...")
    # Cần đảm bảo rằng biến môi trường OPENAI_API_KEY đã được thiết lập.
    embedding = OpenAIEmbeddings() 
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embedding,
        persist_directory=CHROMA_DB_DIR
    )
    print("✅ Hoàn tất: Vectorstore đã sẵn sàng.")
    
    return vectorstore

# Khởi tạo vectorstore khi drive.py được import
VECTORSTORE = setup_vectorstore()

# Hàm getter để main.py có thể truy cập vectorstore
def get_vectorstore():
    return VECTORSTORE
