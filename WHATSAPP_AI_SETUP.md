# 🤖 AI Draft Reply Setup - Gemini + OpenAI

## Overview

AI Agent automatically generates **smart, context-aware replies** for WhatsApp messages using:
- **Google Gemini API** (Recommended - Free tier)
- **OpenAI API** (Alternative)
- **Smart Templates** (Fallback - No API key needed)

---

## Quick Start

### Option 1: Google Gemini (Recommended) ⭐

**Free tier available, no credit card required!**

#### Step 1: Get Gemini API Key

1. Go to: https://makersuite.google.com/app/apikey
2. Click **Create API Key**
3. Copy the key

#### Step 2: Add to .env

```bash
# Edit .env file
GEMINI_API_KEY=AIzaSy...your-key-here
AI_DRAFT_PROVIDER=gemini
```

#### Step 3: Install Dependencies

```bash
pip install google-generativeai
```

#### Step 4: Run

```bash
python main.py
```

**Expected Output:**
```
✨ AI Draft Generator: ✅ Enabled (Gemini - gemini-2.0-flash-exp)
```

---

### Option 2: OpenAI API

**Requires paid API key ($5 minimum)**

#### Step 1: Get OpenAI API Key

1. Go to: https://platform.openai.com/api-keys
2. Click **Create new secret key**
3. Copy the key

#### Step 2: Add to .env

```bash
# Edit .env file
OPENAI_API_KEY=sk-...your-key-here
AI_DRAFT_PROVIDER=openai
```

#### Step 3: Install Dependencies

```bash
pip install openai
```

#### Step 4: Run

```bash
python main.py
```

**Expected Output:**
```
✨ AI Draft Generator: ✅ Enabled (OpenAI - gpt-4o-mini)
```

---

### Option 3: Template Fallback (No Setup)

**No API key needed - works out of the box!**

```bash
# Just run - templates work automatically!
python main.py
```

**Output:**
```
⚠️  AI provider not available - using template fallback
```

---

## Configuration

### .env Settings

```env
# Auto-detect (checks GEMINI_API_KEY first, then OPENAI_API_KEY)
AI_DRAFT_PROVIDER=auto

# Force Gemini
AI_DRAFT_PROVIDER=gemini
GEMINI_API_KEY=AIzaSy...

# Force OpenAI
AI_DRAFT_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Custom OpenAI-compatible API
OPENAI_BASE_URL=https://custom-api.com/v1
```

### Model Selection

**Gemini Models:**
```env
GEMINI_MODEL=gemini-2.0-flash-exp      # Fast, recommended
GEMINI_MODEL=gemini-1.5-flash          # Alternative
GEMINI_MODEL=gemini-1.5-pro            # More detailed
```

**OpenAI Models:**
```env
OPENAI_MODEL=gpt-4o-mini               # Fast, cost-effective
OPENAI_MODEL=gpt-4o                    # More capable
OPENAI_MODEL=gpt-3.5-turbo             # Cheapest
```

---

## Examples

### Example 1: Meeting Request

**Incoming:**
```
Hi! Can we schedule a meeting tomorrow at 3 PM to discuss the project timeline?
```

**Gemini AI Reply:**
```
Hi! Tomorrow at 3 PM works perfectly for me. I've blocked off the time on my calendar.

Looking forward to discussing the project timeline. Should I prepare anything specific or send over an agenda beforehand?

See you tomorrow!
```

**Template Reply (Fallback):**
```
Hi Ahmed,

Thanks for your message. I'd be happy to help with this.

Could you share:
- Your preferred time slots
- Expected duration
- Any specific requirements?

Looking forward to connecting.

Best regards,
[Your Name]
```

---

### Example 2: Support Request

**Incoming:**
```
I'm having trouble logging in. It shows "invalid credentials" error since yesterday.
```

**Gemini AI Reply:**
```
Hi, sorry to hear you're having login issues. Let's get this sorted out.

First, try resetting your password using the "Forgot Password" link on the login page. Make sure to check your spam folder for the reset email.

If that doesn't work, please let me know:
1. What browser/device are you using?
2. Did you recently change your password?
3. Are you able to access any other features?

I'm here to help!
```

---

### Example 3: Question

**Incoming:**
```
What time does the office close today?
```

**Gemini AI Reply:**
```
Hi! The office closes at 6 PM today. If you need anything after hours, feel free to reach out and I'll do my best to help.
```

---

### Example 4: Personal Message

**Incoming:**
```
Hey! Are we still on for lunch this weekend?
```

**Gemini AI Reply:**
```
Hey! Yes, definitely still on! Looking forward to it. Let me know what time works best for you and if there's anywhere specific you want to go.
```

---

## Comparison

| Feature | Gemini | OpenAI | Templates |
|---------|--------|--------|-----------|
| **Quality** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Speed** | 2-3 seconds | 3-5 seconds | Instant |
| **Cost** | Free (60/min) | Paid | Free |
| **Setup** | API key | API key + $5 | None |
| **Human-like** | ✅ Excellent | ✅ Excellent | ⚠️ Good |
| **No Placeholders** | ✅ Yes | ✅ Yes | ❌ [Your Name] |
| **Context Aware** | ✅ Yes | ✅ Yes | ⚠️ Keywords |

---

## Pricing

### Gemini API (Free Tier)

- **60 requests per minute** (free)
- **1,500 requests per day** (free)
- No credit card required

**Perfect for:** Personal use, testing, low volume

### OpenAI API (Paid)

- **gpt-4o-mini**: ~$0.00015 per reply
- **gpt-4o**: ~$0.005 per reply
- Minimum $5 credit

**Perfect for:** Production, high volume, advanced features

---

## Troubleshooting

### Issue: "GEMINI_API_KEY not found"

**Solution:**
```bash
# 1. Get API key from https://makersuite.google.com/app/apikey
# 2. Add to .env file:
GEMINI_API_KEY=AIzaSy...your-key-here

# 3. Restart main.py
```

### Issue: "Module not found: google.generativeai"

**Solution:**
```bash
pip install google-generativeai
```

### Issue: "OpenAI API key invalid"

**Solution:**
1. Check key in .env is correct
2. Verify API key has credits: https://platform.openai.com/usage
3. Try: `OPENAI_API_KEY=sk-...` (no spaces)

### Issue: "Rate limit exceeded"

**Solution:**
```bash
# Gemini: Wait 1 minute, or upgrade plan
# OpenAI: Add more credits, or use gpt-3.5-turbo

# Or switch to templates temporarily
AI_DRAFT_PROVIDER=template
```

### Issue: "AI generation failed"

**Solution:**
- Check internet connection
- Verify API key is valid
- Check API quota/limits
- Fallback to templates automatically

---

## Files

| File | Purpose |
|------|---------|
| `ai_draft_generator.py` | AI draft engine (Gemini + OpenAI) |
| `.env.example` | Configuration template |
| `requirements.txt` | Python dependencies |
| `WHATSAPP_AI_SETUP.md` | This guide |

---

## API Key Setup Links

| Provider | Get API Key | Docs |
|----------|-------------|------|
| **Gemini** | https://makersuite.google.com/app/apikey | https://ai.google.dev/docs |
| **OpenAI** | https://platform.openai.com/api-keys | https://platform.openai.com/docs |

---

## Best Practices

### For Gemini:
1. ✅ Use `gemini-2.0-flash-exp` for speed
2. ✅ Free tier is sufficient for most users
3. ✅ No credit card needed

### For OpenAI:
1. ✅ Use `gpt-4o-mini` for cost efficiency
2. ✅ Set spending limits in dashboard
3. ✅ Monitor usage regularly

### For Templates:
1. ✅ Works offline
2. ✅ No API costs
3. ✅ Instant response

---

## Quick Reference

```bash
# Check what's available
python ai_draft_generator.py

# Install all dependencies
pip install -r requirements.txt

# Setup Gemini (recommended)
# 1. Get key: https://makersuite.google.com/app/apikey
# 2. Add to .env: GEMINI_API_KEY=...
# 3. Run: python main.py

# Setup OpenAI
# 1. Get key: https://platform.openai.com/api-keys
# 2. Add to .env: OPENAI_API_KEY=...
# 3. Run: python main.py

# Use templates (no setup)
python main.py
```

---

**Date:** 2026-03-07  
**Status:** ✅ PRODUCTION READY  
**Providers:** Gemini ⭐ | OpenAI | Templates
