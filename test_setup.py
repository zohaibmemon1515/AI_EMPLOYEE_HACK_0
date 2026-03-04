#!/usr/bin/env python3
"""Test script to verify Gmail Watcher setup."""

import sys
from pathlib import Path

print("=" * 70)
print("Gmail Watcher - Setup Verification")
print("=" * 70)
print()

base_dir = Path(__file__).parent

# Check Python version
print(f"✓ Python version: {sys.version_info.major}.{sys.version_info.minor}")

# Check credentials
creds = base_dir / "credentials" / "gmail" / "credentials.json"
if creds.exists():
    print(f"✓ credentials.json: EXISTS")
else:
    print(f"⚠️  credentials.json: NOT FOUND")
    print(f"   Path: {creds}")

# Check token
token = base_dir / "credentials" / "gmail" / "token.json"
if token.exists():
    print(f"✓ token.json: EXISTS (authenticated)")
else:
    print(f"⚠️  token.json: NOT FOUND (will create on first run)")

# Check .env
env = base_dir / ".env"
if env.exists():
    print(f"✓ .env: EXISTS")
else:
    print(f"⚠️  .env: NOT FOUND")

# Check vault
vault = base_dir / "Vault"
if vault.exists():
    print(f"✓ Vault: EXISTS")
else:
    print(f"⚠️  Vault: NOT FOUND")

# Check watcher script
watcher = base_dir / "watchers" / "gmail_watcher.py"
if watcher.exists():
    print(f"✓ gmail_watcher.py: EXISTS")
else:
    print(f"⚠️  gmail_watcher.py: NOT FOUND")

# Check dependencies
print("\nChecking dependencies...")
try:
    import dotenv
    print("✓ python-dotenv")
except:
    print("✗ python-dotenv MISSING")

try:
    import google.auth
    print("✓ google-auth")
except:
    print("✗ google-auth MISSING")

try:
    import google_auth_oauthlib
    print("✓ google-auth-oauthlib")
except:
    print("✗ google-auth-oauthlib MISSING")

try:
    import googleapiclient
    print("✓ google-api-python-client")
except:
    print("✗ google-api-python-client MISSING")

print()
print("=" * 70)
print("Verification Complete!")
print("=" * 70)
print()

if creds.exists():
    print("✅ Ready to run!")
    print()
    print("Command: python main.py")
    print()
    print("Note: Browser will open for Gmail authentication on first run")
else:
    print("⚠️  Missing credentials.json")
    print()
    print("To get started:")
    print("1. Go to: https://console.cloud.google.com/apis/credentials")
    print("2. Create OAuth 2.0 Client ID (Desktop application)")
    print("3. Download credentials.json")
    print(f"4. Save to: {creds}")
