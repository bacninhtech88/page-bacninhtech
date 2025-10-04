# ====================================================================
# FILE: main.py - API Xử lý Webhook Facebook, AI và Kết nối DB
# Cập nhật lần cuối: 30/09/2025 (Phiên bản hoàn chỉnh)
# ====================================================================
import uvicorn
import logging
import requests
import os
import resend

from fastapi import FastAPI, Request, BackgroundTasks 
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

# Import các file chức năng đã tách
from facebook_tools import get_page_info, get_latest_posts, handle_webhook_data, reply_comment 
from drive import get_vectorstore
from agent import get_answer 

from dotenv import load_dotenv

# URL của endpoint PHP để ghi dữ liệu
PHP_CONNECT_URL = "https://foreignervietnam.com/langchain/connect.php" 
VERIFY_TOKEN = "dong1411" # Mã xác minh Webhook của bạn

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

load_dotenv()
os.environ["CHROMA_TELEMETRY"] = "false"

# ==== KHAI BÁO FASTAPI APP VÀ MIDDLEWARE ====
app = FastAPI() 

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả các domain gọi API
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==== TẢI VECTORSTORE (CHẠY ĐỒNG BỘ KHI KHỞI ĐỘNG) ====
# Đảm bảo quá trình này không bị Timeout (Kiểm tra drive.py)
try:
    VECTORSTORE = get_vectorstore()
    logging.info("✅ VECTORSTORE đã được tải/khởi tạo thành công.")
except Exception as e:
    logging.error(f"❌ LỖI KHỞI TẠO RAG: Không thể tải VECTORSTORE: {e}")
    # Đặt VECTORSTORE là None để xử lý lỗi sau này nếu cần
    VECTORSTORE = None
# =====================================================


# ========== 1. Các Hàm Hỗ trợ và Kiểm tra Kết Nối ==========

# ==== Gửi email (Giữ nguyên) ====
resend.api_key = "re_DwokJ9W5_E7evBxTVZ2kVVGLPEd9puRuC"

def send_email(subject: str, content: str):
    try:
        resend.Emails.send({
            "from": "bot@bacninhtech.com",
            "to": "contact@bacninhtech.com",
            "subject": subject,
            "html": f"<p>{content}</p>",
        })
    except Exception as e:
        print("Lỗi gửi mail:", e)

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

# ========== 2. Các Endpoints API Cơ bản ==========

@app.get("/api/page_info")
def page_info_endpoint():
    return get_page_info()

@app.get("/api/page_posts")
def page_posts_endpoint():
    return get_latest_posts()

@app.get("/")
async def root():
    """API gốc, trả về trạng thái kết nối của DB và Facebook Page."""
    fb_status = test_facebook_connection()
    
    return {
        "message": "App is running",
        **fb_status,
        "rag_status": "Ready" if VECTORSTORE else "Failed (Check Logs)" # Thêm trạng thái RAG
    }

# ====================================================================
# HÀM XỬ LÝ NỀN (BACKGROUND TASK) CHO AI VÀ PHẢN HỒI
# ====================================================================
def process_ai_reply(idcomment: str, message: str, idpage: str):
    """
    Hàm này chạy trong nền để tạo câu trả lời AI và đăng lên Facebook.
    """
    if not VECTORSTORE:
        logging.error(f"❌ Không thể xử lý AI cho {idcomment}: VECTORSTORE không khả dụng.")
        return
        
    try:
        # 1. GỌI AI ĐỂ TẠO CÂU TRẢ LỜI
        logging.info(f"⏳ Bắt đầu gọi AI cho bình luận: {idcomment}")
        ai_response = get_answer(message, VECTORSTORE)
        logging.info(f"✅ AI đã trả lời cho {idcomment}: {ai_response[:50]}...")

        # 2. PHẢN HỒI BÌNH LUẬN TRÊN FACEBOOK
        fb_response = reply_comment(idcomment, ai_response) 
        
        if 'id' in fb_response:
            logging.info(f"✅ Đã phản hồi thành công trên Facebook. ID phản hồi: {fb_response['id']}")
            
            # --- Tùy chọn: Gửi cập nhật trạng thái DB (Bạn tự bổ sung API cập nhật PHP) ---
            # update_payload = {"idcomment": idcomment, "status": "REPLIED", "ai_response": ai_response}
            # requests.post("YOUR_UPDATE_STATUS_URL", json=update_payload, timeout=5)
            # -----------------------------------------------------------------------------

        else:
            logging.error(f"❌ Lỗi phản hồi Facebook cho {idcomment}: {fb_response}")

    except Exception as e:
        logging.error(f"❌ Lỗi xử lý AI/Facebook Reply cho {idcomment}: {e}")

# ========== 3. Endpoint Webhook Facebook ==========

@app.get("/webhook")
async def verify_webhook(request: Request):
    """Xử lý yêu cầu GET để xác minh webhook từ Facebook."""
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logging.info("✅ Webhook verified successfully.")
        return PlainTextResponse(challenge, status_code=200)
    
    logging.warning("❌ Webhook verification failed. Invalid token or mode.")
    return PlainTextResponse("Invalid token", status_code=403)



@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    # ... (các đoạn code đầu)
    try:
        data = await request.json()
        
        # 1. Ghi DB
        handle_webhook_data(data, PHP_CONNECT_URL) # Giữ nguyên

        # 2. KÍCH HOẠT XỬ LÝ AI BẤT ĐỒNG BỘ
        if data.get('object') == 'page' and data.get('entry'):
            for entry in data['entry']:
                idpage = entry.get('id')
                for change in entry.get('changes', []):
                    # Lọc sự kiện bình luận (comment)
                    if change.get('field') == 'feed' and change.get('value', {}).get('item') == 'comment':
                        value = change['value']
                        idcomment = value.get('comment_id')
                        message = value.get('message', '').strip()
                        idpost = value.get('post_id')
                        # >>> ID NGƯỜI GỬI BÌNH LUẬN CẦN LẤY Ở ĐÂY <<<
                        idpersion = value.get('from', {}).get('id') 

                        # >>>>>>>>>> ĐIỂM SỬA LỖI VÒNG LẶP CỐT LÕI <<<<<<<<<<
                        if idpersion == idpage:
                            logging.info(f"⏭️ Bỏ qua bình luận tự động của Page ID {idpage} (Fix tại main.py).")
                            continue
                        # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
                        
                        # Chỉ xử lý comment mới, không phải reply
                        if message and idcomment and idcomment != idpost: 
                             # Thêm tác vụ AI vào hàng đợi nền
                             background_tasks.add_task(process_ai_reply, idcomment, message, idpage)
                             logging.info(f"➡️ Đã thêm tác vụ AI cho comment ID: {idcomment}")

    except Exception as e:
        logging.error(f"❌ Lỗi xử lý Webhook: {e}")

    # BẮT BUỘC: Trả về 200 OK ngay lập tức cho Facebook
    return JSONResponse({"status": "ok"}, status_code=200)

# ========== 4. Khởi chạy Ứng dụng ==========
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)