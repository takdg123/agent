#!/bin/bash

# Test TORRI for a week
# This script helps you test the daily report system

echo "🧪 TORRI Weekly Test Setup"
echo "="*70

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "❌ Ollama is not running"
    echo ""
    echo "Please start Ollama first:"
    echo "  ollama serve"
    echo ""
    echo "Or in background:"
    echo "  nohup ollama serve > ollama.log 2>&1 &"
    exit 1
fi

echo "✅ Ollama is running"

# Show options
echo ""
echo "Choose test mode:"
echo ""
echo "1. Single test run (run report once now)"
echo "2. Set up daily cron for 1 week (10:00 AM)"
echo "3. Generate 7 test reports now (simulated week)"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "📊 Running single test..."
        ./run_daily_report_ollama.py
        ;;
    
    2)
        echo ""
        echo "📅 Setting up daily cron for 1 week..."
        
        # Create cron entry
        CRON_CMD="0 10 * * * cd /home/dtak/torri && ./run_daily_report_ollama.py >> /home/dtak/torri/daily_report.log 2>&1"
        
        # Add to crontab
        (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
        
        echo "✅ Cron job added!"
        echo ""
        echo "Daily reports will run at 10:00 AM"
        echo ""
        echo "To view cron jobs:"
        echo "  crontab -l"
        echo ""
        echo "To remove after 1 week:"
        echo "  crontab -e"
        echo "  (delete the line with run_daily_report_ollama.py)"
        ;;
    
    3)
        echo ""
        echo "📊 Generating 7 test reports..."
        for i in {1..7}; do
            echo ""
            echo "=== Day $i ==="
            ./run_daily_report_ollama.py
            
            if [ $i -lt 7 ]; then
                echo ""
                echo "⏸️  Waiting 5 seconds before next report..."
                sleep 5
            fi
        done
        
        echo ""
        echo "✅ Generated 7 reports!"
        echo "Check data/reports/ for HTML files"
        ;;
    
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
