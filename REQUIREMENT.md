Bot cảnh báo chứng khoán VN — Kế hoạch triển khai 
Mục tiêu: Thu thập dữ liệu giá cổ phiếu Việt Nam (ưu tiên miễn phí), tính một số chỉ báo kỹ thuật cơ bản, và gửi cảnh báo (Telegram/Email) khi điều kiện được thỏa.

⸻

0) Phạm vi & Ưu tiên
    •    Dữ liệu: vnstock
    •    Chỉ báo: SMA(20,50), RSI(14), MACD(12,26,9), Volume tăng/giảm, ... 
    •    Cảnh báo: Điều kiện đơn giản (ví dụ RSI < 30; cắt SMA20; MACD cắt signal).
    •    Lưu trữ: SQLite (file-based, nhẹ).
    •    Tự động hóa: Cron/schedule chạy định kỳ (5–15 phút phiên, 1h/ngoài giờ).

⸻

1) Kiến trúc tổng quan

CLI / Scheduler ──▶ Fetcher (vnstock)
                      │
                      ├─▶ Cache/DB (SQLite)
                      │
                      ├─▶ Indicator Engine (pandas + talib/pandas-ta)
                      │
                      └─▶ Rule Engine (alert conditions)
                               │
                               └─▶ Notifier (Telegram / Email)

1.1 Thư viện chính
    •    pandas, numpy
    •    vnstock
    •    pandas-ta hoặc TA-Lib (ưu tiên pandas-ta vì cài đặt nhẹ)
    •    sqlalchemy + sqlite3
    •    python-telegram-bot hoặc telegram/LARK
    •    schedule (nếu không dùng cron)
    •    tenacity (retry), ratelimit/token-bucket tự viết (giới hạn API)

1.2 Cấu trúc thư mục

project-root/
├─ README.md
├─ REQUIREMENT.md
├─ .env.example
├─ requirements.txt
├─ config/
│   ├─ tickers.yaml            # danh sách mã theo sàn/ngành
│   ├─ rules.yaml              # cấu hình chỉ báo & ngưỡng cảnh báo
│   └─ scheduler.yaml          # tần suất chạy theo thời gian/phiên
├─ data/
│   └─ stocks.db               # SQLite database
├─ src/
│   ├─ main.py                 # entrypoint CLI
│   ├─ scheduler.py            # cron/schedule loop
│   ├─ fetcher/
│   │   ├─ yfinance_fetcher.py
│   │   └─ vnstock_fetcher.py
│   ├─ store/
│   │   ├─ db.py               # session, migrations nhẹ
│   │   └─ models.py           # ORM models
│   ├─ indicators/
│   │   └─ ta.py               # SMA/RSI/MACD...
│   ├─ rules/
│   │   └─ engine.py           # evaluate conditions -> signals
│   ├─ notify/
│   │   ├─ telegram.py
│   │   └─ emailer.py
│   ├─ utils/
│   │   ├─ logging.py
│   │   ├─ rate_limit.py       # token bucket 60 req/min (vnstock)
│   │   └─ time_utils.py
│   └─ cli/
│       └─ commands.py         # sync, backfill, run-once, test-alert

⸻

2) Cấu hình & Bí mật
    •    Tạo file .env dựa trên .env.example:

# .env.example
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
DB_PATH=./data/stocks.db
YF_TIMEOUT=15
VNSTOCK_ENABLE=false
MARKET=VN

    •    config/tickers.yaml ví dụ:

exchanges:
  HSX: ["VNM", "HPG", "VCB"]
  HNX: ["PVS", "SHS"]
  UPCOM: []

    •    config/rules.yaml ví dụ:

indicators:
  sma:
    periods: [20, 50]
  rsi:
    period: 14
  macd:
    fast: 12
    slow: 26
    signal: 9
rules:
  - name: rsi_oversold
    expr: "rsi_14 < 30"
    notify: telegram
  - name: close_cross_sma20_up
    expr: "close[-1] > sma_20[-1] and close[-2] <= sma_20[-2]"
    notify: telegram
  - name: macd_bullish_cross
    expr: "macd[-1] > macd_signal[-1] and macd[-2] <= macd_signal[-2]"
    notify: telegram

    •    config/scheduler.yaml ví dụ:

# phút: tần suất fetch phiên giao dịch (09:00–15:00 GMT+7)
intraday_minutes: 5
# phút: tần suất fetch ngoài giờ (cache/backfill)
off_hours_minutes: 60
trading_days: ["Mon","Tue","Wed","Thu","Fri"]


⸻

3) Thiết kế Database (SQLite)

3.1 Bảng & Chỉ mục
    •    stock_prices
    •    id (PK), ticker, date (DATE), open, high, low, close, volume, source (“yf”|“vnstock”), ingested_at (DATETIME)
    •    Index: (ticker, date), source
    •    indicators
    •    id (PK), ticker, date, name (“sma_20”/“rsi_14”/“macd”/“macd_signal”), value (REAL)
    •    Unique: (ticker,date,name)
    •    alerts
    •    id (PK), ticker, date, rule, status (“new”|“sent”), sent_at, detail (JSON)
    •    meta
    •    key (PK), value (TEXT)  # dùng cho version/migration nhẹ

3.2 ERD đơn giản

stock_prices (1) ──▶ (N) indicators (theo ticker+date)
             └──▶ (N) alerts

3.3 Chính sách làm mới dữ liệu
    •    Cache-first: chỉ fetch khi thiếu phiên/thiếu ngày.
    •    Backfill: lùi 2–3 năm lịch sử khi lần đầu thêm ticker.
    •    Refresh: endpoint CLI run --refresh <ticker> --days 30 để ép cập nhật 30 ngày gần nhất.

⸻

4) Fetcher & Rate Limiting

- Sử dụng vnstock finance để fetch data

⸻

5) Indicator Engine
    •    Input: dataframe có cột open, high, low, close, volume, date.
    •    Tính toán:
    •    sma_20, sma_50
    •    rsi_14
    •    macd, macd_signal, macd_hist
    •    Output: ghi vào bảng indicators (upsert theo ticker,date,name).

Pseudo-code:

prices = load_prices(ticker)
ind = {}
ind["sma_20"] = ta.sma(prices.close, length=20)
ind["sma_50"] = ta.sma(prices.close, length=50)
ind["rsi_14"] = ta.rsi(prices.close, length=14)
macd = ta.macd(prices.close, fast=12, slow=26, signal=9)
ind["macd"], ind["macd_signal"], ind["macd_hist"] = macd["MACD_12_26_9"], macd["MACDs_12_26_9"], macd["MACDh_12_26_9"]
write_indicators(ticker, prices.date, ind)


⸻

6) Rule Engine (đánh giá tín hiệu)
    •    Đọc rules.yaml, parse expr.
    •    Hỗ trợ index [-1], [-2] để so sánh 2 phiên gần nhất.
    •    Trả về danh sách signals với lý do & dữ liệu kèm theo.

Ví dụ đánh giá:

ctx = {
  "close": series_close,
  "sma_20": series_sma20,
  "rsi_14": series_rsi,
  "macd": series_macd,
  "macd_signal": series_sig,
}
if eval_expr("close[-1] > sma_20[-1] and close[-2] <= sma_20[-2]", ctx):
    emit_signal(ticker, "close_cross_sma20_up", detail={...})

Chống lặp cảnh báo: kiểm tra alerts cho rule+ticker+date. Nếu đã sent, bỏ qua.

⸻

7) Notifier (Telegram/Email)

7.1 Telegram
    •    Tạo bot @BotFather → lấy TELEGRAM_BOT_TOKEN.
    •    Lấy TELEGRAM_CHAT_ID từ @userinfobot hoặc bằng API.
    •    Payload gợi ý:

📈 [VNM] RSI(14)=28.4 < 30 (Oversold)
Close: 64,500  | SMA20: 65,200 | Time: 2025-08-26 14:30

7.2 Email (tùy chọn)
    •    SMTP Gmail app password hoặc dịch vụ khác.

⸻

8) Scheduler
    •    Hai mode: intraday và off_hours.
    •    Xác định giờ phiên VN (GMT+7).
    •    Loop:
    1.    Nạp tickers từ tickers.yaml.
    2.    Fetch (cache-aware) → update DB.
    3.    Tính chỉ báo.
    4.    Đánh giá rule → gửi alert.
    5.    Sleep theo scheduler.yaml.

CLI ví dụ:

python -m src.main run --mode intraday
python -m src.main backfill --tickers HSX --years 3
python -m src.main test-alert --ticker VNM --rule rsi_oversold


⸻

10) Hiệu năng & Độ tin cậy
    •    Concurrency: tối đa 5–8 tickers song song.
    •    Rate limit: vnstock 60 req/phút (token bucket bắt buộc).
    •    Retry: tenacity (max 3, backoff 1,2,4s).
    •    Logging: INFO cho luồng chính, DEBUG khi bật --verbose.
    •    Idempotent: upsert theo (ticker,date).

⸻

11) Lộ trình triển khai (milestones)
    1.    M0 – Bootstrap (0.5–1 ngày)
    •    Tạo repo, cấu trúc thư mục, requirements.txt, .env.example.
    •    DB + models + migrations nhẹ.
    2.    M1 – Fetcher + DB (1 ngày)
    •    YF fetch daily + backfill; ghi stock_prices.
    3.    M2 – Indicators (0.5 ngày)
    •    Tính SMA/RSI/MACD; ghi indicators.
    4.    M3 – Rules + Telegram (0.5 ngày)
    •    Engine expr, gửi cảnh báo, chống lặp.
    5.    M4 – Scheduler + Intraday (0.5 ngày)
    •    Chạy định kỳ, phân biệt intraday/off-hours.
    6.    M5 – Hardening (0.5 ngày)
    •    Retry, rate limit vnstock, unit tests chính.
    7.    M6 – Mở rộng (tùy)
    •    Screeners, dashboard (Streamlit), thêm rules.

⸻

12) Prompt gợi ý để yêu cầu AI sinh mã (copy/paste)
    •    Sinh fetcher YF + lưu SQLite:
Viết module Python yfinance_fetcher.py với hàm fetch_daily(ticker: str, years: int) -> pd.DataFrame dùng yfinance.download. Chuẩn hóa cột open,high,low,close,volume,date. Thêm hàm upsert_prices(df, source="yf") ghi vào SQLite (stock_prices) qua SQLAlchemy, unique (ticker,date).
    •    Sinh indicators:
Viết module indicators/ta.py dùng pandas_ta tính sma_20,sma_50,rsi_14,macd,macd_signal,macd_hist từ dataframe giá. Thêm write_indicators(df) upsert vào bảng indicators theo (ticker,date,name).
    •    Sinh rule engine:
Viết rules/engine.py nhận rules.yaml, build context là pandas Series và evaluate biểu thức (chấp nhận [-1],[-2]). Trả về list tín hiệu và ghi vào alerts nếu chưa tồn tại bản ghi rule+ticker+date.
    •    Sinh notifier Telegram:
Viết notify/telegram.py với send_message(text: str) dùng TELEGRAM_BOT_TOKEN,TELEGRAM_CHAT_ID từ .env. Format thông điệp như ví dụ.
    •    Sinh scheduler:
Viết scheduler.py đọc scheduler.yaml, phân biệt intraday/off-hours theo giờ VN. Vòng lặp: load tickers → fetch (cache-aware) → tính chỉ báo → evaluate rules → notify → sleep N phút.

⸻

13) Ghi chú kỹ thuật quan trọng
    •    Đồng bộ timezone: chuẩn hoá date về YYYY-MM-DD (UTC hoặc GMT+7 nhất quán).
    •    Chặn alert lặp: theo ticker+rule+date.
    •    Sai lệch mã/ticker YF: mapping ticker_map.yaml nếu cần.
    •    Talib vs pandas-ta: nếu OS khó cài TA-Lib, dùng pandas-ta cho nhẹ.
    •    An toàn cấu hình: .env không commit lên repo public.

⸻

14) Danh sách việc (checklist)
    •    Tạo repo + scaffold thư mục
    •    Tạo SQLite + ORM models + indices
    •    YF fetch daily + backfill + upsert
    •    Indicators + upsert
    •    Rules + Telegram notify
    •    Scheduler intraday/off-hours
    •    Retry + rate limit (vnstock)
    •    Tests cơ bản
    •    Tài liệu hoá README + ví dụ chạy

⸻

15) Lệnh chạy mẫu

# cài đặt
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# backfill 2 năm HSX
python -m src.main backfill --exchange HSX --years 2

# chạy intraday 5 phút/lần
python -m src.main run --mode intraday --verbose

# kiểm tra rule & gửi thử
python -m src.main test-alert --ticker VNM --rule rsi_oversold


⸻

16) Hướng mở rộng tương lai
    •    Screeners theo FA (PE, ROE, NIM từ vnstock).
    •    Streamlit dashboard + biểu đồ nến/RSI/MACD.
    •    Lịch sử alert + thống kê win-rate theo rule.
    •    Thêm trailing stop/ATR và khung thời gian khác (1h/4h/1w).
    •    Đưa lên server (Railway/Fly.io/VPS) + healthcheck.
