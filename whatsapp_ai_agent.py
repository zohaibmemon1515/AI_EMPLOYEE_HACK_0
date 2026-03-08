#!/usr/bin/env python3
r"""
Complete WhatsApp AI Agent - Gold Tier

Full workflow:
1. Watch WhatsApp Web for new messages (Playwright)
2. Extract sender phone number (even if name is saved)
3. Generate AI draft reply using Gemini API
4. Save draft to Pending_Approval/
5. When moved to Approved/, send via UltraMsg API
6. Move to Done/ after sending

Usage:
    python whatsapp_ai_agent.py [vault_path] [interval]
"""

import hashlib
import json
import os
import re
import shutil
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import dotenv

# Load environment variables
dotenv.load_dotenv()

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# Windows-safe logging
import logging
class WindowsSafeHandler(logging.StreamHandler):
    EMOJI_MAP = {
        '👁️': '[O]', '📋': '[T]', '🤖': '[AI]', '✅': '[OK]', '❌': '[X]',
        '⚠️': '[!]', '📝': '[N]', '🔄': '[~]', '📊': '[D]', '📁': '[F]',
        '💬': '[W]', '📱': '[M]', '📧': '[E]', '🚀': '[G]',
    }
    def emit(self, record):
        try:
            msg = self.format(record)
            if sys.platform == "win32":
                for emoji, repl in self.EMOJI_MAP.items():
                    msg = msg.replace(emoji, repl)
            self.stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            try:
                msg = self.format(record).encode('ascii', 'ignore').decode('ascii')
                self.stream.write(msg + self.terminator)
                self.flush()
            except Exception:
                pass

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = WindowsSafeHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)


# =============================================================================
# Configuration
# =============================================================================

class Config:
    WHATSAPP_WEB_URL = "https://web.whatsapp.com"
    BROWSER_HEADLESS = os.getenv("WHATSAPP_BROWSER_HEADLESS", "false").lower() == "true"
    POLL_INTERVAL = int(os.getenv("WHATSAPP_POLL_INTERVAL", "30"))
    MAX_MESSAGES_PER_POLL = int(os.getenv("WHATSAPP_MAX_MESSAGES_PER_POLL", "20"))
    RATE_LIMIT_HOURLY = int(os.getenv("WHATSAPP_RATE_LIMIT_HOURLY", "10"))
    
    # UltraMsg Configuration
    ULTRAMSG_INSTANCE_ID = os.getenv("ULTRAMSG_INSTANCE_ID", "")
    ULTRAMSG_TOKEN = os.getenv("ULTRAMSG_TOKEN", "")
    
    # Gemini API Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class WhatsAppMessage:
    message_id: str
    chat_name: str
    phone_number: str  # Extracted phone number
    from_name: str
    message_text: str
    timestamp: datetime
    is_group: bool
    has_media: bool
    classification: str = "unknown"
    priority: str = "medium"


# =============================================================================
# Contact Manager - Extract Phone Numbers
# =============================================================================

class ContactManager:
    """Manages contact list and extracts phone numbers."""
    
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.contacts_file = vault_path / "Contacts" / "contacts.json"
        self.contacts = {}
        self._load_contacts()
    
    def _load_contacts(self):
        """Load contacts from JSON file."""
        if self.contacts_file.exists():
            try:
                self.contacts = json.loads(self.contacts_file.read_text(encoding='utf-8'))
                logger.info(f"Loaded {len(self.contacts)} contacts")
            except Exception as e:
                logger.error(f"Load contacts error: {e}")
                self.contacts = {}
    
    def _save_contacts(self):
        """Save contacts to JSON file."""
        try:
            self.contacts_file.parent.mkdir(parents=True, exist_ok=True)
            self.contacts_file.write_text(
                json.dumps(self.contacts, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
        except Exception as e:
            logger.error(f"Save contacts error: {e}")
    
    def add_contact(self, name: str, phone: str):
        """Add or update contact."""
        clean_name = name.strip().lower()
        clean_phone = self._clean_phone(phone)
        
        if clean_name not in self.contacts:
            self.contacts[clean_name] = {
                "name": name,
                "phone": clean_phone,
                "added": datetime.now().isoformat()
            }
            self._save_contacts()
            logger.info(f"Added contact: {name} -> {clean_phone}")
    
    def get_phone(self, name: str) -> Optional[str]:
        """Get phone number for a contact name."""
        clean_name = name.strip().lower()
        if clean_name in self.contacts:
            return self.contacts[clean_name]["phone"]
        return None
    
    def _clean_phone(self, phone: str) -> str:
        """Clean phone number - keep only + and digits."""
        cleaned = re.sub(r'[^\d+]', '', phone)
        if not cleaned.startswith('+'):
            # Add Pakistan country code if missing
            if cleaned.startswith('0'):
                cleaned = '+92' + cleaned[1:]
            else:
                cleaned = '+' + cleaned
        return cleaned


# =============================================================================
# AI Draft Generator - Gemini API
# =============================================================================

class AIDraftGenerator:
    """Generates AI draft replies using Google Gemini API."""
    
    def __init__(self):
        self.client = None
        self.model = None
        self.available = False
        self._init_gemini()
    
    def _init_gemini(self):
        """Initialize Gemini API."""
        if not Config.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not set - using template fallback")
            return
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=Config.GEMINI_API_KEY)
            
            # Try model
            try:
                self.model = genai.GenerativeModel(Config.GEMINI_MODEL)
                self.model.generate_content("Hi")  # Test
                self.client = self.model
                self.available = True
                logger.info(f"✨ Gemini AI: ✅ Enabled ({Config.GEMINI_MODEL})")
            except Exception as e:
                # Try fallback model
                try:
                    self.model = genai.GenerativeModel('gemini-1.0-pro')
                    self.model.generate_content("Hi")
                    self.client = self.model
                    self.available = True
                    logger.info(f"✨ Gemini AI: ✅ Enabled (gemini-1.0-pro)")
                except Exception as e2:
                    logger.error(f"Gemini model error: {e2}")
        except ImportError:
            logger.error("google-generativeai not installed")
            logger.info("Install: pip install google-generativeai")
        except Exception as e:
            logger.error(f"Gemini init error: {e}")
    
    def generate_draft(self, message_text: str, sender_name: str,
                      chat_name: str, is_group: bool = False) -> str:
        """Generate AI draft reply."""
        if not self.available:
            return self._template_fallback(message_text, sender_name)
        
        try:
            prompt = self._create_prompt(message_text, sender_name, chat_name, is_group)
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"AI generation error: {e}")
            return self._template_fallback(message_text, sender_name)
    
    def _create_prompt(self, message_text: str, sender_name: str,
                      chat_name: str, is_group: bool) -> str:
        """Create AI prompt."""
        chat_type = "Group" if is_group else "Individual"
        
        return f"""You are a helpful assistant that drafts WhatsApp replies.

Generate a concise, natural reply (under 100 words):

**Sender**: {sender_name}
**Chat Type**: {chat_type}
**Message**:
{message_text}

Guidelines:
- Keep it natural and conversational
- Address specific points mentioned
- No placeholders like [Your Name]
- Just the reply text, ready to send

Reply:"""
    
    def _template_fallback(self, message_text: str, sender_name: str) -> str:
        """Template fallback when AI not available."""
        msg_lower = message_text.lower()
        
        if any(w in msg_lower for w in ['problem', 'issue', 'error', 'help']):
            return f"Hi {sender_name}, thanks for reaching out. I understand you're facing an issue. To help better: 1) When did this start? 2) What steps have you tried? I'll help resolve this quickly."
        elif any(w in msg_lower for w in ['meeting', 'call', 'schedule', 'time']):
            return f"Hi {sender_name}, thanks for your message. I'd be happy to help. Could you share your preferred time slots and expected duration? Looking forward to connecting."
        elif '?' in message_text:
            return f"Hi {sender_name}, good question! Let me get back to you on this shortly."
        else:
            return f"Hi {sender_name}, thanks for your message! I'll review this and get back to you within 24-48 hours. If urgent, please let me know."


# =============================================================================
# UltraMsg Client - Send WhatsApp Messages
# =============================================================================

class UltraMsgClient:
    """Send WhatsApp messages via UltraMsg API."""
    
    def __init__(self):
        self.instance_id = Config.ULTRAMSG_INSTANCE_ID
        self.token = Config.ULTRAMSG_TOKEN
        self.is_configured = bool(self.instance_id and self.token)
        self.base_url = "https://api.ultramsg.com"
    
    def send_message(self, phone: str, message: str) -> tuple:
        """
        Send WhatsApp message.
        Returns: (success: bool, message_id: str, error: str)
        """
        if not self.is_configured:
            return (False, "", "UltraMsg not configured")
        
        try:
            import requests
            
            url = f"{self.base_url}/{self.instance_id}/messages/chat"
            
            payload = {
                "token": self.token,
                "to": phone,
                "body": message,
                "priority": 1
            }
            
            response = requests.post(url, data=payload, timeout=30)
            result = response.json()
            
            if result.get("sent") == "true":
                message_id = result.get("id", "")
                logger.info(f"✅ Sent via UltraMsg! ID: {message_id}")
                return (True, message_id, "")
            else:
                error = result.get("error", "Unknown error")
                logger.error(f"UltraMsg error: {error}")
                return (False, "", error)
                
        except Exception as e:
            logger.error(f"UltraMsg send error: {e}")
            return (False, "", str(e))


# =============================================================================
# Playwright WhatsApp Client
# =============================================================================

class PlaywrightWhatsAppClient:
    """Real WhatsApp Web client using Playwright."""
    
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.session_path = vault_path.parent / "sessions" / "whatsapp"
        self.playwright = None
        self.browser = None
        self.page = None
        self._authenticated = False
        self.session_path.mkdir(parents=True, exist_ok=True)
    
    def start_browser(self):
        """Start Chromium browser."""
        try:
            from playwright.sync_api import sync_playwright
            
            logger.info("🌐 Starting browser...")
            self.playwright = sync_playwright().start()
            
            self.browser = self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.session_path),
                headless=Config.BROWSER_HEADLESS,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
                timeout=60000,
            )
            
            self.page = self.browser.pages[0] if self.browser.pages else self.browser.new_page()
            logger.info("✓ Browser started")
            return True
        except Exception as e:
            logger.error(f"Browser start error: {e}")
            return False
    
    def navigate_to_whatsapp(self):
        """Navigate to WhatsApp Web."""
        try:
            logger.info("🌐 Navigating to WhatsApp Web...")
            self.page.goto(Config.WHATSAPP_WEB_URL, wait_until="networkidle", timeout=60000)
            time.sleep(5)
            logger.info("✓ WhatsApp Web loaded")
            return True
        except Exception as e:
            logger.error(f"Navigate error: {e}")
            return False
    
    def check_authentication(self) -> bool:
        """Check if WhatsApp is authenticated."""
        try:
            time.sleep(2)
            
            # Check for chat list
            chat_list = self.page.query_selector('div[role="row"]')
            
            # Check for QR code
            qr_section = self.page.query_selector('div[data-testid="qr-container"]')
            
            if qr_section:
                self._authenticated = False
                return False
            
            if chat_list:
                self._authenticated = True
                logger.info("✓ WhatsApp session active")
                return True
            
            self._authenticated = False
            return False
        except Exception as e:
            logger.error(f"Auth check error: {e}")
            return False
    
    def wait_for_authentication(self, timeout=180):
        """Wait for user to scan QR code."""
        logger.info("\n" + "=" * 70)
        logger.info("📱 WhatsApp Authentication Required")
        logger.info("=" * 70)
        logger.info("\n1. Open WhatsApp on your phone")
        logger.info("2. Go to: Settings > Linked Devices")
        logger.info("3. Tap: Link a Device")
        logger.info("4. Scan the QR code")
        logger.info(f"\n⏳ Waiting ({timeout//60} minutes)...")
        logger.info("=" * 70 + "\n")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if self.check_authentication():
                    logger.info("\n✅ Authentication successful!")
                    return True
                
                qr_present = self.page.query_selector('div[data-testid="qr-container"]')
                
                if qr_present:
                    print("   ⚠️  QR code visible - waiting for scan...", end="\r")
                else:
                    print("   ⏳ Loading...", end="\r")
                
                time.sleep(3)
            except Exception as e:
                logger.error(f"Auth wait error: {e}")
                time.sleep(2)
        
        logger.error("\n❌ Authentication timeout")
        return False
    
    def get_unread_messages(self):
        """Get unread messages from WhatsApp."""
        messages = []
        
        if not self._authenticated:
            return messages
        
        try:
            self.page.wait_for_selector('div[role="row"]', timeout=5000)
            time.sleep(2)
            
            chats = self.page.query_selector_all('div[role="row"]')
            logger.info(f"📱 Found {len(chats)} chats...")
            
            for chat in chats[:Config.MAX_MESSAGES_PER_POLL]:
                try:
                    # Check for unread indicator
                    unread_badge = chat.query_selector('[aria-label*="unread"]')
                    if not unread_badge:
                        continue
                    
                    # Get chat info
                    chat_name_el = chat.query_selector('span[title]')
                    message_el = chat.query_selector('span[dir="auto"]')
                    time_el = chat.query_selector('time')
                    
                    chat_name = chat_name_el.get_attribute('title') if chat_name_el else 'Unknown'
                    preview = message_el.text_content() if message_el else ''
                    timestamp = time_el.get_attribute('datetime') if time_el else datetime.now().isoformat()
                    
                    # Click to open chat and get full message
                    try:
                        chat.click()
                        time.sleep(1.5)
                        full_message = self._get_full_message()
                        self.page.keyboard.press('Escape')
                        time.sleep(0.5)
                        message_text = full_message if full_message else preview
                    except:
                        message_text = preview
                    
                    # Detect if group or has media
                    is_group = 'group' in chat_name.lower()
                    has_media = any(c in message_text for c in ['📷', '🎤', '📹', '📎', 'Image', 'Video'])
                    
                    msg = WhatsAppMessage(
                        message_id=hashlib.md5(f"{chat_name}:{timestamp}:{message_text}".encode()).hexdigest()[:16],
                        chat_name=chat_name,
                        phone_number="",  # Will be extracted later
                        from_name=chat_name,
                        message_text=message_text,
                        timestamp=datetime.fromisoformat(timestamp.replace('Z', '+00:00')) if timestamp else datetime.now(),
                        is_group=is_group,
                        has_media=has_media,
                    )
                    messages.append(msg)
                    logger.info(f"   📱 {chat_name}: {message_text[:50]}...")
                    
                except Exception as e:
                    logger.error(f"Parse message error: {e}")
                    continue
            
            logger.info(f"✓ Found {len(messages)} unread")
        except Exception as e:
            logger.error(f"Get messages error: {e}")
        
        return messages
    
    def _get_full_message(self) -> str:
        """Get full message text from opened chat."""
        try:
            messages = self.page.query_selector_all('div[data-testid="message-container"]')
            if messages:
                last_msg = messages[-1]
                msg_el = last_msg.query_selector('span[dir="auto"]')
                if msg_el:
                    return msg_el.text_content().strip()
        except Exception as e:
            logger.error(f"Get full message error: {e}")
        return ""
    
    def mark_chat_as_read(self, chat_name: str):
        """Mark chat as read."""
        try:
            chats = self.page.query_selector_all('div[role="row"]')
            for chat in chats:
                name_el = chat.query_selector('span[title]')
                if name_el and name_el.text_content() == chat_name:
                    chat.click()
                    time.sleep(1)
                    self.page.keyboard.press('Escape')
                    time.sleep(0.5)
                    logger.info(f"✓ Marked '{chat_name}' as read")
                    return True
        except Exception as e:
            logger.error(f"Mark read error: {e}")
        return False
    
    def close(self):
        """Close browser."""
        try:
            if self.browser:
                logger.info("✓ Browser session preserved")
        except:
            pass
        try:
            if self.playwright:
                self.playwright.stop()
        except:
            pass


# =============================================================================
# WhatsApp AI Agent - Main Class
# =============================================================================

class WhatsAppAIAgent:
    """Main WhatsApp AI Agent with complete workflow."""
    
    def __init__(self, vault_path: Path, check_interval: int = 30):
        self.vault_path = vault_path
        self.check_interval = check_interval
        
        # Initialize components
        self.contact_manager = ContactManager(vault_path)
        self.ai_draft_generator = AIDraftGenerator()
        self.ultramsg_client = UltraMsgClient()
        self.playwright_client = PlaywrightWhatsAppClient(vault_path)
        
        # Folders
        self.needs_action_folder = vault_path / "Needs_Action"
        self.pending_approval_folder = vault_path / "Pending_Approval"
        self.approved_folder = vault_path / "Approved"
        self.done_folder = vault_path / "Done"
        
        # Create folders
        for folder in [self.needs_action_folder, self.pending_approval_folder, 
                       self.approved_folder, self.done_folder]:
            folder.mkdir(parents=True, exist_ok=True)
        
        # State
        self.processed_ids = set()
        self._running = False
        self._load_state()
        
        logger.info(f"\n💬 WhatsApp AI Agent initialized")
        logger.info(f"   Vault: {vault_path}")
        logger.info(f"   Poll: {check_interval}s")
        logger.info(f"   AI Draft: {'✅ Gemini' if self.ai_draft_generator.available else '⚠️ Templates'}")
        logger.info(f"   UltraMsg: {'✅ Enabled' if self.ultramsg_client.is_configured else '⚠️ Not configured'}")
    
    def _load_state(self):
        """Load processed message IDs."""
        state_file = self.vault_path / "In_Progress" / "whatsapp" / "processed.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text(encoding='utf-8'))
                self.processed_ids = set(data.get("processed_ids", []))
                logger.info(f"✓ Loaded {len(self.processed_ids)} processed IDs")
            except:
                self.processed_ids = set()
        else:
            self.processed_ids = set()
    
    def _save_state(self):
        """Save processed message IDs."""
        state_file = self.vault_path / "In_Progress" / "whatsapp" / "processed.json"
        data = {
            "processed_ids": list(self.processed_ids),
            "last_updated": datetime.now().isoformat(),
            "count": len(self.processed_ids),
        }
        try:
            state_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        except Exception as e:
            logger.error(f"Save state error: {e}")
    
    def check_for_new_messages(self):
        """Check for new WhatsApp messages."""
        if not self.playwright_client.check_authentication():
            return []
        
        messages = self.playwright_client.get_unread_messages()
        
        # Filter already processed
        new_messages = [m for m in messages if m.message_id not in self.processed_ids]
        
        return new_messages
    
    def extract_phone_number(self, message: WhatsAppMessage) -> str:
        """Extract or lookup phone number for sender."""
        # Try to get from contacts
        phone = self.contact_manager.get_phone(message.from_name)
        
        if phone:
            logger.info(f"✓ Found contact: {message.from_name} -> {phone}")
            return phone
        
        # Try to extract from chat_name if it contains a number
        chat_name = message.chat_name
        
        # Check if chat_name is a phone number
        phone_match = re.search(r'(\+?\d[\d\-]{8,})', chat_name)
        if phone_match:
            phone = self.contact_manager._clean_phone(phone_match.group(1))
            logger.info(f"✓ Extracted from chat: {phone}")
            self.contact_manager.add_contact(message.from_name, phone)
            return phone
        
        # If no phone found, use a placeholder (user needs to add manually)
        logger.warning(f"⚠️ No phone for {message.from_name} - using placeholder")
        phone = f"+PLACEHOLDER_{message.from_name.replace(' ', '_')}"
        self.contact_manager.add_contact(message.from_name, phone)
        return phone
    
    def create_message_file(self, message: WhatsAppMessage) -> Path:
        """Create message file in Needs_Action."""
        phone = self.extract_phone_number(message)
        message.phone_number = phone
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"WHATSAPP_{message.message_id}_{timestamp}.md"
        
        frontmatter = {
            "type": "whatsapp_message",
            "message_id": message.message_id,
            "from": message.from_name,
            "phone": phone,
            "chat_name": message.chat_name,
            "received": message.timestamp.isoformat(),
            "priority": message.priority,
            "classification": message.classification,
            "is_group": str(message.is_group).lower(),
            "has_media": str(message.has_media).lower(),
        }
        
        content = f"""## WhatsApp Message

**From**: {message.from_name}
**Phone**: {phone}
**Chat**: {message.chat_name}

---

### Message

{message.message_text}

---

- New Contact: {"Yes" if phone.startswith('+PLACEHOLDER') else "No"}
- Has Media: {"Yes" if message.has_media else "No"}
"""
        
        filepath = self.needs_action_folder / filename
        fm = "\n".join([f"{k}: {v}" for k, v in frontmatter.items()])
        filepath.write_text(f"---\n{fm}\n---\n\n{content}", encoding='utf-8')
        
        logger.info(f"✓ Created: {filename}")
        return filepath
    
    def create_draft_reply(self, message: WhatsAppMessage) -> Path:
        """Create AI draft reply in Pending_Approval."""
        draft = self.ai_draft_generator.generate_draft(
            message_text=message.message_text,
            sender_name=message.from_name,
            chat_name=message.chat_name,
            is_group=message.is_group
        )
        
        filename = f"WHATSAPP_REPLY_{message.message_id}.md"
        filepath = self.pending_approval_folder / filename
        
        content = f"""---
type: whatsapp_reply
message_id: {message.message_id}
from: {message.from_name}
phone: {message.phone_number}
chat_name: {message.chat_name}
status: pending_approval
---

# Draft Reply

## Original Message
**From**: {message.from_name}
**Phone**: {message.phone_number}
**Chat**: {message.chat_name}

```
{message.message_text}
```

---

## AI Draft Reply

{draft}

---

## Actions
- ✅ Review reply
- ✅ Edit if needed
- 📤 Move to `Approved/` to send
- ❌ Move to `Rejected/` to discard
"""
        
        filepath.write_text(content, encoding='utf-8')
        logger.info(f"✓ Created draft: {filename}")
        return filepath
    
    def check_approved_replies(self):
        """Check Approved/ folder for replies to send."""
        approved_files = []
        
        if not self.approved_folder.exists():
            return []
        
        for file in self.approved_folder.glob("WHATSAPP_REPLY_*.md"):
            try:
                content = file.read_text(encoding='utf-8')
                if "type: whatsapp_reply" in content:
                    approved_files.append(file)
                    logger.info(f"📋 Found approved: {file.name}")
            except Exception as e:
                logger.error(f"Read error: {e}")
        
        return approved_files
    
    def process_approved_reply(self, file_path: Path) -> bool:
        """Process approved reply and send via UltraMsg."""
        logger.info(f"Processing: {file_path.name}")
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Extract phone number
            phone_match = re.search(r"phone:\s*(\S+)", content)
            if not phone_match:
                logger.error("No phone number found")
                return False
            
            phone = phone_match.group(1).strip()
            
            # Skip placeholder phones
            if phone.startswith('+PLACEHOLDER'):
                logger.error(f"⚠️ Placeholder phone - update contacts first: {phone}")
                logger.info("Add real phone in Contacts/contacts.json")
                return False
            
            # Clean phone
            phone = re.sub(r'[\s\-]', '', phone)
            if not phone.startswith('+'):
                phone = '+' + phone
            
            # Extract message
            draft_match = re.search(r"## AI Draft Reply\s*\n(.*?)(?:---|\Z)", content, re.DOTALL)
            if not draft_match:
                logger.error("No draft message found")
                return False
            
            message = draft_match.group(1).strip()
            
            logger.info(f"   To: {phone}")
            logger.info(f"   Message: {message[:80]}...")
            
            # Send via UltraMsg
            sent = False
            if self.ultramsg_client.is_configured:
                logger.info("   Sending via UltraMsg API...")
                success, msg_id, error = self.ultramsg_client.send_message(phone, message)
                
                if success:
                    logger.info(f"✅ Sent! ID: {msg_id}")
                    sent = True
                else:
                    logger.error(f"❌ Send failed: {error}")
            else:
                logger.warning("⚠️ UltraMsg not configured - manual send required")
            
            # Move to Done
            done_path = self.done_folder / file_path.name
            shutil.move(str(file_path), str(done_path))
            
            if sent:
                logger.info(f"✅ Sent automatically via UltraMsg")
            else:
                logger.info(f"✅ Prepared: {done_path.name}")
                logger.info(f"   Send manually via WhatsApp Web")
            
            return True
            
        except Exception as e:
            logger.error(f"Process error: {e}")
            return False
    
    def run(self):
        """Main run loop."""
        self._running = True
        
        def signal_handler(sig, frame):
            logger.info("Shutdown requested")
            self._running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("\n" + "=" * 70)
        logger.info("💬 WhatsApp AI Agent RUNNING")
        logger.info("=" * 70)
        logger.info(f"📬 Poll: {self.check_interval}s")
        logger.info(f"📁 Vault: {self.vault_path}")
        logger.info(f"🤖 AI: {'✅ Gemini' if self.ai_draft_generator.available else '⚠️ Templates'}")
        logger.info(f"📤 UltraMsg: {'✅ Auto-send' if self.ultramsg_client.is_configured else '⚠️ Manual'}")
        logger.info("\nPress Ctrl+C to stop")
        logger.info("=" * 70 + "\n")
        
        # Start browser
        if not self.playwright_client.start_browser():
            logger.error("❌ Browser start failed")
            return
        
        self.playwright_client.navigate_to_whatsapp()
        
        # Authenticate
        if not self.playwright_client.check_authentication():
            if not self.playwright_client.wait_for_authentication():
                logger.error("❌ Authentication failed")
                self.playwright_client.close()
                return
        
        try:
            while self._running:
                try:
                    # Check for new messages
                    messages = self.check_for_new_messages()
                    
                    if messages:
                        logger.info(f"\n📱 Found {len(messages)} new messages")
                        for msg in messages:
                            self.create_message_file(msg)
                            self.create_draft_reply(msg)
                            self.playwright_client.mark_chat_as_read(msg.chat_name)
                            self.processed_ids.add(msg.message_id)
                            self._save_state()
                        logger.info(f"✓ Processed {len(messages)} messages")
                    
                    # Check approved replies
                    approved = self.check_approved_replies()
                    if approved:
                        logger.info(f"\n📤 Found {len(approved)} approved replies")
                        for file in approved:
                            self.process_approved_reply(file)
                    
                    # Status
                    else:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"[{timestamp}] ✓ No new messages", end="\r")
                    
                    time.sleep(self.check_interval)
                    
                except Exception as e:
                    logger.error(f"Loop error: {e}")
                    time.sleep(self.check_interval)
                    
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the agent."""
        self._running = False
        self.playwright_client.close()
        self._save_state()
        logger.info("Stopped")


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    vault_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./Vault")
    check_interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    if not vault_path.is_absolute():
        vault_path = Path(__file__).parent / vault_path
    
    agent = WhatsAppAIAgent(vault_path, check_interval)
    agent.run()


if __name__ == "__main__":
    main()
