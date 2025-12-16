#!/bin/bash
#
# Update stop.sh on Raspberry Pi to fix the 'local' keyword error
# Run this on the Raspberry Pi
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STOP_SCRIPT="$SCRIPT_DIR/stop.sh"

echo "=========================================="
echo "Updating stop.sh to fix 'local' keyword error"
echo "=========================================="
echo ""

# Check if stop.sh exists
if [ ! -f "$STOP_SCRIPT" ]; then
    echo "ERROR: stop.sh not found at $STOP_SCRIPT"
    exit 1
fi

# Backup original
if [ ! -f "${STOP_SCRIPT}.backup" ]; then
    cp "$STOP_SCRIPT" "${STOP_SCRIPT}.backup"
    echo "✓ Created backup: ${STOP_SCRIPT}.backup"
fi

# Check if line 149 has the error
if grep -n "^[[:space:]]*local process_info" "$STOP_SCRIPT" | grep -v "kill_process\|find_all_pids" | grep -q "^149:"; then
    echo "Found 'local' keyword error on line 149"
    echo "Fixing..."
    
    # Fix line 149 - remove 'local' keyword
    sed -i '149s/^[[:space:]]*local process_info=/    process_info=/' "$STOP_SCRIPT"
    
    # Also add process_user line if missing
    if ! grep -A1 "process_info=" "$STOP_SCRIPT" | grep -q "process_user="; then
        # Add process_user line after process_info
        sed -i '149a\    process_user=$(ps -o user= -p "$pid" 2>/dev/null | tr -d '"'"' '"'"')' "$STOP_SCRIPT"
    fi
    
    echo "✓ Fixed line 149"
else
    echo "✓ Line 149 is already correct (no 'local' keyword)"
fi

# Verify the fix
echo ""
echo "Verifying fix..."
if grep -n "^[[:space:]]*local process_info" "$STOP_SCRIPT" | grep -v "kill_process\|find_all_pids" | grep -q "^149:"; then
    echo "✗ ERROR: Fix failed - line 149 still has 'local'"
    exit 1
else
    echo "✓ Verification passed - line 149 is correct"
fi

# Check syntax
echo ""
echo "Checking bash syntax..."
if bash -n "$STOP_SCRIPT" 2>/dev/null; then
    echo "✓ Bash syntax is valid"
else
    echo "✗ ERROR: Bash syntax check failed"
    bash -n "$STOP_SCRIPT"
    exit 1
fi

echo ""
echo "=========================================="
echo "Update completed successfully!"
echo "=========================================="
echo ""
echo "The stop.sh file has been fixed."
echo "You can now test the restart from the web interface."
echo ""

