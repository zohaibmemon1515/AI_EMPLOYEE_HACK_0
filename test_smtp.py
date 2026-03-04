#!/usr/bin/env python3
"""Test SMTP configuration."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Config
SMTP_SERVER = os.getenv("GMAIL_SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("GMAIL_SMTP_PORT", "587"))
SMTP_USER = os.getenv("GMAIL_SMTP_USER", "")
SMTP_PASSWORD = os.getenv("GMAIL_SMTP_PASSWORD", "")
USE_SMTP = os.getenv("USE_SMTP", "false").lower() == "true"

print("=" * 70)
print("SMTP Configuration Test")
print("=" * 70)
print()

print(f"SMTP Server: {SMTP_SERVER}:{SMTP_PORT}")
print(f"Username: {SMTP_USER}")
print(f"Password set: {'Yes' if SMTP_PASSWORD else 'No'}")
print(f"USE_SMTP: {USE_SMTP}")
print()

if not SMTP_USER or not SMTP_PASSWORD:
    print("⚠️  SMTP credentials not configured!")
    print()
    print("To enable SMTP:")
    print("1. Edit .env file")
    print("2. Add your Gmail address:")
    print("   GMAIL_SMTP_USER=your-email@gmail.com")
    print("3. Add app password:")
    print("   GMAIL_SMTP_PASSWORD=your-apppassword")
    print("4. Set USE_SMTP=true")
    print()
    print("See SMTP_SETUP.md for detailed instructions")
else:
    print("Testing SMTP connection...")
    print()
    
    try:
        # Connect to SMTP server
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            print(f"✓ Connected to {SMTP_SERVER}")
            
            # Login
            server.login(SMTP_USER, SMTP_PASSWORD)
            print(f"✓ Logged in as {SMTP_USER}")
            
        print()
        print("=" * 70)
        print("✅ SMTP Configuration is WORKING!")
        print("=" * 70)
        print()
        print("To send emails via SMTP:")
        print("1. Set USE_SMTP=true in .env")
        print("2. Run: python main.py")
        print("3. Approve a draft by moving to Approved/")
        print()
        
    except smtplib.SMTPAuthenticationError:
        print("❌ Authentication failed!")
        print()
        print("Possible issues:")
        print("1. App password is incorrect")
        print("2. 2FA not enabled")
        print("3. Need to generate new app password")
        print()
        print("See SMTP_SETUP.md for help")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print()
        print("Possible issues:")
        print("1. Firewall blocking port 587")
        print("2. Network connection issue")
        print("3. SMTP server unavailable")
