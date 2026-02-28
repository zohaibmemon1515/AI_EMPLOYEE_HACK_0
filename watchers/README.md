# Watchers

Lightweight Python scripts that monitor various inputs and create actionable files for Claude to process.

## Available Watchers

### File System Watcher (`filesystem_watcher.py`)

Monitors the `Inbox` folder for new files and creates action files in `Needs_Action`.

**Usage:**
```bash
python filesystem_watcher.py [vault_path] [check_interval]

# Examples:
python filesystem_watcher.py "../Vault" 30
python filesystem_watcher.py "E:\path\to\Vault" 60
```

**Features:**
- Detects new files in the Inbox folder
- Calculates file hash to avoid duplicates
- Determines file type and priority automatically
- Creates properly formatted action files
- Moves processed files to `In_Progress/filesystem/`

### Base Watcher (`base_watcher.py`)

Abstract base class for creating new watchers.

**To create a new watcher:**
```python
from base_watcher import BaseWatcher

class MyWatcher(BaseWatcher):
    def check_for_updates(self) -> list:
        # Return list of new items
        pass

    def create_action_file(self, item) -> Path:
        # Create action file for item
        pass
```

## Adding New Watchers

1. Create a new Python file in this directory
2. Inherit from `BaseWatcher`
3. Implement `check_for_updates()` and `create_action_file()`
4. Add to `run.py` if it should start automatically

## Watcher Lifecycle

```
Start → Check for updates → Create action files → Wait → Repeat
  │                                              │
  └────────────── Stop (Ctrl+C) ─────────────────┘
```

## Logging

All watchers log to stdout with timestamps:
```
2026-02-26 10:00:00 - FileSystemWatcher - INFO - New file detected: document.pdf
2026-02-26 10:00:01 - FileSystemWatcher - INFO - Created action file: FILE_document_20260226_100001.md
```
