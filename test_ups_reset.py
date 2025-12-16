#!/usr/bin/env python3
"""
Test UPS Reset/Restart Program

This program tests the UPS reset and restart functionality via SNMP SET commands.
Uses SNMPv2c protocol to send commands to the Borri STS32A UPS.

Requires: Python 3.6+, pysnmp>=4.4.12, pyasn1>=0.4.8

This script uses the same pysnmp library as ups_snmp_trap_receiver_v3.py.
If ups_snmp_trap_receiver_v3.py works, this script should also work.
"""

import sys
import argparse
import time
import subprocess
import os

# Print Python version and path for debugging
print(f"[DEBUG] Python version: {sys.version}", file=sys.stderr)
print(f"[DEBUG] Python executable: {sys.executable}", file=sys.stderr)
print(f"[DEBUG] Python path: {sys.path[:3]}...", file=sys.stderr)

# Try to import config.py for default values
try:
    import config
    DEFAULT_UPS_IP = getattr(config, 'UPS_IP', '192.168.111.173')
    DEFAULT_COMMUNITY = getattr(config, 'SNMP_COMMUNITY', 'public')
    DEFAULT_PORT = getattr(config, 'SNMP_PORT', 161)
except (ImportError, AttributeError):
    DEFAULT_UPS_IP = '192.168.111.173'
    DEFAULT_COMMUNITY = 'public'
    DEFAULT_PORT = 161

# Try to import pysnmp - gracefully handle import failures
USE_ENTITY_API = False
cmdgen = None
rfc1902 = None

# Try to import pysnmp.entity (same as ups_snmp_trap_receiver_v3.py)
try:
    from pysnmp.entity import engine, config as snmp_config
    from pysnmp.proto import rfc1902
    # Try to import cmdgen separately - may not be available in pysnmp 7.1.22
    try:
        from pysnmp.entity.rfc3413.oneliner import cmdgen
        USE_ENTITY_API = True
        print("[INFO] Using pysnmp entity API with cmdgen", file=sys.stderr)
    except ImportError:
        print("[INFO] pysnmp.entity available but cmdgen not found (pysnmp version issue)", file=sys.stderr)
        print("[INFO] Will use snmpset command instead", file=sys.stderr)
        USE_ENTITY_API = False
except ImportError as e:
    print("[INFO] pysnmp.entity not available, will use snmpset command", file=sys.stderr)
    print(f"[DEBUG] Import error: {e}", file=sys.stderr)
    USE_ENTITY_API = False

# Note: We don't try hlapi because it causes import errors in pysnmp 7.1.22
# The script will use subprocess (snmpset command) as fallback, which is more reliable

# OIDs from ATS_Stork_V1_05 - Borri STS32A.MIB
# Note: Device firmware uses atsAgent(2) instead of atsAgent(3) as defined in MIB
# Based on testing: GET works with atsAgent(2), so we default to V2
RESET_OID_V3 = '1.3.6.1.4.1.37662.1.2.3.1.1.7.12'  # agentConfigResetToDefault (atsAgent=3, MIB-defined)
RESET_OID_V2 = '1.3.6.1.4.1.37662.1.2.2.1.1.7.12'  # agentConfigResetToDefault (atsAgent=2, device firmware)
RESTART_OID_V3 = '1.3.6.1.4.1.37662.1.2.3.1.1.7.13'  # agentConfigRestart (atsAgent=3, MIB-defined)
RESTART_OID_V2 = '1.3.6.1.4.1.37662.1.2.2.1.1.7.13'  # agentConfigRestart (atsAgent=2, device firmware)

# Default to V2 (device firmware version) since GET operations confirm this works
# Will try V3 as fallback if V2 fails
RESET_OID = RESET_OID_V2
RESTART_OID = RESTART_OID_V2

# Action values: 1 = execute, 2 = nothing
ACTION_EXECUTE = 1
ACTION_NOTHING = 2


def print_header(text):
    """Print a formatted header."""
    print(f"\n{'=' * 70}")
    print(f"{text:^70}")
    print(f"{'=' * 70}\n")


def print_info(text):
    """Print info message."""
    print(f"[INFO] {text}")


def print_success(text):
    """Print success message."""
    print(f"[SUCCESS] {text}")


def print_error(text):
    """Print error message."""
    print(f"[ERROR] {text}")


def print_warning(text):
    """Print warning message."""
    print(f"[WARNING] {text}")


def send_snmp_set(host, oid, value, community='public', port=161, try_alternative_oid=True):
    """
    Send SNMP SET command to UPS.
    Uses pysnmp entity API if available, otherwise uses snmpset command.
    
    Args:
        host: UPS IP address
        oid: OID to set (primary OID, will try alternative if this fails)
        value: Value to set (INTEGER)
        community: SNMP community string
        port: SNMP port
        try_alternative_oid: If True, try atsAgent(2) version if atsAgent(3) fails
    
    Returns:
        True if successful, False otherwise
    """
    # Try primary OID first
    result = _send_snmp_set_single(host, oid, value, community, port)
    
    # If failed and we should try alternative, try atsAgent(2) version
    if not result and try_alternative_oid:
        # Convert atsAgent(3) to atsAgent(2) if needed
        if '.1.2.3.' in oid:
            alt_oid = oid.replace('.1.2.3.', '.1.2.2.')
            print_info(f"Trying alternative OID (atsAgent=2): {alt_oid}")
            result = _send_snmp_set_single(host, alt_oid, value, community, port, try_alternative_oid=False)
    
    return result


def _send_snmp_set_single(host, oid, value, community='public', port=161, try_alternative_oid=False):
    """
    Internal function to send SNMP SET command with a single OID.
    """
    try:
        if USE_ENTITY_API and cmdgen is not None:
            # Use entity API (same as ups_snmp_trap_receiver_v3.py)
            try:
                print_info("Using pysnmp entity API (same as ups_snmp_trap_receiver_v3.py)")
                cmdGen = cmdgen.CommandGenerator()
                errorIndication, errorStatus, errorIndex, varBinds = cmdGen.setCmd(
                    cmdgen.CommunityData(community, mpModel=1),  # SNMPv2c
                    cmdgen.UdpTransportTarget((host, port)),
                    (oid, rfc1902.Integer(value))  # Use rfc1902.Integer for value
                )
                
                if errorIndication:
                    print_error(f"SNMP error: {errorIndication}")
                    return False
                elif errorStatus:
                    error_msg = str(errorStatus)
                    if hasattr(errorStatus, 'prettyPrint'):
                        error_msg = errorStatus.prettyPrint()
                    print_error(f"SNMP error status: {error_msg}")
                    if errorIndex:
                        print_error(f"Error at index: {errorIndex}")
                    return False
                else:
                    # Success
                    for varBind in varBinds:
                        oid_str, val = varBind
                        print_info(f"Set {oid_str} = {val}")
                    return True
            except Exception as e1:
                print_error(f"Failed to use entity API: {e1}")
                import traceback
                traceback.print_exc()
                # Try subprocess fallback
                print_info("Falling back to snmpset command...")
                return send_snmp_set_via_subprocess(host, oid, value, community, port)
        else:
            # Use subprocess to call snmpset command (more reliable)
            print_info("Using snmpset command (pysnmp API not available)...")
            return send_snmp_set_via_subprocess(host, oid, value, community, port)
            
    except Exception as e:
        print_error(f"Exception sending SNMP SET: {e}")
        import traceback
        traceback.print_exc()
        # Try subprocess fallback
        print_info("Attempting fallback method using snmpset command...")
        return send_snmp_set_via_subprocess(host, oid, value, community, port)


def send_snmp_set_via_subprocess(host, oid, value, community='public', port=161):
    """
    Send SNMP SET command using subprocess (snmpset command).
    This is a fallback method when pysnmp API is not available.
    
    Args:
        host: UPS IP address
        oid: OID to set
        value: Value to set (INTEGER)
        community: SNMP community string
        port: SNMP port
    
    Returns:
        True if successful, False otherwise
    """
    try:
        import subprocess
        # Use snmpset command (part of net-snmp package)
        cmd = [
            'snmpset',
            '-v', '2c',  # SNMPv2c
            '-c', community,
            '-t', '5',  # Timeout: 5 seconds (reduce from default)
            '-r', '2',  # Retries: 2 (reduce from default)
            f'{host}:{port}',
            oid,
            'i',  # INTEGER type
            str(value)
        ]
        
        print_info(f"Using snmpset command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15  # Increased timeout to allow for retries
        )
        
        if result.returncode == 0:
            print_info(f"snmpset output: {result.stdout.strip()}")
            return True
        else:
            print_error(f"snmpset failed with return code {result.returncode}")
            if result.stderr:
                print_error(f"Error: {result.stderr.strip()}")
            return False
            
    except FileNotFoundError:
        print_error("snmpset command not found. Please install net-snmp:")
        print_error("  Ubuntu/Debian: sudo apt-get install snmp")
        print_error("  Or install pysnmp: pip install pysnmp")
        return False
    except subprocess.TimeoutExpired:
        print_error("snmpset command timed out")
        return False
    except Exception as e:
        print_error(f"Exception using snmpset: {e}")
        return False


def reset_ups(host, community='public', port=161, interactive=False):
    """
    Reset UPS to default values.
    
    Args:
        host: UPS IP address
        community: SNMP community string
        port: SNMP port
        interactive: If True, prompt for confirmation
    
    Returns:
        True if successful, False otherwise
    """
    if interactive:
        print_warning(f"This will RESET all parameters of UPS at {host} to default values!")
        response = input("Are you sure you want to continue? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print_info("Reset cancelled by user.")
            return False
    
    print_info(f"Sending reset command to UPS at {host}...")
    print_info(f"OID: {RESET_OID}")
    print_info(f"Value: {ACTION_EXECUTE} (reset)")
    
    success = send_snmp_set(host, RESET_OID, ACTION_EXECUTE, community, port)
    
    if success:
        print_success(f"Reset command sent successfully to {host}")
        print_info("The UPS should reset all parameters to default values.")
        return True
    else:
        print_error(f"Failed to send reset command to {host}")
        return False


def restart_ups(host, community='public', port=161, interactive=False):
    """
    Restart UPS.
    
    Args:
        host: UPS IP address
        community: SNMP community string
        port: SNMP port
        interactive: If True, prompt for confirmation
    
    Returns:
        True if successful, False otherwise
    """
    if interactive:
        print_warning(f"This will RESTART the UPS at {host}!")
        response = input("Are you sure you want to continue? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print_info("Restart cancelled by user.")
            return False
    
    print_info(f"Sending restart command to UPS at {host}...")
    print_info(f"OID: {RESTART_OID}")
    print_info(f"Value: {ACTION_EXECUTE} (restart)")
    
    success = send_snmp_set(host, RESTART_OID, ACTION_EXECUTE, community, port)
    
    if success:
        print_success(f"Restart command sent successfully to {host}")
        print_info("The UPS should restart shortly.")
        return True
    else:
        print_error(f"Failed to send restart command to {host}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Test UPS reset/restart functionality via SNMP',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Reset UPS to defaults (uses config.py defaults)
  python3 test_ups_reset.py --reset
  
  # Restart UPS
  python3 test_ups_reset.py --restart
  
  # Reset specific UPS device
  python3 test_ups_reset.py --reset --host 192.168.111.173
  
  # Restart with custom community
  python3 test_ups_reset.py --restart --community private
  
  # Interactive mode (prompts for confirmation)
  python3 test_ups_reset.py --reset --interactive
        """
    )
    
    parser.add_argument(
        '--host', '-H',
        type=str,
        default=DEFAULT_UPS_IP,
        help=f'UPS IP address or hostname (default: {DEFAULT_UPS_IP})'
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
        '--reset',
        action='store_true',
        help='Reset UPS to default values'
    )
    
    parser.add_argument(
        '--restart',
        action='store_true',
        help='Restart UPS'
    )
    
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Interactive mode (prompts for confirmation)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.reset and not args.restart:
        parser.error("Must specify either --reset or --restart")
    
    if args.reset and args.restart:
        parser.error("Cannot specify both --reset and --restart at the same time")
    
    # Print header
    if args.reset:
        print_header(f"UPS Reset Test - {args.host}")
    else:
        print_header(f"UPS Restart Test - {args.host}")
    
    print_info(f"Target UPS: {args.host}")
    print_info(f"SNMP Community: {args.community}")
    print_info(f"SNMP Port: {args.port}")
    print()
    
    # Execute command
    if args.reset:
        success = reset_ups(args.host, args.community, args.port, args.interactive)
    else:
        success = restart_ups(args.host, args.community, args.port, args.interactive)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
