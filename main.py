# xử lý truy vấn AI + webhook Facebook
# https://developers.facebook.com/apps/1786295022763777/add/  Link webhook nếu không có cài ngoài

import os
import uvicorn
import socket
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from db import engine, SessionLocal, get_db 
from sqlalchemy import text
from facebook_tools import reply_comment
from agent import get_answer

from facebook_tools import get_page_info, get_latest_posts

app = FastAPI()

# CORS cho phép frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép mọi domain gọi API
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== API do bạn đã viết ==========
@app.get("/api/page_info")
def page_info():
    return get_page_info()

@app.get("/api/page_posts")
def page_posts():
    return get_latest_posts()

# ========== Webhook Facebook ==========
VERIFY_TOKEN = "dong1411"  # điền giống như trong FB app phần xác minh mã

def test_mysql_connection(host="s88d68.cloudnetwork.vn", port=3306):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)  # timeout 5s
    try:
        sock.connect((host, port))
        return {"db_port_check": "open", "host": host, "port": port}
    except socket.error as e:
        return {"db_port_check": "failed", "host": host, "port": port, "error": str(e)}
    finally:
        sock.close()

@app.get("/")
async def root():
    result = test_mysql_connection()
    return {
        "message": "App is running on Render",
        **result
    }
# async def root(db=Depends(get_db)):
#     try:
#         result = db.execute(text("SELECT 1")).fetchone()
#         return {
#             "message": "App is running on Render",
#             "db_connection": "success",
#             "result": result[0]
#         }
#     except Exception as e:
#         return {
#             "message": "App is running on Render",
#             "db_connection": "failed",
#             "error": str(e)
#         }


@app.get("/webhook")
async def verify_webhook(request: Request):
    params = dict(request.query_params)
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return PlainTextResponse(params["hub.challenge"], status_code=200)
    return PlainTextResponse("Invalid token", status_code=403)


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    # lấy comment text
    if "entry" in data:
        for entry in data["entry"]:
            for change in entry["changes"]:
                if change["field"] == "feed":
                    comment = change["value"]["message"]
                    comment_id = change["value"]["comment_id"]
                    # gọi LangChain để sinh câu trả lời
                    answer = get_answer(comment)
                    # phản hồi lên Facebook
                    reply_comment(comment_id, answer)
    return {"status": "ok"}


def test_connection():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Kết nối database thành công!", result.scalar())
    except Exception as e:
        print("❌ Lỗi kết nối database:", e)




if __name__ == "__main__":
    test_connection()
    # Lấy PORT từ biến môi trường, nếu không có thì mặc định 8000 (chạy local)/ luôn đặt sau cùng
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
