# Daily Report Setup - Complete Guide

## Quick Setup (5 minutes)

### Step 1: Start Ollama (Background)

```bash
cd /home/dtak/torri

# Start Ollama in background
nohup ollama serve > ollama.log 2>&1 &

# Verify it's running
curl http://localhost:11434/api/tags
```

### Step 2: Configure Email (Optional but Recommended)

Edit `/home/dtak/torri/.env`:

```bash
# Email settings
SENDER_EMAIL=your-gmail@gmail.com
SENDER_PASSWORD=your-app-password
RECIPIENT_EMAIL=your-email@example.com

# Paper settings
MAX_PAPERS=20
OLLAMA_MODEL=qwen2.5:7b
```

**Get Gmail App Password:**
1. Go to https://myaccount.google.com/apppasswords
2. Create new app password
3. Use that password (not your regular Gmail password)

### Step 3: Test Once

```bash
./run_daily_report_ollama.py
```

Check:
- Console output for errors
- `data/reports/` for HTML file
- Your email inbox

### Step 4: Set Up Daily Automation

```bash
crontab -e
```

Add this line (for 10:00 AM daily):

```bash
0 10 * * * cd /home/dtak/torri && /home/dtak/miniconda3/envs/torri/bin/python run_daily_report_ollama.py >> /home/dtak/torri/daily_report.log 2>&1
```

Save and exit.

## Verify Cron Setup

```bash
# List cron jobs
crontab -l

# Check cron service is running
sudo systemctl status cron
```

## Different Schedule Options

```bash
# Every day at 10:00 AM
0 10 * * * cd /home/dtak/torri && ./run_daily_report_ollama.py >> daily_report.log 2>&1

# Every weekday (Mon-Fri) at 9:00 AM
0 9 * * 1-5 cd /home/dtak/torri && ./run_daily_report_ollama.py >> daily_report.log 2>&1

# Twice a day (9 AM and 5 PM)
0 9,17 * * * cd /home/dtak/torri && ./run_daily_report_ollama.py >> daily_report.log 2>&1

# Every 6 hours
0 */6 * * * cd /home/dtak/torri && ./run_daily_report_ollama.py >> daily_report.log 2>&1
```

## Auto-Start Ollama on Boot (Optional)

### Option 1: Systemd Service

Create `/etc/systemd/system/ollama.service`:

```bash
sudo nano /etc/systemd/system/ollama.service
```

Content:
```ini
[Unit]
Description=Ollama Service
After=network.target

[Service]
Type=simple
User=dtak
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama
sudo systemctl status ollama
```

### Option 2: Cron @reboot

```bash
crontab -e

# Add this line:
@reboot nohup /usr/local/bin/ollama serve > /home/dtak/torri/ollama.log 2>&1 &
```

## Monitor and Troubleshoot

### Check Logs

```bash
# Daily report logs
tail -f /home/dtak/torri/daily_report.log

# Ollama logs
tail -f /home/dtak/torri/ollama.log

# System cron logs
grep CRON /var/log/syslog | tail -20
```

### Check Generated Reports

```bash
ls -lh /home/dtak/torri/data/reports/
```

### Test Email Separately

```bash
/home/dtak/miniconda3/envs/torri/bin/python test_email.py
```

### Check Ollama Status

```bash
# Is Ollama running?
curl http://localhost:11434/api/tags

# List models
ollama list

# Check processes
ps aux | grep ollama
```

## Weekly Test Mode

Run the interactive test:

```bash
./test_weekly.sh
```

Choose:
1. Single test run
2. Set up daily cron for 1 week
3. Generate 7 reports now

## Disable Daily Reports

```bash
# Remove from cron
crontab -e
# Delete the line with run_daily_report_ollama.py

# Or comment it out with #
# 0 10 * * * cd /home/dtak/torri && ./run_daily_report_ollama.py >> daily_report.log 2>&1
```

## Full Example Setup

```bash
# 1. Start Ollama in background
cd /home/dtak/torri
nohup ollama serve > ollama.log 2>&1 &

# 2. Wait a moment
sleep 5

# 3. Test run
./run_daily_report_ollama.py

# 4. Check report was generated
ls -lh data/reports/

# 5. Set up daily at 10 AM
(crontab -l 2>/dev/null; echo "0 10 * * * cd /home/dtak/torri && /home/dtak/miniconda3/envs/torri/bin/python run_daily_report_ollama.py >> /home/dtak/torri/daily_report.log 2>&1") | crontab -

# 6. Verify
crontab -l

echo "✅ Setup complete!"
```

## Expected Behavior

### Daily at 10:00 AM:
1. ✅ Fetch latest papers from arXiv (astro-ph.HE, kilonova, GRB)
2. ✅ Filter by keywords (kilonova, GRB, neutron star, etc.)
3. ✅ Analyze each paper with Ollama (Qwen2.5:7b)
4. ✅ Generate HTML report
5. ✅ Save to `data/reports/daily_report_YYYYMMDD.html`
6. ✅ Send email with report (if configured)
7. ✅ Log to `daily_report.log`

### What You'll Receive:
- **Email** with HTML report (if configured)
- **HTML file** in `data/reports/`
- **Paper summaries** with AI analysis
- **Log file** for debugging

## Customization

See `RESEARCH_FOCUS.md` for changing research topics.

---

**Setup Time:** ~5 minutes  
**Daily Runtime:** ~2-5 minutes (depends on number of papers)  
**Cost:** $0 (all local)
