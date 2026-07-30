#!/bin/bash

# Stop Ollama service

echo "🛑 Stopping Ollama..."

# Find and kill Ollama processes
PIDS=$(pgrep -f ollama)

if [ -z "$PIDS" ]; then
    echo "✅ Ollama is not running"
    exit 0
fi

echo "Found Ollama processes: $PIDS"

for PID in $PIDS; do
    echo "  Killing process $PID..."
    kill $PID 2>/dev/null
done

# Wait a moment
sleep 2

# Force kill if still running
PIDS=$(pgrep -f ollama)
if [ ! -z "$PIDS" ]; then
    echo "⚠️ Force killing remaining processes..."
    for PID in $PIDS; do
        kill -9 $PID 2>/dev/null
    done
fi

# Final check
sleep 1
PIDS=$(pgrep -f ollama)
if [ -z "$PIDS" ]; then
    echo "✅ Ollama stopped successfully"
else
    echo "❌ Some Ollama processes may still be running"
    echo "   Try: sudo killall ollama"
fi
