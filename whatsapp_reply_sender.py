#!/usr/bin/env python3
r"""
WhatsApp Reply Sender - Prepares approved replies for manual sending.

Watches Approved/ folder and prepares WhatsApp messages.
"""

import json
import logging
import os
import re
import shutil
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

import dotenv

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))


class WhatsAppReplySender:
    def __init__(self, vault_path: Path, check_interval: int = 5):
        self.vault_path = Path(vault_path)
        self.approved_folder = self.vault_path / "Approved"
        self.done_folder = self.vault_path / "Done"
        self.check_interval = check_interval
        self.processed_files = set()
        self._running = False

        self.approved_folder.mkdir(parents=True, exist_ok=True)
        self.done_folder.mkdir(parents=True, exist_ok=True)

        print(f"\n💬 WhatsApp Reply Sender initialized")
        print(f"   Watching: {self.approved_folder}")
        print(f"   Check: {check_interval}s")

    def check_for_approved_replies(self):
        approved_files = []
        try:
            if not self.approved_folder.exists():
                return []

            for file in self.approved_folder.glob("WHATSAPP_REPLY_*.md"):
                if file.name not in self.processed_files:
                    try:
                        content = file.read_text(encoding='utf-8')
                        if "type: whatsapp_reply" in content:
                            approved_files.append(file)
                            self.processed_files.add(file.name)
                            logger.info(f"Found: {file.name}")
                    except Exception as e:
                        logger.error(f"Read error: {e}")
        except Exception as e:
            logger.error(f"Check error: {e}")

        return approved_files

    def process_approved_file(self, file_path: Path) -> bool:
        logger.info(f"Processing: {file_path.name}")

        try:
            content = file_path.read_text(encoding='utf-8')

            chat_match = re.search(r"chat_name:\s*(.+)", content)
            draft_match = re.search(r"## Reply.*?\n(.*?)(?:---|\Z)", content, re.DOTALL)

            if not chat_match:
                logger.error("No chat_name found")
                return False

            chat_name = chat_match.group(1).strip()

            if draft_match:
                message = draft_match.group(1).strip().replace('```', '').strip()
            else:
                logger.error("No message found")
                return False

            logger.info(f"   To: {chat_name}")
            logger.info(f"   Message: {message[:80]}...")

            # Move to Done for manual sending
            done_path = self.done_folder / file_path.name
            shutil.move(str(file_path), str(done_path))

            logger.info(f"✅ Prepared: {done_path.name}")
            logger.info(f"   Send manually via WhatsApp Web")

            self.log_action(file_path.name, "prepared", str(done_path))

            # Update dashboard
            self._update_dashboard()

            return True

        except Exception as e:
            logger.error(f"Error: {e}")
            return False

    def _update_dashboard(self):
        """Update Obsidian Dashboard."""
        try:
            from dashboard_updater import update_dashboard
            update_dashboard(self.vault_path)
        except Exception as e:
            logger.debug(f"Dashboard update skipped: {e}")

    def log_action(self, filename: str, action: str, result: str):
        log_dir = self.vault_path / "Logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.json"

        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text(encoding='utf-8'))
            except:
                logs = []
        else:
            logs = []

        logs.append({
            "timestamp": datetime.now().isoformat(),
            "file": filename,
            "action": action,
            "result": result,
            "actor": "whatsapp_reply_sender",
        })

        log_file.write_text(json.dumps(logs, indent=2, ensure_ascii=False), encoding='utf-8')

    def run(self):
        self._running = True

        def signal_handler(sig, frame):
            logger.info("Shutdown requested")
            self._running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        print("\n" + "=" * 70)
        print("💬 WhatsApp Reply Sender RUNNING")
        print("=" * 70)
        print(f"   Monitoring: {self.approved_folder}")
        print(f"   Check: {self.check_interval}s")
        print(f"\n   Move files to Approved/ to prepare")
        print("\nPress Ctrl+C to stop")
        print("=" * 70 + "\n")

        try:
            while self._running:
                try:
                    approved_files = self.check_for_approved_replies()

                    if approved_files:
                        logger.info(f"Found {len(approved_files)} approved")
                        for file in approved_files:
                            self.process_approved_file(file)
                    else:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"[{timestamp}] ✓ No approved", end="\r")

                    time.sleep(self.check_interval)
                except Exception as e:
                    logger.error(f"Loop error: {e}")
                    time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        finally:
            self.stop()

    def stop(self):
        self._running = False
        logger.info("Stopped")


def main():
    vault_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./Vault")
    check_interval = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    if not vault_path.is_absolute():
        vault_path = Path(__file__).parent / vault_path

    sender = WhatsAppReplySender(vault_path, check_interval)
    sender.run()


if __name__ == "__main__":
    main()
