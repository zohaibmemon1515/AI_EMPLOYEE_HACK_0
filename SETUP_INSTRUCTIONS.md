# 📧 Silver Tier Gmail Automation - Complete Setup Guide

## Overview

This guide provides step-by-step instructions to set up production-grade Gmail automation with OAuth 2.0 authentication for your AI Employee system.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Google Cloud Setup](#1-google-cloud-setup)
3. [File Structure Setup](#2-file-structure-setup)
4. [Install Dependencies](#3-install-dependencies)
5. [First-Time Authentication](#4-first-time-authentication)
6. [Verify Setup](#5-verify-setup)
7. [Configure MCP Server](#6-configure-mcp-server)
8. [Human-in-the-Loop Workflow](#7-human-in-the-loop-workflow)
9. [Production Configuration](#8-production-configuration)
10. [Scheduling](#9-scheduling)
11. [Security Best Practices](#10-security-best-practices)
12. [Troubleshooting](#11-troubleshooting)
13. [Monitoring & Logs](#12-monitoring--logs)

---

## Prerequisites

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.10+ | Watcher scripts |
| Node.js | v18+ LTS | MCP servers |
| Google Account | Any Gmail | Email access |
| Git | Latest | Version control |

---

## 1. Google Cloud Setup

### 1.1 Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Create Project** (top left)
3. Project name: `AI Employee Gmail`
4. Click **Create**
5. Wait for project creation (10-20 seconds)

### 1.2 Enable Gmail API

1. In your project, navigate to **APIs & Services** → **Library**
2. Search for "Gmail API"
3. Click **Gmail API** from results
4. Click **Enable** button
5. Wait for API to be enabled (green checkmark)

### 1.3 Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** user type
3. Click **Create**

**App Information:**
- App name: `AI Employee Gmail`
- User support email: Your email address
- App logo: (optional)
- App domain: Leave blank for testing
- Developer contact: Your email address

4. Click **Save and Continue**

**Scopes:**
5. Click **Add or Remove Scopes**
6. Select these scopes:
   - `.../auth/gmail.modify` - Read, compose, send, and permanently delete your Gmail
   - `.../auth/gmail.send` - Send email on your behalf
7. Click **Update**
8. Click **Save and Continue**

**Test Users:**
9. Click **Add Users**
10. Add your Gmail address
11. Click **Save and Continue**

### 1.4 Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
3. Application type: **Desktop app**
4. Name: `AI Employee Desktop Client`
5. Click **Create**

### 1.5 Download Credentials

1. Click the **Download** icon (down arrow) next to your newly created credentials
2. Save the file as `credentials.json`
3. **Important:** Keep this file secure!

---

## 2. File Structure Setup

### 2.1 Create Credentials Directory

```bash
# From project root (silver folder)
mkdir -p credentials/gmail
```

### 2.2 Move Credentials File

Move your downloaded `credentials.json` to:

```
silver/credentials/gmail/credentials.json
```

**⚠️ SECURITY WARNING:**
- Never store `credentials.json` inside the Obsidian vault
- Never commit credentials files to version control
- Keep this file private and secure

### 2.3 Create .env File

```bash
# Copy the template
cp .env.example .env
```

Edit `.env` with your settings (optional - defaults work for most cases):

```ini
# Paths (relative to project root)
GMAIL_CREDENTIALS_PATH=./credentials/gmail/credentials.json
GMAIL_TOKEN_PATH=./credentials/gmail/token.json

# Watcher Configuration
GMAIL_POLL_INTERVAL=120

# Security Settings
DEV_MODE=true
DRY_RUN=true
RATE_LIMIT_HOURLY=5
FORCE_APPROVAL_NEW_SENDER=true
FORCE_APPROVAL_LEGAL_KEYWORDS=true
```

---

## 3. Install Dependencies

### 3.1 Python Dependencies

```bash
# Using UV (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

### 3.2 Node.js Dependencies (for MCP Server)

```bash
# Install MCP email server dependencies
npm install
```

This installs:
- `@modelcontextprotocol/sdk` - MCP protocol
- `googleapis` - Gmail API client
- `dotenv` - Environment variables

---

## 4. First-Time Authentication

### 4.1 Run Gmail Watcher

```bash
python watchers/gmail_watcher.py Vault 120
```

### 4.2 Complete OAuth Flow

**What happens:**

1. ✅ Watcher checks for `token.json`
2. ⚠️ No token found - first run detected
3. 🌐 Browser window opens automatically
4. 🔐 Google login screen appears
5. 👤 Sign in with your Gmail account
6. ✅ Grant permissions to AI Employee
7. 🔄 Browser receives authorization code
8. 💾 `token.json` is generated and saved
9. ✅ Authentication complete!
10. 🚀 Monitoring loop starts automatically

**Expected Output:**

```
======================================================================
🔐 Gmail Authentication
======================================================================

⚠️  No token file found - first run detected

📋 What will happen:
   1. Browser will open automatically
   2. Sign in with your Google account
   3. Grant permissions to access Gmail
   4. Browser will close automatically
   5. Token will be saved securely

🌐 Opening browser for authentication...

✅ AUTHENTICATION SUCCESSFUL!

✓ Token saved to: credentials/gmail/token.json
✓ Scopes granted: gmail.modify, gmail.send
✓ Token expires: 2026-03-04T12:00:00Z

🚀 Starting Gmail monitoring...

======================================================================
✅ Gmail Watcher is now RUNNING
======================================================================
```

### 4.3 Token Management

**Token Location:**
- Saved to: `credentials/gmail/token.json`
- Auto-refreshes when expired
- Stored outside Obsidian vault for security

**Revoke Access:**
- Go to [Google Account Permissions](https://myaccount.google.com/permissions)
- Find "AI Employee Gmail"
- Click **Remove Access**

---

## 5. Verify Setup

### 5.1 Test Gmail Watcher

```bash
python watchers/gmail_watcher.py Vault 120
```

**Expected behavior:**
- No browser opens (token exists)
- Starts monitoring immediately
- Checks Gmail every 120 seconds

### 5.2 Send Test Email

1. Send email to yourself with subject: **"Test - Interested in pricing"**
2. Mark it as **unread** in Gmail
3. Wait up to 120 seconds

### 5.3 Check Action Files

Verify these files are created:

```
Vault/Needs_Action/EMAIL_<id>_<timestamp>.md    ← Action file
Vault/Plans/PLAN_EMAIL_<id>.md                   ← Plan generated
Vault/Pending_Approval/EMAIL_REPLY_<id>.md      ← Draft reply
```

### 5.4 Verify Email Classification

Open the action file and check:

```markdown
---
type: email
classification: sales
priority: medium
requires_approval: true
---
```

---

## 6. Configure MCP Server

### 6.1 Start MCP Server

```bash
node email_mcp_server.js 8809
```

**Expected output:**
```
============================================================
📧 Email MCP Server
============================================================
Credentials: ./credentials/gmail/credentials.json
Token: ./credentials/gmail/token.json
Port: 8809
============================================================

Email MCP Server running on stdio
```

### 6.2 Available MCP Tools

| Tool | Description |
|------|-------------|
| `send_email` | Send email via Gmail API |
| `draft_email` | Create draft without sending |
| `mark_as_read` | Mark email as read |
| `search_email` | Search emails with query |
| `get_email` | Get specific email details |
| `archive_email` | Archive (remove from inbox) |
| `delete_email` | Permanently delete email |

### 6.3 Test MCP Tools

Example tool call (via MCP client):

```json
{
  "tool": "search_email",
  "params": {
    "query": "is:unread",
    "maxResults": 5
  }
}
```

---

## 7. Human-in-the-Loop Workflow

### 7.1 Email Processing Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Gmail Watcher detects new email                         │
│    - Polls every 120 seconds                                │
│    - Query: is:unread OR is:important                       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Classification Engine                                     │
│    - Analyzes content                                       │
│    - Categories: sales/support/invoice/spam/internal        │
│    - Detects legal keywords                                 │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Create Action Files                                       │
│    - Needs_Action/EMAIL_<id>.md                             │
│    - Plans/PLAN_EMAIL_<id>.md                               │
│    - Pending_Approval/EMAIL_REPLY_<id>.md                   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Human Review                                              │
│    - Review draft reply                                     │
│    - Edit if needed                                         │
│    - Move to Approved/ to send                              │
│    - Move to Rejected/ to discard                           │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Orchestrator Detects Approval                             │
│    - Watches Approved/ folder                               │
│    - Calls MCP send_email tool                              │
│    - Marks original as read                                 │
│    - Logs action                                            │
│    - Moves to Done/                                         │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Approving Email Replies

1. Navigate to `Vault/Pending_Approval/`
2. Open `EMAIL_REPLY_<id>.md`
3. Review the draft reply
4. Edit if needed
5. **Move file to `Vault/Approved/`**
6. Orchestrator will send automatically (within 60 seconds)

### 7.3 Rejecting Email Replies

1. Open the draft file
2. Add comment explaining rejection
3. **Move file to `Vault/Rejected/`**

---

## 8. Production Configuration

### 8.1 Update .env for Production

```ini
# Disable dry run (actually send emails)
DRY_RUN=false

# Disable dev mode (less verbose logging)
DEV_MODE=false

# Adjust rate limit as needed
RATE_LIMIT_HOURLY=10

# Keep approval requirements enabled
FORCE_APPROVAL_NEW_SENDER=true
FORCE_APPROVAL_LEGAL_KEYWORDS=true
```

### 8.2 Configure Internal Domains

Add to `.env`:

```ini
INTERNAL_DOMAINS=yourcompany.com,subsidiary.com
```

Or edit `watchers/gmail_watcher.py`:

```python
self.classifier = EmailClassifier(
    internal_domains=["yourcompany.com", "subsidiary.com"]
)
```

---

## 9. Scheduling

### Option A: Windows Task Scheduler

**Gmail Watcher (runs continuously):**

1. Open **Task Scheduler**
2. Click **Create Basic Task**
3. Name: `Gmail Watcher`
4. Trigger: **When I log on**
5. Action: **Start a program**
6. Program/script:
   ```
   C:\path\to\uv.exe
   ```
7. Arguments:
   ```
   run python watchers/gmail_watcher.py Vault 120
   ```
8. Start in:
   ```
   E:\Web Development\Governer Course\Q4\Hackhathon 0\silver
   ```
9. Check **Open Properties**
10. Check **Run with highest privileges**

**Orchestrator (runs every minute):**

1. Create another task: `AI Employee Orchestrator`
2. Trigger: **Daily**, repeat task every **1 minute**
3. Action:
   ```
   Program: C:\path\to\uv.exe
   Arguments: run python orchestrator.py Vault
   Start in: E:\path\to\silver
   ```

### Option B: Cron (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Gmail Watcher (runs continuously in background)
@reboot cd /path/to/silver && nohup uv run python watchers/gmail_watcher.py Vault 120 > Logs/gmail_watcher.log 2>&1 &

# Orchestrator (runs every minute)
* * * * * cd /path/to/silver && uv run python orchestrator.py Vault >> Logs/orchestrator.log 2>&1
```

### Option C: Systemd Service (Linux)

**Create service file:**

```bash
sudo nano /etc/systemd/system/gmail-watcher.service
```

**Content:**
```ini
[Unit]
Description=Gmail Watcher for AI Employee
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/silver
ExecStart=/path/to/uv run python watchers/gmail_watcher.py Vault 120
Restart=always
RestartSec=10
Environment="PATH=/path/to/uv"

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable gmail-watcher
sudo systemctl start gmail-watcher
sudo systemctl status gmail-watcher
```

### Option D: Start Script (All Platforms)

**Create `start_ai_employee.py`:**

```python
#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

base_dir = Path(__file__).parent

# Start Gmail Watcher
print("📧 Starting Gmail Watcher...")
subprocess.Popen([
    sys.executable,
    str(base_dir / "watchers" / "gmail_watcher.py"),
    str(base_dir / "Vault"),
    "120"
])

print("✅ Gmail Watcher started!")
print("Press Ctrl+C to stop")

try:
    while True:
        import time
        time.sleep(60)
except KeyboardInterrupt:
    print("\n🛑 Stopping...")
```

---

## 10. Security Best Practices

### ✅ DO:

1. **Store credentials securely**
   - Outside Obsidian vault
   - In `credentials/` folder
   - With restrictive file permissions

2. **Use .env file**
   - Never hardcode secrets
   - Add to `.gitignore`
   - Use different files for dev/prod

3. **Enable approval requirements**
   - `FORCE_APPROVAL_NEW_SENDER=true`
   - `FORCE_APPROVAL_LEGAL_KEYWORDS=true`

4. **Monitor logs regularly**
   - Check `Vault/Logs/` daily
   - Review failed authentications
   - Audit sent emails

5. **Rotate credentials**
   - Every 90 days
   - If compromised, revoke immediately
   - Update token.json

### ❌ DON'T:

1. **Never commit credentials**
   - Add to `.gitignore`
   - Don't share via email
   - Don't paste in chat

2. **Never store in vault**
   - Obsidian syncs to cloud
   - Credentials would be exposed
   - Violates security best practices

3. **Never disable approvals in production**
   - Always review before sending
   - Especially for new senders
   - Legal/contract emails

4. **Never share token.json**
   - Contains refresh token
   - Grants full Gmail access
   - Treat like a password

---

## 11. Troubleshooting

### Issue: "Credentials file not found"

**Solution:**
```bash
# Verify file exists
ls credentials/gmail/credentials.json

# Check path in .env
cat .env | grep CREDENTIALS_PATH

# Ensure correct path
# Should be: ./credentials/gmail/credentials.json
```

### Issue: "Token expired"

**Solution:**
Token should auto-refresh. If not:

```bash
# Delete old token
rm credentials/gmail/token.json

# Re-authenticate
python watchers/gmail_watcher.py Vault 120
```

### Issue: "Rate limit exceeded"

**Solution:**
1. Wait for hourly reset
2. Or increase limit in `.env`:
   ```ini
   RATE_LIMIT_HOURLY=10
   ```
3. Check Gmail API quotas in Cloud Console

### Issue: "Email not sending"

**Solution:**
1. Check MCP server is running:
   ```bash
   node email_mcp_server.js 8809
   ```
2. Verify `DRY_RUN=false` in `.env`
3. Check token has send scope:
   ```bash
   python auth_handler.py --info
   ```
4. Check logs for errors:
   ```bash
   cat Vault/Logs/*.json | jq '.[-10:]'
   ```

### Issue: "Duplicate emails processed"

**Solution:**
1. Check `processed_ids.json` exists:
   ```bash
   cat Vault/In_Progress/gmail/processed_ids.json
   ```
2. Verify file is writable
3. Restart watcher to reload state

### Issue: "Browser doesn't open for authentication"

**Solution:**
1. Check firewall isn't blocking port 8080
2. Manually visit URL shown in console
3. Or run authentication separately:
   ```bash
   python auth_handler.py --force
   ```

---

## 12. Monitoring & Logs

### Log Location

```
Vault/Logs/YYYY-MM-DD.json
```

### Log Format

```json
{
  "timestamp": "2026-03-04T10:30:00",
  "action_type": "email_processed",
  "email_id": "18e42abc...",
  "actor": "gmail_watcher",
  "approval_status": "pending",
  "result": "success",
  "details": {
    "classification": "sales",
    "action_file": "Vault/Needs_Action/EMAIL_abc123.md",
    "plan_file": "Vault/Plans/PLAN_EMAIL_abc123.md",
    "draft_file": "Vault/Pending_Approval/EMAIL_REPLY_abc123.md"
  }
}
```

### View Recent Logs

```bash
# Last 10 entries (requires jq)
cat Vault/Logs/$(date +%Y-%m-%d).json | jq '.[-10:]'

# Search for errors
cat Vault/Logs/*.json | jq '.[] | select(.result == "error")'

# Count emails processed today
cat Vault/Logs/$(date +%Y-%m-%d).json | jq '[.[] | select(.action_type == "email_processed")] | length'
```

### Dashboard Updates

The orchestrator updates `Vault/Dashboard.md` with:
- Pending tasks count
- Completed tasks count
- Last updated timestamp

---

## Quick Reference Commands

```bash
# Start Gmail Watcher
python watchers/gmail_watcher.py Vault 120

# Run Orchestrator once
python orchestrator.py Vault

# Start MCP Server
node email_mcp_server.js 8809

# Test authentication
python auth_handler.py --info

# Force re-authentication
python auth_handler.py --force

# Revoke token
python auth_handler.py --revoke

# View today's logs
cat Vault/Logs/$(date +%Y-%m-%d).json

# Check processed emails count
python -c "import json; print(json.load(open('Vault/In_Progress/gmail/processed_ids.json'))['count'])"

# List known senders
cat Vault/In_Progress/gmail/known_senders.json | jq '.senders'
```

---

## Resources

- **Gmail API Docs**: https://developers.google.com/gmail/api
- **OAuth 2.0 Guide**: https://developers.google.com/identity/protocols/oauth2
- **Google Cloud Console**: https://console.cloud.google.com/
- **MCP Protocol**: https://modelcontextprotocol.io/
- **WhatsApp Watcher**: See [WHATSAPP_README.md](WHATSAPP_README.md)

---

## WhatsApp Integration (Bonus)

### Quick Setup

The WhatsApp watcher uses a **file-based approach** - no browser automation required!

### How It Works

1. Create JSON files in `Vault/In_Progress/whatsapp/incoming/`
2. Watcher detects and processes them (every 30 seconds)
3. Creates action files in `Vault/Needs_Action/`
4. Same workflow as Gmail: Plans → Draft → Approval → Send

### Add WhatsApp Message

```json
{
  "id": "msg_001",
  "chat_name": "Ahmed Khan",
  "chat_id": "923001234567@c.us",
  "from_name": "Ahmed Khan",
  "message": "Hi! Can we schedule a meeting?",
  "timestamp": "2026-03-06T19:50:00",
  "is_group": false,
  "has_media": false
}
```

### Test Message Included

A test message is already created. Run `python main.py` and wait ~30 seconds.

### Documentation

See [WHATSAPP_README.md](WHATSAPP_README.md) for complete details.

---

## Support

For issues or questions:
1. Check logs in `Vault/Logs/`
2. Review this setup guide
3. Verify `.env` configuration
4. Check credentials file location
5. Test authentication separately

**Security Contact:**
- Revoke compromised tokens: https://myaccount.google.com/permissions
- Report security issues to your system administrator
