# WhatsApp Watcher - File-Based Integration

## Overview

The WhatsApp Watcher monitors a folder for incoming WhatsApp messages and creates action files in your Obsidian Vault. This is a **file-based simulation** that works without browser automation.

## Quick Start

### 1. Run the AI Employee

```bash
python main.py
```

You'll see:
```
💬 Starting WhatsApp Watcher...
   ✓ Started (PID: XXXXX)
💬 WhatsApp Watcher RUNNING
   Poll interval: 30s
   Mode: File-based simulation (no browser)
```

### 2. Add a WhatsApp Message

Create a JSON file in `Vault/In_Progress/whatsapp/incoming/`:

```json
{
  "id": "msg_001",
  "chat_name": "John Doe",
  "chat_id": "1234567890@c.us",
  "from_name": "John Doe",
  "message": "Hi! Can we schedule a meeting tomorrow?",
  "timestamp": "2026-03-06T19:50:00",
  "is_group": false,
  "has_media": false
}
```

### 3. Watcher Processes It

Within 30 seconds, the watcher will:
1. ✅ Detect the JSON file
2. ✅ Create action file: `Vault/Needs_Action/WHATSAPP_*.md`
3. ✅ Archive the JSON: `Vault/In_Progress/whatsapp/archived/`

## Message JSON Format

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique message ID (auto-generated if missing) |
| `chat_name` | string | Name of contact or group |
| `chat_id` | string | WhatsApp chat ID |
| `from_name` | string | Sender's name |
| `message` | string | Message text |
| `timestamp` | string | ISO 8601 datetime |
| `is_group` | boolean | True if group message |
| `has_media` | boolean | True if message has media |

## Classification

Messages are automatically classified:

| Category | Keywords | Priority |
|----------|----------|----------|
| **Business** | meeting, call, project, work, deadline | Medium |
| **Support** | help, issue, problem, error | Medium |
| **Personal** | (default) | Low |
| **Spam** | winner, lottery, prize, free money | High (requires approval) |

## Integration Options

### Option 1: Manual (Current)

Manually create JSON files in the `incoming/` folder.

### Option 2: WhatsApp Web Automation (Future)

Use Playwright to scrape WhatsApp Web:

```python
from playwright.sync_api import sync_playwright

def scrape_whatsapp():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://web.whatsapp.com")
        # Wait for QR scan...
        # Extract messages...
        # Save to incoming/ folder
```

### Option 3: WhatsApp Business API (Production)

Use official WhatsApp Business API for production deployments.

### Option 4: Third-Party Services

Services like Twilio WhatsApp API can forward messages to your watcher.

## Folder Structure

```
Vault/
└── In_Progress/
    └── whatsapp/
        ├── incoming/      # Add new messages here
        ├── archived/      # Processed messages
        ├── processed_ids.json
        └── known_contacts.json
```

## Testing

### Test with Sample Message

A test message is already created. Just run:

```bash
python main.py
```

Within 30 seconds, you should see:
```
📱 Found 1 new WhatsApp message(s)
   ✓ Created action file: WHATSAPP_*.md
```

### Test Directly

```bash
# Run watcher standalone
python watchers/whatsapp_watcher.py ./Vault 30
```

## Troubleshooting

### Watcher not detecting messages?

1. Check JSON syntax is valid
2. Ensure file is in `incoming/` folder
3. Check `Vault/Logs/YYYY-MM-DD.json` for errors

### Message already processed?

Each message ID is tracked. Use unique IDs for new messages.

### Rate limit exceeded?

Watcher processes max 10 messages/hour (configurable in `.env`).

## Configuration

Edit `.env`:

```env
# Poll interval (seconds)
WHATSAPP_POLL_INTERVAL=30

# Rate limit (messages/hour)
WHATSAPP_RATE_LIMIT_HOURLY=10

# Max messages per poll
WHATSAPP_MAX_MESSAGES_PER_POLL=20
```

## Future Enhancements

- [ ] Playwright browser automation
- [ ] WhatsApp Business API integration
- [ ] Twilio WhatsApp API support
- [ ] Media file download
- [ ] Voice message transcription
- [ ] Auto-reply templates
- [ ] Group message handling

## Security Notes

⚠️ **Important:**
- Don't commit `incoming/` files with real phone numbers
- Archive processed messages regularly
- Use rate limiting to prevent abuse

---

**Need Help?** Check the main [README.md](../README.md) for general setup.
