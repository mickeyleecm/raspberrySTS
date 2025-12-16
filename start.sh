#!/bin/bash
#
# Start script for UPS SNMP Trap Receiver daemon
# All files (lock, PID, log) are created in the script directory
#

# Get the directory where this script is located and change to it
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Configuration - all files relative to script directory
PYTHON_SCRIPT="ups_snmp_trap_receiver_v3.py"
PID_FILE="ups_trap_receiver.pid"
# Generate log filename with current date (format: ups_trapsYYYYMMDD.log)
LOG_DATE=$(date +%Y%m%d)
LOG_FILE="logs/ups_traps${LOG_DATE}.log"
LOCK_FILE="ups_trap_receiver.lock"
PORT=162

# Default values (can be overridden by environment variables)
UPS_IP="${UPS_IP:-}"
EMAIL_CONFIG="${EMAIL_CONFIG:-email_config.json}"

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

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    print_error "python3 not found. Please install Python 3."
    exit 1
fi

# Check if script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    print_error "Python script not found: $PYTHON_SCRIPT"
    exit 1
fi

# Function to cleanup stale lock files in current directory
cleanup_stale_locks() {
    local lock_files=("$LOCK_FILE" "ups_trap_receiver.pid.lock")
    
    for lock_file in "${lock_files[@]}"; do
        if [ -f "$lock_file" ]; then
            LOCK_PID=$(cat "$lock_file" 2>/dev/null)
            if [ -n "$LOCK_PID" ]; then
                if ! ps -p "$LOCK_PID" > /dev/null 2>&1; then
                    print_warning "Removing stale lock file: $lock_file (PID: $LOCK_PID not running)"
                    rm -f "$lock_file"
                fi
            else
                print_warning "Removing invalid lock file: $lock_file (empty or invalid)"
                rm -f "$lock_file"
            fi
        fi
    done
}

# Function to acquire lock (using flock)
acquire_lock() {
    # Clean up any stale locks first
    cleanup_stale_locks
    
    # Check if lock file exists and process is running
    if [ -f "$LOCK_FILE" ]; then
        LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null)
        if [ -n "$LOCK_PID" ] && ps -p "$LOCK_PID" > /dev/null 2>&1; then
            print_error "Another start process is already running (PID: $LOCK_PID)."
            print_info "If you're sure no other process is running, remove: $LOCK_FILE"
            exit 1
        fi
    fi
    
    # Try to create and lock the lock file
    exec 200>"$LOCK_FILE"
    if ! flock -n 200; then
        print_error "Another start process is already running or lock file is held."
        print_info "If you're sure no other process is running, remove: $LOCK_FILE"
        exit 1
    fi
    # Write our PID to lock file
    echo $$ > "$LOCK_FILE"
}

# Function to release lock
release_lock() {
    flock -u 200 2>/dev/null
    exec 200>&- 2>/dev/null
    rm -f "$LOCK_FILE"
}

# Set trap to release lock on exit
trap 'release_lock' EXIT INT TERM

# Acquire lock
acquire_lock

# Check if daemon is already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$OLD_PID" ]; then
        if ps -p "$OLD_PID" > /dev/null 2>&1; then
            print_warning "Process is already running (PID: $OLD_PID)"
            print_info "Use './stop.sh' to stop it first, or remove $PID_FILE if the process is not running"
            exit 1
        else
            print_warning "Stale PID file found. Removing it..."
            rm -f "$PID_FILE"
        fi
    fi
fi

# Check if running as root (required for port 162)
if [ "$PORT" -lt 1024 ] && [ "$EUID" -ne 0 ]; then
    print_warning "Port $PORT requires root privileges."
    
    # Check if we can use sudo without password (if configured)
    if sudo -n true 2>/dev/null; then
        SUDO_CMD="sudo"
        print_info "Using sudo (passwordless - configured in sudoers)"
    elif command -v sudo > /dev/null 2>&1; then
        SUDO_CMD="sudo"
        print_warning "Attempting to start with sudo..."
        print_warning "Note: You will be prompted for your password."
        print_warning "To avoid password prompts, run: sudo ./setup_nsluser_sudo.sh"
    else
        print_error "sudo is not available, but root privileges are required for port $PORT"
        print_error "Please install sudo or run this script as root"
        exit 1
    fi
else
    SUDO_CMD=""
fi

# Build command arguments - use relative paths
ARGS=("--daemon" "--pid-file" "$PID_FILE" "--log-file" "$LOG_FILE" "--port" "$PORT")

# Add UPS IP if specified
if [ -n "$UPS_IP" ]; then
    ARGS+=("--ups-ip" "$UPS_IP")
fi

# Add email config if specified and exists
if [ -n "$EMAIL_CONFIG" ] && [ -f "$EMAIL_CONFIG" ]; then
    ARGS+=("--email-config" "$EMAIL_CONFIG")
fi

# Start the daemon
print_info "Starting UPS SNMP Trap Receiver daemon..."
print_info "  Script: $PYTHON_SCRIPT"
print_info "  Directory: $SCRIPT_DIR"
print_info "  PID file: $PID_FILE"
print_info "  Log file: $LOG_FILE"
print_info "  Port: $PORT"

if [ -n "$UPS_IP" ]; then
    print_info "  Allowed UPS IP: $UPS_IP"
fi

# Execute the command (run from script directory)
if $SUDO_CMD python3 "$PYTHON_SCRIPT" "${ARGS[@]}"; then
    # Wait for the daemon to start and write PID file
    sleep 2
    
    # Check if PID file was created
    if [ -f "$PID_FILE" ]; then
        NEW_PID=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$NEW_PID" ] && ps -p "$NEW_PID" > /dev/null 2>&1; then
            print_info "Daemon started successfully (PID: $NEW_PID)"
            print_info "PID file: $SCRIPT_DIR/$PID_FILE"
            print_info "Log file: $SCRIPT_DIR/$LOG_FILE"
            print_info "To stop the daemon, run: ./stop.sh"
            exit 0
        else
            print_error "Daemon process not found after start (PID: $NEW_PID)."
            print_error "Check $LOG_FILE for errors."
            exit 1
        fi
    else
        print_error "PID file was not created: $PID_FILE"
        print_error "Check $LOG_FILE for errors."
        exit 1
    fi
else
    print_error "Failed to start daemon. Check $LOG_FILE for errors."
    exit 1
fi
