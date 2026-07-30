# Quick Test Instructions 🧪

## Test the New Models

Since you've downloaded AstroSage-70B and Qwen2.5:32B, let's test them!

### Option 1: Automatic Test (Recommended)

```bash
cd /home/dtak/torri

# This will start Ollama (if needed) and run all tests
./test_models_with_ollama.sh
```

### Option 2: Manual Test

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Run tests
cd /home/dtak/torri
./test_new_models.py
```

## What the Test Does

The test script will:

1. ✅ Check if models are available
2. 🌟 Test **AstroSage-70B** with astronomy question
3. 🔭 Test **Qwen2.5:32B** with Korean translation
4. 🧠 Initialize all 6 expert agents
5. 📄 Run GRB Expert on a sample paper

**Expected time**: 2-3 minutes (70B models are slower but more accurate!)

## Expected Output

```
======================================================================
🧪 Testing New Models (AstroSage-70B + Qwen2.5:32B)
======================================================================

📋 Configuration:
   Astro Expert Model: astrosage:70b-q4_K_M
   General Model: qwen2.5:32b
   Language Model: qwen2.5:32b

======================================================================
Test 1: Model Availability
======================================================================

🔍 Checking Ollama service...
   ✅ Ollama is running
   Available models: 5
      • astrosage:70b-q4_K_M
      • qwen2.5:32b
      ...

======================================================================
Test 2: AstroSage-70B (Astronomy Expert)
======================================================================

🌟 Testing astrosage:70b-q4_K_M...
   Generating response... (this may take 30-60s for 70B model)

   Response:
   ------------------------------------------------------------------
   [Detailed astronomy response about GRB prompt emission]
   ------------------------------------------------------------------

   ✅ AstroSage-70B is working!

======================================================================
Test 3: Qwen2.5:32B (General Model)
======================================================================

🔭 Testing qwen2.5:32b...
   Generating response... (this may take 15-30s for 32B model)

   Response:
   ------------------------------------------------------------------
   이 논문은 GRB 240710A의 관측 결과와 중성자별 병합에서 발생한
   킬로노바 방출을 제시합니다.
   ------------------------------------------------------------------

   ✅ Qwen2.5:32B is working!

======================================================================
...

📊 TEST SUMMARY
======================================================================

✅ Model Availability: PASS
✅ AstroSage-70B Test: PASS
✅ Qwen2.5:32B Test: PASS
✅ Expert Initialization: PASS
✅ GRB Expert Test: PASS

🎉 All tests completed!
```

## After Testing

Once tests pass, run the full daily report:

```bash
cd /home/dtak/torri
./run_daily_report_refactored.py
```

This will:
- Fetch today's papers from arXiv
- Analyze with **6 expert agents** using new models
- Generate professional HTML report
- Email if quality >= 70/100

## Monitoring GPU Usage

In another terminal, watch GPU memory:

```bash
watch -n 1 nvidia-smi
```

Expected VRAM usage:
- During AstroSage-70B: ~40-42GB
- During Qwen2.5:32B: ~20-22GB
- Peak: ~42GB (fits in your 48GB A6000!)

## Troubleshooting

### "Ollama is not running"
```bash
ollama serve
```

### "Model not found: astrosage:70b-q4_K_M"
Check if model exists:
```bash
ollama list
```

If missing, create it:
```bash
ollama create astrosage:70b-q4_K_M -f /tmp/astrosage_modelfile
```

### "Out of memory"
The models should fit, but if issues:
```bash
# Check GPU usage
nvidia-smi

# Make sure no other processes using GPU
# Close other applications using CUDA
```

### "Test times out"
70B models are slower - this is normal!
- AstroSage-70B: 30-60s per query
- Qwen2.5:32B: 15-30s per query

## Performance Comparison

**Before (Qwen2.5:7B)**:
- Response time: ~3-5s
- Quality: Good
- VRAM: ~5GB

**After (AstroSage-70B + Qwen2.5:32B)**:
- Response time: ~30-45s (slower but worth it!)
- Quality: Excellent (astronomy-specialized!)
- VRAM: ~20-40GB

The extra time is worth it for research-grade analysis with astronomy expertise! ✨

---

**Ready to test?**
```bash
cd /home/dtak/torri
./test_models_with_ollama.sh
```
