# ====================================================================
# FILE: main.py - API Xử lý Webhook Facebook, AI và Kết nối DB
# Cập nhật lần cuối: 26/09/2025
# ====================================================================
import uvicorn
import logging
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import text # Dùng để chạy truy vấn kiểm tra DB
# Giả định các file này tồn tại và được cấu hình
# from db import SessionLocal, get_db
from facebook_tools import get_page_info, get_latest_posts 
from agent import get_answer 

import os
import io
import shutil
import requests
import resend
import re
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA

from pydantic import BaseModel


# URL của endpoint PHP để ghi dữ liệu
PHP_CONNECT_URL = "https://foreignervietnam.com/langchain/connect.php" 
VERIFY_TOKEN = "dong1411" # Mã xác minh Webhook của bạn

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả các domain gọi API
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()
os.environ["CHROMA_TELEMETRY"] = "false"

# ==== Cấu hình API ====
CREDENTIALS_URL = "https://foreignervietnam.com/langchain/drive-folder.php"
CREDENTIALS_TOKEN = os.getenv("CREDENTIALS_TOKEN")
SERVICE_ACCOUNT_FILE = "/tmp/drive-folder.json"
FOLDER_ID = "1rXRIAvC4wb63WjrAaj0UUiidpL2AiZzQ"
# ========== 1. Các Hàm Kiểm Tra Kết Nối (Connection Health Checks) ==========
# ==== Gửi email ====
resend.api_key = "re_DwokJ9W5_E7evBxTVZ2kVVGLPEd9puRuC"

def send_email(subject: str, content: str):
    try:
        resend.Emails.send({
            "from": "bot@bacninhtech.com",
            "to": "contact@bacninhtech.com",
            "subject": subject,
            "html": f"<p>{content}</p>",
        })
    except Exception as e:
        print("Lỗi gửi mail:", e)

# ==== Tải file credentials từ API ====
headers = {"X-Access-Token": CREDENTIALS_TOKEN}
response = requests.get(CREDENTIALS_URL, headers=headers)
if response.status_code == 200:
    with open(SERVICE_ACCOUNT_FILE, "wb") as f:
        f.write(response.content)
else:
    raise Exception(f"Không thể tải file credentials: {response.status_code}")

# ==== Google Drive functions ====
def authenticate_drive():
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
    return build("drive", "v3", credentials=creds)

def download_drive_files(drive_service):
    os.makedirs("/tmp/data", exist_ok=True)
    results = drive_service.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed=false",
        fields="files(id, name)"
    ).execute()
    files = results.get("files", [])
    for file in files:
        file_path = os.path.join("/tmp/data", file["name"])
        if os.path.exists(file_path):
            continue
        request = drive_service.files().get_media(fileId=file["id"])
        with io.FileIO(file_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

# ==== Tải và xử lý tài liệu ====
def load_documents():
    docs = []
    for filename in os.listdir("/tmp/data"):
        filepath = os.path.join("/tmp/data", filename)
        if os.path.getsize(filepath) == 0:
            continue
        if filename.endswith(".pdf"):
            docs.extend(PyPDFLoader(filepath).load())
        elif filename.endswith(".txt"):
            docs.extend(TextLoader(filepath).load())
        elif filename.endswith(".docx"):
            docs.extend(Docx2txtLoader(filepath).load())
    return docs

# ==== Tạo Vectorstore từ tài liệu ====
drive_service = authenticate_drive()
download_drive_files(drive_service)
documents = load_documents()

text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
splits = text_splitter.split_documents(documents)

embedding = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(
    documents=splits,
    embedding=embedding,
    persist_directory="/tmp/chroma_db"
)







def test_facebook_connection():
    """Kiểm tra kết nối tới Facebook Page bằng cách gọi hàm get_page_info."""
    try:
        page_info = get_page_info()
        if "id" in page_info and "name" in page_info:
            return {
                "facebook_connection": "success",
                "page_id": page_info.get("id"),
                "page_name": page_info.get("name")
            }
        else:
            return {
                "facebook_connection": "failed",
                "message": "Không thể lấy thông tin Page. Kiểm tra Access Token và quyền."
            }
    except Exception as e:
        return {
            "facebook_connection": "failed",
            "error": str(e),
            "message": "Lỗi khi gọi API Facebook."
        }

# ========== 2. Các Endpoints API Cơ bản ==========

@app.get("/api/page_info")
def page_info_endpoint():
    return get_page_info()

@app.get("/api/page_posts")
def page_posts_endpoint():
    return get_latest_posts()

@app.get("/")
async def root():
    """API gốc, trả về trạng thái kết nối của DB và Facebook Page."""
    fb_status = test_facebook_connection()
    
    # Kết hợp kết quả của cả hai hàm
    return {
        "message": "App is running",
        **fb_status,
    }

# ========== 3. Endpoint Webhook Facebook ==========

@app.get("/webhook")
async def verify_webhook(request: Request):
    """Xử lý yêu cầu GET để xác minh webhook từ Facebook."""
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logging.info("✅ Webhook verified successfully.")
        return PlainTextResponse(challenge, status_code=200)
    
    logging.warning("❌ Webhook verification failed. Invalid token or mode.")
    return PlainTextResponse("Invalid token", status_code=403)

@app.post("/webhook")
async def webhook(request: Request):
    """
    Xử lý dữ liệu POST từ Webhook Facebook, trích xuất và GỬI tới connect.php để lưu DB.
    """
    try:
        data = await request.json()
        logging.info(f"📩 Dữ liệu Webhook nhận được: {data}")

        # Lọc dữ liệu: Chỉ xử lý sự kiện 'page'
        if data.get('object') != 'page' or not data.get('entry'):
            return JSONResponse({"status": "ok"})

        for entry in data['entry']:
            idpage = entry.get('id')

            for change in entry.get('changes', []):
                # Lọc sự kiện bình luận (comment) trong trường 'feed'
                if change.get('field') == 'feed' and change.get('value', {}).get('item') == 'comment':
                    value = change['value']
                    
                    # --- 1. Trích xuất dữ liệu ---
                    idcomment = value.get('comment_id')
                    idpost = value.get('post_id')
                    idpersion = value.get('from', {}).get('id') 
                    message = value.get('message', '').strip()
                    creatime = value.get('created_time') 
                    
                    # Bỏ qua nếu thiếu nội dung hoặc sự kiện không hợp lệ
                    if not message or not idcomment or idcomment == idpost:
                        continue
                        
                    # --- 2. Chuẩn bị Payload cho connect.php ---
                    db_payload = {
                        "idpage": idpage,
                        "idpersion": idpersion,
                        "idpost": idpost,
                        "idcomment": idcomment,
                        "message": message,
                        "creatime": creatime,
                        "status": "PENDING",    
                        "is_replied": 0,    
                        "ai_response": None,
                        "processed_at": None
                    }

                    # --- 3. Gửi yêu cầu POST tới connect.php ---
                    response = requests.post(PHP_CONNECT_URL, json=db_payload, timeout=5)
                    
                    if response.status_code == 200 and response.json().get('status') == 'success':
                        logging.info(f"✅ Bình luận ID {idcomment} đã được ghi thành công qua PHP.")
                    else:
                        logging.error(f"❌ Lỗi ghi DB qua PHP. Code: {response.status_code}, Res: {response.text}")
                        
    except Exception as e:
        # Ghi log lỗi nội bộ
        logging.error(f"❌ Lỗi xử lý Webhook hoặc gửi tới PHP: {e}")

    # BẮT BUỘC: Trả về 200 OK cho Facebook để xác nhận đã nhận
    return JSONResponse({"status": "ok"}, status_code=200)

# ========== 4. Khởi chạy Ứng dụng ==========
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    # Sử dụng 'main:app' vì file là main.py
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)