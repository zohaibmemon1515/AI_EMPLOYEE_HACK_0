# 🚀 Quick Start - Silver Tier Gmail Automation

**Get started in 5 minutes!**

---

## Step 1: Install Dependencies (2 minutes)

```bash
# Python dependencies
uv sync
# or
pip install -r requirements.txt

# Node.js dependencies
npm install
```

---

## Step 2: Run Setup (1 minute)

```bash
python main.py --setup
```

This creates all folders and `.env` file automatically!

---

## Step 3: Get Gmail Credentials (2 minutes)

1. **Go to:** https://console.cloud.google.com/apis/credentials

2. **Create OAuth 2.0 Client ID:**
   - Click **+ CREATE CREDENTIALS** → **OAuth client ID**
   - Application type: **Desktop app**
   - Name: `AI Employee`
   - Click **Create**

3. **Download credentials.json:**
   - Click the **Download** icon
   - Save as `credentials.json`

4. **Move to correct location:**
   ```
   silver/credentials/gmail/credentials.json
   ```

---

## Step 4: Start & Authenticate (1 minute)

```bash
python main.py
```

**What happens:**
1. ✅ Folders created
2. 🌐 Browser opens automatically
3. 🔐 Sign in with Google
4. ✅ Grant Gmail permissions
5. 💾 Token saved to `credentials/gmail/token.json`
6. 🚀 Gmail monitoring starts!

---

## ✅ You're Done!

**AI Employee is now:**
- 📧 Monitoring Gmail every 120 seconds
- 📁 Watching file system every 30 seconds
- 🤖 Processing approvals every 60 seconds

---

## 📬 Test It!

1. **Send yourself an email** with subject: "Test - Interested in pricing"
2. **Mark it as unread** in Gmail
3. **Wait 120 seconds**
4. **Check these folders:**
   ```
   Vault/Needs_Action/     ← Action file created
   Vault/Plans/            ← Plan generated
   Vault/Pending_Approval/ ← Draft reply ready
   ```

---

## 📂 Approve a Draft Reply

1. Open draft in `Vault/Pending_Approval/EMAIL_REPLY_*.md`
2. Review the reply
3. **Move file to `Vault/Approved/`**
4. Orchestrator will send automatically!

---

## 🎯 Common Commands

```bash
# Start everything
python main.py

# Setup wizard
python main.py --setup

# Test authentication
python main.py --auth

# Gmail watcher only
python main.py --gmail-only

# View logs
cat Vault/Logs/*.json

# Check token info
python auth_handler.py --info
```

---

## 📖 Need Help?

- **Full Setup Guide:** `SETUP_INSTRUCTIONS.md`
- **Documentation:** `README.md`
- **Troubleshooting:** See `SETUP_INSTRUCTIONS.md` section 11

---

## 🔐 Security Notes

✅ Credentials stored outside vault  
✅ Token auto-refreshes  
✅ Approval required for new senders  
✅ Audit logging enabled  

❌ Never commit credentials  
❌ Never share token.json  
❌ Never disable approvals in production  

---

**Happy Automating! 🎉**
