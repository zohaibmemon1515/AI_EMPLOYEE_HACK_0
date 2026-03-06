# 💬 WhatsApp Watcher - Real WhatsApp Web Automation

## Overview

The WhatsApp Watcher uses **Playwright** to automate real WhatsApp Web - just like Gmail Watcher uses the Gmail API. It monitors your actual WhatsApp messages and creates action files in your Obsidian Vault.

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  WhatsApp Web   │────▶│   Playwright     │────▶│  WhatsApp       │
│  (Real Browser) │     │   Browser        │     │  Watcher        │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                       │
                                                       ▼
                                                ┌──────────────────┐
                                                │  Obsidian Vault  │
                                                │  Needs_Action/   │
                                                └──────────────────┘
```

## Quick Start

### 1. Install Playwright

```bash
# Install Python package
pip install playwright

# Install browser binaries
playwright install chromium
```

### 2. Run AI Employee

```bash
python main.py
```

### 3. First-Time Authentication

On first run:
1. Browser window opens automatically
2. WhatsApp Web loads
3. QR code appears
4. Scan with your phone:
   - Open WhatsApp on phone
   - Settings > Linked Devices
   - Link a Device
   - Scan QR code
5. Session is saved for future runs

### 4. Monitoring Starts

After authentication:
- Watches WhatsApp Web every 30 seconds
- Detects unread messages automatically
- Creates action files in `Vault/Needs_Action/`

## How It Works

### Architecture

```python
# Gmail Watcher (API-based)
Gmail API → gmail_watcher.py → Needs_Action/

# WhatsApp Watcher (Browser-based)
WhatsApp Web → Playwright → whatsapp_watcher.py → Needs_Action/
```

### Message Flow

1. **Browser Opens**: Chromium launches with persistent session
2. **Navigate to WhatsApp**: Loads web.whatsapp.com
3. **Check Authentication**: Verifies QR scan status
4. **Poll for Messages**: Every 30 seconds:
   - Extract chat list
   - Find unread messages
   - Parse message content
5. **Create Action Files**: For each new message:
   - `Vault/Needs_Action/WHATSAPP_*.md`
   - `Vault/Plans/PLAN_EMAIL_*.md`
   - `Vault/Pending_Approval/EMAIL_REPLY_*.md`
6. **Mark as Processed**: Track message IDs to avoid duplicates

### Session Persistence

- **First Run**: QR scan required
- **Subsequent Runs**: Session loaded from `sessions/whatsapp/`
- **Session Expires**: Re-scan QR code

## Configuration

Edit `.env`:

```env
# WhatsApp Settings
WHATSAPP_POLL_INTERVAL=30           # Check every 30 seconds
WHATSAPP_BROWSER_HEADLESS=false     # Show browser window
WHATSAPP_BROWSER_TIMEOUT=60         # Page load timeout
WHATSAPP_RATE_LIMIT_HOURLY=10       # Max messages per hour
WHATSAPP_MAX_MESSAGES_PER_POLL=20   # Max chats to check
WHATSAPP_SESSION_PATH=./sessions/whatsapp  # Session storage
```

## Features

### Automatic Classification

| Category | Keywords | Priority |
|----------|----------|----------|
| **Business** | meeting, call, project, work, deadline | Medium |
| **Support** | help, issue, problem, error | Medium |
| **Personal** | (default) | Low |
| **Spam** | winner, lottery, prize, free money | High |

### Message Processing

- ✅ Unread message detection
- ✅ Group message support
- ✅ Media message detection
- ✅ Contact tracking (new vs known)
- ✅ Duplicate prevention
- ✅ Rate limiting
- ✅ Structured logging

### Browser Automation

- ✅ Persistent sessions (QR scan once)
- ✅ Auto-reconnect on disconnect
- ✅ Headless or visible mode
- ✅ Multi-chat monitoring
- ✅ Message extraction
- ✅ Send message capability (future)

## Usage Examples

### Run Standalone

```bash
# Default settings (30s interval)
python watchers/whatsapp_watcher.py ./Vault

# Custom interval
python watchers/whatsapp_watcher.py ./Vault 60
```

### Run with Main App

```bash
python main.py
```

Starts:
- Gmail Watcher (60s)
- WhatsApp Watcher (30s)
- Orchestrator (5s)

### Check Logs

```bash
# Today's WhatsApp logs
cat Vault/Logs/$(date +%Y-%m-%d).json | jq '.[] | select(.actor == "whatsapp_watcher")'

# Count messages processed
cat Vault/In_Progress/whatsapp/processed_ids.json | jq '.count'
```

## Troubleshooting

### Issue: Browser doesn't open

**Solution:**
```bash
# Install Playwright browsers
playwright install chromium

# Verify installation
python -c "from playwright.sync_api import sync_playwright; print('OK')"
```

### Issue: QR code not appearing

**Solution:**
1. Clear session data:
   ```bash
   rm -rf sessions/whatsapp/*
   ```
2. Restart watcher
3. Check internet connection

### Issue: "Not authenticated" message

**Solution:**
- Wait for QR code to load (up to 60 seconds)
- Refresh WhatsApp Web manually in browser
- Re-scan QR code with phone

### Issue: Messages not detected

**Solution:**
1. Check if messages are marked as unread in WhatsApp
2. Verify WhatsApp Web is loaded (not logged out)
3. Check browser console for errors
4. Increase poll interval in `.env`

### Issue: Session expires frequently

**Solution:**
- Don't logout from WhatsApp Web manually
- Keep browser session files in `sessions/whatsapp/`
- Re-authenticate when needed (QR scan)

## Comparison: Gmail vs WhatsApp Watcher

| Feature | Gmail Watcher | WhatsApp Watcher |
|---------|---------------|------------------|
| **Source** | Gmail API | WhatsApp Web |
| **Auth** | OAuth 2.0 | QR Code |
| **Protocol** | REST API | Browser Automation |
| **Poll Interval** | 60s | 30s |
| **Session** | token.json | Browser profile |
| **Rate Limit** | 5/hour | 10/hour |

## Security Notes

⚠️ **Important:**

1. **Session Storage**: `sessions/whatsapp/` contains authentication data
   - Don't share this folder
   - Added to `.gitignore`
   
2. **QR Code**: Only scan on trusted computers
   - Logout from Linked Devices when done
   - Monitor active sessions in WhatsApp

3. **Rate Limiting**: Respect WhatsApp's limits
   - Don't poll too frequently
   - Stay under 10 messages/hour

4. **Browser Security**: Keep Playwright updated
   ```bash
   pip install --upgrade playwright
   playwright install chromium
   ```

## Advanced Usage

### Send Messages (Future)

```python
# In development - will be available soon
whatsapp_client.send_message("Ahmed Khan", "Meeting at 3 PM")
```

### Read Specific Chat

```python
# Open a specific chat
whatsapp_client.click_chat("Ahmed Khan")

# Get messages from that chat
messages = whatsapp_client.get_chat_messages()
```

### Group Messages

```python
# Groups are detected automatically
# is_group=True in message metadata
# Classification works same as individual messages
```

## Files Created

| File/Folder | Purpose |
|-------------|---------|
| `sessions/whatsapp/` | Browser session data |
| `Vault/In_Progress/whatsapp/processed_ids.json` | Track processed messages |
| `Vault/In_Progress/whatsapp/known_contacts.json` | Known contacts list |
| `Vault/Needs_Action/WHATSAPP_*.md` | Message action files |
| `Vault/Plans/PLAN_EMAIL_*.md` | Action plans |
| `Vault/Pending_Approval/EMAIL_REPLY_*.md` | Draft replies |
| `Vault/Logs/YYYY-MM-DD.json` | Structured logs |

## Resources

- [Playwright Docs](https://playwright.dev/python/)
- [WhatsApp Web](https://web.whatsapp.com/)
- [Gmail Watcher](watchers/gmail_watcher.py) - Reference implementation

---

**Status**: ✅ Production Ready  
**Mode**: Real WhatsApp Web via Playwright  
**Last Updated**: 2026-03-06
