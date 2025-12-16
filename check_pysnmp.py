#!/usr/bin/env python3
"""Quick diagnostic script to check pysnmp installation."""

import sys

print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print()

# Check if pysnmp is installed
try:
    import pysnmp
    print(f"✓ pysnmp is installed")
    try:
        print(f"  Version: {pysnmp.__version__}")
    except:
        print(f"  Version: unknown")
except ImportError as e:
    print(f"✗ pysnmp is NOT installed")
    print(f"  Error: {e}")
    sys.exit(1)

print()

# Check if hlapi can be imported
try:
    from pysnmp.hlapi import SnmpEngine, CommunityData, UdpTransportTarget
    print(f"✓ pysnmp.hlapi can be imported")
except ImportError as e:
    print(f"✗ pysnmp.hlapi CANNOT be imported")
    print(f"  Error: {e}")
    sys.exit(1)

print()

# Check all required imports
required_imports = [
    'SnmpEngine',
    'CommunityData', 
    'UdpTransportTarget',
    'ContextData',
    'ObjectType',
    'ObjectIdentity',
    'getCmd'
]

print("Checking required imports:")
all_ok = True
for imp in required_imports:
    try:
        exec(f"from pysnmp.hlapi import {imp}")
        print(f"  ✓ {imp}")
    except ImportError as e:
        print(f"  ✗ {imp} - {e}")
        all_ok = False

if all_ok:
    print("\n✓ All imports successful! pysnmp is ready to use.")
else:
    print("\n✗ Some imports failed. pysnmp may need to be reinstalled.")
    sys.exit(1)

print()

# Check asyncio transport (required for trap receiver)
print("Checking asyncio transport (required for trap receiver):")
try:
    from pysnmp.carrier.asyncio.dgram import udp
    print("  ✓ pysnmp.carrier.asyncio.dgram.udp can be imported")
    print("\n✓ All checks passed! pysnmp is fully compatible.")
except AttributeError as e:
    if "coroutine" in str(e).lower():
        print("  ✗ Python 3.11+ compatibility issue detected!")
        print(f"  Error: {e}")
        print("\n  This is a known issue with Debian's python3-pysnmp4 package.")
        print("  Solution: Run './fix_pysnmp_python311.sh' to fix this issue.")
        print("  Or manually:")
        print("    1. sudo apt-get remove python3-pysnmp4")
        print("    2. pip3 install --upgrade pysnmp pyasn1")
        sys.exit(1)
except ImportError as e:
    print(f"  ✗ Cannot import asyncio transport: {e}")
    print("\n  This may indicate a compatibility issue.")
    sys.exit(1)
except Exception as e:
    print(f"  ✗ Unexpected error: {e}")
    sys.exit(1)

