# WhatsApp Watcher Setup Guide

💬 WhatsApp Web automation using Playwright for the AI Employee system.

## Overview

The WhatsApp Watcher monitors WhatsApp Web for new messages and creates action files in your Obsidian Vault, similar to how the Gmail Watcher works with emails.

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  WhatsApp Web   │────▶│  Playwright MCP  │────▶│  WhatsApp       │
│  (Browser)      │     │  Server (Port)   │     │  Watcher        │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                       │
                                                       ▼
                                                ┌──────────────────┐
                                                │  Obsidian Vault  │
                                                │  Needs_Action/   │
                                                └──────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
# Ensure Playwright is installed
npm install -D @playwright/mcp@latest

# Or using the project's package.json
npm install
```

### 2. Configure Environment

Add these to your `.env` file:

```env
# WhatsApp settings
WHATSAPP_POLL_INTERVAL=30
WHATSAPP_BROWSER_HEADLESS=false
WHATSAPP_RATE_LIMIT_HOURLY=10
WHATSAPP_MCP_PORT=8810
```

### 3. Run the Setup

```bash
# Create necessary folders
python main.py --setup

# Start AI Employee (Gmail + WhatsApp)
python main.py
```

### 4. Authenticate WhatsApp Web

When you first run the watcher:

1. A browser window will open
2. Navigate to WhatsApp Web (https://web.whatsapp.com)
3. Scan the QR code with your phone
4. The watcher will detect your session

## Architecture

### Files Created

| File | Purpose |
|------|---------|
| `watchers/whatsapp_watcher.py` | Main WhatsApp monitoring script |
| `whatsapp_mcp_server.js` | MCP server for WhatsApp automation |
| `Vault/In_Progress/whatsapp/` | WhatsApp state storage |
| `sessions/whatsapp/` | Browser session data |

### WhatsApp Message Flow

1. **Detection**: Watcher polls WhatsApp Web every 30 seconds
2. **Classification**: Messages classified (business, personal, spam, support)
3. **Action File**: Created in `Vault/Needs_Action/WHATSAPP_*.md`
4. **Plan**: Action plan generated in `Vault/Plans/`
5. **Draft Reply**: Optional draft in `Vault/Pending_Approval/`
6. **Approval**: Move to `Approved/` to send via Playwright

### Message Classification

| Category | Keywords | Priority |
|----------|----------|----------|
| Business | meeting, call, project, work, deadline | Medium |
| Support | help, issue, problem, error | Medium |
| Personal | (default) | Low |
| Spam | winner, lottery, prize, click here | High (requires approval) |

## MCP Tools

The WhatsApp MCP server provides these tools:

| Tool | Description |
|------|-------------|
| `whatsapp_navigate` | Navigate to WhatsApp Web |
| `whatsapp_check_session` | Check authentication status |
| `whatsapp_get_messages` | Get unread messages |
| `whatsapp_click_chat` | Open a specific chat |
| `whatsapp_type_message` | Type a message |
| `whatsapp_send_message` | Send the typed message |
| `whatsapp_send_to_contact` | Complete send workflow |

### Example Tool Usage

```bash
# Check session status
python scripts/mcp-client.py call \
  -u http://localhost:8810 \
  -t whatsapp_check_session \
  -p '{}'

# Get unread messages
python scripts/mcp-client.py call \
  -u http://localhost:8810 \
  -t whatsapp_get_messages \
  -p '{"maxMessages": 20}'

# Send message to contact
python scripts/mcp-client.py call \
  -u http://localhost:8810 \
  -t whatsapp_send_to_contact \
  -p '{"chatName": "John Doe", "message": "Hello!"}'
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `WHATSAPP_POLL_INTERVAL` | 30 | Seconds between checks |
| `WHATSAPP_BROWSER_HEADLESS` | false | Run browser in background |
| `WHATSAPP_BROWSER_TIMEOUT` | 60 | Browser timeout (seconds) |
| `WHATSAPP_RATE_LIMIT_HOURLY` | 10 | Max messages per hour |
| `WHATSAPP_MCP_PORT` | 8810 | MCP server port |

## Troubleshooting

### Browser doesn't open

```bash
# Check if Playwright browsers are installed
npx playwright install
```

### QR code not appearing

1. Clear browser cache
2. Logout from WhatsApp Web
3. Restart the watcher
4. Try incognito mode

### Messages not detected

1. Check if WhatsApp Web is loaded
2. Verify session is authenticated
3. Check browser console for errors
4. Increase `WHATSAPP_POLL_INTERVAL`

### MCP server not starting

```bash
# Check if port is available
netstat -ano | findstr :8810

# Kill process using the port
taskkill /PID <PID> /F
```

## Security Notes

⚠️ **Important Security Practices:**

1. **Never commit session files** - Added to `.gitignore`
2. **Use rate limiting** - Prevents API abuse
3. **Human-in-the-Loop** - Approval required for sending
4. **Local storage only** - Sessions stored locally

## Testing

### Test WhatsApp Watcher Directly

```bash
# Run watcher with verbose logging
python watchers/whatsapp_watcher.py ./Vault --interval 10
```

### Test MCP Server

```bash
# Start server
node whatsapp_mcp_server.js 8810

# In another terminal, test tools
python scripts/mcp-client.py call \
  -u http://localhost:8810 \
  -t whatsapp_navigate \
  -p '{}'
```

## Integration with Main App

The WhatsApp watcher runs alongside Gmail in `main.py`:

```python
# Gmail Watcher (60s interval)
subprocess.Popen([python, gmail_watcher.py, vault, 60])

# WhatsApp Watcher (30s interval)
subprocess.Popen([python, whatsapp_watcher.py, vault, 30])

# Orchestrator (Approved folder)
subprocess.Popen([python, orchestrator.py, vault])
```

## Future Enhancements

- [ ] Group message handling
- [ ] Media file download
- [ ] End-to-end encrypted backup
- [ ] Multi-device support
- [ ] Voice message transcription
- [ ] Auto-reply templates

## Resources

- [WhatsApp Web Documentation](https://web.whatsapp.com)
- [Playwright MCP](https://github.com/microsoft/playwright-mcp)
- [Gmail Watcher](./watchers/gmail_watcher.py) - Reference implementation

---

**Need Help?** Check the main [README.md](../README.md) for general setup instructions.
