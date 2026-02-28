---
name: task-processing
description: |
  Process tasks from the Needs_Action folder - classify, plan, execute, and document.
  Use for handling emails, files, requests, and other actionable items.
---

# Task Processing Skills

## Overview

These skills enable the AI Employee to process tasks systematically following the Company Handbook guidelines.

## Task Classification

### Priority Levels

| Priority | Response Time | Examples |
|----------|---------------|----------|
| **Critical** | Immediate | System down, security issue, emergency |
| **High** | 4 hours | Client inquiry, invoice due, urgent request |
| **Medium** | 24 hours | General inquiry, task assignment |
| **Low** | 48 hours | FYI items, newsletters |

### Task Types

1. **email** - Email messages requiring response
2. **whatsapp** - WhatsApp messages requiring response
3. **file_drop** - Files dropped for processing
4. **payment** - Payment/invoice processing
5. **task** - General task assignment
6. **approval_request** - Awaiting human decision
7. **social_media** - Social media posts/scheduling

## Processing Steps

### Step 1: Read and Understand

```markdown
1. Read the task file completely
2. Identify the task type and priority
3. Note any deadlines or time-sensitive elements
4. Check for attachments or referenced files
```

### Step 2: Check Guidelines

```markdown
1. Read Company_Handbook.md for relevant rules
2. Check Business_Goals.md for alignment
3. Verify you have permission for required actions
4. Identify if approval is needed
```

### Step 3: Plan Actions

```markdown
1. List all required actions
2. Order actions logically
3. Identify dependencies
4. Estimate time required
```

### Step 4: Execute Actions

```markdown
1. Take actions within your permissions
2. For restricted actions, create approval request
3. Document each action as you go
4. Handle errors gracefully
```

### Step 5: Document and Close

```markdown
1. Summarize actions taken
2. Note any follow-up needed
3. Update task status to "completed"
4. Move file to appropriate folder
```

## Action Templates

### Email Response

```markdown
## Actions Taken

1. Read email from [sender]
2. Identified request: [summary]
3. Checked Company Handbook for guidelines
4. Drafted response: [summary]
5. [Sent/Saved for approval]

## Response Draft

[Draft content here]

## Status
- [x] Email processed
- [x] Response drafted
- [ ] Awaiting approval / Sent
```

### File Processing

```markdown
## Actions Taken

1. Received file: [filename]
2. File type: [type]
3. Content summary: [brief summary]
4. Extracted actions: [list]
5. Filed in: [destination]

## Extracted Information

[Key information from file]

## Status
- [x] File processed
- [x] Information extracted
- [x] Filed appropriately
```

### Payment Request

```markdown
## Actions Taken

1. Received payment request
2. Amount: $[amount]
3. Vendor: [vendor name]
4. Due date: [date]

## Approval Required

⚠️ **Payment requires human approval**

Created approval request: `Pending_Approval/PAYMENT_[vendor]_[date].md`

## Status
- [x] Payment request logged
- [x] Approval request created
- [ ] Awaiting human approval
```

## Approval Thresholds

| Action | Threshold | Required |
|--------|-----------|----------|
| Payment | > $100 | Approval |
| Payment | > $500 | **STOP** - Explicit approval |
| Email to new contact | Any | Approval |
| Social media post | Any | Approval |
| File deletion | Any | Approval |
| System config change | Any | Approval |

## Error Handling

### If Task is Unclear

```markdown
## Issue: Unclear Task

The task requirements are not clear. 

**What I understood**: [your understanding]
**What's unclear**: [specific questions]

**Action**: Flagged for human clarification
```

### If Missing Information

```markdown
## Issue: Missing Information

Required information is missing:
- [item 1]
- [item 2]

**Action**: Created follow-up request
```

### If Action Fails

```markdown
## Issue: Action Failed

**Attempted**: [action]
**Error**: [error message]
**Retry**: [yes/no, attempts]

**Action**: [escalated / noted for review]
```

## Quality Checklist

Before marking a task complete:

- [ ] All required actions taken
- [ ] Actions documented clearly
- [ ] Approval obtained where needed
- [ ] File moved to correct folder
- [ ] Dashboard updated (if applicable)
- [ ] Follow-up items noted
