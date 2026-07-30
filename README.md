# TORRI - Transient Observation Research & Realtime Intelligence 🔬

AI-powered daily research digest for high-energy astrophysics (GRBs, kilonovae, neutron star mergers).

## Quick Start

### 1. Setup Models (First Time)
```bash
./setup_models.sh
```

Downloads and configures:
- **AstroSage-70B** (astronomy expert for GRB/kilonova)
- **Qwen2.5:32B** (general analysis, translation, writing)

### 2. Test Models
```bash
./test_models_with_ollama.sh
```

### 3. Run Daily Report
```bash
./run_daily_report_refactored.py
```

### 4. Setup Automatic Daily Reports
```bash
./setup_daily_cron.sh
```

## What It Does

```
Daily Workflow:
  ↓
📥 Fetch papers from arXiv (astro-ph.HE)
  ↓
🎯 Score against your interest profile (config/interests.yml)
     nomic-embed-text ranks candidates → LLM triage gates them
     Each kept paper carries a score, topic tags, and a stated reason
  ↓
📖 Extract full text (PDF → fitz → intro / methods / results / conclusions)
  ↓
📚 Recall similar past papers + running topic notes
  ↓
🔬 Analyze with 6 Expert Agents:
  • Domain experts (AstroSage-70B), only those whose domain the paper
    touches, strongest first, each seeing the reviews already written:
      – GRB Expert
      – Kilonova Expert
  • Astrophysicist (Qwen2.5:32B)  → synthesis
  • Critic (Qwen2.5:32B)          → scores it
       ↳ below threshold, back to the Astrophysicist to revise,
         then re-reviewed (up to 2 rounds; best version wins)
  • Writer (Qwen2.5:32B)          → polishes the English
  • Language Expert (Qwen2.5:32B) → translates the FINAL English
  ↓
🔢 Extract key numbers
  ↓
🔍 Validate Quality (Rules + LLM)
  ↓
📄 Generate mobile-first HTML report (verdict-first cards)
  ↓
📧 Email Results (if quality >= 70%)
  ↓
🧠 Record embeddings + update topic notes
```

Translation is deliberately **last**. Earlier the order was synthesis →
translate → critic → writer, so the writer rewrote the English *after* the Korean
had been derived from the pre-polish draft, and the two drifted apart. Korean is
now a strict translation of the final English, so they cannot disagree.

## Features

✅ **Interest-Aware** - relevance scored against a prose profile you edit  
✅ **Reads the paper** - analyses full text, not just the abstract  
✅ **Multi-Expert Analysis** - 6 specialized AI agents  
✅ **Astronomy Expertise** - AstroSage-70B knows GRB/kilonova physics  
✅ **Bilingual, and consistent** - Korean is a translation of the final English  
✅ **Mobile-First Report** - single-column, verdict-first, email-safe (no JS)  
✅ **Quality Control** - Multi-layer validation (rules + LLM + critic)  
✅ **Learning System** - semantic recall + running per-topic notes  
✅ **Automatic** - Daily cron job, zero maintenance  

## Tuning what you see

`config/interests.yml` drives relevance. Edit `profile` (prose describing your
work), `core` (topics you want), and `exclude` (topics to reject). Papers below
`threshold` are dropped; every kept paper shows its score and why it was kept, so
you can see the filter's reasoning instead of trusting it.

Editing `profile` automatically invalidates the cached embedding.

## Tests

```bash
for f in test/test_*.py; do python3 "$f"; done
```

Uses stdlib `unittest`; no test dependencies. LLM and network access are stubbed,
except one PDF-extraction test that uses a cached PDF if present.

## System Requirements

- **GPU**: NVIDIA A6000 (48GB VRAM) or similar
- **Python**: 3.12+
- **Ollama**: Latest version
- **Disk**: ~60GB for models

> **Two GPUs?** By default the ollama unit pins `CUDA_VISIBLE_DEVICES=0`, so
> AstroSage (42.5GB) and Qwen (21.7GB) cannot both stay resident in one 48GB card
> and a model is reloaded on every paper. See
> [docs/ollama-two-gpu-setup.md](docs/ollama-two-gpu-setup.md) — worth roughly
> 7 minutes of a 40 minute run.

## Documentation

- **[MODEL_UPGRADE_GUIDE.md](MODEL_UPGRADE_GUIDE.md)** - Model setup & troubleshooting
- **[AUTOMATIC_SETUP.md](AUTOMATIC_SETUP.md)** - Cron job setup & monitoring
- **[MULTI_EXPERT_SYSTEM.md](MULTI_EXPERT_SYSTEM.md)** - Expert agent details
- **[REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)** - Code architecture

## Configuration

Edit `.env` file:
```bash
# Models
ASTRO_EXPERT_MODEL=astrosage:70b-q4_K_M
GENERAL_MODEL=qwen2.5:32b
LANGUAGE_MODEL=qwen2.5:32b

# Email
EMAIL_FROM=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_TO=recipient@email.com

# Qdrant (optional)
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

## Monitoring

Check automatic report status:
```bash
./check_daily_report.sh
```

View logs:
```bash
tail -f logs/daily_report_*.log
```

View latest report:
```bash
ls -lt data/reports/expert_report_*.html | head -1
```

## Architecture

```
torri/
├── config/
│   └── interests.yml      # Your research profile - drives relevance
├── src/
│   ├── harness/           # Multi-expert agent system
│   │   ├── expert_agents.py        # 6 expert agents
│   │   ├── expert_harness.py       # Orchestration
│   │   └── knowledge_store.py      # Embeddings + running topic notes
│   ├── utils/             # Shared utilities
│   │   ├── llm_client.py           # LLM interface (raises on failure)
│   │   ├── relevance.py            # Profile match → LLM triage gate
│   │   ├── embeddings.py           # nomic-embed-text + cosine
│   │   ├── paper_text.py           # PDF → sections
│   │   ├── key_numbers.py          # Quantitative results
│   │   ├── latex_to_html.py        # Escaping + math rendering
│   │   ├── paper_filter.py         # Cheap keyword pre-filter
│   │   └── html_report_generator.py # Mobile-first report
│   ├── routines/          # Paper fetching
│   └── report_validator.py # Quality validation
│
├── data/
│   ├── knowledge/         # embeddings.jsonl + topics/*.md
│   ├── pdfs/              # PDF cache
│   └── reports/           # Generated reports
├── test/                  # stdlib unittest suites
│
├── run_daily_report_refactored.py  # Main script
├── setup_models.sh                 # Model setup
├── test_models_with_ollama.sh      # Testing
└── setup_daily_cron.sh             # Automation setup
```

## Performance

| Metric | Value |
|--------|-------|
| **Papers per day** | 5-10 (relevant) |
| **Analysis time** | ~45-60 min |
| **Quality score** | 85-95/100 |
| **Email success** | ~90% |
| **VRAM usage** | 20-42GB (sequential) |

## Example Report

```html
🔬 TORRI Research Digest
High-Energy Astrophysics • Multi-Expert Analysis

📊 Today's Analysis: 8 papers

Paper 1: GRB 240710A: Discovery of a Bright Kilonova
Quality: High (8.5/10) | GRB: 83% | Kilonova: 91%

📝 Expert Analysis:
[Comprehensive analysis by astrophysicist, synthesizing
 GRB and kilonova expert reviews...]

🇰🇷 한국어 요약:
GRB 240710A의 다파장 관측을 통해 중성자별 병합에서 
발생한 킬로노바 방출을 확인했습니다...

🎓 Expert Reviews:
• GRB Expert: The jet break constrains opening angle...
• Kilonova Expert: Blue component indicates lanthanide-poor ejecta...
```

## Troubleshooting

### No models found
```bash
ollama list
# Should show: astrosage:70b-q4_K_M, qwen2.5:32b
```

### Out of memory
```bash
nvidia-smi  # Check GPU usage
# Models load sequentially to fit in 48GB
```

### No email received
Check `.env` email settings and quality score in logs

### Report quality low
System auto-regenerates if < 70%, check logs for issues

## Credits

- **AstroSage-70B**: Astronomy-specialized LLM
- **Qwen2.5**: General-purpose LLM by Alibaba
- **Ollama**: Local LLM runtime

## License

Research use only.

---

**Version**: 2.0 (Refactored + Multi-Expert)  
**Last Updated**: July 15, 2026  
**Status**: Production Ready ✅
