#!/bin/bash
#
# Setup script to configure sudoers for nsluser
# This allows nsluser to run stop.sh, start.sh, and restart.sh without password
#
# IMPORTANT: This script must be run as root (or with sudo)
#

if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root (or with sudo)"
    echo "Please run: sudo ./setup_nsluser_sudo.sh"
    exit 1
fi

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STOP_SCRIPT="$SCRIPT_DIR/stop.sh"
START_SCRIPT="$SCRIPT_DIR/start.sh"
RESTART_SCRIPT="$SCRIPT_DIR/restart.sh"

echo "=========================================="
echo "Setting up sudoers for nsluser"
echo "=========================================="
echo ""

# Verify scripts exist
if [ ! -f "$STOP_SCRIPT" ]; then
    echo "ERROR: stop.sh not found at $STOP_SCRIPT"
    exit 1
fi

if [ ! -f "$START_SCRIPT" ]; then
    echo "ERROR: start.sh not found at $START_SCRIPT"
    exit 1
fi

if [ ! -f "$RESTART_SCRIPT" ]; then
    echo "ERROR: restart.sh not found at $RESTART_SCRIPT"
    exit 1
fi

echo "Scripts found:"
echo "  - $STOP_SCRIPT"
echo "  - $START_SCRIPT"
echo "  - $RESTART_SCRIPT"
echo ""

# Make scripts executable
chmod +x "$STOP_SCRIPT" "$START_SCRIPT" "$RESTART_SCRIPT"
echo "✓ Made scripts executable"

# Set correct ownership (nsluser should own the scripts)
if id "nsluser" &>/dev/null; then
    chown nsluser:nsluser "$STOP_SCRIPT" "$START_SCRIPT" "$RESTART_SCRIPT" 2>/dev/null
    echo "✓ Set ownership to nsluser:nsluser"
else
    echo "⚠ Warning: nsluser does not exist, skipping ownership change"
fi
echo ""

# Create sudoers file
SUDOERS_FILE="/etc/sudoers.d/nsluser-raspberryrle"
echo "Creating sudoers file: $SUDOERS_FILE"
echo ""

cat > "$SUDOERS_FILE" <<EOF
# Allow nsluser to run UPS trap receiver management scripts without password
# This is required because the daemon runs as root (port 162 requires root)
nsluser ALL=(ALL) NOPASSWD: $STOP_SCRIPT
nsluser ALL=(ALL) NOPASSWD: $START_SCRIPT
nsluser ALL=(ALL) NOPASSWD: $RESTART_SCRIPT

# Allow www-data to run restart.sh as nsluser without password
# This is required for web interface restart functionality
# Note: restart.sh changes to its own directory, so absolute path works
www-data ALL=(nsluser) NOPASSWD: $RESTART_SCRIPT
EOF

# Set correct permissions
chmod 0440 "$SUDOERS_FILE"
echo "✓ Created sudoers file with correct permissions"
echo ""

# Verify syntax
echo "Verifying sudoers syntax..."
if visudo -c -f "$SUDOERS_FILE" 2>/dev/null; then
    echo "✓ Sudoers syntax is valid"
else
    echo "ERROR: Sudoers syntax is invalid!"
    echo "Removing invalid file..."
    rm -f "$SUDOERS_FILE"
    exit 1
fi
echo ""

# Test if nsluser can run the scripts
echo "Testing sudo configuration..."
if sudo -u nsluser sudo "$STOP_SCRIPT" --help > /dev/null 2>&1 || sudo -u nsluser sudo -n "$STOP_SCRIPT" 2>&1 | grep -q "running instances"; then
    echo "✓ Sudo configuration works!"
else
    echo "⚠ Warning: Could not verify sudo configuration automatically"
    echo "  You can test manually with: sudo -u nsluser sudo $STOP_SCRIPT"
fi
echo ""

echo "=========================================="
echo "Setup completed!"
echo "=========================================="
echo ""
echo "✓ nsluser can now run these commands without password:"
echo "    sudo $STOP_SCRIPT"
echo "    sudo $START_SCRIPT"
echo "    sudo $RESTART_SCRIPT"
echo ""
echo "✓ www-data can now run restart.sh as nsluser (for web interface):"
echo "    sudo -u nsluser $RESTART_SCRIPT"
echo ""
echo "✓ nsluser can simply run:"
echo "    ./restart.sh  (will use sudo automatically)"
echo ""
echo "✓ Web interface can now restart without password!"
echo ""



