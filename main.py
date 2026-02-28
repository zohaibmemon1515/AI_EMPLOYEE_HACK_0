#!/usr/bin/env python3
r"""
AI Employee - Main Entry Point

Starts the complete AI Employee system:
1. File System Watcher (monitors Inbox for new files)
2. Orchestrator (processes tasks with Claude Code)

Usage:
    python main.py              # Start everything
    python main.py --once       # Run orchestrator once and exit
    python main.py --watch-only # Just watcher, no orchestrator
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime


class AIEmployee:
    """Main AI Employee controller."""

    def __init__(self, vault_path: Path, check_interval: int = 30):
        """
        Initialize the AI Employee system.

        Args:
            vault_path: Path to the Obsidian vault
            check_interval: Seconds between watcher checks
        """
        self.base_dir = Path(__file__).parent
        self.vault_path = vault_path
        self.check_interval = check_interval

        self.watcher_process = None
        self._running = False

    def start_watcher(self):
        """Start the File System Watcher."""
        print("📁 Starting File System Watcher...")

        watcher_script = self.base_dir / "watchers" / "filesystem_watcher.py"

        # Start watcher as a subprocess
        self.watcher_process = subprocess.Popen(
            [
                sys.executable,
                "-u",  # Unbuffered output
                str(watcher_script),
                str(self.vault_path),
                str(self.check_interval),
            ],
        )

        print(f"   ✓ Watcher started (PID: {self.watcher_process.pid})")
        return self.watcher_process

    def run_orchestrator(self):
        """Run the Orchestrator once."""
        print("\n" + "=" * 60)
        print("🤖 Running Orchestrator...")

        orchestrator_script = self.base_dir / "orchestrator.py"

        try:
            result = subprocess.run(
                [sys.executable, str(orchestrator_script), str(self.vault_path)],
                capture_output=False,
                text=True,
            )
            print("   ✓ Orchestrator completed")
            return result.returncode
        except Exception as e:
            print(f"   ⚠️  Orchestrator error: {e}")
            return 1

    def start(self, continuous: bool = True):
        """
        Start the AI Employee system.

        Args:
            continuous: If True, run orchestrator in a loop. If False, run once.
        """
        self._running = True

        print("=" * 60)
        print("🤖 AI Employee - Bronze Tier")
        print("=" * 60)
        print(f"Vault: {self.vault_path}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print()

        # Start the watcher
        self.start_watcher()

        print()
        print("✅ AI Employee is now running!")
        print()
        print("What's happening:")
        print("  • File System Watcher is monitoring Vault/Inbox/")
        if continuous:
            print(f"  • Orchestrator runs every 60 seconds to process tasks")
        print()
        print("Drop files in Vault/Inbox/ to get started.")
        print()
        print("Press Ctrl+C to stop.\n")

        orchestrator_interval = 60  # seconds
        last_run = 0
        start_time = time.time()

        try:
            while self._running:
                current_time = time.time()

                # Run orchestrator periodically (only in continuous mode)
                if continuous and (current_time - last_run) >= orchestrator_interval:
                    self.run_orchestrator()
                    last_run = current_time

                # Check if watcher is still running
                if self.watcher_process and self.watcher_process.poll() is not None:
                    print("\n⚠️  Watcher has stopped unexpectedly")
                    if continuous:
                        print("🔄 Restarting watcher...")
                        self.start_watcher()
                    else:
                        break

                time.sleep(1)

                # Safety: restart orchestrator after first run if it's been too long
                if continuous and last_run == 0 and (current_time - start_time) >= 5:
                    self.run_orchestrator()
                    last_run = current_time

        except KeyboardInterrupt:
            print("\n\n🛑 Shutting down AI Employee...")
        finally:
            self.stop()

    def stop(self):
        """Stop all components."""
        self._running = False

        if self.watcher_process:
            print("   Stopping Watcher...")
            self.watcher_process.terminate()
            try:
                self.watcher_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.watcher_process.kill()
            print("   ✓ Watcher stopped")

        print()
        print("=" * 60)
        print("👋 AI Employee stopped")
        print(f"Stopped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AI Employee - Your autonomous digital assistant"
    )
    parser.add_argument(
        "--vault",
        type=str,
        default=None,
        help="Path to Obsidian vault (default: ./Vault)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Watcher check interval in seconds (default: 30)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run orchestrator once and exit (no continuous loop)",
    )
    parser.add_argument(
        "--watch-only",
        action="store_true",
        help="Start watchers only, no orchestrator",
    )

    args = parser.parse_args()

    # Determine vault path
    if args.vault:
        vault_path = Path(args.vault)
    else:
        vault_path = Path(__file__).parent / "Vault"

    # Validate vault exists
    if not vault_path.exists():
        print(f"❌ Vault not found: {vault_path}")
        print("   Please ensure the Vault folder exists.")
        sys.exit(1)

    # Create AI Employee instance
    ai_employee = AIEmployee(vault_path, check_interval=args.interval)

    # Handle different modes
    if args.watch_only:
        # Just start watcher, no orchestrator
        print("=" * 60)
        print("🤖 AI Employee - Watch Only Mode")
        print("=" * 60)
        ai_employee.start_watcher()
        print("\n✅ Watcher started. Press Ctrl+C to stop.\n")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping watcher...")
        finally:
            if ai_employee.watcher_process:
                ai_employee.watcher_process.terminate()

    elif args.once:
        # Run orchestrator once, then start watcher
        ai_employee.run_orchestrator()
        print("\n✅ Orchestrator completed. Starting watcher...")
        ai_employee.start_watcher()
        print("\n✅ Watcher started. Press Ctrl+C to stop.\n")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping watcher...")
        finally:
            if ai_employee.watcher_process:
                ai_employee.watcher_process.terminate()

    else:
        # Full mode - watcher + continuous orchestrator
        ai_employee.start(continuous=True)


if __name__ == "__main__":
    main()
