#!/usr/bin/env python3
"""Move test draft to Approved folder."""
import shutil
from pathlib import Path

base_dir = Path(__file__).parent
src = base_dir / "Vault" / "Pending_Approval" / "EMAIL_REPLY_TEST.md"
dst = base_dir / "Vault" / "Approved" / "EMAIL_REPLY_TEST.md"

if src.exists():
    shutil.move(str(src), str(dst))
    print(f"✅ Moved {src.name} to Approved/")
    print(f"   Orchestrator will detect it within 5 seconds!")
else:
    print(f"❌ File not found: {src}")
