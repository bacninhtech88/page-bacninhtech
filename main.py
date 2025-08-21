# xử lý truy vấn AI + webhook Facebook
# https://developers.facebook.com/apps/1786295022763777/add/  Link webhook nếu không có cài ngoài

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

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

@app.get("/")
async def root():
    return {"message": "App is running on Render"}


@app.get("/page")
async def verify_webhook(request: Request):
    """
    Facebook gọi GET khi xác minh webhook
    Ví dụ: ?hub.mode=subscribe&hub.verify_token=xxx&hub.challenge=1234
    """
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(challenge, status_code=200)
    else:
        return PlainTextResponse("Verification failed", status_code=403)

@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)
    else:
        return JSONResponse(content={"error": "Invalid token"}, status_code=403)


@app.post("/webhook")
async def receive_webhook(request: Request):
    """
    Facebook gọi POST khi có sự kiện (comment, message, feed...)
    """
    data = await request.json()
    print("🔔 Webhook event received:", data, flush=True)

    # Ví dụ: xử lý comment
    if "entry" in data:
        for entry in data["entry"]:
            if "changes" in entry:
                for change in entry["changes"]:
                    if change.get("field") == "feed":
                        comment_data = change.get("value", {})
                        if comment_data.get("item") == "comment":
                            message = comment_data.get("message")
                            comment_id = comment_data.get("comment_id")
                            print(f"💬 Comment mới: {message} (ID: {comment_id})")

    return JSONResponse(content={"status": "ok"}, status_code=200)
