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
