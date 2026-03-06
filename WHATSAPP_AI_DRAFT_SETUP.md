# 🤖 AI Draft Reply Generator - Setup Guide

## Overview

The AI Draft Generator automatically creates **smart, context-aware replies** for WhatsApp messages - just like Gmail's Smart Reply but more advanced!

---

## Two Modes

### Mode 1: AI-Powered (Recommended) ✨

Uses local LLM (Ollama) to generate intelligent replies.

**Features:**
- Context-aware responses
- Understands message intent
- Natural, conversational tone
- No placeholders like "[Your Name]"

### Mode 2: Template Fallback ⚡

Smart templates when AI is not available.

**Features:**
- Intent detection (meeting, support, question)
- Professional templates
- Works offline
- No dependencies

---

## Setup AI Mode (Recommended)

### Step 1: Install Ollama

**Windows:**
```bash
# Download from https://ollama.com
# Run installer
```

**Linux/Mac:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Step 2: Pull Model

```bash
# Download llama3.2 model (recommended)
ollama pull llama3.2
```

**Alternative models:**
```bash
ollama pull mistral      # Faster, smaller
ollama pull phi3         # Very fast
ollama pull llama3.1     # More detailed
```

### Step 3: Install Python Client

```bash
pip install ollama
```

### Step 4: Verify Installation

```bash
# Test Ollama
ollama run llama3.2 "Hello!"

# Test Python client
python -c "import ollama; print(ollama.list())"
```

### Step 5: Run WhatsApp Watcher

```bash
python main.py
```

**Expected output:**
```
💬 WhatsApp Watcher initialized
   Vault: ./Vault
   Poll Interval: 30s
   Mode: Real WhatsApp Web (Playwright)
   ✨ AI Draft Generator: ✅ Enabled (llama3.2)
   Approval Flow: ✅ Same as Gmail
```

---

## Usage Examples

### Example 1: Meeting Request

**Incoming Message:**
```
Hi! Can we schedule a meeting tomorrow at 3 PM to discuss the project timeline?
```

**AI Generated Reply:**
```
Hi! Thanks for reaching out. Tomorrow at 3 PM works for me. I've added it to my calendar.

Looking forward to discussing the project timeline. Please send over the meeting link when you get a chance.

Best regards
```

### Example 2: Support Request

**Incoming Message:**
```
I'm having trouble logging in. It shows "invalid credentials" error since yesterday.
```

**AI Generated Reply:**
```
Hi, I understand you're having login issues. Let me help you with that.

First, try resetting your password using the "Forgot Password" link. If that doesn't work, please let me know:
1. What browser are you using?
2. Did you recently change your password?
3. Are you getting the error immediately or after entering credentials?

I'll get this sorted out for you.
```

### Example 3: Question

**Incoming Message:**
```
What time does the office close today?
```

**AI Generated Reply:**
```
Hi! The office closes at 6 PM today. If you need anything after hours, feel free to reach out and I'll do my best to help.
```

### Example 4: Personal Message

**Incoming Message:**
```
Hey! Are we still on for lunch this weekend?
```

**AI Generated Reply:**
```
Hey! Yes, definitely still on! Looking forward to it. Let me know what time works best for you.
```

---

## Template Mode (Fallback)

If AI is not available, smart templates are used:

### Detection Logic

| Keywords | Template |
|----------|----------|
| problem, issue, error, help | Support Reply |
| meeting, call, schedule, tomorrow | Business Reply |
| ? (question mark) | Question Reply |
| (default) | General Reply |

### Template Examples

**Support:**
```
Hi [Name],

Thanks for reaching out. I understand you're facing an issue.

To help you better:
1. When did this start?
2. What steps have you tried?
3. Any error messages?

I'll help resolve this quickly.

Best regards,
[Your Name]
```

**Business:**
```
Hi [Name],

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

## Configuration

Edit `.env`:

```env
# AI Draft Generator
AI_DRAFT_MODEL=llama3.2     # Ollama model to use
AI_DRAFT_ENABLED=true        # Enable/disable AI drafts
```

---

## Troubleshooting

### Issue: "Ollama not installed"

**Solution:**
```bash
# Install Ollama
# Windows: Download from https://ollama.com
# Linux/Mac: curl -fsSL https://ollama.com/install.sh | sh

# Install Python client
pip install ollama
```

### Issue: "Model not found"

**Solution:**
```bash
# Pull the model
ollama pull llama3.2

# Verify
ollama list
```

### Issue: "AI generation failed"

**Solution:**
1. Check Ollama is running:
   ```bash
   ollama list
   ```
2. Test model:
   ```bash
   ollama run llama3.2 "Hello"
   ```
3. Check system resources (AI needs RAM)

### Issue: Slow response

**Solution:**
- Use smaller model: `ollama pull phi3`
- Or use template mode (no AI)

---

## Comparison

| Feature | AI Mode | Template Mode |
|---------|---------|---------------|
| **Quality** | ⭐⭐⭐⭐⭐ Human-like | ⭐⭐⭐ Good |
| **Context** | ⭐⭐⭐⭐⭐ Understands | ⭐⭐ Keyword-based |
| **Speed** | ⭐⭐⭐ 2-5 seconds | ⭐⭐⭐⭐⭐ Instant |
| **Offline** | ❌ Needs Ollama | ✅ Works offline |
| **Setup** | ⚠️ Requires install | ✅ No setup |
| **Placeholders** | ✅ None | ⚠️ [Your Name] |

---

## Files

| File | Purpose |
|------|---------|
| `ai_draft_generator.py` | AI draft generation engine |
| `watchers/whatsapp_watcher.py` | Integrated with WhatsApp |
| `WHATSAPP_AI_SETUP.md` | This guide |

---

## Quick Start

### For AI Mode:
```bash
# 1. Install Ollama
# Download from https://ollama.com

# 2. Pull model
ollama pull llama3.2

# 3. Install Python client
pip install ollama

# 4. Run
python main.py
```

### For Template Mode (No Setup):
```bash
# Just run - templates work automatically!
python main.py
```

---

## Status

| Component | Status |
|-----------|--------|
| AI Draft Generator | ✅ Available |
| Template Fallback | ✅ Built-in |
| WhatsApp Integration | ✅ Working |
| Multi-language Support | ✅ Via AI model |

---

**Date:** 2026-03-07  
**Status:** ✅ PRODUCTION READY  
**Mode:** AI + Template Fallback
