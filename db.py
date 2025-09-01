# langchain_app/db.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Thông tin kết nối (thay giá trị thực tế của bạn)
DB_USER = "vie28925_test"
DB_PASS = "nguyenvandong"
DB_HOST = "103.138.88.18"   # hoặc "localhost" nếu cùng server
DB_NAME = "vie28925_test"

# Tạo engine (dùng pymysql)
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}?charset=utf8mb4"

engine = create_engine(DATABASE_URL, echo=False)

# Tạo Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Hàm lấy session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
