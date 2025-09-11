# xử lý truy vấn AI + webhook Facebook
# https://developers.facebook.com/apps/1786295022763777/add/ Link webhook nếu không có cài ngoài
import requests
import os
import uvicorn
from agent import get_answer
import logging
import socket
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
# from db import engine, SessionLocal, get_db
from sqlalchemy import text
from facebook_tools import reply_comment, get_page_info, get_latest_posts
from agent import get_answer

app = FastAPI()

# CORS cho phép frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép mọi domain gọi API
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== Các hàm kiểm tra kết nối ==========

def test_facebook_connection():
    """Kiểm tra kết nối tới Facebook Page bằng cách gọi hàm get_page_info."""
    try:
        page_info = get_page_info()
        # Giả sử hàm get_page_info sẽ trả về một dictionary nếu thành công
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

# ... (Phần code trên)
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    logging.info(f"📩 Webhook data: {data}")

    if "entry" in data:
        for entry in data["entry"]:
            for change in entry.get("changes", []):
                if change["field"] == "feed":
                    comment = change["value"].get("message", "")
                    comment_id = change["value"].get("comment_id", "")
                    user_id = change["value"]["from"]["id"]
                    user_name = change["value"]["from"]["name"]

                    # Sử dụng logging.info() để ghi lại thông tin comment
                    logging.info(f"📝 Nhận được comment từ {user_name} (ID: {user_id}): '{comment}' với Comment ID: {comment_id}")

                    # ... (Các dòng code còn lại giữ nguyên)
    return {"status": "ok"}
# ... (Phần code dưới)

# ---
# mẫu json facebook gửi
# {
#   "object": "page",
#   "entry": [
#     {
#       "id": "ID_CUA_PAGE",
#       "time": 1754029199,
#       "changes": [
#         {
#           "field": "feed",
#           "value": {
#             "from": {
#               "id": "ID_NGUOI_DUNG",
#               "name": "TÊN_NGƯỜI_DÙNG"
#             },
#             "post_id": "ID_BAI_VIET",
#             "comment_id": "ID_BINH_LUAN",
#             "message": "Nội dung bình luận của người dùng.",
#             "created_time": 1754029199,
#             "item": "comment",
#             "verb": "add"
#           }
#         }
#       ]
#     }
#   ]
# }
# ========== Khởi chạy ứng dụng ==========
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)