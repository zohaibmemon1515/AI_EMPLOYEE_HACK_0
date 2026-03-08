#!/usr/bin/env python3
r"""
WhatsApp Contacts Exporter - UltraMsg API

Exports all WhatsApp contacts from UltraMsg to contacts.json

Usage:
    python export_whatsapp_contacts.py
"""

import requests
import json
import os
from pathlib import Path
from datetime import datetime

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# Configuration
INSTANCE_ID = os.getenv("ULTRAMSG_INSTANCE_ID", "")
TOKEN = os.getenv("ULTRAMSG_TOKEN", "")

OUTPUT_FILE = "Vault/Contacts/contacts.json"


def get_contacts():
    """Fetch contacts from UltraMsg API."""
    
    if not INSTANCE_ID or not TOKEN:
        print("❌ UltraMsg credentials not found")
        print("\n💡 Add to .env file:")
        print(f"   ULTRAMSG_INSTANCE_ID=your-instance-id")
        print(f"   ULTRAMSG_TOKEN=your-token")
        return []
    
    url = f"https://api.ultramsg.com/{INSTANCE_ID}/contacts"
    params = {"token": TOKEN}
    
    print(f"📡 Fetching contacts from UltraMsg...")
    print(f"   Instance: {INSTANCE_ID}")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("ok") == "true":
            contacts = result.get("contacts", [])
            print(f"✅ Found {len(contacts)} contacts")
            return contacts
        else:
            print(f"❌ API error: {result}")
            return []
            
    except requests.exceptions.Timeout:
        print("❌ Timeout - check internet connection")
        return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []


def clean_phone(phone):
    """Clean and format phone number."""
    if not phone:
        return ""
    
    # Keep only digits and +
    phone = ''.join(c for c in phone if c.isdigit() or c == '+')
    
    # Add country code if missing (Pakistan)
    if phone.startswith('0'):
        phone = '+92' + phone[1:]
    elif phone.startswith('3') and len(phone) == 10:
        phone = '+92' + phone
    elif phone.startswith('92') and len(phone) == 11:
        phone = '+' + phone
    elif len(phone) >= 10 and not phone.startswith('+'):
        phone = '+' + phone
    
    return phone


def save_contacts(ultra_contacts):
    """Convert and save to contacts.json."""
    
    contacts = {}
    skipped = 0
    
    for contact in ultra_contacts:
        # UltraMsg contact format
        name = contact.get("name", "").strip()
        phone = contact.get("phone", "").strip()
        
        if not name or not phone:
            skipped += 1
            continue
        
        # Clean phone
        phone = clean_phone(phone)
        
        if len(phone) < 10:
            print(f"⚠️  Skipping {name}: Invalid phone ({phone})")
            skipped += 1
            continue
        
        # Create entry
        key = name.lower().strip()
        contacts[key] = {
            "name": name,
            "phone": phone,
            "added": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat()
        }
    
    # Save to JSON
    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(contacts, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved {len(contacts)} contacts")
    if skipped > 0:
        print(f"⚠️  Skipped {skipped} (invalid data)")
    print(f"📁 File: {output_path.absolute()}")
    
    return contacts


def show_preview(contacts):
    """Show preview of contacts."""
    
    print("\n📋 Preview (first 10):")
    print("-" * 70)
    
    for i, (key, data) in enumerate(list(contacts.items())[:10], 1):
        print(f"{i:2}. {data['name']:25} → {data['phone']}")
    
    if len(contacts) > 10:
        print(f"    ... and {len(contacts) - 10} more")
    
    print("-" * 70)


def main():
    print("=" * 70)
    print("📱 WhatsApp Contacts Exporter")
    print("=" * 70)
    print()
    
    # Fetch contacts
    ultra_contacts = get_contacts()
    
    if not ultra_contacts:
        print("\n❌ No contacts to export")
        print("\n💡 Troubleshooting:")
        print("   1. Check UltraMsg credentials in .env")
        print("   2. Ensure instance is active")
        print("   3. Try again in few minutes")
        return
    
    # Save contacts
    contacts = save_contacts(ultra_contacts)
    
    if contacts:
        # Show preview
        show_preview(contacts)
        
        print("\n✅ SUCCESS!")
        print("\n🚀 Next steps:")
        print("   python whatsapp_ai_agent_pro.py")
        print("\n💡 All future messages will use these phone numbers!")
    else:
        print("\n❌ Failed to save contacts")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
