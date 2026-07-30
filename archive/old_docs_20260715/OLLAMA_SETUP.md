# TORRI with Ollama - Simple Setup ✅

## Overview

Switched from vLLM/Qwen to Ollama for simplicity and reliability.

**Removed:**
- ❌ vLLM (compatibility issues with CUDA)
- ❌ PyTorch/CUDA packages (200+ GB)
- ❌ Complex GPU configuration
- ❌ All Qwen-specific scripts

**Now using:**
- ✅ Ollama (simple, local LLM server)
- ✅ Qwen2.5:7b model via Ollama
- ✅ Lightweight Python environment
- ✅ Easy setup and maintenance

## Quick Start

### 1. Setup Ollama

```bash
cd /home/dtak/torri
./setup_ollama.sh
```

This will:
- Check if Ollama is installed
- Start Ollama service if needed
- Pull the Qwen2.5:7b model

### 2. Run Daily Report

```bash
./run_daily_report_ollama.py
```

This will:
- Fetch latest papers from arXiv
- Analyze them using Ollama + Qwen2.5
- Generate HTML report
- Send email (if configured)

## Configuration

Edit `/home/dtak/torri/.env`:

```bash
# Ollama settings
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_ENABLED=true

# Email settings
SENDER_EMAIL=your-gmail@gmail.com
SENDER_PASSWORD=your-app-password
RECIPIENT_EMAIL=recipient@example.com

# Paper settings
MAX_PAPERS=20
```

## Available Models

```bash
# List installed models
ollama list

# Pull other models
ollama pull llama3.1:8b
ollama pull qwen2.5:14b

# Update model in .env
OLLAMA_MODEL=llama3.1:8b
```

## Automate with Cron

```bash
crontab -e

# Add for 10:00 AM daily:
0 10 * * * cd /home/dtak/torri && ./run_daily_report_ollama.py >> daily_report.log 2>&1
```

## Troubleshooting

### Ollama not running

```bash
ollama serve
```

### Model not found

```bash
ollama pull qwen2.5:7b
```

### Check Ollama status

```bash
curl http://localhost:11434/api/tags
```

## Benefits of Ollama

1. **Simple**: No CUDA version conflicts
2. **Fast**: Optimized for local inference
3. **Flexible**: Easy to switch models
4. **Reliable**: Well-tested and maintained
5. **Lightweight**: No heavy GPU libraries

## Cleanup Done

Removed from environment:
- vllm
- torch, torchvision, torchaudio
- All nvidia-cuda-* packages
- ray, flashinfer, triton
- xformers, compressed-tensors
- Total saved: ~15GB

## Files

- `setup_ollama.sh` - Setup Ollama and pull models
- `run_daily_report_ollama.py` - Main daily report script
- `src/config.py` - Updated configuration
- `.env` - Environment variables

---

**Ready to use!** Just run `./setup_ollama.sh` then `./run_daily_report_ollama.py`
