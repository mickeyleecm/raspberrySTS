#!/bin/bash
#
# Restart script for UPS SNMP Trap Receiver daemon
# Stops all running instances and starts a new one
# Automatically handles sudo when needed
#

# Get the directory where this script is located and change to it
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

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

# Function to check if we need sudo
check_need_sudo() {
    # Check if any running processes are owned by root
    PYTHON_SCRIPT="ups_snmp_trap_receiver_v3.py"
    PIDS=$(ps aux | grep -i "$PYTHON_SCRIPT" | grep -v grep | awk '{print $2}' 2>/dev/null)
    
    if [ -n "$PIDS" ]; then
        for pid in $PIDS; do
            PROCESS_USER=$(ps -o user= -p "$pid" 2>/dev/null | tr -d ' ')
            if [ "$PROCESS_USER" = "root" ] && [ "$EUID" -ne 0 ]; then
                return 0  # Need sudo
            fi
        done
    fi
    
    # Check if port 162 requires root (it does)
    if [ "$EUID" -ne 0 ]; then
        return 0  # Need sudo for port 162
    fi
    
    return 1  # Don't need sudo
}

# Determine if we need sudo
SUDO_CMD=""
if check_need_sudo; then
    if command -v sudo > /dev/null 2>&1; then
        # Test if we can use sudo without password (if configured)
        if sudo -n true 2>/dev/null; then
            SUDO_CMD="sudo"
            print_info "Root privileges required. Using sudo (passwordless - configured)"
        else
            # Check if we're in a non-interactive environment
            # Methods to detect non-interactive:
            # 1. No TTY attached
            # 2. Running from web server (www-data user)
            # 3. No stdin available
            IS_NON_INTERACTIVE=false
            CALLER_USER=$(whoami)
            
            if [ ! -t 0 ] || [ -z "$SSH_TTY" ]; then
                IS_NON_INTERACTIVE=true
            fi
            
            if [ "$CALLER_USER" = "www-data" ] || [ -n "$HTTP_HOST" ] || [ -n "$REQUEST_METHOD" ]; then
                IS_NON_INTERACTIVE=true
            fi
            
            # Try to detect if we're being called from PHP/expect
            PARENT_CMD=$(ps -o cmd= -p $PPID 2>/dev/null | head -1)
            if echo "$PARENT_CMD" | grep -qE "(expect|php|www-data|apache|nginx)"; then
                IS_NON_INTERACTIVE=true
            fi
            
            if [ "$IS_NON_INTERACTIVE" = true ]; then
                # Non-interactive (web, cron, etc.) - passwordless sudo MUST be configured
                print_error "=========================================="
                print_error "ERROR: Passwordless sudo is not configured!"
                print_error "=========================================="
                print_error "This script is running in a non-interactive environment"
                print_error "and cannot prompt for a password."
                print_error ""
                print_error "Current user: $CALLER_USER"
                print_error "Parent process: ${PARENT_CMD:-unknown}"
                print_error ""
                print_error "To fix this, run as root:"
                print_error "  sudo ./setup_nsluser_sudo.sh"
                print_error ""
                print_error "This will configure passwordless sudo for:"
                print_error "  - nsluser (to run stop.sh, start.sh, restart.sh)"
                print_error "  - www-data (to run restart.sh as nsluser)"
                print_error ""
                print_error "After running the setup script, the web interface"
                print_error "will be able to restart without password."
                print_error "=========================================="
                exit 1
            else
                # Interactive use - can prompt for password
                SUDO_CMD="sudo"
                print_warning "Root privileges required. Using sudo..."
                print_warning "Note: To avoid password prompts, run: sudo ./setup_nsluser_sudo.sh"
            fi
        fi
    else
        print_error "sudo is not available, but root privileges are required."
        print_error "Please install sudo or configure sudoers."
        print_error "Run as root: sudo ./setup_nsluser_sudo.sh"
        exit 1
    fi
fi

print_info "=========================================="
print_info "Restarting UPS SNMP Trap Receiver"
print_info "=========================================="
echo ""

# Step 1: Stop all running instances
print_info "Step 1: Stopping all running instances..."
STOP_SUCCESS=true
if $SUDO_CMD ./stop.sh; then
    print_info "Stop completed successfully."
else
    STOP_EXIT_CODE=$?
    print_warning "Stop completed with exit code $STOP_EXIT_CODE"
    # Check if processes are still running
    PYTHON_SCRIPT="ups_snmp_trap_receiver_v3.py"
    REMAINING_PIDS=$(ps aux | grep -i "$PYTHON_SCRIPT" | grep -v grep | awk '{print $2}' 2>/dev/null)
    if [ -n "$REMAINING_PIDS" ]; then
        print_warning "Some processes may still be running (PIDs: $REMAINING_PIDS)"
        print_warning "Attempting force kill..."
        for pid in $REMAINING_PIDS; do
            $SUDO_CMD kill -KILL "$pid" 2>/dev/null && print_info "  Force killed PID $pid" || print_error "  Failed to kill PID $pid"
        done
        sleep 1
    else
        print_info "All processes have stopped."
        STOP_SUCCESS=true
    fi
fi
echo ""

# Wait a moment for processes to fully terminate
print_info "Waiting for processes to fully terminate..."
sleep 3

# Verify no processes are still running
PYTHON_SCRIPT="ups_snmp_trap_receiver_v3.py"
REMAINING_PIDS=$(ps aux | grep -i "$PYTHON_SCRIPT" | grep -v grep | awk '{print $2}' 2>/dev/null)
if [ -n "$REMAINING_PIDS" ]; then
    print_error "Warning: Processes are still running (PIDs: $REMAINING_PIDS)"
    print_error "Attempting final force kill..."
    for pid in $REMAINING_PIDS; do
        $SUDO_CMD kill -KILL "$pid" 2>/dev/null
    done
    sleep 2
fi

# Step 2: Start the daemon
print_info "Step 2: Starting the daemon..."
if $SUDO_CMD ./start.sh; then
    print_info "=========================================="
    print_info "Restart completed successfully!"
    print_info "=========================================="
    exit 0
else
    START_EXIT_CODE=$?
    print_error "=========================================="
    print_error "Restart failed! (exit code: $START_EXIT_CODE)"
    print_error "Check the logs for details."
    print_error "=========================================="
    exit 1
fi

