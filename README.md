# LAB 01 — Raspberry Pi 4 + ThingsBoard Cloud

> Hướng dẫn từ lắp mạch, cài Python trên Raspberry Pi, kết nối ThingsBoard Cloud, tạo Dashboard, widget điều khiển động cơ bước bằng RPC và cảnh báo nhiệt độ.
> Phạm vi: **một Raspberry Pi 4**, DHT11, HC-SR04 và động cơ bước 28BYJ-48 qua module ULN2003A. Không cài ThingsBoard Server trên laptop.

## 1. Mục tiêu và luồng hoạt động

**Luồng telemetry:** DHT11 / HC-SR04 → Python trên Pi → MQTT TLS → ThingsBoard Cloud → Latest Telemetry → Dashboard/biểu đồ.

**Luồng điều khiển:** HC-SR04 đo khoảng cách; khi khoảng cách `< 20 cm`, Pi chạy động cơ bước qua ULN2003A, khi khoảng cách `>= 20 cm`, Pi dừng và nhả cuộn dây.

**Luồng cảnh báo:** Telemetry `temperature` → điều kiện `temperature > 30` trên ThingsBoard → tạo alarm `High Temperature`; khi `temperature <= 30` → xóa alarm theo rule.

Lưu ý: `stepperPosition` là số bước tương đối do phần mềm đếm, không phải vị trí đo bằng encoder. Khi dừng, cuộn dây được nhả để tránh nóng động cơ.

## 2. Phần cứng và đấu nối

### 2.1. Danh sách

- Raspberry Pi 4 (Raspberry Pi OS/Debian 13, đã có Internet và SSH).
- DHT11 module 3 chân (nếu dùng cảm biến DHT11 rời 4 chân, cần điện trở kéo lên DATA).
- HC-SR04; 1 điện trở **1 kΩ** và 1 điện trở **2 kΩ** để chia áp Echo.
- Động cơ bước 28BYJ-48 5 dây và module ULN2003A; cấp nguồn động cơ theo module, dây nối chung GND với Pi.
- Breadboard, dây jumper.

### 2.2. Bảng chân BCM (khác với số chân vật lý)

| Thiết bị | Chân | Nối đến |
|---|---|---|
| DHT11 module | VCC | Pi 3.3 V, **pin vật lý 1** |
| DHT11 module | DATA | **GPIO4**, pin vật lý 7 |
| DHT11 module | GND | Pi GND, pin vật lý 6 |
| HC-SR04 | VCC | Pi 5 V, pin vật lý 2 |
| HC-SR04 | TRIG | **GPIO23**, pin vật lý 16 |
| HC-SR04 | ECHO | **Qua chia áp** đến **GPIO24**, pin vật lý 18 |
| HC-SR04 | GND | Pi GND, pin vật lý 14 |
| ULN2003A | IN1 | **GPIO5**, pin vật lý 29 |
| ULN2003A | IN2 | **GPIO6**, pin vật lý 31 |
| ULN2003A | IN3 | **GPIO13**, pin vật lý 33 |
| ULN2003A | IN4 | **GPIO19**, pin vật lý 35 |
| ULN2003A | VCC / GND | 5 V / GND Pi |
| ULN2003A | Motor connector | Cắm nguyên giắc 5 dây của 28BYJ-48 |

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
.venv/bin/python -c "import paho.mqtt.client, gpiozero, board, adafruit_dht; print('IMPORT OK')"
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
[SENSOR] {'temperature': 29.0, 'humidity': 65.0, 'distance': 24.5}
```

Giá trị là **ví dụ**, không phải số đo thực tế. Dừng bằng `Ctrl+C`.

**Nếu không kết nối:** kiểm tra `TB_HOST`, token, Wi-Fi/Internet, ngày giờ Pi (`date`), DNS (`getent hosts thingsboard.cloud`) và kết nối TLS (`openssl s_client -connect thingsboard.cloud:8883 -servername thingsboard.cloud`). Không tắt xác thực TLS để chữa lỗi chứng chỉ.

## 6. Kiểm tra telemetry trên ThingsBoard

1. Để `./run.sh` chạy trên Pi.
2. Mở **Entities → Devices → RaspberryPi_Lab01**.
3. Chọn tab **Latest telemetry**.
4. Kiểm tra các key `temperature`, `humidity`, `distance` và thời điểm cập nhật.
5. Nếu DHT11 lỗi một chu kỳ, có thể chỉ thấy `distance`; kiểm tra log `[DHT11]` trên terminal.

JSON gửi bởi Pi có dạng:

```json
{"temperature":29.0,"humidity":65.0,"distance":24.5}
```

Topic MQTT: `v1/devices/me/telemetry`.

## 7. Tạo Dashboard giám sát

### 7.1. Tạo Dashboard

1. Vào **Dashboards** ở menu trái.
2. Chọn **Add dashboard** (hoặc dấu `+`).
3. Đặt tên **Raspberry Pi Lab01 Monitoring**.
4. Mở dashboard và chọn **Edit** (biểu tượng bút chì).
5. Chọn **Add widget** / **+**.

### 7.2. Thêm widget nhiệt độ

1. Trong thư viện widget, chọn nhóm phù hợp như **Cards**, **Latest values** hoặc **Digital gauges** (tên phụ thuộc phiên bản).
2. Chọn widget hiển thị **giá trị hiện tại** (Value card, Latest value, Digital gauge...).
3. Ở **Data source**: chọn **Entity** hoặc **Device**, chọn `RaspberryPi_Lab01`.
4. Ở **Data key**: loại **Timeseries** / **Telemetry**, key **`temperature`**.
5. Đặt nhãn `Nhiệt độ`, đơn vị `°C`, số thập phân `1`.
6. **Add/Apply** và lưu Dashboard.

**Lưu ý:** Nếu dropdown key trống, hãy xác nhận `temperature` đã xuất hiện trong **Latest telemetry** trước.

### 7.3. Thêm widget độ ẩm và khoảng cách

Lặp lại các bước trên:

| Widget | Data key | Đơn vị |
|---|---|---|
| Nhiệt độ | `temperature` | °C |
| Độ ẩm | `humidity` | % |
| Khoảng cách | `distance` | cm |

### 7.4. Thêm biểu đồ lịch sử

1. Trong Edit dashboard → **Add widget**.
2. Chọn nhóm **Charts** / **Time series**.
3. Chọn **Time series chart** hoặc **Line chart**.
4. Data source: `RaspberryPi_Lab01`.
5. Thêm Timeseries key `temperature` (có thể thêm `humidity`, nhưng nên dùng trục riêng nếu cần).
6. Chọn khoảng thời gian như **Last 1 hour** ở bộ chọn thời gian của dashboard/widget.
7. Apply → Save dashboard.

### 7.5. Hiển thị vị trí động cơ bước

1. Tạo thêm widget **Latest value**.
2. Data source: `RaspberryPi_Lab01`.
3. Data key type: **Attribute** (thường là client attribute).
4. Key: **`stepperPosition`**.
5. Đặt nhãn `Vị trí động cơ bước`, đơn vị `step`.

Key `stepperPosition` xuất hiện trong telemetry sau khi chương trình bắt đầu đọc cảm biến.

## 8. Điều khiển tự động theo khoảng cách

Code tự động đọc key `distance` từ HC-SR04:

| Khoảng cách | Động cơ |
|---|---|
| `< 20 cm` | Chạy liên tục |
| `>= 20 cm` | Dừng và nhả cuộn dây |

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

## 9. Tạo cảnh báo nhiệt độ trên ThingsBoard

Mục tiêu: **temperature > 30°C → tạo `High Temperature`**, khi `temperature <= 30°C` → clear alarm.

Tùy phiên bản ThingsBoard Cloud và quyền tài khoản, bạn có thể dùng **Device Profile Alarm Rules** hoặc **Rule Engine / Rule Chain**.

### 9.1. Cách ưu tiên: Alarm Rules trong Device Profile

1. Vào **Profiles → Device profiles** (hoặc **Device profiles**).
2. Mở profile mà `RaspberryPi_Lab01` đang sử dụng. Nếu là profile dùng chung, cân nhắc **tạo profile riêng cho Lab01** để không ảnh hưởng thiết bị khác.
3. Tìm tab **Alarm rules / Alarms**.
4. **Add alarm rule**:
   - Alarm type: `High Temperature`
   - Severity: `Warning`
   - Create condition: telemetry `temperature` **greater than 30**
   - Clear condition: telemetry `temperature` **less than or equal to 30**
5. Lưu profile và xác nhận `RaspberryPi_Lab01` được gán profile này.
6. Trên Dashboard, Add widget → nhóm **Alarms** → chọn **Alarms table** / widget danh sách alarm; data source là `RaspberryPi_Lab01`.

### 9.2. Nếu không thấy Alarm Rules

Trong **Rule Engine**, cần rule chain xử lý **POST_TELEMETRY** từ thiết bị, kiểm tra `temperature`, và các nhánh **Create alarm** / **Clear alarm**. Giao diện và node phụ thuộc phiên bản; không tự ý chỉnh rule chain mặc định đang dùng cho các thiết bị khác. Có thể tạo chain riêng cho Lab01 và cấu hình routing phù hợp.

**Để demo mà không làm nóng cảm biến:** tạm đổi ngưỡng trên ThingsBoard thành thấp hơn nhiệt độ phòng, kiểm tra alarm xuất hiện, sau đó đặt lại `30°C`. Không cần sửa code Pi.
