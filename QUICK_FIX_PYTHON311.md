# Quick Fix for Python 3.11+ Compatibility Error

## The Problem

When running `./start.sh`, you see this error:
```
AttributeError: module 'asyncio' has no attribute 'coroutine'. Did you mean: 'coroutines'?
```

This happens because:
- **Python 3.11+** removed the deprecated `asyncio.coroutine` decorator
- **Debian's python3-pysnmp4 package** uses an old pysnmp version that still relies on it
- The two are incompatible

## Quick Solution

### Option 1: Use the Fix Script (Recommended)

```bash
sudo ./fix_pysnmp_python311.sh
```

This script will:
1. Detect your Python version
2. Remove the incompatible Debian package
3. Install pysnmp via pip (compatible version)
4. Verify the installation works

### Option 2: Manual Fix

```bash
# 1. Remove the Debian package
sudo apt-get remove python3-pysnmp4

# 2. Install pip3 if not already installed
sudo apt-get update
sudo apt-get install -y python3-pip

# 3. Install via pip (this installs a newer, compatible version)
# Note: Use --break-system-packages to override externally-managed-environment protection
pip3 install --upgrade pysnmp pyasn1 --break-system-packages

# 4. Verify it works
python3 -c "from pysnmp.carrier.asyncio.dgram import udp; print('OK')"
```

**Note:** 
- If `pip3` is not found, install it first with:
  ```bash
  sudo apt-get update
  sudo apt-get install -y python3-pip
  ```
- If you see `externally-managed-environment` error, use the `--break-system-packages` flag as shown above.

## Verify the Fix

After running the fix, verify it works:

```bash
# Check pysnmp installation
python3 check_pysnmp.py

# Or test the import directly
python3 -c "from pysnmp.carrier.asyncio.dgram import udp; print('✓ OK')"
```

## Start the Daemon

Once fixed, you can start the daemon:

```bash
sudo ./start.sh
```

## Why This Happens

- **Python 3.8**: `asyncio.coroutine` was deprecated
- **Python 3.11+**: `asyncio.coroutine` was completely removed
- **Debian python3-pysnmp4**: Still uses old code with `@asyncio.coroutine`
- **Solution**: Install newer pysnmp via pip that uses modern `async def` syntax

## Check Your Python Version

```bash
python3 --version
```

If you see Python 3.11 or higher, you need to use pip-installed pysnmp instead of the Debian package.

