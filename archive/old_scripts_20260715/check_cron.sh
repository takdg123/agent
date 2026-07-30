#!/bin/bash

# Check cron configuration for TORRI

echo "🔍 TORRI Cron Configuration Check"
echo "="*70

# 1. Check cron service
echo ""
echo "1️⃣  Cron Service Status:"
if systemctl is-active --quiet cron 2>/dev/null || systemctl is-active --quiet crond 2>/dev/null; then
    echo "   ✅ Cron service is running"
else
    echo "   ❌ Cron service is NOT running"
    echo "   Start with: sudo systemctl start cron"
fi

# 2. Check user's crontab
echo ""
echo "2️⃣  Current Crontab Entries:"
if crontab -l 2>/dev/null | grep -q "torri\|run_daily_report"; then
    echo "   ✅ TORRI cron jobs found:"
    crontab -l 2>/dev/null | grep -E "torri|run_daily_report" | while read -r line; do
        echo "      $line"
    done
else
    echo "   ⚠️  No TORRI cron jobs found"
    echo ""
    echo "   To add a daily job (10:00 AM):"
    echo "   crontab -e"
    echo "   # Add this line:"
    echo "   0 10 * * * cd /home/dtak/torri && /home/dtak/miniconda3/envs/torri/bin/python run_daily_report_ollama.py >> /home/dtak/torri/daily_report.log 2>&1"
fi

# 3. Verify paths exist
echo ""
echo "3️⃣  File Paths Verification:"
if [ -f "/home/dtak/torri/run_daily_report_ollama.py" ]; then
    echo "   ✅ Script exists: run_daily_report_ollama.py"
else
    echo "   ❌ Script NOT found: run_daily_report_ollama.py"
fi

if [ -f "/home/dtak/miniconda3/envs/torri/bin/python" ]; then
    echo "   ✅ Python exists: torri environment"
else
    echo "   ❌ Python NOT found in torri environment"
fi

if [ -d "/home/dtak/torri" ]; then
    echo "   ✅ Directory exists: /home/dtak/torri"
else
    echo "   ❌ Directory NOT found: /home/dtak/torri"
fi

# 4. Check log file
echo ""
echo "4️⃣  Log File Check:"
if [ -f "/home/dtak/torri/daily_report.log" ]; then
    size=$(stat -f%z "/home/dtak/torri/daily_report.log" 2>/dev/null || stat -c%s "/home/dtak/torri/daily_report.log" 2>/dev/null)
    echo "   ✅ Log file exists (size: $size bytes)"
    echo ""
    echo "   Last 10 lines:"
    tail -10 "/home/dtak/torri/daily_report.log" 2>/dev/null | sed 's/^/      /'
else
    echo "   ℹ️  Log file not created yet (will be created on first run)"
fi

# 5. Test manual run
echo ""
echo "5️⃣  Test Manual Run:"
echo "   Run this to test:"
echo "   cd /home/dtak/torri && /home/dtak/miniconda3/envs/torri/bin/python run_daily_report_ollama.py"

# 6. Recommended cron format
echo ""
echo "6️⃣  Recommended Cron Entry:"
echo "   Daily at 10:00 AM:"
echo "   0 10 * * * cd /home/dtak/torri && /home/dtak/miniconda3/envs/torri/bin/python run_daily_report_ollama.py >> /home/dtak/torri/daily_report.log 2>&1"
echo ""
echo "   Weekdays at 9:00 AM:"
echo "   0 9 * * 1-5 cd /home/dtak/torri && /home/dtak/miniconda3/envs/torri/bin/python run_daily_report_ollama.py >> /home/dtak/torri/daily_report.log 2>&1"

# 7. Summary
echo ""
echo "="*70
echo "Summary:"
crontab -l 2>/dev/null | grep -q "torri\|run_daily_report" && echo "✅ Cron configured" || echo "⚠️  Cron NOT configured - run './quick_setup.sh' or add manually"
echo ""
