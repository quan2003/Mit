"""
Camera Module - Chụp ảnh từ Camera CM3+ / USB Webcam
Hỗ trợ: OpenCV (USB Cam), PiCamera2 (CM3+)
"""
import io
import os
from pathlib import Path
from datetime import datetime

# Thử import OpenCV
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

# Thử import PiCamera2 (Raspberry Pi CM3+)
try:
    from picamera2 import Picamera2
    HAS_PICAMERA = True
except ImportError:
    HAS_PICAMERA = False

from PIL import Image

CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
SAVE_DIR = Path("captured_images")
SAVE_DIR.mkdir(exist_ok=True)


class Camera:
    def __init__(self):
        self.cap = None
        self.picam = None
        self._init_camera()

    def _init_camera(self):
        if HAS_PICAMERA:
            print("[Camera] Dùng PiCamera2 (CM3+)")
            self.picam = Picamera2()
            config = self.picam.create_still_configuration(
                main={"size": (1920, 1080)}
            )
            self.picam.configure(config)
            self.picam.start()
        elif HAS_OPENCV:
            print(f"[Camera] Dùng OpenCV (index={CAMERA_INDEX})")
            self.cap = cv2.VideoCapture(CAMERA_INDEX)
            if not self.cap.isOpened():
                raise RuntimeError(f"Không thể mở camera index {CAMERA_INDEX}")
        else:
            print("[Camera] ⚠ Không có camera library - chạy mock mode")

    def capture(self, save: bool = True) -> bytes:
        """Chụp ảnh, trả về bytes JPEG"""
        if self.picam:
            # PiCamera2
            frame = self.picam.capture_array()
            img = Image.fromarray(frame).convert("RGB")
        elif self.cap:
            # OpenCV
            ret, frame = self.cap.read()
            if not ret:
                raise RuntimeError("Không thể đọc frame từ camera")
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
        else:
            # Mock: tạo ảnh trắng để test
            print("[Camera] Mock mode: tạo ảnh test")
            img = Image.new("RGB", (640, 480), color=(200, 220, 180))

        # Convert to JPEG bytes
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        img_bytes = buf.getvalue()

        # Lưu ảnh nếu cần
        if save:
            filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            (SAVE_DIR / filename).write_bytes(img_bytes)

        return img_bytes

    def release(self):
        if self.cap:
            self.cap.release()
        if self.picam:
            self.picam.stop()
