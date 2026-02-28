#!/usr/bin/env python3
r"""
Base Watcher Class - Abstract base for all watcher scripts.

Watchers monitor various inputs (email, files, APIs) and create
actionable .md files in the Needs_Action folder for Claude to process.
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any


class BaseWatcher(ABC):
    """Abstract base class for all watcher implementations."""

    def __init__(self, vault_path: str | Path, check_interval: int = 60):
        """
        Initialize the watcher.

        Args:
            vault_path: Path to the Obsidian vault root
            check_interval: Seconds between checks (default: 60)
        """
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / "Needs_Action"
        self.inbox = self.vault_path / "Inbox"
        self.check_interval = check_interval

        # Ensure directories exist
        self.needs_action.mkdir(parents=True, exist_ok=True)
        self.inbox.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)

        # Track processed items to avoid duplicates
        self.processed_ids: set[str] = set()

        # Handler for graceful shutdown
        self._running = False

    @abstractmethod
    def check_for_updates(self) -> list[Any]:
        """
        Check for new items to process.

        Returns:
            List of new items that need action files created
        """
        pass

    @abstractmethod
    def create_action_file(self, item: Any) -> Path:
        """
        Create a .md action file for the given item.

        Args:
            item: The item to create an action file for

        Returns:
            Path to the created action file
        """
        pass

    def _generate_filename(self, prefix: str, unique_id: str) -> str:
        """Generate a unique filename for an action file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{unique_id}_{timestamp}.md"

    def _create_markdown_file(
        self,
        filename: str,
        frontmatter: dict[str, Any],
        content: str,
        suggested_actions: list[str] | None = None,
    ) -> Path:
        """
        Create a properly formatted markdown action file.

        Args:
            filename: Name of the file to create
            frontmatter: Dictionary of frontmatter fields
            content: Main content of the file
            suggested_actions: List of suggested checkbox actions

        Returns:
            Path to the created file
        """
        # Build frontmatter
        fm_lines = ["---"]
        for key, value in frontmatter.items():
            if isinstance(value, list):
                fm_lines.append(f"{key}:")
                for item in value:
                    fm_lines.append(f"  - {item}")
            else:
                fm_lines.append(f"{key}: {value}")
        fm_lines.append("---")

        # Build content
        markdown = "\n".join(fm_lines) + "\n\n"
        markdown += content

        # Add suggested actions if provided
        if suggested_actions:
            markdown += "\n## Suggested Actions\n"
            for action in suggested_actions:
                markdown += f"- [ ] {action}\n"

        # Write file
        filepath = self.needs_action / filename
        filepath.write_text(markdown, encoding="utf-8")

        self.logger.info(f"Created action file: {filepath.name}")
        return filepath

    def run(self):
        """Run the watcher loop continuously."""
        self._running = True
        self.logger.info(f"Starting {self.__class__.__name__}")
        self.logger.info(f"Vault path: {self.vault_path}")
        self.logger.info(f"Check interval: {self.check_interval}s")

        try:
            while self._running:
                try:
                    items = self.check_for_updates()
                    for item in items:
                        try:
                            self.create_action_file(item)
                        except Exception as e:
                            self.logger.error(f"Error creating action file: {e}")
                except Exception as e:
                    self.logger.error(f"Error in check loop: {e}")

                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal")
        finally:
            self.stop()

    def stop(self):
        """Stop the watcher loop."""
        self._running = False
        self.logger.info(f"Stopped {self.__class__.__name__}")

    def is_running(self) -> bool:
        """Check if the watcher is currently running."""
        return self._running
