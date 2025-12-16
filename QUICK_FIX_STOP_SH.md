# Quick Fix for stop.sh "local" Keyword Error

## The Error

When restarting from the web interface, you may see:
```
./stop.sh: line 149: local: can only be used in a function
```

## The Problem

Line 149 in `stop.sh` uses the `local` keyword outside of a function. The `local` keyword can only be used inside functions in bash.

## Quick Fix

### Option 1: Run the Update Script (Recommended)

On your Raspberry Pi:

```bash
cd /usr/local/src/raspberryR1e  # or raspberryRle, depending on your setup
./update_stop_sh.sh
```

This will:
- ✅ Backup the original file
- ✅ Fix line 149 (remove `local` keyword)
- ✅ Verify the fix
- ✅ Check bash syntax

### Option 2: Manual Fix

Edit `stop.sh` and find line 149. Change:

**Before (WRONG):**
```bash
for pid in "${ALL_PIDS_ARRAY[@]}"; do
    local process_info=$(ps -p "$pid" -o comm=,args= 2>/dev/null | head -1)
    print_info "  - PID $pid: $process_info"
done
```

**After (CORRECT):**
```bash
for pid in "${ALL_PIDS_ARRAY[@]}"; do
    process_info=$(ps -p "$pid" -o comm=,args= 2>/dev/null | head -1)
    process_user=$(ps -o user= -p "$pid" 2>/dev/null | tr -d ' ')
    print_info "  - PID $pid (User: ${process_user:-unknown}): $process_info"
done
```

### Option 3: Copy Fixed File

If you have the fixed version, copy it:

```bash
# On your development machine, copy to Pi
scp stop.sh nsluser@raspberrypi:/usr/local/src/raspberryR1e/

# On Pi, make sure it's executable
chmod +x /usr/local/src/raspberryR1e/stop.sh
```

## Verify the Fix

After fixing, verify:

```bash
# Check line 149
sed -n '149p' stop.sh

# Should show (without 'local'):
#     process_info=$(ps -p "$pid" -o comm=,args= 2>/dev/null | head -1)

# Check syntax
bash -n stop.sh

# Should show no errors
```

## Test

After fixing, test the restart:

```bash
./restart.sh
```

Or test from the web interface - the error should be gone!

## Note

The restart is actually working (daemon starts successfully), but this warning appears in the logs. Fixing it will clean up the output.

