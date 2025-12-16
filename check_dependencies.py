#!/usr/bin/env python3
"""
Check if all required dependencies are installed and compatible.
Run this script to diagnose issues on Windows or Linux.
"""

import sys
import platform

print("=" * 60)
print("Dependency Check for UPS SNMP Trap Sender")
print("=" * 60)
print(f"Platform: {platform.system()} {platform.release()}")
print(f"Python: {sys.version}")
python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
print(f"Python Version: {python_version}")
if sys.version_info < (3, 6):
    print("⚠ WARNING: Python 3.6+ recommended")
print()

# Check pysnmp
try:
    import pysnmp
    print(f"✓ pysnmp: {pysnmp.__version__} (installed)")
except ImportError:
    print("✗ pysnmp: NOT INSTALLED")
    print("  Install with: pip install pysnmp")
    sys.exit(1)

# Check pyasn1
try:
    import pyasn1
    print(f"✓ pyasn1: {pyasn1.__version__} (installed)")
except ImportError:
    print("✗ pyasn1: NOT INSTALLED")
    print("  Install with: pip install pyasn1")
    sys.exit(1)

# Check specific imports
print("\nChecking specific imports...")
try:
    from pysnmp.carrier.asyncio.dgram import udp
    print("✓ pysnmp.carrier.asyncio.dgram.udp")
except ImportError as e:
    print(f"✗ pysnmp.carrier.asyncio.dgram.udp: {e}")

try:
    from pysnmp.entity import engine, config
    print("✓ pysnmp.entity.engine, config")
except ImportError as e:
    print(f"✗ pysnmp.entity: {e}")

try:
    from pysnmp.entity.rfc3413 import ntforg
    print("✓ pysnmp.entity.rfc3413.ntforg")
except ImportError as e:
    print(f"✗ pysnmp.entity.rfc3413.ntforg: {e}")

try:
    from pysnmp.proto import rfc1902
    print("✓ pysnmp.proto.rfc1902")
except ImportError as e:
    print(f"✗ pysnmp.proto.rfc1902: {e}")

try:
    from pysnmp.proto.api import v2c as api_v2c
    print("✓ pysnmp.proto.api.v2c")
except ImportError as e:
    print(f"✗ pysnmp.proto.api.v2c: {e}")

try:
    from pysnmp.proto import rfc1905
    print("✓ pysnmp.proto.rfc1905")
except ImportError as e:
    print(f"✗ pysnmp.proto.rfc1905: {e}")

print("\n" + "=" * 60)
print("If all checks passed, you should be able to run ups_snmp_trap_sender.py")
print("=" * 60)

