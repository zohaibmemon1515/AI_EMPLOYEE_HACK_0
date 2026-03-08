#!/usr/bin/env python3
r"""
📱 WhatsApp AI Agent - PRODUCTION READY
========================================

Advanced WhatsApp automation with:
- Real WhatsApp Web integration (Playwright)
- Smart phone number extraction from contacts/chat
- Gemini AI draft replies (correct API)
- UltraMsg auto-send
- Production-grade error handling

Usage:
    python whatsapp_ai_agent_pro.py [vault_path] [interval]
"""

import hashlib
import json
import os
import re
import shutil
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

import dotenv

# Load environment variables
dotenv.load_dotenv()

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# =============================================================================
# Windows-Safe Logging
# =============================================================================

import logging

class WindowsSafeHandler(logging.StreamHandler):
    """Logging handler that replaces emojis with ASCII on Windows."""
    EMOJI_MAP = {
        '👁️': '[O]', '📋': '[T]', '🤖': '[AI]', '✅': '[OK]', '❌': '[X]',
        '⚠️': '[!]', '📝': '[N]', '🔄': '[~]', '📊': '[D]', '📁': '[F]',
        '💬': '[W]', '📱': '[M]', '📧': '[E]', '🚀': '[G]', '👤': '[U]',
        '📞': '[P]', '💰': '[M]', '🔥': '[!]', '⭐': '[S]',
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
logger.setLevel(logging.DEBUG)  # DEBUG for detailed phone extraction logs
if not logger.handlers:
    handler = WindowsSafeHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)


# =============================================================================
# Configuration
# =============================================================================

class Config:
    """Centralized configuration."""
    
    # WhatsApp Web
    WHATSAPP_WEB_URL = "https://web.whatsapp.com"
    BROWSER_HEADLESS = os.getenv("WHATSAPP_BROWSER_HEADLESS", "false").lower() == "true"
    POLL_INTERVAL = int(os.getenv("WHATSAPP_POLL_INTERVAL", "30"))
    MAX_MESSAGES_PER_POLL = int(os.getenv("WHATSAPP_MAX_MESSAGES_PER_POLL", "20"))
    RATE_LIMIT_HOURLY = int(os.getenv("WHATSAPP_RATE_LIMIT_HOURLY", "10"))
    
    # UltraMsg
    ULTRAMSG_INSTANCE_ID = os.getenv("ULTRAMSG_INSTANCE_ID", "").strip()
    ULTRAMSG_TOKEN = os.getenv("ULTRAMSG_TOKEN", "").strip()
    
    # Gemini AI
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-002").strip()
    
    # Session
    SESSION_PATH = Path(os.getenv("WHATSAPP_SESSION_PATH", "./sessions/whatsapp"))
    if not SESSION_PATH.is_absolute():
        SESSION_PATH = BASE_DIR / SESSION_PATH


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class WhatsAppMessage:
    message_id: str
    chat_name: str
    phone_number: str
    from_name: str
    message_text: str
    timestamp: datetime
    is_group: bool
    has_media: bool
    classification: str = "unknown"
    priority: str = "medium"
    raw_data: dict = field(default_factory=dict)


@dataclass
class Contact:
    name: str
    phone: str
    added: datetime
    last_used: datetime = None
    notes: str = ""


# =============================================================================
# Contact Manager - Advanced Phone Extraction
# =============================================================================

class ContactManager:
    """
    Advanced contact management with phone number extraction.
    
    Features:
    - Load/save contacts from JSON
    - Extract phone from chat names
    - Pakistan number formatting
    - Contact deduplication
    """
    
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.contacts_file = vault_path / "Contacts" / "contacts.json"
        self.contacts: Dict[str, Contact] = {}
        self._load_contacts()
    
    def _load_contacts(self):
        """Load contacts from JSON."""
        if self.contacts_file.exists():
            try:
                data = json.loads(self.contacts_file.read_text(encoding='utf-8'))
                for key, value in data.items():
                    self.contacts[key] = Contact(
                        name=value.get("name", key),
                        phone=value.get("phone", ""),
                        added=datetime.fromisoformat(value.get("added", datetime.now().isoformat())),
                        last_used=datetime.fromisoformat(value.get("last_used", datetime.now().isoformat())) if value.get("last_used") else None,
                        notes=value.get("notes", "")
                    )
                logger.info(f"Loaded {len(self.contacts)} contacts")
            except Exception as e:
                logger.error(f"Load contacts error: {e}")
                self.contacts = {}
        else:
            logger.info("No contacts file - will create on first save")
    
    def _save_contacts(self):
        """Save contacts to JSON."""
        try:
            self.contacts_file.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            for key, contact in self.contacts.items():
                data[key] = {
                    "name": contact.name,
                    "phone": contact.phone,
                    "added": contact.added.isoformat(),
                    "last_used": contact.last_used.isoformat() if contact.last_used else None,
                    "notes": contact.notes
                }
            self.contacts_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            logger.debug(f"Saved {len(self.contacts)} contacts")
        except Exception as e:
            logger.error(f"Save contacts error: {e}")
    
    def add_or_update_contact(self, name: str, phone: str) -> bool:
        """
        Add or update contact. Returns True if new contact was added.

        Validates phone number before saving (must have 10+ digits).
        """
        clean_name = name.strip().lower()
        clean_phone = self._clean_phone(phone)

        # Validate phone number - must have at least 10 digits
        digits_only = re.sub(r'[^\d]', '', clean_phone)
        if len(digits_only) < 10:
            logger.debug(f"⚠️  Skipping invalid phone for {name}: {phone} (too short: {len(digits_only)} digits)")
            return False

        # Also skip if it's just a placeholder
        if 'PLACEHOLDER' in clean_phone.upper():
            # Placeholders are OK to save (user will edit later)
            pass

        is_new = clean_name not in self.contacts

        if is_new or self.contacts[clean_name].phone != clean_phone:
            self.contacts[clean_name] = Contact(
                name=name,
                phone=clean_phone,
                added=datetime.now(),
                last_used=datetime.now()
            )
            self._save_contacts()
            logger.info(f"{'Added' if is_new else 'Updated'} contact: {name} -> {clean_phone}")
            return is_new
        else:
            # Update last_used
            self.contacts[clean_name].last_used = datetime.now()
            self._save_contacts()
            return False
    
    def get_phone(self, name: str) -> Optional[str]:
        """Get phone number for a contact name."""
        clean_name = name.strip().lower()
        
        # Exact match
        if clean_name in self.contacts:
            contact = self.contacts[clean_name]
            contact.last_used = datetime.now()
            self._save_contacts()
            return contact.phone
        
        # Partial match
        for key, contact in self.contacts.items():
            if clean_name in key or key in clean_name:
                contact.last_used = datetime.now()
                self._save_contacts()
                return contact.phone
        
        return None
    
    def _clean_phone(self, phone: str) -> str:
        """
        Clean and format phone number.
        
        Handles:
        - Remove spaces, dashes, parentheses
        - Add country code if missing
        - Pakistan numbers (0XXX -> +92XXX)
        """
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Remove leading + if present (we'll add it back)
        cleaned = cleaned.lstrip('+')
        
        # Handle Pakistan numbers
        if cleaned.startswith('0'):
            # 03001234567 -> +923001234567
            cleaned = '92' + cleaned[1:]
        elif len(cleaned) == 10:
            # 3001234567 -> +923001234567
            cleaned = '92' + cleaned
        elif len(cleaned) == 11:
            # 923001234567 -> keep as is
            pass
        
        # Add country code if still no country code
        if not cleaned.startswith('92') and len(cleaned) < 12:
            # Assume Pakistan if short number
            cleaned = '92' + cleaned.lstrip('0')
        
        return '+' + cleaned
    
    def extract_phone_from_chat_name(self, chat_name: str) -> Optional[str]:
        """
        Try to extract phone number from chat name.
        
        Examples:
        - "Ahmed Khan (+923001234567)" -> +923001234567
        - "03001234567" -> +923001234567
        - "+92 300 1234567" -> +923001234567
        """
        # Look for phone number pattern
        patterns = [
            r'\+?[\d\s\-\(\)]{8,}',  # Any phone-like pattern
            r'^\+?\d{10,}$',          # Pure number
            r'\((\+?\d[\d\-\s]+)\)',  # In parentheses
        ]
        
        for pattern in patterns:
            match = re.search(pattern, chat_name)
            if match:
                potential_phone = match.group(0)
                cleaned = self._clean_phone(potential_phone)
                
                # Validate: should be 12-15 digits after +
                digits = re.sub(r'[^\d]', '', cleaned)
                if 10 <= len(digits) <= 15:
                    return cleaned
        
        return None


# =============================================================================
# AI Draft Generator - Gemini API (Correct Implementation)
# =============================================================================

class AIDraftGenerator:
    """
    AI draft reply generator using Google Gemini API.

    Uses the correct Gemini API with auto-detection of available models.
    """

    # Updated model list based on available models (from user logs)
    AVAILABLE_MODELS = [
        'gemini-2.5-flash',              # Latest 2.5 flash
        'gemini-2.5-pro',                # Latest 2.5 pro
        'gemini-2.0-flash',              # Latest 2.0 flash
        'gemini-2.0-flash-001',          # 2.0 flash stable
        'gemini-2.0-flash-lite-001',     # Lite version
        'gemini-2.0-flash-lite',         # Lite
        'gemini-flash-latest',           # Generic latest flash
        'gemini-flash-lite-latest',      # Generic latest flash lite
        'gemini-pro-latest',             # Generic latest pro
        'gemini-2.5-flash-lite',         # 2.5 flash lite
        'gemini-1.5-pro',                # Older but stable
        'gemini-1.0-pro',                # Fallback
    ]

    def __init__(self):
        self.client = None
        self.model = None
        self.available = False
        self._init_gemini()

    def _init_gemini(self):
        """Initialize Gemini API with auto-detection."""
        if not Config.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not set - using template fallback")
            return

        try:
            import google.generativeai as genai

            # Configure with API key
            genai.configure(api_key=Config.GEMINI_API_KEY)

            # Get user-specified model or use default
            user_model = Config.GEMINI_MODEL if Config.GEMINI_MODEL else 'gemini-2.5-flash'

            # Build priority list: user model first, then available models
            model_priority = [user_model] + self.AVAILABLE_MODELS

            # Try each model in order
            for model_name in model_priority:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    # Test the model with simple prompt
                    response = self.model.generate_content("Hi")
                    if response and response.text:
                        self.client = self.model
                        self.available = True
                        logger.info(f"✨ Gemini AI: ✅ Enabled ({model_name})")
                        return
                except Exception as e:
                    logger.debug(f"Model {model_name} failed: {e}")
                    continue

            # If all models fail, try to list and use any available
            try:
                models = genai.list_models()
                for model_info in models:
                    if 'gemini' in model_info.name and 'generateContent' in str(model_info.supported_generation_methods):
                        try:
                            test_model = genai.GenerativeModel(model_info.name)
                            response = test_model.generate_content("Hi")
                            if response and response.text:
                                self.model = test_model
                                self.client = test_model
                                self.available = True
                                logger.info(f"✨ Gemini AI: ✅ Enabled ({model_info.name})")
                                return
                        except:
                            continue
            except Exception as e:
                logger.debug(f"Could not list models: {e}")

            # If everything fails
            logger.error(f"No Gemini models working - using template fallback")

        except ImportError as e:
            logger.error(f"google-generativeai not installed: {e}")
            logger.info("Install: pip install google-generativeai")
        except Exception as e:
            logger.error(f"Gemini init error: {e}")
    
    def generate_draft(self, message_text: str, sender_name: str,
                      chat_name: str, is_group: bool = False) -> str:
        """Generate AI draft reply."""
        if not self.available:
            return self._template_fallback(message_text, sender_name, is_group)
        
        try:
            prompt = self._create_prompt(message_text, sender_name, chat_name, is_group)
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                return response.text.strip()
            else:
                logger.warning("Empty response from Gemini")
                return self._template_fallback(message_text, sender_name, is_group)
                
        except Exception as e:
            logger.error(f"AI generation error: {e}")
            return self._template_fallback(message_text, sender_name, is_group)
    
    def _create_prompt(self, message_text: str, sender_name: str,
                      chat_name: str, is_group: bool) -> str:
        """Create AI prompt for draft generation."""
        chat_type = "Group" if is_group else "Individual"

        return f"""You are drafting a WhatsApp reply. Read the message carefully and respond appropriately.

ORIGINAL MESSAGE:
```
{message_text}
```

SENDER: {sender_name}
CHAT TYPE: {chat_type}

YOUR TASK:
Write a natural, context-aware reply that:
1. Directly responds to what they said (not generic)
2. References specific details from their message
3. Matches the tone (casual/formal based on content)
4. Is concise (1-3 sentences for casual, up to 5 for business)
5. Sounds like a real person, not a bot

EXAMPLES:
- If they ask "Can we meet at 3pm?" → "Yes, 3pm works! See you then."
- If they say "I'm sick" → "Oh no! Hope you feel better soon. Take rest!"
- If they share news → Acknowledge it specifically, don't give generic response

IMPORTANT: Do NOT use phrases like "I understand your concern" or "Thank you for reaching out" - those sound robotic.

DRAFT REPLY (just the reply text, nothing else):"""
    
    def _template_fallback(self, message_text: str, sender_name: str, is_group: bool) -> str:
        """Smart template fallback when AI not available."""
        msg_lower = message_text.lower()
        
        # Detect intent
        if any(w in msg_lower for w in ['problem', 'issue', 'error', 'help', 'not working']):
            return f"Hi {sender_name}, thanks for reaching out. I understand you're facing an issue. To help better: 1) When did this start? 2) What steps have you tried? I'll help resolve this quickly."
        elif any(w in msg_lower for w in ['meeting', 'call', 'schedule', 'tomorrow', 'time', '3pm', '3 pm']):
            return f"Hi {sender_name}, thanks for your message. I'd be happy to help with this. Could you share your preferred time slots and expected duration? Looking forward to connecting."
        elif any(w in msg_lower for w in ['invoice', 'bill', 'payment', 'money']):
            return f"Hi {sender_name}, I'll send you the invoice right away. Could you confirm which email address should I send it to? Thanks!"
        elif '?' in message_text:
            return f"Hi {sender_name}, good question! Let me get back to you on this shortly."
        elif any(w in msg_lower for w in ['thanks', 'thank you', 'shukriya']):
            return f"You're welcome! Glad I could help. Feel free to reach out if you need anything else!"
        else:
            return f"Hi {sender_name}, thanks for your message! I'll review this and get back to you within 24-48 hours. If urgent, please let me know."


# =============================================================================
# UltraMsg Client - Send WhatsApp Messages
# =============================================================================

class UltraMsgClient:
    """
    Send WhatsApp messages via UltraMsg API.

    Production-ready with retry logic and error handling.
    """

    def __init__(self):
        self.instance_id = Config.ULTRAMSG_INSTANCE_ID
        self.token = Config.ULTRAMSG_TOKEN
        self.is_configured = bool(self.instance_id and self.token)
        self.base_url = "https://api.ultramsg.com"

        if self.is_configured:
            logger.info(f"✅ UltraMsg: Configured ({self.instance_id})")
            # Try to sync contacts
            self._sync_contacts()
        else:
            logger.info("⚠️  UltraMsg: Not configured (manual send)")

    def _sync_contacts(self):
        """Sync contacts from UltraMsg API."""
        try:
            import requests

            url = f"{self.base_url}/{self.instance_id}/contacts"
            params = {"token": self.token}

            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get("ok") == "true":
                    contacts = result.get("contacts", [])
                    logger.info(f"📱 Found {len(contacts)} contacts in UltraMsg")

                    # Note: UltraMsg contact sync would go here
                    # For now, just log count
        except Exception as e:
            logger.debug(f"Contact sync error: {e}")
    
    def send_message(self, phone: str, message: str, retry: int = 2) -> tuple:
        """
        Send WhatsApp message with retry logic.
        
        Args:
            phone: Recipient phone number (with +)
            message: Message text
            retry: Number of retries on failure
            
        Returns:
            (success: bool, message_id: str, error: str)
        """
        if not self.is_configured:
            return (False, "", "UltraMsg not configured")
        
        # Clean phone
        clean_phone = re.sub(r'[^\d+]', '', phone)
        if not clean_phone.startswith('+'):
            clean_phone = '+' + clean_phone
        
        last_error = ""
        
        for attempt in range(retry + 1):
            try:
                import requests
                
                url = f"{self.base_url}/{self.instance_id}/messages/chat"
                
                payload = {
                    "token": self.token,
                    "to": clean_phone,
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
                    last_error = error
                    logger.warning(f"UltraMsg error (attempt {attempt + 1}): {error}")
                    
                    if attempt < retry:
                        time.sleep(2)  # Wait before retry
                    
            except requests.exceptions.Timeout:
                last_error = "Timeout"
                logger.warning(f"Timeout (attempt {attempt + 1})")
                if attempt < retry:
                    time.sleep(2)
            except Exception as e:
                last_error = str(e)
                logger.error(f"Send error (attempt {attempt + 1}): {e}")
                if attempt < retry:
                    time.sleep(2)
        
        logger.error(f"Failed after {retry + 1} attempts: {last_error}")
        return (False, "", last_error)


# =============================================================================
# Playwright WhatsApp Client - Real WhatsApp Web
# =============================================================================

class PlaywrightWhatsAppClient:
    """
    Real WhatsApp Web client using Playwright.
    
    Features:
    - Persistent browser session
    - QR code authentication
    - Message extraction
    - Auto-mark as read
    """
    
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.session_path = Config.SESSION_PATH
        self.playwright = None
        self.browser = None
        self.page = None
        self._authenticated = False
        self.session_path.mkdir(parents=True, exist_ok=True)
    
    def start_browser(self):
        """Start Chromium browser with persistent session."""
        try:
            from playwright.sync_api import sync_playwright
            
            logger.info("🌐 Starting browser...")
            self.playwright = sync_playwright().start()
            
            self.browser = self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.session_path),
                headless=Config.BROWSER_HEADLESS,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
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
            
            # Check for chat list (authenticated)
            chat_list = self.page.query_selector('div[role="row"]')
            
            # Check for QR code (not authenticated)
            qr_section = self.page.query_selector('div[data-testid="qr-container"]')
            
            if qr_section:
                self._authenticated = False
                return False
            
            if chat_list:
                self._authenticated = True
                logger.debug("✓ WhatsApp session active")
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
        scans_without_change = 0
        
        while time.time() - start_time < timeout:
            try:
                if self.check_authentication():
                    logger.info("\n✅ Authentication successful!")
                    return True
                
                qr_present = self.page.query_selector('div[data-testid="qr-container"]')
                
                if qr_present:
                    print("   ⚠️  QR code visible - waiting for scan...", end="\r")
                    scans_without_change += 1
                    
                    # Refresh if QR shown for too long
                    if scans_without_change > 20:
                        logger.info("   🔄 Refreshing...")
                        self.page.reload(wait_until="networkidle")
                        time.sleep(5)
                        scans_without_change = 0
                else:
                    print("   ⏳ Loading...", end="\r")
                
                time.sleep(3)
                
            except Exception as e:
                logger.error(f"Auth wait error: {e}")
                try:
                    self.page.goto(Config.WHATSAPP_WEB_URL, wait_until="networkidle")
                    time.sleep(3)
                except:
                    pass
                time.sleep(2)
        
        logger.error("\n❌ Authentication timeout")
        return False
    
    def get_unread_messages(self) -> List[WhatsAppMessage]:
        """Get unread messages from WhatsApp Web with phone number extraction."""
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

                    # Click to open chat and get full message + phone number
                    phone_number = ""
                    try:
                        chat.click()
                        time.sleep(1.5)

                        # Get full message
                        full_message = self._get_full_message()

                        # Extract phone number from chat info header
                        phone_number = self._extract_phone_from_chat_header()

                        # Go back to chat list
                        self.page.keyboard.press('Escape')
                        time.sleep(0.5)

                        message_text = full_message if full_message else preview

                    except Exception as e:
                        logger.debug(f"Could not get full message: {e}")
                        message_text = preview

                    # Detect if group or has media
                    is_group = 'group' in chat_name.lower()
                    has_media = any(c in message_text for c in ['📷', '🎤', '📹', '📎', 'Image', 'Video', 'file'])

                    msg = WhatsAppMessage(
                        message_id=hashlib.md5(f"{chat_name}:{timestamp}:{message_text}".encode()).hexdigest()[:16],
                        chat_name=chat_name,
                        phone_number=phone_number,  # Extracted from WhatsApp
                        from_name=chat_name,
                        message_text=message_text,
                        timestamp=datetime.fromisoformat(timestamp.replace('Z', '+00:00')) if timestamp else datetime.now(),
                        is_group=is_group,
                        has_media=has_media,
                        raw_data={
                            "preview": preview,
                            "timestamp_raw": timestamp,
                            "phone_extracted": phone_number
                        }
                    )
                    messages.append(msg)

                    if phone_number:
                        logger.info(f"   📱 {chat_name}: {message_text[:50]}... | Phone: {phone_number}")
                    else:
                        logger.info(f"   📱 {chat_name}: {message_text[:50]}... | Phone: Not found")

                except Exception as e:
                    logger.error(f"Parse message error: {e}")
                    continue

            logger.info(f"✓ Found {len(messages)} unread")

        except Exception as e:
            logger.error(f"Get messages error: {e}")

        return messages

    def _extract_phone_from_chat_header(self) -> str:
        """
        Extract phone number from WhatsApp chat.

        Strategy for WhatsApp Web 2024+:
        1. Look for phone in header with specific class pattern
        2. Phone numbers are in <span> with classes starting with "x"
        3. Must validate it's actually a phone number (10+ digits)

        Returns:
            Phone number if found (with minimum 10 digits), empty string otherwise
        """
        try:
            # Wait for chat header to fully load
            time.sleep(1.5)

            logger.debug("Searching for phone in chat header...")

            # Method 1: Look for span with phone pattern in header
            # WhatsApp uses: <span class="x...">+92 310 3863238</span>
            try:
                header_container = self.page.query_selector('div[data-testid="chat-info-non-group"], div[data-testid="chat-info"]')
                if header_container:
                    # Get all spans in header
                    spans = header_container.query_selector_all('span')

                    for span in spans:
                        text = span.text_content().strip()
                        logger.debug(f"Span text: {text[:50]}")

                        # Check if this looks like a phone number
                        # Must contain + or digits, and have 10+ digits total
                        digits = re.sub(r'[^\d]', '', text)
                        if ('+' in text or text[0].isdigit()) and len(digits) >= 10:
                            phone = self._parse_phone_from_text(text)
                            if phone and len(phone) >= 12:  # +92 + 10 digits
                                logger.debug(f"✓ Extracted phone from span: {phone}")
                                return phone
            except Exception as e:
                logger.debug(f"Header span search failed: {e}")

            # Method 2: Look for phone pattern in full header text
            try:
                header_text = self.page.query_selector('div[data-testid="chat-info-non-group"]')
                if header_text:
                    all_text = header_text.text_content()
                    logger.debug(f"Full header text: {all_text[:100]}")

                    # Look for phone number pattern
                    phone = self._parse_phone_from_text(all_text)
                    if phone and len(phone) >= 12:
                        logger.debug(f"✓ Extracted from full header: {phone}")
                        return phone
            except:
                pass

            # Method 3: Try chat list item (fallback)
            try:
                chat_in_list = self.page.query_selector('div[role="row"][aria-label*="unread"]')
                if chat_in_list:
                    title = chat_in_list.get_attribute('title')
                    if title:
                        logger.debug(f"Chat list title: {title}")
                        phone = self._parse_phone_from_text(title)
                        if phone and len(phone) >= 12:
                            logger.debug(f"✓ Extracted from chat list: {phone}")
                            return phone
            except:
                pass

        except Exception as e:
            logger.debug(f"Extract phone error: {e}")

        logger.debug("✗ No valid phone number found in WhatsApp UI")
        return ""

    def _parse_phone_from_text(self, text: str) -> Optional[str]:
        """
        Parse phone number from text content.

        Examples:
        - "Ahmed Khan +923001234567" → +923001234567
        - "+92 300 1234567" → +923001234567
        - "03001234567" → +923001234567

        Args:
            text: Text that may contain phone number

        Returns:
            Cleaned phone number or None
        """
        if not text or len(text.strip()) < 5:
            return None

        # Remove common WhatsApp labels
        text = re.sub(r'\b(online|today|yesterday|at\s+\d+:\d+|AM|PM)\b', '', text, flags=re.IGNORECASE)

        # Pattern 1: Look for + followed by 10-15 digits (with possible spaces/dashes)
        match = re.search(r'\+([\d\s\-\(\)]{10,15})', text)
        if match:
            phone = re.sub(r'[^\d]', '', match.group(0))
            if 10 <= len(phone) <= 15:
                return phone

        # Pattern 2: Look for Pakistan numbers (03XX...) - must be exactly 11 digits starting with 03
        match = re.search(r'\b(03\d{9})\b', text)
        if match:
            phone = match.group(1)
            return '+92' + phone[1:]  # Convert 03XX to +923XX

        # Pattern 3: Standalone 10-15 digit number
        match = re.search(r'\b(\d{10,15})\b', text)
        if match:
            phone = match.group(1)
            # Assume Pakistan if starts with 3 and is 10 digits
            if phone.startswith('3') and len(phone) == 10:
                return '+92' + phone
            # If 11 digits starting with 92, add +
            elif phone.startswith('92') and len(phone) == 11:
                return '+' + phone
            # Otherwise just add +
            elif len(phone) >= 10:
                return '+' + phone

        return None
    
    def _get_full_message(self) -> str:
        """Get full message text from opened chat."""
        try:
            # Try message container
            messages = self.page.query_selector_all('div[data-testid="message-container"]')
            if messages:
                last_msg = messages[-1]
                msg_el = last_msg.query_selector('span[dir="auto"]')
                if msg_el:
                    return msg_el.text_content().strip()
            
            # Try bubble
            last_bubble = self.page.query_selector('div[data-testid="bubble"]')
            if last_bubble:
                return last_bubble.text_content().strip()
                
        except Exception as e:
            logger.debug(f"Get full message error: {e}")
        
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
            logger.debug(f"Mark read error: {e}")
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
    """
    Production-ready WhatsApp AI Agent.
    
    Complete workflow:
    1. Read WhatsApp Web messages
    2. Extract phone numbers
    3. Generate AI drafts
    4. Send via UltraMsg when approved
    """
    
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
        logger.info(f"   UltraMsg: {'✅ Auto-send' if self.ultramsg_client.is_configured else '⚠️ Manual'}")
    
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
    
    def check_for_new_messages(self) -> List[WhatsAppMessage]:
        """Check for new WhatsApp messages."""
        if not self.playwright_client.check_authentication():
            return []
        
        messages = self.playwright_client.get_unread_messages()
        
        # Filter already processed
        new_messages = [m for m in messages if m.message_id not in self.processed_ids]
        
        return new_messages
    
    def extract_phone_number(self, message: WhatsAppMessage) -> str:
        """
        Get phone number for sender.

        Priority:
        1. Use phone extracted from WhatsApp Web (highest priority)
        2. Contact lookup by name
        3. Extract from chat name
        4. Create placeholder (user must edit)

        Returns:
            Cleaned phone number
        """
        # Priority 1: Use phone extracted from WhatsApp Web
        if message.phone_number and len(message.phone_number) >= 12:  # +92 + 10 digits
            logger.info(f"✓ Phone from WhatsApp: {message.phone_number}")
            # Save to contacts for future
            self.contact_manager.add_or_update_contact(message.from_name, message.phone_number)
            return message.phone_number
        elif message.phone_number:
            logger.debug(f"⚠️  Invalid phone from WhatsApp (too short): {message.phone_number}")

        # Priority 2: Contact lookup
        phone = self.contact_manager.get_phone(message.from_name)

        if phone and len(phone) >= 12:  # +92 + 10 digits
            logger.info(f"✓ Found contact: {message.from_name} -> {phone}")
            message.phone_number = phone
            return phone
        elif phone:
            logger.debug(f"⚠️  Invalid phone from contacts (too short): {phone}")

        # Priority 3: Extract from chat name
        phone = self.contact_manager.extract_phone_from_chat_name(message.chat_name)

        if phone and len(phone) >= 12:  # +92 + 10 digits
            logger.info(f"✓ Extracted from chat: {phone}")
            self.contact_manager.add_or_update_contact(message.from_name, phone)
            message.phone_number = phone
            return phone
        elif phone:
            logger.debug(f"⚠️  Invalid phone from chat name (too short): {phone}")

        # Priority 4: Create placeholder (only if nothing else works)
        logger.warning(f"⚠️ No valid phone for {message.from_name} (WhatsApp didn't show number)")
        logger.info(f"💡 Tip: Check if '{message.from_name}' has a phone number saved in your phone's contacts")
        phone = f"+PLACEHOLDER_{message.from_name.replace(' ', '_')}"
        self.contact_manager.add_or_update_contact(message.from_name, phone)
        message.phone_number = phone
        return phone
    
    def create_message_file(self, message: WhatsAppMessage) -> Path:
        """Create message file in Needs_Action."""
        phone = self.extract_phone_number(message)
        
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
            "status": "pending"
        }
        
        content = f"""## WhatsApp Message

**From**: {message.from_name}
**Phone**: `{phone}`
**Chat**: {message.chat_name}
**Time**: {message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

---

### Message Content

{message.message_text}

---

### Actions
- [ ] Review message
- [ ] Check draft reply in Pending_Approval/
- [ ] Edit phone number if placeholder
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
created: {datetime.now().isoformat()}
---

# Draft Reply

## Original Message
**From**: {message.from_name}
**Phone**: `{message.phone_number}`
**Chat**: {message.chat_name}
**Time**: {message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

```
{message.message_text}
```

---

## AI Draft Reply

{draft}

---

## Actions
- ✅ Review reply
- ✅ Edit if needed (especially phone number if placeholder)
- 📤 Move to `Approved/` to send
- ❌ Move to `Rejected/` to discard
"""
        
        filepath.write_text(content, encoding='utf-8')
        logger.info(f"✓ Created draft: {filename}")
        return filepath
    
    def check_approved_replies(self) -> List[Path]:
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
        """
        Process approved reply and send via UltraMsg.

        Extracts phone and message from file content.
        """
        logger.info(f"Processing: {file_path.name}")

        try:
            content = file_path.read_text(encoding='utf-8')

            # Extract phone number from frontmatter (between --- and ---)
            frontmatter_match = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
            phone = None

            if frontmatter_match:
                frontmatter = frontmatter_match.group(1)
                # Look for phone in frontmatter
                phone_match = re.search(r'^phone:\s*(\+?\d+)', frontmatter, re.MULTILINE)
                if phone_match:
                    phone = phone_match.group(1).strip()

            # Fallback: search entire content
            if not phone:
                phone_match = re.search(r"^phone:\s*(\+?\d+)", content, re.MULTILINE)
                if phone_match:
                    phone = phone_match.group(1).strip()

            # Validate phone number
            if not phone:
                logger.error("❌ No phone number found")
                logger.debug(f"Content preview: {content[:500]}")
                return False

            # Check if phone is just "+" or incomplete
            if phone == '+' or not phone or len(phone) < 10:
                logger.error(f"❌ Invalid phone number: '{phone}'")
                logger.info("💡 Check the draft file and ensure phone number is complete (e.g., +923001234567)")
                return False

            # Check for placeholder
            if phone.startswith('+PLACEHOLDER'):
                logger.error(f"⚠️ Placeholder phone - update contacts first: {phone}")
                logger.info("💡 Fix: Edit Contacts/contacts.json and add real phone number")
                return False

            # Clean phone - remove spaces, dashes, etc
            phone = re.sub(r'[\s\-]', '', phone)
            if not phone.startswith('+'):
                phone = '+' + phone

            # Extract message - look for content after "## AI Draft Reply"
            message = None

            # Pattern 1: After "## AI Draft Reply" header
            draft_match = re.search(r"## AI Draft Reply\s*\n+(.*?)\n+---", content, re.DOTALL)
            if draft_match:
                message = draft_match.group(1).strip()

            # Pattern 2: Between last two --- separators
            if not message:
                parts = content.split('---')
                if len(parts) >= 3:
                    # Get content between the last two ---
                    message = parts[-2].strip()
                    # Remove any markdown headers
                    message = re.sub(r'^#+\s*.*?\n', '', message).strip()

            # Pattern 3: After "Reply:" or "Message:"
            if not message:
                reply_match = re.search(r"(?:Reply:|Message:)\s*\n+(.+)", content, re.DOTALL)
                if reply_match:
                    message = reply_match.group(1).strip()

            # Clean message
            if message:
                # Remove markdown code blocks
                message = re.sub(r'^```.*?\n', '', message, flags=re.MULTILINE)
                message = re.sub(r'\n```$', '', message)
                message = message.strip()

            if not message or len(message) < 5:
                logger.error("❌ No valid message found")
                logger.debug(f"Content preview: {content[:500]}")
                return False

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
                logger.info(f"📱 Copy message and send to {phone} via WhatsApp Web")

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
            import traceback
            logger.debug(traceback.format_exc())
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
                    import traceback
                    logger.debug(traceback.format_exc())
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
    """Main entry point."""
    vault_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./Vault")
    check_interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    if not vault_path.is_absolute():
        vault_path = Path(__file__).parent / vault_path
    
    agent = WhatsAppAIAgent(vault_path, check_interval)
    agent.run()


if __name__ == "__main__":
    main()
