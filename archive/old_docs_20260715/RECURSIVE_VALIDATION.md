# Recursive Report Validation & Auto-Fix ✨

## How It Works

The system now automatically regenerates reports when quality is insufficient:

### Flow Diagram

```
┌─────────────────────────┐
│ 1. Generate Report      │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ 2. Validate Quality     │
│    - Structure          │
│    - Content            │
│    - Languages          │
│    - Format             │
│    - Links              │
└──────────┬──────────────┘
           │
           ▼
      ┌────────┐
      │ Valid? │◄──────┐
      └───┬────┘       │
          │            │
    YES   │    NO      │
          │            │
          ▼            │
   ┌──────────┐   ┌────────────────┐
   │   SEND   │   │ 3. Auto-Fix    │
   │  EMAIL   │   │    - Analyze   │
   └──────────┘   │    - Improve   │
                  │    - Regenerate│
                  └────────┬───────┘
                           │
                  Attempt < Max?
                           │
                          YES
                           │
                  ─────────┘
```

## Validation Process

### Attempt 1: Initial Generation
```
📊 Report Generation Attempt 1/3
Generating initial report...
🔍 Validating report quality...

Quality Score: 65/100 (NEEDS IMPROVEMENT)
❌ Issues found - regenerating...
```

### Attempt 2: Auto-Fix
```
📊 Report Generation Attempt 2/3
🔄 Regenerating with quality improvements...
   Previous score: 65/100
   Applying 3 improvements:
      • Ensure both English and Korean content are generated
      • Generate more comprehensive Korean summaries
      • Fix HTML formatting errors
   
   Re-analyzing papers with enhanced prompts...
      [1/5] Improving Low-hard to high-soft spectral...
      [2/5] Improving Magnetospheric flows in X-ray...
      ...

Quality Score: 82/100 (GOOD)
✅ Report quality acceptable!
```

### Attempt 3: Final Try (if needed)
```
📊 Report Generation Attempt 3/3
🔄 Regenerating with quality improvements...
   ...
```

## Auto-Fix Strategies

### 1. Enhanced Prompts
For papers with poor analysis, regenerate with:
- **Explicit requirements** (minimum word count)
- **Structured format** (numbered sections)
- **Quality emphasis** (professional, comprehensive)
- **Attempt tracking** (shows retry number to model)

### 2. Targeted Improvements

Based on validation issues:

| Issue | Fix Strategy |
|-------|-------------|
| **Missing Korean** | Regenerate with stricter Korean prompt |
| **Short analysis** | Require minimum 200 words English, 150 chars Korean |
| **Broken HTML** | Validate tags, regenerate structure |
| **Missing links** | Re-extract arXiv IDs |
| **Format errors** | Clean HTML, escape special chars |

### 3. Progressive Enhancement

```python
Attempt 1: Standard generation
Attempt 2: Enhanced prompts + regenerate worst 5 papers
Attempt 3: Strictest prompts + regenerate worst 10 papers
```

## Configuration

### Max Attempts
```python
MAX_ATTEMPTS = 3  # Default: 3 tries
```

### Quality Threshold
```python
MINIMUM_SCORE = 70  # Send if >= 70
CRITICAL_ISSUES = False  # Must have no critical issues
```

### Regeneration Strategy
```python
# Papers to regenerate per attempt
attempt_1: 0 (initial)
attempt_2: 5 (worst 5)
attempt_3: 10 (worst 10)
```

## Output Examples

### Successful Case
```
======================================================================
📊 Report Generation Attempt 1/3
======================================================================
Generating initial report...

🔍 Validating report quality...
🟢 Quality Score: 92/100 (EXCELLENT)
✅ Valid: True
✅ No critical issues found

✅ Report quality acceptable! (Score: 92/100)

✅ Report saved: daily_report_20260715.html
📧 Sending email...
✅ Email sent to user@example.com
```

### Failed Case (Max Attempts)
```
======================================================================
📊 Report Generation Attempt 3/3
======================================================================
🔄 Regenerating with quality improvements...
   Previous score: 58/100
   ...

🔍 Validating report quality...
🔴 Quality Score: 62/100 (NEEDS IMPROVEMENT)

⚠️  Max attempts reached. Best score: 62/100

❌ Report still has critical issues after 3 attempts!
   Saving as DRAFT, NOT sending email.
📄 Draft saved: daily_report_20260715_DRAFT.html
```

## Benefits

1. **Automatic Quality Control** - No bad reports sent
2. **Self-Improving** - Uses validation feedback
3. **Transparent** - Shows all attempts and scores
4. **Configurable** - Adjust thresholds and attempts
5. **Fallback** - Always saves draft even if fails

## Validation Metrics

### Quality Score (0-100)

- **Structure**: 25 points
- **Content**: 30 points
- **Language**: 20 points
- **Format**: 15 points
- **Links**: 10 points

**Penalties:**
- Critical issue: -10 points each
- Warning: -3 points each

### Grades

- **🟢 90-100**: EXCELLENT - Send immediately
- **🟡 70-89**: GOOD - Send with confidence  
- **🔴 <70**: NEEDS IMPROVEMENT - Regenerate

## Testing

```bash
cd /home/dtak/torri

# Run with auto-fix
./run_daily_report_ollama.py

# Watch the recursive improvement process
# You'll see attempts 1, 2, 3 with improving scores
```

## Future Enhancements

1. **Smart regeneration** - Only regenerate problematic papers
2. **ML-based scoring** - Learn what makes good reports
3. **A/B testing** - Compare different generation strategies
4. **User feedback** - Learn from email engagement
5. **Caching** - Save good analyses for reuse

---

**Status**: Implemented ✅  
**Max Attempts**: 3  
**Quality Threshold**: 70/100  
**Auto-Send**: Only if valid and score >= 70
