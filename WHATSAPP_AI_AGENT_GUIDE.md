# 📱 Complete WhatsApp AI Agent Setup Guide

## Overview

Yeh complete WhatsApp AI Agent hai jo:

1. ✅ **WhatsApp Web** se messages read karta hai (Playwright se)
2. ✅ **Sender ka phone number** extract karta hai (bhale name se saved ho)
3. ✅ **Gemini AI** se smart draft reply banata hai
4. ✅ **Approved/** folder mein move karne se message send ho jata hai
5. ✅ **UltraMsg API** se automatically WhatsApp bhejta hai

---

## 📋 Requirements

### 1. Python Packages Install Karein

```bash
pip install google-generativeai playwright requests python-dotenv
playwright install chromium
```

### 2. Gemini API Key Setup Karein

1. Visit: https://makersuite.google.com/app/apikey
2. Click **"Create API Key"**
3. Copy API key
4. `.env` file mein paste karein:

```env
GEMINI_API_KEY=AIzaSy...your-key-here
GEMINI_MODEL=gemini-1.5-flash-latest
```

### 3. UltraMsg Setup (Optional - Auto-send ke liye)

Agar aap chahte hain ke messages **automatically send** hon:

1. Visit: https://ultramsg.com/
2. Sign up / Login karein
3. Create new instance
4. Copy **Instance ID** aur **Token**
5. `.env` file mein paste karein:

```env
ULTRAMSG_INSTANCE_ID=your-instance-id
ULTRAMSG_TOKEN=your-token
```

**Note:** Agar UltraMsg configure nahi hai, toh drafts manual bheje ja sakte hain (copy/paste to WhatsApp Web)

### 4. `.env` File Configure Karein

`.env.example` ko copy karke `.env` banayein:

```bash
copy .env.example .env
```

Phir edit karein:

```env
# Gemini API (Required for AI drafts)
GEMINI_API_KEY=AIzaSy...your-key-here
GEMINI_MODEL=gemini-1.5-flash-latest

# UltraMsg (Optional for auto-send)
ULTRAMSG_INSTANCE_ID=your-instance-id
ULTRAMSG_TOKEN=your-token

# WhatsApp Settings
WHATSAPP_POLL_INTERVAL=30
WHATSAPP_BROWSER_HEADLESS=false
```

---

## 🚀 Kaise Chalayein

### Step 1: Agent Start Karein

```bash
python whatsapp_ai_agent.py
```

Ya custom vault path ke saath:

```bash
python whatsapp_ai_agent.py "E:\Path\To\Vault"
```

### Step 2: WhatsApp Authenticate Karein

Jab aap pehli baar chalayein:

1. Browser open hoga
2. WhatsApp Web QR code dikhega
3. Apne phone se QR code scan karein:
   - WhatsApp > Settings > Linked Devices > Link a Device
4. Scan karne ke baad agent automatically start ho jayega

### Step 3: Messages Process Honge

Agent har 30 seconds mein:
- Naye messages check karega
- Har message ka **phone number** nikalega
- **AI draft reply** banayega
- Files create karega:
  - `Needs_Action/WHATSAPP_*.md` - Original message
  - `Pending_Approval/WHATSAPP_REPLY_*.md` - AI draft reply

---

## 📂 Folder Structure

```
Vault/
├── Needs_Action/           # New messages
│   └── WHATSAPP_abc123_20260308_230000.md
├── Pending_Approval/       # AI draft replies
│   └── WHATSAPP_REPLY_abc123.md
├── Approved/               # Move here to send
│   └── WHATSAPP_REPLY_abc123.md
├── Done/                   # Sent messages
│   └── WHATSAPP_REPLY_abc123.md
├── Contacts/
│   └── contacts.json       # Saved contacts with phones
└── In_Progress/
    └── whatsapp/
        └── processed.json  # State tracking
```

---

## 🔄 Complete Workflow

### 1. New Message Aata Hai

```
WhatsApp Web → Agent reads message → Extracts phone number
```

### 2. AI Draft Banta Hai

```
Message text → Gemini AI → Smart reply draft
```

**Example Draft:**
```
Hi Ahmed, thanks for your message! I'd be happy to help with the meeting. 
Tomorrow at 3 PM works for me. Should I send a calendar invite?

Best regards
```

### 3. Aap Review Karte Hain

File open karein: `Pending_Approval/WHATSAPP_REPLY_*.md`

- Reply check karein
- Edit karein agar zaroorat ho
- Phone number verify karein

### 4. Send Karein

**Option A: Automatic (UltraMsg configured)**
```
Move to Approved/ → Automatically sends via UltraMsg API → Moves to Done/
```

**Option B: Manual (UltraMsg not configured)**
```
Move to Approved/ → Copy message → Paste in WhatsApp Web → Moves to Done/
```

---

## 👥 Contact Management

### Phone Numbers Kaise Kaam Karte Hain

Agent automatically phone numbers manage karta hai:

1. **Pehli baar message:** Phone number extract hota hai
2. **Contacts file:** `Contacts/contacts.json` mein save hota hai
3. **Next time:** Saved number use hota hai

### Example `contacts.json`:

```json
{
  "ahmed khan": {
    "name": "Ahmed Khan",
    "phone": "+923001234567",
    "added": "2026-03-08T23:00:00"
  },
  "abu bakr": {
    "name": "Abu Bakr",
    "phone": "+923339876543",
    "added": "2026-03-08T23:05:00"
  }
}
```

### Manual Contact Add Karna

Agar phone number automatically na mile:

1. Edit karein: `Contacts/contacts.json`
2. Add entry:
```json
{
  "contact name": {
    "name": "Contact Name",
    "phone": "+923001234567"
  }
}
```

---

## 🎯 AI Reply Examples

### Business Meeting Request

**Message:**
```
Hi! Can we schedule a meeting tomorrow at 3 PM to discuss the project timeline?
```

**AI Draft:**
```
Hi! Tomorrow at 3 PM works perfectly for me. I'll prepare the project timeline 
document. Should we meet at the office or online via Zoom?

Looking forward to it!
```

### Support Query

**Message:**
```
I'm having an issue with the login page. It shows an error when I click submit.
```

**AI Draft:**
```
Thanks for reaching out. I understand you're facing a login issue.

To help better:
1. What error message do you see?
2. Which browser are you using?
3. When did this start?

I'll help resolve this quickly.
```

### General Message

**Message:**
```
Thanks for your help yesterday!
```

**AI Draft:**
```
You're welcome! Glad I could help. Feel free to reach out if you need anything else!
```

---

## ⚙️ Configuration Options

### `.env` Settings

```env
# Polling
WHATSAPP_POLL_INTERVAL=30          # Check every 30 seconds
WHATSAPP_MAX_MESSAGES_PER_POLL=20  # Max messages per check

# Browser
WHATSAPP_BROWSER_HEADLESS=false    # true = background, false = visible
WHATSAPP_BROWSER_TIMEOUT=60        # Browser timeout (seconds)

# Rate Limiting
WHATSAPP_RATE_LIMIT_HOURLY=10      # Max messages per hour

# AI
GEMINI_MODEL=gemini-1.5-flash-latest  # AI model
```

---

## 🔧 Troubleshooting

### Issue: "GEMINI_API_KEY not set"

**Solution:**
1. Check `.env` file exists
2. Verify API key is correct
3. Restart agent

### Issue: "No phone number found"

**Solution:**
1. Check `Contacts/contacts.json`
2. Add contact manually
3. Or edit draft file and add phone number

### Issue: "UltraMsg not configured"

**Solution:**
- **Option 1:** Configure UltraMsg (see setup above)
- **Option 2:** Use manual sending (copy/paste to WhatsApp Web)

### Issue: Browser doesn't start

**Solution:**
```bash
pip install playwright
playwright install chromium
```

### Issue: QR code doesn't appear

**Solution:**
1. Close browser
2. Delete `sessions/whatsapp/` folder
3. Restart agent
4. Try again

---

## 📊 Status Commands

### Check Running Agent

Agent console output:
```
[23:00:00] ✓ No new messages
[23:00:30] 📱 Found 2 new messages
[23:00:31] ✓ Created: WHATSAPP_abc123_20260308_230030.md
[23:00:32] ✓ Created draft: WHATSAPP_REPLY_abc123.md
```

### Check Logs

```bash
# Today's log file
Vault/Logs/2026-03-08.json
```

---

## 🎉 Quick Start Summary

```bash
# 1. Install packages
pip install google-generativeai playwright requests python-dotenv
playwright install chromium

# 2. Setup .env
copy .env.example .env
# Edit .env and add GEMINI_API_KEY

# 3. Run agent
python whatsapp_ai_agent.py

# 4. Authenticate WhatsApp
# Scan QR code with phone

# 5. Done! Agent is running
# Messages will be processed automatically
```

---

## 📝 Example Message Flow

### Input (WhatsApp Message)
```
From: Ahmed Khan
Phone: +923001234567
Message: "Hi! Can you send me the invoice for last month?"
```

### AI Draft (Auto-generated)
```markdown
---
type: whatsapp_reply
from: Ahmed Khan
phone: +923001234567
---

Hi Ahmed! Sure, I'll send you last month's invoice right away. 
Could you confirm which email address should I send it to?

Thanks!
```

### After Approval
```
Move to Approved/ → Sent to +923001234567 via UltraMsg → Done/
```

---

## ✅ Complete!

Ab aapka WhatsApp AI Agent ready hai! 🚀

- Messages automatically process honge
- AI smart replies banayega
- Aap approve karein aur message send ho jaye!

**Happy Automating!** 🎉
