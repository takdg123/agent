# Email Configuration Fix

## Problem
```
❌ Email failed: 'Config' object has no attribute 'email_from'
```

## Root Cause
The script was using outdated attribute names that didn't match the Config class:

**Script was using:**
- `config.email_from` ❌
- `config.email_password` ❌
- `config.email_to` ❌

**Config class actually has:**
- `config.sender_email` ✅
- `config.sender_password` ✅
- `config.recipient_email` ✅

## Fixes Applied

### 1. Fixed `run_daily_report_refactored.py`
**Before:**
```python
yag = yagmail.SMTP(config.email_from, config.email_password)
yag.send(
    to=config.email_to,
    subject=f"...",
    contents=html
)
```

**After:**
```python
if not config.email_enabled:
    print("\n📧 Email not configured (skipping)")
    return False

yag = yagmail.SMTP(config.sender_email, config.sender_password)
yag.send(
    to=config.recipient_email,
    subject=f"...",
    contents=html
)
```

### 2. Fixed `src/config.py`
Added missing OpenAI-compatible API configuration attributes:
```python
self.openai_compatible_enabled = os.getenv("OPENAI_COMPATIBLE_ENABLED", "false").lower() == "true"
self.openai_compatible_url = os.getenv("OPENAI_COMPATIBLE_URL", "http://localhost:8000/v1")
self.openai_compatible_api_key = os.getenv("OPENAI_COMPATIBLE_API_KEY", "EMPTY")
self.openai_compatible_model = os.getenv("OPENAI_COMPATIBLE_MODEL", "Qwen2.5-VL-7B-Instruct")
```

These were referenced in `__str__` method but not defined.

## Current Configuration

Based on your `.env` file:

```bash
✅ Email is ENABLED and configured:
   Sender: takdg123@gmail.com
   Recipient: takdg123@gmail.com
   
✅ Ollama: DISABLED (not needed)
✅ OpenAI-Compatible: ENABLED (http://localhost:8000/v1)
✅ Vision Processing: ENABLED
✅ Agent Harness: ENABLED
```

## Email Behavior

The script will now:
1. ✅ Check if email is configured (`config.email_enabled`)
2. ✅ Only send email if quality score ≥ 70
3. ✅ Use correct attribute names
4. ✅ Show clear messages if email is skipped

## Testing

To test email functionality:
```bash
cd ~/torri
conda activate torri
python3 run_daily_report_refactored.py
```

The report will be:
- Always saved to: `data/reports/expert_report_YYYYMMDD.html`
- Emailed only if: quality score ≥ 70 AND email is configured

## Environment Variables

Your `.env` file has all required email settings:
```bash
SENDER_EMAIL=takdg123@gmail.com
SENDER_PASSWORD=zlgehvhtaictmfvy
RECIPIENT_EMAIL=takdg123@gmail.com
```

Email should work correctly now! 📧✅
