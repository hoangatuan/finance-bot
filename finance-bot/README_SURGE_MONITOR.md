# Surge Monitor - Local Setup Guide

This guide explains how to run the surge monitoring system locally on your machine.

## Quick Start

### 1. Install Dependencies

```bash
cd finance-bot
pip install -r requirements.txt
```

**Note**: The `python-dotenv` package is included, which automatically loads variables from `.env` file. You don't need to export them manually!

### 2. Get Lark Webhook URL

1. Open your Lark group chat
2. Go to **Settings** (gear icon) > **BOTs**
3. Click **Add** to create a new bot
4. Copy the **Webhook URL** (format: `https://open.larksuite.com/open-apis/bot/v2/hook/...`)

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your Lark webhook:

```bash
cp env.example .env
```

Edit `.env` and set:
```bash
LARK_WEBHOOK_URL=https://open.larksuite.com/open-apis/bot/v2/hook/your_webhook_id
MONITORED_TICKERS=HPG,MBB,DXG,KDH,SSI  # Optional, can also use config file
SURGE_VOLUME_MULTIPLIER=1.2
SURGE_PRICE_CHANGE_PCT=3.0
```

### 4. Configure Monitored Tickers

Edit `config/monitored_tickers.yaml` to specify which tickers to monitor:

```yaml
tickers:
  - HPG
  - MBB
  - DXG
  - KDH
  - SSI

surge_thresholds:
  volume_multiplier: 1.2
  price_change_pct: 3.0
```

## Running the Monitor

### Option 1: Run Once (for testing)

Run a single monitoring cycle:

```bash
python run_surge_monitor.py --once
```

### Option 2: Run Continuously

Run the monitor continuously (checks every 30 minutes during trading hours):

```bash
python run_surge_monitor.py
```

The service will:
- Only run during trading hours (9am-11:30am and 1pm-2:45pm, Mon-Fri, GMT+7)
- Check for surges every 30 minutes
- Send Lark notifications when surges are detected
- Continue running until you stop it (Ctrl+C)

### Option 3: Schedule with Cron (Recommended)

Set up a cron job to run every 30 minutes during trading hours:

#### On macOS/Linux:

```bash
crontab -e
```

Add this line (runs every 30 minutes during trading hours, Mon-Fri):

```cron
0,30 9-11,13-14 * * 1-5 cd /path/to/finance-bot && /usr/bin/python3 run_surge_monitor.py --once
```

**Note**: 
- Replace `/path/to/finance-bot` with your actual path
- Replace `/usr/bin/python3` with your Python path (check with `which python3`)
- The cron expression `0,30 9-11,13-14 * * 1-5` means:
  - At minutes 0 and 30
  - During hours 9-11 (9am-11:30am) and 13-14 (1pm-2:45pm)
  - Every day of month
  - Every month
  - Monday to Friday (1-5)

#### Verify Cron Job:

```bash
crontab -l
```

## How It Works

1. **Trading Hours Check**: The monitor only runs during:
   - 9:00 AM - 11:30 AM (GMT+7)
   - 1:00 PM - 2:45 PM (GMT+7)
   - Monday to Friday

2. **Surge Detection**: For each ticker:
   - Fetches recent historical data (last 30 days)
   - Calculates volume and price indicators
   - Detects if volume is > threshold × average volume
   - Detects if price changed > threshold percentage

3. **Deep Analysis**: When a surge is detected:
   - Performs multi-timeframe analysis (1M, 1W, 1D, 4H)
   - Calculates technical indicators (RSI, SMA, MACD)
   - Analyzes support/resistance levels
   - Gets AI insights (if OpenAI API key is configured)

4. **Notification**: Sends formatted report to Lark group with:
   - Surge details (volume ratio, price change)
   - Technical indicators
   - AI analysis (if available)

5. **Deduplication**: Prevents duplicate alerts for the same ticker within 30 minutes

## Troubleshooting

### "No tickers configured"
- Check `config/monitored_tickers.yaml` has tickers listed
- Or set `MONITORED_TICKERS` environment variable

### "Lark webhook URL not configured"
- Make sure `LARK_WEBHOOK_URL` is set in `.env`
- Get the webhook URL from your Lark group: Settings > BOTs > Add Bot > Copy Webhook URL
- Or export it as an environment variable: `export LARK_WEBHOOK_URL=your_webhook_url`

### "Outside trading hours"
- This is normal behavior - the monitor only runs during trading hours
- Check the current time is within 9am-11:30am or 1pm-2:45pm (GMT+7), Monday-Friday

### Cron job not running
- Check cron service is running: `sudo service cron status` (Linux) or check System Preferences (macOS)
- Check cron logs: `/var/log/cron` (Linux) or Console.app (macOS)
- Verify Python path in cron job is correct
- Use absolute paths in cron job

## Testing

Test the monitor outside trading hours:

```bash
# Force run (ignores trading hours check)
python -c "
import asyncio
from src.scheduler.main import run_monitoring
asyncio.run(run_monitoring(verbose=True))
"
```

## Stopping the Service

If running continuously:
- Press `Ctrl+C` to stop

If using cron:
- Remove the cron job: `crontab -e` and delete the line
- Or disable it by commenting out the line with `#`

