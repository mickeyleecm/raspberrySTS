#!/bin/bash
#
# Quick script to check if sudoers is configured correctly
#

echo "=========================================="
echo "Checking Sudoers Configuration"
echo "=========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESTART_SCRIPT="$SCRIPT_DIR/restart.sh"
SUDOERS_FILE="/etc/sudoers.d/nsluser-raspberryrle"

echo "1. Checking if sudoers file exists..."
if [ -f "$SUDOERS_FILE" ]; then
    echo "   ✓ Found: $SUDOERS_FILE"
    echo ""
    echo "   Contents:"
    cat "$SUDOERS_FILE" | sed 's/^/      /'
    echo ""
else
    echo "   ✗ NOT FOUND: $SUDOERS_FILE"
    echo "   Run: sudo ./setup_nsluser_sudo.sh"
    echo ""
fi

echo "2. Checking sudoers syntax..."
if [ -f "$SUDOERS_FILE" ]; then
    if sudo visudo -c -f "$SUDOERS_FILE" 2>&1; then
        echo "   ✓ Syntax is valid"
    else
        echo "   ✗ Syntax is INVALID!"
    fi
    echo ""
fi

echo "3. Testing nsluser passwordless sudo..."
if sudo -u nsluser sudo -n true 2>/dev/null; then
    echo "   ✓ nsluser can use sudo without password"
else
    echo "   ✗ nsluser CANNOT use sudo without password"
    echo "   Run: sudo ./setup_nsluser_sudo.sh"
fi
echo ""

echo "4. Testing www-data can run restart.sh as nsluser..."
if sudo -u www-data sudo -n -u nsluser "$RESTART_SCRIPT" --help > /dev/null 2>&1 || \
   sudo -u www-data sudo -n -u nsluser true 2>/dev/null; then
    echo "   ✓ www-data can run commands as nsluser without password"
else
    echo "   ✗ www-data CANNOT run commands as nsluser without password"
    echo "   Run: sudo ./setup_nsluser_sudo.sh"
fi
echo ""

echo "5. Testing restart.sh detection..."
CURRENT_USER=$(whoami)
echo "   Current user: $CURRENT_USER"
if sudo -n true 2>/dev/null; then
    echo "   ✓ Current user can use sudo without password"
else
    echo "   ✗ Current user needs password for sudo"
fi
echo ""

echo "=========================================="
echo "Summary"
echo "=========================================="
echo ""
echo "If all checks pass (✓), the web interface should work."
echo "If any check fails (✗), run: sudo ./setup_nsluser_sudo.sh"
echo ""

