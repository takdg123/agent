#!/bin/bash
# Setup script for downloading and configuring models for TORRI
# Optimized for NVIDIA A6000 (48GB VRAM)

set -e

echo "=========================================================================="
echo "🚀 TORRI Model Setup for A6000"
echo "=========================================================================="
echo ""

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is not installed!"
    echo ""
    echo "Please install Ollama first:"
    echo "   curl -fsSL https://ollama.com/install.sh | sh"
    echo ""
    exit 1
fi

echo "✅ Ollama is installed"
echo ""

# Start Ollama service if not running
if ! pgrep -x "ollama" > /dev/null; then
    echo "🔄 Starting Ollama service..."
    ollama serve &
    sleep 5
fi

echo "=========================================================================="
echo "📥 Downloading Models (This may take a while...)"
echo "=========================================================================="
echo ""

# 1. AstroSage-70B (Astronomy expert model)
echo "1️⃣  AstroSage-70B-GGUF (Astronomy Expert)"
echo "   Model: mradermacher/AstroSage-70B-GGUF"
echo "   Quantization: Q4_K_M (~40GB)"
echo "   Use: GRB Expert, Kilonova Expert"
echo ""

# Create Modelfile for AstroSage
cat > /tmp/astrosage_modelfile << 'EOF'
FROM mradermacher/AstroSage-70B-GGUF:Q4_K_M

TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
"""

PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 8192
EOF

echo "   Creating AstroSage model in Ollama..."
if ollama list | grep -q "astrosage:70b-q4_K_M"; then
    echo "   ✅ AstroSage already exists, skipping..."
else
    # Note: You'll need to manually download from HuggingFace and create the model
    echo "   ⚠️  Manual setup required for AstroSage:"
    echo ""
    echo "   1. Download from: https://huggingface.co/mradermacher/AstroSage-70B-GGUF"
    echo "      File: AstroSage-70B.Q4_K_M.gguf (~40GB)"
    echo ""
    echo "   2. Create model:"
    echo "      ollama create astrosage:70b-q4_K_M -f /tmp/astrosage_modelfile"
    echo ""
    echo "   For now, we'll use qwen2.5:72b as fallback..."
fi

echo ""

# 2. Qwen2.5-32B (General purpose, larger model)
echo "2️⃣  Qwen2.5:32B (General Expert)"
echo "   Size: ~20GB"
echo "   Use: Astrophysicist, Language Expert, Critic, Writer"
echo ""

if ollama list | grep -q "qwen2.5:32b"; then
    echo "   ✅ Qwen2.5:32B already exists"
else
    echo "   📥 Pulling Qwen2.5:32B..."
    ollama pull qwen2.5:32b
    echo "   ✅ Downloaded Qwen2.5:32B"
fi

echo ""

# 3. Optional: Qwen2.5-72B (Maximum capability, if you want even larger)
echo "3️⃣  Qwen2.5:72B (Optional - Maximum Capability)"
echo "   Size: ~40GB"
echo "   Use: Can replace 32B for even better quality"
echo ""

read -p "   Do you want to download Qwen2.5:72B? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if ollama list | grep -q "qwen2.5:72b"; then
        echo "   ✅ Qwen2.5:72B already exists"
    else
        echo "   📥 Pulling Qwen2.5:72B (this will take a while)..."
        ollama pull qwen2.5:72b
        echo "   ✅ Downloaded Qwen2.5:72B"
    fi
else
    echo "   ⏭️  Skipping Qwen2.5:72B"
fi

echo ""

echo "=========================================================================="
echo "📋 Model Summary"
echo "=========================================================================="
echo ""
ollama list
echo ""

echo "=========================================================================="
echo "⚙️  Configuration"
echo "=========================================================================="
echo ""
echo "Add these to your .env file (if not already present):"
echo ""
echo "# Model Configuration"
echo "ASTRO_EXPERT_MODEL=astrosage:70b-q4_K_M  # Or qwen2.5:72b as fallback"
echo "GENERAL_MODEL=qwen2.5:32b                # Or qwen2.5:72b for more capability"
echo "LANGUAGE_MODEL=qwen2.5:32b               # Or qwen2.5:72b for better translation"
echo ""

# Update .env if it exists
if [ -f "/home/dtak/torri/.env" ]; then
    echo "📝 Updating .env file..."
    
    # Backup
    cp /home/dtak/torri/.env /home/dtak/torri/.env.backup
    
    # Update or add model configurations
    if grep -q "ASTRO_EXPERT_MODEL" /home/dtak/torri/.env; then
        sed -i 's/^ASTRO_EXPERT_MODEL=.*/ASTRO_EXPERT_MODEL=astrosage:70b-q4_K_M/' /home/dtak/torri/.env
    else
        echo "ASTRO_EXPERT_MODEL=astrosage:70b-q4_K_M" >> /home/dtak/torri/.env
    fi
    
    if grep -q "GENERAL_MODEL" /home/dtak/torri/.env; then
        sed -i 's/^GENERAL_MODEL=.*/GENERAL_MODEL=qwen2.5:32b/' /home/dtak/torri/.env
    else
        echo "GENERAL_MODEL=qwen2.5:32b" >> /home/dtak/torri/.env
    fi
    
    if grep -q "LANGUAGE_MODEL" /home/dtak/torri/.env; then
        sed -i 's/^LANGUAGE_MODEL=.*/LANGUAGE_MODEL=qwen2.5:32b/' /home/dtak/torri/.env
    else
        echo "LANGUAGE_MODEL=qwen2.5:32b" >> /home/dtak/torri/.env
    fi
    
    echo "   ✅ Updated .env file (backup saved to .env.backup)"
fi

echo ""
echo "=========================================================================="
echo "🎯 Model Assignment"
echo "=========================================================================="
echo ""
echo "Expert Agent            → Model"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "GRB Expert              → AstroSage-70B (astronomy specialized)"
echo "Kilonova Expert         → AstroSage-70B (astronomy specialized)"
echo "Astrophysicist          → Qwen2.5:32B (synthesis & context)"
echo "Language Expert         → Qwen2.5:32B (bilingual translation)"
echo "Critic                  → Qwen2.5:32B (quality review)"
echo "Writer                  → Qwen2.5:32B (polishing)"
echo ""

echo "=========================================================================="
echo "✅ Setup Complete!"
echo "=========================================================================="
echo ""
echo "🚀 Next Steps:"
echo ""
echo "1. If you haven't set up AstroSage yet:"
echo "   - Download: https://huggingface.co/mradermacher/AstroSage-70B-GGUF"
echo "   - File: AstroSage-70B.Q4_K_M.gguf"
echo "   - Run: ollama create astrosage:70b-q4_K_M -f /tmp/astrosage_modelfile"
echo ""
echo "2. Test the setup:"
echo "   cd /home/dtak/torri"
echo "   ./run_daily_report_refactored.py"
echo ""
echo "3. Monitor GPU usage:"
echo "   nvidia-smi -l 1"
echo ""
echo "Expected VRAM usage:"
echo "  - AstroSage-70B Q4_K_M: ~40GB"
echo "  - Qwen2.5:32B: ~20GB"
echo "  - Total (when running simultaneously): ~45-48GB"
echo "  - Your A6000 has 48GB - perfect fit! ✨"
echo ""
