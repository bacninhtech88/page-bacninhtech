# ====================================================================
# FILE: main.py - API Xử lý Webhook Facebook, AI và Kết nối DB
# Cập nhật lần cuối: 26/09/2025
# ====================================================================
import uvicorn
import logging
import requests
import os
import resend
# ... (Giữ nguyên các import cần thiết khác) ...

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import text 
from facebook_tools import get_page_info, get_latest_posts 
from agent import get_answer 

from dotenv import load_dotenv
# Bỏ tất cả các import Google Drive và Langchain liên quan đến tạo vectorstore

from pydantic import BaseModel

# --- IMPORT MỚI ---
from drive import get_vectorstore
# -----------------


# URL của endpoint PHP để ghi dữ liệu
PHP_CONNECT_URL = "https://foreignervietnam.com/langchain/connect.php" 
VERIFY_TOKEN = "dong1411" # Mã xác minh Webhook của bạn

# Cấu hình logging
# ... (Giữ nguyên cấu hình logging) ...
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

# ==== TẢI VECTORSTORE SAU KHI TÁCH FILE ====
# VECTORSTORE sẽ được tạo ra khi drive.py được import
VECTORSTORE = get_vectorstore()
# ========================================

# ==== Gửi email ====
resend.api_key = "re_DwokJ9W5_E7evBxTVZ2kVVGLPEd9puRuC"

def send_email(subject: str, content: str):
    # ... (Giữ nguyên hàm send_email) ...
    try:
        resend.Emails.send({
            "from": "bot@bacninhtech.com",
            "to": "contact@bacninhtech.com",
            "subject": subject,
            "html": f"<p>{content}</p>",
        })
    except Exception as e:
        print("Lỗi gửi mail:", e)

# BỎ TOÀN BỘ CÁC HÀM: authenticate_drive, download_drive_files, load_documents, và code tạo vectorstore ở đây.


def test_facebook_connection():
    # ... (Giữ nguyên hàm test_facebook_connection) ...
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
# ... (Giữ nguyên các Endpoints) ...
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
    
    return {
        "message": "App is running",
        **fb_status,
        "rag_status": "Ready" if VECTORSTORE else "Failed" # Thêm trạng thái RAG
    }

# ========== 3. Endpoint Webhook Facebook ==========
# ... (Giữ nguyên các Endpoint Webhook) ...
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
    # ... (Giữ nguyên logic webhook) ...
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
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)