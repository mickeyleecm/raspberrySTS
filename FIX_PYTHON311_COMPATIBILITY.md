# Fix for Python 3.11+ Compatibility Issue

## Problem

The Debian package `python3-pysnmp4` uses an older version of pysnmp that relies on deprecated `asyncio.coroutine`, which was removed in Python 3.11+. This causes the following error:

```
AttributeError: module 'asyncio' has no attribute 'coroutine'. Did you mean: 'coroutines'?
```

## Solution

The program now automatically detects this issue and provides clear instructions. However, you need to install pysnmp via pip instead of using the Debian package.

### Quick Fix

```bash
# Remove the Debian package (if installed)
sudo apt-get remove python3-pysnmp4

# Install pip3 if not already installed
sudo apt-get update
sudo apt-get install -y python3-pip

# Install via pip (this installs a newer, compatible version)
# Note: Use --break-system-packages to override externally-managed-environment protection
pip3 install --upgrade pysnmp pyasn1 --break-system-packages
```

**Notes:** 
- If `pip3` command is not found, install it first:
  ```bash
  sudo apt-get update
  sudo apt-get install -y python3-pip
  ```
- If you see `externally-managed-environment` error, use the `--break-system-packages` flag. This is safe for system-wide installations when you need to override Debian's package management protection.

### Alternative: Use Twisted Transport

If you prefer to keep the Debian package, you can install twisted for an alternative transport:

```bash
pip3 install twisted
```

The program will automatically detect and use the twisted transport if asyncio is not available.

## Verification

After installing via pip, verify the installation:

```bash
python3 -c "from pysnmp.carrier.asyncio.dgram import udp; print('OK')"
```

If this works without errors, you're good to go!

## Running the Program

After fixing the compatibility issue:

```bash
sudo python3 ups_gpio_led_controller.py --critical-pin 17 --warning-pin 17
```

## Why This Happens

- **Python 3.11+**: Removed deprecated `asyncio.coroutine` decorator
- **Debian python3-pysnmp4**: Uses old pysnmp version that still uses `asyncio.coroutine`
- **Solution**: Install newer pysnmp via pip that uses modern asyncio API

## Check Your Python Version

```bash
python3 --version
```

If you see Python 3.11 or higher, you need to use pip-installed pysnmp instead of the Debian package.

