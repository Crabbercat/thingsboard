# LAB 01 — Raspberry Pi 4 + ThingsBoard Cloud

> Hướng dẫn từ lắp mạch, cài Python trên Raspberry Pi, kết nối ThingsBoard Cloud và điều khiển động cơ bước theo khoảng cách.
> Phạm vi: **một Raspberry Pi 4**, HC-SR04 và động cơ bước 28BYJ-48 qua module ULN2003A. Không cài ThingsBoard Server trên laptop.

## 1. Mục tiêu và luồng hoạt động

**Luồng telemetry:** HC-SR04 → Python trên Pi → MQTT TLS → ThingsBoard Cloud → Latest Telemetry → Dashboard/biểu đồ.

**Luồng điều khiển:** HC-SR04 đo khoảng cách; khi khoảng cách `< 20 cm`, Pi chạy động cơ bước qua ULN2003A, khi khoảng cách `>= 20 cm`, Pi dừng và nhả cuộn dây.

Lưu ý: `stepperPosition` là số bước tương đối do phần mềm đếm, không phải vị trí đo bằng encoder. Khi dừng, cuộn dây được nhả để tránh nóng động cơ.

## 2. Phần cứng và đấu nối

### 2.1. Danh sách

- Raspberry Pi 4 (Raspberry Pi OS/Debian 13, đã có Internet và SSH).
- HC-SR04; 1 điện trở **1 kΩ** và 1 điện trở **2 kΩ** để chia áp Echo.
- Động cơ bước 28BYJ-48 5 dây và module ULN2003A; cấp nguồn động cơ theo module, dây nối chung GND với Pi.
- Breadboard, dây jumper.

### 2.2. Bảng chân BCM (khác với số chân vật lý)

| Thiết bị   | Chân           | Nối đến                                                     |
| ------------ | --------------- | -------------------------------------------------------------- |
| HC-SR04      | VCC             | Pi 5 V, pin vật lý 2                                         |
| HC-SR04      | TRIG            | **GPIO23**, pin vật lý 16                              |
| HC-SR04      | ECHO            | **Qua chia áp** đến **GPIO24**, pin vật lý 18 |
| HC-SR04      | GND             | Pi GND, pin vật lý 14                                        |
| ULN2003A     | IN1             | **GPIO5**, pin vật lý 29                               |
| ULN2003A     | IN2             | **GPIO6**, pin vật lý 31                               |
| ULN2003A     | IN3             | **GPIO13**, pin vật lý 33                              |
| ULN2003A     | IN4             | **GPIO19**, pin vật lý 35                              |
| ULN2003A     | VCC / GND       | 5 V / GND Pi                                                   |
| ULN2003A     | Motor connector | Cắm nguyên giắc 5 dây của 28BYJ-48                        |

**Mạch chia áp HC-SR04:**

```text
HC-SR04 ECHO (5 V)
        |
       1 kΩ
        |
        +---------------- GPIO24 (Pi)
        |
       2 kΩ
        |
       GND ---------------- GND Pi
```

Không nối ECHO 5 V trực tiếp vào GPIO Pi. Không cấp nguồn động cơ từ GPIO hoặc nguồn 3.3 V Pi. Tắt nguồn trước khi đấu dây. Nếu động cơ quay ngược, đổi thứ tự `STEPPER_PINS`.

Mặc định code dùng `STEPPER_PINS=5,6,13,19`, `STEP_DELAY=0.003` giây và `DISTANCE_THRESHOLD_CM=20`. Có thể ghi đè bằng biến môi trường.

## 3. Chuẩn bị ThingsBoard Cloud

1. Mở **https://thingsboard.cloud/entities/devices/all** và đăng nhập.
2. Vào **Entities → Devices** (tên menu có thể khác đôi chút theo giao diện).
3. Nhấn **Add device** / dấu `+` → đặt tên **RaspberryPi_Lab01** → lưu.
4. Mở thiết bị → **Credentials** / **Manage credentials** → lấy **Access Token**.
5. Giữ token bí mật. **Không đưa token vào ảnh chụp, GitHub hoặc slide**.

**Hostname của tài khoản này là `thingsboard.cloud`, không phải URL đầy đủ.**

## 4. Chuyển code lên Pi

Sau khi giải nén `thingsboard_lab01.zip` trên Windows, ví dụ thư mục:

`C:\Users\LENOVO\Desktop\thingsboard_lab01`

Trong **PowerShell Windows**:

```powershell
scp -r "C:\Users\LENOVO\Desktop\thingsboard_lab01" pi@192.168.137.144:/home/pi/
ssh pi@192.168.137.144
```

`192.168.137.144` chỉ là **ví dụ IP cũ**; thay bằng IP hiện tại của Pi. Nếu code đã nằm trên Pi, bỏ qua bước SCP.

## 5. Cài Python và thư viện trên Pi

Trong **terminal Raspberry Pi**:

```bash
cd ~/thingsboard_lab01
sudo apt update
sudo apt install -y python3-venv python3-dev python3-lgpio
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

Kiểm tra import:

```bash
.venv/bin/python -c "import paho.mqtt.client, gpiozero; print('IMPORT OK')"
```

Nếu lỗi `lgpio`/`RPi.GPIO`, kiểm tra phiên bản Debian và môi trường venv; `--system-site-packages` cho phép dùng gói GPIO đã cài bằng apt. **Không** cài pip bằng `sudo` vào Python hệ thống.

### 5.1. Cấu hình `.env`

```bash
cp .env.example .env
nano .env
```

Sửa thành:

```dotenv
TB_HOST=thingsboard.cloud
TB_PORT=8883
TB_TOKEN=PASTE_YOUR_DEVICE_ACCESS_TOKEN_HERE
SEND_INTERVAL=2
```

Thay `PASTE_YOUR_DEVICE_ACCESS_TOKEN_HERE` bằng token thực. Không nhập `https://` vào `TB_HOST`. Cổng `8883` dùng MQTT qua TLS; Pi cần Internet và thời gian hệ thống đúng để xác thực chứng chỉ.

Lưu nano: `Ctrl+O` → Enter → `Ctrl+X`.

### 5.2. Khởi chạy

```bash
chmod +x run.sh
./run.sh
```

Terminal dự kiến:

```text
[MQTT] Connected to thingsboard.cloud
Lab01 started. Ctrl+C to exit.
[SENSOR] {'distance': 24.5, 'motorRunning': False, 'stepperPosition': 0}
```

Giá trị là **ví dụ**, không phải số đo thực tế. Dừng bằng `Ctrl+C`.

**Nếu không kết nối:** kiểm tra `TB_HOST`, token, Wi-Fi/Internet, ngày giờ Pi (`date`), DNS (`getent hosts thingsboard.cloud`) và kết nối TLS (`openssl s_client -connect thingsboard.cloud:8883 -servername thingsboard.cloud`). Không tắt xác thực TLS để chữa lỗi chứng chỉ.

## 6. Kiểm tra telemetry trên ThingsBoard

1. Để `./run.sh` chạy trên Pi.
2. Mở **Entities → Devices → RaspberryPi_Lab01**.
3. Chọn tab **Latest telemetry**.
4. Kiểm tra các key `distance`, `motorRunning`, `stepperPosition` và thời điểm cập nhật.

JSON gửi bởi Pi có dạng:

```json
{"distance":24.5,"motorRunning":false,"stepperPosition":0}
```

Topic MQTT: `v1/devices/me/telemetry`.

## 7. Tạo Dashboard giám sát

### 7.1. Tạo Dashboard

1. Vào **Dashboards** ở menu trái.
2. Chọn **Add dashboard** (hoặc dấu `+`).
3. Đặt tên **Raspberry Pi Lab01 Monitoring**.
4. Mở dashboard và chọn **Edit** (biểu tượng bút chì).
5. Chọn **Add widget** / **+**.

### 7.2. Thêm widget giám sát

Lặp lại các bước trên:

| Widget | Data key | Đơn vị |
|---|---|---|
| Khoảng cách | `distance` | cm |
| Trạng thái động cơ | `motorRunning` | boolean |
| Vị trí động cơ | `stepperPosition` | step |

### 7.3. Thêm biểu đồ lịch sử

1. Trong Edit dashboard → **Add widget**.
2. Chọn nhóm **Charts** / **Time series**.
3. Chọn **Time series chart** hoặc **Line chart**.
4. Data source: `RaspberryPi_Lab01`.
5. Thêm Timeseries key `distance` hoặc `stepperPosition`.
6. Chọn khoảng thời gian như **Last 1 hour** ở bộ chọn thời gian của dashboard/widget.
7. Apply → Save dashboard.

### 7.4. Hiển thị vị trí động cơ bước

1. Tạo thêm widget **Latest value**.
2. Data source: `RaspberryPi_Lab01`.
3. Data key type: **Attribute** (thường là client attribute).
4. Key: **`stepperPosition`**.
5. Đặt nhãn `Vị trí động cơ bước`, đơn vị `step`.

Key `stepperPosition` xuất hiện trong telemetry sau khi chương trình bắt đầu đọc cảm biến.

## 8. Điều khiển tự động theo khoảng cách

Code tự động đọc key `distance` từ HC-SR04:

| Khoảng cách | Động cơ                |
| ------------- | ------------------------- |
| `< 20 cm`   | Chạy liên tục          |
| `>= 20 cm`  | Dừng và nhả cuộn dây |

Mỗi chu kỳ đo, telemetry gửi thêm:

```json
{"distance":15.2,"motorRunning":true,"stepperPosition":42}
```

Ngưỡng có thể thay đổi bằng biến môi trường:

```dotenv
DISTANCE_THRESHOLD_CM=20
```

Nếu cần kiểm tra thủ công qua MQTT RPC, method `setStepperRunning` nhận:

```json
{"method":"setStepperRunning","params":{"running":true}}
```

Lệnh này chỉ có tác dụng tạm thời; ở lần đo khoảng cách kế tiếp, logic tự động sẽ đặt lại trạng thái theo ngưỡng 20 cm.
