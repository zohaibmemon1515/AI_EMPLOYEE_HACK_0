#!/usr/bin/env python3
"""Real-time Dashboard Updater - Updates every 2 seconds"""

import json
import os
import time
import signal
import sys
from datetime import datetime
from pathlib import Path


class RealTimeDashboardUpdater:
    """Updates dashboard in real-time every 2 seconds."""
    
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.dashboard = vault_path / "Dashboard.md"
        self.needs_action = vault_path / "Needs_Action"
        self.pending_approval = vault_path / "Pending_Approval"
        self.approved = vault_path / "Approved"
        self.done = vault_path / "Done"
        self.logs = vault_path / "Logs"
        self.in_progress_gmail = vault_path / "In_Progress" / "gmail"
        self.in_progress_whatsapp = vault_path / "In_Progress" / "whatsapp"
        self._running = False
        
    def count_files(self, folder: Path, prefix: str = None) -> int:
        """Count .md files in folder."""
        if not folder.exists():
            return 0
        count = 0
        for f in folder.iterdir():
            if f.is_file() and f.suffix == ".md":
                if prefix is None or f.name.startswith(prefix):
                    count += 1
        return count
    
    def get_today_stats(self) -> dict:
        """Get today's stats from logs."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs / f"{today}.json"
        
        stats = {
            "gmail_processed": 0, "gmail_sent": 0,
            "whatsapp_processed": 0, "whatsapp_sent": 0,
        }
        
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text(encoding="utf-8"))
                for entry in logs:
                    actor = entry.get("actor", "").lower()
                    action = entry.get("action_type", "")
                    
                    if "gmail" in actor and action == "email_processed":
                        stats["gmail_processed"] += 1
                    elif "whatsapp" in actor and action == "message_processed":
                        stats["whatsapp_processed"] += 1
                    elif action == "sent":
                        if "gmail" in actor:
                            stats["gmail_sent"] += 1
                        elif "whatsapp" in actor:
                            stats["whatsapp_sent"] += 1
            except:
                pass
        
        return stats
    
    def get_rate_limits(self) -> dict:
        """Get current rate limit status."""
        gmail_remaining = 5
        whatsapp_remaining = 10
        
        # Check Gmail
        gmail_file = self.in_progress_gmail / "processed_ids.json"
        if gmail_file.exists():
            try:
                data = json.loads(gmail_file.read_text())
                gmail_remaining = max(0, 5 - data.get("count", 0))
            except:
                pass
        
        # Check WhatsApp
        whatsapp_file = self.in_progress_whatsapp / "processed_ids.json"
        if whatsapp_file.exists():
            try:
                data = json.loads(whatsapp_file.read_text())
                whatsapp_remaining = max(0, 10 - data.get("count", 0))
            except:
                pass
        
        return gmail_remaining, whatsapp_remaining
    
    def get_recent_activity(self, limit: int = 10) -> str:
        """Build recent activity table."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs / f"{today}.json"
        
        if not log_file.exists():
            return "| Time | Activity | Status |\n|------|----------|--------|\n| - | No activity | - |"
        
        try:
            logs = json.loads(log_file.read_text(encoding="utf-8"))
            recent = logs[-limit:]
            
            lines = ["| Time | Activity | Status |", "|------|----------|--------|"]
            for entry in reversed(recent):
                t = entry.get("timestamp", "")[11:19]
                action = entry.get("action_type", "").replace("_", " ").title()
                icon = "✅" if entry.get("result") == "success" else "❌"
                actor = "📧" if "gmail" in entry.get("actor", "").lower() else "💬"
                lines.append(f"| {t} | {actor} {action} | {icon} |")
            
            return "\n".join(lines) + "\n"
        except:
            return "| Time | Activity | Status |\n|------|----------|--------|\n| - | Loading... | - |"
    
    def update_dashboard(self):
        """Update dashboard with real-time stats."""
        if not self.dashboard.exists():
            return
        
        now = datetime.now()
        content = self.dashboard.read_text(encoding="utf-8")
        
        # Count all files
        pending = self.count_files(self.needs_action)
        approval = self.count_files(self.pending_approval)
        approved_count = self.count_files(self.approved)
        done_count = self.count_files(self.done)
        
        # Count by type
        email_pending = self.count_files(self.needs_action, "EMAIL_")
        whatsapp_pending = self.count_files(self.needs_action, "WHATSAPP_")
        email_drafts = self.count_files(self.pending_approval, "EMAIL_REPLY_")
        whatsapp_drafts = self.count_files(self.pending_approval, "WHATSAPP_REPLY_")
        
        # Get stats
        stats = self.get_today_stats()
        gmail_rate, whatsapp_rate = self.get_rate_limits()
        activity = self.get_recent_activity(8)
        
        # Update all values
        content = self._update_value(content, "Pending Tasks", pending, now)
        content = self._update_value(content, "Pending Approval", approval, now)
        content = self._update_value(content, "Approved", approved_count, now)
        content = self._update_value(content, "Completed Today", done_count, now)
        
        content = self._update_line(content, "Emails Pending:", f"{email_pending}")
        content = self._update_line(content, "WhatsApp Pending:", f"{whatsapp_pending}")
        content = self._update_line(content, "Email Drafts:", f"{email_drafts}")
        content = self._update_line(content, "WhatsApp Drafts:", f"{whatsapp_drafts}")
        
        content = self._update_line(content, "Gmail Processed:", f"{stats['gmail_processed']}")
        content = self._update_line(content, "Gmail Sent:", f"{stats['gmail_sent']}")
        content = self._update_line(content, "WhatsApp Processed:", f"{stats['whatsapp_processed']}")
        content = self._update_line(content, "WhatsApp Sent:", f"{stats['whatsapp_sent']}")
        
        content = self._update_line(content, "Gmail Rate Limit:", f"{gmail_rate}/5 remaining")
        content = self._update_line(content, "WhatsApp Rate Limit:", f"{whatsapp_rate}/10 remaining")
        
        content = self._update_line(content, "**Last Sync** |", now.strftime("%Y-%m-%d %H:%M:%S"))
        content = self._update_line(content, "last_check:", now.strftime("%H:%M:%S"))
        content = self._update_line(content, "last_updated:", now.strftime("%Y-%m-%d"))
        
        # Update activity table
        if "<!-- RECENT_ACTIVITY_START -->" in content:
            start = content.find("<!-- RECENT_ACTIVITY_START -->")
            end = content.find("<!-- RECENT_ACTIVITY_END -->") + len("<!-- RECENT_ACTIVITY_END -->")
            if end > start:
                content = content[:start] + f"<!-- RECENT_ACTIVITY_START -->\n{activity}<!-- RECENT_ACTIVITY_END -->" + content[end:]
        
        self.dashboard.write_text(content, encoding="utf-8")
        print(f"[{now.strftime('%H:%M:%S')}] ✓ Dashboard: {pending} pending | {approval} approval | {done_count} done", end="\r")
    
    def _update_value(self, content: str, label: str, value: int, now: datetime) -> str:
        """Update a metric value in the table."""
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if f"**{label}**" in line and "|" in line:
                parts = line.split("|")
                if len(parts) >= 2:
                    parts[1] = f" {value} "
                    parts[2] = f" {now.strftime('%H:%M:%S')} |"
                    lines[i] = "|".join(parts)
                    break
        return "\n".join(lines)
    
    def _update_line(self, content: str, marker: str, value: str) -> str:
        """Update a line containing marker."""
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if marker in line:
                lines[i] = line.split(marker)[0] + marker + " " + value
                break
        return "\n".join(lines)
    
    def run(self, interval: int = 2):
        """Run real-time dashboard updates."""
        self._running = True
        
        def signal_handler(sig, frame):
            self._running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        print("\n" + "=" * 70)
        print("📊 Dashboard Real-Time Updater")
        print("=" * 70)
        print(f"   Updating every {interval} seconds")
        print(f"   Dashboard: {self.dashboard}")
        print("\nPress Ctrl+C to stop")
        print("=" * 70 + "\n")
        
        # Initial update
        self.update_dashboard()
        
        while self._running:
            try:
                time.sleep(interval)
                self.update_dashboard()
            except Exception as e:
                print(f"\n   ⚠️  Error: {e}")
                time.sleep(interval)
        
        print("\n   ✓ Dashboard updater stopped")


def main():
    vault_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "Vault"
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    
    if not vault_path.is_absolute():
        vault_path = Path(__file__).parent / vault_path
    
    updater = RealTimeDashboardUpdater(vault_path)
    updater.run(interval)


if __name__ == "__main__":
    main()
