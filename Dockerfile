# Sử dụng base image chính thức của Python
FROM python:3.11

# Cài đặt thư mục làm việc
WORKDIR /app

# Copy toàn bộ mã nguồn vào Docker container
COPY . /app

# Cài đặt các thư viện từ requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose cổng 8000
EXPOSE $PORT

# Chạy FastAPI server khi container khởi động
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
