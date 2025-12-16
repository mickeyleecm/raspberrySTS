#!/usr/bin/env python3
"""
Get UPS Status Module

This module provides a class to query UPS/ATS/i-STS device status via SNMP GET operations.
It is designed to be used by other programs (like ups_snmp_trap_receiver_v2.py) to get
current device status information.

Uses SNMPv2c protocol and OIDs from GetIDTable.py.

Features:
- Query device identification
- Query battery status
- Query input/output power status
- Query ATS-specific status (Source A/B, Output, HMI settings)
- Query i-STS-specific status
- Auto-detect device type
- Returns structured data (dictionaries) for easy integration
- Can be run as a standalone program with command-line interface
- Supports output to file (text or JSON format)

Requires: Python 3.6+, pysnmp>=4.4.12, pyasn1>=0.4.8

Usage Examples:
==============

1. As a Python Module (for use in other programs):
   -------------------------------------------------
   from GetUPSStatus import GetUPSStatus
   
   # Create status query object
   status = GetUPSStatus('192.168.111.173', community='public')
   
   # Test connectivity
   if status.test_connectivity():
       # Get all status
       all_status = status.get_all_status()
       
       # Or get specific sections
       ident = status.get_identification()
       output = status.get_output_status()
       battery = status.get_battery_status()  # UPS only
       
       # Get ATS-specific status
       input_status = status.get_input_status('ats')
       hmi_settings = status.get_ats_hmi_settings()
       misc = status.get_ats_miscellaneous()

2. As a Standalone Program (command-line):
   ----------------------------------------
   # Query all status (default device from config.py)
   python GetUPSStatus.py
   
   # Query specific device
   python GetUPSStatus.py --host 192.168.111.173
   
   # Query specific section
   python GetUPSStatus.py --host 192.168.111.173 --section identification
   python GetUPSStatus.py --host 192.168.111.173 --section battery
   python GetUPSStatus.py --host 192.168.111.173 --section input
   python GetUPSStatus.py --host 192.168.111.173 --section output
   
   # Query ATS-specific sections
   python GetUPSStatus.py --host 192.168.111.173 --section ats-hmi
   python GetUPSStatus.py --host 192.168.111.173 --section ats-misc
   
   # Output status to text file
   python GetUPSStatus.py --host 192.168.111.173 --output-file status.txt
   
   # Output status to JSON file
   python GetUPSStatus.py --host 192.168.111.173 --output-file status.json --format json
   
   # Use custom community string
   python GetUPSStatus.py --host 192.168.111.173 --community private
   
   # Specify device type explicitly
   python GetUPSStatus.py --host 192.168.111.173 --device-type ats
   
   # Query with custom port
   python GetUPSStatus.py --host 192.168.111.173 --port 1610

3. Command-Line Arguments:
   ------------------------
   --host, -H          Device IP address or hostname
   --community, -c     SNMP community string (default: 'public')
   --port, -p          SNMP port (default: 161)
   --section, -s       Query section: identification, battery, input, output,
                       ats-hmi, ats-misc, or all (default: all)
   --device-type, -t   Device type: auto, ups, ats, or ists (default: auto)
   --output-file, -o   Write status to file (supports .txt or .json)
   --format, -f        Output format: text or json (default: text)
"""

import sys
import argparse
import json
import asyncio
import time
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

# Import OIDs and enumerations from GetIDTable
try:
    from GetIDTable import (
        # UPS OIDs
        UPS_IDENT_OIDS, SMAP_IDENT_OIDS, BATTERY_OIDS, INPUT_OIDS, OUTPUT_OIDS, THREE_PHASE_OIDS,
        # ATS OIDs
        ATS_IDENT_OIDS, ATS_INPUT_OIDS, ATS_OUTPUT_OIDS, ATS_HMI_SWITCH_OIDS, ATS_MISC_OIDS,
        ATS_BASE_OID, ATS_OBJECT_GROUP_BASE,
        # i-STS OIDs
        ISTS_PRODUCT_OIDS, ISTS_CONTROL_OIDS, ISTS_UTILISATION_OIDS,
        ISTS_INPUT_BASE_OID, ISTS_OUTPUT_BASE_OID, ISTS_ALARMS_OID, ISTS_BASE_OID,
        # Enumerations
        BATTERY_STATUS, LINE_FAIL_CAUSE, OUTPUT_STATUS, CHARGE_STATUS, RECTIFIER_STATUS,
        IN_OUT_CONFIG, FAULT_STATUS, SOURCE_STATUS, ISTS_SUPPLY_STATUS, ISTS_ALARM_FLAGS,
        # Helper functions
        get_oid_by_name, get_all_oids_by_device_type, get_enumeration
    )
except ImportError as e:
    print(f"ERROR: Failed to import GetIDTable: {e}", file=sys.stderr)
    print("Make sure GetIDTable.py is in the same directory", file=sys.stderr)
    raise

# Try to import pysnmp
try:
    try:
        from pysnmp.hlapi import (
            SnmpEngine, CommunityData, UdpTransportTarget,
            ContextData, ObjectType, ObjectIdentity, getCmd, nextCmd
        )
        USE_ENTITY_API = False
        USE_HLAPI = True
    except ImportError:
        from pysnmp.entity import engine
        USE_ENTITY_API = True
        USE_HLAPI = False
except ImportError as e:
    print(f"ERROR: Failed to import pysnmp: {e}", file=sys.stderr)
    print("Install with: pip install pysnmp pyasn1", file=sys.stderr)
    raise

# Default SNMP settings
DEFAULT_COMMUNITY = 'public'
DEFAULT_PORT = 161


class GetUPSStatus:
    """
    Query UPS/ATS/i-STS device status via SNMP GET operations (using SNMPv2c).
    
    This class provides methods to query current device status and returns
    structured data (dictionaries) for easy integration with other programs.
    
    Example:
        >>> status = GetUPSStatus('192.168.111.173')
        >>> ident = status.get_identification()
        >>> battery = status.get_battery_status()
        >>> output = status.get_output_status()
    """
    
    def __init__(self, host: str, community: str = DEFAULT_COMMUNITY, port: int = DEFAULT_PORT):
        """
        Initialize UPS Status Query.
        
        Args:
            host: UPS/ATS/i-STS device IP address or hostname
            community: SNMP community string (default: 'public')
            port: SNMP port (default: 161)
        """
        self.host = host
        self.community = community
        self.port = port
        
        # Initialize SNMP engine
        if USE_HLAPI:
            self.snmp_engine = SnmpEngine()
        elif USE_ENTITY_API:
            self.snmp_engine = engine.SnmpEngine()
        else:
            self.snmp_engine = None
        
        # Cache for device type detection
        self._device_type = None
        self._device_type_checked = False
        
        # Timing statistics (cumulative across all method calls)
        self._snmp_timing_stats = {
            'total_queries': 0,
            'total_snmp_time': 0.0,
            'total_extraction_time': 0.0
        }
    
    def query_oid(self, oid: str, try_without_zero: bool = False) -> Optional[Any]:
        """
        Query a single OID.
        
        Args:
            oid: OID string to query
            try_without_zero: If True and query fails, try without .0 suffix
        
        Returns:
            Value from OID or None if error
        """
        # Measure SNMP request/response time
        snmp_start_time = time.time()
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
                return None
            
            # Process response (common for all APIs)
            if errorIndication:
                error_msg = str(errorIndication)
                # Record SNMP timing
                snmp_end_time = time.time()
                snmp_duration = snmp_end_time - snmp_start_time
                self._snmp_timing_stats['total_queries'] += 1
                self._snmp_timing_stats['total_snmp_time'] += snmp_duration
                # Try without .0 suffix if requested and OID ends with .0
                if try_without_zero and oid.endswith('.0'):
                    alt_oid = oid[:-2]
                    return self.query_oid(alt_oid, try_without_zero=False)
                return None
            elif errorStatus:
                error_msg = str(errorStatus)
                if hasattr(errorStatus, 'prettyPrint'):
                    error_msg = errorStatus.prettyPrint()
                # Record SNMP timing
                snmp_end_time = time.time()
                snmp_duration = snmp_end_time - snmp_start_time
                self._snmp_timing_stats['total_queries'] += 1
                self._snmp_timing_stats['total_snmp_time'] += snmp_duration
                # Try without .0 suffix if requested and OID ends with .0
                if try_without_zero and oid.endswith('.0'):
                    alt_oid = oid[:-2]
                    return self.query_oid(alt_oid, try_without_zero=False)
                return None
            else:
                for varBind in varBinds:
                    oid_str, value = varBind
                    # Record SNMP timing
                    snmp_end_time = time.time()
                    snmp_duration = snmp_end_time - snmp_start_time
                    self._snmp_timing_stats['total_queries'] += 1
                    self._snmp_timing_stats['total_snmp_time'] += snmp_duration
                    return value
        except Exception as e:
            # Record SNMP timing even on error
            snmp_end_time = time.time()
            snmp_duration = snmp_end_time - snmp_start_time
            self._snmp_timing_stats['total_queries'] += 1
            self._snmp_timing_stats['total_snmp_time'] += snmp_duration
            # Try without .0 suffix if requested and OID ends with .0
            if try_without_zero and oid.endswith('.0'):
                alt_oid = oid[:-2]
                return self.query_oid(alt_oid, try_without_zero=False)
            return None
        
        # Record SNMP timing if no API available
        snmp_end_time = time.time()
        snmp_duration = snmp_end_time - snmp_start_time
        self._snmp_timing_stats['total_queries'] += 1
        self._snmp_timing_stats['total_snmp_time'] += snmp_duration
        return None
    
    def query_multiple_oids(self, oid_dict: Dict[str, str], try_without_zero: bool = False) -> Dict[str, Any]:
        """
        Query multiple OIDs.
        
        Args:
            oid_dict: Dictionary mapping description to OID
            try_without_zero: If True, try OIDs without .0 suffix if query fails
        
        Returns:
            Dictionary mapping description to value
        """
        results = {}
        for desc, oid in oid_dict.items():
            value = self.query_oid(oid, try_without_zero=try_without_zero)
            results[desc] = value
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
                        if 'atsOutputGroupLoad' in oid_name or ('Load' in oid_name and 'ats' in oid_name.lower()):
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
        
        return str_value
    
    def detect_device_type(self) -> str:
        """
        Auto-detect device type by querying device-specific OIDs.
        
        Returns:
            Device type: 'ups', 'ats', 'ists', or 'unknown'
        """
        if self._device_type_checked:
            return self._device_type
        
        self._device_type_checked = True
        
        # Try i-STS first (43.6.1.4.1.32796)
        ists_test = self.query_oid('43.6.1.4.1.32796.1.1', try_without_zero=True)
        if ists_test is not None:
            self._device_type = 'ists'
            return 'ists'
        
        # Try ATS (1.3.6.1.4.1.37662) - check both atsAgent(2) and atsAgent(3)
        # First check sysObjectID to determine which version
        sys_oid = self.query_oid('1.3.6.1.2.1.1.2.0', try_without_zero=True)  # sysObjectID
        if sys_oid:
            sys_oid_str = str(sys_oid)
            if '1.3.6.1.4.1.37662.1.2.2' in sys_oid_str:
                # Device uses atsAgent(2)
                ats_test = self.query_oid('1.3.6.1.4.1.37662.1.2.2.1.1.1.1.0', try_without_zero=True)  # ATS Model
            else:
                # Try atsAgent(3)
                ats_test = self.query_oid('1.3.6.1.4.1.37662.1.2.3.1.1.1.1.0', try_without_zero=True)  # ATS Model
        else:
            # Fallback: try both
            ats_test = self.query_oid('1.3.6.1.4.1.37662.1.2.2.1.1.1.1.0', try_without_zero=True) or \
                      self.query_oid('1.3.6.1.4.1.37662.1.2.3.1.1.1.1.0', try_without_zero=True)
        
        if ats_test is not None:
            self._device_type = 'ats'
            return 'ats'
        
        # Default to UPS
        self._device_type = 'ups'
        return 'ups'
    
    def get_identification(self, device_type: str = None) -> Dict[str, Any]:
        """
        Get device identification information.
        
        Args:
            device_type: Device type ('ups', 'ats', 'ists') or None for auto-detect
        
        Returns:
            Dictionary with identification information, including timing data
        """
        extraction_start_time = time.time()
        # Track SNMP stats at method start
        snmp_queries_start = self._snmp_timing_stats['total_queries']
        snmp_time_start = self._snmp_timing_stats['total_snmp_time']
        
        if device_type is None:
            device_type = self.detect_device_type()
        
        results = {}
        
        if device_type == 'ats':
            # ATS identification
            ident_results = self.query_multiple_oids(ATS_IDENT_OIDS, try_without_zero=True)
            results = {
                'model': self.format_value(ident_results.get('atsIdentGroupModel'), 'Model'),
                'serial_number': self.format_value(ident_results.get('atsIdentGroupSerialNumber'), 'Serial'),
                'manufacturer': self.format_value(ident_results.get('atsIdentGroupManufacturer'), 'Manufacturer'),
                'firmware_revision': self.format_value(ident_results.get('atsIdentGroupFirmwareRevision'), 'Firmware'),
                'agent_firmware_revision': self.format_value(ident_results.get('atsIdentGroupAgentFirmwareRevision'), 'AgentFirmware'),
                'raw': ident_results
            }
        elif device_type == 'ists':
            # i-STS identification
            ident_results = self.query_multiple_oids(ISTS_PRODUCT_OIDS, try_without_zero=True)
            results = {
                'product_name': self.format_value(ident_results.get('istsProductName'), 'String'),
                'product_version': self.format_value(ident_results.get('istsProductVersion'), 'String'),
                'version_date': self.format_value(ident_results.get('istsVersionDate'), 'String'),
                'raw': ident_results
            }
        else:
            # UPS identification (try SMAP first, fall back to RFC 1628)
            smap_results = self.query_multiple_oids(SMAP_IDENT_OIDS, try_without_zero=True)
            rfc_results = self.query_multiple_oids(UPS_IDENT_OIDS, try_without_zero=True)
            
            results = {
                'model': self.format_value(smap_results.get('upsBaseIdentModel') or rfc_results.get('upsIdentModel'), 'Model'),
                'name': self.format_value(smap_results.get('upsBaseIdentUpsName') or rfc_results.get('upsIdentUPSName'), 'Name'),
                'firmware_revision': self.format_value(smap_results.get('upsSmartIdentFirmwareRevision') or rfc_results.get('upsIdentFirmwareRevision'), 'Firmware'),
                'manufacture_date': self.format_value(smap_results.get('upsSmartIdentDateOfManufacture') or rfc_results.get('upsIdentDateOfManufacture'), 'Date'),
                'serial_number': self.format_value(smap_results.get('upsSmartIdentUpsSerialNumber') or rfc_results.get('upsIdentSerialNumber'), 'Serial'),
                'agent_firmware_revision': self.format_value(smap_results.get('upsSmartIdentAgentFirmwareRevision') or rfc_results.get('upsIdentAgentFirmwareRevision'), 'AgentFirmware'),
                'raw': {**smap_results, **rfc_results}
            }
        
        # Record data extraction time
        extraction_end_time = time.time()
        extraction_duration = extraction_end_time - extraction_start_time
        self._snmp_timing_stats['total_extraction_time'] += extraction_duration
        
        # Calculate SNMP stats for this method call (difference from start)
        snmp_queries_during = self._snmp_timing_stats['total_queries'] - snmp_queries_start
        snmp_time_during = self._snmp_timing_stats['total_snmp_time'] - snmp_time_start
        
        # Add timing information to results
        results['_timing'] = {
            'extraction_time_seconds': round(extraction_duration, 4),
            'snmp_queries_count': snmp_queries_during,
            'total_snmp_time_seconds': round(snmp_time_during, 4),
            'average_snmp_time_seconds': round(
                snmp_time_during / max(snmp_queries_during, 1), 4
            ) if snmp_queries_during > 0 else 0.0
        }
        
        return results
    
    def get_battery_status(self) -> Dict[str, Any]:
        """
        Get battery status and health (UPS devices only).
        
        Returns:
            Dictionary with battery status information, including timing data
        """
        extraction_start_time = time.time()
        # Track SNMP stats at method start
        snmp_queries_start = self._snmp_timing_stats['total_queries']
        snmp_time_start = self._snmp_timing_stats['total_snmp_time']
        
        results = {}
        battery_results = self.query_multiple_oids(BATTERY_OIDS, try_without_zero=True)
        
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
        
        # Battery Capacity
        capacity = battery_results.get('upsSmartBatteryCapacity') or battery_results.get('upsEstimatedChargeRemaining')
        
        # Battery Voltage
        voltage = battery_results.get('upsSmartBatteryVoltage') or battery_results.get('upsBatteryVoltage')
        
        # Battery Temperature
        temperature = battery_results.get('upsSmartBatteryTemperature') or battery_results.get('upsBatteryTemperature')
        
        # Runtime Remaining
        runtime = battery_results.get('upsSmartBatteryRunTimeRemaining') or battery_results.get('upsEstimatedMinutesRemaining')
        if runtime is not None:
            try:
                runtime_val = int(str(runtime))
                # Check if it's in minutes (RFC) or seconds (SMAP)
                if runtime_val < 10000:  # Likely minutes
                    runtime_seconds = runtime_val * 60
                else:  # Likely seconds
                    runtime_seconds = runtime_val
            except (ValueError, TypeError):
                runtime_seconds = None
        else:
            runtime_seconds = None
        
        results = {
            'status': status_str,
            'status_code': int(str(status_val)) if status_val is not None else None,
            'capacity': self.format_value(capacity, 'Capacity'),
            'capacity_raw': capacity,
            'voltage': self.format_value(voltage, 'Voltage'),
            'voltage_raw': voltage,
            'temperature': self.format_value(temperature, 'Temperature'),
            'temperature_raw': temperature,
            'runtime_remaining_seconds': runtime_seconds,
            'raw': battery_results
        }
        
        # Record data extraction time
        extraction_end_time = time.time()
        extraction_duration = extraction_end_time - extraction_start_time
        self._snmp_timing_stats['total_extraction_time'] += extraction_duration
        
        # Calculate SNMP stats for this method call (difference from start)
        snmp_queries_during = self._snmp_timing_stats['total_queries'] - snmp_queries_start
        snmp_time_during = self._snmp_timing_stats['total_snmp_time'] - snmp_time_start
        
        # Add timing information to results
        results['_timing'] = {
            'extraction_time_seconds': round(extraction_duration, 4),
            'snmp_queries_count': snmp_queries_during,
            'total_snmp_time_seconds': round(snmp_time_during, 4),
            'average_snmp_time_seconds': round(
                snmp_time_during / max(snmp_queries_during, 1), 4
            ) if snmp_queries_during > 0 else 0.0
        }
        
        return results
    
    def get_input_status(self, device_type: str = None) -> Dict[str, Any]:
        """
        Get input power status.
        
        Args:
            device_type: Device type ('ups', 'ats', 'ists') or None for auto-detect
        
        Returns:
            Dictionary with input power status information, including timing data
        """
        extraction_start_time = time.time()
        # Track SNMP stats at method start
        snmp_queries_start = self._snmp_timing_stats['total_queries']
        snmp_time_start = self._snmp_timing_stats['total_snmp_time']
        
        if device_type is None:
            device_type = self.detect_device_type()
        
        results = {}
        
        if device_type == 'ats':
            # ATS input status (Source A and Source B)
            input_results = self.query_multiple_oids(ATS_INPUT_OIDS, try_without_zero=True)
            
            # Source A Status
            source_a_status = input_results.get('atsInputGroupSourceAstatus')
            source_a_status_str = None
            if source_a_status is not None:
                try:
                    status_int = int(str(source_a_status))
                    source_a_status_str = SOURCE_STATUS.get(status_int, f"unknown({status_int})")
                except (ValueError, TypeError):
                    source_a_status_str = str(source_a_status)
            
            # Source B Status
            source_b_status = input_results.get('atsInputGroupSourceBstatus')
            source_b_status_str = None
            if source_b_status is not None:
                try:
                    status_int = int(str(source_b_status))
                    source_b_status_str = SOURCE_STATUS.get(status_int, f"unknown({status_int})")
                except (ValueError, TypeError):
                    source_b_status_str = str(source_b_status)
            
            # Helper function to safely convert status to int
            def safe_int_convert(value):
                """Safely convert value to int, handling None and empty strings."""
                if value is None:
                    return None
                value_str = str(value).strip()
                if not value_str:  # Empty string
                    return None
                try:
                    return int(value_str)
                except (ValueError, TypeError):
                    return None
            
            results = {
                'preference': self.format_value(input_results.get('atsInputGroupPreference'), 'Preference'),
                'source_a': {
                    'status': source_a_status_str,
                    'status_code': safe_int_convert(source_a_status),
                    'voltage': self.format_value(input_results.get('atsInputGroupSourceAinputVoltage'), 'Voltage'),
                    'voltage_raw': input_results.get('atsInputGroupSourceAinputVoltage'),
                    'frequency': self.format_value(input_results.get('atsInputGroupSourceAinputFrequency'), 'Frequency'),
                    'frequency_raw': input_results.get('atsInputGroupSourceAinputFrequency'),
                    'voltage_range': {
                        'lower': self.format_value(input_results.get('atsInputGroupSourceAvoltageLowerLimit'), 'Voltage'),
                        'upper': self.format_value(input_results.get('atsInputGroupSourceAvoltageUpperLimit'), 'Voltage'),
                    },
                    'frequency_range': {
                        'lower': self.format_value(input_results.get('atsInputGroupSourceAfrequencyLowerLimit'), 'Frequency'),
                        'upper': self.format_value(input_results.get('atsInputGroupSourceAfrequencyUpperLimit'), 'Frequency'),
                    }
                },
                'source_b': {
                    'status': source_b_status_str,
                    'status_code': safe_int_convert(source_b_status),
                    'voltage': self.format_value(input_results.get('atsInputGroupSourceBinputVoltage'), 'Voltage'),
                    'voltage_raw': input_results.get('atsInputGroupSourceBinputVoltage'),
                    'frequency': self.format_value(input_results.get('atsInputGroupSourceBinputFrequency'), 'Frequency'),
                    'frequency_raw': input_results.get('atsInputGroupSourceBinputFrequency'),
                    'voltage_range': {
                        'lower': self.format_value(input_results.get('atsInputGroupSourceBvoltageLowerLimit'), 'Voltage'),
                        'upper': self.format_value(input_results.get('atsInputGroupSourceBvoltageUpperLimit'), 'Voltage'),
                    },
                    'frequency_range': {
                        'lower': self.format_value(input_results.get('atsInputGroupSourceBfrequencyLowerLimit'), 'Frequency'),
                        'upper': self.format_value(input_results.get('atsInputGroupSourceBfrequencyUpperLimit'), 'Frequency'),
                    }
                },
                'raw': input_results
            }
        else:
            # UPS input status
            input_results = self.query_multiple_oids(INPUT_OIDS, try_without_zero=True)
            
            line_voltage = input_results.get('upsSmartInputLineVoltage') or input_results.get('upsInputVoltage')
            frequency = input_results.get('upsSmartInputFrequency') or input_results.get('upsInputFrequency')
            
            # Helper function to safely convert to int
            def safe_int_convert(value):
                """Safely convert value to int, handling None and empty strings."""
                if value is None:
                    return None
                value_str = str(value).strip()
                if not value_str:  # Empty string
                    return None
                try:
                    return int(value_str)
                except (ValueError, TypeError):
                    return None
            
            # Line Fail Cause
            fail_cause = input_results.get('upsSmartInputLineFailCause')
            fail_cause_str = None
            if fail_cause is not None:
                try:
                    cause_int = int(str(fail_cause))
                    fail_cause_str = LINE_FAIL_CAUSE.get(cause_int, f"unknown({cause_int})")
                except (ValueError, TypeError):
                    fail_cause_str = str(fail_cause)
            
            results = {
                'line_voltage': self.format_value(line_voltage, 'Voltage'),
                'line_voltage_raw': line_voltage,
                'max_line_voltage': self.format_value(input_results.get('upsSmartInputMaxLineVoltage'), 'Voltage'),
                'min_line_voltage': self.format_value(input_results.get('upsSmartInputMinLineVoltage'), 'Voltage'),
                'frequency': self.format_value(frequency, 'Frequency'),
                'frequency_raw': frequency,
                'line_fail_cause': fail_cause_str,
                'line_fail_cause_code': safe_int_convert(fail_cause),
                'raw': input_results
            }
        
        # Record data extraction time
        extraction_end_time = time.time()
        extraction_duration = extraction_end_time - extraction_start_time
        self._snmp_timing_stats['total_extraction_time'] += extraction_duration
        
        # Calculate SNMP stats for this method call (difference from start)
        snmp_queries_during = self._snmp_timing_stats['total_queries'] - snmp_queries_start
        snmp_time_during = self._snmp_timing_stats['total_snmp_time'] - snmp_time_start
        
        # Add timing information to results
        results['_timing'] = {
            'extraction_time_seconds': round(extraction_duration, 4),
            'snmp_queries_count': snmp_queries_during,
            'total_snmp_time_seconds': round(snmp_time_during, 4),
            'average_snmp_time_seconds': round(
                snmp_time_during / max(snmp_queries_during, 1), 4
            ) if snmp_queries_during > 0 else 0.0
        }
        
        return results
    
    def get_output_status(self, device_type: str = None) -> Dict[str, Any]:
        """
        Get output power status.
        
        Args:
            device_type: Device type ('ups', 'ats', 'ists') or None for auto-detect
        
        Returns:
            Dictionary with output power status information, including timing data
        """
        extraction_start_time = time.time()
        # Track SNMP stats at method start
        snmp_queries_start = self._snmp_timing_stats['total_queries']
        snmp_time_start = self._snmp_timing_stats['total_snmp_time']
        
        if device_type is None:
            device_type = self.detect_device_type()
        
        results = {}
        
        if device_type == 'ats':
            # ATS output status
            output_results = self.query_multiple_oids(ATS_OUTPUT_OIDS, try_without_zero=True)
            
            results = {
                'source': self.format_value(output_results.get('atsOutputGroupOutputSource'), 'Source'),
                'source_raw': output_results.get('atsOutputGroupOutputSource'),
                'voltage': self.format_value(output_results.get('atsOutputGroupOutputVoltage'), 'Voltage'),
                'voltage_raw': output_results.get('atsOutputGroupOutputVoltage'),
                'frequency': self.format_value(output_results.get('atsOutputGroupOutputFequency'), 'Frequency'),
                'frequency_raw': output_results.get('atsOutputGroupOutputFequency'),
                'current': self.format_value(output_results.get('atsOutputGroupOutputCurrent'), 'Current'),
                'current_raw': output_results.get('atsOutputGroupOutputCurrent'),
                'load': self.format_value(output_results.get('atsOutputGroupLoad'), 'Load'),
                'load_raw': output_results.get('atsOutputGroupLoad'),
                'raw': output_results
            }
        else:
            # UPS output status
            output_results = self.query_multiple_oids(OUTPUT_OIDS, try_without_zero=True)
            
            # Output Status
            status_val = output_results.get('upsBaseOutputStatus') or output_results.get('upsOutputSource')
            status_str = None
            if status_val is not None:
                try:
                    status_int = int(str(status_val))
                    status_str = OUTPUT_STATUS.get(status_int, f"unknown({status_int})")
                except (ValueError, TypeError):
                    status_str = str(status_val)
            
            voltage = output_results.get('upsSmartOutputVoltage') or output_results.get('upsOutputVoltage')
            frequency = output_results.get('upsSmartOutputFrequency') or output_results.get('upsOutputFrequency')
            load = output_results.get('upsSmartOutputLoad') or output_results.get('upsOutputLoad')
            
            results = {
                'status': status_str,
                'status_code': int(str(status_val)) if status_val is not None else None,
                'voltage': self.format_value(voltage, 'Voltage'),
                'voltage_raw': voltage,
                'frequency': self.format_value(frequency, 'Frequency'),
                'frequency_raw': frequency,
                'load': self.format_value(load, 'Load'),
                'load_raw': load,
                'raw': output_results
            }
        
        # Record data extraction time
        extraction_end_time = time.time()
        extraction_duration = extraction_end_time - extraction_start_time
        self._snmp_timing_stats['total_extraction_time'] += extraction_duration
        
        # Calculate SNMP stats for this method call (difference from start)
        snmp_queries_during = self._snmp_timing_stats['total_queries'] - snmp_queries_start
        snmp_time_during = self._snmp_timing_stats['total_snmp_time'] - snmp_time_start
        
        # Add timing information to results
        results['_timing'] = {
            'extraction_time_seconds': round(extraction_duration, 4),
            'snmp_queries_count': snmp_queries_during,
            'total_snmp_time_seconds': round(snmp_time_during, 4),
            'average_snmp_time_seconds': round(
                snmp_time_during / max(snmp_queries_during, 1), 4
            ) if snmp_queries_during > 0 else 0.0
        }
        
        return results
    
    def get_ats_hmi_settings(self) -> Dict[str, Any]:
        """
        Get ATS HMI and switch settings.
        
        Returns:
            Dictionary with HMI and switch settings
        """
        results = {}
        hmi_results = self.query_multiple_oids(ATS_HMI_SWITCH_OIDS, try_without_zero=True)
        
        # Buzzer
        buzzer = hmi_results.get('atsHmiSwitchGroupBuzzer')
        buzzer_str = None
        if buzzer is not None:
            try:
                buzzer_int = int(str(buzzer))
                buzzer_str = "Enabled" if buzzer_int == 2 else "Disabled"
            except (ValueError, TypeError):
                buzzer_str = str(buzzer)
        
        # Alarm
        alarm = hmi_results.get('atsHmiSwitchGroupAtsAlarm')
        alarm_str = None
        if alarm is not None:
            try:
                alarm_int = int(str(alarm))
                alarm_str = "Alarm Occurred" if alarm_int == 2 else "No Alarm"
            except (ValueError, TypeError):
                alarm_str = str(alarm)
        
        results = {
            'buzzer': buzzer_str,
            'buzzer_code': int(str(buzzer)) if buzzer is not None else None,
            'alarm': alarm_str,
            'alarm_code': int(str(alarm)) if alarm is not None else None,
            'auto_return': "On" if (hmi_results.get('atsHmiSwitchGroupAutoReturn') and int(str(hmi_results.get('atsHmiSwitchGroupAutoReturn'))) == 2) else "Off",
            'transfer_by_load': "On" if (hmi_results.get('atsHmiSwitchGroupSourceTransferByLoad') and int(str(hmi_results.get('atsHmiSwitchGroupSourceTransferByLoad'))) == 2) else "Off",
            'transfer_by_phase': "On" if (hmi_results.get('atsHmiSwitchGroupSourceTransferByPhase') and int(str(hmi_results.get('atsHmiSwitchGroupSourceTransferByPhase'))) == 2) else "Off",
            'raw': hmi_results
        }
        
        return results
    
    def get_ats_miscellaneous(self) -> Dict[str, Any]:
        """
        Get ATS miscellaneous information.
        
        Returns:
            Dictionary with miscellaneous information
        """
        results = {}
        misc_results = self.query_multiple_oids(ATS_MISC_OIDS, try_without_zero=True)
        
        results = {
            'system_temperature': self.format_value(misc_results.get('atsMiscellaneousGroupAtsSystemTemperture'), 'Temperature'),
            'system_temperature_raw': misc_results.get('atsMiscellaneousGroupAtsSystemTemperture'),
            'system_max_current': self.format_value(misc_results.get('atsMiscellaneousGroupSystemMaxCurrent'), 'Current'),
            'system_max_current_raw': misc_results.get('atsMiscellaneousGroupSystemMaxCurrent'),
            'raw': misc_results
        }
        
        return results
    
    def get_all_status(self, device_type: str = None) -> Dict[str, Any]:
        """
        Get all available status information for the device.
        
        Args:
            device_type: Device type ('ups', 'ats', 'ists') or None for auto-detect
        
        Returns:
            Dictionary with all status information organized by category
        """
        if device_type is None:
            device_type = self.detect_device_type()
        
        all_status = {
            'device_type': device_type,
            'host': self.host,
            'timestamp': datetime.now().isoformat(),
            'identification': self.get_identification(device_type),
        }
        
        if device_type == 'ats':
            all_status['input'] = self.get_input_status(device_type)
            all_status['output'] = self.get_output_status(device_type)
            all_status['hmi_settings'] = self.get_ats_hmi_settings()
            all_status['miscellaneous'] = self.get_ats_miscellaneous()
        elif device_type == 'ists':
            # i-STS status (simplified - can be expanded)
            control_results = self.query_multiple_oids(ISTS_CONTROL_OIDS, try_without_zero=True)
            all_status['control'] = {
                'active_supply': ISTS_SUPPLY_STATUS.get(int(str(control_results.get('istsActiveSupply')))) if control_results.get('istsActiveSupply') else None,
                'preferred_supply': ISTS_SUPPLY_STATUS.get(int(str(control_results.get('istsPreferredSupply')))) if control_results.get('istsPreferredSupply') else None,
                'supply1_frequency': self.format_value(control_results.get('istsFreq1'), 'Frequency'),
                'supply2_frequency': self.format_value(control_results.get('istsFreq2'), 'Frequency'),
                'raw': control_results
            }
        else:
            all_status['battery'] = self.get_battery_status()
            all_status['input'] = self.get_input_status(device_type)
            all_status['output'] = self.get_output_status(device_type)
        
        return all_status
    
    def test_connectivity(self) -> bool:
        """
        Test SNMP connectivity to the device.
        
        Returns:
            True if device is reachable, False otherwise
        """
        test_oid = '1.3.6.1.2.1.1.1.0'  # sysDescr - should be available on all SNMP devices
        result = self.query_oid(test_oid, try_without_zero=True)
        return result is not None
    
    def export_to_ups_state_file(self, device_type: str = None, output_file: str = None) -> bool:
        """
        Export UPS status to UPSState.txt file.
        
        Args:
            device_type: Device type ('ups', 'ats', 'ists') or None for auto-detect
            output_file: Path to output file (default: UPSState.txt in script directory)
        
        Returns:
            True if file was written successfully, False otherwise
        """
        if output_file is None:
            # Default to UPSState.txt in the same directory as this script
            script_dir = Path(__file__).parent
            output_file = script_dir / 'UPSState.txt'
        else:
            output_file = Path(output_file)
        
        try:
            # Get all status
            if device_type is None:
                device_type = self.detect_device_type()
            
            all_status = self.get_all_status(device_type)
            
            # Format status for display
            formatted_text = format_status_for_display(all_status, device_type)
            
            # Write to file
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(formatted_text)
                f.flush()
                import os
                os.fsync(f.fileno())  # Force write to disk
            
            return True
        except Exception as e:
            print(f"[ERROR] Failed to export UPS status to {output_file}: {e}", file=sys.stderr)
            return False


def format_status_for_display(status: Dict[str, Any], device_type: str = None) -> str:
    """
    Format status dictionary for human-readable display.
    
    Args:
        status: Status dictionary from GetUPSStatus methods
        device_type: Device type ('ups', 'ats', 'ists')
    
    Returns:
        Formatted string for display
    """
    lines = []
    
    if device_type is None:
        device_type = status.get('device_type', 'unknown')
    
    # Header
    lines.append("=" * 80)
    lines.append(f"UPS/ATS/i-STS STATUS QUERY")
    lines.append("=" * 80)
    lines.append(f"Host: {status.get('host', 'N/A')}")
    lines.append(f"Device Type: {device_type.upper()}")
    lines.append(f"Timestamp: {status.get('timestamp', datetime.now().isoformat())}")
    lines.append("=" * 80)
    lines.append("")
    
    # Identification
    if 'identification' in status:
        ident = status['identification']
        lines.append("1. IDENTIFICATION INFORMATION")
        lines.append("-" * 80)
        for key, value in ident.items():
            if key != 'raw':
                lines.append(f"  {key.replace('_', ' ').title()}: {value}")
        lines.append("")
    
    # Battery Status (UPS only)
    if 'battery' in status:
        battery = status['battery']
        lines.append("2. BATTERY STATUS AND HEALTH")
        lines.append("-" * 80)
        lines.append(f"  Status: {battery.get('status', 'N/A')}")
        lines.append(f"  Capacity: {battery.get('capacity', 'N/A')}")
        lines.append(f"  Voltage: {battery.get('voltage', 'N/A')}")
        lines.append(f"  Temperature: {battery.get('temperature', 'N/A')}")
        if battery.get('runtime_remaining_seconds'):
            runtime = battery['runtime_remaining_seconds']
            hours = runtime // 3600
            minutes = (runtime % 3600) // 60
            seconds = runtime % 60
            if hours > 0:
                lines.append(f"  Runtime Remaining: {hours}h {minutes}m {seconds}s")
            elif minutes > 0:
                lines.append(f"  Runtime Remaining: {minutes}m {seconds}s")
            else:
                lines.append(f"  Runtime Remaining: {seconds}s")
        lines.append("")
    
    # Input Status
    if 'input' in status:
        input_status = status['input']
        lines.append("3. INPUT POWER STATUS")
        lines.append("-" * 80)
        
        if device_type == 'ats':
            lines.append(f"  Output Source Priority: {input_status.get('preference', 'N/A')}")
            lines.append("")
            lines.append("  Source A:")
            source_a = input_status.get('source_a', {})
            lines.append(f"    Status: {source_a.get('status', 'N/A')}")
            lines.append(f"    Voltage: {source_a.get('voltage', 'N/A')}")
            lines.append(f"    Frequency: {source_a.get('frequency', 'N/A')}")
            lines.append(f"    Voltage Range: {source_a.get('voltage_range', {}).get('lower', 'N/A')} - {source_a.get('voltage_range', {}).get('upper', 'N/A')}")
            lines.append(f"    Frequency Range: {source_a.get('frequency_range', {}).get('lower', 'N/A')} - {source_a.get('frequency_range', {}).get('upper', 'N/A')}")
            lines.append("")
            lines.append("  Source B:")
            source_b = input_status.get('source_b', {})
            lines.append(f"    Status: {source_b.get('status', 'N/A')}")
            lines.append(f"    Voltage: {source_b.get('voltage', 'N/A')}")
            lines.append(f"    Frequency: {source_b.get('frequency', 'N/A')}")
            lines.append(f"    Voltage Range: {source_b.get('voltage_range', {}).get('lower', 'N/A')} - {source_b.get('voltage_range', {}).get('upper', 'N/A')}")
            lines.append(f"    Frequency Range: {source_b.get('frequency_range', {}).get('lower', 'N/A')} - {source_b.get('frequency_range', {}).get('upper', 'N/A')}")
        else:
            lines.append(f"  Line Voltage: {input_status.get('line_voltage', 'N/A')}")
            lines.append(f"  Max Line Voltage: {input_status.get('max_line_voltage', 'N/A')}")
            lines.append(f"  Min Line Voltage: {input_status.get('min_line_voltage', 'N/A')}")
            lines.append(f"  Frequency: {input_status.get('frequency', 'N/A')}")
            lines.append(f"  Line Fail Cause: {input_status.get('line_fail_cause', 'N/A')}")
        lines.append("")
    
    # Output Status
    if 'output' in status:
        output_status = status['output']
        lines.append("4. OUTPUT POWER STATUS")
        lines.append("-" * 80)
        if device_type == 'ats':
            lines.append(f"  Output Source: {output_status.get('source', 'N/A')}")
            lines.append(f"  Output Voltage: {output_status.get('voltage', 'N/A')}")
            lines.append(f"  Output Frequency: {output_status.get('frequency', 'N/A')}")
            lines.append(f"  Output Current: {output_status.get('current', 'N/A')}")
            lines.append(f"  Output Load: {output_status.get('load', 'N/A')}")
        else:
            lines.append(f"  Status: {output_status.get('status', 'N/A')}")
            lines.append(f"  Voltage: {output_status.get('voltage', 'N/A')}")
            lines.append(f"  Frequency: {output_status.get('frequency', 'N/A')}")
            lines.append(f"  Load: {output_status.get('load', 'N/A')}")
        lines.append("")
    
    # ATS HMI Settings
    if 'hmi_settings' in status:
        hmi = status['hmi_settings']
        lines.append("5. ATS HMI AND SWITCH SETTINGS")
        lines.append("-" * 80)
        lines.append(f"  Buzzer Status: {hmi.get('buzzer', 'N/A')}")
        lines.append(f"  ATS Alarm Status: {hmi.get('alarm', 'N/A')}")
        lines.append(f"  Auto Return: {hmi.get('auto_return', 'N/A')}")
        lines.append(f"  Transfer by Load: {hmi.get('transfer_by_load', 'N/A')}")
        lines.append(f"  Transfer by Phase: {hmi.get('transfer_by_phase', 'N/A')}")
        lines.append("")
    
    # ATS Miscellaneous
    if 'miscellaneous' in status:
        misc = status['miscellaneous']
        lines.append("6. ATS MISCELLANEOUS INFORMATION")
        lines.append("-" * 80)
        lines.append(f"  System Temperature: {misc.get('system_temperature', 'N/A')}")
        lines.append(f"  System Max Current: {misc.get('system_max_current', 'N/A')}")
        lines.append("")
    
    # i-STS Control
    if 'control' in status:
        control = status['control']
        lines.append("2. i-STS CONTROL/OPERATION STATUS")
        lines.append("-" * 80)
        lines.append(f"  Active Supply: {control.get('active_supply', 'N/A')}")
        lines.append(f"  Preferred Supply: {control.get('preferred_supply', 'N/A')}")
        lines.append(f"  Supply 1 Frequency: {control.get('supply1_frequency', 'N/A')}")
        lines.append(f"  Supply 2 Frequency: {control.get('supply2_frequency', 'N/A')}")
        lines.append("")
    
    lines.append("=" * 80)
    lines.append("QUERY COMPLETE")
    lines.append("=" * 80)
    
    return "\n".join(lines)


def write_status_to_file(status: Dict[str, Any], output_file: str, format_type: str = 'text'):
    """
    Write status to a file.
    
    Args:
        status: Status dictionary from GetUPSStatus methods
        output_file: Path to output file
        format_type: Output format ('text' or 'json')
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        if format_type.lower() == 'json':
            # Write as JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(status, f, indent=2, ensure_ascii=False, default=str)
            print(f"\n[INFO] Status written to JSON file: {output_path.absolute()}")
        else:
            # Write as formatted text
            device_type = status.get('device_type', 'unknown')
            formatted_text = format_status_for_display(status, device_type)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(formatted_text)
            print(f"\n[INFO] Status written to file: {output_path.absolute()}")
    except Exception as e:
        print(f"\n[ERROR] Failed to write status to file: {e}", file=sys.stderr)
        raise


def main():
    """Main entry point for standalone execution."""
    # Try to load default IP from config.py
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
    
    parser = argparse.ArgumentParser(
        description='Query UPS/ATS/i-STS device status via SNMP (using SNMPv2c)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query default device (Borri STS32A at 192.168.111.173)
  %(prog)s
  
  # Query specific device
  %(prog)s --host 192.168.111.173
  
  # Query specific section
  %(prog)s --host 192.168.111.173 --section identification
  %(prog)s --host 192.168.111.173 --section battery
  %(prog)s --host 192.168.111.173 --section input
  %(prog)s --host 192.168.111.173 --section output
  
  # Query ATS-specific sections
  %(prog)s --host 192.168.111.173 --section ats-input
  %(prog)s --host 192.168.111.173 --section ats-output
  %(prog)s --host 192.168.111.173 --section ats-hmi
  
  # Output status to file (text format)
  %(prog)s --host 192.168.111.173 --output-file status.txt
  
  # Output status to file (JSON format)
  %(prog)s --host 192.168.111.173 --output-file status.json --format json
  
  # Use custom community string
  %(prog)s --host 192.168.111.173 --community private
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
        choices=['identification', 'battery', 'input', 'output', 'ats-hmi', 'ats-misc', 'all'],
        default='all',
        help='Query specific section only (default: all)'
    )
    
    parser.add_argument(
        '--device-type', '-t',
        type=str,
        choices=['auto', 'ups', 'ats', 'ists'],
        default='auto',
        help='Device type: auto (detect), ups, ats, or ists (default: auto)'
    )
    
    parser.add_argument(
        '--output-file', '-o',
        type=str,
        default=None,
        help='Write status to file (supports .txt for text format, .json for JSON format)'
    )
    
    parser.add_argument(
        '--format', '-f',
        type=str,
        choices=['text', 'json'],
        default='text',
        help='Output format when writing to file: text (formatted) or json (raw data) (default: text)'
    )
    
    args = parser.parse_args()
    
    # Create status query object
    print(f"Connecting to device at {args.host}...", flush=True)
    status_query = GetUPSStatus(args.host, args.community, args.port)
    
    # Test connectivity
    if not status_query.test_connectivity():
        print(f"\n[ERROR] Cannot connect to device at {args.host}:{args.port}", file=sys.stderr)
        print(f"[ERROR] Check:", file=sys.stderr)
        print(f"  - Device is powered on and network connected", file=sys.stderr)
        print(f"  - SNMP is enabled on device", file=sys.stderr)
        print(f"  - Community string is correct (current: '{args.community}')", file=sys.stderr)
        print(f"  - Firewall allows SNMP (port {args.port})", file=sys.stderr)
        print(f"  - IP address is correct: {args.host}", file=sys.stderr)
        sys.exit(1)
    
    print("Connection successful!", flush=True)
    
    # Auto-detect device type if needed
    device_type = args.device_type
    if device_type == 'auto':
        print("Auto-detecting device type...", end=" ", flush=True)
        device_type = status_query.detect_device_type()
        print(f"{device_type.upper()} detected")
    
    # Query based on section
    status_data = {}
    
    try:
        if args.section == 'all':
            print("\nQuerying all status information...", flush=True)
            status_data = status_query.get_all_status(device_type)
        elif args.section == 'identification':
            print("\nQuerying identification information...", flush=True)
            status_data = {
                'device_type': device_type,
                'host': args.host,
                'timestamp': datetime.now().isoformat(),
                'identification': status_query.get_identification(device_type)
            }
        elif args.section == 'battery':
            print("\nQuerying battery status...", flush=True)
            status_data = {
                'device_type': device_type,
                'host': args.host,
                'timestamp': datetime.now().isoformat(),
                'battery': status_query.get_battery_status()
            }
        elif args.section == 'input':
            print("\nQuerying input power status...", flush=True)
            status_data = {
                'device_type': device_type,
                'host': args.host,
                'timestamp': datetime.now().isoformat(),
                'input': status_query.get_input_status(device_type)
            }
        elif args.section == 'output':
            print("\nQuerying output power status...", flush=True)
            status_data = {
                'device_type': device_type,
                'host': args.host,
                'timestamp': datetime.now().isoformat(),
                'output': status_query.get_output_status(device_type)
            }
        elif args.section == 'ats-hmi':
            print("\nQuerying ATS HMI settings...", flush=True)
            status_data = {
                'device_type': device_type,
                'host': args.host,
                'timestamp': datetime.now().isoformat(),
                'hmi_settings': status_query.get_ats_hmi_settings()
            }
        elif args.section == 'ats-misc':
            print("\nQuerying ATS miscellaneous information...", flush=True)
            status_data = {
                'device_type': device_type,
                'host': args.host,
                'timestamp': datetime.now().isoformat(),
                'miscellaneous': status_query.get_ats_miscellaneous()
            }
        
        # Display status
        formatted_output = format_status_for_display(status_data, device_type)
        print("\n" + formatted_output)
        
        # Write to file if requested
        if args.output_file:
            # Auto-detect format from file extension if not specified
            output_format = args.format
            if output_format == 'text' and args.output_file.lower().endswith('.json'):
                output_format = 'json'
            elif output_format == 'json' and not args.output_file.lower().endswith('.json'):
                # If JSON format but .txt extension, keep JSON format
                pass
            
            write_status_to_file(status_data, args.output_file, output_format)
        else:
            # If no output file specified, automatically write to UPSState.txt
            # This ensures the file is always created when running standalone
            script_dir = Path(__file__).parent
            ups_state_file = script_dir / 'UPSState.txt'
            if status_query.export_to_ups_state_file(device_type, str(ups_state_file)):
                print(f"\n[INFO] UPS status written to: {ups_state_file.absolute()}")
        
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Query cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Query failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

