# xử lý truy vấn AI + webhook Facebook
# https://developers.facebook.com/apps/1786295022763777/add/ Link webhook nếu không có cài ngoài
import requests
import os
import uvicorn
import logging
import socket
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
# from db import engine, SessionLocal, get_db
from sqlalchemy import text
from facebook_tools import reply_comment, get_page_info, get_latest_posts
from agent import get_answer

# Cấu hình logging để ghi vào file và in ra console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

app = FastAPI()

# CORS cho phép frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== Các hàm kiểm tra kết nối ==========

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

# ---
# ========== API do bạn đã viết ==========
@app.get("/api/page_info")
def page_info_endpoint():
    return get_page_info()

@app.get("/api/page_posts")
def page_posts_endpoint():
    return get_latest_posts()

# ---
# ========== Webhook Facebook và API gốc ==========
VERIFY_TOKEN = "dong1411"

@app.get("/")
async def root():
    """API gốc, trả về trạng thái kết nối của DB và Facebook Page."""
    fb_status = test_facebook_connection()
    return {
        "message": "App is running",
        **fb_status
    }

@app.get("/webhook")
async def verify_webhook(request: Request):
    params = dict(request.query_params)
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return PlainTextResponse(params["hub.challenge"], status_code=200)
    return PlainTextResponse("Invalid token", status_code=403)

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        logging.info(f"📩 Dữ liệu Webhook nhận được: {data}")
    except Exception as e:
        logging.error(f"❌ Lỗi khi nhận dữ liệu webhook: {e}")
        return JSONResponse({"status": "error"}, status_code=500)
    return JSONResponse({"status": "ok"})

# ========== Khởi chạy ứng dụng ==========
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)