#!/usr/bin/env python3
r"""
Gmail Watcher - Production-grade Gmail automation with OAuth 2.0.

Stable version with proper error handling and graceful shutdown.
"""

# Import logging FIRST to avoid conflicts
import sys

# Windows-safe logging setup
import logging
class WindowsSafeHandler(logging.StreamHandler):
    """Logging handler that replaces emojis with ASCII on Windows."""
    EMOJI_MAP = {
        '👁️': '[O]', '📋': '[T]', '🤖': '[AI]', '✅': '[OK]', '❌': '[X]',
        '⚠️': '[!]', '📝': '[N]', '🔄': '[~]', '📊': '[D]', '📁': '[F]',
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

# Now import other modules
import base64
import hashlib
import json
import os
import re
import shutil
import signal
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import dotenv

# Load environment variables FIRST
dotenv.load_dotenv()

# Add parent directory to path for imports
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))


# =============================================================================
# Configuration
# =============================================================================

class GmailConfig:
    """Centralized configuration."""

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.send",
    ]

    POLL_INTERVAL = int(os.getenv("GMAIL_POLL_INTERVAL", "30"))
    MAX_RETRIES = int(os.getenv("GMAIL_MAX_RETRIES", "5"))
    INITIAL_BACKOFF = float(os.getenv("GMAIL_INITIAL_BACKOFF", "1"))
    MAX_BACKOFF = float(os.getenv("GMAIL_MAX_BACKOFF", "300"))

    DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"
    DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
    RATE_LIMIT_HOURLY = int(os.getenv("RATE_LIMIT_HOURLY", "5"))
    FORCE_APPROVAL_NEW_SENDER = os.getenv("FORCE_APPROVAL_NEW_SENDER", "true").lower() == "true"
    FORCE_APPROVAL_LEGAL_KEYWORDS = os.getenv("FORCE_APPROVAL_LEGAL_KEYWORDS", "true").lower() == "true"

    CREDENTIALS_PATH = Path(os.getenv("GMAIL_CREDENTIALS_PATH", "./credentials/gmail/credentials.json"))
    TOKEN_PATH = Path(os.getenv("GMAIL_TOKEN_PATH", "./credentials/gmail/token.json"))

    # Resolve paths relative to base directory
    if not CREDENTIALS_PATH.is_absolute():
        CREDENTIALS_PATH = BASE_DIR.parent / CREDENTIALS_PATH
    if not TOKEN_PATH.is_absolute():
        TOKEN_PATH = BASE_DIR.parent / TOKEN_PATH


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class EmailData:
    """Represents a Gmail message."""
    message_id: str
    thread_id: str
    from_email: str
    from_name: str
    subject: str
    snippet: str
    body: str
    received_at: datetime
    labels: list[str]
    has_attachments: bool
    classification: str = "unknown"
    priority: str = "medium"
    requires_approval: bool = False
    approval_reason: Optional[str] = None
    requires_reply: bool = False
    is_new_sender: bool = False
    contains_legal_keywords: bool = False


# =============================================================================
# Email Classifier
# =============================================================================

class EmailClassifier:
    """Classifies emails into categories."""

    SALES_KEYWORDS = ["buy", "purchase", "order", "pricing", "quote", "product", "demo"]
    SUPPORT_KEYWORDS = ["help", "issue", "problem", "error", "bug", "not working", "support"]
    INVOICE_KEYWORDS = ["invoice", "payment", "bill", "receipt", "due", "overdue"]
    SPAM_KEYWORDS = ["congratulations you won", "lottery", "claim your prize", "act now"]
    INTERNAL_KEYWORDS = ["team", "internal", "meeting", "sync", "standup"]
    LEGAL_KEYWORDS = ["legal", "contract", "agreement", "liability", "confidential", "nda"]
    URGENT_KEYWORDS = ["urgent", "asap", "emergency", "critical", "immediate"]

    def __init__(self):
        pass

    def classify(self, email: EmailData) -> tuple[str, str, bool]:
        """Classify email and return (category, priority, requires_approval)."""
        text = f"{email.subject} {email.snippet} {email.body}".lower()

        contains_legal = any(kw in text for kw in self.LEGAL_KEYWORDS)
        email.contains_legal_keywords = contains_legal
        is_urgent = any(kw in text for kw in self.URGENT_KEYWORDS)

        scores = {
            "spam": self._score(text, self.SPAM_KEYWORDS),
            "invoice": self._score(text, self.INVOICE_KEYWORDS),
            "support": self._score(text, self.SUPPORT_KEYWORDS),
            "sales": self._score(text, self.SALES_KEYWORDS),
            "internal": self._score(text, self.INTERNAL_KEYWORDS),
        }

        max_score = max(scores.values())
        classification = "general" if max_score <= 0 else max(scores.keys(), key=lambda k: scores[k])

        if is_urgent or classification == "spam":
            priority = "critical" if classification != "spam" else "high"
        elif classification == "invoice":
            priority = "high"
        elif classification in ("support", "sales"):
            priority = "medium"
        else:
            priority = "low"

        requires_approval = (
            contains_legal or
            (email.is_new_sender and GmailConfig.FORCE_APPROVAL_NEW_SENDER) or
            classification == "spam"
        )

        return classification, priority, requires_approval

    def _score(self, text: str, keywords: list[str]) -> int:
        return sum(1 for kw in keywords if kw in text)


# =============================================================================
# Draft Reply Engine
# =============================================================================

class DraftReplyEngine:
    """Generates professional draft replies."""

    def generate_draft(self, email: EmailData) -> str:
        """Generate draft reply based on classification."""
        templates = {
            "sales": self._sales_reply,
            "support": self._support_reply,
            "invoice": self._invoice_reply,
            "internal": self._internal_reply,
        }
        generator = templates.get(email.classification, self._general_reply)
        return generator(email)

    def _sales_reply(self, email: EmailData) -> str:
        return f"""Dear {email.from_name or email.from_email},

Thank you for your interest in our products/services regarding "{email.subject}".

I would be happy to provide more information. Could you please share:
1. Your specific requirements
2. Your timeline
3. Your budget range (if applicable)

Looking forward to hearing from you.

Best regards,
[Your Name]
"""

    def _support_reply(self, email: EmailData) -> str:
        return f"""Dear {email.from_name or email.from_email},

Thank you for contacting support regarding "{email.subject}".

Could you please provide:
1. When did you first notice this issue?
2. What steps have you tried?
3. Any error messages?

I'm committed to resolving this for you.

Best regards,
[Your Name]
Support Team
"""

    def _invoice_reply(self, email: EmailData) -> str:
        return f"""Dear {email.from_name or email.from_email},

Thank you for your email regarding "{email.subject}".

I have received your invoice and will process it according to our payment terms.

Best regards,
[Your Name]
"""

    def _internal_reply(self, email: EmailData) -> str:
        return f"""Hi {email.from_name or email.from_email.split('@')[0]},

Thanks for your message about "{email.subject}".

[Add your response here]

Best,
[Your Name]
"""

    def _general_reply(self, email: EmailData) -> str:
        return f"""Dear {email.from_name or email.from_email},

Thank you for your email regarding "{email.subject}".

I will review your message and get back to you within 24-48 hours.

Best regards,
[Your Name]
"""


# =============================================================================
# Plan Generator
# =============================================================================

class PlanGenerator:
    """Generates action plans for emails."""

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.plans_folder = vault_path / "Plans"
        self.plans_folder.mkdir(parents=True, exist_ok=True)

    def generate_plan(self, email: EmailData) -> Path:
        """Generate plan file."""
        safe_id = hashlib.md5(email.message_id.encode()).hexdigest()[:8]
        filename = f"PLAN_EMAIL_{safe_id}.md"
        filepath = self.plans_folder / filename

        content = f"""---
type: email_plan
email_message_id: {email.message_id}
classification: {email.classification}
priority: {email.priority}
generated: {datetime.now().isoformat()}
---

# Email Action Plan

## Summary

| Field | Value |
|-------|-------|
| **From** | {email.from_name} <{email.from_email}> |
| **Subject** | {email.subject} |
| **Classification** | {email.classification} |
| **Priority** | {email.priority} |

---

## Content

{email.body[:3000] if len(email.body) > 3000 else email.body}

---

## Action Plan

- [ ] Review email content
- [ ] Review draft reply in Pending_Approval/
- [ ] Approve and send, or archive

### Approval: {"Required" if email.requires_approval else "Not Required"}
### Follow-up: {"Yes" if email.classification in ("sales", "support") else "No"}
"""

        filepath.write_text(content, encoding="utf-8")
        return filepath


# =============================================================================
# Structured Logger
# =============================================================================

class StructuredLogger:
    """Structured JSON logging."""

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._current_file: Optional[Path] = None
        self._current_date: Optional[str] = None
        self._log_buffer: list[dict] = []

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

    def log(self, action_type: str, email_id: str, actor: str, result: str = "success", details: dict = None):
        self._log_buffer.append({
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "email_id": email_id,
            "actor": actor,
            "result": result,
            "details": details or {},
        })
        if len(self._log_buffer) >= 10:
            self._flush_buffer()

    def flush(self):
        self._flush_buffer()


# =============================================================================
# Rate Limiter
# =============================================================================

class RateLimiter:
    """Rate limiter."""

    def __init__(self, max_per_hour: int):
        self.max_per_hour = max_per_hour
        self.processed_times: list[datetime] = []

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


# =============================================================================
# Gmail Watcher
# =============================================================================

class GmailWatcher:
    """Production Gmail watcher with OAuth 2.0."""

    def __init__(self, vault_path: Path, check_interval: int = None):
        self.vault_path = Path(vault_path)
        self.check_interval = check_interval or GmailConfig.POLL_INTERVAL
        self.credentials_path = GmailConfig.CREDENTIALS_PATH
        self.token_path = GmailConfig.TOKEN_PATH
        self.processed_ids_file = self.vault_path / "In_Progress" / "gmail" / "processed_ids.json"
        self.processed_ids_file.parent.mkdir(parents=True, exist_ok=True)

        # Components
        self.classifier = EmailClassifier()
        self.draft_engine = DraftReplyEngine()
        self.plan_generator = PlanGenerator(self.vault_path)
        self.rate_limiter = RateLimiter(GmailConfig.RATE_LIMIT_HOURLY)
        self.logger_impl = StructuredLogger(self.vault_path / "Logs")

        # State
        self.service = None
        self.processed_ids: set[str] = set()
        self.known_senders: set[str] = set()
        self._running = False
        self._shutdown_requested = False

        # Load state
        self._load_state()

        print(f"📧 Gmail Watcher initialized")
        print(f"   Vault: {self.vault_path}")
        print(f"   Poll Interval: {self.check_interval}s")

    def _load_state(self):
        """Load processed IDs and known senders."""
        if self.processed_ids_file.exists():
            try:
                data = json.loads(self.processed_ids_file.read_text())
                self.processed_ids = set(data.get("processed_ids", []))
            except:
                self.processed_ids = set()

        senders_file = self.vault_path / "In_Progress" / "gmail" / "known_senders.json"
        if senders_file.exists():
            try:
                data = json.loads(senders_file.read_text())
                self.known_senders = set(data.get("senders", []))
            except:
                self.known_senders = set()

    def _save_processed_ids(self):
        """Save processed IDs."""
        data = {
            "processed_ids": list(self.processed_ids),
            "last_updated": datetime.now().isoformat(),
            "count": len(self.processed_ids),
        }
        try:
            self.processed_ids_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save processed IDs: {e}")

    def _save_known_sender(self, email: str):
        """Add sender to known senders."""
        self.known_senders.add(email)
        senders_file = self.vault_path / "In_Progress" / "gmail" / "known_senders.json"
        try:
            data = {"senders": list(self.known_senders), "last_updated": datetime.now().isoformat()}
            senders_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save known sender: {e}")

    def authenticate(self) -> bool:
        """Authenticate with Gmail API."""
        print("\n" + "=" * 70)
        print("🔐 Gmail Authentication")
        print("=" * 70)

        try:
            # Add base directory to path for auth_handler import
            base_dir = Path(__file__).parent.parent
            sys.path.insert(0, str(base_dir))

            from auth_handler import GmailAuthHandler
            from googleapiclient.discovery import build

            auth_handler = GmailAuthHandler(
                credentials_path=self.credentials_path,
                token_path=self.token_path,
            )

            if auth_handler.has_token_file:
                print("✓ Found existing token")
            else:
                print("⚠️  First run - will open browser")

            creds = auth_handler.authenticate()

            if not creds:
                print("\n❌ Authentication failed")
                return False

            print(f"\n✅ Authentication successful!")
            self.service = build("gmail", "v1", credentials=creds)
            return True

        except FileNotFoundError as e:
            print(f"\n❌ {e}")
            print("\n📋 Setup:")
            print("1. https://console.cloud.google.com/apis/credentials")
            print("2. Create OAuth 2.0 Client ID (Desktop)")
            print("3. Download credentials.json")
            print(f"4. Save to: {self.credentials_path}")
            return False
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            print(f"\n❌ Authentication error: {e}")
            return False

    def check_for_updates(self) -> list[EmailData]:
        """Check Gmail for new emails."""
        new_emails = []

        if not self.rate_limiter.can_process():
            logger.warning(f"Rate limit exceeded ({GmailConfig.RATE_LIMIT_HOURLY}/hour)")
            return new_emails

        if not self.service:
            if not self.authenticate():
                return new_emails

        try:
            # Query: ALL emails from last 1 day (not just unread)
            # This ensures we catch emails opened on other devices too
            one_day_ago = (datetime.now() - timedelta(days=1)).strftime("%Y/%m/%d")
            query = f"after:{one_day_ago}"

            logger.info(f"Searching Gmail with query: {query}")

            # Fetch messages
            response = self.service.users().messages().list(
                userId="me",
                q=query,
                maxResults=50
            ).execute()

            messages = response.get("messages", [])
            logger.info(f"Found {len(messages)} messages in Gmail")

            for msg in messages:
                msg_id = msg["id"]

                # Skip already processed
                if msg_id in self.processed_ids:
                    continue

                try:
                    full_msg = self.service.users().messages().get(
                        userId="me", id=msg_id, format="full"
                    ).execute()

                    email = self._parse_message(full_msg)
                    if email:
                        email.is_new_sender = email.from_email not in self.known_senders
                        classification, priority, requires_approval = self.classifier.classify(email)
                        email.classification = classification
                        email.priority = priority
                        email.requires_approval = requires_approval
                        email.requires_reply = email.classification in ("sales", "support", "general")

                        if email.is_new_sender:
                            email.approval_reason = "New sender"
                        elif email.contains_legal_keywords:
                            email.approval_reason = "Legal keywords"

                        new_emails.append(email)
                        self.logger_impl.log("email_found", msg_id, "gmail_watcher",
                                           details={"from": email.from_email, "subject": email.subject})

                except Exception as e:
                    logger.error(f"Error fetching message {msg_id}: {e}")
                    continue

            return new_emails

        except Exception as e:
            logger.error(f"Gmail API error: {e}")
            # Try to re-authenticate on error
            self.service = None
            return []

    def _parse_message(self, full_msg: dict) -> Optional[EmailData]:
        """Parse Gmail message."""
        try:
            headers = {h["name"].lower(): h["value"] for h in full_msg.get("payload", {}).get("headers", [])}

            from_header = headers.get("from", "")
            from_email = re.search(r"<([^>]+)>", from_header)
            from_email = from_email.group(1) if from_email else from_header.strip()
            from_name = re.search(r'"?([^"<]+)"?\s*<', from_header)
            from_name = from_name.group(1).strip() if from_name else ""

            body = ""
            for part in full_msg.get("payload", {}).get("parts", []):
                if part.get("mimeType") == "text/plain":
                    data = part.get("body", {}).get("data", "")
                    if data:
                        body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                        break

            if not body:
                body_data = full_msg.get("payload", {}).get("body", {}).get("data", "")
                if body_data:
                    body = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")

            return EmailData(
                message_id=full_msg["id"],
                thread_id=full_msg["threadId"],
                from_email=from_email,
                from_name=from_name,
                subject=headers.get("subject", "No Subject"),
                snippet=full_msg.get("snippet", ""),
                body=body,
                received_at=datetime.now(),
                labels=full_msg.get("labelIds", []),
                has_attachments=False,
            )
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return None

    def create_action_file(self, email: EmailData) -> Path:
        """Create action file for email."""
        safe_id = hashlib.md5(email.message_id.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"EMAIL_{safe_id}_{timestamp}.md"

        frontmatter = {
            "type": "email",
            "message_id": email.message_id,
            "from": f"{email.from_name} <{email.from_email}>",
            "subject": email.subject,
            "received": email.received_at.isoformat(),
            "priority": email.priority,
            "classification": email.classification,
            "requires_approval": str(email.requires_approval).lower(),
            "status": "pending",
            "created": datetime.now().isoformat(),
        }

        if email.approval_reason:
            frontmatter["approval_reason"] = email.approval_reason

        content = f"""## Email Content

**From**: {email.from_name} <{email.from_email}>
**Subject**: {email.subject}
**Classification**: {email.classification}

---

{email.body if email.body else email.snippet}

---

## Notes
- New Sender: {"Yes" if email.is_new_sender else "No"}
- Legal Keywords: {"Yes" if email.contains_legal_keywords else "No"}
"""

        if email.requires_approval:
            content += f"\n## ⚠️ Approval Required\n\n**Reason**: {email.approval_reason}\n"

        # Create file
        filepath = self.vault_path / "Needs_Action" / filename
        fm = "\n".join([f"{k}: {v}" for k, v in frontmatter.items()])
        filepath.write_text(f"---\n{fm}\n---\n\n{content}", encoding="utf-8")

        # Generate plan and draft
        self.plan_generator.generate_plan(email)
        if email.requires_reply:
            self._create_draft_reply(email, safe_id)

        # Update state
        self.processed_ids.add(email.message_id)
        self._save_processed_ids()
        self._save_known_sender(email.from_email)
        self.rate_limiter.record()

        self.logger_impl.log("email_processed", email.message_id, "gmail_watcher",
                           details={"classification": email.classification})

        return filepath

    def _create_draft_reply(self, email: EmailData, safe_id: str) -> Path:
        """Create draft reply."""
        draft = self.draft_engine.generate_draft(email)
        filename = f"EMAIL_REPLY_{safe_id}.md"
        filepath = self.vault_path / "Pending_Approval" / filename

        content = f"""---
type: email_reply
email_message_id: {email.message_id}
from: {email.from_email}
original_subject: {email.subject}
status: pending_approval
---

# Draft Reply

## Original Email
**From**: {email.from_name} <{email.from_email}>
**Subject**: {email.subject}

---

```
{draft}
```

---

## Actions
- Move to `/Approved/` to send
- Move to `/Rejected/` to discard
"""

        filepath.write_text(content, encoding="utf-8")
        return filepath

    def run(self):
        """Run the watcher loop."""
        self._running = True

        # Setup signal handlers
        def signal_handler(sig, frame):
            logger.info("Shutdown requested")
            self._shutdown_requested = True
            self._running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        print("\n" + "=" * 70)
        print("✅ Gmail Watcher RUNNING")
        print("=" * 70)
        print(f"📬 Poll interval: {self.check_interval}s")
        print(f"🔒 Rate limit: {GmailConfig.RATE_LIMIT_HOURLY}/hour")
        print(f"📁 Vault: {self.vault_path}")
        print("\nPress Ctrl+C to stop")
        print("=" * 70 + "\n")

        # Authenticate first
        if not self.authenticate():
            logger.error("Authentication failed - exiting")
            return

        iteration = 0
        total_processed = 0

        while self._running and not self._shutdown_requested:
            try:
                iteration += 1
                timestamp = datetime.now().strftime("%H:%M:%S")
                logger.info(f"Check #{iteration} [{timestamp}] - Looking for new emails...")

                emails = self.check_for_updates()

                if emails:
                    print(f"\n📧 Found {len(emails)} new email(s) at {timestamp}")
                    for i, email in enumerate(emails, 1):
                        try:
                            action_file = self.create_action_file(email)
                            total_processed += 1
                            # Show first 5 in detail, rest in summary
                            if i <= 5:
                                print(f"   ✓ [{email.classification.upper()}] {email.subject[:50]}")
                        except Exception as e:
                            logger.error(f"Error creating action file: {e}")

                    if len(emails) > 5:
                        print(f"   ... and {len(emails) - 5} more")

                    print(f"\n📊 Session Stats: {total_processed} emails processed in {iteration} checks")

                    # Update dashboard
                    try:
                        base_dir = Path(__file__).parent.parent
                        sys.path.insert(0, str(base_dir))
                        from dashboard_updater import DashboardUpdater
                        updater = DashboardUpdater(self.vault_path)
                        updater.update_dashboard()
                    except Exception as e:
                        logger.error(f"Dashboard update failed: {e}")
                else:
                    remaining = self.rate_limiter.get_remaining()
                    next_check = datetime.now() + timedelta(seconds=self.check_interval)
                    print(f"✓ No new emails (Rate limit: {remaining}/hr) | Next check: {next_check.strftime('%H:%M:%S')}")

            except Exception as e:
                logger.error(f"Loop error: {e}")
                self.service = None  # Force re-auth on next iteration

            # Wait for next check with progress dots
            for sec in range(self.check_interval):
                if self._shutdown_requested:
                    break
                if sec % 30 == 0:
                    print(".", end="", flush=True)
                time.sleep(1)

        self.stop()

    def stop(self):
        """Stop watcher."""
        self._running = False
        self._shutdown_requested = False
        self.logger_impl.flush()
        logger.info("Gmail Watcher stopped")


# =============================================================================
# Main
# =============================================================================

def main():
    """Main entry point."""
    vault_path = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DIR.parent / "Vault"
    check_interval = int(sys.argv[2]) if len(sys.argv) > 2 else GmailConfig.POLL_INTERVAL

    print("=" * 70)
    print("📧 Gmail Watcher - Silver Tier")
    print("=" * 70)
    print(f"Vault: {vault_path}")
    print(f"Poll Interval: {check_interval}s")
    print(f"Credentials: {GmailConfig.CREDENTIALS_PATH}")
    print("=" * 70 + "\n")

    # Check credentials exist
    if not GmailConfig.CREDENTIALS_PATH.exists():
        print(f"❌ Credentials not found: {GmailConfig.CREDENTIALS_PATH}")
        print("\n📋 Setup:")
        print("1. https://console.cloud.google.com/apis/credentials")
        print("2. Create OAuth 2.0 Client ID (Desktop)")
        print("3. Download credentials.json")
        print(f"4. Save to: {GmailConfig.CREDENTIALS_PATH}")
        sys.exit(1)

    watcher = GmailWatcher(vault_path, check_interval)

    try:
        watcher.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
