# Project Context: Personal AI Employee (Bronze Tier)

## Project Overview

This is a **Bronze Tier** implementation of a "Personal AI Employee" hackathon project from the Q4 Governer Course. The goal is to build an autonomous AI agent that acts as a Digital Full-Time Equivalent (FTE), managing personal and business affairs 24/7 using:

- **Claude Code** as the reasoning engine
- **Obsidian** as the knowledge base/dashboard (local Markdown vault)
- **Python** for watcher scripts (monitoring Gmail, WhatsApp, filesystems)
- **Playwright MCP** for browser automation

### Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Watchers      │────▶│   Obsidian Vault │◀────│   Claude Code   │
│ (Python Scripts)│     │  (Memory/GUI)    │     │  (Brain/Reason) │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                        │
                               ▼                        ▼
                        Markdown Files           MCP Servers (Hands)
                        - Dashboard.md           - Playwright (Browser)
                        - Needs_Action/          - Email, Calendar, etc.
                        - Done/
```

## Directory Structure

```
bronze/
├── main.py                          # Entry point (placeholder)
├── pyproject.toml                   # Python project config (UV)
├── .python-version                  # Python 3.13
├── skills-lock.json                 # Qwen skills registry
├── README.md                        # Project readme
├── Personal AI Employee Hackathon 0_*.md  # Full hackathon blueprint
├── .qwen/
│   └── skills/
│       └── browsing-with-playwright/      # Playwright MCP integration
│           ├── SKILL.md                   # Browser automation guide
│           ├── references/
│           │   └── playwright-tools.md    # Tool documentation
│           └── scripts/
│               ├── mcp-client.py          # MCP client for tool calls
│               ├── start-server.sh        # Start Playwright MCP server
│               ├── stop-server.sh         # Stop Playwright MCP server
│               └── verify.py              # Server health check
└── Vault/
    ├── Welcome.md                   # Default Obsidian note
    └── .obsidian/                   # Obsidian configuration
```

## Building and Running

### Prerequisites

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.13+ | Watcher scripts |
| Node.js | v24+ LTS | MCP servers |
| Claude Code | Active subscription | Reasoning engine |
| Obsidian | v1.10.6+ | Knowledge base |

### Setup Commands

```bash
# Install Python dependencies (UV package manager)
uv sync

# Start Playwright MCP server
bash .qwen/skills/browsing-with-playwright/scripts/start-server.sh

# Verify server is running
python3 .qwen/skills/browsing-with-playwright/scripts/verify.py

# Stop Playwright MCP server
bash .qwen/skills/browsing-with-playwright/scripts/stop-server.sh

# Run the main application
python main.py
```

### Playwright MCP Server Lifecycle

```bash
# Start (runs in background)
npx @playwright/mcp@latest --port 8808 --shared-browser-context &

# Stop (close browser + kill process)
python3 scripts/mcp-client.py call -u http://localhost:8808 -t browser_close -p '{}'
pkill -f "@playwright/mcp"
```

## Development Conventions

### Project Structure

- **Vault/**: Obsidian workspace containing all knowledge base files
  - `Needs_Action/`: Pending tasks for Claude to process
  - `Done/`: Completed tasks
  - `Dashboard.md`: Real-time status summary
  - `Company_Handbook.md`: Rules of engagement

### Watcher Pattern

All watcher scripts follow the base pattern from the hackathon blueprint:

```python
from base_watcher import BaseWatcher
from pathlib import Path

class MyWatcher(BaseWatcher):
    def check_for_updates(self) -> list:
        """Return list of new items to process"""
        pass

    def create_action_file(self, item) -> Path:
        """Create .md file in Needs_Action folder"""
        pass
```

### MCP Tool Usage

Use the `mcp-client.py` helper for browser automation:

```bash
# Navigate to URL
python3 scripts/mcp-client.py call -u http://localhost:8808 \
  -t browser_navigate -p '{"url": "https://example.com"}'

# Take accessibility snapshot (preferred over screenshots)
python3 scripts/mcp-client.py call -u http://localhost:8808 \
  -t browser_snapshot -p '{}'

# Click element
python3 scripts/mcp-client.py call -u http://localhost:8808 \
  -t browser_click -p '{"element": "Submit", "ref": "e42"}'

# Type text
python3 scripts/mcp-client.py call -u http://localhost:8808 \
  -t browser_type -p '{"element": "Search", "ref": "e15", "text": "query"}'
```

### Key Patterns

1. **Human-in-the-Loop**: For sensitive actions, create approval request files in `Pending_Approval/` instead of acting directly
2. **Ralph Wiggum Loop**: Use stop hooks to keep Claude iterating until tasks are complete
3. **Claim-by-Move**: First agent to move a task from `Needs_Action/` to `In_Progress/<agent>/` owns it

## Hackathon Tiers

| Tier | Requirements | Estimated Time |
|------|--------------|----------------|
| **Bronze** | Obsidian vault, 1 watcher, Claude reading/writing | 8-12 hours |
| **Silver** | 2+ watchers, MCP server, HITL workflow | 20-30 hours |
| **Gold** | Full integration, Odoo, audit logging, Ralph loop | 40+ hours |
| **Platinum** | Cloud deployment, 24/7 operation, A2A sync | 60+ hours |

## Resources

- **Hackathon Blueprint**: `Personal AI Employee Hackathon 0_ Building Autonomous FTEs in 2026.md`
- **Playwright Tools**: `.qwen/skills/browsing-with-playwright/references/playwright-tools.md`
- **Zoom Meetings**: Wednesdays 10:00 PM PKT (Meeting ID: 871 8870 7642)
- **YouTube**: https://www.youtube.com/@panaversity
