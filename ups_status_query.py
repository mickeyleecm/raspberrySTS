#!/usr/bin/env python3
"""
UPS/ATS/i-STS Status Query Tool
Queries UPS, ATS (Automatic Transfer Switch), or i-STS (Static Transfer Switch) device status via SNMP and displays comprehensive information.

This tool queries the following device status information:

For UPS devices:
1. UPS Identification Information
2. Battery Status and Health
3. Input Power Monitoring
4. Output Power Status
5. Three-Phase UPS Support (Enterprise Grade)

For ATS devices (Borri STS32A):
MIB File: ATS_Stork_V1_05 - Borri STS32A.MIB
NOTE: Device firmware uses atsAgent(2), not atsAgent(3) as in MIB v1.05
Base OID: 1.3.6.1.4.1.37662.1.2.2.1.1 (atsObjectGroup with atsAgent=2)
sysObjectID: 1.3.6.1.4.1.37662.1.2.2.1 (confirmed from device)
1. ATS Identification Information (atsIdentGroup)
2. Input Power Status - Source A and Source B (atsInputGroup)
3. Output Power Status (atsOutputGroup)
4. HMI and Switch Settings (atsHmiSwitchGroup)
5. Miscellaneous Information (atsMiscellaneousGroup)

For i-STS devices:
MIB File: i-STS snmp-mib.mib
Base OID: 43.6.1.4.1.32796 (ISTS enterprise OID)
1. Product Information
2. Control/Operation Status
3. Input Power Status
4. Output Power Status
5. Alarm Status
6. Utilisation/Statistics

Supports full SNMP tree walking to discover all available OIDs.

Uses SNMPv2c protocol for all queries.

Requires: Python 3.6+, pysnmp>=4.4.12, pyasn1>=0.4.8
"""

import sys
import argparse
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple

# Check Python version
if sys.version_info < (3, 6):
    print(f"ERROR: Python 3.6+ required, but you have {sys.version_info.major}.{sys.version_info.minor}", file=sys.stderr)
    sys.exit(1)

try:
    # Try pysnmp hlapi first (works for both 4.x and 7.x, better for WALK operations)
    try:
        from pysnmp.hlapi import (
            SnmpEngine, CommunityData, UdpTransportTarget,
            ContextData, ObjectType, ObjectIdentity, getCmd, nextCmd
        )
        USE_ENTITY_API = False
        USE_V1ARCH = False
        USE_HLAPI = True
    except ImportError:
        # Fallback to entity API
        from pysnmp.entity import engine, config
        from pysnmp.entity.rfc3413 import cmdrsp
        from pysnmp.proto import rfc1902
        from pysnmp.carrier.asyncio.dgram import udp
        from pysnmp import error
        USE_ENTITY_API = True
        USE_V1ARCH = False
        USE_HLAPI = False
except ImportError as e:
    USE_ENTITY_API = False
    USE_V1ARCH = False
    USE_HLAPI = False
    raise e
except ImportError as e:
    import sys
    print(f"\n{'='*70}", file=sys.stderr)
    print(f"ERROR: Failed to import pysnmp", file=sys.stderr)
    print(f"{'='*70}", file=sys.stderr)
    print(f"Error details: {e}", file=sys.stderr)
    print(f"\nPython version: {sys.version}", file=sys.stderr)
    print(f"Python executable: {sys.executable}", file=sys.stderr)
    print(f"\nTo fix this issue, install pysnmp and its dependencies:", file=sys.stderr)
    print(f"  python -m pip install pysnmp pyasn1", file=sys.stderr)
    print(f"\nOr if using pip3:", file=sys.stderr)
    print(f"  pip3 install pysnmp pyasn1", file=sys.stderr)
    print(f"\nNote: Make sure you're installing to the correct Python environment!", file=sys.stderr)
    print(f"{'='*70}\n", file=sys.stderr)
    sys.exit(1)

# Try to load config from config.py
try:
    import importlib.util
    config_path = Path(__file__).parent / 'config.py'
    if config_path.exists():
        spec = importlib.util.spec_from_file_location("ups_config", config_path)
        ups_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ups_config)
        DEFAULT_UPS_IP = getattr(ups_config, 'UPS_IP', '192.168.111.173')
    else:
        DEFAULT_UPS_IP = '192.168.111.173'  # Borri STS32A default IP
except Exception:
    DEFAULT_UPS_IP = '192.168.111.173'  # Borri STS32A default IP

# SNMP Community String (default is 'public')
DEFAULT_COMMUNITY = 'public'
DEFAULT_PORT = 161

# UPS-MIB OID Definitions (RFC 1628 and SMAP extensions)
# Based on SMAP SNMP R1e.mib and RFC 1628 UPS-MIB

# ATS-MIB OID Definitions (ATS_Stork_V1_05 - Borri STS32A.MIB)
# Base OID: 1.3.6.1.4.1.37662 (ats)
# atsObjectGroup = 1.3.6.1.4.1.37662.1.2.3.1.1

# 1. UPS Identification Information (1.3.6.1.2.1.33.1.1.x)
UPS_IDENT_OIDS = {
    'upsIdentModel': '1.3.6.1.2.1.33.1.1.1.0',           # Model Name
    'upsIdentUPSName': '1.3.6.1.2.1.33.1.1.2.0',         # UPS Name (8-byte identifier)
    'upsIdentFirmwareRevision': '1.3.6.1.2.1.33.1.1.3.0', # Firmware Revision
    'upsIdentDateOfManufacture': '1.3.6.1.2.1.33.1.1.4.0', # Date of Manufacture (mm/dd/yy)
    'upsIdentSerialNumber': '1.3.6.1.2.1.33.1.1.5.0',     # Serial Number
    'upsIdentAgentFirmwareRevision': '1.3.6.1.2.1.33.1.1.6.0', # Agent Firmware Revision
}

# SMAP-specific identification OIDs (from SMAP SNMP R1e.mib)
# Base path: 1.3.6.1.4.1.935.1.1.1.1 (upsIdentp)
# upsBaseIdent = { upsIdentp 1 } = 1.3.6.1.4.1.935.1.1.1.1.1
# upsSmartIdent = { upsIdentp 2 } = 1.3.6.1.4.1.935.1.1.1.1.2
SMAP_IDENT_OIDS = {
    'upsBaseIdentModel': '1.3.6.1.4.1.935.1.1.1.1.1.1.0',      # Model Name (upsBaseIdent 1)
    'upsBaseIdentUpsName': '1.3.6.1.4.1.935.1.1.1.1.1.2.0',    # UPS Name (upsBaseIdent 2)
    'upsSmartIdentFirmwareRevision': '1.3.6.1.4.1.935.1.1.1.1.2.1.0', # Firmware Revision (upsSmartIdent 1)
    'upsSmartIdentDateOfManufacture': '1.3.6.1.4.1.935.1.1.1.1.2.2.0', # Date of Manufacture (upsSmartIdent 2)
    'upsSmartIdentUpsSerialNumber': '1.3.6.1.4.1.935.1.1.1.1.2.3.0', # Serial Number (upsSmartIdent 3)
    'upsSmartIdentAgentFirmwareRevision': '1.3.6.1.4.1.935.1.1.1.1.2.4.0', # Agent Firmware (upsSmartIdent 4)
}

# 2. Battery Status and Health (1.3.6.1.2.1.33.1.2.x and SMAP 1.3.6.1.4.1.935.1.1.1.2.x)
BATTERY_OIDS = {
    # RFC 1628 Battery OIDs
    'upsBatteryStatus': '1.3.6.1.2.1.33.1.2.1.0',              # Battery Status
    'upsSecondsOnBattery': '1.3.6.1.2.1.33.1.2.2.0',          # Time on Battery (seconds)
    'upsEstimatedMinutesRemaining': '1.3.6.1.2.1.33.1.2.3.0', # Runtime Remaining (minutes)
    'upsEstimatedChargeRemaining': '1.3.6.1.2.1.33.1.2.4.0',  # Battery Capacity (%)
    'upsBatteryVoltage': '1.3.6.1.2.1.33.1.2.5.0',            # Battery Voltage (1/10 VDC)
    'upsBatteryTemperature': '1.3.6.1.2.1.33.1.2.6.0',        # Battery Temperature (1/10 °C)
    'upsBatteryTestResult': '1.3.6.1.2.1.33.1.2.7.0',         # Battery Test Result
    
    # SMAP-specific Battery OIDs
    'upsBaseBatteryStatus': '1.3.6.1.4.1.935.1.1.1.2.1.1.0',  # Battery Status
    'upsBaseBatteryTimeOnBattery': '1.3.6.1.4.1.935.1.1.1.2.1.2.0', # Time on Battery
    'upsSmartBatteryCapacity': '1.3.6.1.4.1.935.1.1.1.2.2.1.0', # Battery Capacity (%)
    'upsSmartBatteryVoltage': '1.3.6.1.4.1.935.1.1.1.2.2.2.0', # Battery Voltage (1/10 VDC)
    'upsSmartBatteryTemperature': '1.3.6.1.4.1.935.1.1.1.2.2.3.0', # Battery Temperature (1/10 °C)
    'upsSmartBatteryRunTimeRemaining': '1.3.6.1.4.1.935.1.1.1.2.2.4.0', # Runtime Remaining (seconds)
    'upsSmartBatteryReplaceIndicator': '1.3.6.1.4.1.935.1.1.1.2.2.5.0', # Replace Indicator
    'upsSmartBatteryFullChargeVoltage': '1.3.6.1.4.1.935.1.1.1.2.2.6.0', # Full Charge Voltage
    'upsSmartBatteryCurrent': '1.3.6.1.4.1.935.1.1.1.2.2.7.0', # Battery Current (%)
    'upsBaseBatteryLastReplaceDate': '1.3.6.1.4.1.935.1.1.1.2.1.3.0', # Last Replace Date
}

# Battery Status Enumeration
BATTERY_STATUS = {
    1: 'unknown',
    2: 'batteryNormal',
    3: 'batteryLow',
}

# 3. Input Power Monitoring (1.3.6.1.2.1.33.1.3.x and SMAP 1.3.6.1.4.1.935.1.1.1.3.x)
INPUT_OIDS = {
    # RFC 1628 Input OIDs
    'upsInputLineBads': '1.3.6.1.2.1.33.1.3.2.1.5.1',        # Line Fail Count
    'upsInputVoltage': '1.3.6.1.2.1.33.1.3.3.1.3.1',         # Line Voltage (1/10 VAC)
    'upsInputFrequency': '1.3.6.1.2.1.33.1.3.3.1.2.1',       # Input Frequency (1/10 Hz)
    'upsInputCurrent': '1.3.6.1.2.1.33.1.3.3.1.4.1',         # Input Current (1/10 A)
    
    # SMAP-specific Input OIDs (from SMAP SNMP R1e.mib)
    # upsBaseInput = { upsInputp 1 } = 1.3.6.1.4.1.935.1.1.1.3.1
    # upsSmartInput = { upsInputp 2 } = 1.3.6.1.4.1.935.1.1.1.3.2
    'upsBaseInputPhase': '1.3.6.1.4.1.935.1.1.1.3.1.1.0',     # Input Phase (upsBaseInput 1)
    'upsSmartInputLineVoltage': '1.3.6.1.4.1.935.1.1.1.3.2.1.0', # Line Voltage (1/10 VAC) (upsSmartInput 1)
    'upsSmartInputMaxLineVoltage': '1.3.6.1.4.1.935.1.1.1.3.2.2.0', # Max Line Voltage (1/10 VAC) (upsSmartInput 2)
    'upsSmartInputMinLineVoltage': '1.3.6.1.4.1.935.1.1.1.3.2.3.0', # Min Line Voltage (1/10 VAC) (upsSmartInput 3)
    'upsSmartInputFrequency': '1.3.6.1.4.1.935.1.1.1.3.2.4.0', # Input Frequency (1/10 Hz) (upsSmartInput 4)
    'upsSmartInputLineFailCause': '1.3.6.1.4.1.935.1.1.1.3.2.5.0', # Line Fail Cause (upsSmartInput 5)
}

# Line Fail Cause Enumeration
LINE_FAIL_CAUSE = {
    1: 'noTransfer',
    2: 'highLineVoltage',
    3: 'brownout',
    4: 'blackout',
    5: 'smallMomentarySag',
    6: 'deepMomentarySag',
    7: 'smallMomentarySpike',
    8: 'largeMomentarySpike',
}

# 4. Output Power Status (1.3.6.1.2.1.33.1.4.x and SMAP 1.3.6.1.4.1.935.1.1.1.4.x)
OUTPUT_OIDS = {
    # RFC 1628 Output OIDs
    'upsOutputSource': '1.3.6.1.2.1.33.1.4.1.0',              # Output Status
    'upsOutputVoltage': '1.3.6.1.2.1.33.1.4.4.1.2.1',        # Output Voltage (1/10 VAC)
    'upsOutputFrequency': '1.3.6.1.2.1.33.1.4.2.0',          # Output Frequency (1/10 Hz)
    'upsOutputLoad': '1.3.6.1.2.1.33.1.4.4.1.3.1',           # Output Load (%)
    'upsOutputCurrent': '1.3.6.1.2.1.33.1.4.4.1.4.1',         # Output Current (1/10 A)
    
    # SMAP-specific Output OIDs (from SMAP SNMP R1e.mib)
    # upsBaseOutput = { upsOutputp 1 } = 1.3.6.1.4.1.935.1.1.1.4.1
    # upsSmartOutput = { upsOutputp 2 } = 1.3.6.1.4.1.935.1.1.1.4.2
    'upsBaseOutputStatus': '1.3.6.1.4.1.935.1.1.1.4.1.1.0',  # Output Status (upsBaseOutput 1)
    'upsBaseOutputPhase': '1.3.6.1.4.1.935.1.1.1.4.1.2.0',    # Output Phase (upsBaseOutput 2)
    'upsSmartOutputVoltage': '1.3.6.1.4.1.935.1.1.1.4.2.1.0', # Output Voltage (1/10 VAC) (upsSmartOutput 1)
    'upsSmartOutputFrequency': '1.3.6.1.4.1.935.1.1.1.4.2.2.0', # Output Frequency (1/10 Hz) (upsSmartOutput 2)
    'upsSmartOutputLoad': '1.3.6.1.4.1.935.1.1.1.4.2.3.0',    # Output Load (%) (upsSmartOutput 3)
}

# Output Status Enumeration
OUTPUT_STATUS = {
    1: 'unknown',
    2: 'onLine',
    3: 'onBattery',
    4: 'onBoost',
    5: 'sleeping',
    6: 'onBypass',
    7: 'rebooting',
    8: 'standBy',
    9: 'onBuck',
}

# 5. Three-Phase UPS Support (from SMAP SNMP R1e.mib)
# Base path: 1.3.6.1.4.1.935.1.1.1.8 (upsThreePhase)
# upsThreePhaseInputGrp = { upsThreePhase 2 } = 1.3.6.1.4.1.935.1.1.1.8.2
# upsThreePhaseOutputGrp = { upsThreePhase 3 } = 1.3.6.1.4.1.935.1.1.1.8.3
# upsThreePhaseBypassGrp = { upsThreePhase 4 } = 1.3.6.1.4.1.935.1.1.1.8.4
# upsThreePhaseDCandRectifierStatusGrp = { upsThreePhase 5 } = 1.3.6.1.4.1.935.1.1.1.8.5
# upsThreePhaseFaultStatusGrp = { upsThreePhase 7 } = 1.3.6.1.4.1.935.1.1.1.8.7
THREE_PHASE_OIDS = {
    # Input Phase Readings (upsThreePhaseInputGrp)
    'upsThreePhaseInputFrequency': '1.3.6.1.4.1.935.1.1.1.8.2.1.0', # Input Frequency (upsThreePhaseInputGrp 1)
    'upsThreePhaseInputVoltageR': '1.3.6.1.4.1.935.1.1.1.8.2.2.0', # Input Voltage R phase (upsThreePhaseInputGrp 2)
    'upsThreePhaseInputVoltageS': '1.3.6.1.4.1.935.1.1.1.8.2.3.0', # Input Voltage S phase (upsThreePhaseInputGrp 3)
    'upsThreePhaseInputVoltageT': '1.3.6.1.4.1.935.1.1.1.8.2.4.0', # Input Voltage T phase (upsThreePhaseInputGrp 4)
    
    # Output Phase Readings (upsThreePhaseOutputGrp)
    'upsThreePhaseOutputFrequency': '1.3.6.1.4.1.935.1.1.1.8.3.1.0', # Output Frequency (upsThreePhaseOutputGrp 1)
    'upsThreePhaseOutputVoltageR': '1.3.6.1.4.1.935.1.1.1.8.3.2.0', # Output Voltage R phase (upsThreePhaseOutputGrp 2)
    'upsThreePhaseOutputVoltageS': '1.3.6.1.4.1.935.1.1.1.8.3.3.0', # Output Voltage S phase (upsThreePhaseOutputGrp 3)
    'upsThreePhaseOutputVoltageT': '1.3.6.1.4.1.935.1.1.1.8.3.4.0', # Output Voltage T phase (upsThreePhaseOutputGrp 4)
    'upsThreePhaseOutputLoadR': '1.3.6.1.4.1.935.1.1.1.8.3.5.0',    # Load R phase (%) (upsThreePhaseOutputGrp 5)
    'upsThreePhaseOutputLoadS': '1.3.6.1.4.1.935.1.1.1.8.3.6.0',    # Load S phase (%) (upsThreePhaseOutputGrp 6)
    'upsThreePhaseOutputLoadT': '1.3.6.1.4.1.935.1.1.1.8.3.7.0',    # Load T phase (%) (upsThreePhaseOutputGrp 7)
    
    # Bypass Source (upsThreePhaseBypassGrp)
    'upsThreePhaseBypassFrequency': '1.3.6.1.4.1.935.1.1.1.8.4.1.0', # Bypass Frequency (upsThreePhaseBypassGrp 1)
    'upsThreePhaseBypassVoltageR': '1.3.6.1.4.1.935.1.1.1.8.4.2.0', # Bypass Voltage R phase (upsThreePhaseBypassGrp 2)
    'upsThreePhaseBypassVoltageS': '1.3.6.1.4.1.935.1.1.1.8.4.3.0', # Bypass Voltage S phase (upsThreePhaseBypassGrp 3)
    'upsThreePhaseBypassVoltageT': '1.3.6.1.4.1.935.1.1.1.8.4.4.0', # Bypass Voltage T phase (upsThreePhaseBypassGrp 4)
    
    # DC and Rectifier Status (upsThreePhaseDCandRectifierStatusGrp)
    'upsThreePhaseRectifierRotationError': '1.3.6.1.4.1.935.1.1.1.8.5.1.0', # Rectifier Rotation Error (upsThreePhaseDCandRectifierStatusGrp 1)
    'upsThreePhaseLowBatteryShutdown': '1.3.6.1.4.1.935.1.1.1.8.5.2.0', # Low Battery Shutdown (upsThreePhaseDCandRectifierStatusGrp 2)
    'upsThreePhaseChargeStatus': '1.3.6.1.4.1.935.1.1.1.8.5.6.0', # Charge Status (upsThreePhaseDCandRectifierStatusGrp 6)
    'upsThreePhaseRectifierOperatingStatus': '1.3.6.1.4.1.935.1.1.1.8.5.7.0', # Rectifier Operating Status (upsThreePhaseDCandRectifierStatusGrp 7)
    'upsThreePhaseInOutConfiguration': '1.3.6.1.4.1.935.1.1.1.8.5.4.0', # In/Out Configuration (upsThreePhaseDCandRectifierStatusGrp 4)
    
    # Fault Status Indicators (upsThreePhaseFaultStatusGrp)
    'upsThreePhaseEmergencyStop': '1.3.6.1.4.1.935.1.1.1.8.7.1.0', # Emergency Stop (upsThreePhaseFaultStatusGrp 1)
    'upsThreePhaseHighDCShutdown': '1.3.6.1.4.1.935.1.1.1.8.7.2.0', # High DC Shutdown (upsThreePhaseFaultStatusGrp 2)
    'upsThreePhaseBypassBreaker': '1.3.6.1.4.1.935.1.1.1.8.7.3.0', # Bypass Breaker (upsThreePhaseFaultStatusGrp 3)
    'upsThreePhaseOverLoad': '1.3.6.1.4.1.935.1.1.1.8.7.4.0', # Over Load (upsThreePhaseFaultStatusGrp 4)
    'upsThreePhaseInverterOutputFail': '1.3.6.1.4.1.935.1.1.1.8.7.5.0', # Inverter Output Fail (upsThreePhaseFaultStatusGrp 5)
    'upsThreePhaseOverTemperature': '1.3.6.1.4.1.935.1.1.1.8.7.6.0', # Over Temperature (upsThreePhaseFaultStatusGrp 6)
    'upsThreePhaseShortCircuit': '1.3.6.1.4.1.935.1.1.1.8.7.7.0', # Short Circuit (upsThreePhaseFaultStatusGrp 7)
}

# Charge Status Enumeration
CHARGE_STATUS = {
    1: 'boost',
    2: 'float',
    3: 'no',
}

# Rectifier Operating Status Enumeration
RECTIFIER_STATUS = {
    1: 'unknown',
    2: 'normal',
    3: 'abnormal',
}

# In/Out Configuration Enumeration
IN_OUT_CONFIG = {
    1: '3-in-1-out',
    2: '3-in-3-out',
}

# Fault Status (typically boolean: 1 = active, 2 = inactive)
FAULT_STATUS = {
    1: 'Active',
    2: 'Inactive',
}

# ============================================================================
# ATS (Automatic Transfer Switch) MIB Definitions
# Based on ATS_Stork_V1_05 - Borri STS32A.MIB
#
# ROOT CAUSE AND PROBLEM:
# -----------------------
# The MIB file (ATS_Stork_V1_05 - Borri STS32A.MIB) defines atsAgent(3), which
# results in OID paths like: 1.3.6.1.4.1.37662.1.2.3.1.1.x
# However, the actual device firmware uses atsAgent(2), resulting in OID paths:
# 1.3.6.1.4.1.37662.1.2.2.1.1.x
#
# This mismatch was discovered when:
# 1. Querying sysObjectID (1.3.6.1.2.1.1.2.0) returned: 1.3.6.1.4.1.37662.1.2.2.1
# 2. All status queries using MIB-defined OIDs (with atsAgent=3) failed with "noSuchName"
# 3. Debug file analysis showed the device uses atsAgent(2) path structure
#
# SOLUTION:
# ---------
# All ATS status OIDs have been updated to use atsAgent(2) path:
# - OLD (MIB v1.05): 1.3.6.1.4.1.37662.1.2.3.1.1.x
# - NEW (Device):    1.3.6.1.4.1.37662.1.2.2.1.1.x
#
# The code also includes auto-detection logic to check sysObjectID and try both
# paths if needed for backward compatibility.
#
# Base OID: 1.3.6.1.4.1.37662.1.2.2.1.1 (atsObjectGroup with atsAgent=2)
# sysObjectID: 1.3.6.1.4.1.37662.1.2.2.1 (confirmed from device)
# ============================================================================

# ATS Identification Group (atsIdentGroup = 1.3.6.1.4.1.37662.1.2.2.1.1.1)
ATS_IDENT_OIDS = {
    'atsIdentGroupModel': '1.3.6.1.4.1.37662.1.2.2.1.1.1.1.0',              # Model Name
    'atsIdentGroupSerialNumber': '1.3.6.1.4.1.37662.1.2.2.1.1.1.2.0',      # Serial Number
    'atsIdentGroupManufacturer': '1.3.6.1.4.1.37662.1.2.2.1.1.1.3.0',       # Manufacturer
    'atsIdentGroupFirmwareRevision': '1.3.6.1.4.1.37662.1.2.2.1.1.1.4.0',   # Firmware Revision
    'atsIdentGroupAgentFirmwareRevision': '1.3.6.1.4.1.37662.1.2.2.1.1.1.5.0', # Agent Firmware Revision
}

# ATS Input Group (atsInputGroup = 1.3.6.1.4.1.37662.1.2.2.1.1.2)
ATS_INPUT_OIDS = {
    'atsInputGroupPreference': '1.3.6.1.4.1.37662.1.2.2.1.1.2.1.0',         # Output Source Priority
    'atsInputGroupSourceAstatus': '1.3.6.1.4.1.37662.1.2.2.1.1.2.2.0',      # Source A Status (1=fail, 2=ok)
    'atsInputGroupSourceAinputVoltage': '1.3.6.1.4.1.37662.1.2.2.1.1.2.3.0', # Source A Voltage (0.1 V)
    'atsInputGroupSourceAinputFrequency': '1.3.6.1.4.1.37662.1.2.2.1.1.2.4.0', # Source A Frequency (0.1 Hz)
    'atsInputGroupSourceBstatus': '1.3.6.1.4.1.37662.1.2.2.1.1.2.5.0',      # Source B Status (1=fail, 2=ok)
    'atsInputGroupSourceBinputVoltage': '1.3.6.1.4.1.37662.1.2.2.1.1.2.6.0', # Source B Voltage (0.1 V)
    'atsInputGroupSourceBinputFrequency': '1.3.6.1.4.1.37662.1.2.2.1.1.2.7.0', # Source B Frequency (0.1 Hz)
    'atsInputGroupSourceAvoltageUpperLimit': '1.3.6.1.4.1.37662.1.2.2.1.1.2.8.0', # Source A Voltage Upper Limit (0.1 V)
    'atsInputGroupSourceAvoltageLowerLimit': '1.3.6.1.4.1.37662.1.2.2.1.1.2.9.0', # Source A Voltage Lower Limit (0.1 V)
    'atsInputGroupSourceAfrequencyUpperLimit': '1.3.6.1.4.1.37662.1.2.2.1.1.2.10.0', # Source A Frequency Upper Limit (0.1 Hz)
    'atsInputGroupSourceAfrequencyLowerLimit': '1.3.6.1.4.1.37662.1.2.2.1.1.2.11.0', # Source A Frequency Lower Limit (0.1 Hz)
    'atsInputGroupSourceBvoltageUpperLimit': '1.3.6.1.4.1.37662.1.2.2.1.1.2.12.0', # Source B Voltage Upper Limit (0.1 V)
    'atsInputGroupSourceBvoltageLowerLimit': '1.3.6.1.4.1.37662.1.2.2.1.1.2.13.0', # Source B Voltage Lower Limit (0.1 V)
    'atsInputGroupSourceBfrequencyUpperLimit': '1.3.6.1.4.1.37662.1.2.2.1.1.2.14.0', # Source B Frequency Upper Limit (0.1 Hz)
    'atsInputGroupSourceBfrequencyLowerLimit': '1.3.6.1.4.1.37662.1.2.2.1.1.2.15.0', # Source B Frequency Lower Limit (0.1 Hz)
}

# Source Status Enumeration
SOURCE_STATUS = {
    1: 'fail',
    2: 'ok',
}

# ATS Output Group (atsOutputGroup = 1.3.6.1.4.1.37662.1.2.2.1.1.3)
ATS_OUTPUT_OIDS = {
    'atsOutputGroupOutputSource': '1.3.6.1.4.1.37662.1.2.2.1.1.3.1.0',     # Output Source (Source A/B/Bypass A/B)
    'atsOutputGroupOutputVoltage': '1.3.6.1.4.1.37662.1.2.2.1.1.3.2.0',    # Output Voltage (0.1 V)
    'atsOutputGroupOutputFequency': '1.3.6.1.4.1.37662.1.2.2.1.1.3.3.0',   # Output Frequency (0.1 Hz)
    'atsOutputGroupOutputCurrent': '1.3.6.1.4.1.37662.1.2.2.1.1.3.4.0',    # Output Current (0.1 A)
    'atsOutputGroupLoad': '1.3.6.1.4.1.37662.1.2.2.1.1.3.5.0',             # Output Load (0.1 %)
}

# ATS HMI Switch Group (atsHmiSwitchGroup = 1.3.6.1.4.1.37662.1.2.2.1.1.4)
ATS_HMI_SWITCH_OIDS = {
    'atsHmiSwitchGroupBuzzer': '1.3.6.1.4.1.37662.1.2.2.1.1.4.1.0',        # Buzzer Status (1=disabled, 2=enabled)
    'atsHmiSwitchGroupAtsAlarm': '1.3.6.1.4.1.37662.1.2.2.1.1.4.2.0',      # ATS Alarm (1=nothing, 2=alarm)
    'atsHmiSwitchGroupAutoReturn': '1.3.6.1.4.1.37662.1.2.2.1.1.4.3.0',    # Auto Return (1=off, 2=on)
    'atsHmiSwitchGroupSourceTransferByLoad': '1.3.6.1.4.1.37662.1.2.2.1.1.4.4.0', # Transfer by Load (1=off, 2=on)
    'atsHmiSwitchGroupSourceTransferByPhase': '1.3.6.1.4.1.37662.1.2.2.1.1.4.5.0', # Transfer by Phase (1=off, 2=on)
}

# ATS Miscellaneous Group (atsMiscellaneousGroup = 1.3.6.1.4.1.37662.1.2.2.1.1.5)
ATS_MISC_OIDS = {
    'atsMiscellaneousGroupAtsSystemTemperture': '1.3.6.1.4.1.37662.1.2.2.1.1.5.1.0', # System Temperature (°C)
    'atsMiscellaneousGroupSystemMaxCurrent': '1.3.6.1.4.1.37662.1.2.2.1.1.5.2.0',   # System Max Current (0.1 A)
}

# ATS Base OID for walking entire tree
ATS_BASE_OID = '1.3.6.1.4.1.37662'  # Base ATS enterprise OID
ATS_OBJECT_GROUP_BASE = '1.3.6.1.4.1.37662.1.2.2.1.1'  # atsObjectGroup base (with atsAgent=2)

# ============================================================================
# i-STS MIB Definitions
# Based on i-STS snmp-mib.mib
# Base OID: 43.6.1.4.1.32796 (ISTS enterprise OID)
# Note: The MIB uses 43.6.1.4.1.32796 format (non-standard, may need conversion to 1.3.6.1.4.1.32796)
# ============================================================================

# i-STS Product Information (43.6.1.4.1.32796.1.x)
ISTS_PRODUCT_OIDS = {
    'istsProductName': '43.6.1.4.1.32796.1.1',        # Product Name
    'istsProductVersion': '43.6.1.4.1.32796.1.2',    # Product Version
    'istsVersionDate': '43.6.1.4.1.32796.1.3',       # Version Date
}

# i-STS Control/Operation Variables (43.6.1.4.1.32796.3.1.x)
ISTS_CONTROL_OIDS = {
    'istsActiveSupply': '43.6.1.4.1.32796.3.1.1',     # Active Supply (1=Supply1, 2=Supply2)
    'istsPreferredSupply': '43.6.1.4.1.32796.3.1.2', # Preferred Supply (1=Supply1, 2=Supply2)
    'istsFreq1': '43.6.1.4.1.32796.3.1.3',           # Supply 1 Frequency (0.1 Hz)
    'istsFreq2': '43.6.1.4.1.32796.3.1.4',           # Supply 2 Frequency (0.1 Hz)
    'istsSync': '43.6.1.4.1.32796.3.1.5',            # Sync Status (WORD)
    'istsNeutralI': '43.6.1.4.1.32796.3.1.6',        # Neutral Current (WORD)
}

# i-STS Input Variables (43.6.1.4.1.32796.3.2.x) - SEQUENCE/TABLE
# Note: These are table entries, may need to walk with index
ISTS_INPUT_BASE_OID = '43.6.1.4.1.32796.3.2'  # Base for walking input table

# i-STS Output Variables (43.6.1.4.1.32796.3.3.x) - SEQUENCE/TABLE
ISTS_OUTPUT_BASE_OID = '43.6.1.4.1.32796.3.3'  # Base for walking output table

# i-STS Event Log (43.6.1.4.1.32796.3.4.x) - SEQUENCE/TABLE
ISTS_EVENT_LOG_BASE_OID = '43.6.1.4.1.32796.3.4'  # Base for walking event log table

# i-STS Alarms (43.6.1.4.1.32796.3.5.1)
ISTS_ALARMS_OID = '43.6.1.4.1.32796.3.5.1'  # ALARMS (WORD, bit-mapped)

# i-STS Utilisation/Statistics (43.6.1.4.1.32796.3.6.x)
ISTS_UTILISATION_OIDS = {
    'istsHours1': '43.6.1.4.1.32796.3.6.1',         # Hours on Supply 1 (WORD)
    'istsHours2': '43.6.1.4.1.32796.3.6.2',         # Hours on Supply 2 (WORD)
    'istsHoursPreferred': '43.6.1.4.1.32796.3.6.3', # Hours on Preferred Supply (WORD)
    'istsHoursOperation': '43.6.1.4.1.32796.3.6.4',  # Total Hours of Operation (WORD)
    'istsHoursNoOutput': '43.6.1.4.1.32796.3.6.5',  # Hours with No Output (WORD)
    'istsNumForcedXfers': '43.6.1.4.1.32796.3.6.6', # Number of Forced Transfers (WORD)
    'istsNumSyncLosses': '43.6.1.4.1.32796.3.6.7',   # Number of Sync Losses (WORD)
    'istsLastLoadFault': '43.6.1.4.1.32796.3.6.8',  # Last Load Fault Time (TIME_TICKS)
    'istsNumSupplyOuts': '43.6.1.4.1.32796.3.6.9',  # Number of Supply Outages (WORD)
    'istsLastSupplyOut': '43.6.1.4.1.32796.3.6.10', # Last Supply Out Time (TIME_TICKS)
}

# i-STS Base OID for walking entire tree
ISTS_BASE_OID = '43.6.1.4.1.32796'  # Base i-STS enterprise OID

# Supply Status Enumeration
ISTS_SUPPLY_STATUS = {
    1: 'Supply1',
    2: 'Supply2',
}

# Alarm Bit Flags (from MIB comments - bit positions)
# ALARMS is a WORD with bit-mapped fields
ISTS_ALARM_FLAGS = {
    0: 'SUPPLY_1_BAD',
    1: 'SUPPLY_2_BAD',
    2: 'NOT_ON_PREFERRED',
    3: 'SYNC_LOSS',
    4: 'LOAD_FAULT',
    5: 'HIGH_TEMP',
    6: 'FORCED',
}


class UPSStatusQuery:
    """Query UPS/ATS status via SNMP (using SNMPv2c)."""
    
    def __init__(self, host: str, community: str = DEFAULT_COMMUNITY, port: int = DEFAULT_PORT, debug_file: str = None):
        """
        Initialize UPS Status Query.
        
        Args:
            host: UPS/ATS device IP address or hostname
            community: SNMP community string (default: 'public')
            port: SNMP port (default: 161)
            debug_file: Optional path to debug file to write all SNMP responses
        """
        self.host = host
        self.community = community
        self.port = port
        self.debug_file = debug_file
        self.debug_data = []  # Store all SNMP responses for debug output
        
        # Initialize SNMP engine based on pysnmp version
        if USE_ENTITY_API:
            # Use entity API (synchronous, reliable)
            self.snmp_engine = engine.SnmpEngine()
            # Configure transport once (reused for all queries)
            # Note: Transport configuration is done per-query in pysnmp 7.x
            # No need to pre-configure here
        elif USE_HLAPI:
            self.snmp_engine = SnmpEngine()
        else:
            self.snmp_engine = None
        
        self.results = {}
    
    def _log_debug(self, oid: str, value: Any, error: str = None):
        """Log SNMP query result to debug data."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'oid': oid,
            'value': str(value) if value is not None else None,
            'value_type': type(value).__name__ if value is not None else None,
            'error': error
        }
        if hasattr(value, 'prettyPrint'):
            entry['value_pretty'] = value.prettyPrint()
        self.debug_data.append(entry)
    
    def _write_debug_file(self):
        """Write all debug data to file."""
        if not self.debug_file:
            return
        
        try:
            with open(self.debug_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("SNMP QUERY DEBUG LOG\n")
                f.write("=" * 80 + "\n")
                f.write(f"Host: {self.host}\n")
                f.write(f"Community: {self.community}\n")
                f.write(f"Port: {self.port}\n")
                f.write(f"Query Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
                
                if not self.debug_data:
                    f.write("No SNMP queries were made.\n")
                    return
                
                f.write(f"Total Queries: {len(self.debug_data)}\n")
                f.write(f"Successful: {sum(1 for e in self.debug_data if e['value'] is not None)}\n")
                f.write(f"Failed: {sum(1 for e in self.debug_data if e['error'] is not None)}\n")
                f.write("\n" + "=" * 80 + "\n")
                f.write("DETAILED QUERY RESULTS\n")
                f.write("=" * 80 + "\n\n")
                
                for i, entry in enumerate(self.debug_data, 1):
                    f.write(f"Query #{i}:\n")
                    f.write(f"  Timestamp: {entry['timestamp']}\n")
                    f.write(f"  OID: {entry['oid']}\n")
                    if entry['error']:
                        f.write(f"  ERROR: {entry['error']}\n")
                    else:
                        f.write(f"  Value Type: {entry['value_type']}\n")
                        f.write(f"  Value: {entry['value']}\n")
                        if 'value_pretty' in entry:
                            f.write(f"  Value (Pretty): {entry['value_pretty']}\n")
                    f.write("\n")
                
                # Group by OID base for summary
                f.write("\n" + "=" * 80 + "\n")
                f.write("OID SUMMARY BY BASE\n")
                f.write("=" * 80 + "\n\n")
                
                oid_groups = {}
                for entry in self.debug_data:
                    # Extract base OID (first 3-4 levels)
                    oid_parts = entry['oid'].split('.')
                    if len(oid_parts) >= 4:
                        base = '.'.join(oid_parts[:4])
                    else:
                        base = entry['oid']
                    
                    if base not in oid_groups:
                        oid_groups[base] = {'total': 0, 'success': 0, 'failed': 0}
                    oid_groups[base]['total'] += 1
                    if entry['error']:
                        oid_groups[base]['failed'] += 1
                    else:
                        oid_groups[base]['success'] += 1
                
                for base, stats in sorted(oid_groups.items()):
                    f.write(f"{base}:\n")
                    f.write(f"  Total: {stats['total']}, Success: {stats['success']}, Failed: {stats['failed']}\n")
                    f.write("\n")
                
            print(f"\n[DEBUG] All SNMP responses written to: {self.debug_file}")
        except Exception as e:
            print(f"\n[WARNING] Failed to write debug file: {e}", file=sys.stderr)
    
    def walk_oid(self, base_oid: str, max_results: int = 50) -> List[Tuple[str, Any]]:
        """
        Walk SNMP tree starting from a base OID.
        
        Args:
            base_oid: Base OID to start walking from
            max_results: Maximum number of results to return
            
        Returns:
            List of tuples (oid, value) found
        """
        results = []
        try:
            if USE_HLAPI:
                # Use synchronous hlapi nextCmd (works with both pysnmp 4.x and 7.x)
                from pysnmp.hlapi import nextCmd, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity, SnmpEngine
                
                snmp_engine = self.snmp_engine if hasattr(self, 'snmp_engine') and self.snmp_engine else SnmpEngine()
                
                iterator = nextCmd(
                    snmp_engine,
                    CommunityData(self.community, mpModel=1),  # SNMPv2c
                    UdpTransportTarget((self.host, self.port)),
                    ContextData(),
                    ObjectType(ObjectIdentity(base_oid)),
                    lexicographicMode=False,
                    maxRows=max_results
                )
                for (errorIndication, errorStatus, errorIndex, varBinds) in iterator:
                    if errorIndication:
                        # Some errors are expected (end of tree)
                        if 'No SNMP response' in str(errorIndication) or 'timeout' in str(errorIndication).lower():
                            break
                        continue
                    elif errorStatus:
                        # noSuchName means end of tree, which is normal
                        if errorStatus.prettyPrint() == 'noSuchName':
                            break
                        continue
                    else:
                        for varBind in varBinds:
                            oid_str, value = varBind
                            oid_str = str(oid_str)
                            # Check if we've gone past the base OID
                            if not oid_str.startswith(base_oid):
                                return results
                            results.append((oid_str, value))
                            # Log to debug
                            self._log_debug(oid_str, value)
                            if len(results) >= max_results:
                                return results
            else:
                # For entity API, use a simpler approach - just query common child OIDs
                # This is a workaround since entity API WALK is more complex
                print(f"  [INFO] WALK not fully supported with entity API, trying common OIDs...", file=sys.stderr)
                # Try a few common child OIDs manually
                for i in range(1, min(20, max_results)):
                    test_oid = f"{base_oid}.{i}.0"
                    value = self.query_oid(test_oid, None)
                    if value is not None:
                        results.append((test_oid, value))
                    if len(results) >= max_results:
                        break
                
        except Exception as e:
            print(f"  [ERROR] WALK failed for {base_oid}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        
        return results
    
    def discover_available_oids(self) -> Dict[str, List[Tuple[str, Any]]]:
        """
        Discover available OIDs on the UPS by walking common base OIDs.
        
        Returns:
            Dictionary mapping base OID to list of (oid, value) tuples
        """
        print("\n" + "=" * 80)
        print("DISCOVERING AVAILABLE OIDs")
        print("=" * 80)
        print("Walking common UPS OID bases to find available data...")
        
        discovered = {}
        
        # Common UPS/ATS/i-STS OID bases to try
        base_oids = [
            '43.6.1.4.1.32796',    # i-STS MIB (Static Transfer Switch)
            '1.3.6.1.4.1.37662',   # ATS MIB (Borri STS32A) - prioritize this
            '1.3.6.1.2.1.33',      # RFC 1628 UPS-MIB
            '1.3.6.1.4.1.935',     # SMAP/APC PowerNet MIB
            '1.3.6.1.2.1.1',       # SNMP System MIB (should always work)
        ]
        
        for base_oid in base_oids:
            print(f"\n  Walking {base_oid}...", end=" ", flush=True)
            results = self.walk_oid(base_oid, max_results=100)
            if results:
                print(f"Found {len(results)} OIDs")
                discovered[base_oid] = results
                # Show first few as examples
                for oid, value in results[:5]:
                    value_str = str(value)
                    if hasattr(value, 'prettyPrint'):
                        value_str = value.prettyPrint()
                    if len(value_str) > 60:
                        value_str = value_str[:60] + "..."
                    print(f"    {oid}: {value_str}")
                if len(results) > 5:
                    print(f"    ... and {len(results) - 5} more")
            else:
                print("No OIDs found")
        
        # Write debug file if requested
        if self.debug_file:
            self._write_debug_file()
        
        return discovered
        
    def query_oid(self, oid: str, description: str = None, try_without_zero: bool = False) -> Optional[Any]:
        """
        Query a single OID.
        
        Args:
            oid: OID string to query
            description: Optional description for logging
            try_without_zero: If True and query fails, try without .0 suffix
            
        Returns:
            Value from OID or None if error
        """
        try:
            if USE_ENTITY_API:
                # Use pysnmp 7.x async API (v1arch.asyncio) but run synchronously
                from pysnmp.hlapi.v1arch.asyncio import get_cmd
                from pysnmp.hlapi.v1arch import CommunityData, UdpTransportTarget, ObjectType, ObjectIdentity
                from pysnmp.hlapi.v1arch.asyncio.dispatch import SnmpDispatcher
                
                # Use asyncio to run the async function
                async def _get_oid():
                    dispatcher = SnmpDispatcher()
                    transport = await UdpTransportTarget.create((self.host, self.port))
                    return await get_cmd(
                        dispatcher,
                        CommunityData(self.community, mpModel=1),  # SNMPv2c
                        transport,
                        ObjectType(ObjectIdentity(oid))
                    )
                
                # Run async function synchronously using asyncio.run()
                # This creates a new event loop for each query
                errorIndication, errorStatus, errorIndex, varBinds = asyncio.run(_get_oid())
                
            elif USE_HLAPI:
                # pysnmp 4.x hlapi API (synchronous)
                iterator = getCmd(
                    self.snmp_engine,
                    CommunityData(self.community, mpModel=1),  # SNMPv2c
                    UdpTransportTarget((self.host, self.port)),
                    ContextData(),
                    ObjectType(ObjectIdentity(oid)),
                    lexicographicMode=False
                )
                errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            else:
                if description:
                    print(f"  [ERROR] {description}: No SNMP API available", file=sys.stderr)
                return None
            
            # Process response (common for all APIs)
            if errorIndication:
                error_msg = str(errorIndication)
                self._log_debug(oid, None, error_msg)
                if description:
                    # Check for common connection errors
                    if 'No SNMP response received' in error_msg or 'timeout' in error_msg.lower():
                        print(f"  [ERROR] {description}: Connection timeout - Check if UPS is reachable at {self.host}:{self.port}", file=sys.stderr)
                    elif 'Connection refused' in error_msg or 'refused' in error_msg.lower():
                        print(f"  [ERROR] {description}: Connection refused - Check SNMP service on UPS", file=sys.stderr)
                    else:
                        print(f"  [ERROR] {description}: {error_msg}", file=sys.stderr)
                return None
            elif errorStatus:
                error_msg = str(errorStatus)
                if hasattr(errorStatus, 'prettyPrint'):
                    error_msg = errorStatus.prettyPrint()
                self._log_debug(oid, None, error_msg)
                if description:
                    # Check for "No Such Object" which means OID doesn't exist on this device
                    if 'No Such Object' in error_msg or 'noSuchObject' in error_msg:
                        # Don't show error for missing OIDs - they're optional
                        pass
                    else:
                        print(f"  [ERROR] {description}: {error_msg} at {errorIndex and varBinds[int(errorIndex) - 1][0] if varBinds else '?'}", file=sys.stderr)
                return None
            else:
                for varBind in varBinds:
                    oid_str, value = varBind
                    self._log_debug(str(oid_str), value)
                    return value
        except Exception as e:
            error_msg = str(e)
            self._log_debug(oid, None, error_msg)
            if description:
                print(f"  [ERROR] {description}: {e}", file=sys.stderr)
            
            # Try without .0 suffix if requested and OID ends with .0
            if try_without_zero and oid.endswith('.0'):
                alt_oid = oid[:-2]
                if description:
                    print(f"  [INFO] Trying alternative OID without .0: {alt_oid}", file=sys.stderr)
                return self.query_oid(alt_oid, description, try_without_zero=False)
            
            return None
        
        return None
    
    def query_multiple_oids(self, oid_dict: Dict[str, str], show_errors: bool = True, try_without_zero: bool = False) -> Dict[str, Any]:
        """
        Query multiple OIDs.
        
        Args:
            oid_dict: Dictionary mapping description to OID
            show_errors: Whether to show error messages (default: True)
            try_without_zero: If True, try OIDs without .0 suffix if query fails
            
        Returns:
            Dictionary mapping description to value
        """
        results = {}
        error_count = 0
        success_count = 0
        for desc, oid in oid_dict.items():
            value = self.query_oid(oid, desc if show_errors else None, try_without_zero=try_without_zero)
            results[desc] = value
            if value is None:
                error_count += 1
            else:
                success_count += 1
        if show_errors and error_count > 0:
            print(f"  [WARNING] {error_count} of {len(oid_dict)} OIDs failed to query", file=sys.stderr)
        return results
    
    def format_value(self, value: Any, oid_name: str = None) -> str:
        """
        Format SNMP value for display.
        
        Args:
            value: SNMP value
            oid_name: Optional OID name for special formatting
            
        Returns:
            Formatted string
        """
        if value is None:
            return "N/A"
        
        # Handle different value types
        if hasattr(value, 'prettyPrint'):
            str_value = value.prettyPrint()
        else:
            str_value = str(value)
        
        # Special formatting based on OID name
        if oid_name:
            # Voltage values (1/10 VAC or VDC)
            if 'Voltage' in oid_name or 'voltage' in oid_name:
                try:
                    voltage = float(str_value) / 10.0
                    return f"{voltage:.1f} V"
                except (ValueError, TypeError):
                    pass
            
            # Frequency values (1/10 Hz)
            if 'Frequency' in oid_name or 'frequency' in oid_name:
                try:
                    freq = float(str_value) / 10.0
                    return f"{freq:.1f} Hz"
                except (ValueError, TypeError):
                    pass
            
            # Temperature values (1/10 °C)
            if 'Temperature' in oid_name or 'temperature' in oid_name:
                try:
                    temp = float(str_value) / 10.0
                    return f"{temp:.1f} °C"
                except (ValueError, TypeError):
                    pass
            
            # Percentage values
            if 'Load' in oid_name or 'Capacity' in oid_name or 'Current' in oid_name:
                if '%' not in str_value:
                    try:
                        percent_val = float(str_value)
                        # ATS Load is in 0.1%, so divide by 10
                        if 'atsOutputGroupLoad' in oid_name or 'Load' in oid_name and 'ats' in oid_name.lower():
                            percent = percent_val / 10.0
                        else:
                            percent = percent_val
                        return f"{percent:.1f}%"
                    except (ValueError, TypeError):
                        pass
            
            # ATS-specific: Current values (0.1 A)
            if 'Current' in oid_name and 'ats' in oid_name.lower():
                try:
                    current = float(str_value) / 10.0
                    return f"{current:.1f} A"
                except (ValueError, TypeError):
                    pass
            
            # i-STS-specific: Hours values (WORD - integer hours)
            if 'Hours' in oid_name or 'hours' in oid_name:
                try:
                    hours = int(str_value)
                    if hours >= 24:
                        days = hours // 24
                        remaining_hours = hours % 24
                        return f"{days}d {remaining_hours}h" if days > 0 else f"{hours}h"
                    else:
                        return f"{hours}h"
                except (ValueError, TypeError):
                    pass
            
            # i-STS-specific: Decimal values (for PF, CF)
            if 'PF' in oid_name or 'CF' in oid_name or 'Power Factor' in oid_name or 'Crest Factor' in oid_name:
                try:
                    decimal_val = float(str_value)
                    return f"{decimal_val:.2f}"
                except (ValueError, TypeError):
                    pass
        
        return str_value
    
    def format_time(self, seconds: int) -> str:
        """Format seconds into human-readable time."""
        if seconds is None or seconds == 0:
            return "N/A"
        try:
            delta = timedelta(seconds=int(seconds))
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            secs = delta.seconds % 60
            if delta.days > 0:
                return f"{delta.days}d {hours}h {minutes}m {secs}s"
            elif hours > 0:
                return f"{hours}h {minutes}m {secs}s"
            elif minutes > 0:
                return f"{minutes}m {secs}s"
            else:
                return f"{secs}s"
        except (ValueError, TypeError):
            return str(seconds)
    
    def query_identification(self) -> Dict[str, Any]:
        """Query UPS identification information."""
        print("\n" + "=" * 80)
        print("1. UPS IDENTIFICATION INFORMATION")
        print("=" * 80)
        
        results = {}
        
        # Test basic connectivity first with a simple OID
        print("  Testing connectivity...", end=" ", flush=True)
        test_oid = '1.3.6.1.2.1.1.1.0'  # sysDescr - should be available on all SNMP devices
        test_result = self.query_oid(test_oid, None)
        if test_result is None:
            print("FAILED", file=sys.stderr)
            print(f"  [ERROR] Cannot connect to UPS at {self.host}:{self.port}", file=sys.stderr)
            print(f"  [ERROR] Check:", file=sys.stderr)
            print(f"    - UPS is powered on and network connected", file=sys.stderr)
            print(f"    - SNMP is enabled on UPS", file=sys.stderr)
            print(f"    - Community string is correct (current: '{self.community}')", file=sys.stderr)
            print(f"    - Firewall allows SNMP (port {self.port})", file=sys.stderr)
            print(f"    - IP address is correct: {self.host}", file=sys.stderr)
            return results
        else:
            print("OK")
        
        # Try SMAP OIDs first, fall back to RFC 1628
        smap_results = self.query_multiple_oids(SMAP_IDENT_OIDS, show_errors=False)
        rfc_results = self.query_multiple_oids(UPS_IDENT_OIDS, show_errors=False)
        
        # Use SMAP if available, otherwise use RFC
        model = smap_results.get('upsBaseIdentModel') or rfc_results.get('upsIdentModel')
        name = smap_results.get('upsBaseIdentUpsName') or rfc_results.get('upsIdentUPSName')
        firmware = smap_results.get('upsSmartIdentFirmwareRevision') or rfc_results.get('upsIdentFirmwareRevision')
        manufacture_date = smap_results.get('upsSmartIdentDateOfManufacture') or rfc_results.get('upsIdentDateOfManufacture')
        serial = smap_results.get('upsSmartIdentUpsSerialNumber') or rfc_results.get('upsIdentSerialNumber')
        agent_firmware = smap_results.get('upsSmartIdentAgentFirmwareRevision') or rfc_results.get('upsIdentAgentFirmwareRevision')
        
        print(f"  Model Name:              {self.format_value(model, 'Model')}")
        print(f"  UPS Name:                {self.format_value(name, 'Name')}")
        print(f"  Firmware Revision:      {self.format_value(firmware, 'Firmware')}")
        print(f"  Date of Manufacture:     {self.format_value(manufacture_date, 'Date')}")
        print(f"  Serial Number:           {self.format_value(serial, 'Serial')}")
        print(f"  Agent Firmware Revision: {self.format_value(agent_firmware, 'AgentFirmware')}")
        
        results['model'] = model
        results['name'] = name
        results['firmware'] = firmware
        results['manufacture_date'] = manufacture_date
        results['serial'] = serial
        results['agent_firmware'] = agent_firmware
        
        return results
    
    def query_battery_status(self) -> Dict[str, Any]:
        """Query battery status and health."""
        print("\n" + "=" * 80)
        print("2. BATTERY STATUS AND HEALTH")
        print("=" * 80)
        
        results = {}
        battery_results = self.query_multiple_oids(BATTERY_OIDS)
        
        # Battery Status
        status_val = battery_results.get('upsBaseBatteryStatus') or battery_results.get('upsBatteryStatus')
        if status_val is not None:
            try:
                status_int = int(str(status_val))
                status_str = BATTERY_STATUS.get(status_int, f"unknown({status_int})")
            except (ValueError, TypeError):
                status_str = str(status_val)
        else:
            status_str = "N/A"
        
        print(f"  Battery Status:          {status_str}")
        
        # Time on Battery
        time_on_battery = battery_results.get('upsBaseBatteryTimeOnBattery') or battery_results.get('upsSecondsOnBattery')
        if time_on_battery is not None:
            try:
                time_str = self.format_time(int(str(time_on_battery)))
            except (ValueError, TypeError):
                time_str = str(time_on_battery)
        else:
            time_str = "N/A"
        print(f"  Time on Battery:          {time_str}")
        
        # Battery Capacity
        capacity = battery_results.get('upsSmartBatteryCapacity') or battery_results.get('upsEstimatedChargeRemaining')
        print(f"  Battery Capacity:         {self.format_value(capacity, 'Capacity')}")
        
        # Battery Voltage
        voltage = battery_results.get('upsSmartBatteryVoltage') or battery_results.get('upsBatteryVoltage')
        print(f"  Battery Voltage:          {self.format_value(voltage, 'Voltage')}")
        
        # Battery Temperature
        temperature = battery_results.get('upsSmartBatteryTemperature') or battery_results.get('upsBatteryTemperature')
        print(f"  Battery Temperature:      {self.format_value(temperature, 'Temperature')}")
        
        # Runtime Remaining
        runtime = battery_results.get('upsSmartBatteryRunTimeRemaining') or battery_results.get('upsEstimatedMinutesRemaining')
        if runtime is not None:
            try:
                runtime_val = int(str(runtime))
                # Check if it's in minutes (RFC) or seconds (SMAP)
                if runtime_val < 10000:  # Likely minutes
                    runtime_str = self.format_time(runtime_val * 60)
                else:  # Likely seconds
                    runtime_str = self.format_time(runtime_val)
            except (ValueError, TypeError):
                runtime_str = str(runtime)
        else:
            runtime_str = "N/A"
        print(f"  Runtime Remaining:        {runtime_str}")
        
        # Replace Indicator
        replace_ind = battery_results.get('upsSmartBatteryReplaceIndicator')
        if replace_ind is not None:
            try:
                replace_int = int(str(replace_ind))
                replace_str = "Yes" if replace_int == 1 else "No"
            except (ValueError, TypeError):
                replace_str = str(replace_ind)
        else:
            replace_str = "N/A"
        print(f"  Replace Indicator:        {replace_str}")
        
        # Full Charge Voltage
        full_charge_voltage = battery_results.get('upsSmartBatteryFullChargeVoltage')
        print(f"  Full Charge Voltage:      {self.format_value(full_charge_voltage, 'Voltage')}")
        
        # Battery Current
        battery_current = battery_results.get('upsSmartBatteryCurrent')
        print(f"  Battery Current:          {self.format_value(battery_current, 'Current')}")
        
        # Last Replace Date
        last_replace = battery_results.get('upsBaseBatteryLastReplaceDate')
        print(f"  Last Replace Date:        {self.format_value(last_replace, 'Date')}")
        
        results.update(battery_results)
        return results
    
    def query_input_power(self) -> Dict[str, Any]:
        """Query input power monitoring."""
        print("\n" + "=" * 80)
        print("3. INPUT POWER MONITORING")
        print("=" * 80)
        
        results = {}
        input_results = self.query_multiple_oids(INPUT_OIDS, show_errors=False)
        
        # Line Voltage
        line_voltage = input_results.get('upsSmartInputLineVoltage') or input_results.get('upsInputVoltage')
        print(f"  Line Voltage:             {self.format_value(line_voltage, 'Voltage')}")
        
        # Max/Min Line Voltage
        max_voltage = input_results.get('upsSmartInputMaxLineVoltage')
        min_voltage = input_results.get('upsSmartInputMinLineVoltage')
        print(f"  Max Line Voltage (1min):  {self.format_value(max_voltage, 'Voltage')}")
        print(f"  Min Line Voltage (1min):  {self.format_value(min_voltage, 'Voltage')}")
        
        # Input Frequency
        frequency = input_results.get('upsSmartInputFrequency') or input_results.get('upsInputFrequency')
        print(f"  Input Frequency:          {self.format_value(frequency, 'Frequency')}")
        
        # Line Fail Cause
        fail_cause = input_results.get('upsSmartInputLineFailCause')
        if fail_cause is not None:
            try:
                cause_int = int(str(fail_cause))
                cause_str = LINE_FAIL_CAUSE.get(cause_int, f"unknown({cause_int})")
            except (ValueError, TypeError):
                cause_str = str(fail_cause)
        else:
            cause_str = "N/A"
        print(f"  Line Fail Cause:           {cause_str}")
        
        # Input Phase
        phase = input_results.get('upsBaseInputPhase')
        print(f"  Input Phase:              {self.format_value(phase, 'Phase')}")
        
        results.update(input_results)
        return results
    
    def query_output_power(self) -> Dict[str, Any]:
        """Query output power status."""
        print("\n" + "=" * 80)
        print("4. OUTPUT POWER STATUS")
        print("=" * 80)
        
        results = {}
        output_results = self.query_multiple_oids(OUTPUT_OIDS, show_errors=False)
        
        # Output Status
        status_val = output_results.get('upsBaseOutputStatus') or output_results.get('upsOutputSource')
        if status_val is not None:
            try:
                status_int = int(str(status_val))
                status_str = OUTPUT_STATUS.get(status_int, f"unknown({status_int})")
            except (ValueError, TypeError):
                status_str = str(status_val)
        else:
            status_str = "N/A"
        print(f"  Output Status:            {status_str}")
        
        # Output Voltage
        voltage = output_results.get('upsSmartOutputVoltage') or output_results.get('upsOutputVoltage')
        print(f"  Output Voltage:           {self.format_value(voltage, 'Voltage')}")
        
        # Output Frequency
        frequency = output_results.get('upsSmartOutputFrequency') or output_results.get('upsOutputFrequency')
        print(f"  Output Frequency:          {self.format_value(frequency, 'Frequency')}")
        
        # Output Load
        load = output_results.get('upsSmartOutputLoad') or output_results.get('upsOutputLoad')
        print(f"  Output Load:               {self.format_value(load, 'Load')}")
        
        results.update(output_results)
        return results
    
    def query_ats_identification(self) -> Dict[str, Any]:
        """Query ATS identification information."""
        print("\n" + "=" * 80)
        print("1. ATS IDENTIFICATION INFORMATION")
        print("=" * 80)
        print("Querying ATS identification OIDs...")
        
        results = {}
        # Try querying with .0 first, then without if needed
        ident_results = {}
        for name, oid in ATS_IDENT_OIDS.items():
            value = self.query_oid(oid, name, try_without_zero=True)
            if value is None and oid.endswith('.0'):
                # Try without .0
                alt_oid = oid[:-2]
                value = self.query_oid(alt_oid, name, try_without_zero=False)
            ident_results[name] = value
        
        print(f"  Model Name:              {self.format_value(ident_results.get('atsIdentGroupModel'), 'Model')}")
        print(f"  Serial Number:           {self.format_value(ident_results.get('atsIdentGroupSerialNumber'), 'Serial')}")
        print(f"  Manufacturer:            {self.format_value(ident_results.get('atsIdentGroupManufacturer'), 'Manufacturer')}")
        print(f"  Firmware Revision:       {self.format_value(ident_results.get('atsIdentGroupFirmwareRevision'), 'Firmware')}")
        print(f"  Agent Firmware Revision: {self.format_value(ident_results.get('atsIdentGroupAgentFirmwareRevision'), 'AgentFirmware')}")
        
        results.update(ident_results)
        return results
    
    def query_ats_input(self) -> Dict[str, Any]:
        """Query ATS input power status."""
        print("\n" + "=" * 80)
        print("2. ATS INPUT POWER STATUS")
        print("=" * 80)
        
        results = {}
        input_results = self.query_multiple_oids(ATS_INPUT_OIDS, show_errors=False, try_without_zero=True)
        
        # Preference
        preference = input_results.get('atsInputGroupPreference')
        print(f"  Output Source Priority:   {self.format_value(preference, 'Preference')}")
        
        # Source A Status
        source_a_status = input_results.get('atsInputGroupSourceAstatus')
        if source_a_status is not None:
            try:
                status_int = int(str(source_a_status))
                status_str = SOURCE_STATUS.get(status_int, f"unknown({status_int})")
            except (ValueError, TypeError):
                status_str = str(source_a_status)
        else:
            status_str = "N/A"
        print(f"  Source A Status:          {status_str}")
        
        print(f"  Source A Voltage:         {self.format_value(input_results.get('atsInputGroupSourceAinputVoltage'), 'Voltage')}")
        print(f"  Source A Frequency:       {self.format_value(input_results.get('atsInputGroupSourceAinputFrequency'), 'Frequency')}")
        print(f"  Source A Voltage Range:   {self.format_value(input_results.get('atsInputGroupSourceAvoltageLowerLimit'), 'Voltage')} - {self.format_value(input_results.get('atsInputGroupSourceAvoltageUpperLimit'), 'Voltage')}")
        print(f"  Source A Frequency Range: {self.format_value(input_results.get('atsInputGroupSourceAfrequencyLowerLimit'), 'Frequency')} - {self.format_value(input_results.get('atsInputGroupSourceAfrequencyUpperLimit'), 'Frequency')}")
        
        # Source B Status
        source_b_status = input_results.get('atsInputGroupSourceBstatus')
        if source_b_status is not None:
            try:
                status_int = int(str(source_b_status))
                status_str = SOURCE_STATUS.get(status_int, f"unknown({status_int})")
            except (ValueError, TypeError):
                status_str = str(source_b_status)
        else:
            status_str = "N/A"
        print(f"  Source B Status:          {status_str}")
        
        print(f"  Source B Voltage:         {self.format_value(input_results.get('atsInputGroupSourceBinputVoltage'), 'Voltage')}")
        print(f"  Source B Frequency:       {self.format_value(input_results.get('atsInputGroupSourceBinputFrequency'), 'Frequency')}")
        print(f"  Source B Voltage Range:   {self.format_value(input_results.get('atsInputGroupSourceBvoltageLowerLimit'), 'Voltage')} - {self.format_value(input_results.get('atsInputGroupSourceBvoltageUpperLimit'), 'Voltage')}")
        print(f"  Source B Frequency Range: {self.format_value(input_results.get('atsInputGroupSourceBfrequencyLowerLimit'), 'Frequency')} - {self.format_value(input_results.get('atsInputGroupSourceBfrequencyUpperLimit'), 'Frequency')}")
        
        results.update(input_results)
        return results
    
    def query_ats_output(self) -> Dict[str, Any]:
        """Query ATS output power status."""
        print("\n" + "=" * 80)
        print("3. ATS OUTPUT POWER STATUS")
        print("=" * 80)
        
        results = {}
        output_results = self.query_multiple_oids(ATS_OUTPUT_OIDS, show_errors=False, try_without_zero=True)
        
        print(f"  Output Source:            {self.format_value(output_results.get('atsOutputGroupOutputSource'), 'Source')}")
        print(f"  Output Voltage:           {self.format_value(output_results.get('atsOutputGroupOutputVoltage'), 'Voltage')}")
        print(f"  Output Frequency:         {self.format_value(output_results.get('atsOutputGroupOutputFequency'), 'Frequency')}")
        print(f"  Output Current:           {self.format_value(output_results.get('atsOutputGroupOutputCurrent'), 'Current')}")
        print(f"  Output Load:              {self.format_value(output_results.get('atsOutputGroupLoad'), 'Load')}")
        
        results.update(output_results)
        return results
    
    def query_ats_hmi_switch(self) -> Dict[str, Any]:
        """Query ATS HMI and switch settings."""
        print("\n" + "=" * 80)
        print("4. ATS HMI AND SWITCH SETTINGS")
        print("=" * 80)
        
        results = {}
        hmi_results = self.query_multiple_oids(ATS_HMI_SWITCH_OIDS, show_errors=False, try_without_zero=True)
        
        # Buzzer
        buzzer = hmi_results.get('atsHmiSwitchGroupBuzzer')
        if buzzer is not None:
            try:
                buzzer_int = int(str(buzzer))
                buzzer_str = "Enabled" if buzzer_int == 2 else "Disabled"
            except (ValueError, TypeError):
                buzzer_str = str(buzzer)
        else:
            buzzer_str = "N/A"
        print(f"  Buzzer Status:            {buzzer_str}")
        
        # Alarm
        alarm = hmi_results.get('atsHmiSwitchGroupAtsAlarm')
        if alarm is not None:
            try:
                alarm_int = int(str(alarm))
                alarm_str = "Alarm Occurred" if alarm_int == 2 else "No Alarm"
            except (ValueError, TypeError):
                alarm_str = str(alarm)
        else:
            alarm_str = "N/A"
        print(f"  ATS Alarm Status:         {alarm_str}")
        
        # Auto Return
        auto_return = hmi_results.get('atsHmiSwitchGroupAutoReturn')
        if auto_return is not None:
            try:
                auto_int = int(str(auto_return))
                auto_str = "On" if auto_int == 2 else "Off"
            except (ValueError, TypeError):
                auto_str = str(auto_return)
        else:
            auto_str = "N/A"
        print(f"  Auto Return:               {auto_str}")
        
        # Transfer by Load
        transfer_load = hmi_results.get('atsHmiSwitchGroupSourceTransferByLoad')
        if transfer_load is not None:
            try:
                load_int = int(str(transfer_load))
                load_str = "On" if load_int == 2 else "Off"
            except (ValueError, TypeError):
                load_str = str(transfer_load)
        else:
            load_str = "N/A"
        print(f"  Transfer by Load:          {load_str}")
        
        # Transfer by Phase
        transfer_phase = hmi_results.get('atsHmiSwitchGroupSourceTransferByPhase')
        if transfer_phase is not None:
            try:
                phase_int = int(str(transfer_phase))
                phase_str = "On" if phase_int == 2 else "Off"
            except (ValueError, TypeError):
                phase_str = str(transfer_phase)
        else:
            phase_str = "N/A"
        print(f"  Transfer by Phase:         {phase_str}")
        
        results.update(hmi_results)
        return results
    
    def query_ats_miscellaneous(self) -> Dict[str, Any]:
        """Query ATS miscellaneous information."""
        print("\n" + "=" * 80)
        print("5. ATS MISCELLANEOUS INFORMATION")
        print("=" * 80)
        
        results = {}
        misc_results = self.query_multiple_oids(ATS_MISC_OIDS, show_errors=False, try_without_zero=True)
        
        print(f"  System Temperature:       {self.format_value(misc_results.get('atsMiscellaneousGroupAtsSystemTemperture'), 'Temperature')}")
        print(f"  System Max Current:        {self.format_value(misc_results.get('atsMiscellaneousGroupSystemMaxCurrent'), 'Current')}")
        
        results.update(misc_results)
        return results
    
    def query_ists_product(self) -> Dict[str, Any]:
        """Query i-STS product information."""
        print("\n" + "=" * 80)
        print("1. i-STS PRODUCT INFORMATION")
        print("=" * 80)
        
        results = {}
        product_results = self.query_multiple_oids(ISTS_PRODUCT_OIDS, show_errors=False)
        
        print(f"  Product Name:             {self.format_value(product_results.get('istsProductName'), 'String')}")
        print(f"  Product Version:          {self.format_value(product_results.get('istsProductVersion'), 'String')}")
        print(f"  Version Date:             {self.format_value(product_results.get('istsVersionDate'), 'String')}")
        
        results.update(product_results)
        return results
    
    def query_ists_control(self) -> Dict[str, Any]:
        """Query i-STS control/operation variables."""
        print("\n" + "=" * 80)
        print("2. i-STS CONTROL/OPERATION STATUS")
        print("=" * 80)
        
        results = {}
        control_results = self.query_multiple_oids(ISTS_CONTROL_OIDS, show_errors=False)
        
        # Active Supply
        active_supply = control_results.get('istsActiveSupply')
        if active_supply is not None:
            try:
                supply_int = int(str(active_supply))
                supply_str = ISTS_SUPPLY_STATUS.get(supply_int, f"unknown({supply_int})")
            except (ValueError, TypeError):
                supply_str = str(active_supply)
        else:
            supply_str = "N/A"
        print(f"  Active Supply:             {supply_str}")
        
        # Preferred Supply
        preferred_supply = control_results.get('istsPreferredSupply')
        if preferred_supply is not None:
            try:
                pref_int = int(str(preferred_supply))
                pref_str = ISTS_SUPPLY_STATUS.get(pref_int, f"unknown({pref_int})")
            except (ValueError, TypeError):
                pref_str = str(preferred_supply)
        else:
            pref_str = "N/A"
        print(f"  Preferred Supply:          {pref_str}")
        
        print(f"  Supply 1 Frequency:        {self.format_value(control_results.get('istsFreq1'), 'Frequency')}")
        print(f"  Supply 2 Frequency:        {self.format_value(control_results.get('istsFreq2'), 'Frequency')}")
        print(f"  Sync Status:               {self.format_value(control_results.get('istsSync'), 'Integer')}")
        print(f"  Neutral Current:           {self.format_value(control_results.get('istsNeutralI'), 'Integer')}")
        
        results.update(control_results)
        return results
    
    def query_ists_input(self) -> Dict[str, Any]:
        """Query i-STS input power status."""
        print("\n" + "=" * 80)
        print("3. i-STS INPUT POWER STATUS")
        print("=" * 80)
        
        results = {}
        # Note: Input variables are SEQUENCE/TABLE, need to walk
        print("  Walking input table...")
        try:
            input_walk = self.walk_oid(ISTS_INPUT_BASE_OID, max_results=20)
            s1_values = []
            s2_values = []
            
            for oid, value in input_walk:
                # S1 is at 43.6.1.4.1.32796.3.2.2.x
                if '.3.2.2.' in oid:
                    s1_values.append((oid, value))
                # S2 is at 43.6.1.4.1.32796.3.2.3.x
                elif '.3.2.3.' in oid:
                    s2_values.append((oid, value))
            
            if s1_values:
                # Get first S1 value (usually index 1)
                s1_oid, s1_value = s1_values[0]
                print(f"  Supply 1 Voltage:          {self.format_value(s1_value, 'Voltage')} (from {s1_oid})")
                results['istsS1'] = s1_value
            else:
                print(f"  Supply 1 Voltage:          N/A (no data found)")
            
            if s2_values:
                # Get first S2 value (usually index 1)
                s2_oid, s2_value = s2_values[0]
                print(f"  Supply 2 Voltage:          {self.format_value(s2_value, 'Voltage')} (from {s2_oid})")
                results['istsS2'] = s2_value
            else:
                print(f"  Supply 2 Voltage:          N/A (no data found)")
            
            # Show all found if multiple entries
            if len(s1_values) > 1 or len(s2_values) > 1:
                print(f"  [INFO] Found {len(s1_values)} S1 entries and {len(s2_values)} S2 entries")
        except Exception as e:
            print(f"  [WARNING] Could not query input variables: {e}")
        
        return results
    
    def query_ists_output(self) -> Dict[str, Any]:
        """Query i-STS output power status."""
        print("\n" + "=" * 80)
        print("4. i-STS OUTPUT POWER STATUS")
        print("=" * 80)
        
        results = {}
        # Note: Output variables are SEQUENCE/TABLE, need to walk
        print("  Walking output table...")
        try:
            output_walk = self.walk_oid(ISTS_OUTPUT_BASE_OID, max_results=30)
            output_data = {}
            
            # Map OID patterns to descriptions
            oid_patterns = {
                '.3.3.2.': ('S3', 'Voltage', 'Output Voltage'),
                '.3.3.3.': ('Current', 'Current', 'Output Current'),
                '.3.3.4.': ('KVA', 'Power', 'kVA'),
                '.3.3.5.': ('KW', 'Power', 'kW'),
                '.3.3.6.': ('PF', 'Decimal', 'Power Factor'),
                '.3.3.7.': ('CF', 'Decimal', 'Crest Factor'),
                '.3.3.8.': ('THDIVal', 'Percent', 'THDI Value'),
                '.3.3.9.': ('THDVVal', 'Percent', 'THDV Value'),
            }
            
            for oid, value in output_walk:
                for pattern, (key, fmt, desc) in oid_patterns.items():
                    if pattern in oid:
                        # Store first occurrence of each type
                        if key not in output_data:
                            output_data[key] = (value, desc, fmt)
                        break
            
            # Display results
            if 'S3' in output_data:
                value, desc, fmt = output_data['S3']
                print(f"  {desc}:                  {self.format_value(value, fmt)}")
                results['istsS3'] = value
            
            if 'Current' in output_data:
                value, desc, fmt = output_data['Current']
                print(f"  {desc}:                  {self.format_value(value, fmt)}")
                results['istsCurrent'] = value
            
            if 'KVA' in output_data:
                value, desc, fmt = output_data['KVA']
                print(f"  {desc}:                  {self.format_value(value, fmt)}")
                results['istsKVA'] = value
            
            if 'KW' in output_data:
                value, desc, fmt = output_data['KW']
                print(f"  {desc}:                  {self.format_value(value, fmt)}")
                results['istsKW'] = value
            
            if 'PF' in output_data:
                value, desc, fmt = output_data['PF']
                print(f"  {desc}:                  {self.format_value(value, fmt)}")
                results['istsPF'] = value
            
            if 'CF' in output_data:
                value, desc, fmt = output_data['CF']
                print(f"  {desc}:                  {self.format_value(value, fmt)}")
                results['istsCF'] = value
            
            if 'THDIVal' in output_data:
                value, desc, fmt = output_data['THDIVal']
                print(f"  {desc}:                  {self.format_value(value, fmt)}")
                results['istsTHDIVal'] = value
            
            if 'THDVVal' in output_data:
                value, desc, fmt = output_data['THDVVal']
                print(f"  {desc}:                  {self.format_value(value, fmt)}")
                results['istsTHDVVal'] = value
            
            if not output_data:
                print(f"  [WARNING] No output data found in table")
        except Exception as e:
            print(f"  [WARNING] Could not query output variables: {e}")
        
        return results
    
    def query_ists_alarms(self) -> Dict[str, Any]:
        """Query i-STS alarm status."""
        print("\n" + "=" * 80)
        print("5. i-STS ALARM STATUS")
        print("=" * 80)
        
        results = {}
        alarms = self.query_oid(ISTS_ALARMS_OID, 'Alarms')
        
        if alarms is not None:
            try:
                alarm_value = int(str(alarms))
                # Parse bit flags
                active_alarms = []
                for bit, alarm_name in ISTS_ALARM_FLAGS.items():
                    if alarm_value & (1 << bit):
                        active_alarms.append(alarm_name)
                
                if active_alarms:
                    print(f"  Active Alarms:             {', '.join(active_alarms)}")
                else:
                    print(f"  Active Alarms:             None (All Normal)")
                print(f"  Alarm Value (hex):         0x{alarm_value:04X} ({alarm_value})")
            except (ValueError, TypeError):
                print(f"  Alarm Status:              {alarms}")
        else:
            print(f"  Alarm Status:              N/A")
        
        results['istsAlarms'] = alarms
        return results
    
    def query_ists_utilisation(self) -> Dict[str, Any]:
        """Query i-STS utilisation/statistics."""
        print("\n" + "=" * 80)
        print("6. i-STS UTILISATION/STATISTICS")
        print("=" * 80)
        
        results = {}
        util_results = self.query_multiple_oids(ISTS_UTILISATION_OIDS, show_errors=False)
        
        print(f"  Hours on Supply 1:          {self.format_value(util_results.get('istsHours1'), 'Hours')}")
        print(f"  Hours on Supply 2:          {self.format_value(util_results.get('istsHours2'), 'Hours')}")
        print(f"  Hours on Preferred:         {self.format_value(util_results.get('istsHoursPreferred'), 'Hours')}")
        print(f"  Total Hours of Operation:   {self.format_value(util_results.get('istsHoursOperation'), 'Hours')}")
        print(f"  Hours with No Output:       {self.format_value(util_results.get('istsHoursNoOutput'), 'Hours')}")
        print(f"  Forced Transfers:            {self.format_value(util_results.get('istsNumForcedXfers'), 'Integer')}")
        print(f"  Sync Losses:                {self.format_value(util_results.get('istsNumSyncLosses'), 'Integer')}")
        print(f"  Supply Outages:              {self.format_value(util_results.get('istsNumSupplyOuts'), 'Integer')}")
        
        # Time values (TIME_TICKS - in hundredths of seconds)
        last_load_fault = util_results.get('istsLastLoadFault')
        if last_load_fault:
            try:
                ticks = int(str(last_load_fault))
                seconds = ticks // 100  # Convert from hundredths to seconds
                print(f"  Last Load Fault:            {self.format_time(seconds)}")
            except (ValueError, TypeError):
                print(f"  Last Load Fault:            {last_load_fault}")
        
        last_supply_out = util_results.get('istsLastSupplyOut')
        if last_supply_out:
            try:
                ticks = int(str(last_supply_out))
                seconds = ticks // 100  # Convert from hundredths to seconds
                print(f"  Last Supply Out:            {self.format_time(seconds)}")
            except (ValueError, TypeError):
                print(f"  Last Supply Out:            {last_supply_out}")
        
        results.update(util_results)
        return results
    
    def query_ists_all(self) -> Dict[str, Any]:
        """Query all i-STS status information."""
        print(f"\n{'=' * 80}")
        print(f"i-STS STATUS QUERY")
        print(f"{'=' * 80}")
        print(f"Host: {self.host}")
        print(f"Community: {self.community}")
        print(f"Port: {self.port}")
        print(f"Query Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        all_results = {}
        
        try:
            # Test connection first
            print("\nTesting connectivity...", end=" ", flush=True)
            test_oid = '1.3.6.1.2.1.1.1.0'  # sysDescr
            test_result = self.query_oid(test_oid, None)
            if test_result is None:
                print("FAILED", file=sys.stderr)
                print(f"\n[ERROR] Cannot connect to i-STS at {self.host}:{self.port}", file=sys.stderr)
                return all_results
            else:
                print("OK")
            
            all_results['product'] = self.query_ists_product()
            all_results['control'] = self.query_ists_control()
            all_results['input'] = self.query_ists_input()
            all_results['output'] = self.query_ists_output()
            all_results['alarms'] = self.query_ists_alarms()
            all_results['utilisation'] = self.query_ists_utilisation()
            
            print(f"\n{'=' * 80}")
            print("QUERY COMPLETE")
            print(f"{'=' * 80}")
            
        except KeyboardInterrupt:
            print("\n\n[WARNING] Query interrupted by user", file=sys.stderr)
        except Exception as e:
            print(f"\n[ERROR] Query failed: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        
        return all_results
    
    def query_ats_all(self) -> Dict[str, Any]:
        """Query all ATS status information."""
        print(f"\n{'=' * 80}")
        print(f"ATS STATUS QUERY - Borri STS32A")
        print(f"{'=' * 80}")
        print(f"Host: {self.host}")
        print(f"Community: {self.community}")
        print(f"Port: {self.port}")
        print(f"Query Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if self.debug_file:
            print(f"Debug File: {self.debug_file}")
        
        all_results = {}
        
        try:
            # Test connection first
            print("\nTesting connectivity...", end=" ", flush=True)
            test_oid = '1.3.6.1.2.1.1.1.0'  # sysDescr
            test_result = self.query_oid(test_oid, None)
            if test_result is None:
                print("FAILED", file=sys.stderr)
                print(f"\n[ERROR] Cannot connect to ATS at {self.host}:{self.port}", file=sys.stderr)
                print(f"[INFO] Attempting to walk ATS base OID tree for debugging...", file=sys.stderr)
                # Try walking the ATS base OID to see what's available
                ats_walk = self.walk_oid(ATS_BASE_OID, max_results=50)
                if ats_walk:
                    print(f"[INFO] Found {len(ats_walk)} OIDs under {ATS_BASE_OID}:", file=sys.stderr)
                    for oid, val in ats_walk[:10]:
                        print(f"  {oid}: {val}", file=sys.stderr)
                self._write_debug_file()
                return all_results
            else:
                print("OK")
            
            all_results['identification'] = self.query_ats_identification()
            all_results['input'] = self.query_ats_input()
            all_results['output'] = self.query_ats_output()
            all_results['hmi_switch'] = self.query_ats_hmi_switch()
            all_results['miscellaneous'] = self.query_ats_miscellaneous()
            
            print("\n" + "=" * 80)
            print("QUERY COMPLETE")
            print("=" * 80)
            
            # Write debug file if requested
            if self.debug_file:
                self._write_debug_file()
            
        except KeyboardInterrupt:
            print("\n\n[INTERRUPTED] Query cancelled by user", file=sys.stderr)
            if self.debug_file:
                self._write_debug_file()
            sys.exit(1)
        except Exception as e:
            print(f"\n[ERROR] Unexpected error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            if self.debug_file:
                self._write_debug_file()
            sys.exit(1)
        
        return all_results
    
    def query_three_phase(self) -> Dict[str, Any]:
        """Query three-phase UPS support."""
        print("\n" + "=" * 80)
        print("5. THREE-PHASE UPS SUPPORT (Enterprise Grade)")
        print("=" * 80)
        
        results = {}
        three_phase_results = self.query_multiple_oids(THREE_PHASE_OIDS, show_errors=False)
        
        # Check if three-phase data is available
        has_three_phase = any(v is not None for v in three_phase_results.values())
        
        if not has_three_phase:
            print("  [INFO] Three-phase UPS data not available (device may be single-phase)")
            return results
        
        # Input Phase Readings
        print("\n  Input Phase Readings:")
        input_freq = three_phase_results.get('upsThreePhaseInputFrequency')
        print(f"    Input Frequency:        {self.format_value(input_freq, 'Frequency')}")
        
        input_voltage_r = three_phase_results.get('upsThreePhaseInputVoltageR')
        input_voltage_s = three_phase_results.get('upsThreePhaseInputVoltageS')
        input_voltage_t = three_phase_results.get('upsThreePhaseInputVoltageT')
        print(f"    Input Voltage R:         {self.format_value(input_voltage_r, 'Voltage')}")
        print(f"    Input Voltage S:         {self.format_value(input_voltage_s, 'Voltage')}")
        print(f"    Input Voltage T:         {self.format_value(input_voltage_t, 'Voltage')}")
        
        # Output Phase Readings
        print("\n  Output Phase Readings:")
        output_freq = three_phase_results.get('upsThreePhaseOutputFrequency')
        print(f"    Output Frequency:        {self.format_value(output_freq, 'Frequency')}")
        
        output_voltage_r = three_phase_results.get('upsThreePhaseOutputVoltageR')
        output_voltage_s = three_phase_results.get('upsThreePhaseOutputVoltageS')
        output_voltage_t = three_phase_results.get('upsThreePhaseOutputVoltageT')
        print(f"    Output Voltage R:         {self.format_value(output_voltage_r, 'Voltage')}")
        print(f"    Output Voltage S:         {self.format_value(output_voltage_s, 'Voltage')}")
        print(f"    Output Voltage T:         {self.format_value(output_voltage_t, 'Voltage')}")
        
        output_load_r = three_phase_results.get('upsThreePhaseOutputLoadR')
        output_load_s = three_phase_results.get('upsThreePhaseOutputLoadS')
        output_load_t = three_phase_results.get('upsThreePhaseOutputLoadT')
        print(f"    Load R:                   {self.format_value(output_load_r, 'Load')}")
        print(f"    Load S:                   {self.format_value(output_load_s, 'Load')}")
        print(f"    Load T:                   {self.format_value(output_load_t, 'Load')}")
        
        # Bypass Source
        print("\n  Bypass Source:")
        bypass_freq = three_phase_results.get('upsThreePhaseBypassFrequency')
        print(f"    Bypass Frequency:        {self.format_value(bypass_freq, 'Frequency')}")
        
        bypass_voltage_r = three_phase_results.get('upsThreePhaseBypassVoltageR')
        bypass_voltage_s = three_phase_results.get('upsThreePhaseBypassVoltageS')
        bypass_voltage_t = three_phase_results.get('upsThreePhaseBypassVoltageT')
        print(f"    Bypass Voltage R:         {self.format_value(bypass_voltage_r, 'Voltage')}")
        print(f"    Bypass Voltage S:         {self.format_value(bypass_voltage_s, 'Voltage')}")
        print(f"    Bypass Voltage T:         {self.format_value(bypass_voltage_t, 'Voltage')}")
        
        # DC and Rectifier Status
        print("\n  DC and Rectifier Status:")
        rectifier_error = three_phase_results.get('upsThreePhaseRectifierRotationError')
        print(f"    Rectifier Rotation Error: {self.format_value(rectifier_error)}")
        
        low_battery_shutdown = three_phase_results.get('upsThreePhaseLowBatteryShutdown')
        if low_battery_shutdown is not None:
            try:
                shutdown_int = int(str(low_battery_shutdown))
                shutdown_str = FAULT_STATUS.get(shutdown_int, str(low_battery_shutdown))
            except (ValueError, TypeError):
                shutdown_str = str(low_battery_shutdown)
        else:
            shutdown_str = "N/A"
        print(f"    Low Battery Shutdown:     {shutdown_str}")
        
        charge_status = three_phase_results.get('upsThreePhaseChargeStatus')
        if charge_status is not None:
            try:
                charge_int = int(str(charge_status))
                charge_str = CHARGE_STATUS.get(charge_int, f"unknown({charge_int})")
            except (ValueError, TypeError):
                charge_str = str(charge_status)
        else:
            charge_str = "N/A"
        print(f"    Charge Status:            {charge_str}")
        
        rectifier_status = three_phase_results.get('upsThreePhaseRectifierOperatingStatus')
        if rectifier_status is not None:
            try:
                rect_int = int(str(rectifier_status))
                rect_str = RECTIFIER_STATUS.get(rect_int, f"unknown({rect_int})")
            except (ValueError, TypeError):
                rect_str = str(rectifier_status)
        else:
            rect_str = "N/A"
        print(f"    Rectifier Operating Status: {rect_str}")
        
        in_out_config = three_phase_results.get('upsThreePhaseInOutConfiguration')
        if in_out_config is not None:
            try:
                config_int = int(str(in_out_config))
                config_str = IN_OUT_CONFIG.get(config_int, f"unknown({config_int})")
            except (ValueError, TypeError):
                config_str = str(in_out_config)
        else:
            config_str = "N/A"
        print(f"    In/Out Configuration:      {config_str}")
        
        # Fault Status Indicators
        print("\n  Fault Status Indicators:")
        fault_statuses = {
            'Emergency Stop': three_phase_results.get('upsThreePhaseEmergencyStop'),
            'High DC Shutdown': three_phase_results.get('upsThreePhaseHighDCShutdown'),
            'Bypass Breaker': three_phase_results.get('upsThreePhaseBypassBreaker'),
            'Over Load': three_phase_results.get('upsThreePhaseOverLoad'),
            'Inverter Output Fail': three_phase_results.get('upsThreePhaseInverterOutputFail'),
            'Over Temperature': three_phase_results.get('upsThreePhaseOverTemperature'),
            'Short Circuit': three_phase_results.get('upsThreePhaseShortCircuit'),
        }
        
        for fault_name, fault_val in fault_statuses.items():
            if fault_val is not None:
                try:
                    fault_int = int(str(fault_val))
                    fault_str = FAULT_STATUS.get(fault_int, str(fault_val))
                except (ValueError, TypeError):
                    fault_str = str(fault_val)
            else:
                fault_str = "N/A"
            print(f"    {fault_name:25s}: {fault_str}")
        
        results.update(three_phase_results)
        return results
    
    def query_all(self) -> Dict[str, Any]:
        """Query all UPS status information."""
        print(f"\n{'=' * 80}")
        print(f"UPS STATUS QUERY")
        print(f"{'=' * 80}")
        print(f"Host: {self.host}")
        print(f"Community: {self.community}")
        print(f"Port: {self.port}")
        print(f"Query Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        all_results = {}
        connection_ok = False
        
        try:
            # Test connection first
            ident_results = self.query_identification()
            if ident_results:
                connection_ok = True
                all_results['identification'] = ident_results
            else:
                print("\n" + "=" * 80)
                print("CONNECTION FAILED")
                print("=" * 80)
                print(f"\n[ERROR] Cannot connect to UPS at {self.host}:{self.port}")
                print(f"[ERROR] Please check the connection and try again.")
                return all_results
            
            all_results['battery'] = self.query_battery_status()
            all_results['input'] = self.query_input_power()
            all_results['output'] = self.query_output_power()
            all_results['three_phase'] = self.query_three_phase()
            
            print("\n" + "=" * 80)
            print("QUERY COMPLETE")
            print("=" * 80)
            
            # Show summary of key status
            if connection_ok:
                print("\nSUMMARY:")
                output_status = None
                battery_status = None
                battery_capacity = None
                
                # Get output status
                if 'output' in all_results:
                    output_data = all_results['output']
                    if 'upsBaseOutputStatus' in output_data and output_data['upsBaseOutputStatus']:
                        try:
                            status_int = int(str(output_data['upsBaseOutputStatus']))
                            output_status = OUTPUT_STATUS.get(status_int, f"unknown({status_int})")
                        except:
                            pass
                
                # Get battery status
                if 'battery' in all_results:
                    battery_data = all_results['battery']
                    if 'upsBaseBatteryStatus' in battery_data and battery_data['upsBaseBatteryStatus']:
                        try:
                            status_int = int(str(battery_data['upsBaseBatteryStatus']))
                            battery_status = BATTERY_STATUS.get(status_int, f"unknown({status_int})")
                        except:
                            pass
                    if 'upsSmartBatteryCapacity' in battery_data and battery_data['upsSmartBatteryCapacity']:
                        battery_capacity = battery_data['upsSmartBatteryCapacity']
                
                if output_status:
                    print(f"  Output Status: {output_status}")
                if battery_status:
                    print(f"  Battery Status: {battery_status}")
                if battery_capacity is not None:
                    print(f"  Battery Capacity: {self.format_value(battery_capacity, 'Capacity')}")
            
        except KeyboardInterrupt:
            print("\n\n[INTERRUPTED] Query cancelled by user", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"\n[ERROR] Unexpected error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        return all_results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Query UPS/ATS/i-STS status via SNMP (using SNMPv2c)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query default device (Borri STS32A at 192.168.111.173)
  %(prog)s
  
  # Query ATS device specifically
  %(prog)s --host 192.168.111.173 --device-type ats
  
  # Query i-STS device specifically
  %(prog)s --host 192.168.1.200 --device-type ists
  
  # Query specific ATS section
  %(prog)s --host 192.168.111.173 --section ats-input
  
  # Query specific i-STS section
  %(prog)s --host 192.168.1.200 --section ists-control
  
  # Discover all available OIDs
  %(prog)s --host 192.168.111.173 --section discover
  
  # Query UPS device
  %(prog)s --host 192.168.1.100 --device-type ups
  
  # Use custom community string
  %(prog)s --host 192.168.111.173 --community private
  
  # Query with debug file output
  %(prog)s --host 192.168.111.173 --device-type ats --debug-file snmp_debug.txt
        """
    )
    
    parser.add_argument(
        '--host', '-H',
        type=str,
        default=DEFAULT_UPS_IP,
        help=f'UPS device IP address or hostname (default: {DEFAULT_UPS_IP} from config.py)'
    )
    
    parser.add_argument(
        '--community', '-c',
        type=str,
        default=DEFAULT_COMMUNITY,
        help=f'SNMP community string (default: {DEFAULT_COMMUNITY})'
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=DEFAULT_PORT,
        help=f'SNMP port (default: {DEFAULT_PORT})'
    )
    
    parser.add_argument(
        '--section', '-s',
        type=str,
        choices=['identification', 'battery', 'input', 'output', 'three-phase', 'all', 'discover', 
                 'ats-identification', 'ats-input', 'ats-output', 'ats-hmi', 'ats-misc', 'ats-all',
                 'ists-product', 'ists-control', 'ists-input', 'ists-output', 'ists-alarms', 'ists-utilisation', 'ists-all'],
        default='all',
        help='Query specific section only, "ats-all" for ATS device, "ists-all" for i-STS device, or "discover" to find available OIDs (default: all)'
    )
    
    parser.add_argument(
        '--device-type', '-t',
        type=str,
        choices=['auto', 'ups', 'ats', 'ists'],
        default='auto',
        help='Device type: auto (detect), ups, ats, or ists (default: auto)'
    )
    
    parser.add_argument(
        '--discover', '-d',
        action='store_true',
        help='Discover available OIDs on the UPS (same as --section discover)'
    )
    
    parser.add_argument(
        '--debug-file', '-D',
        type=str,
        default=None,
        help='Write all SNMP query responses to a debug file for troubleshooting'
    )
    
    args = parser.parse_args()
    
    # Handle discover flag
    if args.discover:
        args.section = 'discover'
    
    # Create query object
    query = UPSStatusQuery(args.host, args.community, args.port, debug_file=args.debug_file)
    
    # Auto-detect device type if needed
    device_type = args.device_type
    if device_type == 'auto':
        # Try to detect by querying device-specific OIDs
        print("Auto-detecting device type...", end=" ", flush=True)
        # Try i-STS first (43.6.1.4.1.32796)
        ists_test = query.query_oid('43.6.1.4.1.32796.1.1', None)  # i-STS Product Name
        if ists_test is not None:
            device_type = 'ists'
            print("i-STS (Static Transfer Switch) detected")
        else:
            # Try ATS (1.3.6.1.4.1.37662) - check both atsAgent(2) and atsAgent(3)
            # First check sysObjectID to determine which version
            sys_oid = query.query_oid('1.3.6.1.2.1.1.2.0', None)  # sysObjectID
            if sys_oid:
                sys_oid_str = str(sys_oid)
                if '1.3.6.1.4.1.37662.1.2.2' in sys_oid_str:
                    # Device uses atsAgent(2)
                    ats_test = query.query_oid('1.3.6.1.4.1.37662.1.2.2.1.1.1.1.0', None)  # ATS Model
                else:
                    # Try atsAgent(3)
                    ats_test = query.query_oid('1.3.6.1.4.1.37662.1.2.3.1.1.1.1.0', None)  # ATS Model
            else:
                # Fallback: try both
                ats_test = query.query_oid('1.3.6.1.4.1.37662.1.2.2.1.1.1.1.0', None) or \
                          query.query_oid('1.3.6.1.4.1.37662.1.2.3.1.1.1.1.0', None)
            if ats_test is not None:
                device_type = 'ats'
                print("ATS (Automatic Transfer Switch) detected")
            else:
                device_type = 'ups'
                print("UPS detected (or ATS/i-STS not responding)")
    
    # Query based on section
    if args.section == 'discover':
        discovered = query.discover_available_oids()
        if not discovered:
            print("\n[WARNING] No OIDs discovered. Check SNMP connectivity and community string.", file=sys.stderr)
        else:
            print("\n" + "=" * 80)
            print("DISCOVERY COMPLETE")
            print("=" * 80)
            print(f"\nFound OIDs in {len(discovered)} base OID tree(s)")
            print("\nUse this information to identify which OIDs your device supports.")
    elif args.section == 'ists-all' or (args.section == 'all' and device_type == 'ists'):
        query.query_ists_all()
    elif args.section == 'ists-product':
        query.query_ists_product()
    elif args.section == 'ists-control':
        query.query_ists_control()
    elif args.section == 'ists-input':
        query.query_ists_input()
    elif args.section == 'ists-output':
        query.query_ists_output()
    elif args.section == 'ists-alarms':
        query.query_ists_alarms()
    elif args.section == 'ists-utilisation':
        query.query_ists_utilisation()
    elif args.section == 'ats-all' or (args.section == 'all' and device_type == 'ats'):
        query.query_ats_all()
    elif args.section == 'ats-identification':
        query.query_ats_identification()
    elif args.section == 'ats-input':
        query.query_ats_input()
    elif args.section == 'ats-output':
        query.query_ats_output()
    elif args.section == 'ats-hmi':
        query.query_ats_hmi_switch()
    elif args.section == 'ats-misc':
        query.query_ats_miscellaneous()
    elif args.section == 'all':
        if device_type == 'ists':
            query.query_ists_all()
        elif device_type == 'ats':
            query.query_ats_all()
        else:
            query.query_all()
    elif args.section == 'identification':
        if device_type == 'ists':
            query.query_ists_product()
        elif device_type == 'ats':
            query.query_ats_identification()
        else:
            query.query_identification()
    elif args.section == 'battery':
        query.query_battery_status()
    elif args.section == 'input':
        if device_type == 'ists':
            query.query_ists_input()
        elif device_type == 'ats':
            query.query_ats_input()
        else:
            query.query_input_power()
    elif args.section == 'output':
        if device_type == 'ists':
            query.query_ists_output()
        elif device_type == 'ats':
            query.query_ats_output()
        else:
            query.query_output_power()
    elif args.section == 'three-phase':
        query.query_three_phase()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

