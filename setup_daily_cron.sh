#!/bin/bash
# Setup automatic daily report with cron

set -e

echo "=========================================================================="
echo "⏰ Setting Up Automatic Daily Report"
echo "=========================================================================="
echo ""

TORRI_DIR="/home/dtak/torri"
PYTHON_BIN="/home/dtak/miniconda3/envs/torri/bin/python3"
SCRIPT="$TORRI_DIR/run_daily_report_refactored.py"
LOG_DIR="$TORRI_DIR/logs"

# Create logs directory
echo "📁 Creating logs directory..."
mkdir -p "$LOG_DIR"
echo "   ✅ Created: $LOG_DIR"
echo ""

# Check if script exists
if [ ! -f "$SCRIPT" ]; then
    echo "❌ Error: $SCRIPT not found!"
    exit 1
fi

echo "✅ Script found: $SCRIPT"
echo ""

# Ask for schedule
echo "⏰ When should the daily report run?"
echo ""
echo "Choose an option:"
echo "  1) 9:00 AM daily (recommended)"
echo "  2) 8:00 AM daily"
echo "  3) 10:00 AM daily"
echo "  4) Custom time"
echo ""
read -p "Enter choice (1-4): " choice

case $choice in
    1)
        CRON_TIME="0 9 * * *"
        TIME_DESC="9:00 AM daily"
        ;;
    2)
        CRON_TIME="0 8 * * *"
        TIME_DESC="8:00 AM daily"
        ;;
    3)
        CRON_TIME="0 10 * * *"
        TIME_DESC="10:00 AM daily"
        ;;
    4)
        echo ""
        read -p "Enter hour (0-23): " hour
        read -p "Enter minute (0-59): " minute
        CRON_TIME="$minute $hour * * *"
        TIME_DESC="${hour}:${minute} daily"
        ;;
    *)
        echo "❌ Invalid choice!"
        exit 1
        ;;
esac

echo ""
echo "📋 Selected schedule: $TIME_DESC"
echo ""

# Create wrapper script that ensures Ollama is running
WRAPPER_SCRIPT="$TORRI_DIR/run_daily_report_cron.sh"

echo "📝 Creating wrapper script..."

cat > "$WRAPPER_SCRIPT" << 'WRAPPER_EOF'
#!/bin/bash
# Cron wrapper for daily report
# Ensures Ollama is running and captures output

TORRI_DIR="/home/dtak/torri"
PYTHON_BIN="/home/dtak/miniconda3/envs/torri/bin/python3"
LOG_DIR="$TORRI_DIR/logs"
DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/daily_report_$DATE.log"

# Redirect all output to log file
exec > "$LOG_FILE" 2>&1

echo "=========================================================================="
echo "🚀 TORRI Daily Report - Automatic Run"
echo "=========================================================================="
echo ""
echo "📅 Date: $(date)"
echo "📁 Directory: $TORRI_DIR"
echo ""

# Check if Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    echo "🔄 Starting Ollama service..."
    nohup ollama serve > "$LOG_DIR/ollama_$DATE.log" 2>&1 &
    sleep 10
    echo "   ✅ Ollama started"
else
    echo "✅ Ollama already running"
fi

echo ""
echo "=========================================================================="
echo "📄 Running Daily Report"
echo "=========================================================================="
echo ""

# Change to torri directory
cd "$TORRI_DIR"

# Run the report
$PYTHON_BIN run_daily_report_refactored.py

EXIT_CODE=$?

echo ""
echo "=========================================================================="
echo "📊 Completion Status"
echo "=========================================================================="

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Daily report completed successfully!"
    echo "   Exit code: $EXIT_CODE"
else
    echo "❌ Daily report failed!"
    echo "   Exit code: $EXIT_CODE"
fi

echo ""
echo "📁 Log saved: $LOG_FILE"
echo "⏰ Completed: $(date)"
echo "=========================================================================="

# Clean up old logs (keep last 30 days)
find "$LOG_DIR" -name "daily_report_*.log" -mtime +30 -delete 2>/dev/null
find "$LOG_DIR" -name "ollama_*.log" -mtime +30 -delete 2>/dev/null

exit $EXIT_CODE
WRAPPER_EOF

chmod +x "$WRAPPER_SCRIPT"
echo "   ✅ Created: $WRAPPER_SCRIPT"
echo ""

# Backup existing crontab
echo "💾 Backing up existing crontab..."
crontab -l > "$TORRI_DIR/crontab_backup_$(date +%Y%m%d_%H%M%S).txt" 2>/dev/null || true
echo "   ✅ Backup saved"
echo ""

# Add to crontab
echo "📝 Adding to crontab..."

# Remove any existing TORRI daily report entries
crontab -l 2>/dev/null | grep -v "run_daily_report" | grep -v "TORRI Daily Report" > /tmp/crontab_new || true

# Add new entry
cat >> /tmp/crontab_new << CRON_EOF

# TORRI Daily Report - $TIME_DESC
$CRON_TIME $WRAPPER_SCRIPT

CRON_EOF

# Install new crontab
crontab /tmp/crontab_new
rm /tmp/crontab_new

echo "   ✅ Crontab updated"
echo ""

# Show current crontab
echo "=========================================================================="
echo "📋 Current Crontab"
echo "=========================================================================="
echo ""
crontab -l | grep -A 1 "TORRI"
echo ""

# Create monitoring script
MONITOR_SCRIPT="$TORRI_DIR/check_daily_report.sh"

cat > "$MONITOR_SCRIPT" << 'MONITOR_EOF'
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
MONITOR_EOF

chmod +x "$MONITOR_SCRIPT"

echo "=========================================================================="
echo "✅ Setup Complete!"
echo "=========================================================================="
echo ""
echo "📋 Configuration:"
echo "   Schedule: $TIME_DESC"
echo "   Script: $SCRIPT"
echo "   Logs: $LOG_DIR/"
echo ""
echo "=========================================================================="
echo "🎯 Next Steps"
echo "=========================================================================="
echo ""
echo "1. Test the cron job manually:"
echo "   $WRAPPER_SCRIPT"
echo ""
echo "2. Monitor the daily reports:"
echo "   ./check_daily_report.sh"
echo ""
echo "3. View latest log:"
echo "   tail -f $LOG_DIR/daily_report_*.log"
echo ""
echo "4. Edit schedule if needed:"
echo "   crontab -e"
echo ""
echo "=========================================================================="
echo "⚠️  Important Notes"
echo "=========================================================================="
echo ""
echo "• The report will run automatically at $TIME_DESC"
echo "• Logs are saved to: $LOG_DIR/"
echo "• Old logs (>30 days) are automatically cleaned up"
echo "• Ollama will start automatically if not running"
echo "• Check logs regularly to ensure reports are working"
echo ""
echo "=========================================================================="
echo ""
echo "🎉 Automatic daily reports are now active!"
echo ""
