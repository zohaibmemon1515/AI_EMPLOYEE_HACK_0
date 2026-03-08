#!/usr/bin/env python3
r"""
File System Watcher - Monitors the Inbox folder for new files.

When new files are dropped into the Inbox folder, this watcher
creates corresponding action files in the Needs_Action folder
for Claude to process.

Usage:
    python filesystem_watcher.py [vault_path] [check_interval]

Example:
    python filesystem_watcher.py "E:\path\to\Vault" 30
"""

import hashlib
import shutil
from pathlib import Path
from typing import Any

# Windows-safe logging setup
import logging
class WindowsSafeHandler(logging.StreamHandler):
    """Logging handler that replaces emojis with ASCII on Windows."""
    EMOJI_MAP = {
        '👁️': '[O]', '📋': '[T]', '🤖': '[AI]', '✅': '[OK]', '❌': '[X]',
        '⚠️': '[!]', '📝': '[N]', '🔄': '[~]', '📊': '[D]', '📁': '[F]',
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

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = WindowsSafeHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)

from base_watcher import BaseWatcher


class FileSystemWatcher(BaseWatcher):
    """Watches the Inbox folder for new files."""

    def __init__(self, vault_path: str | Path, check_interval: int = 30):
        """
        Initialize the file system watcher.

        Args:
            vault_path: Path to the Obsidian vault root
            check_interval: Seconds between checks (default: 30)
        """
        super().__init__(vault_path, check_interval)
        self.drop_folder = self.vault_path / "Inbox"
        self.processed_folder = self.vault_path / "In_Progress" / "filesystem"

        # Ensure folders exist
        self.drop_folder.mkdir(parents=True, exist_ok=True)
        self.processed_folder.mkdir(parents=True, exist_ok=True)

        # Track processed files by hash
        self._load_processed_hashes()

    def _load_processed_hashes(self):
        """Load hashes of already processed files."""
        self.processed_hashes = set()
        hash_file = self.processed_folder / ".processed_hashes"
        if hash_file.exists():
            self.processed_hashes = set(hash_file.read_text().splitlines())

    def _save_processed_hashes(self):
        """Save the set of processed file hashes."""
        hash_file = self.processed_folder / ".processed_hashes"
        hash_file.write_text("\n".join(self.processed_hashes))

    def _get_file_hash(self, filepath: Path) -> str:
        """Calculate MD5 hash of a file."""
        hasher = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _get_file_type(self, filepath: Path) -> str:
        """Determine the type of file based on extension and content."""
        ext = filepath.suffix.lower()

        type_mapping = {
            ".txt": "text",
            ".md": "markdown",
            ".pdf": "document",
            ".doc": "document",
            ".docx": "document",
            ".xls": "spreadsheet",
            ".xlsx": "spreadsheet",
            ".csv": "data",
            ".json": "data",
            ".xml": "data",
            ".png": "image",
            ".jpg": "image",
            ".jpeg": "image",
            ".gif": "image",
            ".webp": "image",
            ".mp3": "audio",
            ".wav": "audio",
            ".mp4": "video",
            ".avi": "video",
        }

        return type_mapping.get(ext, "unknown")

    def _detect_priority(self, filepath: Path, content: str) -> str:
        """Detect priority based on filename and content keywords."""
        name_lower = filepath.name.lower()
        content_lower = content.lower()

        # Critical keywords
        critical_keywords = ["urgent", "emergency", "asap", "critical", "immediate"]
        if any(kw in name_lower or kw in content_lower for kw in critical_keywords):
            return "critical"

        # High priority keywords
        high_keywords = ["invoice", "payment", "due", "deadline", "important"]
        if any(kw in name_lower or kw in content_lower for kw in high_keywords):
            return "high"

        # Medium priority keywords
        medium_keywords = ["review", "check", "update", "reminder"]
        if any(kw in name_lower or kw in content_lower for kw in medium_keywords):
            return "medium"

        return "low"

    def check_for_updates(self) -> list[dict[str, Any]]:
        """
        Check the Inbox folder for new files.

        Returns:
            List of file info dictionaries for new files
        """
        new_files = []

        if not self.drop_folder.exists():
            return new_files

        for filepath in self.drop_folder.iterdir():
            if filepath.is_file() and not filepath.name.startswith("."):
                file_hash = self._get_file_hash(filepath)

                if file_hash not in self.processed_hashes:
                    self.logger.info(f"New file detected: {filepath.name}")
                    new_files.append({
                        "path": filepath,
                        "hash": file_hash,
                    })

        return new_files

    def create_action_file(self, item: dict[str, Any]) -> Path:
        """
        Create an action file for a new file in the Inbox.

        Args:
            item: Dictionary with 'path' and 'hash' keys

        Returns:
            Path to the created action file
        """
        filepath = item["path"]
        file_hash = item["hash"]

        # Read file content (if text-based)
        content = ""
        text_extensions = {".txt", ".md", ".csv", ".json", ".xml", ".log"}
        if filepath.suffix.lower() in text_extensions:
            try:
                content = filepath.read_text(encoding="utf-8")
                # Truncate long content for the action file
                if len(content) > 2000:
                    content = content[:2000] + "\n\n... [content truncated]"
            except Exception as e:
                content = f"[Could not read file content: {e}]"

        # Get file metadata
        stat = filepath.stat()
        file_size = stat.st_size
        file_type = self._get_file_type(filepath)
        priority = self._detect_priority(filepath, content)

        # Generate filename
        safe_name = filepath.stem.replace(" ", "_")[:50]
        filename = self._generate_filename("FILE", safe_name)

        # Create frontmatter
        frontmatter = {
            "type": "file_drop",
            "original_name": filepath.name,
            "file_type": file_type,
            "size_bytes": file_size,
            "priority": priority,
            "status": "pending",
            "created": __import__("datetime").datetime.now().isoformat(),
            "file_hash": file_hash,
        }

        # Build content
        action_content = f"""## File Information

- **Original Name**: {filepath.name}
- **Type**: {file_type}
- **Size**: {file_size:,} bytes
- **Location**: `{filepath}`
- **Priority**: {priority}

## File Content

```
{content if content else "[Binary file - content not displayed]"}
```

## Processing Notes

*Add notes about how this file should be processed*
"""

        # Suggested actions based on file type
        suggested_actions = [
            f"Review {filepath.name} content",
            "Categorize file appropriately",
            "Extract any action items",
            "Move original file to appropriate folder",
        ]

        if file_type == "document":
            suggested_actions.append("Summarize key points")
        elif file_type == "data":
            suggested_actions.append("Analyze data for insights")
        elif file_type == "image":
            suggested_actions.append("Add alt text and description")

        # Create the action file
        action_file = self._create_markdown_file(
            filename=filename,
            frontmatter=frontmatter,
            content=action_content,
            suggested_actions=suggested_actions,
        )

        # Mark file as processed
        self.processed_hashes.add(file_hash)
        self._save_processed_hashes()

        # Move original file to processed folder
        dest = self.processed_folder / filepath.name
        shutil.move(str(filepath), str(dest))
        self.logger.info(f"Moved original file to: {dest}")

        return action_file


def main():
    """Main entry point for running the watcher."""
    import sys

    # Parse arguments
    vault_path = sys.argv[1] if len(sys.argv) > 1 else "../Vault"
    check_interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    # Create and run watcher
    watcher = FileSystemWatcher(vault_path, check_interval)

    try:
        watcher.run()
    except KeyboardInterrupt:
        print("\nWatcher interrupted by user")
        watcher.stop()
    except Exception as e:
        logger.error(f"Watcher crashed: {e}")
        raise


if __name__ == "__main__":
    main()
