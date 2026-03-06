#!/usr/bin/env python3
"""Simple Dashboard Updater - Updates stats in real-time"""

import json
from datetime import datetime
from pathlib import Path


def update_dashboard(vault_path):
    """Update Dashboard.md with current stats."""
    dashboard = vault_path / "Dashboard.md"
    logs = vault_path / "Logs"
    needs_action = vault_path / "Needs_Action"
    pending_approval = vault_path / "Pending_Approval"
    approved = vault_path / "Approved"
    done = vault_path / "Done"
    
    if not dashboard.exists():
        print("   ⚠️  Dashboard not found")
        return
    
    now = datetime.now()
    
    # Count files
    pending = len(list(needs_action.glob("*.md"))) if needs_action.exists() else 0
    approval = len(list(pending_approval.glob("*.md"))) if pending_approval.exists() else 0
    approved_count = len(list(approved.glob("*.md"))) if approved.exists() else 0
    done_count = len(list(done.glob("*.md"))) if done.exists() else 0
    
    # Count by type
    email_pending = len(list(needs_action.glob("EMAIL_*.md"))) if needs_action.exists() else 0
    whatsapp_pending = len(list(needs_action.glob("WHATSAPP_*.md"))) if needs_action.exists() else 0
    email_drafts = len(list(pending_approval.glob("EMAIL_REPLY_*.md"))) if pending_approval.exists() else 0
    whatsapp_drafts = len(list(pending_approval.glob("WHATSAPP_REPLY_*.md"))) if pending_approval.exists() else 0
    
    # Get today's stats
    today = now.strftime("%Y-%m-%d")
    log_file = logs / f"{today}.json"
    
    gmail_processed = 0
    gmail_sent = 0
    whatsapp_processed = 0
    whatsapp_sent = 0
    
    if log_file.exists():
        try:
            log_data = json.loads(log_file.read_text(encoding="utf-8"))
            for entry in log_data:
                actor = entry.get("actor", "").lower()
                action = entry.get("action_type", "")
                
                if "gmail" in actor:
                    if action == "email_processed":
                        gmail_processed += 1
                    elif action == "email_sent":
                        gmail_sent += 1
                elif "whatsapp" in actor:
                    if action == "message_processed":
                        whatsapp_processed += 1
                    elif action == "sent":
                        whatsapp_sent += 1
        except Exception as e:
            print(f"   ⚠️  Log read error: {e}")
    
    # Read dashboard
    content = dashboard.read_text(encoding="utf-8")
    
    # Update counts - simple string replacement
    content = content.replace("| 0 | 00:00:00 |", f"| {pending} | {now.strftime('%H:%M:%S')} |", 4)
    
    # Update detailed breakdown
    if "Emails Pending:" in content:
        content = _replace_line(content, "Emails Pending:", f"Emails Pending: {email_pending}")
        content = _replace_line(content, "WhatsApp Pending:", f"WhatsApp Pending: {whatsapp_pending}")
        content = _replace_line(content, "Email Drafts:", f"Email Drafts: {email_drafts}")
        content = _replace_line(content, "WhatsApp Drafts:", f"WhatsApp Drafts: {whatsapp_drafts}")
    
    # Update stats
    if "Gmail Processed:" in content:
        content = _replace_line(content, "Gmail Processed:", f"Gmail Processed: {gmail_processed}")
        content = _replace_line(content, "Gmail Sent:", f"Gmail Sent: {gmail_sent}")
        content = _replace_line(content, "WhatsApp Processed:", f"WhatsApp Processed: {whatsapp_processed}")
        content = _replace_line(content, "WhatsApp Sent:", f"WhatsApp Sent: {whatsapp_sent}")
    
    # Update timestamp
    if "Last Sync" in content:
        content = _replace_line(content, "**Last Sync** |", f"**Last Sync** | {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Update recent activity
    activity_table = _get_recent_activity(log_file)
    if "<!-- RECENT_ACTIVITY_START -->" in content:
        start = content.find("<!-- RECENT_ACTIVITY_START -->")
        end = content.find("<!-- RECENT_ACTIVITY_END -->") + len("<!-- RECENT_ACTIVITY_END -->")
        if end > start:
            content = content[:start] + f"<!-- RECENT_ACTIVITY_START -->\n{activity_table}<!-- RECENT_ACTIVITY_END -->" + content[end:]
    
    # Save
    dashboard.write_text(content, encoding="utf-8")
    print(f"   ✓ Dashboard updated - {pending} pending, {approval} approval")


def _replace_line(content, marker, new_value):
    """Replace a line containing marker."""
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if marker in line:
            lines[i] = line.split(marker)[0] + marker + " " + str(new_value).split(marker)[-1].strip()
            break
    return "\n".join(lines)


def _get_recent_activity(log_file):
    """Build recent activity table."""
    if not log_file.exists():
        return "| Time | Activity | Status |\n|------|----------|--------|\n| - | No activity | - |"
    
    try:
        log_data = json.loads(log_file.read_text(encoding="utf-8"))
        recent = log_data[-8:]  # Last 8 entries
        
        lines = ["| Time | Activity | Status |", "|------|----------|--------|"]
        for entry in reversed(recent):
            time = entry.get("timestamp", "")[11:19]
            action = entry.get("action_type", "").replace("_", " ").title()
            result = "✅" if entry.get("result") == "success" else "❌"
            actor = "📧" if "gmail" in entry.get("actor", "").lower() else "💬"
            lines.append(f"| {time} | {actor} {action} | {result} |")
        
        return "\n".join(lines) + "\n"
    except:
        return "| Time | Activity | Status |\n|------|----------|--------|\n| - | Loading... | - |"


if __name__ == "__main__":
    import sys
    vault = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "Vault"
    update_dashboard(vault)
