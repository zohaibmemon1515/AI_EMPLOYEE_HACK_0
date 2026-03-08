#!/usr/bin/env python3
r"""
🚀 AI Employee - Gold Tier - Single File Runner

Everything runs from this one file:
- Gmail Watcher (with AI drafts)
- WhatsApp AI Agent (with phone extraction)
- Dashboard Updater
- Ralph Loop (autonomous tasks)

Usage:
    python main.py              # Start everything
    python main.py --export     # Export WhatsApp contacts first
"""

import os
import sys
import io
import time
import subprocess
import signal
from pathlib import Path
from datetime import datetime

# Set console encoding to UTF-8 on Windows - MUST be first
if sys.platform == "win32":
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        # Reconfigure stdout/stderr for UTF-8
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        # Set console code page to UTF-8
        os.system("chcp 65001 >nul 2>&1")
    except Exception:
        pass  # Fallback to default encoding

# Check Python version
if sys.version_info < (3, 10):
    print("Python 3.10+ required")
    sys.exit(1)


class GoldTierSetup:
    """Gold Tier setup wizard."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.vault = base_dir / "Vault"
        self.env_file = base_dir / ".env"

    def run(self):
        print("=" * 70)
        print("AI Employee - Gold Tier Setup")
        print("=" * 70)
        print()

        # Create Gold Tier folders
        print("📁 Creating Gold Tier folders...")
        folders = [
            self.vault / "CEO_Briefings",
            self.vault / "Audits",
            self.vault / "Social_Media" / "Scheduled",
            self.vault / "Social_Media" / "Published",
            self.vault / "Social_Media" / "Reports",
            self.vault / "Social_Media" / "Templates",
            self.vault / "Invoice_Sync" / "Incoming",
            self.vault / "Invoice_Sync" / "Processed",
            self.vault / "Invoice_Sync" / "Export",
            self.vault / "In_Progress" / "task_executor",
            self.vault / "In_Progress" / "crm",
            self.vault / "Scheduled_Messages",
        ]
        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)
            print(f"   ✓ {folder.relative_to(self.base_dir)}")

        # Create .env if not exists
        if not self.env_file.exists():
            self.env_file.write_text("""# =============================================================================
# AI Employee - Gold Tier Configuration
# =============================================================================

# -----------------------------------------------------------------------------
# Gmail API Configuration (Silver Tier)
# -----------------------------------------------------------------------------
GMAIL_CREDENTIALS_PATH=./credentials/gmail/credentials.json
GMAIL_TOKEN_PATH=./credentials/gmail/token.json
GMAIL_POLL_INTERVAL=120
DEV_MODE=true
DRY_RUN=true

# -----------------------------------------------------------------------------
# WhatsApp Configuration (Silver Tier)
# -----------------------------------------------------------------------------
WHATSAPP_POLL_INTERVAL=30
WHATSAPP_BROWSER_HEADLESS=false
WHATSAPP_RATE_LIMIT_HOURLY=10

# -----------------------------------------------------------------------------
# Odoo Accounting Configuration (Gold Tier - Optional)
# -----------------------------------------------------------------------------
ODOO_BASE_URL=http://localhost:8069
ODOO_DB_NAME=odoo
ODOO_USERNAME=admin
ODOO_PASSWORD=

# -----------------------------------------------------------------------------
# Facebook Configuration (Gold Tier - Optional)
# -----------------------------------------------------------------------------
FACEBOOK_PAGE_ACCESS_TOKEN=
FACEBOOK_PAGE_ID=

# -----------------------------------------------------------------------------
# Instagram Configuration (Gold Tier - Optional)
# -----------------------------------------------------------------------------
INSTAGRAM_BUSINESS_ACCOUNT_ID=
INSTAGRAM_ACCESS_TOKEN=

# -----------------------------------------------------------------------------
# Twitter Configuration (Gold Tier - Optional)
# -----------------------------------------------------------------------------
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_TOKEN_SECRET=
TWITTER_BEARER_TOKEN=

# -----------------------------------------------------------------------------
# AI Draft Configuration (Silver Tier)
# -----------------------------------------------------------------------------
AI_DRAFT_PROVIDER=auto
GEMINI_API_KEY=
OPENAI_API_KEY=
""")
            print("\n✓ Created .env")

        print("\n" + "=" * 70)
        print("✅ Gold Tier Setup Complete!")
        print("=" * 70)
        print("\nNext: Run 'python main.py' to start full system")


class GoldTierServices:
    """Gold Tier service manager."""

    def __init__(self, base_dir: Path, vault_path: Path):
        self.base_dir = base_dir
        self.vault_path = vault_path
        self.processes = {}

    def start_ralph_loop(self):
        """Start Ralph Loop autonomous task processor."""
        script = self.base_dir / "modules" / "planning" / "ralph_loop.py"
        if script.exists():
            self.processes["ralph_loop"] = subprocess.Popen(
                [sys.executable, "-u", str(script), "--continuous", "--interval", "60"],
                cwd=str(self.base_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print(f"   ✓ Ralph Loop started (PID: {self.processes['ralph_loop'].pid})")
            return True
        return False

    def start_social_scheduler(self):
        """Start social media scheduler."""
        script = self.base_dir / "modules" / "social" / "social_scheduler.py"
        if script.exists():
            # Run once to process due posts
            subprocess.Popen(
                [sys.executable, "-u", str(script), "--process"],
                cwd=str(self.base_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print(f"   ✓ Social Scheduler triggered")
            return True
        return False

    def start_mcp_servers(self):
        """Start Gold Tier MCP servers."""
        # Accounting MCP Server
        mcp_script = self.base_dir / "mcp_servers" / "accounting_mcp_server.js"
        if mcp_script.exists():
            self.processes["accounting_mcp"] = subprocess.Popen(
                ["node", str(mcp_script), "8811"],
                cwd=str(self.base_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print(f"   ✓ Accounting MCP Server started (PID: {self.processes['accounting_mcp'].pid})")

        # Social MCP Server
        mcp_script = self.base_dir / "mcp_servers" / "social_mcp_server.js"
        if mcp_script.exists():
            self.processes["social_mcp"] = subprocess.Popen(
                ["node", str(mcp_script), "8812"],
                cwd=str(self.base_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print(f"   ✓ Social MCP Server started (PID: {self.processes['social_mcp'].pid})")

    def run_weekly_tasks(self):
        """Run weekly audit and CEO briefing."""
        try:
            # Run weekly audit
            from modules.reporting.weekly_audit import WeeklyAudit
            audit = WeeklyAudit(self.vault_path)
            result = audit.run_weekly_audit()
            print(f"   ✓ Weekly Audit: {result.status} (Score: {result.health_score}/100)")
        except Exception as e:
            print(f"   ⚠ Weekly Audit skipped: {e}")

        try:
            # Generate CEO briefing
            from modules.reporting.ceo_briefing import CEOBriefingGenerator
            generator = CEOBriefingGenerator(self.vault_path)
            briefing = generator.generate_weekly_briefing()
            generator.save_briefing(briefing)
            print(f"   ✓ CEO Briefing generated: {briefing.briefing_id}")
        except Exception as e:
            print(f"   ⚠ CEO Briefing skipped: {e}")

    def stop_all(self):
        """Stop all Gold Tier services."""
        for name, process in self.processes.items():
            print(f"   Stopping {name}...")
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"      ✓ {name} stopped")
            except:
                process.kill()
                print(f"      ✓ {name} killed")
        self.processes.clear()


class SilverTierSetup:
    """Silver Tier setup wizard."""

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

        print("\n" + "=" * 70)
        print("✅ Setup Complete!")
        print("=" * 70)


class AIEmployee:
    """Main AI Employee controller - Full Gold Tier."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.vault = base_dir / "Vault"
        self.gold_services = GoldTierServices(base_dir, self.vault)

        # Silver Tier processes
        self.gmail_watcher = None
        self.whatsapp_watcher = None
        self.whatsapp_reply_sender = None
        self.orchestrator = None
        self.dashboard_updater = None

        # State
        self.running = False
        self.gold_enabled = True

    def start(self, silver_only: bool = False, gold_only: bool = False):
        """
        Start AI Employee system.

        Args:
            silver_only: Run only Silver Tier components
            gold_only: Run only Gold Tier components
        """
        print("=" * 70)
        print("🤖 AI Employee - Gold Tier (Full System)")
        print("=" * 70)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Vault: {self.vault}")
        print("=" * 70)
        print()

        # Check setup
        self.check_setup()

        if not gold_only:
            # Start Silver Tier Components
            self._start_silver_tier()

        if not silver_only:
            # Start Gold Tier Components
            self._start_gold_tier()

        self.running = True

        print("\n" + "=" * 70)
        print("✅ AI Employee is RUNNING!")
        print("=" * 70)
        print()

        if not silver_only and not gold_only:
            print("📬 What's happening:")
            print("   Silver Tier:")
            print("   • Gmail Watcher: Checking every 60 seconds")
            print("   • WhatsApp AI Agent: Checking every 30 seconds (with AI drafts)")
            print("   • WhatsApp Reply Sender: Monitoring Approved/ (5 seconds)")
            print("   • Orchestrator: Watching Approved/ folder")
            print("   • Dashboard Updater: Updating every 2 seconds")
            print()
            print("   Gold Tier:")
            print("   • Ralph Loop: Processing tasks autonomously")
            print("   • Social Scheduler: Processing scheduled posts")
            print("   • MCP Servers: Accounting (8811), Social (8812)")
            print()

        print("Press Ctrl+C to stop")
        print("=" * 70)
        print()

        try:
            # Monitor all processes
            while self.running:
                timestamp = datetime.now().strftime("%H:%M:%S")

                if not gold_only:
                    self._monitor_silver_tier(timestamp)

                if not silver_only:
                    self._monitor_gold_tier(timestamp)

                time.sleep(10)

        except KeyboardInterrupt:
            print("\n\n🛑 Stopping...")
        finally:
            self.stop()

    def _start_silver_tier(self):
        """Start Silver Tier components."""
        # Start Gmail Watcher
        gmail_script = self.base_dir / "watchers" / "gmail_watcher.py"
        if gmail_script.exists():
            print("\n📧 Starting Gmail Watcher...")
            self.gmail_watcher = subprocess.Popen(
                [sys.executable, "-u", str(gmail_script), str(self.vault), "60"],
            )
            print(f"   ✓ Started (PID: {self.gmail_watcher.pid})")

        # Wait a moment
        time.sleep(1)

        # Start WhatsApp AI Agent PRO (Production Ready)
        whatsapp_pro_script = self.base_dir / "whatsapp_ai_agent_pro.py"
        if whatsapp_pro_script.exists():
            print("\n🤖 Starting WhatsApp AI Agent PRO...")
            print("   • Reads WhatsApp Web messages via Playwright")
            print("   • Extracts phone numbers (smart contact lookup)")
            print("   • Generates AI draft replies using Gemini API")
            print("   • Auto-sends via UltraMsg when approved")
            print("   • PRO: Fixed draft extraction, better phone parsing")
            self.whatsapp_watcher = subprocess.Popen(
                [sys.executable, "-u", str(whatsapp_pro_script), str(self.vault), "30"],
            )
            print(f"   ✓ Started (PID: {self.whatsapp_watcher.pid})")
        else:
            # Fallback to old WhatsApp AI Agent
            whatsapp_agent_script = self.base_dir / "whatsapp_ai_agent.py"
            if whatsapp_agent_script.exists():
                print("\n🤖 Starting WhatsApp AI Agent...")
                self.whatsapp_watcher = subprocess.Popen(
                    [sys.executable, "-u", str(whatsapp_agent_script), str(self.vault), "30"],
                )
                print(f"   ✓ Started (PID: {self.whatsapp_watcher.pid})")
            else:
                # Fallback to old WhatsApp Watcher
                whatsapp_script = self.base_dir / "watchers" / "whatsapp_watcher.py"
                if whatsapp_script.exists():
                    print("\n💬 Starting WhatsApp Watcher (legacy)...")
                    self.whatsapp_watcher = subprocess.Popen(
                        [sys.executable, "-u", str(whatsapp_script), str(self.vault), "30"],
                    )
                    print(f"   ✓ Started (PID: {self.whatsapp_watcher.pid})")

        # Wait a moment
        time.sleep(1)

        # Start WhatsApp Reply Sender
        reply_script = self.base_dir / "whatsapp_reply_sender.py"
        if reply_script.exists():
            print("\n📤 Starting WhatsApp Reply Sender...")
            self.whatsapp_reply_sender = subprocess.Popen(
                [sys.executable, "-u", str(reply_script), str(self.vault), "5"],
            )
            print(f"   ✓ Started (PID: {self.whatsapp_reply_sender.pid})")

        # Wait a moment
        time.sleep(1)

        # Start Orchestrator
        orchestrator_script = self.base_dir / "orchestrator.py"
        if orchestrator_script.exists():
            print("\n📬 Starting Approved Folder Monitor...")
            self.orchestrator = subprocess.Popen(
                [sys.executable, "-u", str(orchestrator_script), str(self.vault)],
            )
            print(f"   ✓ Started (PID: {self.orchestrator.pid})")

        # Wait a moment
        time.sleep(1)

        # Start Dashboard Updater
        dashboard_script = self.base_dir / "realtime_dashboard.py"
        if dashboard_script.exists():
            print("\n📊 Starting Real-Time Dashboard Updater...")
            self.dashboard_updater = subprocess.Popen(
                [sys.executable, "-u", str(dashboard_script), str(self.vault), "2"],
            )
            print(f"   ✓ Started (PID: {self.dashboard_updater.pid})")

    def _start_gold_tier(self):
        """Start Gold Tier components."""
        print("\n" + "=" * 70)
        print("🏆 Starting Gold Tier Services...")
        print("=" * 70)

        # Start Ralph Loop - run once initially to process any pending tasks
        print("\n🔄 Running Ralph Loop (initial cycle)...")
        try:
            from modules.planning.ralph_loop import RalphLoop
            loop = RalphLoop(self.vault)
            iteration = loop.run_cycle()
            print(f"   ✓ Ralph Loop cycle complete: {iteration.state}")
            print(f"   ✓ Tasks processed: {iteration.tasks_processed}")
            if iteration.errors:
                print(f"   ⚠ Errors: {iteration.errors}")
        except Exception as e:
            print(f"   ⚠ Ralph Loop initial cycle skipped: {e}")

        # Start Social Scheduler
        self.gold_services.start_social_scheduler()

        # Start MCP Servers
        self.gold_services.start_mcp_servers()

        # Run weekly tasks (audit and CEO briefing)
        print("\n📊 Running weekly tasks...")
        self.gold_services.run_weekly_tasks()

        print("\n✅ Gold Tier services started")

    def _monitor_silver_tier(self, timestamp: str):
        """Monitor Silver Tier processes."""
        # Check Gmail Watcher
        if self.gmail_watcher and self.gmail_watcher.poll() is not None:
            print(f"\n[{timestamp}] ⚠️  Gmail Watcher stopped")
            if self.gmail_watcher.returncode != 0:
                script = self.base_dir / "watchers" / "gmail_watcher.py"
                if script.exists():
                    print("   Restarting...")
                    time.sleep(3)
                    self.gmail_watcher = subprocess.Popen(
                        [sys.executable, "-u", str(script), str(self.vault), "60"],
                    )

        # Check WhatsApp Watcher
        if self.whatsapp_watcher and self.whatsapp_watcher.poll() is not None:
            print(f"\n[{timestamp}] ⚠️  WhatsApp Watcher stopped")
            if self.whatsapp_watcher.returncode != 0:
                script = self.base_dir / "watchers" / "whatsapp_watcher.py"
                if script.exists():
                    print("   Restarting...")
                    time.sleep(3)
                    self.whatsapp_watcher = subprocess.Popen(
                        [sys.executable, "-u", str(script), str(self.vault), "30"],
                    )

        # Check WhatsApp Reply Sender
        if self.whatsapp_reply_sender and self.whatsapp_reply_sender.poll() is not None:
            print(f"\n[{timestamp}] ⚠️  WhatsApp Reply Sender stopped")
            if self.whatsapp_reply_sender.returncode != 0:
                script = self.base_dir / "whatsapp_reply_sender.py"
                if script.exists():
                    print("   Restarting...")
                    time.sleep(3)
                    self.whatsapp_reply_sender = subprocess.Popen(
                        [sys.executable, "-u", str(script), str(self.vault), "5"],
                    )

        # Check Orchestrator
        if self.orchestrator and self.orchestrator.poll() is not None:
            print(f"\n[{timestamp}] ⚠️  Orchestrator stopped")
            if self.orchestrator.returncode != 0:
                script = self.base_dir / "orchestrator.py"
                if script.exists():
                    print("   Restarting...")
                    time.sleep(3)
                    self.orchestrator = subprocess.Popen(
                        [sys.executable, "-u", str(script), str(self.vault)],
                    )

        # Check Dashboard Updater
        if self.dashboard_updater and self.dashboard_updater.poll() is not None:
            print(f"\n[{timestamp}] ⚠️  Dashboard Updater stopped")
            if self.dashboard_updater.returncode != 0:
                script = self.base_dir / "realtime_dashboard.py"
                if script.exists():
                    print("   Restarting...")
                    time.sleep(3)
                    self.dashboard_updater = subprocess.Popen(
                        [sys.executable, "-u", str(script), str(self.vault), "2"],
                    )

        # Show status
        print(f"[{timestamp}] ✓ Silver Tier Running", end="\r")

    def _monitor_gold_tier(self, timestamp: str):
        """Monitor Gold Tier processes."""
        # Gold Tier runs as single cycles, not continuous processes
        # Just show status
        print(f"[{timestamp}] ✓ Gold Tier Active        ", end="\r")

    def check_setup(self):
        """Check if setup is complete."""
        # Check Gmail setup
        token = self.base_dir / "credentials" / "gmail" / "token.json"
        if token.exists():
            print("   ✓ Gmail authenticated")
        else:
            print("   ⚠️  Gmail not configured (optional)")

        # Check WhatsApp setup
        whatsapp_watcher = self.base_dir / "watchers" / "whatsapp_watcher.py"
        if whatsapp_watcher.exists():
            print("   ✓ WhatsApp Watcher found")
        else:
            print("   ⚠️  WhatsApp Watcher not found")

        # Check Gold Tier modules
        ralph_loop = self.base_dir / "modules" / "planning" / "ralph_loop.py"
        if ralph_loop.exists():
            print("   ✓ Gold Tier: Ralph Loop available")

        ceo_briefing = self.base_dir / "modules" / "reporting" / "ceo_briefing.py"
        if ceo_briefing.exists():
            print("   ✓ Gold Tier: CEO Briefing available")

        weekly_audit = self.base_dir / "modules" / "reporting" / "weekly_audit.py"
        if weekly_audit.exists():
            print("   ✓ Gold Tier: Weekly Audit available")

        if not self.vault.exists():
            print("   ⚠️  Creating Vault...")
            self.vault.mkdir(parents=True, exist_ok=True)

    def stop(self):
        """Stop all processes."""
        print("\n" + "=" * 70)
        print("🛑 Stopping AI Employee...")
        print("=" * 70)

        # Stop Silver Tier
        print("\nStopping Silver Tier...")
        processes = [
            ("Gmail Watcher", self.gmail_watcher),
            ("WhatsApp Watcher", self.whatsapp_watcher),
            ("WhatsApp Reply Sender", self.whatsapp_reply_sender),
            ("Orchestrator", self.orchestrator),
            ("Dashboard Updater", self.dashboard_updater),
        ]

        for name, process in processes:
            if process:
                print(f"   Stopping {name}...")
                try:
                    process.terminate()
                    process.wait(timeout=5)
                    print(f"      ✓ {name} stopped")
                except:
                    process.kill()
                    print(f"      ✓ {name} killed")

        # Stop Gold Tier
        print("\nStopping Gold Tier...")
        self.gold_services.stop_all()

        print("\n" + "=" * 70)
        print("👋 AI Employee Stopped")
        print("=" * 70)


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\n🛑 Interrupt received...")
    sys.exit(0)


def main():
    """Main entry point."""
    base_dir = Path(__file__).parent

    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)

    # Parse arguments
    silver_only = "--silver" in sys.argv
    gold_only = "--gold" in sys.argv
    run_setup = "--setup" in sys.argv

    if run_setup:
        print("\n🎉 Running setup for both Silver and Gold Tier...\n")
        silver_setup = SilverTierSetup(base_dir)
        silver_setup.run()
        print()
        gold_setup = GoldTierSetup(base_dir)
        gold_setup.run()
        return

    # Check if first run
    env_file = base_dir / ".env"
    if not env_file.exists():
        print("=" * 70)
        print("🎉 Welcome to AI Employee - Gold Tier!")
        print("=" * 70)
        print()
        print("First time setup needed.")
        print()
        choice = input("Run setup now? (y/n): ").strip().lower()
        if choice == 'y':
            silver_setup = SilverTierSetup(base_dir)
            silver_setup.run()
            print()
            gold_setup = GoldTierSetup(base_dir)
            gold_setup.run()
            print("\nNow starting...")
            time.sleep(2)

    # Start AI Employee
    ai = AIEmployee(base_dir)
    ai.start(silver_only=silver_only, gold_only=gold_only)


if __name__ == "__main__":
    main()
