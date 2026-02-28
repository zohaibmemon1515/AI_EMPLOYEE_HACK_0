---
name: vault-management
description: |
  Manage files in the Obsidian vault - read, write, move, and organize markdown files.
  Use for all vault file operations including task processing and documentation.
---

# Vault Management Skills

## Overview

These skills enable the AI Employee to manage files within the Obsidian vault structure.

## Folder Structure

```
Vault/
├── Dashboard.md              # Main status dashboard
├── Company_Handbook.md       # Rules and guidelines
├── Business_Goals.md         # Goals and objectives
├── Inbox/                    # Raw incoming files
├── Needs_Action/             # Pending tasks for processing
├── In_Progress/              # Tasks currently being worked on
├── Pending_Approval/         # Awaiting human decision
├── Done/                     # Completed tasks
├── Plans/                    # Multi-step task plans
├── Briefings/                # CEO briefings and reports
├── Accounting/               # Financial records
└── Updates/                  # Sync updates (Cloud tier)
```

## File Operations

### Reading Files

```bash
# Read any file in the vault
read_file "Vault/Needs_Action/TASK_123.md"
read_file "Vault/Company_Handbook.md"
read_file "Vault/Business_Goals.md"
```

### Writing Files

```bash
# Create new action file
write_file "Vault/Needs_Action/EMAIL_response.md" << 'EOF'
---
type: email
priority: high
status: pending
created: 2026-02-26T10:00:00Z
---

## Email to Process
[Content here]

## Actions
- [ ] Draft response
- [ ] Send for approval
EOF
```

### Moving Files

```bash
# Move completed task to Done
move_file "Vault/Needs_Action/completed_task.md" "Vault/Done/"

# Move task to In_Progress when starting
move_file "Vault/Needs_Action/task.md" "Vault/In_Progress/agent_name/"

# Move to Pending_Approval for human review
move_file "Vault/Needs_Action/payment_request.md" "Vault/Pending_Approval/"
```

### Updating Dashboard

```bash
# Update the Dashboard.md with current status
# 1. Read current dashboard
# 2. Update relevant sections
# 3. Write back with new timestamp
```

## Task Processing Workflow

### Step 1: Claim Task
```bash
# Move from Needs_Action to In_Progress
mv "Vault/Needs_Action/task.md" "Vault/In_Progress/ai_employee/"
```

### Step 2: Process Task
```bash
# Read the task file
# Read Company_Handbook.md for rules
# Read Business_Goals.md for context
# Take appropriate actions
```

### Step 3: Document Actions
```markdown
## Actions Taken

1. Read the task requirements
2. Checked Company Handbook for guidelines
3. Performed action: [describe]
4. Created approval request: [if applicable]

## Result
[Describe outcome]
```

### Step 4: Complete Task
```bash
# Move to Done folder
mv "Vault/In_Progress/ai_employee/task.md" "Vault/Done/"

# Update Dashboard.md
```

## Approval Request Pattern

For sensitive actions requiring human approval:

```markdown
---
type: approval_request
action: [payment/email/post]
amount: [if payment]
created: 2026-02-26T10:00:00Z
status: pending
---

## Action Required

**Action**: [Describe the action]
**Details**: [Additional context]

## To Approve
Move this file to `/Approved` folder.

## To Reject
Move this file to `/Rejected` folder with reason.
```

## Best Practices

1. **Always read Company_Handbook.md** before taking actions
2. **Log all actions** in the task file
3. **Request approval** for sensitive operations
4. **Update Dashboard.md** after processing
5. **Move files** to appropriate folders when status changes
6. **Preserve original content** when modifying files
7. **Use ISO timestamps** for all date fields

## Error Handling

- If a file cannot be processed, add an error note and move to `Needs_Action/`
- If approval is needed, create a clear approval request file
- If uncertain, flag for human review
