# Báo Cáo Kỹ Thuật: Hệ Thống Phát Hiện Bệnh Cây Mít Thông Minh

## 1. Tổng Quan Hệ Thống

Hệ thống IoT + AI phát hiện bệnh cây Mít tự động gồm 3 tầng:
- **Edge Layer**: Jetson Nano thu thập ảnh + cảm biến
- **Cloud Layer**: AI phân tích bệnh + lưu trữ dữ liệu
- **Application Layer**: Web/App giám sát và điều khiển

---

## 2. Stack Công Nghệ

### 🔧 Edge Device (Jetson Nano)

| Thành phần | Công nghệ | Mô tả |
|---|---|---|
| Camera | Raspberry Pi CM3+ / USB Cam | Chụp ảnh lá, thân cây |
| Cảm biến | DHT22 (GPIO) | Đo nhiệt độ, độ ẩm |
| Runtime | Python 3.8+ | Điều phối toàn bộ |
| Giao tiếp | MQTT / REST API (HTTPS) | Gửi dữ liệu lên Cloud |
| Điều khiển | GPIO + Relay Module | Bật/tắt Light System |
| Tự động hóa | Cron Job / APScheduler | Chụp ảnh định kỳ |

### ☁️ Cloud Backend

| Thành phần | Công nghệ | Mô tả |
|---|---|---|
| API Server | **FastAPI** (Python) | Nhận ảnh, trả kết quả |
| AI Model | **YOLO11-cls** | Phân loại 4 bệnh cây Mít |
| Database | **PostgreSQL** | Lưu lịch sử, kết quả |
| File Storage | **MinIO / S3** | Lưu trữ ảnh |
| Message Queue | **MQTT Broker** (Mosquitto) | Real-time communication |
| Deploy | **Docker + Nginx** | Container hóa dễ scale |

### 🌐 Web/App

| Thành phần | Công nghệ | Mô tả |
|---|---|---|
| Frontend | **React.js / Next.js** | Dashboard giám sát |
| Charts | **Chart.js / Recharts** | Biểu đồ tỉ lệ bệnh |
| Real-time | **WebSocket / Socket.io** | Cập nhật live |
| Mobile | **React Native** (tùy chọn) | App điện thoại |

### 🤖 AI/ML

| Thành phần | Công nghệ |
|---|---|
| Framework | **Ultralytics YOLO11** |
| Ngôn ngữ | Python |
| Dataset | 17,728 ảnh (4 class, đã augment) |
| Classes | `pink_disease`, `stem_cracking_gummosis`, `batocera_rufomaculata`, `stripe_canker` |
| Input size | 224×224 px |

---

## 3. Kiến Trúc Triển Khai

```
┌──────────────────────────────────────────────────────┐
│                   CLOUD SERVER                        │
│  ┌─────────────┐   ┌──────────────┐   ┌───────────┐  │
│  │  FastAPI    │   │  YOLO11-cls  │   │PostgreSQL │  │
│  │  (REST API) │──►│  Inference   │   │ Database  │  │
│  └──────┬──────┘   └──────────────┘   └───────────┘  │
│         │                  ▲                ▲         │
│         └──────────────────┴────────────────┘        │
│                                                       │
│  ┌─────────────────────────────────────────────────┐  │
│  │  Web Dashboard (Next.js)                        │  │
│  │  - Xem kết quả phát hiện bệnh                  │  │
│  │  - Lịch sử + biểu đồ thống kê                 │  │
│  │  - Điều khiển đèn từ xa                        │  │
│  └─────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
                           ▲
                    HTTPS / MQTT
                           ▼
┌──────────────────────────────────────────────────────┐
│                JETSON NANO (Edge)                     │
│                                                       │
│  Camera CM3+ ──► Capture ──► Gửi API ──► Nhận kết quả│
│                                               │       │
│  DHT22 Sensor ──────────────────────────────►        │
│                                               │       │
│                              ┌────────────────┘       │
│                              ▼                        │
│                    Relay → Light System               │
└──────────────────────────────────────────────────────┘
```

---

## 4. Luồng Hoạt Động Chi Tiết

### 🔁 Chu trình tự động (mỗi N phút)

```
1. [Jetson Nano] Chụp ảnh bằng Camera CM3+
2. [Jetson Nano] Đọc nhiệt độ, độ ẩm từ DHT22
3. [Jetson Nano] POST ảnh + sensor data → Cloud API
4. [Cloud API]   Chạy YOLO11 → phát hiện bệnh
5. [Cloud API]   Lưu kết quả vào PostgreSQL + ảnh vào Storage
6. [Cloud API]   Trả kết quả về Jetson Nano
7. [Jetson Nano] Nhận kết quả → quyết định bật/tắt đèn (nếu cần)
8. [Cloud API]   Push notification → Web/App qua WebSocket
9. [Web/App]     Hiển thị real-time kết quả cho người dùng
```

---

## 5. Tính Năng Hệ Thống

### ✅ Core Features
- Phát hiện 4 loại bệnh cây Mít tự động
- Giám sát môi trường (nhiệt độ, độ ẩm) real-time
- Dashboard xem ảnh + kết quả phân loại
- Lịch sử phát hiện bệnh theo thời gian
- Điều khiển hệ thống đèn từ xa (Web/App)
- Cảnh báo khi phát hiện bệnh (push notification)

### 🔔 Alert System
| Bệnh | Mức độ | Hành động |
|------|--------|-----------|
| `pink_disease` | 🔴 Cao | Alert ngay + ghi log |
| `stem_cracking_gummosis` | 🔴 Cao | Alert ngay + ghi log |
| `batocera_rufomaculata` | 🟡 TB | Alert + khuyến nghị |
| `stripe_canker` | 🟡 TB | Alert + khuyến nghị |

---

## 6. Kế Hoạch Triển Khai

| Giai đoạn | Nội dung | Thời gian |
|---|---|---|
| **Phase 1** | Train YOLO11 + đánh giá model | 1-2 tuần |
| **Phase 2** | Xây dựng Cloud API (FastAPI) | 1 tuần |
| **Phase 3** | Lập trình Jetson Nano client | 1 tuần |
| **Phase 4** | Xây dựng Web Dashboard | 1-2 tuần |
| **Phase 5** | Tích hợp + test toàn hệ thống | 1 tuần |
| **Phase 6** | Deploy thực tế + fine-tune | Ongoing |

---

## 7. Yêu Cầu Phần Cứng

| Thiết bị | Thông số |
|---|---|
| Jetson Nano | 4GB RAM, CUDA support |
| Camera | Raspberry Pi CM3+ hoặc USB Cam 5MP+ |
| Sensor | DHT22 (Temperature + Humidity) |
| Relay Module | 1-2 channel (điều khiển đèn) |
| Cloud Server | Min 4 vCPU, 8GB RAM, GPU (tùy chọn) |

---

*Báo cáo được tạo bởi: TRƯƠNG TẤN NGHĨA*
