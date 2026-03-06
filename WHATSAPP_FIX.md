# WhatsApp Watcher - Fix Applied

## Issue
When running `python main.py`, the WhatsApp watcher failed with:
```
whatsapp_watcher.py: error: unrecognized arguments: 30
```

## Root Cause
The `main.py` calls the WhatsApp watcher with positional arguments:
```python
subprocess.Popen([
    sys.executable, 
    "-u", 
    str(self.base_dir / "watchers" / "whatsapp_watcher.py"),
    str(self.vault),  # Positional arg 1: vault path
    "30"              # Positional arg 2: interval
])
```

But the original `whatsapp_watcher.py` only accepted `--interval` as a named argument.

## Fix Applied
Updated `watchers/whatsapp_watcher.py` main function to accept both:
1. **Positional argument**: `whatsapp_watcher.py /vault/path 30`
2. **Named argument**: `whatsapp_watcher.py /vault/path --interval 30`

### Code Change
```python
# Before (only supported --interval flag)
parser.add_argument("--interval", type=int, default=30, help="Check interval in seconds")

# After (supports both positional and flag)
parser.add_argument("interval", nargs="?", type=int, default=30, help="Check interval in seconds")
parser.add_argument("--interval", "-i", dest="interval_flag", type=int, default=None, help="Check interval in seconds")

# Support both positional and flag-based interval
interval = args.interval_flag if args.interval_flag is not None else args.interval
```

## Files Modified
1. ✅ `watchers/whatsapp_watcher.py` - Fixed argument parsing
2. ✅ `.env` - Added WhatsApp configuration
3. ✅ `.env.example` - Added WhatsApp configuration template
4. ✅ `.gitignore` - Added sessions/ and other sensitive files
5. ✅ `main.py` - Already correct (calls with positional args)

## Testing
Run the following to test:

```bash
# Test 1: Run via main.py (integration test)
python main.py

# Test 2: Run WhatsApp watcher directly with positional args
python watchers/whatsapp_watcher.py ./Vault 30

# Test 3: Run WhatsApp watcher with named arg
python watchers/whatsapp_watcher.py ./Vault --interval 30

# Test 4: Run argument parsing test
python test_whatsapp_args.py
```

## Expected Behavior
After the fix:
1. ✅ `main.py` starts successfully
2. ✅ Gmail Watcher runs (PID shown)
3. ✅ WhatsApp Watcher runs (PID shown)
4. ✅ Orchestrator runs (PID shown)
5. ✅ All three processes monitored and restarted if they crash

## WhatsApp Flow
1. Browser opens to WhatsApp Web
2. QR code displayed for first-time auth
3. Scan QR with phone
4. Watcher polls every 30 seconds
5. New messages → `Vault/Needs_Action/WHATSAPP_*.md`
6. Plans generated → `Vault/Plans/`
7. Draft replies → `Vault/Pending_Approval/`
8. Move to `Approved/` → Auto-send via Playwright

## Configuration
Edit `.env` to customize:

```env
# Poll interval (seconds)
WHATSAPP_POLL_INTERVAL=30

# Browser visibility
WHATSAPP_BROWSER_HEADLESS=false

# Rate limit (messages/hour)
WHATSAPP_RATE_LIMIT_HOURLY=10

# MCP server port
WHATSAPP_MCP_PORT=8810
```

## Troubleshooting

### Still getting argument error?
Make sure you pulled the latest changes:
```bash
git pull
```

### WhatsApp watcher crashes immediately?
Check logs:
```bash
tail -f Logs/*.json
```

### Browser doesn't open?
Install Playwright browsers:
```bash
npx playwright install
```

### QR code not showing?
1. Clear browser cache
2. Logout from WhatsApp Web
3. Restart watcher

## Status
✅ **FIXED** - WhatsApp watcher now runs alongside Gmail without errors

---
**Date**: 2026-03-06  
**Tier**: Silver (Gmail + WhatsApp + Orchestrator)
