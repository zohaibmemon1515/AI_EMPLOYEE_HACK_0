---
name: ralph-wiggum-loop
description: |
  Ralph Wiggum pattern - Keep Claude iterating until tasks are complete.
  This plugin intercepts Claude's exit and re-injects the prompt if tasks are incomplete.
---

# Ralph Wiggum Loop Plugin

## Overview

The Ralph Wiggum pattern is a stop hook that keeps Claude Code iterating until multi-step tasks are complete. It's essential for autonomous operation.

## How It Works

```
┌─────────────────────┐
│  Orchestrator       │
│  Creates state file │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Claude processes   │
│  the task           │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Claude tries to    │
│  exit               │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Stop hook checks:  │
│  Task in /Done?     │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │           │
    YES         NO
     │           │
     ▼           ▼
┌─────────┐ ┌────────────────┐
│ Allow   │ │ Block exit,    │
│ exit    │ │ re-inject      │
│ (done)  │ │ prompt (loop)  │
└─────────┘ └────────────────┘
```

## Implementation

### Option 1: File-Based Completion (Recommended)

The orchestrator checks if the task file has been moved to `/Done`:

```python
#!/usr/bin/env python3
"""
Ralph Wiggum Stop Hook - File-based completion check.

Usage:
    claude --prompt "Process tasks" | python ralph_hook.py --task-file "task.md"
"""

import sys
import time
from pathlib import Path

MAX_ITERATIONS = 10
CHECK_INTERVAL = 2  # seconds


def is_task_complete(task_name: str, done_folder: Path) -> bool:
    """Check if task has been moved to Done folder."""
    # Check if task file exists in Done folder
    done_file = done_folder / task_name
    if done_file.exists():
        return True

    # Check for any .md file containing the task name
    for f in done_folder.glob("*.md"):
        if task_name.lower() in f.name.lower():
            return True

    return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Ralph Wiggum Stop Hook")
    parser.add_argument("--task-file", required=True, help="Task file to monitor")
    parser.add_argument("--vault-path", default="../Vault", help="Vault path")
    parser.add_argument("--max-iterations", type=int, default=MAX_ITERATIONS)

    args = parser.parse_args()

    vault_path = Path(args.vault_path)
    done_folder = vault_path / "Done"
    needs_action = vault_path / "Needs_Action"

    iteration = 0

    print(f"🔄 Ralph Wiggum Loop started")
    print(f"   Task file: {args.task_file}")
    print(f"   Max iterations: {args.max_iterations}")

    while iteration < args.max_iterations:
        iteration += 1

        # Check if task is complete
        if is_task_complete(args.task_file, done_folder):
            print(f"✅ Task complete! Found in /Done folder")
            sys.exit(0)

        # Check if task still exists in Needs_Action
        task_path = needs_action / args.task_file
        if not task_path.exists():
            # Task might have been moved elsewhere
            print(f"⚠️ Task file no longer in Needs_Action")
            print(f"   Checking if moved to Done...")
            time.sleep(CHECK_INTERVAL)
            continue

        print(f"⏳ Iteration {iteration}/{args.max_iterations}")
        print(f"   Task still pending, continuing...")

        # Wait before next check
        time.sleep(CHECK_INTERVAL)

    print(f"❌ Max iterations ({args.max_iterations}) reached")
    print(f"   Task may still be incomplete")
    sys.exit(1)


if __name__ == "__main__":
    main()
```

### Option 2: Promise-Based Completion

Claude outputs a special token when complete:

```markdown
At the end of processing, Claude should output:

<promise>TASK_COMPLETE</promise>

The stop hook looks for this token to determine completion.
```

```python
def check_promise(output: str) -> bool:
    """Check if Claude output contains completion promise."""
    return "<promise>TASK_COMPLETE</promise>" in output
```

## Usage with Orchestrator

```bash
# Start processing with Ralph loop
python orchestrator.py "E:\path\to\Vault" | \
  python ralph_hook.py --task-file "task.md" --max-iterations 10
```

## Integration with Claude Code

### As a Plugin

Create `.claude/plugins/ralph-wiggum.py` in your home directory:

```python
#!/usr/bin/env python3
"""Claude Code Ralph Wiggum Plugin"""

import subprocess
import sys
from pathlib import Path

def before_exit(context):
    """Called before Claude exits."""
    vault_path = context.get("vault_path", "../Vault")
    done_folder = Path(vault_path) / "Done"

    # Check for incomplete tasks
    needs_action = Path(vault_path) / "Needs_Action"
    pending = list(needs_action.glob("*.md"))

    if pending:
        print(f"\n⚠️  {len(pending)} pending task(s) remain")
        print("   Re-injecting prompt to continue processing...")
        # Return False to prevent exit
        return False

    print("\n✅ All tasks complete, exiting...")
    return True
```

### Configuration

Add to your Claude Code configuration:

```json
{
  "plugins": {
    "ralph-wiggum": {
      "enabled": true,
      "max_iterations": 10,
      "check_interval": 2,
      "completion_check": "file_based"
    }
  }
}
```

## Best Practices

1. **Set reasonable max iterations** (5-10) to prevent infinite loops
2. **Log each iteration** for debugging
3. **Check multiple completion conditions** (file moved, status changed, etc.)
4. **Handle errors gracefully** - don't crash the loop
5. **Provide clear exit messages** so users know what happened

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Loop never exits | Check completion condition logic |
| Loop exits too early | Verify file movement is detected |
| Max iterations hit | Task may need more steps or has error |
| Task file not found | Check file naming and paths |
