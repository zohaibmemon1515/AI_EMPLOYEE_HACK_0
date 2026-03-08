# Gold Tier Quick Start Guide

## Overview

This guide helps you quickly set up and run the Gold Tier AI Employee system.

## Prerequisites

- Python 3.13+
- Node.js v20+
- Git

## Installation

### 1. Install Python Dependencies

```bash
# Using UV (recommended)
uv sync

# Or using pip
pip install -e .
```

### 2. Install Node.js Dependencies

```bash
npm install
```

### 3. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
# For Odoo Accounting (optional)
ODOO_BASE_URL=http://localhost:8069
ODOO_DB_NAME=odoo
ODOO_USERNAME=admin
ODOO_PASSWORD=your_password

# For Facebook (optional)
FACEBOOK_PAGE_ACCESS_TOKEN=your_token
FACEBOOK_PAGE_ID=your_page_id

# For Instagram (optional)
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_id
INSTAGRAM_ACCESS_TOKEN=your_token

# For Twitter (optional)
TWITTER_API_KEY=your_key
TWITTER_API_SECRET=your_secret
TWITTER_ACCESS_TOKEN=your_token
TWITTER_ACCESS_TOKEN_SECRET=your_secret
```

## Running the System

### Option 1: Silver Tier Only (Existing)

```bash
python main.py
```

This runs the existing Silver Tier system (Gmail + WhatsApp) without any Gold Tier features.

### Option 2: Silver + Gold Tier

```bash
# Start Silver Tier
python main.py

# In another terminal, start Gold Tier
python gold_tier_integration.py --start
```

### Option 3: Individual Gold Tier Components

```bash
# Ralph Loop (autonomous task processing)
python -m modules.planning.ralph_loop --continuous

# Planner Agent
python -m modules.planning.planner_agent --prioritize

# CEO Briefing Generator
python -m modules.reporting.ceo_briefing --generate

# Weekly Audit
python -m modules.reporting.weekly_audit --run

# Social Scheduler
python -m modules.social.social_scheduler --process

# Social Summary
python -m modules.social.social_summary --weekly
```

### Option 4: MCP Servers

```bash
# Accounting MCP Server
node mcp_servers/accounting_mcp_server.js --port 8811

# Social MCP Server
node mcp_servers/social_mcp_server.js --port 8812
```

## Module Testing

### Test Accounting Module

```bash
# Test Odoo connection
python -m modules.accounting.odoo_client --test

# Run accounting audit
python -m modules.accounting.accounting_audit --quick

# Sync invoices
python -m modules.accounting.invoice_sync --status
```

### Test Social Media Modules

```bash
# Facebook
python -m modules.social.facebook_agent --info

# Instagram
python -m modules.social.instagram_agent --info

# Twitter
python -m modules.social.twitter_agent --info

# Social Scheduler
python -m modules.social.social_scheduler --stats
```

### Test Planning Modules

```bash
# Ralph Loop
python -m modules.planning.ralph_loop --status

# Planner Agent
python -m modules.planning.planner_agent --list

# Task Executor
python -m modules.planning.task_executor --recent
```

### Test Reporting Modules

```bash
# CEO Briefing
python -m modules.reporting.ceo_briefing --generate

# Weekly Audit
python -m modules.reporting.weekly_audit --run
```

### Test Skills Framework

```python
from modules.skills import (
    CommunicationSkill,
    AccountingSkill,
    MarketingSkill,
    PlanningSkill
)

# Test Communication
comm = CommunicationSkill()
print(comm.available_actions)

# Test Accounting
acct = AccountingSkill()
print(acct.available_actions)

# Test Marketing
marketing = MarketingSkill()
result = marketing.generate_post("educational", "AI Tips")
print(result.result)

# Test Planning
planning = PlanningSkill()
result = planning.analyze_tasks()
print(result.result)
```

## Folder Structure

```
Gold/
├── modules/
│   ├── accounting/      # Odoo integration, invoices, audit
│   ├── social/          # Facebook, Instagram, Twitter agents
│   ├── planning/        # Ralph Loop, planner, executor
│   ├── reporting/       # CEO briefing, weekly audit
│   └── skills/          # Agent skills framework
├── mcp_servers/
│   ├── accounting_mcp_server.js
│   └── social_mcp_server.js
├── utils/
│   └── audit_logger.py  # Centralized logging
├── Vault/
│   ├── CEO_Briefings/   # Weekly CEO reports
│   ├── Audits/          # Weekly audit reports
│   ├── Social_Media/
│   │   ├── Scheduled/
│   │   ├── Published/
│   │   └── Reports/
│   ├── Invoice_Sync/
│   │   ├── Incoming/
│   │   ├── Processed/
│   │   └── Export/
│   └── Logs/            # All activity logs
└── gold_tier_integration.py
```

## Common Workflows

### Lead-to-Invoice Automation

1. Lead arrives via WhatsApp → `Needs_Action/`
2. Ralph Loop detects and processes:
   - Classifies lead
   - Creates CRM entry
   - Generates proposal
   - Creates invoice
   - Sends follow-up
3. All actions logged to `Vault/Logs/`

### Weekly Reporting

1. Every Monday at 9 AM:
   ```bash
   python -m modules.reporting.weekly_audit --run
   python -m modules.reporting.ceo_briefing --generate
   ```

2. Or use Gold Tier integration:
   ```bash
   python gold_tier_integration.py --weekly
   ```

### Social Media Posting

1. Generate content:
   ```bash
   python -m modules.social.social_scheduler --plan
   ```

2. Schedule posts:
   ```python
   from modules.social.social_scheduler import SocialScheduler
   scheduler = SocialScheduler()
   scheduler.schedule_post("facebook", "Content here", scheduled_time=...)
   ```

3. Process scheduled posts:
   ```bash
   python -m modules.social.social_scheduler --process
   ```

## Troubleshooting

### Odoo Connection Failed

```bash
# Check Odoo is running
curl http://localhost:8069

# Verify credentials
python -m modules.accounting.odoo_client --test
```

### Social Media Not Configured

Check `.env` file has correct tokens:
```bash
FACEBOOK_PAGE_ACCESS_TOKEN=...
INSTAGRAM_BUSINESS_ACCOUNT_ID=...
TWITTER_BEARER_TOKEN=...
```

### Ralph Loop Not Processing Tasks

```bash
# Check for pending tasks
python -m modules.planning.planner_agent --list

# Run single cycle manually
python -m modules.planning.ralph_loop --run
```

### MCP Server Not Responding

```bash
# Check if port is in use
netstat -an | grep 8811  # Accounting
netstat -an | grep 8812  # Social

# Restart server
node mcp_servers/accounting_mcp_server.js --port 8811
```

## Next Steps

1. **Configure Odoo**: Set up Odoo Community Edition for accounting
2. **Connect Social Accounts**: Get API tokens from Facebook, Instagram, Twitter
3. **Customize Skills**: Extend Agent Skills for your specific needs
4. **Set Up Scheduling**: Configure cron jobs or Task Scheduler for weekly reports

## Resources

- Full Documentation: `GOLD_TIER_DOCUMENTATION.md`
- Hackathon Blueprint: `Personal AI Employee Hackathon 0_ Building Autonomous FTEs in 2026.md`
- Silver Tier Docs: `QUICKSTART.md`

---

*For support, refer to the documentation or check logs in `Vault/Logs/`*
