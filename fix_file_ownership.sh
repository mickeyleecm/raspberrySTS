#!/bin/bash
#
# Fix file ownership for restart scripts
# Should be run as root
#

if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root (or with sudo)"
    echo "Please run: sudo ./fix_file_ownership.sh"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

echo "=========================================="
echo "Fixing File Ownership"
echo "=========================================="
echo ""

# Check if nsluser exists
if ! id "nsluser" &>/dev/null; then
    echo "ERROR: nsluser does not exist"
    echo "Please create the user first or check the username"
    exit 1
fi

echo "Setting ownership to nsluser:nsluser for:"
echo "  - stop.sh"
echo "  - start.sh"
echo "  - restart.sh"
echo ""

chown nsluser:nsluser stop.sh start.sh restart.sh 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✓ Ownership changed successfully"
    echo ""
    echo "Current ownership:"
    ls -l stop.sh start.sh restart.sh | awk '{print $3, $4, $9}'
else
    echo "✗ Failed to change ownership"
    exit 1
fi

echo ""
echo "=========================================="
echo "Done!"
echo "=========================================="

