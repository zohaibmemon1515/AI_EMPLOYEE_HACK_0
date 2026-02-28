#!/usr/bin/env python3
"""Quick test to verify all imports work."""

import sys
from pathlib import Path

base = Path(__file__).parent

print("Testing imports...")

# Test base_watcher
try:
    sys.path.insert(0, str(base / "watchers"))
    from base_watcher import BaseWatcher
    print("✅ base_watcher.py - OK")
except Exception as e:
    print(f"❌ base_watcher.py - {e}")

# Test filesystem_watcher
try:
    from filesystem_watcher import FileSystemWatcher
    print("✅ filesystem_watcher.py - OK")
except Exception as e:
    print(f"❌ filesystem_watcher.py - {e}")

# Test orchestrator
try:
    sys.path.insert(0, str(base))
    import orchestrator
    print("✅ orchestrator.py - OK")
except Exception as e:
    print(f"❌ orchestrator.py - {e}")

# Test main
try:
    import main
    print("✅ main.py - OK")
except Exception as e:
    print(f"❌ main.py - {e}")

print("\n✅ All imports tested!")
