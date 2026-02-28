# 🤖 Personal AI Employee - Bronze Tier

> **Tagline:** Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop.

This is a **Bronze Tier** implementation of a "Personal AI Employee" hackathon project - an autonomous AI agent that acts as a Digital Full-Time Equivalent (FTE), managing personal and business affairs 24/7.

**✨ Works WITHOUT Claude Code!** Uses a local rule-based processor by default.

## Quick Start

```bash
# Install dependencies
uv sync

# Start everything with one command!
python main.py

# Or use different modes:
python main.py --once         # Run orchestrator once, then keep watcher running
python main.py --watch-only   # Just watcher, no orchestrator
python main.py --interval 60  # Custom check interval (60 seconds)

# Test imports
python test_imports.py

# Test watcher
python test_watcher.py
```

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Watchers      │────▶│   Obsidian Vault │◀────│   Local/Claude  │
│ (Python Scripts)│     │  (Memory/GUI)    │     │  (Processor)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                        │
                               ▼                        ▼
                        Markdown Files           Rules or MCP
                        - Dashboard.md           - Local (default)
                        - Needs_Action/          - Claude (optional)
                        - Done/
```

## Project Structure

```
bronze/
├── main.py                      # Entry point
├── run.py                       # Run script for watchers/orchestrator
├── orchestrator.py              # Triggers Claude to process tasks
├── pyproject.toml               # Python project config
├── watchers/
│   ├── base_watcher.py          # Abstract base class
│   ├── filesystem_watcher.py    # Monitors Inbox folder
│   └── README.md                # Watcher documentation
├── skills/
│   ├── vault-management.md      # Vault operations skill
│   ├── task-processing.md       # Task processing skill
│   └── ralph-wiggum-loop.md     # Persistence pattern
└── Vault/                       # Obsidian vault
    ├── Dashboard.md             # Main status dashboard
    ├── Company_Handbook.md      # Rules and guidelines
    ├── Business_Goals.md        # Goals and objectives
    ├── Inbox/                   # Raw incoming files
    ├── Needs_Action/            # Pending tasks
    ├── In_Progress/             # Tasks being worked on
    ├── Pending_Approval/        # Awaiting human decision
    ├── Done/                    # Completed tasks
    ├── Plans/                   # Multi-step task plans
    └── Briefings/               # Reports and briefings
```

## Features (Bronze Tier)

- ✅ **Obsidian Vault** with Dashboard, Company Handbook, and Business Goals
- ✅ **File System Watcher** monitoring Inbox folder for new files
- ✅ **Local Task Processor** - Rule-based AI (no Claude required!)
- ✅ **Orchestrator** to process tasks automatically
- ✅ **Agent Skills** documentation for future Claude integration
- ✅ **Plan Template** for multi-step tasks
- ✅ **Ralph Wiggum Loop** pattern for persistence
- ✅ **Human-in-the-Loop** approval workflow

## Usage

### 1. Drop a File in Inbox

Place any file in `Vault/Inbox/` - the File System Watcher will:
- Detect the new file
- Create an action file in `Needs_Action/`
- Move the original to `In_Progress/filesystem/`

### 2. Run the System

```bash
python main.py
```

The Local Task Processor will:
- Scan `Needs_Action/` for pending tasks
- Process each task using rules
- Move completed tasks to `Done/`
- Move approval-required tasks to `Pending_Approval/`
- Update the Dashboard

### 3. Review Results

Check:
- `Done/` folder for completed tasks
- `Pending_Approval/` for items needing your decision
- `Dashboard.md` for summary

## Commands

| Command | Description |
|---------|-------------|
| `python main.py` | **Start everything** - Watcher + Local Processor (continuous) |
| `python main.py --once` | Run processor once, then keep watcher running |
| `python main.py --watch-only` | Start watcher only, no processor |
| `python main.py --interval 60` | Custom check interval in seconds |
| `python local_processor.py` | Run local processor directly |
| `python orchestrator.py` | Run orchestrator (uses local processor by default) |
| `python test_imports.py` | Test all imports |
| `python test_watcher.py` | Test watcher startup |

## Configuration

### Watcher Settings

Edit `watchers/filesystem_watcher.py`:
```python
check_interval = 30  # Seconds between checks
```

### Priority Detection

Files are auto-classified by keywords:
- **Critical**: "urgent", "emergency", "ASAP", "critical"
- **High**: "invoice", "payment", "due", "deadline"
- **Medium**: "review", "check", "update", "reminder"
- **Low**: Everything else

## Approval Thresholds

| Action | Threshold | Required |
|--------|-----------|----------|
| Payment | > $100 | Approval |
| Payment | > $500 | **STOP** - Explicit approval |
| Email to new contact | Any | Approval |
| Social media post | Any | Approval |
| File deletion | Any | Approval |

## Hackathon Tiers

| Tier | Requirements | Status |
|------|--------------|--------|
| **Bronze** | Vault, 1 watcher, Claude integration | ✅ Complete |
| **Silver** | 2+ watchers, MCP server, HITL workflow | 🔄 Next |
| **Gold** | Full integration, Odoo, audit logging | ⏳ Future |
| **Platinum** | Cloud deployment, 24/7 operation | ⏳ Future |

## Prerequisites

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.13+ | Watcher scripts & Local Processor |
| Node.js | v24+ LTS | MCP servers (optional, for future) |
| Obsidian | v1.10.6+ | Knowledge base |

**Note:** Claude Code is **NOT required**. The system works with a local rule-based processor by default. You can optionally integrate Claude Code later for advanced reasoning.

## Resources

- [Hackathon Blueprint](./Personal%20AI%20Employee%20Hackathon%200_%20Building%20Autonomous%20FTEs%20in%202026.md)
- [Company Handbook](./Vault/Company_Handbook.md)
- [Business Goals](./Vault/Business_Goals.md)
- [Dashboard](./Vault/Dashboard.md)

## License

MIT - Part of the Q4 Governer Course Hackathon 0
