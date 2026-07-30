# Quick Start - Ollama Daily Reports

## 1. Start Ollama (Required)

**Option A: In a terminal (see logs)**
```bash
ollama serve
```
Keep this terminal open.

**Option B: Background mode**
```bash
nohup ollama serve > /home/dtak/torri/ollama.log 2>&1 &
```

Check if running:
```bash
curl http://localhost:11434/api/tags
```

## 2. One-Time Test

```bash
cd /home/dtak/torri
./run_daily_report_ollama.py
```

## 3. Weekly Test (Interactive)

```bash
./test_weekly.sh
```

Choose:
1. **Single test** - Run once now
2. **Daily cron** - Auto-run at 10 AM for a week
3. **7 reports** - Generate 7 reports in a row (simulated week)

## 4. Manual Cron Setup

```bash
crontab -e

# Add this line for daily 10 AM:
0 10 * * * cd /home/dtak/torri && ./run_daily_report_ollama.py >> /home/dtak/torri/daily_report.log 2>&1
```

## Check Logs

```bash
# Ollama logs (if background)
tail -f /home/dtak/torri/ollama.log

# Daily report logs (if cron)
tail -f /home/dtak/torri/daily_report.log

# Generated reports
ls -lh /home/dtak/torri/data/reports/
```

## Stop Ollama

```bash
# Find process
ps aux | grep ollama

# Kill it
pkill -f ollama

# Or use the stop script
./stop_ollama.sh
```

## Common Issues

### "Ollama not running"
```bash
ollama serve
```

### "No papers found"
The script fetches from multiple arXiv categories. If still empty, check your internet connection.

### "Email not sent"
Configure email in `.env`:
```bash
SENDER_EMAIL=your-gmail@gmail.com
SENDER_PASSWORD=your-app-password
RECIPIENT_EMAIL=recipient@example.com
```

## First Time Setup

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull model
./setup_ollama.sh

# 3. Start Ollama
ollama serve

# 4. Run test (in another terminal)
./run_daily_report_ollama.py
```

That's it! 🚀
