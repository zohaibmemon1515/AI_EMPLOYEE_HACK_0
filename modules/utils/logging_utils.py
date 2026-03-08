#!/usr/bin/env python3
"""
Shared Logging Utilities for Windows Unicode Support

Provides UTF-8 compatible logging handlers that work on Windows consoles.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


class WindowsSafeStreamHandler(logging.StreamHandler):
    """Stream handler that handles Unicode emojis on Windows consoles."""
    
    # Emoji replacement map for Windows console compatibility
    EMOJI_REPLACEMENTS = {
        '👁️': '[O]',      # Observe
        '📋': '[T]',      # Task
        '🤖': '[AI]',     # AI
        '✅': '[OK]',     # Success
        '❌': '[X]',      # Error
        '⚠️': '[!]',      # Warning
        '📝': '[N]',      # Note
        '🔄': '[~]',      # Refresh
        '📊': '[D]',      # Dashboard
        '📁': '[F]',      # Folder
        '🔍': '[S]',      # Search
        '💾': '[S]',      # Save
        '🚀': '[G]',      # Go
        '📧': '[E]',      # Email
        '💬': '[W]',      # WhatsApp
        '📱': '[M]',      # Mobile
        '🕐': '[T]',      # Time
        '✨': '[*]',      # Sparkle
        '🎯': '[T]',      # Target
        '📌': '[P]',      # Pin
        '🔔': '[A]',      # Alert
        '📈': '[G]',      # Growth
        '📉': '[D]',      # Decline
        '🔧': '[C]',      # Config
        '🛠️': '[T]',      # Tools
        '🗂️': '[F]',      # Files
        '📅': '[D]',      # Date
        '⏰': '[A]',      # Alarm
        '🎉': '[!]',      # Celebration
        '👍': '[Y]',      # Thumbs up
        '👎': '[N]',      # Thumbs down
        '🔥': '[F]',      # Fire
        '💰': '[M]',      # Money
        '💡': '[I]',      # Idea
        '🎨': '[A]',      # Art
        '📢': '[A]',      # Announcement
        '🔗': '[L]',      # Link
        '⭐': '[S]',      # Star
        '❤️': '[H]',      # Heart
        '🔴': '[R]',      # Red circle
        '🟢': '[G]',      # Green circle
        '🟡': '[Y]',      # Yellow circle
        '🔵': '[B]',      # Blue circle
    }
    
    def __init__(self, stream=None, replace_emojis: bool = True):
        """
        Initialize handler.
        
        Args:
            stream: Output stream (defaults to sys.stderr)
            replace_emojis: Whether to replace emojis with ASCII alternatives
        """
        super().__init__(stream)
        self.replace_emojis = replace_emojis and sys.platform == "win32"
    
    def _sanitize_message(self, msg: str) -> str:
        """Replace emojis with ASCII alternatives for Windows console."""
        if not self.replace_emojis:
            return msg
        for emoji, replacement in self.EMOJI_REPLACEMENTS.items():
            msg = msg.replace(emoji, replacement)
        return msg
    
    def emit(self, record):
        """Emit a record with Unicode handling."""
        try:
            msg = self.format(record)
            if self.replace_emojis:
                msg = self._sanitize_message(msg)
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except UnicodeEncodeError:
            # Fallback: strip all non-ASCII
            try:
                msg = self.format(record)
                msg = msg.encode('ascii', 'ignore').decode('ascii')
                stream = self.stream
                stream.write(msg + self.terminator)
                self.flush()
            except Exception:
                pass  # Silent failure to prevent logging errors from crashing app


def setup_logging(
    name: str,
    level: int = logging.INFO,
    log_format: Optional[str] = None,
    log_file: Optional[Path] = None,
    console_handler: bool = True,
    file_handler: bool = True
) -> logging.Logger:
    """
    Set up logging with Windows Unicode support.
    
    Args:
        name: Logger name
        level: Logging level
        log_format: Custom format string
        log_file: Path to log file
        console_handler: Whether to add console handler
        file_handler: Whether to add file handler
    
    Returns:
        Configured logger
    """
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler with emoji replacement
    if console_handler:
        console = WindowsSafeStreamHandler()
        console.setFormatter(logging.Formatter(log_format))
        logger.addHandler(console)
    
    # File handler with UTF-8 encoding
    if file_handler and log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setFormatter(logging.Formatter(log_format))
        logger.addHandler(fh)

    return logger

