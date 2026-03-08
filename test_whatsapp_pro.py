#!/usr/bin/env python3
"""
Quick test script for WhatsApp AI Agent PRO

Tests:
1. Phone extraction from draft files
2. Gemini API connectivity
3. Contact manager
4. UltraMsg configuration

Usage:
    python test_whatsapp_pro.py
"""

import sys
from pathlib import Path

# Add base directory to path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

print("=" * 70)
print("🧪 WhatsApp AI Agent PRO - Test Suite")
print("=" * 70)

# Test 1: Phone Extraction
print("\n[TEST 1] Phone Number Extraction")
print("-" * 70)

import re

test_cases = [
    # (content, expected_phone)
    ("""---
type: whatsapp_reply
phone: +923001234567
---
Test""", "+923001234567"),
    
    ("""---
type: whatsapp_reply
phone: +923339876543
---
Test""", "+923339876543"),
]

all_passed = True

for i, (content, expected) in enumerate(test_cases, 1):
    frontmatter_match = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    phone = None
    
    if frontmatter_match:
        frontmatter = frontmatter_match.group(1)
        phone_match = re.search(r'^phone:\s*(\+?\d+)', frontmatter, re.MULTILINE)
        if phone_match:
            phone = phone_match.group(1).strip()
    
    # Validate
    if phone and len(phone) >= 10 and phone != '+':
        print(f"  ✅ Test {i}: PASS - Extracted: {phone}")
    else:
        print(f"  ❌ Test {i}: FAIL - Got: {phone}")
        all_passed = False

if all_passed:
    print("\n✅ Phone Extraction: ALL TESTS PASSED")
else:
    print("\n❌ Phone Extraction: SOME TESTS FAILED")

# Test 2: Gemini API
print("\n[TEST 2] Gemini API Connectivity")
print("-" * 70)

try:
    from whatsapp_ai_agent_pro import AIDraftGenerator
    
    gen = AIDraftGenerator()
    
    if gen.available:
        print(f"  ✅ Gemini AI: Enabled ({gen.model.model_name})")
        
        # Test generation
        try:
            draft = gen.generate_draft(
                message_text="Hi! Can we meet tomorrow?",
                sender_name="Test User",
                chat_name="Test"
            )
            print(f"  ✅ Draft Generation: Working")
            print(f"     Sample: {draft[:50]}...")
        except Exception as e:
            print(f"  ⚠️  Draft Generation: Error - {e}")
    else:
        print(f"  ⚠️  Gemini AI: Not available (using templates)")
        
except ImportError as e:
    print(f"  ❌ Import Error: {e}")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 3: Contact Manager
print("\n[TEST 3] Contact Manager")
print("-" * 70)

try:
    from whatsapp_ai_agent_pro import ContactManager
    
    vault_path = BASE_DIR / "Vault"
    cm = ContactManager(vault_path)
    
    print(f"  ✅ Loaded: {len(cm.contacts)} contacts")
    
    if cm.contacts:
        for name, contact in list(cm.contacts.items())[:3]:
            print(f"     • {contact.name}: {contact.phone}")
    
    # Test phone extraction
    test_chats = [
        "Ahmed (+923001234567)",
        "03001234567",
        "+923339876543",
    ]
    
    print(f"\n  Phone Extraction Tests:")
    for chat_name in test_chats:
        phone = cm.extract_phone_from_chat_name(chat_name)
        if phone:
            print(f"    ✅ '{chat_name}' → {phone}")
        else:
            print(f"    ⚠️  '{chat_name}' → Not extracted")
    
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 4: UltraMsg Configuration
print("\n[TEST 4] UltraMsg Configuration")
print("-" * 70)

try:
    from whatsapp_ai_agent_pro import UltraMsgClient
    
    client = UltraMsgClient()
    
    if client.is_configured:
        print(f"  ✅ UltraMsg: Configured ({client.instance_id})")
    else:
        print(f"  ⚠️  UltraMsg: Not configured")
        print(f"      Set ULTRAMSG_INSTANCE_ID and ULTRAMSG_TOKEN in .env")
        
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 5: Draft File Validation
print("\n[TEST 5] Draft File Validation")
print("-" * 70)

approved_folder = BASE_DIR / "Vault" / "Approved"

if approved_folder.exists():
    draft_files = list(approved_folder.glob("WHATSAPP_REPLY_*.md"))
    
    if draft_files:
        print(f"  Found {len(draft_files)} draft files\n")
        
        for file in draft_files[:3]:
            content = file.read_text(encoding='utf-8')
            
            # Extract phone
            frontmatter_match = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
            phone = None
            
            if frontmatter_match:
                frontmatter = frontmatter_match.group(1)
                phone_match = re.search(r'^phone:\s*(\+?\d+)', frontmatter, re.MULTILINE)
                if phone_match:
                    phone = phone_match.group(1).strip()
            
            # Validate
            if phone and len(phone) >= 10 and phone != '+':
                print(f"  ✅ {file.name}")
                print(f"     Phone: {phone} (Valid)")
            else:
                print(f"  ❌ {file.name}")
                print(f"     Phone: '{phone}' (INVALID - needs fix)")
    else:
        print(f"  ℹ️  No draft files in Approved/")
else:
    print(f"  ℹ️  Approved/ folder not found")

# Summary
print("\n" + "=" * 70)
print("📊 Test Summary")
print("=" * 70)
print("""
To fix invalid draft files:
1. Open file in Approved/ folder
2. Edit frontmatter section (between ---)
3. Ensure phone has complete number:
   ✅ phone: +923001234567
   ❌ phone: +
   ❌ phone: +PLACEHOLDER_...

To fix contacts:
1. Open Vault/Contacts/contacts.json
2. Add real phone numbers:
   {
     "name": {
       "name": "Contact Name",
       "phone": "+923001234567"
     }
   }

To run the agent:
   python whatsapp_ai_agent_pro.py
""")

print("=" * 70)
print("✅ Test Complete!")
print("=" * 70)
