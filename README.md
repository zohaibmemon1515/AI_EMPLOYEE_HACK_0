# 🤖 AI Employee - Silver Tier

**Production-Grade Gmail Automation with OAuth 2.0**

Autonomous email processing with human-in-the-loop approval workflow.

---

## 🚀 Quick Start

### One Command to Start Everything

```bash
python main.py
```

**What happens:**
1. ✅ Checks setup (folders, credentials, .env)
2. 🌐 Opens browser for Gmail authentication (first run only)
3. 🔐 Saves token.json securely
4. 📧 Starts Gmail monitoring (every 120 seconds)
5. 📁 Starts file system monitoring (every 30 seconds)
6. 🤖 Runs orchestrator (processes approvals every 60 seconds)

---

## ✨ Features

### Gmail Automation
- **OAuth 2.0 Authentication** - Secure desktop flow with auto browser open
- **Smart Polling** - Checks every 120 seconds (configurable)
- **Email Classification** - Sales, Support, Invoice, Spam, Internal
- **Duplicate Prevention** - Tracks processed message IDs
- **Exponential Backoff** - Handles API errors gracefully
- **Rate Limiting** - Prevents abuse (default: 5/hour)

### Intelligent Processing
- **Auto Classification** - Rule-based email categorization
- **Plan Generation** - Creates action plans automatically
- **Draft Replies** - Professional templates for each category
- **Security Rules** - Force approval for new senders, legal keywords

### Human-in-the-Loop
- **Approval Workflow** - All drafts require human approval
- **Pending_Approval/** - Drafts awaiting review
- **Approved/** - Ready to send
- **Rejected/** - Discarded drafts
- **Audit Logging** - Structured JSON logs

### MCP Integration
- **Email MCP Server** - Gmail API tools
- **send_email** - Send via Gmail
- **mark_as_read** - Mark processed emails
- **search_email** - Search inbox
- **draft_email** - Create drafts

---

## 📋 Prerequisites

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.10+ | Watcher scripts |
| Node.js | v18+ LTS | MCP servers |
| Google Account | Any Gmail | Email access |

---

## 🛠️ Setup (First Time)

### Step 1: Install Dependencies

```bash
# Python dependencies
uv sync
# or
pip install -r requirements.txt

# Node.js dependencies
npm install
```

### Step 2: Run Setup Wizard

```bash
python main.py --setup
```

This creates:
- ✅ All required folders
- ✅ `.env` configuration file
- ✅ Credentials directory structure

### Step 3: Get Gmail Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create **OAuth 2.0 Client ID** (Desktop application)
3. Download `credentials.json`
4. Save to: `credentials/gmail/credentials.json`

### Step 4: Start & Authenticate

```bash
python main.py
```

**First run:**
- 🌐 Browser opens automatically
- 🔐 Sign in with Google
- ✅ Grant Gmail permissions
- 💾 Token saved securely
- 🚀 Monitoring starts!

**Subsequent runs:**
- ✅ Uses existing token
- 🔄 Auto-refreshes if expired
- 📧 Starts monitoring immediately

---

## 📂 Directory Structure

```
silver/
├── watchers/
│   ├── base_watcher.py       # Base class for watchers
│   ├── gmail_watcher.py      # Gmail API integration
│   └── filesystem_watcher.py # File system monitoring
│
├── auth_handler.py           # OAuth 2.0 authentication
├── orchestrator.py           # Task processing & approvals
├── email_mcp_server.js       # MCP email tools server
├── main.py                   # Main entry point
│
├── Vault/                    # Obsidian vault
│   ├── Needs_Action/        # Pending items
│   ├── Plans/               # Generated action plans
│   ├── Pending_Approval/    # Drafts awaiting approval
│   ├── Approved/            # Ready to execute
│   ├── Rejected/            # Discarded items
│   ├── Done/                # Completed tasks
│   └── Logs/                # Structured JSON logs
│
├── credentials/
│   └── gmail/
│       ├── credentials.json  # OAuth credentials (gitignored)
│       └── token.json        # Auth token (gitignored)
│
├── .env                      # Configuration (gitignored)
├── .env.example              # Template
└── SETUP_INSTRUCTIONS.md     # Detailed setup guide
```

---

## 📧 Email Processing Flow

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
│    - Needs_Action/EMAIL_<id>.md      ← Action item          │
│    - Plans/PLAN_EMAIL_<id>.md        ← Action plan          │
│    - Pending_Approval/EMAIL_REPLY_<id>.md ← Draft reply     │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Human Review                                              │
│    - Review draft reply                                     │
│    - Edit if needed                                         │
│    - Move to Approved/ to send ✅                           │
│    - Move to Rejected/ to discard ❌                        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Orchestrator Executes                                     │
│    - Detects approval                                       │
│    - Calls MCP send_email tool                              │
│    - Marks original as read                                 │
│    - Logs action                                            │
│    - Moves to Done/                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Email Classification

| Category | Keywords | Priority | Auto-Reply |
|----------|----------|----------|------------|
| **Sales** | buy, purchase, pricing, quote, demo | Medium | ✅ Draft |
| **Support** | help, issue, problem, error, bug | Medium | ✅ Draft |
| **Invoice** | invoice, payment, bill, due | High | ✅ Draft |
| **Spam** | congratulations, lottery, act now | High | ❌ Archive |
| **Internal** | team, meeting, internal | Low | ✅ Draft |
| **General** | (no match) | Low | ✅ Draft |

### Approval Triggers

Emails require approval if:
- ✅ New sender (not in known senders)
- ✅ Contains legal keywords (contract, agreement, liability)
- ✅ Classified as spam
- ✅ Contains financial keywords

---

## 🔐 Security Features

### Authentication
- **OAuth 2.0 Desktop Flow** - Industry standard
- **Auto Token Refresh** - Seamless operation
- **Secure Storage** - Outside Obsidian vault
- **Scoped Permissions** - Minimum required access

### Rate Limiting
- **5 emails/hour** (configurable)
- Prevents API abuse
- Protects against runaway automation

### Approval Requirements
- **New Senders** - Always require approval
- **Legal Keywords** - Contract, agreement, liability
- **Financial** - Payments, invoices over threshold

### Audit Logging
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
    "action_file": "Vault/Needs_Action/EMAIL_abc123.md"
  }
}
```

---

## 🛠️ Commands

### Main Commands

```bash
# Start complete system
python main.py

# Run setup wizard
python main.py --setup

# Test authentication
python main.py --auth

# Gmail watcher only
python main.py --gmail-only

# Run orchestrator once
python orchestrator.py Vault

# Start MCP server
node email_mcp_server.js 8809
```

### Standalone Watcher

```bash
# Gmail watcher
python watchers/gmail_watcher.py Vault 120

# File system watcher
python watchers/filesystem_watcher.py Vault 30
```

### Authentication Management

```bash
# View token info
python auth_handler.py --info

# Force re-authentication
python auth_handler.py --force

# Revoke token
python auth_handler.py --revoke
```

---

## ⚙️ Configuration (.env)

```ini
# Gmail API OAuth 2.0
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

# Logging
LOG_LEVEL=INFO
LOG_DIR=./Logs
```

---

## 📊 Monitoring & Logs

### Log Location
```
Vault/Logs/YYYY-MM-DD.json
```

### View Logs

```bash
# Today's logs
cat Vault/Logs/$(date +%Y-%m-%d).json

# Last 10 entries (requires jq)
cat Vault/Logs/*.json | jq '.[-10:]'

# Search for errors
cat Vault/Logs/*.json | jq '.[] | select(.result == "error")'
```

### Dashboard

The orchestrator updates `Vault/Dashboard.md` with:
- Pending tasks count
- Completed tasks count
- Last updated timestamp

---

## 🤖 MCP Email Tools

The MCP server provides these tools:

```javascript
// Send email
send_email({
  to: "recipient@example.com",
  subject: "Re: Original Subject",
  body: "Email content",
  inReplyTo: "message-id"
})

// Create draft
draft_email({
  to: "recipient@example.com",
  subject: "Draft Subject",
  body: "Draft content"
})

// Mark as read
mark_as_read({ messageId: "gmail-message-id" })

// Search emails
search_email({
  query: "is:unread from:example@gmail.com",
  maxResults: 10
})

// Get email details
get_email({
  messageId: "gmail-message-id",
  includeBody: true
})
```

---

## 📅 Scheduling

### Windows Task Scheduler

**Gmail Watcher (continuous):**
```
Program: C:\path\to\uv.exe
Arguments: run python watchers/gmail_watcher.py Vault 120
Start in: E:\path\to\silver
Trigger: At log on
```

**Orchestrator (every minute):**
```
Program: C:\path\to\uv.exe
Arguments: run python orchestrator.py Vault
Start in: E:\path\to\silver
Trigger: Daily, repeat every 1 minute
```

### Linux Cron

```bash
# Gmail Watcher
@reboot cd /path/to/silver && nohup uv run python watchers/gmail_watcher.py Vault 120 > Logs/gmail_watcher.log 2>&1 &

# Orchestrator
* * * * * cd /path/to/silver && uv run python orchestrator.py Vault >> Logs/orchestrator.log 2>&1
```

---

## 🐛 Troubleshooting

### "Credentials file not found"

```bash
# Verify file exists
ls credentials/gmail/credentials.json

# Check path in .env
cat .env | grep CREDENTIALS_PATH
```

### "Token expired"

```bash
# Delete and re-authenticate
rm credentials/gmail/token.json
python main.py
```

### "Rate limit exceeded"

- Wait for hourly reset
- Or increase in `.env`: `RATE_LIMIT_HOURLY=10`

### "Email not sending"

1. Check MCP server: `node email_mcp_server.js 8809`
2. Verify `DRY_RUN=false` in `.env`
3. Check logs for errors

---

## 🔒 Security Best Practices

### ✅ DO:
- Store credentials outside vault
- Use `.env` file (gitignored)
- Enable approval requirements
- Monitor logs regularly
- Rotate credentials every 90 days

### ❌ DON'T:
- Commit credentials to git
- Store tokens in vault
- Disable approval for new senders
- Share credentials

---

## 📚 Documentation

- **Setup Guide**: `SETUP_INSTRUCTIONS.md` - Complete step-by-step setup
- **Hackathon Blueprint**: `Personal AI Employee Hackathon 0_.md`
- **Gmail API Docs**: https://developers.google.com/gmail/api
- **OAuth 2.0 Guide**: https://developers.google.com/identity/protocols/oauth2

---

## 🎯 Quick Reference

### First Run Flow
```
1. python main.py
2. Browser opens automatically
3. Sign in with Google
4. Grant permissions
5. Token saved
6. Monitoring starts!
```

### Approve Email Reply
```
1. Review draft in Pending_Approval/
2. Edit if needed
3. Move to Approved/
4. Orchestrator sends automatically
```

### Check Status
```bash
# View token info
python auth_handler.py --info

# View logs
cat Vault/Logs/*.json | jq '.[-5:]'

# Check processed count
cat Vault/In_Progress/gmail/processed_ids.json | jq '.count'
```

---

## 🚀 Ready to Start?

```bash
# Quick start
python main.py

# Or with setup
python main.py --setup
```

**Happy Automating! 🎉**
