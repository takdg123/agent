#!/bin/bash
# Start Ollama and test new models

echo "=========================================================================="
echo "🚀 Starting Ollama and Testing New Models"
echo "=========================================================================="
echo ""

# Check if Ollama is already running
if pgrep -x "ollama" > /dev/null; then
    echo "✅ Ollama is already running"
else
    echo "🔄 Starting Ollama service..."
    ollama serve > /tmp/ollama.log 2>&1 &
    OLLAMA_PID=$!
    echo "   Started with PID: $OLLAMA_PID"
    
    # Wait for Ollama to be ready
    echo "   Waiting for Ollama to be ready..."
    sleep 5
    
    # Check if it's responding
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "   ✅ Ollama is responding"
    else
        echo "   ⚠️  Ollama may not be fully ready, waiting a bit more..."
        sleep 5
    fi
fi

echo ""
echo "=========================================================================="
echo "📋 Available Models"
echo "=========================================================================="
echo ""
ollama list

echo ""
echo "=========================================================================="
echo "🧪 Running Model Tests"
echo "=========================================================================="
echo ""

cd /home/dtak/torri
/home/dtak/miniconda3/envs/torri/bin/python3 test_new_models.py

TEST_EXIT=$?

echo ""
echo "=========================================================================="

if [ $TEST_EXIT -eq 0 ]; then
    echo "✅ All tests passed!"
else
    echo "⚠️  Some tests failed (exit code: $TEST_EXIT)"
    echo ""
    echo "Check /tmp/ollama.log for Ollama logs"
fi

echo "=========================================================================="
echo ""
