#!/usr/bin/env python3
r"""
WhatsApp Watcher - Real Playwright-based WhatsApp Web monitoring.

Monitors actual WhatsApp Web for new messages using browser automation.
"""

import hashlib
import json
import os
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import dotenv

dotenv.load_dotenv()

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR.parent))

from base_watcher import BaseWatcher
from ai_draft_generator import AIDraftReplyGenerator


class WhatsAppConfig:
    WHATSAPP_WEB_URL = "https://web.whatsapp.com"
    BROWSER_HEADLESS = os.getenv("WHATSAPP_BROWSER_HEADLESS", "false").lower() == "true"
    POLL_INTERVAL = int(os.getenv("WHATSAPP_POLL_INTERVAL", "30"))
    MAX_MESSAGES_PER_POLL = int(os.getenv("WHATSAPP_MAX_MESSAGES_PER_POLL", "20"))
    RATE_LIMIT_HOURLY = int(os.getenv("WHATSAPP_RATE_LIMIT_HOURLY", "10"))
    VAULT_PATH = Path(os.getenv("WHATSAPP_VAULT_PATH", "./Vault"))
    SESSION_PATH = Path(os.getenv("WHATSAPP_SESSION_PATH", "./sessions/whatsapp"))

    if not VAULT_PATH.is_absolute():
        VAULT_PATH = BASE_DIR.parent / VAULT_PATH
    if not SESSION_PATH.is_absolute():
        SESSION_PATH = BASE_DIR.parent / SESSION_PATH


@dataclass
class WhatsAppMessage:
    message_id: str
    chat_name: str
    chat_id: str
    from_name: str
    message_text: str
    timestamp: datetime
    is_group: bool
    has_media: bool
    classification: str = "unknown"
    priority: str = "medium"
    requires_approval: bool = False


class WhatsAppMessageClassifier:
    URGENT_KEYWORDS = ["urgent", "asap", "emergency", "critical", "immediate", "help"]
    SPAM_KEYWORDS = ["winner", "lottery", "prize", "click here", "free money"]
    SUPPORT_KEYWORDS = ["help", "issue", "problem", "error", "not working"]
    BUSINESS_KEYWORDS = ["meeting", "call", "project", "work", "deadline", "task"]

    def classify(self, message: WhatsAppMessage) -> tuple:
        text = message.message_text.lower()
        is_urgent = any(kw in text for kw in self.URGENT_KEYWORDS)
        is_spam = any(kw in text for kw in self.SPAM_KEYWORDS)

        if is_spam:
            category = "spam"
        elif any(kw in text for kw in self.SUPPORT_KEYWORDS):
            category = "support"
        elif any(kw in text for kw in self.BUSINESS_KEYWORDS):
            category = "business"
        else:
            category = "personal"

        priority = "critical" if is_urgent else ("medium" if category in ("business", "support") else "low")
        requires_approval = is_spam
        return category, priority, requires_approval


class PlanGenerator:
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.plans_folder = vault_path / "Plans"
        self.plans_folder.mkdir(parents=True, exist_ok=True)

    def generate_plan(self, message: WhatsAppMessage) -> Path:
        safe_id = message.message_id
        filepath = self.plans_folder / f"PLAN_WHATSAPP_{safe_id}.md"
        content = f"""---
type: whatsapp_plan
message_id: {message.message_id}
classification: {message.classification}
priority: {message.priority}
---

# WhatsApp Action Plan

**From**: {message.from_name}  
**Chat**: {message.chat_name}  
**Classification**: {message.classification}

---

{message.message_text[:3000]}

---

- [ ] Review message
- [ ] Review draft reply
- [ ] Approve or archive
"""
        filepath.write_text(content, encoding="utf-8")
        return filepath


class RateLimiter:
    def __init__(self, max_per_hour: int):
        self.max_per_hour = max_per_hour
        self.processed_times = []

    def can_process(self) -> bool:
        now = datetime.now()
        cutoff = now - timedelta(hours=1)
        self.processed_times = [t for t in self.processed_times if t > cutoff]
        return len(self.processed_times) < self.max_per_hour

    def record(self):
        self.processed_times.append(datetime.now())

    def get_remaining(self) -> int:
        now = datetime.now()
        cutoff = now - timedelta(hours=1)
        self.processed_times = [t for t in self.processed_times if t > cutoff]
        return max(0, self.max_per_hour - len(self.processed_times))


class StructuredLogger:
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._current_file = None
        self._current_date = None
        self._log_buffer = []

    def _get_log_file(self) -> Path:
        today = datetime.now().strftime("%Y-%m-%d")
        if self._current_date != today:
            self._flush_buffer()
            self._current_date = today
            self._current_file = self.log_dir / f"{today}.json"
            if self._current_file.exists():
                try:
                    self._log_buffer = json.loads(self._current_file.read_text())
                except:
                    self._log_buffer = []
        return self._current_file

    def _flush_buffer(self):
        if self._current_file and self._log_buffer:
            self._current_file.write_text(json.dumps(self._log_buffer, indent=2), encoding="utf-8")

    def log(self, action_type: str, message_id: str, actor: str, result: str = "success", details: dict = None):
        self._log_buffer.append({
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "message_id": message_id,
            "actor": actor,
            "result": result,
            "details": details or {},
        })
        if len(self._log_buffer) >= 10:
            self._flush_buffer()

    def flush(self):
        self._flush_buffer()


class PlaywrightWhatsAppClient:
    """Real WhatsApp Web client using Playwright."""

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.session_path = WhatsAppConfig.SESSION_PATH
        self.playwright = None
        self.browser = None
        self.page = None
        self._authenticated = False
        self.session_path.mkdir(parents=True, exist_ok=True)

    def start_browser(self):
        try:
            from playwright.sync_api import sync_playwright

            print("   🌐 Starting browser...")
            self.playwright = sync_playwright().start()

            self.browser = self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.session_path),
                headless=WhatsAppConfig.BROWSER_HEADLESS,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
                timeout=60000,
            )

            self.page = self.browser.pages[0] if self.browser.pages else self.browser.new_page()
            print("   ✓ Browser started")
            return True
        except Exception as e:
            print(f"   ❌ Error starting browser: {e}")
            return False

    def navigate_to_whatsapp(self):
        try:
            print(f"   🌐 Navigating to WhatsApp Web...")
            self.page.goto(WhatsAppConfig.WHATSAPP_WEB_URL, wait_until="networkidle", timeout=60000)
            time.sleep(5)
            print("   ✓ WhatsApp Web loaded")
            return True
        except Exception as e:
            print(f"   ❌ Error navigating: {e}")
            return False

    def check_authentication(self) -> bool:
        try:
            time.sleep(2)
            chat_list = self.page.query_selector('div[role="row"]')
            search_box = self.page.query_selector('div[contenteditable="true"][data-tab="10"]')
            
            if chat_list or search_box:
                try:
                    chats = self.page.query_selector_all('div[role="row"]')
                    if len(chats) > 0:
                        self._authenticated = True
                        print("   ✓ WhatsApp session active")
                        return True
                except:
                    pass

            qr_section = self.page.query_selector('div[data-testid="qr-container"]')
            if qr_section:
                self._authenticated = False
                return False

            loading = self.page.query_selector('div[data-testid="bootstrap-loading"]')
            if loading:
                print("   ⏳ Loading...")
                return False

            self._authenticated = False
            return False
        except Exception as e:
            print(f"   ❌ Error checking auth: {e}")
            return False

    def wait_for_authentication(self, timeout=180):
        print("\n" + "=" * 70)
        print("📱 WhatsApp Authentication Required")
        print("=" * 70)
        print("\n1. Open WhatsApp on your phone")
        print("2. Go to: Settings > Linked Devices")
        print("3. Tap: Link a Device")
        print("4. Scan the QR code")
        print("\n⏳ Waiting (3 minutes)...")
        print("=" * 70 + "\n")

        start_time = time.time()
        scans_without_change = 0

        while time.time() - start_time < timeout:
            try:
                if self.check_authentication():
                    time.sleep(3)
                    if self.check_authentication():
                        print("\n✅ Authentication successful!")
                        return True

                qr_present = self.page.query_selector('div[data-testid="qr-container"]')
                
                if qr_present:
                    print("   ⚠️  QR code visible - waiting for scan...", end="\r")
                else:
                    print("   ⏳ Loading...", end="\r")

                if qr_present:
                    scans_without_change += 1
                    if scans_without_change > 20:
                        print("\n   🔄 Refreshing...")
                        self.page.reload(wait_until="networkidle")
                        time.sleep(5)
                        scans_without_change = 0

                time.sleep(3)
            except Exception as e:
                print(f"\n   Error: {e}")
                try:
                    self.page.goto(WhatsAppConfig.WHATSAPP_WEB_URL, wait_until="networkidle")
                    time.sleep(3)
                except:
                    pass
                time.sleep(2)

        print("\n❌ Authentication timeout")
        return False

    def get_unread_messages(self):
        messages = []
        if not self._authenticated:
            return messages

        try:
            self.page.wait_for_selector('div[role="row"]', timeout=5000)
            time.sleep(2)
            chats = self.page.query_selector_all('div[role="row"]')
            print(f"   📱 Found {len(chats)} chats...")

            for chat in chats[:WhatsAppConfig.MAX_MESSAGES_PER_POLL]:
                try:
                    unread_badge = chat.query_selector('[aria-label*="unread"]')
                    if not unread_badge:
                        continue

                    chat_name_el = chat.query_selector('span[title]')
                    message_el = chat.query_selector('span[dir="auto"]')
                    time_el = chat.query_selector('time')

                    chat_name = chat_name_el.get_attribute('title') if chat_name_el else 'Unknown'
                    preview = message_el.text_content() if message_el else ''
                    timestamp = time_el.get_attribute('datetime') if time_el else datetime.now().isoformat()

                    # Click to get full message
                    try:
                        chat.click()
                        time.sleep(1.5)
                        full_message = self._get_full_message()
                        self.page.keyboard.press('Escape')
                        time.sleep(0.5)
                        message_text = full_message if full_message else preview
                    except:
                        message_text = preview

                    is_group = 'group' in chat_name.lower()
                    has_media = any(c in message_text for c in ['📷', '🎤', '📹', '📎'])

                    msg = WhatsAppMessage(
                        message_id=hashlib.md5(f"{chat_name}:{timestamp}:{message_text}".encode()).hexdigest()[:16],
                        chat_name=chat_name,
                        chat_id=chat_name.lower().replace(' ', '_'),
                        from_name=chat_name,
                        message_text=message_text,
                        timestamp=datetime.fromisoformat(timestamp.replace('Z', '+00:00')),
                        is_group=is_group,
                        has_media=has_media,
                    )
                    messages.append(msg)
                    print(f"      📱 {chat_name}: {message_text[:50]}...")
                except Exception as e:
                    print(f"   Error: {e}")
                    continue

            print(f"   ✓ Found {len(messages)} unread")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        return messages

    def _get_full_message(self) -> str:
        try:
            messages = self.page.query_selector_all('div[data-testid="message-container"]')
            if messages:
                last_msg = messages[-1]
                msg_el = last_msg.query_selector('span[dir="auto"]')
                if msg_el:
                    return msg_el.text_content().strip()
            
            last_bubble = self.page.query_selector('div[data-testid="bubble"]')
            if last_bubble:
                return last_bubble.text_content().strip()
        except Exception as e:
            print(f"   ⚠️  Could not get full message: {e}")
        return ""

    def mark_chat_as_read(self, chat_name: str):
        try:
            chats = self.page.query_selector_all('div[role="row"]')
            for chat in chats:
                name_el = chat.query_selector('span[title]')
                if name_el and name_el.text_content() == chat_name:
                    chat.click()
                    time.sleep(1)
                    self.page.keyboard.press('Escape')
                    time.sleep(0.5)
                    print(f"   ✓ Marked '{chat_name}' as read")
                    return True
        except Exception as e:
            print(f"   ❌ Error: {e}")
        return False

    def close(self):
        try:
            if self.browser:
                print("   ✓ Browser session preserved")
        except:
            pass
        try:
            if self.playwright:
                self.playwright.stop()
        except:
            pass


class WhatsAppWatcher(BaseWatcher):
    def __init__(self, vault_path: Path, check_interval: int = None):
        vault_path = Path(vault_path)
        super().__init__(vault_path, check_interval or WhatsAppConfig.POLL_INTERVAL)

        self.classifier = WhatsAppMessageClassifier()
        self.ai_draft_generator = AIDraftReplyGenerator()
        self.plan_generator = PlanGenerator(vault_path)
        self.playwright_client = PlaywrightWhatsAppClient(vault_path)
        self.rate_limiter = RateLimiter(WhatsAppConfig.RATE_LIMIT_HOURLY)
        self.logger_impl = StructuredLogger(vault_path / "Logs")

        self.processed_ids = set()
        self.known_contacts = set()
        self._running = False

        self._load_state()

        print(f"\n💬 WhatsApp Watcher initialized")
        print(f"   Vault: {vault_path}")
        print(f"   Poll Interval: {self.check_interval}s")
        if self.ai_draft_generator.available:
            print(f"   ✨ AI Draft: ✅ Enabled")
        else:
            print(f"   ✨ AI Draft: ⚠️ Templates")

    def _load_state(self):
        processed_file = self.vault_path / "In_Progress" / "whatsapp" / "processed_ids.json"
        processed_file.parent.mkdir(parents=True, exist_ok=True)

        if processed_file.exists():
            try:
                data = json.loads(processed_file.read_text())
                self.processed_ids = set(data.get("processed_ids", []))
                print(f"   ✓ Loaded {len(self.processed_ids)} processed IDs")
            except Exception as e:
                print(f"   ⚠️  Load error: {e}")
                self.processed_ids = set()
        else:
            print(f"   ℹ️  First run")
            self.processed_ids = set()

        contacts_file = self.vault_path / "In_Progress" / "whatsapp" / "known_contacts.json"
        if contacts_file.exists():
            try:
                data = json.loads(contacts_file.read_text())
                self.known_contacts = set(data.get("contacts", []))
            except:
                self.known_contacts = set()

    def _save_processed_ids(self):
        processed_file = self.vault_path / "In_Progress" / "whatsapp" / "processed_ids.json"
        data = {
            "processed_ids": list(self.processed_ids),
            "last_updated": datetime.now().isoformat(),
            "count": len(self.processed_ids),
        }
        try:
            processed_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"   ✓ Saved {len(self.processed_ids)} IDs")
        except Exception as e:
            self.logger.error(f"Save error: {e}")

    def _save_known_contact(self, contact: str):
        self.known_contacts.add(contact)
        contacts_file = self.vault_path / "In_Progress" / "whatsapp" / "known_contacts.json"
        try:
            data = {"contacts": list(self.known_contacts), "last_updated": datetime.now().isoformat()}
            contacts_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            self.logger.error(f"Contact save error: {e}")

    def check_for_updates(self):
        new_messages = []

        if not self.rate_limiter.can_process():
            return new_messages

        if not self.playwright_client.check_authentication():
            return new_messages

        messages = self.playwright_client.get_unread_messages()

        for msg in messages:
            if msg.message_id in self.processed_ids:
                print(f"   ⏭️  Skip: {msg.chat_name}")
                continue

            classification, priority, requires_approval = self.classifier.classify(msg)
            msg.classification = classification
            msg.priority = priority
            msg.requires_approval = requires_approval

            new_messages.append(msg)
            self.logger_impl.log("message_found", msg.message_id, "whatsapp_watcher",
                               details={"from": msg.from_name, "chat": msg.chat_name})

        if messages:
            print(f"   📊 {len(messages)} found, {len(new_messages)} new")

        return new_messages

    def create_action_file(self, message: WhatsAppMessage) -> Path:
        safe_id = message.message_id
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"WHATSAPP_{safe_id}_{timestamp}.md"

        frontmatter = {
            "type": "whatsapp_message",
            "message_id": message.message_id,
            "chat_name": message.chat_name,
            "chat_id": message.chat_id,
            "from": message.from_name,
            "received": message.timestamp.isoformat(),
            "priority": message.priority,
            "classification": message.classification,
            "requires_approval": str(message.requires_approval).lower(),
            "status": "pending",
            "created": datetime.now().isoformat(),
            "is_group": str(message.is_group).lower(),
            "has_media": str(message.has_media).lower(),
        }

        content = f"""## WhatsApp Message

**From**: {message.from_name}
**Chat**: {message.chat_name}
**Type**: {"Group" if message.is_group else "Individual"}

---

### Message

{message.message_text}

---

- New Contact: {"Yes" if message.from_name not in self.known_contacts else "No"}
- Has Media: {"Yes" if message.has_media else "No"}
"""

        filepath = self.vault_path / "Needs_Action" / filename
        fm = "\n".join([f"{k}: {v}" for k, v in frontmatter.items()])
        filepath.write_text(f"---\n{fm}\n---\n\n{content}", encoding="utf-8")

        self.plan_generator.generate_plan(message)
        self._create_draft_reply(message, safe_id)

        self.processed_ids.add(message.message_id)
        self._save_processed_ids()
        self._save_known_contact(message.from_name)
        self.rate_limiter.record()

        print(f"   ✓ Created: {filename}")
        return filepath

    def _create_draft_reply(self, message: WhatsAppMessage, safe_id: str) -> Path:
        draft = self.ai_draft_generator.generate_draft(
            message_text=message.message_text,
            sender_name=message.from_name,
            chat_name=message.chat_name,
            is_group=message.is_group
        )
        
        filename = f"WHATSAPP_REPLY_{safe_id}.md"
        filepath = self.vault_path / "Pending_Approval" / filename

        content = f"""---
type: whatsapp_reply
message_id: {message.message_id}
from: {message.from_name}
chat_name: {message.chat_name}
status: pending_approval
---

# Draft Reply

## Original
**From**: {message.from_name}
**Chat**: {message.chat_name}

```
{message.message_text}
```

---

## Reply

{draft}

---

## Actions
- ✅ Review
- ✅ Edit if needed
- 📤 Move to `Approved/` to send
- ❌ Move to `Rejected/`
"""

        filepath.write_text(content, encoding="utf-8")
        print(f"   ✓ Created draft: {filename}")
        return filepath

    def run(self):
        self._running = True

        def signal_handler(sig, frame):
            self.logger.info("Shutdown requested")
            self._running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        print("\n" + "=" * 70)
        print("💬 WhatsApp Watcher RUNNING")
        print("=" * 70)
        print(f"📬 Poll: {self.check_interval}s")
        print(f"🔒 Rate: {WhatsAppConfig.RATE_LIMIT_HOURLY}/hr")
        print(f"📁 Vault: {self.vault_path}")
        print("\nPress Ctrl+C to stop")
        print("=" * 70 + "\n")

        if not self.playwright_client.start_browser():
            print("❌ Browser start failed")
            return

        self.playwright_client.navigate_to_whatsapp()

        if not self.playwright_client.check_authentication():
            if not self.playwright_client.wait_for_authentication():
                print("❌ Auth failed")
                self.playwright_client.close()
                return

        try:
            while self._running:
                try:
                    messages = self.check_for_updates()

                    if messages:
                        print(f"\n📱 Found {len(messages)} new")
                        for msg in messages:
                            self.create_action_file(msg)
                            self.playwright_client.mark_chat_as_read(msg.chat_name)
                        print(f"   ✓ Processed {len(messages)}")

                        # Update dashboard after processing
                        try:
                            base_dir = Path(__file__).parent.parent
                            sys.path.insert(0, str(base_dir))
                            from dashboard_updater import update_dashboard
                            update_dashboard(self.vault_path)
                        except:
                            pass
                    else:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        remaining = self.rate_limiter.get_remaining()
                        print(f"[{timestamp}] ✓ No new ({remaining}/hr)", end="\r")

                    time.sleep(self.check_interval)
                except Exception as e:
                    self.logger.error(f"Loop error: {e}")
                    time.sleep(self.check_interval)
        except KeyboardInterrupt:
            self.logger.info("Shutdown requested")
        finally:
            self.stop()

    def stop(self):
        self._running = False
        self.playwright_client.close()
        self.logger_impl.flush()

        # Update dashboard
        try:
            base_dir = Path(__file__).parent.parent
            sys.path.insert(0, str(base_dir))
            from dashboard_updater import update_dashboard
            update_dashboard(self.vault_path)
        except Exception as e:
            logger.debug(f"Dashboard update skipped: {e}")

        self.logger.info("Stopped")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="WhatsApp Watcher")
    parser.add_argument("vault_path", nargs="?", default="./Vault")
    parser.add_argument("interval", nargs="?", type=int, default=30)
    parser.add_argument("--interval", "-i", dest="interval_flag", type=int, default=None)

    args = parser.parse_args()
    interval = args.interval_flag if args.interval_flag is not None else args.interval

    vault_path = Path(args.vault_path)
    if not vault_path.is_absolute():
        vault_path = Path(__file__).parent.parent / vault_path

    watcher = WhatsAppWatcher(vault_path, interval)
    watcher.run()


if __name__ == "__main__":
    main()
