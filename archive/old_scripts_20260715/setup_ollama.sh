#!/bin/bash

# Setup Ollama with Qwen for TORRI
# This script checks Ollama installation and pulls the Qwen model

echo "🚀 TORRI Ollama Setup"
echo "="*70

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is not installed"
    echo ""
    echo "Please install Ollama:"
    echo "  curl -fsSL https://ollama.com/install.sh | sh"
    echo ""
    exit 1
fi

echo "✅ Ollama is installed"
ollama --version

# Check if Ollama service is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Ollama service is not running"
    echo ""
    echo "Starting Ollama service..."
    ollama serve > /dev/null 2>&1 &
    sleep 3
fi

echo "✅ Ollama service is running"

# Pull Qwen model
MODEL="qwen2.5:7b"
echo ""
echo "📥 Pulling model: $MODEL"
echo "   (This may take a while on first run...)"
ollama pull $MODEL

echo ""
echo "✅ Setup complete!"
echo ""
echo "Available models:"
ollama list

echo ""
echo "To test the model:"
echo "  ollama run $MODEL"
