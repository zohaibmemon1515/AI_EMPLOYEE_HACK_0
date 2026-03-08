#!/usr/bin/env python3
r"""
Gold Tier Integration Module

This module provides Gold Tier functionality that can be optionally
loaded alongside the Silver Tier system without modifying main.py.

Usage:
    # In main.py or separately:
    from gold_tier_integration import GoldTierIntegration

    gold = GoldTierIntegration(vault_path)
    gold.start_background_services()
"""

import logging
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import dotenv

# Load environment variables
dotenv.load_dotenv()

# Windows-safe logging setup
class WindowsSafeHandler(logging.StreamHandler):
    """Logging handler that replaces emojis with ASCII on Windows."""
    EMOJI_MAP = {
        '👁️': '[O]', '📋': '[T]', '🤖': '[AI]', '✅': '[OK]', '❌': '[X]',
        '⚠️': '[!]', '📝': '[N]', '🔄': '[~]', '📊': '[D]', '📁': '[F]',
        '🔍': '[S]', '💾': '[S]', '🚀': '[G]', '📧': '[E]', '💬': '[W]',
        '📱': '[M]', '🕐': '[T]', '✨': '[*]', '🎯': '[T]', '📌': '[P]',
        '🔔': '[A]', '📈': '[G]', '📉': '[D]', '🔧': '[C]', '🛠️': '[T]',
        '🗂️': '[F]', '📅': '[D]', '⏰': '[A]', '🎉': '[!]', '👍': '[Y]',
        '👎': '[N]', '🔥': '[F]', '💰': '[M]', '💡': '[I]', '🎨': '[A]',
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

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = WindowsSafeHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)


class GoldTierIntegration:
    """
    Gold Tier Integration for AI Employee.

    Provides additional Gold Tier functionality:
    - Ralph Loop autonomous task processing
    - Social media scheduling
    - Weekly audit generation
    - CEO briefing generation
    - MCP server management

    This module is designed to run alongside Silver Tier without modification.
    """

    def __init__(self, vault_path: Path = None):
        """
        Initialize Gold Tier integration.

        Args:
            vault_path: Path to Obsidian vault
        """
        self.vault_path = vault_path or Path.cwd() / "Vault"
        self.base_dir = self.vault_path.parent

        # Gold Tier processes
        self.ralph_loop_process: Optional[subprocess.Popen] = None
        self.social_scheduler_process: Optional[subprocess.Popen] = None
        self.accounting_mcp_process: Optional[subprocess.Popen] = None
        self.social_mcp_process: Optional[subprocess.Popen] = None

        # Service state
        self.services_running = False
        self.last_weekly_audit: Optional[datetime] = None
        self.last_ceo_briefing: Optional[datetime] = None

        logger.info(f"GoldTierIntegration initialized at {self.vault_path}")

    def start_background_services(self, run_ralph_loop: bool = True, run_social_scheduler: bool = True):
        """
        Start Gold Tier background services.

        Args:
            run_ralph_loop: Whether to run Ralph Loop
            run_social_scheduler: Whether to run social scheduler
        """
        logger.info("Starting Gold Tier background services...")

        # Start Ralph Loop for autonomous task processing
        if run_ralph_loop:
            self._start_ralph_loop()

        # Start social scheduler for automated posting
        if run_social_scheduler:
            self._start_social_scheduler()

        self.services_running = True
        logger.info("Gold Tier background services started")

    def _start_ralph_loop(self):
        """Start Ralph Loop process."""
        try:
            ralph_script = self.base_dir / "modules" / "planning" / "ralph_loop.py"

            if ralph_script.exists():
                self.ralph_loop_process = subprocess.Popen(
                    [sys.executable, "-u", str(ralph_script), "--continuous", "--interval", "60"],
                    cwd=str(self.base_dir)
                )
                logger.info(f"Ralph Loop started (PID: {self.ralph_loop_process.pid})")
            else:
                logger.warning(f"Ralph Loop script not found: {ralph_script}")

        except Exception as e:
            logger.error(f"Failed to start Ralph Loop: {e}")

    def _start_social_scheduler(self):
        """Start social scheduler process."""
        try:
            scheduler_script = self.base_dir / "modules" / "social" / "social_scheduler.py"

            if scheduler_script.exists():
                self.social_scheduler_process = subprocess.Popen(
                    [sys.executable, "-u", str(scheduler_script), "--process"],
                    cwd=str(self.base_dir)
                )
                logger.info(f"Social Scheduler started (PID: {self.social_scheduler_process.pid})")
            else:
                logger.warning(f"Social Scheduler script not found: {scheduler_script}")

        except Exception as e:
            logger.error(f"Failed to start Social Scheduler: {e}")

    def start_mcp_servers(self):
        """Start Gold Tier MCP servers."""
        logger.info("Starting Gold Tier MCP servers...")

        # Start Accounting MCP Server
        self._start_accounting_mcp()

        # Start Social MCP Server
        self._start_social_mcp()

        logger.info("Gold Tier MCP servers started")

    def _start_accounting_mcp(self):
        """Start Accounting MCP Server."""
        try:
            mcp_script = self.base_dir / "mcp_servers" / "accounting_mcp_server.js"

            if mcp_script.exists():
                self.accounting_mcp_process = subprocess.Popen(
                    ["node", str(mcp_script), "8811"],
                    cwd=str(self.base_dir)
                )
                logger.info(f"Accounting MCP Server started (PID: {self.accounting_mcp_process.pid})")
            else:
                logger.warning(f"Accounting MCP script not found: {mcp_script}")

        except Exception as e:
            logger.error(f"Failed to start Accounting MCP: {e}")

    def _start_social_mcp(self):
        """Start Social MCP Server."""
        try:
            mcp_script = self.base_dir / "mcp_servers" / "social_mcp_server.js"

            if mcp_script.exists():
                self.social_mcp_process = subprocess.Popen(
                    ["node", str(mcp_script), "8812"],
                    cwd=str(self.base_dir)
                )
                logger.info(f"Social MCP Server started (PID: {self.social_mcp_process.pid})")
            else:
                logger.warning(f"Social MCP script not found: {mcp_script}")

        except Exception as e:
            logger.error(f"Failed to start Social MCP: {e}")

    def run_weekly_tasks(self):
        """
        Run weekly Gold Tier tasks.

        Should be called periodically (e.g., every Monday at 9 AM).
        """
        now = datetime.now()

        # Check if we should run weekly audit
        should_run_audit = False
        if self.last_weekly_audit is None:
            should_run_audit = True
        elif now - self.last_weekly_audit >= timedelta(days=7):
            should_run_audit = True

        # Check if we should run CEO briefing
        should_run_briefing = False
        if self.last_ceo_briefing is None:
            should_run_briefing = True
        elif now - self.last_ceo_briefing >= timedelta(days=7):
            should_run_briefing = True

        if should_run_audit:
            self._run_weekly_audit()
            self.last_weekly_audit = now

        if should_run_briefing:
            self._generate_ceo_briefing()
            self.last_ceo_briefing = now

    def _run_weekly_audit(self):
        """Run weekly business audit."""
        try:
            logger.info("Running weekly business audit...")

            from modules.reporting.weekly_audit import WeeklyAudit

            audit = WeeklyAudit(self.vault_path)
            result = audit.run_weekly_audit()

            logger.info(f"Weekly audit complete: {result.status} (score: {result.health_score})")

        except Exception as e:
            logger.error(f"Failed to run weekly audit: {e}")

    def _generate_ceo_briefing(self):
        """Generate CEO weekly briefing."""
        try:
            logger.info("Generating CEO briefing...")

            from modules.reporting.ceo_briefing import CEOBriefingGenerator

            generator = CEOBriefingGenerator(self.vault_path)
            briefing = generator.generate_weekly_briefing()
            generator.save_briefing(briefing)

            logger.info(f"CEO briefing generated: {briefing.briefing_id}")

        except Exception as e:
            logger.error(f"Failed to generate CEO briefing: {e}")

    def process_social_posts(self):
        """Process scheduled social media posts."""
        try:
            logger.info("Processing scheduled social posts...")

            from modules.social.social_scheduler import SocialScheduler

            scheduler = SocialScheduler(self.vault_path)
            result = scheduler.process_queue()

            logger.info(f"Social post processing: {result['published']} published, {result['failed']} failed")

        except Exception as e:
            logger.error(f"Failed to process social posts: {e}")

    def monitor_services(self):
        """
        Monitor and restart failed services.

        Should be called periodically in a main loop.
        """
        if not self.services_running:
            return

        # Check Ralph Loop
        if self.ralph_loop_process:
            if self.ralph_loop_process.poll() is not None:
                logger.warning("Ralph Loop process stopped, restarting...")
                time.sleep(3)
                self._start_ralph_loop()

        # Check Social Scheduler
        if self.social_scheduler_process:
            if self.social_scheduler_process.poll() is not None:
                logger.warning("Social Scheduler process stopped, restarting...")
                time.sleep(3)
                self._start_social_scheduler()

    def stop_services(self):
        """Stop all Gold Tier services."""
        logger.info("Stopping Gold Tier services...")

        processes = [
            ("Ralph Loop", self.ralph_loop_process),
            ("Social Scheduler", self.social_scheduler_process),
            ("Accounting MCP", self.accounting_mcp_process),
            ("Social MCP", self.social_mcp_process),
        ]

        for name, process in processes:
            if process:
                logger.info(f"Stopping {name}...")
                try:
                    process.terminate()
                    process.wait(timeout=5)
                    logger.info(f"  {name} stopped")
                except:
                    process.kill()
                    logger.info(f"  {name} killed")

        self.services_running = False
        logger.info("Gold Tier services stopped")

    def get_status(self) -> dict:
        """
        Get Gold Tier service status.

        Returns:
            Status dictionary
        """
        return {
            "services_running": self.services_running,
            "ralph_loop": "running" if self.ralph_loop_process and self.ralph_loop_process.poll() is None else "stopped",
            "social_scheduler": "running" if self.social_scheduler_process and self.social_scheduler_process.poll() is None else "stopped",
            "accounting_mcp": "running" if self.accounting_mcp_process and self.accounting_mcp_process.poll() is None else "stopped",
            "social_mcp": "running" if self.social_mcp_process and self.social_mcp_process.poll() is None else "stopped",
            "last_weekly_audit": self.last_weekly_audit.isoformat() if self.last_weekly_audit else None,
            "last_ceo_briefing": self.last_ceo_briefing.isoformat() if self.last_ceo_briefing else None
        }


# =============================================================================
# Factory Function
# =============================================================================

def create_gold_tier_integration(vault_path: Path = None) -> GoldTierIntegration:
    """
    Create Gold Tier integration.

    Args:
        vault_path: Path to vault

    Returns:
        GoldTierIntegration instance
    """
    return GoldTierIntegration(vault_path)


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Command-line interface for Gold Tier integration."""
    import argparse

    parser = argparse.ArgumentParser(description="Gold Tier Integration")
    parser.add_argument("--vault", type=str, help="Vault path")
    parser.add_argument("--start", action="store_true", help="Start services")
    parser.add_argument("--stop", action="store_true", help="Stop services")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--weekly", action="store_true", help="Run weekly tasks")
    parser.add_argument("--social", action="store_true", help="Process social posts")

    args = parser.parse_args()

    print("=" * 70)
    print("Gold Tier Integration")
    print("=" * 70)

    try:
        vault_path = Path(args.vault) if args.vault else Path.cwd() / "Vault"
        gold = GoldTierIntegration(vault_path)

        if args.start:
            print("\n🚀 Starting Gold Tier services...")
            gold.start_background_services()
            gold.start_mcp_servers()
            print("\nServices started. Press Ctrl+C to stop.")

            try:
                while True:
                    gold.monitor_services()
                    time.sleep(10)
            except KeyboardInterrupt:
                print("\n\nStopping services...")
                gold.stop_services()

        elif args.stop:
            print("\n🛑 Stopping Gold Tier services...")
            gold.stop_services()

        elif args.status:
            status = gold.get_status()
            print(f"\n📊 Gold Tier Status:")
            print(f"   Services Running: {status['services_running']}")
            print(f"   Ralph Loop: {status['ralph_loop']}")
            print(f"   Social Scheduler: {status['social_scheduler']}")
            print(f"   Accounting MCP: {status['accounting_mcp']}")
            print(f"   Social MCP: {status['social_mcp']}")
            print(f"   Last Weekly Audit: {status['last_weekly_audit'] or 'Never'}")
            print(f"   Last CEO Briefing: {status['last_ceo_briefing'] or 'Never'}")

        elif args.weekly:
            print("\n📊 Running weekly tasks...")
            gold.run_weekly_tasks()

        elif args.social:
            print("\n📱 Processing social posts...")
            gold.process_social_posts()

        else:
            print("\nUsage: python gold_tier_integration.py --start|--stop|--status|--weekly|--social")

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
