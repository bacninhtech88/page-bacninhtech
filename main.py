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

@app.get("/webhook")
async def verify_webhook(request: Request):
    params = dict(request.query_params)
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return PlainTextResponse(params["hub.challenge"], status_code=200)
    return PlainTextResponse("Invalid token", status_code=403)


@app.post("/webhook")
async def webhook_handler(request: Request):
    data = await request.json()
    print("📩 Webhook event:", data)
    return {"status": "ok"}
