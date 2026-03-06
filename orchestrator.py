#!/usr/bin/env python3
r"""
Orchestrator with Real-time Approved Folder Monitoring

Watches Approved/ folder and sends emails immediately when drafts are approved.
Supports both Gmail API and SMTP.
"""

import json
import logging
import os
import re
import shutil
import smtplib
import sys
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Optional

import dotenv

# Load environment variables
dotenv.load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# SMTP Configuration
SMTP_SERVER = os.getenv("GMAIL_SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("GMAIL_SMTP_PORT", "587"))
SMTP_USER = os.getenv("GMAIL_SMTP_USER", "")
SMTP_PASSWORD = os.getenv("GMAIL_SMTP_PASSWORD", "")
USE_SMTP = os.getenv("USE_SMTP", "false").lower() == "true"

# Add base directory to path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# Import dashboard updater
try:
    from dashboard_updater import update_dashboard
    DASHBOARD_AVAILABLE = True
except:
    DASHBOARD_AVAILABLE = False


class ApprovedWatcher:
    """Watches Approved folder and sends emails immediately."""

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.approved_folder = vault_path / "Approved"
        self.done_folder = vault_path / "Done"
        self.rejected_folder = vault_path / "Rejected"
        self.logs_folder = vault_path / "Logs"
        
        # Ensure folders exist
        self.approved_folder.mkdir(parents=True, exist_ok=True)
        self.done_folder.mkdir(parents=True, exist_ok=True)
        self.logs_folder.mkdir(parents=True, exist_ok=True)
        
        # Track processed files
        self.processed_files: set[str] = set()
        self._load_processed()
        
        # MCP client
        self.mcp_available = self._check_mcp()
        
        print(f"\n📬 Approved Folder Watcher initialized")
        print(f"   Watching: {self.approved_folder}")
        print(f"   MCP Server: {'Available' if self.mcp_available else 'Not available'}")

    def _load_processed(self):
        """Load list of already processed files."""
        processed_file = self.vault_path / "In_Progress" / "orchestrator" / "processed.json"
        processed_file.parent.mkdir(parents=True, exist_ok=True)
        
        if processed_file.exists():
            try:
                data = json.loads(processed_file.read_text())
                self.processed_files = set(data.get("files", []))
            except:
                self.processed_files = set()

    def _save_processed(self):
        """Save processed files list."""
        processed_file = self.vault_path / "In_Progress" / "orchestrator" / "processed.json"
        data = {"files": list(self.processed_files), "updated": datetime.now().isoformat()}
        try:
            processed_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save processed: {e}")

    def _check_mcp(self) -> bool:
        """Check if MCP server is available."""
        # For now, always use direct API (more reliable)
        return False

    def get_approved_files(self) -> list[Path]:
        """Get all unprocessed EMAIL files in Approved folder (skip WhatsApp)."""
        if not self.approved_folder.exists():
            return []

        files = []
        for filepath in self.approved_folder.iterdir():
            if filepath.is_file() and filepath.suffix == ".md":
                # Skip WhatsApp reply files (handled by whatsapp_reply_sender.py)
                if filepath.name.startswith("WHATSAPP_REPLY_"):
                    continue

                if filepath.name not in self.processed_files:
                    files.append(filepath)

        return sorted(files, key=lambda f: f.stat().st_mtime)

    def read_draft_file(self, filepath: Path) -> dict[str, Any]:
        """Read draft file and extract email details."""
        try:
            content = filepath.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            logger.error(f"Unicode error reading {filepath.name}: {e}")
            # Try with latin-1 as fallback
            content = filepath.read_text(encoding="latin-1")

        # Extract frontmatter
        frontmatter = {}
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                fm_text = parts[1]
                for line in fm_text.strip().split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        frontmatter[key.strip()] = value.strip()

        # Extract draft body from between ``` marks
        draft_body = ""
        if "```" in content:
            parts = content.split("```")
            if len(parts) >= 2:
                draft_body = parts[1].strip()

        # Try to extract "from" from frontmatter first
        to_email = frontmatter.get("from", "")

        # If not in frontmatter, try to extract from content section
        if not to_email:
            # Look for "## From: Name <email@address.com>"
            from_match = re.search(r"##\s*From:\s*[^<]*<([^>]+)>", content)
            if from_match:
                to_email = from_match.group(1)
            else:
                # Try without angle brackets
                from_match = re.search(r"##\s*From:\s*(\S+@\S+)", content)
                if from_match:
                    to_email = from_match.group(1)

        # Clean up email if it has extra spaces
        to_email = to_email.strip() if to_email else ""

        # Get subject from frontmatter or content
        subject = frontmatter.get("original_subject", frontmatter.get("subject", ""))
        if not subject:
            # Try to extract from "## Original: Subject"
            orig_match = re.search(r"##\s*Original:\s*(.+)", content)
            if orig_match:
                subject = orig_match.group(1).strip()

        return {
            "path": filepath,
            "name": filepath.name,
            "email_message_id": frontmatter.get("email_message_id", ""),
            "to": to_email,
            "subject": subject,
            "draft_body": draft_body,
            "content": content,
        }

    def send_email(self, draft_info: dict) -> bool:
        """Send email using SMTP or direct API."""
        try:
            # Use SMTP if configured
            if USE_SMTP and SMTP_USER and SMTP_PASSWORD:
                return self._send_via_smtp(draft_info)
            else:
                # Fall back to Gmail API
                return self._send_direct(draft_info)
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def _send_via_smtp(self, draft_info: dict) -> bool:
        """Send email via Gmail SMTP."""
        try:
            print(f"   📤 Sending via SMTP: {SMTP_USER} -> {draft_info['to']}")

            # Create message
            msg = MIMEMultipart()
            msg["From"] = SMTP_USER
            msg["To"] = draft_info["to"]
            msg["Subject"] = draft_info["subject"]

            if draft_info.get("email_message_id"):
                msg["In-Reply-To"] = draft_info["email_message_id"]
                msg["References"] = draft_info["email_message_id"]

            msg.attach(MIMEText(draft_info["draft_body"], "plain"))

            # Connect to SMTP server and send
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()  # Secure the connection
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)

            logger.info(f"Email sent via SMTP to {draft_info['to']}")
            return True

        except Exception as e:
            logger.error(f"SMTP send error: {e}")
            return False

    def _send_via_mcp(self, draft_info: dict) -> bool:
        """Send email via MCP server."""
        try:
            import requests
            
            payload = {
                "tool": "send_email",
                "params": {
                    "to": draft_info["to"],
                    "subject": draft_info["subject"],
                    "body": draft_info["draft_body"],
                    "inReplyTo": draft_info["email_message_id"],
                }
            }
            
            response = requests.post(
                "http://localhost:8809/call",
                json=payload,
                timeout=30
            )
            
            result = response.json()
            
            if result.get("content"):
                response_text = result["content"][0]["text"]
                response_data = json.loads(response_text)
                
                if response_data.get("success"):
                    logger.info(f"Email sent via MCP: {response_data.get('messageId')}")
                    return True
            
            logger.error(f"MCP send failed: {result}")
            return False
            
        except Exception as e:
            logger.error(f"MCP error: {e}")
            return False

    def _send_direct(self, draft_info: dict) -> bool:
        """Send email directly via Gmail API."""
        try:
            from auth_handler import GmailAuthHandler
            from googleapiclient.discovery import build
            import base64
            from email.message import EmailMessage

            # Authenticate
            base_dir = Path(__file__).parent
            creds_path = base_dir / "credentials" / "gmail" / "credentials.json"
            token_path = base_dir / "credentials" / "gmail" / "token.json"

            auth = GmailAuthHandler(str(creds_path), str(token_path))
            creds = auth.authenticate()

            if not creds:
                logger.error("Authentication failed")
                return False

            # Build service
            service = build("gmail", "v1", credentials=creds)

            # Create message
            msg = EmailMessage()
            msg["To"] = draft_info["to"]
            msg["Subject"] = draft_info["subject"]
            if draft_info.get("email_message_id"):
                msg["In-Reply-To"] = draft_info["email_message_id"]
                msg["References"] = draft_info["email_message_id"]
            msg.set_content(draft_info["draft_body"])

            # Encode and send
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

            response = service.users().messages().send(
                userId="me",
                body={"raw": raw}
            ).execute()

            message_id = response.get("id", "unknown")
            logger.info(f"Email sent directly: {message_id}")
            return True

        except Exception as e:
            logger.error(f"Direct send error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def mark_as_read(self, message_id: str):
        """Mark original email as read."""
        try:
            from auth_handler import GmailAuthHandler
            from googleapiclient.discovery import build

            base_dir = Path(__file__).parent
            auth = GmailAuthHandler(
                str(base_dir / "credentials" / "gmail" / "credentials.json"),
                str(base_dir / "credentials" / "gmail" / "token.json")
            )
            creds = auth.authenticate()

            if creds:
                service = build("gmail", "v1", credentials=creds)

                # Fixed: Use correct API syntax
                service.users().messages().modify(
                    userId="me",
                    id=message_id,
                    body={"removeLabelIds": ["UNREAD"]}
                ).execute()

                logger.info(f"Marked email {message_id} as read")
        except Exception as e:
            logger.error(f"Failed to mark as read: {e}")

    def log_action(self, draft_info: dict, success: bool, message_id: str = None):
        """Log the action to JSON file."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_folder / f"{today}.json"
        
        # Load existing logs
        logs = []
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text())
            except:
                logs = []
        
        # Add new entry
        logs.append({
            "timestamp": datetime.now().isoformat(),
            "action_type": "email_sent",
            "email_id": draft_info.get("email_message_id", ""),
            "actor": "orchestrator",
            "result": "success" if success else "failed",
            "details": {
                "to": draft_info.get("to", ""),
                "subject": draft_info.get("original_subject", ""),
                "draft_file": draft_info.get("name", ""),
                "sent_message_id": message_id,
            }
        })
        
        # Save logs
        try:
            log_file.write_text(json.dumps(logs, indent=2))
        except Exception as e:
            logger.error(f"Failed to save log: {e}")

    def process_approved_file(self, filepath: Path) -> bool:
        """Process a single approved file."""
        print(f"\n{'='*70}")
        print(f"📧 Processing Approved Draft: {filepath.name}")
        print(f"{'='*70}")

        # Read draft
        draft_info = self.read_draft_file(filepath)

        print(f"   To: {draft_info['to']}")
        print(f"   Subject: {draft_info['subject']}")
        print()

        # Send email
        print("   📤 Sending email...")
        success = self.send_email(draft_info)

        if success:
            print(f"   ✅ Email sent successfully!")

            # Mark original as read
            if draft_info["email_message_id"]:
                print("   ✓ Marking original as read...")
                self.mark_as_read(draft_info["email_message_id"])

            # Move to Done
            dest = self.done_folder / filepath.name
            shutil.move(str(filepath), str(dest))
            print(f"   ✓ Moved to Done/")

            # Log action
            self.log_action(draft_info, True)

            # Update dashboard
            self._update_dashboard()

            # Update processed list
            self.processed_files.add(filepath.name)
            self._save_processed()

            print(f"\n{'='*70}")
            print(f"✅ COMPLETE - Email sent to {draft_info['to']}")
            print(f"{'='*70}")

            return True
        else:
            print(f"   ❌ Failed to send email")

            # Log failure
            self.log_action(draft_info, False)

            print(f"\n{'='*70}")
            print(f"❌ FAILED - Check logs for details")
            print(f"{'='*70}")

            return False

    def _update_dashboard(self):
        """Update Obsidian Dashboard."""
        try:
            from dashboard_updater import update_dashboard
            update_dashboard(self.vault_path)
        except Exception as e:
            logger.debug(f"Dashboard update skipped: {e}")

    def run(self):
        """Run the approved folder watcher."""
        print(f"\n{'='*70}")
        print(f"📬 Approved Folder Watcher RUNNING")
        print(f"{'='*70}")
        print(f"   Monitoring: {self.approved_folder}")
        print(f"   Check interval: 5 seconds")
        print(f"\n   Move draft files to Approved/ to send automatically")
        print(f"{'='*70}\n")

        check_count = 0
        last_dashboard_update = 0

        while True:
            try:
                check_count += 1
                timestamp = datetime.now().strftime("%H:%M:%S")

                # Update dashboard every 5 seconds (every loop)
                if check_count - last_dashboard_update >= 1:
                    self._update_dashboard()
                    last_dashboard_update = check_count

                # Get approved files
                files = self.get_approved_files()

                if files:
                    print(f"\n[{timestamp}] 📬 Found {len(files)} approved file(s)")

                    for filepath in files:
                        success = self.process_approved_file(filepath)

                        if success:
                            print(f"\n[{timestamp}] ✅ Sent: {filepath.name}")
                        else:
                            print(f"\n[{timestamp}] ❌ Failed: {filepath.name}")

                    print()
                else:
                    # Show status
                    print(f"[{timestamp}] ✓ Dashboard updated | Watching Approved/ ...", end="\r")

                # Wait 5 seconds
                time.sleep(5)

            except KeyboardInterrupt:
                print(f"\n\n🛑 Stopping Approved Watcher...")
                break
            except Exception as e:
                logger.error(f"Error in watch loop: {e}")
                time.sleep(5)


def main():
    """Main entry point."""
    vault_path = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DIR / "Vault"
    
    print("=" * 70)
    print("📬 Orchestrator - Approved Folder Monitor")
    print("=" * 70)
    print(f"Vault: {vault_path}")
    print("=" * 70)
    
    watcher = ApprovedWatcher(vault_path)
    watcher.run()


if __name__ == "__main__":
    main()
