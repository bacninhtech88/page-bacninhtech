# ====================================================================
# FILE: facebook_tools.py - Xử lý Graph API và Webhook Logic
# ====================================================================
import requests
import os
import logging # Cần để ghi log lỗi khi xử lý webhook
from dotenv import load_dotenv

load_dotenv()

# Cấu hình logging tạm thời (nên sử dụng logging từ main)
# logging.basicConfig(level=logging.INFO) 

ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")

def get_page_info(page_id="105438444519744"):
    # ... (Giữ nguyên) ...
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
    # ... (Giữ nguyên) ...
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

def reply_comment(comment_id: str, message: str):
    # ... (Giữ nguyên) ...
    url = f"https://graph.facebook.com/v19.0/{comment_id}/comments"
    params = {"access_token": ACCESS_TOKEN}
    data = {"message": message}
    response = requests.post(url, params=params, data=data)
    return response.json()

# ====================================================================
# HÀM MỚI: Xử lý Webhook Facebook và Ghi DB qua PHP (ĐÃ SỬA LỖI VÒNG LẶP)
# ====================================================================
def handle_webhook_data(data: dict, php_connect_url: str):
    """
    Trích xuất dữ liệu từ payload webhook và gửi tới connect.php.

    Args:
        data (dict): Dữ liệu JSON từ webhook POST request.
        php_connect_url (str): URL của endpoint PHP để ghi DB.
    """
    
    # Lọc dữ liệu: Chỉ xử lý sự kiện 'page'
    if data.get('object') != 'page' or not data.get('entry'):
        return

    for entry in data['entry']:
        # Lấy ID Page ngay ở đây để so sánh sau này
        idpage = entry.get('id')

        for change in entry.get('changes', []):
            # Lọc sự kiện bình luận (comment) trong trường 'feed'
            if change.get('field') == 'feed' and change.get('value', {}).get('item') == 'comment':
                value = change['value']
                
                # --- 1. Trích xuất dữ liệu ---
                idcomment = value.get('comment_id')
                idpost = value.get('post_id')
                idpersion = value.get('from', {}).get('id') # ID người comment
                message = value.get('message', '').strip()
                creatime = value.get('created_time') 
                
                # >>>>>> KIỂM TRA MỚI: BỎ QUA BÌNH LUẬN TỪ CHÍNH PAGE <<<<<<
                if idpersion == idpage:
                    logging.info(f"⏭️ Bỏ qua bình luận tự động của Page ID {idpage} để tránh vòng lặp.")
                    continue
                # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
                
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
                try:
                    response = requests.post(php_connect_url, json=db_payload, timeout=5)
                    
                    if response.status_code == 200 and response.json().get('status') == 'success':
                        logging.info(f"✅ Bình luận ID {idcomment} đã được ghi thành công qua PHP.")
                    else:
                        logging.error(f"❌ Lỗi ghi DB qua PHP. Code: {response.status_code}, Res: {response.text}")
                except requests.exceptions.RequestException as e:
                    logging.error(f"❌ Lỗi mạng khi gửi tới PHP: {e}")