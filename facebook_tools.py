# gọi facebook graph API
import requests
import os
from dotenv import load_dotenv
load_dotenv()

ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")

def get_page_info(page_id="105438444519744"):
    url = f"https://graph.facebook.com/v19.0/{page_id}"
    params = {
        "access_token": ACCESS_TOKEN,
        "fields": "name,fan_count,about"
    }
    res = requests.get(url, params=params)
    data = res.json()
    if "error" in data:
        print("Lỗi:", data["error"]["message"])
    return data

def get_latest_posts(page_id="105438444519744", limit=3):
    url = f"https://graph.facebook.com/v19.0/{page_id}/posts"
    params = {
        "access_token": ACCESS_TOKEN,
        "limit": limit,
        "fields": "message,created_time"
    }
    res = requests.get(url, params=params)
    data = res.json()
    if "error" in data:
        print("Lỗi:", data["error"]["message"])
    return data

