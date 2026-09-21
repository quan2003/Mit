from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# SQLite cho local dev (không cần cài PostgreSQL)
# Đổi DATABASE_URL trong .env khi deploy production
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./caymit.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Prediction(Base):
    """Lưu kết quả phát hiện bệnh"""
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    image_path = Column(String, nullable=True)         # Đường dẫn ảnh đã lưu
    predicted_class = Column(String, nullable=False)   # Tên bệnh
    confidence = Column(Float, nullable=False)         # Độ tin cậy (0-1)
    model_used = Column(String, default="best_11")     # Model nào inference
    all_scores = Column(Text, nullable=True)           # JSON scores tất cả class
    device_id = Column(String, nullable=True)          # ID của Jetson Nano
    created_at = Column(DateTime, default=datetime.utcnow)


class SensorData(Base):
    """Lưu dữ liệu cảm biến nhiệt độ, độ ẩm"""
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    temperature = Column(Float, nullable=False)        # Nhiệt độ (°C)
    humidity = Column(Float, nullable=False)           # Độ ẩm (%)
    device_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DeviceState(Base):
    """Lưu trạng thái thiết bị (đèn, relay...)"""
    __tablename__ = "device_states"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, nullable=False)
    light_on = Column(Boolean, default=False)          # Trạng thái đèn
    is_online = Column(Boolean, default=False)         # Thiết bị online?
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def get_db():
    """Dependency injection - lấy DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Tạo tất cả bảng nếu chưa có"""
    Base.metadata.create_all(bind=engine)
