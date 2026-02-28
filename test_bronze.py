#!/usr/bin/env python3
"""
Test Script - Verify Bronze Tier Implementation

Run this to check that all components are in place and working.

Usage:
    python test_bronze.py
"""

import sys
from pathlib import Path


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def ok(self, message: str):
        print(f"  ✅ {message}")
        self.passed += 1

    def fail(self, message: str):
        print(f"  ❌ {message}")
        self.failed += 1

    def warn(self, message: str):
        print(f"  ⚠️  {message}")
        self.warnings += 1

    def summary(self):
        total = self.passed + self.failed
        print()
        print(f"Results: {self.passed}/{total} passed, {self.failed} failed, {self.warnings} warnings")
        return self.failed == 0


def test_directory_structure(results: TestResult, base_path: Path):
    """Test that all required directories exist."""
    print("\n📁 Testing Directory Structure...")

    required_dirs = [
        "Vault/Inbox",
        "Vault/Needs_Action",
        "Vault/Done",
        "Vault/Plans",
        "Vault/Pending_Approval",
        "Vault/Briefings",
        "Vault/Accounting",
        "Vault/In_Progress",
        "watchers",
        "skills",
    ]

    for dir_path in required_dirs:
        full_path = base_path / dir_path
        if full_path.exists() and full_path.is_dir():
            results.ok(f"Directory exists: {dir_path}")
        else:
            results.fail(f"Missing directory: {dir_path}")


def test_required_files(results: TestResult, base_path: Path):
    """Test that all required files exist."""
    print("\n📄 Testing Required Files...")

    required_files = [
        "Vault/Dashboard.md",
        "Vault/Company_Handbook.md",
        "Vault/Business_Goals.md",
        "Vault/Plans/Plan_Template.md",
        "watchers/base_watcher.py",
        "watchers/filesystem_watcher.py",
        "orchestrator.py",
        "run.py",
        "skills/vault-management.md",
        "skills/task-processing.md",
        "skills/ralph-wiggum-loop.md",
    ]

    for file_path in required_files:
        full_path = base_path / file_path
        if full_path.exists():
            results.ok(f"File exists: {file_path}")
        else:
            results.fail(f"Missing file: {file_path}")


def test_python_syntax(results: TestResult, base_path: Path):
    """Test that Python files have valid syntax."""
    print("\n🐍 Testing Python Syntax...")

    python_files = [
        "watchers/base_watcher.py",
        "watchers/filesystem_watcher.py",
        "orchestrator.py",
        "run.py",
    ]

    for file_path in python_files:
        full_path = base_path / file_path
        try:
            compile(full_path.read_text(), str(full_path), "exec")
            results.ok(f"Valid syntax: {file_path}")
        except SyntaxError as e:
            results.fail(f"Syntax error in {file_path}: {e}")


def test_dashboard_content(results: TestResult, base_path: Path):
    """Test that Dashboard.md has required sections."""
    print("\n📊 Testing Dashboard Content...")

    dashboard = base_path / "Vault/Dashboard.md"
    if not dashboard.exists():
        results.fail("Dashboard.md not found")
        return

    content = dashboard.read_text()

    required_sections = [
        "Quick Status",
        "Active Tasks",
        "Today's Activity",
        "Business Goals Progress",
    ]

    for section in required_sections:
        if section in content:
            results.ok(f"Dashboard has section: {section}")
        else:
            results.warn(f"Dashboard missing section: {section}")


def test_handbook_content(results: TestResult, base_path: Path):
    """Test that Company_Handbook.md has required sections."""
    print("\n📖 Testing Company Handbook Content...")

    handbook = base_path / "Vault/Company_Handbook.md"
    if not handbook.exists():
        results.fail("Company_Handbook.md not found")
        return

    content = handbook.read_text()

    required_sections = [
        "Core Principles",
        "Communication Rules",
        "Financial Rules",
        "Task Processing Rules",
        "Security Rules",
    ]

    for section in required_sections:
        if section in content:
            results.ok(f"Handbook has section: {section}")
        else:
            results.warn(f"Handbook missing section: {section}")


def test_watcher_implementation(results: TestResult, base_path: Path):
    """Test that watchers implement required methods."""
    print("\n👀 Testing Watcher Implementation...")

    watcher_file = base_path / "watchers/base_watcher.py"
    if not watcher_file.exists():
        results.fail("base_watcher.py not found")
        return

    content = watcher_file.read_text()

    required_methods = [
        "check_for_updates",
        "create_action_file",
        "run",
        "stop",
    ]

    for method in required_methods:
        if f"def {method}" in content:
            results.ok(f"BaseWatcher has method: {method}")
        else:
            results.fail(f"BaseWatcher missing method: {method}")


def test_bronze_tier_complete(results: TestResult, base_path: Path):
    """Test Bronze tier requirements are met."""
    print("\n🏆 Testing Bronze Tier Requirements...")

    # Requirement 1: Obsidian vault with Dashboard.md and Company_Handbook.md
    if (base_path / "Vault/Dashboard.md").exists() and \
       (base_path / "Vault/Company_Handbook.md").exists():
        results.ok("Obsidian vault with Dashboard.md and Company_Handbook.md")
    else:
        results.fail("Missing Dashboard.md or Company_Handbook.md")

    # Requirement 2: One working Watcher script
    if (base_path / "watchers/filesystem_watcher.py").exists():
        results.ok("File System Watcher script exists")
    else:
        results.fail("Missing File System Watcher")

    # Requirement 3: Local Processor (no Claude required)
    if (base_path / "local_processor.py").exists():
        results.ok("Local Task Processor exists (no Claude needed)")
    else:
        results.fail("Missing Local Task Processor")

    # Requirement 4: Basic folder structure
    folders = ["Inbox", "Needs_Action", "Done"]
    all_exist = all((base_path / "Vault" / f).exists() for f in folders)
    if all_exist:
        results.ok("Basic folder structure (Inbox, Needs_Action, Done)")
    else:
        results.fail("Missing required folders")

    # Requirement 5: Orchestrator
    if (base_path / "orchestrator.py").exists():
        results.ok("Orchestrator script for task processing")
    else:
        results.fail("Missing orchestrator.py")

    # Requirement 6: Main entry point
    if (base_path / "main.py").exists():
        results.ok("Main entry point (python main.py)")
    else:
        results.fail("Missing main.py")


def main():
    base_path = Path(__file__).parent
    results = TestResult()

    print("=" * 60)
    print("🤖 Bronze Tier Implementation Test")
    print("=" * 60)
    print(f"Testing: {base_path}")

    test_directory_structure(results, base_path)
    test_required_files(results, base_path)
    test_python_syntax(results, base_path)
    test_dashboard_content(results, base_path)
    test_handbook_content(results, base_path)
    test_watcher_implementation(results, base_path)
    test_bronze_tier_complete(results, base_path)

    print()
    print("=" * 60)
    success = results.summary()
    print("=" * 60)

    if success:
        print("\n🎉 Bronze Tier implementation is COMPLETE!")
        print("\nNext steps:")
        print("  1. Run: python run.py --orchestrator --dry-run")
        print("  2. Review the output")
        print("  3. Start watchers: python run.py --watchers")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
