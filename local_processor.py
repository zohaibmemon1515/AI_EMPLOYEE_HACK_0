#!/usr/bin/env python3
r"""
Local Task Processor - Rule-based task processor (no Claude required).

This processor handles tasks automatically using predefined rules:
1. Reads task files from Needs_Action folder
2. Classifies and processes them based on rules
3. Moves completed tasks to Done folder
4. Creates approval requests for sensitive actions
5. Updates Dashboard.md

Usage:
    python local_processor.py [vault_path]
"""

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


class LocalTaskProcessor:
    """Rule-based task processor that works without Claude."""

    def __init__(self, vault_path: Path):
        """
        Initialize the local processor.

        Args:
            vault_path: Path to the Obsidian vault
        """
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / "Needs_Action"
        self.done = self.vault_path / "Done"
        self.pending_approval = self.vault_path / "Pending_Approval"
        self.dashboard = self.vault_path / "Dashboard.md"
        self.handbook = self.vault_path / "Company_Handbook.md"

        # Ensure directories exist
        self.needs_action.mkdir(parents=True, exist_ok=True)
        self.done.mkdir(parents=True, exist_ok=True)
        self.pending_approval.mkdir(parents=True, exist_ok=True)

        # Statistics
        self.processed_count = 0
        self.approval_count = 0
        self.error_count = 0

    def get_pending_files(self) -> list[Path]:
        """Get all pending action files."""
        if not self.needs_action.exists():
            return []

        pending = []
        for filepath in self.needs_action.iterdir():
            if filepath.is_file() and filepath.suffix == ".md":
                content = filepath.read_text(encoding="utf-8")
                if "status: pending" in content.lower() or "status: in_progress" in content.lower():
                    pending.append(filepath)

        return sorted(pending, key=lambda f: f.stat().st_mtime)

    def read_task_file(self, filepath: Path) -> dict[str, Any]:
        """Parse a task file and extract metadata."""
        content = filepath.read_text(encoding="utf-8")

        # Extract frontmatter
        frontmatter = {}
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                fm_text = parts[1]
                for line in fm_text.strip().split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        frontmatter[key.strip()] = value.strip()

        return {
            "path": filepath,
            "name": filepath.name,
            "frontmatter": frontmatter,
            "content": content,
            "type": frontmatter.get("type", "task"),
            "priority": frontmatter.get("priority", "medium"),
            "status": frontmatter.get("status", "pending"),
        }

    def classify_priority(self, content: str, filename: str) -> str:
        """Classify priority based on content and filename."""
        text = (content + " " + filename).lower()

        if any(kw in text for kw in ["urgent", "emergency", "asap", "critical", "immediate"]):
            return "critical"
        elif any(kw in text for kw in ["invoice", "payment", "due", "deadline", "important"]):
            return "high"
        elif any(kw in text for kw in ["review", "check", "update", "reminder"]):
            return "medium"
        return "low"

    def process_task(self, task_info: dict[str, Any]) -> dict[str, Any]:
        """
        Process a single task using rules.

        Args:
            task_info: Task information dictionary

        Returns:
            Processing result dictionary
        """
        content = task_info["content"]
        task_type = task_info["type"]
        filepath = task_info["path"]

        result = {
            "success": False,
            "actions_taken": [],
            "requires_approval": False,
            "approval_reason": None,
            "error": None,
            "move_to": "Done",
        }

        try:
            # Add processing timestamp
            result["actions_taken"].append(f"Read task: {filepath.name}")
            result["actions_taken"].append(f"Task type: {task_type}")

            # Process based on task type
            if task_type == "file_drop":
                result = self._process_file_drop(task_info, result)
            elif task_type == "email":
                result = self._process_email(task_info, result)
            elif task_type == "task":
                result = self._process_general_task(task_info, result)
            elif task_type == "approval_request":
                result = self._process_approval_request(task_info, result)
            else:
                result["actions_taken"].append(f"Unknown task type: {task_type}")
                result["actions_taken"].append("Moving to Done for manual review")

            # Add completion note
            result["actions_taken"].append(f"Processed at: {datetime.now().isoformat()}")
            result["success"] = True

        except Exception as e:
            result["error"] = str(e)
            result["actions_taken"].append(f"Error: {e}")
            self.error_count += 1

        return result

    def _process_file_drop(self, task_info: dict, result: dict) -> dict:
        """Process a file drop task."""
        frontmatter = task_info["frontmatter"]
        content = task_info["content"]

        result["actions_taken"].append("Identified as file drop task")

        # Extract file info
        original_name = frontmatter.get("original_name", "unknown")
        file_type = frontmatter.get("file_type", "unknown")
        file_size = frontmatter.get("size_bytes", 0)

        result["actions_taken"].append(f"Original file: {original_name}")
        result["actions_taken"].append(f"File type: {file_type}, Size: {file_size} bytes")

        # Check for sensitive content
        sensitive_keywords = ["password", "credit card", "bank account", "ssn", "confidential"]
        if any(kw in content.lower() for kw in sensitive_keywords):
            result["requires_approval"] = True
            result["approval_reason"] = "File contains potentially sensitive information"
            result["move_to"] = "Pending_Approval"
            self.approval_count += 1
        else:
            result["actions_taken"].append("No sensitive content detected")
            result["actions_taken"].append("File processed and categorized")

        return result

    def _process_email(self, task_info: dict, result: dict) -> dict:
        """Process an email task."""
        content = task_info["content"]
        frontmatter = task_info["frontmatter"]

        result["actions_taken"].append("Identified as email task")

        # Extract email info
        sender = frontmatter.get("from", "Unknown")
        subject = frontmatter.get("subject", "No Subject")

        result["actions_taken"].append(f"From: {sender}")
        result["actions_taken"].append(f"Subject: {subject}")

        # Check if response needed
        if any(kw in content.lower() for kw in ["question", "help", "urgent", "asap"]):
            result["actions_taken"].append("Email requires response")
            result["requires_approval"] = True
            result["approval_reason"] = "Email response needs approval before sending"
            result["move_to"] = "Pending_Approval"
            self.approval_count += 1
        else:
            result["actions_taken"].append("Email is informational - no response needed")

        return result

    def _process_general_task(self, task_info: dict, result: dict) -> dict:
        """Process a general task."""
        content = task_info["content"]

        result["actions_taken"].append("Identified as general task")
        result["actions_taken"].append("Task understood and documented")

        # Check for payment/financial keywords
        payment_keywords = ["pay", "payment", "invoice", "money", "dollar", "$"]
        if any(kw in content.lower() for kw in payment_keywords):
            result["actions_taken"].append("Task involves financial transaction")
            result["requires_approval"] = True
            result["approval_reason"] = "Financial tasks require human approval"
            result["move_to"] = "Pending_Approval"
            self.approval_count += 1
        else:
            result["actions_taken"].append("No financial content - auto-completed")

        return result

    def _process_approval_request(self, task_info: dict, result: dict) -> dict:
        """Process an approval request."""
        result["actions_taken"].append("This is an approval request")
        result["actions_taken"].append("Waiting for human decision")
        result["move_to"] = "Pending_Approval"
        return result

    def update_task_file(self, filepath: Path, result: dict[str, Any]) -> Path:
        """
        Update the task file with processing results.

        Args:
            filepath: Path to the task file
            result: Processing result dictionary

        Returns:
            New path of the file
        """
        content = filepath.read_text(encoding="utf-8")

        # Update status in frontmatter
        if result["move_to"] == "Done":
            content = re.sub(r"status:\s*\w+", "status: completed", content, flags=re.IGNORECASE)
        elif result["move_to"] == "Pending_Approval":
            content = re.sub(r"status:\s*\w+", "status: awaiting_approval", content, flags=re.IGNORECASE)

        # Add processing notes section
        processing_notes = "\n\n## AI Processing Notes\n\n"
        processing_notes += f"**Processed at**: {datetime.now().isoformat()}\n\n"
        processing_notes += "**Actions Taken**:\n"
        for action in result["actions_taken"]:
            processing_notes += f"- {action}\n"

        if result["requires_approval"]:
            processing_notes += f"\n⚠️ **Approval Required**: {result['approval_reason']}\n"

        if result["error"]:
            processing_notes += f"\n❌ **Error**: {result['error']}\n"

        # Check if processing notes already exist
        if "## AI Processing Notes" not in content:
            content += processing_notes

        # Determine destination
        if result["move_to"] == "Done":
            dest_folder = self.done
        elif result["move_to"] == "Pending_Approval":
            dest_folder = self.pending_approval
        else:
            dest_folder = self.done

        # Move file
        dest_path = dest_folder / filepath.name

        # Write updated content
        dest_path.write_text(content, encoding="utf-8")

        # Remove original file
        filepath.unlink()

        return dest_path

    def update_dashboard(self):
        """Update the Dashboard.md with processing summary."""
        if not self.dashboard.exists():
            return

        content = self.dashboard.read_text(encoding="utf-8")

        # Update timestamp
        now = datetime.now()
        content = re.sub(
            r"last_updated:\s*\d{4}-\d{2}-\d{2}",
            f"last_updated: {now.strftime('%Y-%m-%d')}",
            content,
        )

        # Count pending files
        pending_count = len(self.get_pending_files())
        done_count = len(list(self.done.glob("*.md"))) if self.done.exists() else 0
        approval_count = len(list(self.pending_approval.glob("*.md"))) if self.pending_approval.exists() else 0

        # Update counts (simple regex replacement)
        content = re.sub(
            r"\*\*Pending Tasks\*\* \| \d+",
            f"**Pending Tasks** | {pending_count}",
            content,
        )

        self.dashboard.write_text(content, encoding="utf-8")

    def process_all(self) -> dict[str, int]:
        """
        Process all pending tasks.

        Returns:
            Statistics dictionary
        """
        stats = {
            "processed": 0,
            "completed": 0,
            "pending_approval": 0,
            "errors": 0,
        }

        print(f"🔍 Scanning {self.needs_action} for pending files...")

        pending_files = self.get_pending_files()

        if not pending_files:
            print("✅ No pending files to process!")
            return stats

        print(f"📁 Found {len(pending_files)} pending file(s)")
        print()

        for filepath in pending_files:
            print(f"📄 Processing: {filepath.name}")

            # Read task
            task_info = self.read_task_file(filepath)

            # Process task
            result = self.process_task(task_info)

            # Update file
            new_path = self.update_task_file(filepath, result)

            # Update stats
            stats["processed"] += 1
            if result["success"]:
                if result["move_to"] == "Done":
                    stats["completed"] += 1
                    print(f"   ✅ Completed → {new_path}")
                else:
                    stats["pending_approval"] += 1
                    print(f"   ⏳ Awaiting approval → {new_path}")
            else:
                stats["errors"] += 1
                print(f"   ❌ Error: {result.get('error', 'Unknown')}")

            self.processed_count += 1

        # Update dashboard
        print("\n📊 Updating dashboard...")
        self.update_dashboard()

        print()
        print("=" * 60)
        print("Processing Summary:")
        print(f"  Processed: {stats['processed']}")
        print(f"  Completed: {stats['completed']}")
        print(f"  Pending Approval: {stats['pending_approval']}")
        print(f"  Errors: {stats['errors']}")
        print("=" * 60)

        return stats


def main():
    """Main entry point."""
    import sys

    vault_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "Vault"

    print("=" * 60)
    print("🤖 Local Task Processor (No Claude Required)")
    print("=" * 60)
    print(f"Vault: {vault_path}")
    print()

    processor = LocalTaskProcessor(vault_path)
    processor.process_all()


if __name__ == "__main__":
    main()
