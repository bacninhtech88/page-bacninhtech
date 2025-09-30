# ====================================================================
# FILE: main.py - API Xử lý Webhook Facebook, AI và Kết nối DB
# Cập nhật lần cuối: 26/09/2025
# ====================================================================
import uvicorn
import logging
import requests
import os
# ... (Các imports khác) ...

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from facebook_tools import get_page_info, get_latest_posts, handle_webhook_data 
# ... (Các imports từ drive, agent, v.v.) ...

# ... (Giữ nguyên các khai báo và cấu hình ban đầu: logging, app, load_dotenv, VECTORSTORE, send_email, v.v.) ...


# URL của endpoint PHP để ghi dữ liệu
PHP_CONNECT_URL = "https://foreignervietnam.com/langchain/connect.php" 
VERIFY_TOKEN = "dong1411" # Mã xác minh Webhook của bạn

# ... (Giữ nguyên các hàm test_facebook_connection, page_info_endpoint, root, verify_webhook) ...

# ... (Đoạn giữa của main.py) ...

@app.post("/webhook")
async def webhook(request: Request):
    """
    Xử lý dữ liệu POST từ Webhook Facebook bằng cách gọi hàm bên ngoài.
    """
    try:
        data = await request.json()
        logging.info(f"📩 Dữ liệu Webhook nhận được: {data}")
        
        # GỌI HÀM ĐÃ CHUYỂN SANG facebook_tools.py
        handle_webhook_data(data, PHP_CONNECT_URL)

    except Exception as e:
        # Ghi log lỗi nội bộ
        logging.error(f"❌ Lỗi xử lý Webhook: {e}")

    # BẮT BUỘC: Trả về 200 OK cho Facebook để xác nhận đã nhận
    return JSONResponse({"status": "ok"}, status_code=200)

# ========== 4. Khởi chạy Ứng dụng ==========
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)