#!/usr/bin/env python3
"""Clear processed IDs to re-process all emails."""

import json
from pathlib import Path

base_dir = Path(__file__).parent
processed_file = base_dir / "Vault" / "In_Progress" / "gmail" / "processed_ids.json"

if processed_file.exists():
    # Backup old file
    backup = processed_file.with_suffix(".json.backup")
    backup.write_text(processed_file.read_text())
    print(f"✓ Backup created: {backup}")
    
    # Clear processed IDs
    data = {
        "processed_ids": [],
        "last_updated": "cleared",
        "count": 0
    }
    processed_file.write_text(json.dumps(data, indent=2))
    
    print(f"✓ Cleared: {processed_file}")
    print()
    print("Now restart main.py - all emails will be processed as new!")
    print("Run: python main.py")
else:
    print("No processed_ids.json found - nothing to clear")
