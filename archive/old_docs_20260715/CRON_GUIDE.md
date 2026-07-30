# Cron Setup Guide

## Check Current Status

```bash
cd /home/dtak/torri
./check_cron.sh
```

This will show:
- ✅/❌ Cron service status
- ✅/❌ TORRI cron jobs (if any)
- ✅/❌ File paths verification
- 📋 Log file contents
- 📝 Recommended cron entries

## Quick Setup

### Option 1: Automated (Recommended)

```bash
./quick_setup.sh
```

### Option 2: Manual

```bash
crontab -e
```

Add one of these lines:

**Daily at 10:00 AM:**
```cron
0 10 * * * cd /home/dtak/torri && /home/dtak/miniconda3/envs/torri/bin/python run_daily_report_ollama.py >> /home/dtak/torri/daily_report.log 2>&1
```

**Weekdays at 9:00 AM:**
```cron
0 9 * * 1-5 cd /home/dtak/torri && /home/dtak/miniconda3/envs/torri/bin/python run_daily_report_ollama.py >> /home/dtak/torri/daily_report.log 2>&1
```

**Twice daily (9 AM & 5 PM):**
```cron
0 9,17 * * * cd /home/dtak/torri && /home/dtak/miniconda3/envs/torri/bin/python run_daily_report_ollama.py >> /home/dtak/torri/daily_report.log 2>&1
```

## Verify Cron is Working

### List your cron jobs:
```bash
crontab -l
```

### Check cron service:
```bash
systemctl status cron
```

### View cron logs:
```bash
# Recent cron activity
grep CRON /var/log/syslog | tail -20

# TORRI specific
tail -f /home/dtak/torri/daily_report.log
```

### Test run manually:
```bash
cd /home/dtak/torri
/home/dtak/miniconda3/envs/torri/bin/python run_daily_report_ollama.py
```

## Cron Syntax Reference

```
* * * * * command
│ │ │ │ │
│ │ │ │ └─── Day of week (0-7, 0 or 7 = Sunday)
│ │ │ └───── Month (1-12)
│ │ └─────── Day of month (1-31)
│ └───────── Hour (0-23)
└─────────── Minute (0-59)
```

### Examples:

```cron
# Every day at 10:00 AM
0 10 * * *

# Every weekday at 9:00 AM
0 9 * * 1-5

# Every 6 hours
0 */6 * * *

# Twice a day (9 AM and 5 PM)
0 9,17 * * *

# First day of month at 8 AM
0 8 1 * *
```

## Troubleshooting

### Cron job not running?

1. **Check cron is running:**
   ```bash
   systemctl status cron
   ```

2. **Check your crontab:**
   ```bash
   crontab -l
   ```

3. **Check paths are absolute:**
   ```bash
   # Good (absolute paths):
   0 10 * * * cd /home/dtak/torri && /home/dtak/miniconda3/envs/torri/bin/python run_daily_report_ollama.py
   
   # Bad (relative paths):
   0 10 * * * cd torri && python run_daily_report_ollama.py
   ```

4. **Check log file:**
   ```bash
   tail -f /home/dtak/torri/daily_report.log
   ```

5. **Test manually:**
   ```bash
   cd /home/dtak/torri
   /home/dtak/miniconda3/envs/torri/bin/python run_daily_report_ollama.py
   ```

### No output in log?

Make sure you redirect both stdout and stderr:
```cron
... >> /home/dtak/torri/daily_report.log 2>&1
```

### Environment variables not working?

Cron has minimal environment. Set them explicitly:
```cron
0 10 * * * cd /home/dtak/torri && PATH=/home/dtak/miniconda3/envs/torri/bin:$PATH /home/dtak/miniconda3/envs/torri/bin/python run_daily_report_ollama.py >> daily_report.log 2>&1
```

## Remove Cron Job

```bash
crontab -e

# Delete or comment out the line:
# 0 10 * * * cd /home/dtak/torri && ...
```

Or remove all:
```bash
crontab -r
```

## Check If Job Ran Today

```bash
# Check log file
ls -lh /home/dtak/torri/daily_report.log

# Check generated reports
ls -lht /home/dtak/torri/data/reports/ | head -5
```

---

**Quick check:** Run `./check_cron.sh` to see your status!
