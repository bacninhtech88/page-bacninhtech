# ====================================================================
# FILE: main.py - API Xử lý Webhook Facebook, AI và Kết nối DB
# Cập nhật lần cuối: 26/09/2025
# ====================================================================

import requests
import os
import uvicorn
import logging
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import text # Dùng để chạy truy vấn kiểm tra DB
# Giả định các file này tồn tại và được cấu hình
from db import SessionLocal, get_db
from facebook_tools import get_page_info, get_latest_posts 
from agent import get_answer 

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

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 1. Các Hàm Kiểm Tra Kết Nối (Connection Health Checks) ==========

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

def test_db_connection():
    """Kiểm tra kết nối tới Database bằng cách chạy một truy vấn đơn giản."""
    db_status = {"db_connection": "failed", "message": "Lỗi kết nối hoặc truy vấn DB."}
    
    try:
        with SessionLocal() as db:
            # Chạy truy vấn đơn giản để kiểm tra kết nối
            db.execute(text("SELECT 1"))
            db_status = {"db_connection": "success", "message": "Kết nối Database thành công."}
    except Exception as e:
        db_status["error"] = str(e)
        logging.error(f"❌ Lỗi kết nối Database: {e}")
        
    return db_status

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
    db_status = test_db_connection()
    
    # Kết hợp kết quả của cả hai hàm
    return {
        "message": "App is running",
        **fb_status,
        **db_status
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