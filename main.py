#!/usr/bin/env python3
r"""
AI Employee - Silver Tier - Main Entry Point

Runs both Gmail Watcher and Approved Folder Monitor with real-time display.
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

# Check Python version
if sys.version_info < (3, 10):
    print("❌ Python 3.10+ required")
    sys.exit(1)


class SilverTierSetup:
    """Setup wizard."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.vault = base_dir / "Vault"
        self.creds_dir = base_dir / "credentials" / "gmail"
        self.whatsapp_session_dir = base_dir / "sessions" / "whatsapp"
        self.env_file = base_dir / ".env"

    def run(self):
        print("=" * 70)
        print("AI Employee - Silver Tier Setup")
        print("=" * 70)
        print()

        # Create folders
        print("📁 Creating folders...")
        folders = [
            self.vault / "Needs_Action",
            self.vault / "Plans",
            self.vault / "Pending_Approval",
            self.vault / "Approved",
            self.vault / "Rejected",
            self.vault / "Done",
            self.vault / "Logs",
            self.vault / "In_Progress" / "gmail",
            self.vault / "In_Progress" / "whatsapp",
            self.creds_dir,
            self.whatsapp_session_dir,
        ]
        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)
            print(f"   ✓ {folder.relative_to(self.base_dir)}")

        # Create .env
        if not self.env_file.exists():
            self.env_file.write_text("""GMAIL_CREDENTIALS_PATH=./credentials/gmail/credentials.json
GMAIL_TOKEN_PATH=./credentials/gmail/token.json
GMAIL_POLL_INTERVAL=120
WHATSAPP_POLL_INTERVAL=30
WHATSAPP_BROWSER_HEADLESS=false
WHATSAPP_RATE_LIMIT_HOURLY=10
DEV_MODE=true
DRY_RUN=true
RATE_LIMIT_HOURLY=5
""")
            print("\n✓ Created .env")

        print("\n" + "=" * 70)
        print("✅ Setup Complete!")
        print("=" * 70)
        print("\nNext: Run 'python main.py'")


class AIEmployee:
    """Main AI Employee controller."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.vault = base_dir / "Vault"
        self.gmail_watcher = None
        self.whatsapp_watcher = None
        self.whatsapp_reply_sender = None
        self.orchestrator = None
        self.dashboard_updater = None
        self.running = False

    def start(self):
        print("=" * 70)
        print("🤖 AI Employee - Silver Tier (Gmail + WhatsApp)")
        print("=" * 70)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Vault: {self.vault}")
        print("=" * 70)
        print()

        # Check setup
        self.check_setup()

        # Start Gmail Watcher
        print("\n📧 Starting Gmail Watcher...")
        self.gmail_watcher = subprocess.Popen(
            [sys.executable, "-u", str(self.base_dir / "watchers" / "gmail_watcher.py"),
             str(self.vault), "60"],  # Check every 60 seconds
        )
        print(f"   ✓ Started (PID: {self.gmail_watcher.pid})")

        # Wait a moment
        time.sleep(2)

        # Start WhatsApp Watcher
        print("\n💬 Starting WhatsApp Watcher...")
        self.whatsapp_watcher = subprocess.Popen(
            [sys.executable, "-u", str(self.base_dir / "watchers" / "whatsapp_watcher.py"),
             str(self.vault), "30"],  # Check every 30 seconds
        )
        print(f"   ✓ Started (PID: {self.whatsapp_watcher.pid})")

        # Wait a moment
        time.sleep(2)

        # Start WhatsApp Reply Sender
        print("\n📤 Starting WhatsApp Reply Sender...")
        self.whatsapp_reply_sender = subprocess.Popen(
            [sys.executable, "-u", str(self.base_dir / "whatsapp_reply_sender.py"),
             str(self.vault), "5"],  # Check every 5 seconds
        )
        print(f"   ✓ Started (PID: {self.whatsapp_reply_sender.pid})")

        # Wait a moment
        time.sleep(2)

        # Start Orchestrator (Approved folder monitor)
        print("\n📬 Starting Approved Folder Monitor...")
        self.orchestrator = subprocess.Popen(
            [sys.executable, "-u", str(self.base_dir / "orchestrator.py"), str(self.vault)],
        )
        print(f"   ✓ Started (PID: {self.orchestrator.pid})")

        # Wait a moment
        time.sleep(2)

        # Start Real-Time Dashboard Updater
        print("\n📊 Starting Real-Time Dashboard Updater...")
        self.dashboard_updater = subprocess.Popen(
            [sys.executable, "-u", str(self.base_dir / "realtime_dashboard.py"),
             str(self.vault), "2"],  # Update every 2 seconds
        )
        print(f"   ✓ Started (PID: {self.dashboard_updater.pid})")

        print("\n" + "=" * 70)
        print("✅ AI Employee is RUNNING!")
        print("=" * 70)
        print()
        print("📬 What's happening:")
        print("   • Gmail Watcher: Checking every 60 seconds")
        print("   • WhatsApp Watcher: Checking every 30 seconds (Playwright)")
        print("   • WhatsApp Reply Sender: Monitoring Approved/ (5 seconds)")
        print("   • Orchestrator: Watching Approved/ folder (every 5 seconds)")
        print("   • Dashboard Updater: Updating every 2 seconds ⚡")
        print()
        print("📂 Email Flow:")
        print("   1. New emails → Needs_Action/")
        print("   2. Plans → Plans/")
        print("   3. Draft replies → Pending_Approval/")
        print("   4. Move to Approved/ → AUTO-SEND! ⚡")
        print()
        print("💬 WhatsApp Flow:")
        print("   1. WhatsApp Web → Browser monitors messages")
        print("   2. New messages → Needs_Action/WHATSAPP_*.md")
        print("   3. Plans → Plans/")
        print("   4. Draft replies → Pending_Approval/WHATSAPP_REPLY_*.md")
        print("   5. Move to Approved/ → AUTO-SEND via WhatsApp Web! ⚡")
        print()
        print("📊 Monitoring:")
        print("   • Logs: Vault/Logs/YYYY-MM-DD.json")
        print("   • Gmail Processed: Vault/In_Progress/gmail/processed_ids.json")
        print("   • WhatsApp Processed: Vault/In_Progress/whatsapp/processed_ids.json")
        print()
        print("Press Ctrl+C to stop")
        print("=" * 70)
        print()

        self.running = True

        try:
            # Monitor all processes
            while self.running:
                timestamp = datetime.now().strftime("%H:%M:%S")

                # Check Gmail Watcher
                if self.gmail_watcher.poll() is not None:
                    print(f"\n[{timestamp}] ⚠️  Gmail Watcher stopped")
                    if self.gmail_watcher.returncode != 0:
                        print("   Restarting...")
                        time.sleep(3)
                        self.gmail_watcher = subprocess.Popen(
                            [sys.executable, "-u", str(self.base_dir / "watchers" / "gmail_watcher.py"),
                             str(self.vault), "60"],
                        )

                # Check WhatsApp Watcher
                if self.whatsapp_watcher.poll() is not None:
                    print(f"\n[{timestamp}] ⚠️  WhatsApp Watcher stopped")
                    if self.whatsapp_watcher.returncode != 0:
                        print("   Restarting...")
                        time.sleep(3)
                        self.whatsapp_watcher = subprocess.Popen(
                            [sys.executable, "-u", str(self.base_dir / "watchers" / "whatsapp_watcher.py"),
                             str(self.vault), "30"],
                        )

                # Check WhatsApp Reply Sender
                if self.whatsapp_reply_sender.poll() is not None:
                    print(f"\n[{timestamp}] ⚠️  WhatsApp Reply Sender stopped")
                    if self.whatsapp_reply_sender.returncode != 0:
                        print("   Restarting...")
                        time.sleep(3)
                        self.whatsapp_reply_sender = subprocess.Popen(
                            [sys.executable, "-u", str(self.base_dir / "whatsapp_reply_sender.py"),
                             str(self.vault), "5"],
                        )

                # Check Orchestrator
                if self.orchestrator.poll() is not None:
                    print(f"\n[{timestamp}] ⚠️  Orchestrator stopped")
                    if self.orchestrator.returncode != 0:
                        print("   Restarting...")
                        time.sleep(3)
                        self.orchestrator = subprocess.Popen(
                            [sys.executable, "-u", str(self.base_dir / "orchestrator.py"), str(self.vault)],
                        )

                # Check Dashboard Updater
                if self.dashboard_updater.poll() is not None:
                    print(f"\n[{timestamp}] ⚠️  Dashboard Updater stopped")
                    if self.dashboard_updater.returncode != 0:
                        print("   Restarting...")
                        time.sleep(3)
                        self.dashboard_updater = subprocess.Popen(
                            [sys.executable, "-u", str(self.base_dir / "realtime_dashboard.py"),
                             str(self.vault), "2"],
                        )

                # Show status
                print(f"[{timestamp}] ✓ Running | Dashboard: 2s | Gmail: 60s | WhatsApp: 30s | Reply: 5s | Approved: 5s", end="\r")

                time.sleep(10)

        except KeyboardInterrupt:
            print("\n\n🛑 Stopping...")
        finally:
            self.stop()

    def check_setup(self):
        """Check if setup is complete."""
        creds = self.base_dir / "credentials" / "gmail" / "credentials.json"
        token = self.base_dir / "credentials" / "gmail" / "token.json"

        if token.exists():
            print("   ✓ Gmail authenticated")
        elif creds.exists():
            print("   ✓ credentials.json found")
            print("      🌐 Browser will open for authentication")
        else:
            print("   ⚠️  No credentials")
            print("      📋 Add credentials.json to enable Gmail")

        # Check WhatsApp setup
        whatsapp_watcher = self.base_dir / "watchers" / "whatsapp_watcher.py"
        whatsapp_sender = self.base_dir / "whatsapp_reply_sender.py"

        if whatsapp_watcher.exists() and whatsapp_sender.exists():
            print("   ✓ WhatsApp Watcher found")
            print("   ✓ WhatsApp Reply Sender found")
            print("      🌐 Real WhatsApp Web (Playwright)")
            print("      Browser will open for QR scan on first run")
            print("      Draft replies auto-generated (like Gmail)")
        else:
            print("   ⚠️  WhatsApp components not found")

        if not self.vault.exists():
            print("   ⚠️  Creating Vault...")
            self.vault.mkdir(parents=True, exist_ok=True)

    def stop(self):
        """Stop all processes."""
        if self.gmail_watcher:
            print("   Stopping Gmail Watcher...")
            self.gmail_watcher.terminate()
            try:
                self.gmail_watcher.wait(timeout=5)
            except:
                self.gmail_watcher.kill()
            print("   ✓ Stopped")

        if self.whatsapp_watcher:
            print("   Stopping WhatsApp Watcher...")
            self.whatsapp_watcher.terminate()
            try:
                self.whatsapp_watcher.wait(timeout=5)
            except:
                self.whatsapp_watcher.kill()
            print("   ✓ Stopped")

        if self.whatsapp_reply_sender:
            print("   Stopping WhatsApp Reply Sender...")
            self.whatsapp_reply_sender.terminate()
            try:
                self.whatsapp_reply_sender.wait(timeout=5)
            except:
                self.whatsapp_reply_sender.kill()
            print("   ✓ Stopped")

        if self.orchestrator:
            print("   Stopping Orchestrator...")
            self.orchestrator.terminate()
            try:
                self.orchestrator.wait(timeout=5)
            except:
                self.orchestrator.kill()
            print("   ✓ Stopped")

        if self.dashboard_updater:
            print("   Stopping Dashboard Updater...")
            self.dashboard_updater.terminate()
            try:
                self.dashboard_updater.wait(timeout=5)
            except:
                self.dashboard_updater.kill()
            print("   ✓ Stopped")

        print("\n" + "=" * 70)
        print("👋 Stopped")
        print("=" * 70)


def main():
    """Main entry point."""
    base_dir = Path(__file__).parent

    if len(sys.argv) > 1:
        if sys.argv[1] == "--setup":
            setup = SilverTierSetup(base_dir)
            setup.run()
            return

    # Check if first run
    creds_file = base_dir / "credentials" / "gmail" / "credentials.json"
    token_file = base_dir / "credentials" / "gmail" / "token.json"
    env_file = base_dir / ".env"

    if not env_file.exists() or (not creds_file.exists() and not token_file.exists()):
        print("=" * 70)
        print("🎉 Welcome to AI Employee - Silver Tier!")
        print("=" * 70)
        print()
        print("First time setup needed.")
        print()
        print("Options:")
        print("  1. Run setup: python main.py --setup")
        print("  2. Start directly: python main.py")
        print()

        choice = input("Run setup now? (y/n): ").strip().lower()
        if choice == 'y':
            setup = SilverTierSetup(base_dir)
            setup.run()
            print("\nNow starting...")
            time.sleep(2)

    # Start
    ai = AIEmployee(base_dir)
    ai.start()


if __name__ == "__main__":
    main()
