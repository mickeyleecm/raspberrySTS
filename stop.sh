#!/bin/bash
#
# Stop script for UPS SNMP Trap Receiver daemon
# Kills ALL running instances of ups_snmp_trap_receiver_v3.py
# All files (PID, lock) are expected in the script directory
#

# Get the directory where this script is located and change to it
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Configuration - all files relative to script directory
PYTHON_SCRIPT="ups_snmp_trap_receiver_v3.py"
PID_FILE="ups_trap_receiver.pid"
LOCK_FILE="ups_trap_receiver.lock"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to find all PIDs running ups_snmp_trap_receiver_v3.py
find_all_pids() {
    # Find all processes matching the script name
    # Use multiple methods to ensure we catch all instances
    local pids=""
    
    # Method 1: Search for the script name in process arguments
    pids=$(ps aux | grep -i "${PYTHON_SCRIPT}" | grep -v grep | awk '{print $2}')
    
    # Method 2: Also search using pgrep if available (more reliable)
    if command -v pgrep > /dev/null 2>&1; then
        local pgrep_pids=$(pgrep -f "${PYTHON_SCRIPT}" 2>/dev/null)
        if [ -n "$pgrep_pids" ]; then
            pids="$pids $pgrep_pids"
        fi
    fi
    
    # Remove duplicates and return unique PIDs, one per line
    echo "$pids" | tr ' ' '\n' | sort -u | grep -v '^$'
}

# Function to kill a process gracefully, then forcefully if needed
kill_process() {
    local pid=$1
    
    # Verify process still exists
    if ! ps -p "$pid" > /dev/null 2>&1; then
        print_warning "  Process $pid no longer exists (may have already stopped)"
        return 0  # Not an error if already gone
    fi
    
    local process_info=$(ps -p "$pid" -o comm=,args= 2>/dev/null | head -1)
    print_info "Stopping process (PID: $pid)..."
    if [ -n "$process_info" ]; then
        print_info "  Process: $process_info"
    fi
    
    # Try graceful shutdown with SIGTERM
    if kill -TERM "$pid" 2>/dev/null; then
        # Wait for process to stop (max 10 seconds)
        local timeout=10
        local elapsed=0
        while [ $elapsed -lt $timeout ]; do
            if ! ps -p "$pid" > /dev/null 2>&1; then
                print_info "  Process $pid stopped successfully (graceful shutdown)."
                return 0
            fi
            sleep 1
            elapsed=$((elapsed + 1))
        done
        
        # If still running, try SIGKILL
        if ps -p "$pid" > /dev/null 2>&1; then
            print_warning "  Process $pid did not stop gracefully. Force killing..."
            if kill -KILL "$pid" 2>/dev/null; then
                sleep 2  # Give it a moment to die
                if ! ps -p "$pid" > /dev/null 2>&1; then
                    print_info "  Process $pid force stopped."
                    return 0
                else
                    print_error "  Failed to stop process $pid. Process may be stuck or in uninterruptible state."
                    return 1
                fi
            else
                print_error "  Failed to send SIGKILL to process $pid"
                return 1
            fi
        fi
    else
        print_warning "  Failed to send SIGTERM to process $pid (may have already stopped)"
        # Check if it's actually gone
        if ! ps -p "$pid" > /dev/null 2>&1; then
            print_info "  Process $pid is no longer running."
            return 0
        fi
        return 1
    fi
}

# Main stopping logic
print_info "Searching for all running instances of $PYTHON_SCRIPT..."

# Find all PIDs and store in array for reliable iteration
ALL_PIDS_ARRAY=()
while IFS= read -r pid; do
    if [ -n "$pid" ] && [ "$pid" -gt 0 ] 2>/dev/null; then
        ALL_PIDS_ARRAY+=("$pid")
    fi
done < <(find_all_pids)

# Check if we found any processes
if [ ${#ALL_PIDS_ARRAY[@]} -eq 0 ]; then
    print_warning "No running instances of $PYTHON_SCRIPT found."
    
    # Clean up stale files
    if [ -f "$PID_FILE" ]; then
        print_info "Removing stale PID file: $PID_FILE"
        rm -f "$PID_FILE"
    fi
    if [ -f "$LOCK_FILE" ]; then
        print_info "Removing stale lock file: $LOCK_FILE"
        rm -f "$LOCK_FILE"
    fi
    
    exit 0
fi

# Count how many processes found
PID_COUNT=${#ALL_PIDS_ARRAY[@]}
print_info "Found $PID_COUNT running instance(s) of $PYTHON_SCRIPT"

# Display all PIDs found
for pid in "${ALL_PIDS_ARRAY[@]}"; do
    process_info=$(ps -p "$pid" -o comm=,args= 2>/dev/null | head -1)
    process_user=$(ps -o user= -p "$pid" 2>/dev/null | tr -d ' ')
    print_info "  - PID $pid (User: ${process_user:-unknown}): $process_info"
done

# Kill all processes in a loop
KILLED_COUNT=0
FAILED_COUNT=0

for pid in "${ALL_PIDS_ARRAY[@]}"; do
    if kill_process "$pid"; then
        KILLED_COUNT=$((KILLED_COUNT + 1))
    else
        FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
done

# Clean up PID and lock files
if [ -f "$PID_FILE" ]; then
    print_info "Removing PID file: $PID_FILE"
    rm -f "$PID_FILE"
fi
if [ -f "$LOCK_FILE" ]; then
    print_info "Removing lock file: $LOCK_FILE"
    rm -f "$LOCK_FILE"
fi

# Summary
if [ $FAILED_COUNT -eq 0 ]; then
    print_info "Successfully stopped $KILLED_COUNT instance(s) of $PYTHON_SCRIPT"
    exit 0
else
    print_warning "Stopped $KILLED_COUNT instance(s), but $FAILED_COUNT instance(s) may still be running"
    exit 1
fi
