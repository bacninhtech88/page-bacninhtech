# xử lý truy vấn AI
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from facebook_tools import get_page_info, get_latest_posts

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép mọi domain gọi API
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/page_info")
def page_info():
    return get_page_info()

@app.get("/api/page_posts")
def page_posts():
    return get_latest_posts()
