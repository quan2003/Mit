"""
Router: Camera Stream - MJPEG live stream + Snapshot từ camera
"""
import cv2
import io
import os
import uuid
import json
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from PIL import Image
from sqlalchemy.orm import Session

from database import Prediction, get_db

router = APIRouter(prefix="/api/stream", tags=["Camera Stream"])

CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/capture")
def capture_and_predict(
    model_name: str = "best_11",
    device_id: str = "web-camera",
    db: Session = Depends(get_db)
):
    """
    Chụp 1 frame từ camera → chạy YOLO → lưu DB → trả kết quả
    Dùng cho chế độ chụp định kỳ hoặc nút 'Chụp & Phân Tích' trên web
    """
    from model_service import model_service

    # Mở camera, chụp 1 frame
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        # Mock nếu không có camera
        img = Image.new("RGB", (640, 480), (30, 60, 30))
        print("[Capture] Không có camera - dùng mock image")
    else:
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return {"error": "Không thể chụp ảnh từ camera"}
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    # Inference
    threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))
    result = model_service.predict(img, model_name)
    if result["confidence"] < threshold:
        result["predicted_class"] = "Binh_thuong"

    # Lưu ảnh
    filename = f"cam_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.jpg"
    file_path = UPLOAD_DIR / filename
    img.save(str(file_path), format="JPEG", quality=90)

    # Lưu DB
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

    return {
        "id": db_pred.id,
        "predicted_class": db_pred.predicted_class,
        "confidence": db_pred.confidence,
        "all_scores": json.loads(db_pred.all_scores or "{}"),
        "model_used": db_pred.model_used,
        "image_filename": filename,
        "captured_at": db_pred.created_at.isoformat(),
    }


def generate_frames():
    """Generator MJPEG frames từ camera"""
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 15)

    if not cap.isOpened():
        # Camera không có → trả 1 frame thông báo
        img = Image.new("RGB", (640, 480), (20, 20, 30))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.text((200, 230), "Không tìm thấy camera", fill=(200, 200, 200))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.getvalue() + b"\r\n")
        cap.release()
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")
    finally:
        cap.release()


def generate_frames_with_ai(model_name: str = "best_11"):
    """Generator MJPEG với YOLO overlay real-time"""
    from model_service import model_service
    import json

    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 15)

    if not cap.isOpened():
        cap.release()
        return

    CLASS_COLORS_BGR = {
        "pink_disease":            (180, 130, 244),
        "stem_cracking_gummosis":  (50,  160, 250),
        "batocera_rufomaculata":   (160, 130, 255),
        "stripe_canker":           (80,  200, 100),
    }
    CLASS_VI = {
        "pink_disease": "Nam Hong",
        "stem_cracking_gummosis": "Nut Than",
        "batocera_rufomaculata": "Sau Duc Than",
        "stripe_canker": "Soc Vo",
    }

    frame_count = 0
    last_result = None

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Chỉ inference mỗi 15 frames (~1 lần/giây) để nhẹ CPU
            if frame_count % 15 == 0:
                try:
                    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    last_result = model_service.predict(pil_img, model_name)
                except Exception:
                    pass

            # Vẽ overlay nếu có kết quả
            if last_result:
                cls = last_result["predicted_class"]
                conf = last_result["confidence"]
                color = CLASS_COLORS_BGR.get(cls, (255, 255, 255))
                label_vi = CLASS_VI.get(cls, cls)

                # Box viền
                h, w = frame.shape[:2]
                cv2.rectangle(frame, (10, 10), (w-10, h-10), color, 2)

                # Background label
                label_text = f"{label_vi}: {conf*100:.0f}%"
                (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                cv2.rectangle(frame, (10, 10), (10 + tw + 10, 10 + th + 14), color, -1)
                cv2.putText(frame, label_text, (15, 10 + th + 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

            frame_count += 1
            _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")
    finally:
        cap.release()


@router.get("/camera")
def camera_stream():
    """Stream camera thô (không có AI)"""
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/camera/ai")
def camera_stream_ai(model_name: str = "best_11"):
    """Stream camera + YOLO overlay real-time"""
    return StreamingResponse(
        generate_frames_with_ai(model_name),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
