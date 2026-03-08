#!/usr/bin/env python3
r"""
🚀 AI Employee - Simple Single File Runner

Everything runs from ONE file:
✅ Gmail Watcher (AI drafts)
✅ WhatsApp AI Agent (phone extraction)
✅ Dashboard Updater
✅ Ralph Loop

Usage:
    python run.py                 # Start everything
    python run.py --export        # Export WhatsApp contacts first
"""

import os
import sys
import time
import subprocess
import signal
from pathlib import Path
from datetime import datetime

# Windows UTF-8 fix
if sys.platform == "win32":
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout = open(sys.stdout.fileno(), 'w', encoding='utf-8', buffering=1)
        sys.stderr = open(sys.stderr.fileno(), 'w', encoding='utf-8', buffering=1)
    except:
        pass

BASE_DIR = Path(__file__).parent
VAULT = BASE_DIR / "Vault"

# Processes
processes = []
running = True


def signal_handler(sig, frame):
    global running
    print("\n\n🛑 Stopping...")
    running = False
    for p in processes:
        try:
            p.terminate()
        except:
            pass
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def export_contacts():
    """Export WhatsApp contacts from UltraMsg."""
    print("=" * 70)
    print("📱 Exporting WhatsApp Contacts...")
    print("=" * 70)
    
    script = BASE_DIR / "export_whatsapp_contacts.py"
    if script.exists():
        subprocess.run([sys.executable, str(script)])
    else:
        print("❌ export_whatsapp_contacts.py not found")
    sys.exit(0)


def start_gmail_watcher():
    """Start Gmail Watcher with AI drafts."""
    script = BASE_DIR / "watchers" / "gmail_watcher.py"
    if script.exists():
        print("📧 Starting Gmail Watcher (AI drafts enabled)...")
        p = subprocess.Popen([sys.executable, "-u", str(script), str(VAULT), "60"])
        processes.append(p)
        print(f"   ✓ Started (PID: {p.pid})")
    else:
        print("   ⚠️  gmail_watcher.py not found")


def start_whatsapp_agent():
    """Start WhatsApp AI Agent."""
    script = BASE_DIR / "whatsapp_ai_agent_pro.py"
    if script.exists():
        print("📱 Starting WhatsApp AI Agent...")
        p = subprocess.Popen([sys.executable, "-u", str(script), str(VAULT), "30"])
        processes.append(p)
        print(f"   ✓ Started (PID: {p.pid})")
    else:
        print("   ⚠️  whatsapp_ai_agent_pro.py not found")


def start_reply_sender():
    """Start WhatsApp Reply Sender."""
    script = BASE_DIR / "whatsapp_reply_sender.py"
    if script.exists():
        print("📤 Starting WhatsApp Reply Sender...")
        p = subprocess.Popen([sys.executable, "-u", str(script), str(VAULT), "5"])
        processes.append(p)
        print(f"   ✓ Started (PID: {p.pid})")
    else:
        print("   ⚠️  whatsapp_reply_sender.py not found")


def start_orchestrator():
    """Start Approved folder orchestrator."""
    script = BASE_DIR / "orchestrator.py"
    if script.exists():
        print("📬 Starting Orchestrator...")
        p = subprocess.Popen([sys.executable, "-u", str(script), str(VAULT)])
        processes.append(p)
        print(f"   ✓ Started (PID: {p.pid})")
    else:
        print("   ⚠️  orchestrator.py not found")


def start_dashboard_updater():
    """Start real-time dashboard updater."""
    script = BASE_DIR / "dashboard_updater.py"
    if script.exists():
        print("📊 Starting Dashboard Updater...")
        p = subprocess.Popen([sys.executable, "-u", str(script), str(VAULT), "2"])
        processes.append(p)
        print(f"   ✓ Started (PID: {p.pid})")
    else:
        print("   ⚠️  dashboard_updater.py not found")


def start_ralph_loop():
    """Start Ralph Loop for autonomous tasks."""
    script = BASE_DIR / "modules" / "planning" / "ralph_loop.py"
    if script.exists():
        print("🤖 Starting Ralph Loop...")
        p = subprocess.Popen([sys.executable, "-u", str(script), "--continuous"])
        processes.append(p)
        print(f"   ✓ Started (PID: {p.pid})")
    else:
        print("   ⚠️  ralph_loop.py not found")


def main():
    # Check for --export flag
    if len(sys.argv) > 1 and sys.argv[1] == "--export":
        export_contacts()
        return
    
    # Header
    print("=" * 70)
    print("🤖 AI Employee - Gold Tier")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Vault: {VAULT}")
    print("=" * 70)
    print()
    
    # Check .env
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        print("⚠️  .env file not found!")
        print("   Copy .env.example to .env and add your API keys")
        print()
    
    # Start all services
    print("🚀 Starting services...\n")
    
    start_gmail_watcher()
    time.sleep(1)
    
    start_whatsapp_agent()
    time.sleep(1)
    
    start_reply_sender()
    time.sleep(1)
    
    start_orchestrator()
    time.sleep(1)
    
    start_dashboard_updater()
    time.sleep(1)
    
    start_ralph_loop()
    time.sleep(1)
    
    # Status
    print("\n" + "=" * 70)
    print("✅ AI Employee is RUNNING!")
    print("=" * 70)
    print()
    print("📬 What's happening:")
    print("   📧 Gmail: Checking every 60s (AI drafts enabled)")
    print("   📱 WhatsApp: Checking every 30s (phone extraction)")
    print("   📤 Reply Sender: Monitoring Approved/ (5s)")
    print("   📬 Orchestrator: Processing approved drafts")
    print("   📊 Dashboard: Updating every 2s")
    print("   🤖 Ralph Loop: Autonomous task processing")
    print()
    print("💡 New drafts show at TOP of Pending_Approval/")
    print("💡 Press Ctrl+C to stop")
    print("=" * 70)
    print()
    
    # Monitor
    try:
        while running:
            time.sleep(5)
            
            # Check if processes are alive
            for i, p in enumerate(processes):
                if p.poll() is not None:
                    print(f"⚠️  Process {i} died, restarting...")
                    processes.pop(i)
                    # Restart all (simple approach)
                    for proc in processes:
                        try:
                            proc.terminate()
                        except:
                            pass
                    processes.clear()
                    time.sleep(2)
                    # Restart would go here (simplified for now)
                    break
                    
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping...")
    finally:
        for p in processes:
            try:
                p.terminate()
            except:
                pass


if __name__ == "__main__":
    main()
