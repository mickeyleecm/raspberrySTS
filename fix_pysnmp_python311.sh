#!/bin/bash
#
# Fix script for Python 3.11+ compatibility issue with pysnmp
# This script removes the incompatible Debian package and installs pysnmp via pip
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run as root (use sudo)"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
print_info "Detected Python version: $PYTHON_VERSION"

# Extract major and minor version
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

# Check if Python 3.11+
if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
    print_warning "Python 3.11+ detected. The Debian python3-pysnmp4 package is incompatible."
    print_info "This script will fix the compatibility issue."
else
    print_info "Python version is below 3.11, but we'll still ensure pysnmp is properly installed."
fi

# Step 1: Check if Debian package is installed
print_info "Checking for Debian python3-pysnmp4 package..."
if dpkg -l | grep -q "^ii.*python3-pysnmp4"; then
    print_warning "Found Debian python3-pysnmp4 package (incompatible with Python 3.11+)"
    print_info "Removing python3-pysnmp4 package..."
    apt-get remove -y python3-pysnmp4 || {
        print_error "Failed to remove python3-pysnmp4 package"
        exit 1
    }
    print_info "✓ Removed python3-pysnmp4 package"
else
    print_info "✓ Debian python3-pysnmp4 package not found (or already removed)"
fi

# Step 2: Install pip3 if not available
if ! command -v pip3 &> /dev/null; then
    print_warning "pip3 not found. Installing python3-pip..."
    print_info "Updating package list..."
    apt-get update || {
        print_warning "apt-get update failed, continuing anyway..."
    }
    print_info "Installing python3-pip..."
    apt-get install -y python3-pip || {
        print_error "Failed to install python3-pip"
        print_error "Please install it manually with: sudo apt-get install python3-pip"
        exit 1
    }
    print_info "✓ Installed python3-pip"
    
    # Verify pip3 is now available
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 still not found after installation. Please check your PATH."
        exit 1
    fi
else
    print_info "✓ pip3 is available"
    PIP3_VERSION=$(pip3 --version 2>/dev/null || echo "unknown")
    print_info "  pip3 version: $PIP3_VERSION"
fi

# Step 3: Upgrade pip (with --break-system-packages if needed)
print_info "Upgrading pip..."
if pip3 install --upgrade pip --break-system-packages 2>/dev/null; then
    print_info "✓ Upgraded pip"
elif pip3 install --upgrade pip 2>/dev/null; then
    print_info "✓ Upgraded pip"
else
    print_warning "Failed to upgrade pip, continuing anyway..."
fi

# Step 4: Install pysnmp and pyasn1 via pip (with --break-system-packages flag)
print_info "Installing pysnmp and pyasn1 via pip3..."
print_warning "Using --break-system-packages flag to override externally-managed-environment protection"
if pip3 install --upgrade pysnmp pyasn1 --break-system-packages; then
    print_info "✓ Installed pysnmp and pyasn1 via pip3"
else
    print_error "Failed to install pysnmp/pyasn1 via pip3"
    print_error "If you see 'externally-managed-environment' error, this script should have handled it."
    print_error "Please check the error message above."
    exit 1
fi

# Step 5: Verify installation
print_info "Verifying pysnmp installation..."
if python3 -c "from pysnmp.carrier.asyncio.dgram import udp; print('OK')" 2>/dev/null; then
    print_info "✓ pysnmp asyncio transport works correctly!"
else
    print_error "✗ pysnmp asyncio transport still has issues"
    print_info "Trying to check what version was installed..."
    python3 -c "import pysnmp; print(f'pysnmp version: {pysnmp.__version__}')" 2>/dev/null || true
    exit 1
fi

# Step 6: Show installed version
PYSNMP_VERSION=$(python3 -c "import pysnmp; print(pysnmp.__version__)" 2>/dev/null || echo "unknown")
print_info "Installed pysnmp version: $PYSNMP_VERSION"

print_info ""
print_info "=========================================="
print_info "Fix completed successfully!"
print_info "=========================================="
print_info ""
print_info "You can now run ./start.sh to start the daemon."
print_info ""

