#!/bin/bash

# Quick Daily Report Setup Script
# This automates the entire setup process

echo "🚀 TORRI Daily Report Setup"
echo "="*70

# Step 1: Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is not installed"
    echo ""
    echo "Please install Ollama first:"
    echo "  curl -fsSL https://ollama.com/install.sh | sh"
    echo ""
    exit 1
fi

echo "✅ Ollama is installed"

# Step 2: Check if Ollama is running, if not start it
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚡ Starting Ollama in background..."
    nohup ollama serve > ollama.log 2>&1 &
    sleep 5
    
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Ollama started successfully"
    else
        echo "❌ Failed to start Ollama"
        exit 1
    fi
else
    echo "✅ Ollama is already running"
fi

# Step 3: Check if model is downloaded
echo ""
echo "📥 Checking Qwen model..."
if ollama list | grep -q "qwen2.5:7b"; then
    echo "✅ Qwen2.5:7b model is available"
else
    echo "⚡ Pulling Qwen2.5:7b model (this may take a while)..."
    ollama pull qwen2.5:7b
fi

# Step 4: Test run
echo ""
echo "🧪 Running test report..."
/home/dtak/miniconda3/envs/torri/bin/python run_daily_report_ollama.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Test report completed!"
else
    echo ""
    echo "❌ Test report failed. Check the error messages above."
    exit 1
fi

# Step 5: Ask about cron setup
echo ""
echo "📅 Would you like to set up daily automation?"
echo ""
echo "Options:"
echo "  1) Yes, run daily at 10:00 AM"
echo "  2) Yes, but different time"
echo "  3) No, I'll run manually"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        # Add cron for 10 AM
        CRON_CMD="0 10 * * * cd /home/dtak/torri && /home/dtak/miniconda3/envs/torri/bin/python run_daily_report_ollama.py >> /home/dtak/torri/daily_report.log 2>&1"
        (crontab -l 2>/dev/null | grep -v "run_daily_report_ollama.py"; echo "$CRON_CMD") | crontab -
        
        echo ""
        echo "✅ Daily report scheduled for 10:00 AM"
        ;;
    
    2)
        echo ""
        echo "Enter hour (0-23): "
        read hour
        echo "Enter minute (0-59): "
        read minute
        
        CRON_CMD="$minute $hour * * * cd /home/dtak/torri && /home/dtak/miniconda3/envs/torri/bin/python run_daily_report_ollama.py >> /home/dtak/torri/daily_report.log 2>&1"
        (crontab -l 2>/dev/null | grep -v "run_daily_report_ollama.py"; echo "$CRON_CMD") | crontab -
        
        echo ""
        echo "✅ Daily report scheduled for $hour:$minute"
        ;;
    
    3)
        echo ""
        echo "✅ No automation set up. Run manually with:"
        echo "   ./run_daily_report_ollama.py"
        ;;
    
    *)
        echo "Invalid choice"
        ;;
esac

# Step 6: Summary
echo ""
echo "="*70
echo "✅ SETUP COMPLETE!"
echo "="*70
echo ""
echo "What was set up:"
echo "  ✅ Ollama is running"
echo "  ✅ Qwen2.5:7b model is ready"
echo "  ✅ Test report generated"
echo ""
echo "Check your setup:"
echo "  - Reports: ls -lh data/reports/"
echo "  - Logs: tail -f daily_report.log"
echo "  - Cron: crontab -l"
echo ""
echo "To configure email, edit .env file:"
echo "  SENDER_EMAIL=your-gmail@gmail.com"
echo "  SENDER_PASSWORD=your-app-password"
echo "  RECIPIENT_EMAIL=recipient@example.com"
echo ""
echo "See DAILY_SETUP.md for more details."
echo ""
