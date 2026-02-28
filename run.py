#!/usr/bin/env python3
"""
Run Script - Start all watchers and the orchestrator.

Usage:
    python run.py [--watchers] [--orchestrator] [--dry-run]
    
Examples:
    python run.py --watchers          # Start watchers only
    python run.py --orchestrator      # Run orchestrator once
    python run.py --watchers --orchestrator  # Start both
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime


def get_vault_path() -> Path:
    """Get the vault path (parent of this script's directory)."""
    return Path(__file__).parent / "Vault"


def start_watchers():
    """Start all watcher scripts."""
    vault_path = get_vault_path()
    watchers_dir = Path(__file__).parent / "watchers"

    print("🚀 Starting AI Employee Watchers...")
    print(f"   Vault: {vault_path}")
    print()

    processes = []

    # Start File System Watcher
    print("📁 Starting File System Watcher...")
    fs_watcher = subprocess.Popen(
        [sys.executable, str(watchers_dir / "filesystem_watcher.py"), str(vault_path), "30"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    processes.append(("File System Watcher", fs_watcher))
    print(f"   ✓ File System Watcher started (PID: {fs_watcher.pid})")

    print()
    print("✅ All watchers started!")
    print()
    print("Watchers are now monitoring:")
    print("  - Inbox folder for new files")
    print()
    print("Press Ctrl+C to stop all watchers.")
    print()

    try:
        # Keep running until interrupted
        while True:
            time.sleep(1)

            # Check if processes are still running
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"⚠️  {name} has stopped")

    except KeyboardInterrupt:
        print("\n\n🛑 Stopping watchers...")
        for name, proc in processes:
            proc.terminate()
            print(f"   ✓ {name} stopped")


def run_orchestrator(dry_run: bool = False):
    """Run the orchestrator once."""
    vault_path = get_vault_path()

    print("🤖 Running AI Employee Orchestrator...")
    print(f"   Vault: {vault_path}")
    print()

    cmd = [sys.executable, "orchestrator.py", str(vault_path)]
    if dry_run:
        cmd.append("--dry-run")

    subprocess.run(cmd)


def main():
    parser = argparse.ArgumentParser(description="AI Employee Run Script")
    parser.add_argument(
        "--watchers",
        action="store_true",
        help="Start watcher scripts",
    )
    parser.add_argument(
        "--orchestrator",
        action="store_true",
        help="Run orchestrator once",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run (no actual Claude execution)",
    )

    args = parser.parse_args()

    # Default to both if nothing specified
    if not args.watchers and not args.orchestrator:
        print("No action specified. Use --watchers or --orchestrator")
        print()
        print("Usage:")
        print("  python run.py --watchers         # Start watchers")
        print("  python run.py --orchestrator     # Run orchestrator")
        print("  python run.py --watchers --orchestrator  # Both")
        return

    if args.watchers:
        start_watchers()

    if args.orchestrator:
        run_orchestrator(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
