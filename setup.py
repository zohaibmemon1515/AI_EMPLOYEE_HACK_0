#!/usr/bin/env python3
"""Setup script to create the Bronze tier folder structure."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
VAULT_DIR = BASE_DIR / "Vault"

# Define all directories to create
directories = [
    VAULT_DIR / "Inbox",
    VAULT_DIR / "Needs_Action",
    VAULT_DIR / "Done",
    VAULT_DIR / "Plans",
    VAULT_DIR / "Pending_Approval",
    VAULT_DIR / "Briefings",
    VAULT_DIR / "Accounting",
    VAULT_DIR / "Updates",
    VAULT_DIR / "In_Progress",
    BASE_DIR / "watchers",
    BASE_DIR / "skills",
]

for directory in directories:
    directory.mkdir(parents=True, exist_ok=True)
    print(f"✓ Created: {directory}")

print("\n✅ Folder structure created successfully!")
