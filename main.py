# ====================================================================
# FILE: main.py - API Xử lý Webhook Facebook, AI và Kết nối DB
# Cập nhật lần cuối: 30/09/2025
# ====================================================================
import uvicorn
import logging
import requests
import os
import resend

from fastapi import FastAPI, Request, BackgroundTasks # Đảm bảo BackgroundTasks đã được import
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from facebook_tools import get_page_info, get_latest_posts, handle_webhook_data, reply_comment 
from drive import get_vectorstore
from agent import get_answer 

from dotenv import load_dotenv

# URL của endpoint PHP để ghi dữ liệu
PHP_CONNECT_URL = "https://foreignervietnam.com/langchain/connect.php" 
VERIFY_TOKEN = "dong1411" # Mã xác minh Webhook của bạn

# Cấu hình logging
# ... (Giữ nguyên logging.basicConfig) ...

load_dotenv()
os.environ["CHROMA_TELEMETRY"] = "false"

# ************************************************
# KHÔI PHỤC KHAI BÁO APP TẠI ĐÂY!
# ************************************************
app = FastAPI() # <--- DÒNG NÀY RẤT QUAN TRỌNG VÀ PHẢI CÓ TRƯỚC DECORATOR

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả các domain gọi API
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ************************************************


# ==== TẢI VECTORSTORE ====
VECTORSTORE = get_vectorstore()
# =======================

# ... (Tiếp tục với hàm send_email, test_facebook_connection, và các endpoints) ...

# ... (Hàm process_ai_reply, webhook POST, và uvicorn.run đều đã đúng) ...