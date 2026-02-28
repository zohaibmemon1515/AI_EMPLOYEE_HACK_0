#!/usr/bin/env python3
r"""
Orchestrator - Triggers task processing (Local or Claude Code).

This script:
1. Scans the Needs_Action folder for pending items
2. Uses Local Processor (rule-based) or Claude Code
3. Processes tasks and moves files appropriately

Usage:
    python orchestrator.py [vault_path] [--dry-run] [--use-claude]

Example:
    python orchestrator.py "E:\path\to\Vault"
    python orchestrator.py "E:\path\to\Vault" --dry-run
"""

import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class Orchestrator:
    """Orchestrates Claude Code processing of action files."""

    def __init__(self, vault_path: str | Path):
        """
        Initialize the orchestrator.

        Args:
            vault_path: Path to the Obsidian vault root
        """
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / "Needs_Action"
        self.done = self.vault_path / "Done"
        self.plans = self.vault_path / "Plans"
        self.dashboard = self.vault_path / "Dashboard.md"

        # Ensure directories exist
        self.needs_action.mkdir(parents=True, exist_ok=True)
        self.done.mkdir(parents=True, exist_ok=True)
        self.plans.mkdir(parents=True, exist_ok=True)

    def get_pending_files(self) -> list[Path]:
        """Get all pending action files."""
        if not self.needs_action.exists():
            return []

        pending = []
        for filepath in self.needs_action.iterdir():
            if filepath.is_file() and filepath.suffix == ".md":
                # Check if file has pending status
                content = filepath.read_text(encoding="utf-8")
                if "status: pending" in content.lower() or "status: in_progress" in content.lower():
                    pending.append(filepath)

        return sorted(pending, key=lambda f: f.stat().st_mtime)

    def read_action_file(self, filepath: Path) -> dict[str, Any]:
        """Parse an action file and extract metadata."""
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
            "type": frontmatter.get("type", "unknown"),
            "priority": frontmatter.get("priority", "medium"),
        }

    def create_processing_prompt(self, files: list[dict[str, Any]]) -> str:
        """Create a prompt for Claude Code to process the files."""
        prompt = """# AI Employee Task Processing

You are an AI Employee processing tasks from your Obsidian vault.

## Context
- **Vault**: """ + str(self.vault_path) + """
- **Current Time**: """ + datetime.now().isoformat() + """
- **Pending Files**: """ + str(len(files)) + """

## Your Instructions

1. **Read** the Company Handbook at `Company_Handbook.md` for rules and guidelines
2. **Read** the Business Goals at `Business_Goals.md` for context
3. **Process** each pending file in the Needs_Action folder:
   - Understand the task/request
   - Take appropriate actions (within your permissions)
   - For actions requiring approval, create a file in `Pending_Approval/`
   - Update the file with your actions taken
   - Move completed files to `Done/`

4. **Update** the Dashboard.md with a summary of work done

## Priority Order
Process files in this order:
1. Critical priority first
2. Then High priority
3. Then Medium priority
4. Then Low priority

## Output Format
For each file processed, document:
- What you understood the task to be
- What actions you took
- Any follow-up needed
- Where you moved the file

---

## Files to Process

"""

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_files = sorted(
            files,
            key=lambda f: priority_order.get(f.get("priority", "medium"), 2),
        )

        for i, file_info in enumerate(sorted_files, 1):
            prompt += f"""
### File {i}: {file_info['name']}
- **Type**: {file_info['type']}
- **Priority**: {file_info['priority']}
- **Path**: {file_info['path']}

--- Content ---
{file_info['content'][:3000]}  # Truncate to avoid token limits
--- End Content ---

"""

        prompt += """
---

## Next Steps

Please process these files according to the Company Handbook guidelines.
Remember to:
- Ask for approval before any financial transactions
- Log all actions taken
- Move completed tasks to /Done
- Update the Dashboard with your progress
"""

        return prompt

    def run_claude(self, prompt: str, dry_run: bool = False) -> str:
        """
        Run Claude Code with the given prompt.

        Args:
            prompt: The prompt to send to Claude
            dry_run: If True, just print the prompt without running Claude

        Returns:
            Claude's response
        """
        if dry_run:
            print("=== DRY RUN - Would send to Claude ===")
            print(prompt[:2000] + "..." if len(prompt) > 2000 else prompt)
            return "[Dry run - no response]"

        try:
            # Run Claude Code with the prompt
            result = subprocess.run(
                ["claude", "--prompt", prompt],
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                cwd=str(self.vault_path),
            )

            if result.returncode != 0:
                raise RuntimeError(f"Claude exited with code {result.returncode}: {result.stderr}")

            return result.stdout

        except FileNotFoundError:
            print("Warning: 'claude' command not found.")
            print("Make sure Claude Code is installed and in your PATH.")
            print("Install from: https://claude.com/product/claude-code")
            return "[Error: Claude not installed]"

        except subprocess.TimeoutExpired:
            print("Warning: Claude timed out after 10 minutes.")
            return "[Error: Timeout]"

    def update_dashboard(self, processed_count: int, claude_response: str):
        """Update the Dashboard.md with processing summary."""
        if not self.dashboard.exists():
            return

        content = self.dashboard.read_text(encoding="utf-8")

        # Update timestamp
        content = content.replace(
            "last_updated: 2026-",
            f"last_updated: {datetime.now().strftime('%Y-%m-%d')}",
        )

        # Update pending count
        pending_files = self.get_pending_files()
        content = content.replace(
            "**Pending Tasks** | 0 |",
            f"**Pending Tasks** | {len(pending_files)} |",
        )

        self.dashboard.write_text(content, encoding="utf-8")

    def process_all(self, dry_run: bool = False, use_claude: bool = False):
        """
        Process all pending files.

        Args:
            dry_run: If True, don't actually process
            use_claude: If True, try Claude first, fallback to local
        """
        print(f"🔍 Scanning {self.needs_action} for pending files...")

        pending_files = self.get_pending_files()

        if not pending_files:
            print("✅ No pending files to process!")
            return

        print(f"📁 Found {len(pending_files)} pending file(s)")
        print()

        # Use local processor (default) or Claude
        if use_claude:
            # Try Claude first
            print("🤖 Attempting to use Claude Code...")
            file_infos = [self.read_action_file(f) for f in pending_files]
            prompt = self.create_processing_prompt(file_infos)
            response = self.run_claude(prompt, dry_run)

            if "not found" in response or "Error" in response:
                print("\n⚠️  Claude not available, falling back to Local Processor...")
                self._process_with_local(pending_files, dry_run)
            else:
                print("✅ Processing complete!")
                print(f"\n📄 Claude Response:\n{response[:500]}...")
        else:
            # Use local processor directly
            self._process_with_local(pending_files, dry_run)

    def _process_with_local(self, pending_files: list[Path], dry_run: bool = False):
        """Process files using local processor."""
        if dry_run:
            print("\n[DRY RUN] Would process files with Local Processor")
            for f in pending_files:
                print(f"  - {f.name}")
            return

        # Import and use local processor
        from local_processor import LocalTaskProcessor

        print("🤖 Using Local Task Processor (Rule-based)...")
        print()

        processor = LocalTaskProcessor(self.vault_path)
        processor.process_all()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Orchestrate task processing")
    parser.add_argument(
        "vault_path",
        nargs="?",
        default=None,
        help="Path to the Obsidian vault (default: ./Vault)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print prompt without running processor",
    )
    parser.add_argument(
        "--use-claude",
        action="store_true",
        help="Try Claude Code first (fallback to local)",
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Determine vault path
    if args.vault_path:
        vault_path = Path(args.vault_path)
    else:
        vault_path = Path(__file__).parent / "Vault"

    # Run orchestrator
    orchestrator = Orchestrator(vault_path)
    orchestrator.process_all(dry_run=args.dry_run, use_claude=args.use_claude)


if __name__ == "__main__":
    main()
