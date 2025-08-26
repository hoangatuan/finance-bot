# Kế hoạch triển khai Bot cảnh báo chứng khoán VN

## Mục tiêu
Thu thập dữ liệu giá cổ phiếu Việt Nam, tính chỉ báo kỹ thuật cơ bản, và gửi cảnh báo (Telegram/Email) khi điều kiện được thỏa.

---

## Milestone 1: Implement logic gọi APIs ✅

### Cấu trúc dự án
- [x] Tạo cấu trúc thư mục theo yêu cầu
- [x] Tạo `requirements.txt` với các dependencies cần thiết
- [x] Tạo `.env.example` với các biến môi trường
- [ ] Tạo `README.md` với hướng dẫn cài đặt và sử dụng

### VNStock API Integration
- [x] Nghiên cứu vnstock API documentation
- [x] Tạo `src/fetcher/vnstock_fetcher.py`
- [x] Implement hàm `fetch_historical()` với interval support
- [x] Chuẩn hóa dữ liệu (open, high, low, close, volume, date)
- [x] Implement `fetch_realtime()` cho real-time data
- [x] Support multiple sources (VCI) với fallback
- [x] Factory pattern cho scalable architecture

### Rate Limiting & Retry
- [x] Implement rate limiting (60 req/phút) trong VNStock fetcher
- [x] Implement retry logic với tenacity (max 3, backoff 1,2,4s)
- [x] Tích hợp rate limiting vào fetcher
- [x] Async support với asyncio

### ✅ Đã hoàn thành:
- **Base Fetcher**: Abstract class với interface chung
- **VNStock Fetcher**: Historical + Real-time data fetching
- **Factory Pattern**: Scalable architecture cho multiple data sources
- **Rate Limiting**: 60 req/phút với async support
- **Retry Logic**: Exponential backoff với tenacity
- **Data Normalization**: Standardized format cho historical và real-time data
- **Interval Support**: 1m, 5m, 15m, 30m, 1H, 1D, 1W, 1M
- **Multiple Sources**: VCI, TCBS, MSN với fallback mechanism
- **Trading Status**: Kiểm tra giờ giao dịch VN (GMT+7)

### 🔄 Còn lại:
- README.md với hướng dẫn cài đặt và sử dụng

---

## Milestone 2: Technical Analysis Logic

### Indicator Engine
- [ ] Tạo `src/indicators/ta.py`
- [ ] Implement tính toán SMA(20, 50)
- [ ] Implement tính toán RSI(14)
- [ ] Implement tính toán MACD(12, 26, 9)
- [ ] Implement phân tích khối lượng (volume increase/decrease)
- [ ] Tạo hàm `write_indicators()` để upsert vào bảng indicators

### Data Processing Pipeline
- [ ] Tạo pipeline xử lý dữ liệu từ raw prices đến indicators
- [ ] Implement cache-aware logic (chỉ tính khi cần thiết)
- [ ] Tối ưu hóa performance cho việc tính toán indicators

---

## Milestone 3: Data Storage

### Database Design & Models
- [ ] Thiết kế schema SQLite với các bảng: `stock_prices`, `indicators`, `alerts`, `meta`
- [ ] Tạo SQLAlchemy models (`src/store/models.py`)
- [ ] Tạo database connection và session management (`src/store/db.py`)
- [ ] Tạo database migrations nhẹ

### Data Management
- [ ] Implement cache-first approach: chỉ fetch khi thiếu phiên/thiếu ngày
- [ ] Implement backfill logic: lùi 2-3 năm lịch sử khi lần đầu thêm ticker
- [ ] Implement refresh endpoint: ép cập nhật dữ liệu theo yêu cầu

---

## Milestone 4: Rule Engine & Alert System

### Rule Engine
- [ ] Tạo `src/rules/engine.py`
- [ ] Parse và load `config/rules.yaml`
- [ ] Implement expression evaluator hỗ trợ index [-1], [-2]
- [ ] Tạo context với pandas Series cho việc đánh giá

### Alert System
- [ ] Implement logic đánh giá rules và tạo signals
- [ ] Tạo bảng `alerts` để lưu trữ và chống lặp
- [ ] Tích hợp với rule engine
- [ ] Implement alert deduplication (theo ticker+rule+date)

---

## Milestone 5: Notification System

### Telegram Bot
- [ ] Tạo `src/notify/telegram.py`
- [ ] Implement `send_message(text: str)` 
- [ ] Format message theo template yêu cầu
- [ ] Tích hợp với rule engine
- [ ] Setup bot token và chat ID

### Email System (Optional)
- [ ] Tạo `src/notify/emailer.py`
- [ ] Implement SMTP email sending
- [ ] Tích hợp với rule engine
- [ ] Setup email credentials

---

## Milestone 6: Scheduler & Automation

### Scheduler System
- [ ] Tạo `src/scheduler.py`
- [ ] Implement intraday mode (5 phút/lần trong giờ giao dịch)
- [ ] Implement off-hours mode (60 phút/lần ngoài giờ giao dịch)
- [ ] Xác định giờ phiên VN (GMT+7)

### Main Automation Loop
- [ ] Tạo main loop: load tickers → fetch → indicators → rules → notify → sleep
- [ ] Tích hợp với scheduler configuration
- [ ] Implement concurrency (tối đa 5-8 tickers song song)
- [ ] Add health checks và monitoring

---

## Milestone 7: Command Line Interface

### CLI Implementation
- [ ] Tạo `src/cli/commands.py`
- [ ] Implement command `run --mode intraday/off-hours`
- [ ] Implement command `backfill --exchange HSX --years 2`
- [ ] Implement command `test-alert --ticker VNM --rule rsi_oversold`
- [ ] Implement command `refresh --ticker VNM --days 30`

### CLI Features
- [ ] Add verbose mode cho debugging
- [ ] Add help documentation cho mỗi command
- [ ] Implement proper error handling và user feedback

---

## Milestone 8: Documentation & Deployment

### Configuration Files
- [ ] Tạo `config/tickers.yaml` với danh sách mã chứng khoán
- [ ] Tạo `config/rules.yaml` với các rules mặc định
- [ ] Tạo `config/scheduler.yaml` với cấu hình thời gian

### Documentation
- [ ] Hoàn thiện README.md với examples
- [ ] Tạo hướng dẫn cài đặt chi tiết
- [ ] Tạo troubleshooting guide
- [ ] Tạo API documentation

### Deployment & Testing
- [ ] Tạo Dockerfile (optional)
- [ ] Tạo deployment scripts
- [ ] Setup monitoring và alerting
- [ ] Tạo unit tests cho các module chính
- [ ] Test end-to-end workflow

---

## Dependencies chính
- pandas, numpy
- vnstock
- pandas-ta
- sqlalchemy + sqlite3
- python-telegram-bot
- schedule
- tenacity

## Cấu trúc thư mục cuối cùng
```
project-root/
├─ README.md
├─ REQUIREMENT.md
├─ PLAN.md
├─ .env.example
├─ requirements.txt
├─ config/
│   ├─ tickers.yaml
│   ├─ rules.yaml
│   └─ scheduler.yaml
├─ data/
│   └─ stocks.db
└─ src/
    ├─ main.py
    ├─ scheduler.py
    ├─ fetcher/
    ├─ store/
    ├─ indicators/
    ├─ rules/
    ├─ notify/
    ├─ utils/
    └─ cli/
```

## Lệnh chạy mẫu
```bash
# Cài đặt
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Backfill dữ liệu
python -m src.main backfill --exchange HSX --years 2

# Chạy intraday
python -m src.main run --mode intraday --verbose

# Test alert
python -m src.main test-alert --ticker VNM --rule rsi_oversold
```

---

## Ghi chú quan trọng
- Đồng bộ timezone: chuẩn hóa về GMT+7
- Rate limit vnstock: 60 req/phút
- Chống alert lặp: theo ticker+rule+date
- Cache-first approach: chỉ fetch khi cần thiết
- Idempotent operations: upsert theo unique constraints
- Concurrency: tối đa 5-8 tickers song song
- Retry: tenacity (max 3, backoff 1,2,4s)
