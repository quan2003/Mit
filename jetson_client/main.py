"""
Jetson Nano Main Client
Vòng lặp chính: chụp ảnh → gửi API → nhận kết quả → điều khiển đèn
"""
import io
import os
import time
import signal
import sys
import requests
from datetime import datetime
from dotenv import load_dotenv

from camera import Camera
from sensor import SensorReader

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
DEVICE_ID = os.getenv("DEVICE_ID", "jetson-nano-01")
CAPTURE_INTERVAL = int(os.getenv("CAPTURE_INTERVAL", "300"))  # seconds

# GPIO relay (chỉ dùng trên Jetson Nano thật)
RELAY_PIN = os.getenv("RELAY_PIN", None)
gpio = None

def init_gpio():
    global gpio
    if RELAY_PIN:
        try:
            import Jetson.GPIO as GPIO
            gpio = GPIO
            gpio.setmode(gpio.BOARD)
            gpio.setup(int(RELAY_PIN), gpio.OUT, initial=gpio.LOW)
            print(f"[GPIO] Relay pin {RELAY_PIN} sẵn sàng")
        except ImportError:
            print("[GPIO] Không có Jetson.GPIO - bỏ qua relay")

def set_relay(on: bool):
    """Bật/tắt relay (đèn)"""
    if gpio:
        state = gpio.HIGH if on else gpio.LOW
        gpio.output(int(RELAY_PIN), state)
    print(f"[Relay] Đèn: {'BẬT' if on else 'TẮT'}")

def send_heartbeat():
    """Báo thiết bị online"""
    try:
        requests.post(f"{API_BASE_URL}/api/devices/heartbeat",
                      params={"device_id": DEVICE_ID}, timeout=5)
    except Exception:
        pass

def check_pending_command():
    """Poll backend để lấy lệnh điều khiển đèn"""
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/devices/command/{DEVICE_ID}", timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("has_command"):
                set_relay(data.get("light_on", False))
    except Exception as e:
        print(f"[Command] Lỗi poll command: {e}")

def send_sensor_data(sensor: SensorReader):
    """Gửi dữ liệu cảm biến"""
    try:
        data = sensor.read()
        resp = requests.post(
            f"{API_BASE_URL}/api/sensors",
            json={**data, "device_id": DEVICE_ID},
            timeout=10,
        )
        print(f"[Sensor] Nhiệt độ: {data['temperature']}°C | Độ ẩm: {data['humidity']}%")
        return data
    except Exception as e:
        print(f"[Sensor] Lỗi gửi sensor: {e}")
        return None

def capture_and_predict(camera: Camera):
    """Chụp ảnh và gửi lên API để predict"""
    try:
        print(f"[Camera] Chụp ảnh... {datetime.now().strftime('%H:%M:%S')}")
        img_bytes = camera.capture(save=True)

        # Gửi lên API
        resp = requests.post(
            f"{API_BASE_URL}/api/predict",
            files={"file": ("capture.jpg", io.BytesIO(img_bytes), "image/jpeg")},
            data={"model_name": "best_11", "device_id": DEVICE_ID},
            timeout=30,
        )

        if resp.status_code == 200:
            result = resp.json()
            cls = result["predicted_class"]
            conf = result["confidence"]
            print(f"[Result] Phát hiện: {cls} ({conf*100:.1f}%)")
            return result
        else:
            print(f"[API] Lỗi: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"[Camera] Lỗi: {e}")
    return None

def main():
    print("=" * 50)
    print(f"CayMit Jetson Client khởi động")
    print(f"Device ID : {DEVICE_ID}")
    print(f"API       : {API_BASE_URL}")
    print(f"Interval  : {CAPTURE_INTERVAL}s")
    print("=" * 50)

    init_gpio()
    camera = Camera()
    sensor = SensorReader()

    def shutdown(sig, frame):
        print("\n[Shutdown] Đang tắt...")
        camera.release()
        sensor.cleanup()
        if gpio:
            gpio.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    poll_counter = 0

    while True:
        try:
            # Mỗi vòng lặp
            send_heartbeat()
            send_sensor_data(sensor)
            capture_and_predict(camera)
            check_pending_command()

            print(f"[Sleep] Chờ {CAPTURE_INTERVAL}s...\n")
            
            # Poll lệnh mỗi 10s trong lúc chờ
            for _ in range(CAPTURE_INTERVAL // 10):
                time.sleep(10)
                check_pending_command()

        except Exception as e:
            print(f"[Main] Lỗi không mong đợi: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
