"""
Router: Predict - Nhận ảnh, chạy YOLO, trả kết quả
"""
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from database import Prediction, get_db
from model_service import model_service
from PIL import Image
import io

router = APIRouter(prefix="/api/predict", tags=["Prediction"])

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(exist_ok=True)


class PredictionResponse(BaseModel):
    id: int
    predicted_class: str
    confidence: float
    all_scores: dict
    model_used: str
    image_path: Optional[str]
    device_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/models")
def get_models():
    """Lay danh sach model da load de frontend cho nguoi dung chon."""
    return model_service.get_available_models()


@router.post("", response_model=PredictionResponse)
async def predict(
    file: UploadFile = File(...),
    model_name: str = Form(default="best_11"),
    device_id: str = Form(default=None),
    db: Session = Depends(get_db)
):
    """
    Nhận ảnh, chạy YOLO inference, lưu DB và trả kết quả
    """
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "File phải là ảnh!")

    # Đọc ảnh
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")

    # Inference
    try:
        result = model_service.predict(image, model_name)
    except Exception as e:
        raise HTTPException(500, f"Lỗi inference: {str(e)}")

    # ── Áp dụng threshold ──────────────────────────────────────────
    threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))
    if result["confidence"] < threshold:
        result["predicted_class"] = "Binh_thuong"
        # giữ nguyên confidence và all_scores để FE vẫn xem được
    # ───────────────────────────────────────────────────────────────

    # Lưu ảnh vào disk
    ext = Path(file.filename).suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / filename
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(contents)

    # Lưu vào DB
    db_pred = Prediction(
        image_path=str(file_path),
        predicted_class=result["predicted_class"],
        confidence=result["confidence"],
        model_used=result["model_used"],
        all_scores=result["all_scores"],
        device_id=device_id,
    )
    db.add(db_pred)
    db.commit()
    db.refresh(db_pred)

    return PredictionResponse(
        id=db_pred.id,
        predicted_class=db_pred.predicted_class,
        confidence=db_pred.confidence,
        all_scores=json.loads(db_pred.all_scores or "{}"),
        model_used=db_pred.model_used,
        image_path=db_pred.image_path,
        device_id=db_pred.device_id,
        created_at=db_pred.created_at,
    )


@router.get("", response_model=List[PredictionResponse])
def get_predictions(
    skip: int = 0,
    limit: int = 50,
    predicted_class: Optional[str] = None,
    device_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Lấy lịch sử dự đoán"""
    query = db.query(Prediction)
    if predicted_class:
        query = query.filter(Prediction.predicted_class == predicted_class)
    if device_id:
        query = query.filter(Prediction.device_id == device_id)

    items = query.order_by(Prediction.created_at.desc()).offset(skip).limit(limit).all()

    return [
        PredictionResponse(
            id=item.id,
            predicted_class=item.predicted_class,
            confidence=item.confidence,
            all_scores=json.loads(item.all_scores or "{}"),
            model_used=item.model_used,
            image_path=item.image_path,
            device_id=item.device_id,
            created_at=item.created_at,
        ) for item in items
    ]


@router.get("/{prediction_id}")
def get_prediction_detail(prediction_id: int, db: Session = Depends(get_db)):
    """Chi tiết 1 bản ghi prediction"""
    item = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not item:
        raise HTTPException(404, "Không tìm thấy")
    return item


@router.get("/image/{filename}")
def get_image(filename: str):
    """Trả về ảnh đã upload"""
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(404, "Ảnh không tồn tại")
    return FileResponse(file_path)
