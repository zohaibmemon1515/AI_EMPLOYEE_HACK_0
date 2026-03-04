#!/usr/bin/env python3
r"""
Dashboard Updater - Updates Obsidian Dashboard with real-time stats
"""

import json
import os
from datetime import datetime
from pathlib import Path


class DashboardUpdater:
    """Updates Obsidian Dashboard.md with current stats."""

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.dashboard = vault_path / "Dashboard.md"
        self.needs_action = vault_path / "Needs_Action"
        self.pending_approval = vault_path / "Pending_Approval"
        self.approved = vault_path / "Approved"
        self.done = vault_path / "Done"
        self.logs = vault_path / "Logs"

    def count_files(self, folder: Path, extension: str = ".md") -> int:
        """Count files in folder."""
        if not folder.exists():
            return 0
        return len([f for f in folder.iterdir() if f.is_file() and f.suffix == extension])

    def get_today_stats(self) -> dict:
        """Get today's processing stats."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs / f"{today}.json"

        stats = {
            "emails_processed": 0,
            "emails_sent": 0,
            "emails_failed": 0,
        }

        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text())
                for entry in logs:
                    if entry.get("action_type") == "email_processed":
                        stats["emails_processed"] += 1
                    elif entry.get("action_type") == "email_sent":
                        if entry.get("result") == "success":
                            stats["emails_sent"] += 1
                        else:
                            stats["emails_failed"] += 1
            except:
                pass

        return stats

    def update_dashboard(self):
        """Update Dashboard.md with current stats."""
        if not self.dashboard.exists():
            # Create basic dashboard
            self.create_dashboard()
            return

        content = self.dashboard.read_text(encoding="utf-8")
        now = datetime.now()

        # Count files
        pending_count = self.count_files(self.needs_action)
        approval_count = self.count_files(self.pending_approval)
        approved_count = self.count_files(self.approved)
        done_count = self.count_files(self.done)

        # Get today's stats
        today_stats = self.get_today_stats()

        # Update timestamp
        content = self._replace_line(
            content,
            r"last_updated:\s*\d{4}-\d{2}-\d{2}",
            f"last_updated: {now.strftime('%Y-%m-%d')}"
        )
        content = self._replace_line(
            content,
            r"last_check:\s*\d{2}:\d{2}:\d{2}",
            f"last_check: {now.strftime('%H:%M:%S')}"
        )

        # Update counts
        content = self._replace_line(
            content,
            r"\*\*Pending Tasks\*\*\s*\|\s*\d+",
            f"**Pending Tasks** | {pending_count}"
        )
        content = self._replace_line(
            content,
            r"\*\*Pending Approval\*\*\s*\|\s*\d+",
            f"**Pending Approval** | {approval_count}"
        )
        content = self._replace_line(
            content,
            r"\*\*Approved\*\*\s*\|\s*\d+",
            f"**Approved** | {approved_count}"
        )
        content = self._replace_line(
            content,
            r"\*\*Completed Today\*\*\s*\|\s*\d+",
            f"**Completed Today** | {done_count}"
        )

        # Update today's stats section
        content = self._replace_line(
            content,
            r"Emails Processed:\s*\d+",
            f"Emails Processed: {today_stats['emails_processed']}"
        )
        content = self._replace_line(
            content,
            r"Emails Sent:\s*\d+",
            f"Emails Sent: {today_stats['emails_sent']}"
        )

        # Save updated dashboard
        self.dashboard.write_text(content, encoding="utf-8")
        print(f"   ✓ Dashboard updated")

    def _replace_line(self, content: str, pattern: str, replacement: str) -> str:
        """Replace line matching pattern."""
        import re
        return re.sub(pattern, replacement, content, flags=re.IGNORECASE)

    def create_dashboard(self):
        """Create new Dashboard.md."""
        now = datetime.now()
        content = f"""---
generated: {now.strftime('%Y-%m-%dT%H:%M:%S')}
last_updated: {now.strftime('%Y-%m-%d')}
last_check: {now.strftime('%H:%M:%S')}
status: active
---

# 🤖 AI Employee Dashboard

## Quick Status

| Metric | Count | Last Updated |
|--------|-------|--------------|
| **Pending Tasks** | 0 | {now.strftime('%H:%M:%S')} |
| **Pending Approval** | 0 | {now.strftime('%H:%M:%S')} |
| **Approved** | 0 | {now.strftime('%H:%M:%S')} |
| **Completed Today** | 0 | {now.strftime('%H:%M:%S')} |

---

## 📊 Today's Activity

### Email Statistics
- Emails Processed: 0
- Emails Sent: 0
- Emails Failed: 0

---

## 📬 Recent Activity

<!-- Recent activity will be logged here -->

---

## 📋 Active Tasks

| Task | Priority | Status |
|------|----------|--------|
| *No active tasks* | - | - |

---

## 🎯 System Status

| Component | Status |
|-----------|--------|
| **Gmail Watcher** | 🟢 Running |
| **Orchestrator** | 🟢 Running |
| **Last Sync** | {now.strftime('%Y-%m-%d %H:%M:%S')} |

---

## 📝 Quick Notes

*Space for notes*

---

## 🔗 Quick Links

- [[Needs_Action]] - Pending tasks
- [[Pending_Approval]] - Awaiting approval
- [[Approved]] - Ready to execute
- [[Done]] - Completed tasks
- [[Plans]] - Action plans
- [[Logs]] - Activity logs
"""
        self.dashboard.write_text(content, encoding="utf-8")
        print(f"   ✓ Dashboard created")


def update_dashboard(vault_path: Path):
    """Update dashboard function."""
    updater = DashboardUpdater(vault_path)
    updater.update_dashboard()


if __name__ == "__main__":
    import sys
    vault_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "Vault"
    updater = DashboardUpdater(vault_path)
    updater.update_dashboard()
