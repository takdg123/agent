#!/bin/bash
# Check status of daily report

LOG_DIR="/home/dtak/torri/logs"

echo "=========================================================================="
echo "📊 TORRI Daily Report Status"
echo "=========================================================================="
echo ""

# Show next scheduled run
echo "⏰ Next Scheduled Run:"
echo "   $(grep -A 1 "TORRI Daily Report" <(crontab -l) | tail -1 | awk '{print $1, $2, $3, $4, $5}')"
echo ""

# Show last 5 runs
echo "📜 Recent Runs (Last 5):"
echo ""
ls -lt "$LOG_DIR"/daily_report_*.log 2>/dev/null | head -5 | while read -r line; do
    file=$(echo "$line" | awk '{print $NF}')
    date=$(echo "$line" | awk '{print $6, $7, $8}')
    size=$(echo "$line" | awk '{print $5}')
    
    # Check if successful
    if grep -q "✅ Daily report completed successfully" "$file" 2>/dev/null; then
        status="✅ SUCCESS"
    else
        status="❌ FAILED"
    fi
    
    echo "   $date - $size - $status"
    echo "      Log: $file"
done

echo ""

# Show latest log excerpt
LATEST_LOG=$(ls -t "$LOG_DIR"/daily_report_*.log 2>/dev/null | head -1)

if [ -n "$LATEST_LOG" ]; then
    echo "📄 Latest Log Excerpt:"
    echo "   File: $LATEST_LOG"
    echo ""
    echo "   Last 20 lines:"
    echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    tail -20 "$LATEST_LOG" | sed 's/^/   /'
    echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    echo "⚠️  No logs found yet"
fi

echo ""
echo "=========================================================================="
