# Automatic Daily Report Setup 🤖

## Quick Setup

Run the setup script:

```bash
cd /home/dtak/torri
./setup_daily_cron.sh
```

This will:
1. ✅ Create logs directory
2. ✅ Create wrapper script (handles Ollama startup)
3. ✅ Ask for schedule (default: 9 AM daily)
4. ✅ Set up cron job
5. ✅ Create monitoring script

## Schedule Options

When you run `./setup_daily_cron.sh`, you'll be asked:

```
⏰ When should the daily report run?

Choose an option:
  1) 9:00 AM daily (recommended)
  2) 8:00 AM daily
  3) 10:00 AM daily
  4) Custom time
```

**Recommended**: Option 1 (9:00 AM) - Gets papers published overnight

## What Gets Created

### 1. Wrapper Script
**`run_daily_report_cron.sh`**

Handles:
- Starting Ollama (if not running)
- Running the daily report
- Capturing logs
- Cleaning up old logs (30 day retention)

### 2. Cron Job

Automatically added to your crontab:

```bash
# TORRI Daily Report - 9:00 AM daily
0 9 * * * /home/dtak/torri/run_daily_report_cron.sh
```

### 3. Logs Directory

```
/home/dtak/torri/logs/
├── daily_report_20260715_090001.log
├── daily_report_20260716_090001.log
├── ollama_20260715_090001.log
└── ...
```

### 4. Monitoring Script
**`check_daily_report.sh`**

Shows:
- Next scheduled run
- Recent run history
- Latest log excerpt

## Testing

### Test Manually First

Before relying on cron, test manually:

```bash
cd /home/dtak/torri

# Test the wrapper script
./run_daily_report_cron.sh
```

This runs exactly what cron will run.

Check the log:
```bash
ls -lt logs/daily_report_*.log | head -1
tail -f logs/daily_report_*.log
```

### Test Cron Job

Run it immediately (don't wait for scheduled time):

```bash
# Get the cron command
crontab -l | grep TORRI -A 1

# Run it manually
/home/dtak/torri/run_daily_report_cron.sh
```

## Monitoring

### Check Status

```bash
cd /home/dtak/torri
./check_daily_report.sh
```

Output:
```
========================================================================
📊 TORRI Daily Report Status
========================================================================

⏰ Next Scheduled Run:
   0 9 * * * (9:00 AM daily)

📜 Recent Runs (Last 5):

   Jul 15 09:00 - 125K - ✅ SUCCESS
      Log: /home/dtak/torri/logs/daily_report_20260715_090001.log
   Jul 14 09:00 - 118K - ✅ SUCCESS
      Log: /home/dtak/torri/logs/daily_report_20260714_090001.log
   ...

📄 Latest Log Excerpt:
   ...
```

### View Logs

```bash
# Latest log
tail -50 logs/daily_report_*.log | tail -50

# Live monitoring (during scheduled run)
tail -f logs/daily_report_*.log

# All logs
ls -lh logs/
```

### Check Cron

```bash
# View crontab
crontab -l

# Edit if needed
crontab -e
```

## What Happens Daily

```
                Daily at 9:00 AM
                       ↓
┌──────────────────────────────────────────────────┐
│ 1. Cron triggers run_daily_report_cron.sh       │
└──────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────┐
│ 2. Check/Start Ollama                           │
│    - If not running: start it                   │
│    - Wait 10s for startup                       │
└──────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────┐
│ 3. Run Daily Report                             │
│    • Fetch papers from arXiv                    │
│    • Filter for GRB/kilonova                    │
│    • Analyze with 6 experts:                    │
│      - GRB Expert (AstroSage-70B)               │
│      - Kilonova Expert (AstroSage-70B)          │
│      - Astrophysicist (Qwen2.5:32B)             │
│      - Language Expert (Qwen2.5:32B)            │
│      - Critic (Qwen2.5:32B)                     │
│      - Writer (Qwen2.5:32B)                     │
│    • Validate report quality                    │
│    • Generate HTML                              │
└──────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────┐
│ 4. Send Email (if quality >= 70/100)            │
│    To: YOUR_EMAIL                               │
│    Subject: TORRI Multi-Expert Digest           │
└──────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────┐
│ 5. Save Logs                                    │
│    • Report: logs/daily_report_YYYYMMDD.log    │
│    • Ollama: logs/ollama_YYYYMMDD.log          │
│    • HTML: data/reports/expert_report_YYYYMMDD │
└──────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────┐
│ 6. Cleanup Old Logs (>30 days)                  │
└──────────────────────────────────────────────────┘
```

## Expected Behavior

### Successful Run

Log should show:
```
========================================================================
🚀 TORRI Daily Report - Automatic Run
========================================================================

✅ Ollama already running
📥 Fetching papers from arXiv RSS feeds...
✅ 8 relevant papers selected
🔬 Analyzing 8 papers with 6-expert system...
✅ Analyzed 8/8 papers
📄 Generating HTML report...
🔍 Validating report...
🟢 Overall Score: 87/100 (EXCELLENT)
📧 Sending email...
✅ Email sent successfully!

========================================================================
✅ Daily report completed successfully!
   Exit code: 0
========================================================================
```

### Typical Run Time

- Paper fetching: ~5-10s
- Analysis (8 papers × 6 experts): ~40-60 minutes
  - AstroSage-70B: ~2-3 min per paper × 2 experts
  - Qwen2.5:32B: ~1-2 min per paper × 4 experts
- Report generation: ~5s
- Email: ~2s

**Total**: ~45-65 minutes for 8 papers

## Troubleshooting

### No Email Received

Check:
1. Log file: `tail logs/daily_report_*.log`
2. Quality score: Must be >= 70/100
3. Email settings in `.env`:
   ```bash
   EMAIL_FROM=your_email@gmail.com
   EMAIL_PASSWORD=your_app_password
   EMAIL_TO=recipient@email.com
   ```

### Report Failed

Common issues:

1. **Ollama not running**
   ```bash
   # Check if Ollama started
   grep "Ollama" logs/daily_report_*.log
   
   # Check Ollama log
   tail logs/ollama_*.log
   ```

2. **Models not found**
   ```bash
   ollama list
   # Should show: astrosage:70b-q4_K_M, qwen2.5:32b
   ```

3. **Out of memory**
   ```bash
   nvidia-smi
   # Check if GPU has enough memory
   ```

4. **No papers found**
   ```
   ✅ 0 relevant papers selected
   ```
   - Normal on some days (no GRB/kilonova papers)
   - Check if arXiv is accessible

### Cron Not Running

Check cron status:
```bash
# Check if cron is running
systemctl status cron

# Check crontab
crontab -l

# Check syslog
grep CRON /var/log/syslog | tail
```

### Permission Issues

If logs show permission errors:
```bash
# Fix permissions
chmod +x /home/dtak/torri/run_daily_report_cron.sh
chmod +x /home/dtak/torri/run_daily_report_refactored.py

# Check log directory
ls -ld /home/dtak/torri/logs
```

## Customization

### Change Schedule

```bash
# Edit crontab
crontab -e

# Examples:
0 8 * * *    # 8 AM daily
0 20 * * *   # 8 PM daily
0 9 * * 1-5  # 9 AM weekdays only
0 9 * * 1,3,5 # 9 AM Mon, Wed, Fri only
```

### Change Email Recipient

Edit `.env`:
```bash
EMAIL_TO=new_recipient@email.com
```

### Adjust Quality Threshold

In `run_daily_report_refactored.py`, change:
```python
if quality_score >= 70:  # Change this threshold
    send_email()
```

### Keep More/Fewer Logs

In `run_daily_report_cron.sh`, change:
```bash
# Keep last 30 days (change to 90, 7, etc.)
find "$LOG_DIR" -name "daily_report_*.log" -mtime +30 -delete
```

## Disable Automatic Reports

### Temporary (skip next run)

```bash
# Comment out the cron job
crontab -e
# Add # before the TORRI line
```

### Permanent

```bash
# Remove from crontab
crontab -e
# Delete the TORRI lines

# Or use crontab -r to remove all cron jobs (careful!)
```

## Re-enable

```bash
# Just run setup again
./setup_daily_cron.sh
```

## Summary

✅ **Setup**: `./setup_daily_cron.sh`
✅ **Monitor**: `./check_daily_report.sh`
✅ **Logs**: `logs/daily_report_*.log`
✅ **Schedule**: Customizable (default 9 AM)
✅ **Automatic**: Runs daily, no intervention needed

After setup, the system will:
- ✅ Fetch papers daily at scheduled time
- ✅ Analyze with 6 expert agents
- ✅ Generate professional HTML reports
- ✅ Email results if quality is good
- ✅ Store everything in memory for learning
- ✅ Clean up old logs automatically

Set it and forget it! 🚀

---

**Next**: Run `./setup_daily_cron.sh` to get started!
