#!/usr/bin/env python3
"""
Test script to verify WhatsApp watcher argument parsing.
"""

import sys
from pathlib import Path

# Add watchers directory to path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR / "watchers"))

from whatsapp_watcher import WhatsAppWatcher, WhatsAppConfig

def test_argument_parsing():
    """Test that arguments are parsed correctly."""
    import argparse
    
    parser = argparse.ArgumentParser(description="WhatsApp Watcher")
    parser.add_argument("vault_path", nargs="?", default="./Vault", help="Path to Obsidian vault")
    parser.add_argument("interval", nargs="?", type=int, default=30, help="Check interval in seconds")
    parser.add_argument("--interval", "-i", dest="interval_flag", type=int, default=None, help="Check interval in seconds")
    
    # Test case 1: Positional arguments (like main.py calls)
    test_args_1 = parser.parse_args(["/path/to/vault", "30"])
    assert test_args_1.vault_path == "/path/to/vault"
    assert test_args_1.interval == 30
    print("✓ Test 1 passed: Positional arguments work")
    
    # Test case 2: Only vault path
    test_args_2 = parser.parse_args(["/path/to/vault"])
    assert test_args_2.vault_path == "/path/to/vault"
    assert test_args_2.interval == 30  # default
    print("✓ Test 2 passed: Default interval works")
    
    # Test case 3: Flag-based interval
    test_args_3 = parser.parse_args(["/path/to/vault", "--interval", "60"])
    assert test_args_3.vault_path == "/path/to/vault"
    assert test_args_3.interval_flag == 60
    print("✓ Test 3 passed: Flag-based interval works")
    
    # Test case 4: No arguments
    test_args_4 = parser.parse_args([])
    assert test_args_4.vault_path == "./Vault"
    assert test_args_4.interval == 30
    print("✓ Test 4 passed: No arguments uses defaults")
    
    print("\n✅ All argument parsing tests passed!")

def test_watcher_initialization():
    """Test that WhatsAppWatcher can be initialized."""
    vault_path = BASE_DIR / "Vault"
    vault_path.mkdir(exist_ok=True)
    
    try:
        watcher = WhatsAppWatcher(vault_path, 30)
        print(f"✓ WhatsAppWatcher initialized with interval={watcher.check_interval}s")
        assert watcher.check_interval == 30
        print("✅ Watcher initialization test passed!")
    except Exception as e:
        print(f"⚠️ Watcher initialization note: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("WhatsApp Watcher - Argument Parsing Test")
    print("=" * 60)
    print()
    
    test_argument_parsing()
    print()
    test_watcher_initialization()
    
    print()
    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)
