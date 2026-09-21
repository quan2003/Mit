"""
Sensor Module - Đọc nhiệt độ và độ ẩm từ DHT22
Graceful fallback nếu không có phần cứng
"""
import os
import random

# Thử import DHT library
try:
    import adafruit_dht
    import board
    HAS_DHT = True
except ImportError:
    HAS_DHT = False

DHT_PIN = int(os.getenv("DHT_PIN", "4"))


class SensorReader:
    def __init__(self):
        self.dht = None
        if HAS_DHT:
            try:
                pin = getattr(board, f"D{DHT_PIN}")
                self.dht = adafruit_dht.DHT22(pin)
                print(f"[Sensor] DHT22 khởi tạo trên pin D{DHT_PIN}")
            except Exception as e:
                print(f"[Sensor] ⚠ Lỗi khởi tạo DHT22: {e} - dùng mock")
        else:
            print("[Sensor] Không có thư viện DHT - dùng mock data")

    def read(self) -> dict:
        """Đọc nhiệt độ và độ ẩm"""
        if self.dht:
            try:
                temp = self.dht.temperature
                humidity = self.dht.humidity
                if temp is not None and humidity is not None:
                    return {"temperature": round(temp, 1), "humidity": round(humidity, 1)}
            except RuntimeError as e:
                print(f"[Sensor] Lỗi đọc DHT22: {e}")

        # Mock data để test
        return {
            "temperature": round(random.uniform(25.0, 35.0), 1),
            "humidity": round(random.uniform(60.0, 85.0), 1),
        }

    def cleanup(self):
        if self.dht:
            self.dht.exit()
