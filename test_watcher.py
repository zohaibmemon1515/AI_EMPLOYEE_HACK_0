#!/usr/bin/env python3
"""Test that watcher starts correctly."""

import sys
import time
import subprocess
from pathlib import Path

base = Path(__file__).parent
vault = base / "Vault"

print("Testing watcher startup...")
print(f"Vault: {vault}")

# Start watcher
proc = subprocess.Popen(
    [sys.executable, str(base / "watchers" / "filesystem_watcher.py"), str(vault), "5"],
)

print(f"Watcher started with PID: {proc.pid}")
print("Waiting 10 seconds...")

for i in range(10):
    time.sleep(1)
    if proc.poll() is not None:
        print(f"❌ Watcher exited after {i+1} seconds!")
        print(f"Return code: {proc.returncode}")
        sys.exit(1)
    print(f"  {i+1}s - still running...")

# Stop watcher
print("\nStopping watcher...")
proc.terminate()
try:
    proc.wait(timeout=5)
    print("✅ Watcher stopped cleanly")
except subprocess.TimeoutExpired:
    proc.kill()
    print("✅ Watcher killed")

print("\n✅ Watcher test PASSED!")
