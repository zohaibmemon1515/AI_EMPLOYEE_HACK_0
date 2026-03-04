# 📧 SMTP Setup Guide for Gmail

## Why Use SMTP?

SMTP is **more reliable** than Gmail API for sending emails:
- ✅ No OAuth token expiration issues
- ✅ Simpler configuration
- ✅ Works with all email clients
- ✅ Better deliverability

---

## Step 1: Enable 2-Factor Authentication

1. Go to [Google Account](https://myaccount.google.com/)
2. Click **Security** in left menu
3. Under "Signing in to Google", click **2-Step Verification**
4. Click **Get Started**
5. Follow the setup process

---

## Step 2: Generate App Password

1. Go to [App Passwords](https://myaccount.google.com/apppasswords)
2. Select app: **Mail**
3. Select device: **Other (Custom name)**
4. Enter name: `AI Employee`
5. Click **Generate**
6. **Copy the 16-character password** (save it securely)

Example: `abcd efgh ijkl mnop`

---

## Step 3: Configure .env File

Edit `.env` file in project root:

```ini
# Gmail SMTP Configuration
GMAIL_SMTP_SERVER=smtp.gmail.com
GMAIL_SMTP_PORT=587
GMAIL_SMTP_USER=your-email@gmail.com
GMAIL_SMTP_PASSWORD=abcd efgh ijkl mnop  # Your App Password (no spaces)

# Use SMTP instead of API
USE_SMTP=true
```

**Important:**
- Remove spaces from app password: `abcdefghijklmnop`
- Use your full Gmail address
- Keep `USE_SMTP=true` for SMTP mode

---

## Step 4: Test Configuration

Create test file `test_smtp.py`:

```python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()

# Config
SMTP_SERVER = os.getenv("GMAIL_SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("GMAIL_SMTP_PORT", "587"))
SMTP_USER = os.getenv("GMAIL_SMTP_USER", "")
SMTP_PASSWORD = os.getenv("GMAIL_SMTP_PASSWORD", "")

print(f"Testing SMTP connection...")
print(f"Server: {SMTP_SERVER}:{SMTP_PORT}")
print(f"User: {SMTP_USER}")

try:
    # Connect and test
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        print("✅ SMTP connection successful!")
        
except Exception as e:
    print(f"❌ SMTP connection failed: {e}")
```

Run test:
```bash
python test_smtp.py
```

---

## Step 5: Run AI Employee

```bash
python main.py
```

Now when you approve a draft:
1. Move to `Approved/` folder
2. Orchestrator detects (within 5 seconds)
3. Sends via SMTP ✅
4. Shows success message
5. Moves to `Done/` folder

---

## Troubleshooting

### "Invalid credentials"
- Check app password is correct (no spaces)
- Ensure 2FA is enabled
- Regenerate app password if needed

### "Connection timeout"
- Check firewall isn't blocking port 587
- Try port 465 (SSL) instead:
  ```ini
  GMAIL_SMTP_PORT=465
  ```

### "Less secure apps" error
- Google no longer supports "less secure apps"
- Must use **App Password** method (see Step 2)

### "Recipient address required"
- Check draft file has "from:" field in frontmatter
- Example:
  ```markdown
  ---
  from: recipient@example.com
  ---
  ```

---

## SMTP vs API Comparison

| Feature | SMTP | Gmail API |
|---------|------|-----------|
| Setup | Simple (app password) | Complex (OAuth) |
| Reliability | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Token Expiry | No | Yes (auto-refresh) |
| Rate Limits | 500/day | 1M/day |
| Best For | Personal use | Business use |

---

## Quick Reference

### SMTP Settings
```
Server: smtp.gmail.com
Port: 587 (TLS) or 465 (SSL)
Security: STARTTLS
```

### .env Template
```ini
USE_SMTP=true
GMAIL_SMTP_SERVER=smtp.gmail.com
GMAIL_SMTP_PORT=587
GMAIL_SMTP_USER=yourname@gmail.com
GMAIL_SMTP_PASSWORD=yourapppassword
```

---

## Security Notes

✅ **DO:**
- Use App Passwords (not regular password)
- Enable 2FA on your account
- Keep .env file secure (gitignored)
- Monitor sent emails regularly

❌ **DON'T:**
- Share your app password
- Commit .env to git
- Use regular Gmail password
- Disable 2FA

---

**Ready to send emails via SMTP!** 🚀
