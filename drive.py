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
CREDENTIALS_URL = "https://foreignervietnam.com/langchain/drive-folder.php"
CREDENTIALS_TOKEN = os.getenv("CREDENTIALS_TOKEN")
SERVICE_ACCOUNT_FILE = "/tmp/drive-folder.json"
# Thay thế bằng ID thư mục Google Drive của bạn
FOLDER_ID = "1rXRIAvC4wb63WjrAaj0UUiidpL2AiZzQ" 
TEMP_DATA_DIR = "/tmp/data"
CHROMA_DB_DIR = "/tmp/chroma_db"

def setup_vectorstore():
    """
    Tải file xác thực, tải tài liệu từ Google Drive, xử lý chúng
    và trả về Vectorstore (ChromaDB) đã được khởi tạo.
    """
    # 1. Tải file credentials từ API
    print("Bắt đầu: Tải file xác thực...")
    headers = {"X-Access-Token": CREDENTIALS_TOKEN}
    try:
        response = requests.get(CREDENTIALS_URL, headers=headers)
        if response.status_code == 200:
            with open(SERVICE_ACCOUNT_FILE, "wb") as f:
                f.write(response.content)
            print("Hoàn tất: Tải file xác thực thành công.")
        else:
            raise Exception(f"Không thể tải file credentials: {response.status_code}")
    except Exception as e:
        # Nếu lỗi xác thực, dừng ngay quá trình khởi tạo RAG
        print(f"LỖI FATAL: Lỗi tải hoặc lưu file credentials: {e}")
        raise e

    # 2. Xác thực Google Drive
    print("Bắt đầu: Xác thực Google Drive...")
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
    drive_service = build("drive", "v3", credentials=creds)
    print("Hoàn tất: Xác thực Google Drive thành công.")

    # 3. Tải tài liệu từ Drive
    os.makedirs(TEMP_DATA_DIR, exist_ok=True)
    print(f"Bắt đầu: Tải tài liệu từ Folder ID {FOLDER_ID}...")
    
    results = drive_service.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed=false",
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
        if os.path.getsize(filepath) == 0: continue
        
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