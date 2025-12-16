#!/usr/bin/env python3
"""
UPS SNMP Trap Sender
Sends SNMP traps to a server (for testing or simulation).
Cross-platform: Windows and Linux.
Requires: Python 3.6+, pysnmp>=4.4.12, pyasn1>=0.4.8
"""

import logging
import sys
import platform
from datetime import datetime
from typing import Optional, List, Tuple, Any

# Check Python version (requires 3.6+)
if sys.version_info < (3, 6):
    print(f"ERROR: Python 3.6+ required, but you have {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}", file=sys.stderr)
    sys.exit(1)

from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import ntforg
from pysnmp.proto import rfc1902

# Check pysnmp and pyasn1 versions for debugging
try:
    import pysnmp
    PYSNMP_VERSION = pysnmp.__version__
except (ImportError, AttributeError):
    PYSNMP_VERSION = "not installed"

try:
    import pyasn1
    PYASN1_VERSION = pyasn1.__version__
except (ImportError, AttributeError):
    PYASN1_VERSION = "not installed"

# UPS-MIB OID mappings (RFC 1628) - for reference
UPS_OIDS = {
    '1.3.6.1.2.1.33.2.1': 'upsTrapOnBattery',
    '1.3.6.1.2.1.33.1.6.3.6': 'upsAlarmInputBad',
    '1.3.6.1.2.1.33.1.6.3.8': 'upsAlarmOutputOverload',
    '1.3.6.1.2.1.33.1.6.3.18': 'upsAlarmGeneralFault',
    '1.3.6.1.2.1.33.1.6.3.13': 'upsAlarmChargerFailed',
    '1.3.6.1.2.1.33.1.6.3.20': 'upsAlarmCommunicationsLost',
    '1.3.6.1.2.1.33.2.2': 'upsTrapTestCompleted',
    '1.3.6.1.2.1.33.1.6.3.1': 'upsAlarmBatteryLow',
    '1.3.6.1.2.1.33.1.6.3.2': 'upsAlarmBatteryDischarged',
    '1.3.6.1.2.1.33.1.6.3.3': 'upsAlarmBatteryTestFailure',
    '1.3.6.1.2.1.33.1.6.3.4': 'upsAlarmBatteryReplacement',
    '1.3.6.1.2.1.33.1.6.3.5': 'upsAlarmBatteryTemperature',
}

# Predefined trap messages
# These match the actual format from UPS devices
PREDEFINED_TRAPS = {
    'battery_power': {
        'trap_oid': '1.3.6.1.4.1.935.0.5',  # Trap OID that appears in snmpTrapOID
        'trap_name': 'UPSBatteryPower',
        'message': 'UPS has switched to battery power',
        'variables': [
            # The message appears as a variable with OID 1.3.6.1.4.1.935.0.5
            ('1.3.6.1.4.1.935.0.5', rfc1902.OctetString('UPS has switched to battery power')),
        ]
    },
    'power_restored': {
        'trap_oid': '1.3.6.1.4.1.935.0.9',  # Trap OID that appears in snmpTrapOID
        'trap_name': 'UtilityPowerRestored',
        'message': 'Utility power has been restored.',
        'variables': [
            # The message appears as a variable with OID 1.3.6.1.4.1.935.0.9
            ('1.3.6.1.4.1.935.0.9', rfc1902.OctetString('Utility power has been restored.')),
        ]
    },
    'battery_low': {
        'trap_oid': '1.3.6.1.2.1.33.1.6.3.1',
        'trap_name': 'upsAlarmBatteryLow',
        'message': 'Battery charge below acceptable threshold',
        'variables': [
            ('1.3.6.1.2.1.33.1.6.3.1', rfc1902.Integer(1)),
        ]
    },
    'input_bad': {
        'trap_oid': '1.3.6.1.2.1.33.1.6.3.6',
        'trap_name': 'upsAlarmInputBad',
        'message': 'Input voltage/frequency out of tolerance',
        'variables': [
            ('1.3.6.1.2.1.33.1.6.3.6', rfc1902.Integer(1)),
        ]
    },
}


class UPSTrapSender:
    """SNMP Trap Sender for UPS devices."""
    
    def __init__(
        self,
        target_host: str = 'localhost',
        target_port: int = 162,
        community: str = 'public',
        snmp_version: str = '2c'
    ):
        """
        Initialize the UPS SNMP Trap Sender.
        
        Args:
            target_host: Target server hostname or IP address
            target_port: Target server port (default 162)
            community: SNMP community string (default 'public')
            snmp_version: SNMP version ('1' or '2c', default '2c')
        """
        self.target_host = target_host
        self.target_port = target_port
        self.community = community
        self.snmp_version = snmp_version
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger(__name__)
        
        # Validate SNMP version
        if self.snmp_version not in ['1', '2c']:
            raise ValueError(f"Unsupported SNMP version: {self.snmp_version}")
        
        # Create SNMP engine
        self.snmp_engine = engine.SnmpEngine()
        
        # Setup transport
        self._setup_transport()
        
        # Setup SNMP configuration
        self._setup_snmp()
    
    def _setup_transport(self):
        """Setup UDP transport."""
        config.add_transport(
            self.snmp_engine,
            udp.DOMAIN_NAME + (1,),
            udp.UdpTransport().open_client_mode()
        )
    
    def _setup_snmp(self):
        """Setup SNMP version and community."""
        if self.snmp_version == '1':
            try:
                config.add_v1_system(self.snmp_engine, 'my-area', self.community)
            except AttributeError:
                try:
                    config.addV1System(self.snmp_engine, 'my-area', self.community)
                except AttributeError:
                    self.logger.warning("SNMPv1 system configuration not available")
        elif self.snmp_version == '2c':
            # For SNMPv2c, try to configure but don't require it
            # v2c traps can work without explicit configuration
            v2c_configured = False
            try:
                config.add_v2c_system(self.snmp_engine, 'my-area', self.community)
                v2c_configured = True
            except AttributeError:
                try:
                    config.addV2cSystem(self.snmp_engine, 'my-area', self.community)
                    v2c_configured = True
                except AttributeError:
                    # v2c doesn't require explicit configuration - this is normal
                    pass
            
            if not v2c_configured:
                # This is expected - SNMPv2c traps don't require explicit configuration
                self.logger.debug("SNMPv2c explicit configuration not available - traps will still be sent")
    
    def send_trap(
        self,
        trap_oid: str,
        var_binds: Optional[List[Tuple[str, Any]]] = None,
        enterprise_oid: Optional[str] = None
    ) -> bool:
        """
        Send an SNMP trap.
        
        Args:
            trap_oid: Trap OID (e.g., '1.3.6.1.2.1.33.2.1')
            var_binds: List of (OID, value) tuples for variable bindings
            enterprise_oid: Enterprise OID (optional)
        
        Returns:
            True if trap was sent successfully, False otherwise
        """
        try:
            # Default variable bindings
            if var_binds is None:
                var_binds = []
            
            # Prepare variable bindings
            formatted_var_binds = []
            
            # Add sysUpTime (standard SNMP trap variable)
            sys_uptime = rfc1902.TimeTicks(int(datetime.now().timestamp() * 100) % (2**32))
            formatted_var_binds.append(
                (rfc1902.ObjectIdentifier('1.3.6.1.2.1.1.3.0'), sys_uptime)
            )
            
            # Add snmpTrapOID (standard SNMP trap variable)
            formatted_var_binds.append(
                (rfc1902.ObjectIdentifier('1.3.6.1.6.3.1.1.4.1.0'), rfc1902.ObjectIdentifier(trap_oid))
            )
            
            # Add custom variable bindings
            for oid, value in var_binds:
                if isinstance(oid, str):
                    oid = rfc1902.ObjectIdentifier(oid)
                
                # Convert value to appropriate type if needed
                if isinstance(value, (int, rfc1902.Integer)):
                    if not isinstance(value, rfc1902.Integer):
                        value = rfc1902.Integer(value)
                elif isinstance(value, str):
                    if not isinstance(value, rfc1902.OctetString):
                        value = rfc1902.OctetString(value)
                elif isinstance(value, rfc1902.TimeTicks):
                    pass  # Already correct type
                elif isinstance(value, rfc1902.ObjectIdentifier):
                    pass  # Already correct type
                else:
                    # Try to convert to OctetString as fallback
                    value = rfc1902.OctetString(str(value))
                
                formatted_var_binds.append((oid, value))
            
            # Send trap using NotificationOriginator
            # Create callback context to capture results
            cbCtx = {'done': False, 'error_indication': None, 'error_status': None}
            
            def cbFun(snmpEngine, stateReference, errorIndication, errorStatus, errorIndex, varBinds, cbCtx):
                """Callback function for trap sending."""
                cbCtx['error_indication'] = errorIndication
                cbCtx['error_status'] = errorStatus
                cbCtx['error_index'] = errorIndex
                cbCtx['var_binds'] = varBinds
                cbCtx['done'] = True
            
            # Create NotificationOriginator (takes no arguments)
            notification_originator = ntforg.NotificationOriginator()
            
            # Try to set callback - check available methods
            if hasattr(notification_originator, 'registerCallback'):
                notification_originator.registerCallback(cbFun, cbCtx)
            elif hasattr(notification_originator, 'setCallback'):
                notification_originator.setCallback(cbFun, cbCtx)
            else:
                # Store callback in context for later use
                cbCtx['callback'] = cbFun
            
            # Send the trap - use the correct method names (send_varbinds or send_pdu)
            # Based on available methods: ['send_pdu', 'send_varbinds']
            # Track which method succeeded
            method_succeeded = False
            use_raw_socket = False
            
            # For SNMPv2c, the standard methods often fail with context_name=None
            # So we'll try them but fall back to raw socket if they fail
            if self.snmp_version == '2c':
                # For v2c, prefer raw socket method as it's more reliable
                self.logger.debug("Using raw socket method for SNMPv2c (more reliable)")
                use_raw_socket = True
            else:
                # For v1, try standard methods first
                try:
                    # Try send_varbinds (lowercase with underscore - the actual method name)
                    context_name = 'my-area' if self.snmp_version == '1' else None
                    notification_originator.send_varbinds(
                        self.snmp_engine,
                        context_name,
                        (self.target_host, self.target_port),
                        None,  # contextName (additional context)
                        'trap',  # notifyType
                        formatted_var_binds
                    )
                    method_succeeded = True
                except (AttributeError, TypeError, Exception) as e:
                    self.logger.debug(f"send_varbinds failed: {e}")
                    try:
                        # Try send_pdu (lowercase with underscore)
                        context_name = 'my-area' if self.snmp_version == '1' else None
                        notification_originator.send_pdu(
                            self.snmp_engine,
                            context_name,
                            (self.target_host, self.target_port),
                            None,
                            'trap',
                            formatted_var_binds
                        )
                        method_succeeded = True
                    except (AttributeError, TypeError, Exception) as e2:
                        # Standard methods not available or failed - use fallback
                        self.logger.debug(f"send_pdu failed: {e2}")
                        self.logger.info("Falling back to raw UDP socket method...")
                        use_raw_socket = True
            
            # Handle different sending methods
            if use_raw_socket:
                # Use raw socket fallback (most reliable across platforms)
                try:
                    self._send_trap_raw_socket(formatted_var_binds, trap_oid)
                    # Success - no need to wait for dispatcher
                    error_indication = None
                    error_status = None
                    error_index = None
                    var_binds_out = []
                    # Cleanup dispatcher since we didn't use it
                    try:
                        if hasattr(self.snmp_engine, 'transport_dispatcher'):
                            self.snmp_engine.transport_dispatcher.close_dispatcher()
                    except:
                        pass
                except Exception as e:
                    self.logger.error(f"Raw socket method failed: {e}")
                    raise
            elif method_succeeded:
                # Standard methods worked - wait for callback
                # Start dispatcher and wait for callback
                self.snmp_engine.transport_dispatcher.job_started(1)
                
                # Wait for callback to complete (with timeout)
                import time
                timeout = 2.0
                start_time = time.time()
                while not cbCtx.get('done', False) and (time.time() - start_time) < timeout:
                    self.snmp_engine.transport_dispatcher.run_once(timeout=0.1)
                    time.sleep(0.01)
                
                # Get results from callback
                error_indication = cbCtx.get('error_indication')
                error_status = cbCtx.get('error_status')
                error_index = cbCtx.get('error_index')
                var_binds_out = cbCtx.get('var_binds', [])
                
                # Stop dispatcher
                try:
                    self.snmp_engine.transport_dispatcher.close_dispatcher()
                except:
                    pass
            else:
                # Should not reach here, but handle gracefully
                raise Exception("No suitable method found to send trap")
            
            if error_indication:
                self.logger.error(f"Error sending trap: {error_indication}")
                return False
            elif error_status:
                self.logger.error(f"SNMP error: {error_status.prettyPrint()}")
                return False
            else:
                self.logger.info(f"Trap sent successfully to {self.target_host}:{self.target_port}")
                self.logger.info(f"  Trap OID: {trap_oid}")
                return True
        
        except Exception as e:
            self.logger.error(f"Exception while sending trap: {e}", exc_info=True)
            return False
    
    def send_predefined_trap(self, trap_name: str) -> bool:
        """
        Send a predefined trap.
        
        Args:
            trap_name: Name of predefined trap (e.g., 'battery_power', 'power_restored')
        
        Returns:
            True if trap was sent successfully, False otherwise
        """
        if trap_name not in PREDEFINED_TRAPS:
            self.logger.error(f"Unknown predefined trap: {trap_name}")
            self.logger.info(f"Available traps: {', '.join(PREDEFINED_TRAPS.keys())}")
            return False
        
        trap_info = PREDEFINED_TRAPS[trap_name]
        self.logger.info(f"Sending predefined trap: {trap_info['trap_name']}")
        self.logger.info(f"  Message: {trap_info['message']}")
        
        return self.send_trap(
            trap_oid=trap_info['trap_oid'],
            var_binds=trap_info['variables']
        )
    
    def _send_trap_raw_socket(self, var_binds, trap_oid):
        """
        Fallback method: Send trap using raw UDP socket.
        This is a simpler approach that should work when pysnmp API methods fail.
        Works reliably on both Windows and Linux.
        
        Note: Different pysnmp/pyasn1 versions on Windows vs Linux may cause
        different behavior due to stricter type checking in newer versions.
        """
        import socket
        from pysnmp.proto.api import v2c as api_v2c
        from pysnmp.proto import rfc1905
        # rfc1902 is already imported at module level, use that
        
        # Log platform and versions for debugging
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        self.logger.debug(f"Platform: {platform.system()} {platform.release()}")
        self.logger.debug(f"Python: {python_version}")
        self.logger.debug(f"pysnmp version: {PYSNMP_VERSION}, pyasn1 version: {PYASN1_VERSION}")
        
        # Build SNMP v2c trap message
        # Linux often has stricter type checking, so we need to be more careful
        var_bind_list = rfc1905.VarBindList()
        
        for oid, value in var_binds:
            var_bind_created = False
            error_messages = []
            
            # Method 1: Try VarBind constructor with tuple (works on Windows, may fail on Linux)
            try:
                var_bind = rfc1905.VarBind((oid, value))
                var_bind_list.append(var_bind)
                var_bind_created = True
            except Exception as e1:
                error_messages.append(f"Tuple constructor: {str(e1)[:100]}")
            
            # Method 2: Create empty VarBind and set components with verifyConstraints=False
            # This is more compatible with strict type checking on Linux
            if not var_bind_created:
                try:
                    var_bind = rfc1905.VarBind()
                    var_bind.setComponentByPosition(0, oid)
                    # Use verifyConstraints=False to bypass strict type checking
                    # This is needed on Linux where pyasn1 is stricter
                    var_bind.setComponentByPosition(1, value, verifyConstraints=False)
                    var_bind_list.append(var_bind)
                    var_bind_created = True
                except Exception as e2:
                    error_messages.append(f"setComponentByPosition: {str(e2)[:100]}")
            
            # Method 3: Try using the VarBind's clone method or direct assignment
            if not var_bind_created:
                try:
                    # Create VarBind and use direct component assignment
                    var_bind = rfc1905.VarBind()
                    var_bind[0] = oid
                    var_bind[1] = value
                    var_bind_list.append(var_bind)
                    var_bind_created = True
                except Exception as e3:
                    error_messages.append(f"Direct assignment: {str(e3)[:100]}")
            
            # Method 4: Try using VarBindList constructor with single tuple
            if not var_bind_created:
                try:
                    temp_list = rfc1905.VarBindList([(oid, value)])
                    var_bind_list.extend(temp_list)
                    var_bind_created = True
                except Exception as e4:
                    error_messages.append(f"VarBindList constructor: {str(e4)[:100]}")
            
            if not var_bind_created:
                error_msg = f"Could not create VarBind for OID {oid} with value type {type(value).__name__}"
                error_msg += f"\nPlatform: {platform.system()}, pysnmp: {PYSNMP_VERSION}, pyasn1: {PYASN1_VERSION}"
                error_msg += f"\nAttempted methods:\n" + "\n".join(f"  - {msg}" for msg in error_messages)
                self.logger.error(error_msg)
                raise Exception(error_msg)
        
        # Create TrapPDU
        # SNMPv2c TrapPDU structure: [request-id, error-status, error-index, var-bind-list]
        # For traps: request-id=0, error-status=0, error-index=0, var-bind-list=our list
        pdu = api_v2c.TrapPDU()
        
        # Set all components of TrapPDU
        # Use verifyConstraints=False to bypass strict type checking on Linux
        try:
            # Component 0: request-id (Integer32, typically 0 for traps)
            pdu.setComponentByPosition(0, rfc1902.Integer(0), verifyConstraints=False)
            # Component 1: error-status (Integer with enums, 0 for traps)
            pdu.setComponentByPosition(1, rfc1902.Integer(0), verifyConstraints=False)
            # Component 2: error-index (Integer, 0 for traps)
            pdu.setComponentByPosition(2, rfc1902.Integer(0), verifyConstraints=False)
            # Component 3: var-bind-list
            pdu.setComponentByPosition(3, var_bind_list, verifyConstraints=False)
        except Exception as e:
            self.logger.debug(f"setComponentByPosition with verifyConstraints=False failed: {e}")
            # Try alternative: use direct assignment or named components
            try:
                # Try setting components by name or direct assignment
                pdu[0] = rfc1902.Integer(0)
                pdu[1] = rfc1902.Integer(0)
                pdu[2] = rfc1902.Integer(0)
                pdu[3] = var_bind_list
            except Exception as e2:
                self.logger.debug(f"Direct assignment failed: {e2}")
                # Last resort: try creating PDU with all components at once
                try:
                    # Create PDU with components in constructor if possible
                    # rfc1902 is already imported at module level
                    # Build the PDU manually using the proper structure
                    pdu = api_v2c.TrapPDU()
                    # Try using setComponentByName if available
                    if hasattr(pdu, 'setComponentByName'):
                        pdu.setComponentByName('request-id', rfc1902.Integer(0), verifyConstraints=False)
                        pdu.setComponentByName('error-status', rfc1902.Integer(0), verifyConstraints=False)
                        pdu.setComponentByName('error-index', rfc1902.Integer(0), verifyConstraints=False)
                        pdu.setComponentByName('variable-bindings', var_bind_list, verifyConstraints=False)
                    else:
                        raise Exception("No suitable method to set TrapPDU components")
                except Exception as e3:
                    self.logger.error(f"All TrapPDU construction methods failed: {e3}")
                    raise Exception(f"Could not create TrapPDU: {e3}")
        
        # Build SNMP message
        # In pysnmp 7.x, Message structure: [version, community, pdu]
        # version=1 for SNMPv2c, community=OctetString, pdu=TrapPDU
        msg = api_v2c.Message()
        
        # Set version (SNMPv2c = 1)
        try:
            msg.setComponentByPosition(0, rfc1902.Integer(1), verifyConstraints=False)
        except Exception as e:
            self.logger.debug(f"Failed to set version: {e}")
            try:
                msg[0] = rfc1902.Integer(1)
            except Exception as e2:
                raise Exception(f"Could not set version on Message: {e2}")
        
        # Set community string (position 1)
        community_set = False
        try:
            # Method 1: Try setComponentByPosition
            community_octet = rfc1902.OctetString(self.community)
            msg.setComponentByPosition(1, community_octet, verifyConstraints=False)
            community_set = True
        except Exception as e1:
            self.logger.debug(f"setComponentByPosition for community failed: {e1}")
        
        if not community_set:
            try:
                # Method 2: Try direct assignment
                msg[1] = rfc1902.OctetString(self.community)
                community_set = True
            except Exception as e2:
                self.logger.debug(f"Direct assignment for community failed: {e2}")
        
        if not community_set:
            try:
                # Method 3: Try setComponentByName
                if hasattr(msg, 'setComponentByName'):
                    msg.setComponentByName('community', rfc1902.OctetString(self.community), verifyConstraints=False)
                    community_set = True
            except Exception as e3:
                self.logger.debug(f"setComponentByName for community failed: {e3}")
        
        if not community_set:
            raise Exception(f"Could not set community string on Message object")
        
        # Set PDU (position 2)
        pdu_set = False
        try:
            msg.setComponentByPosition(2, pdu, verifyConstraints=False)
            pdu_set = True
        except Exception as e:
            self.logger.debug(f"setComponentByPosition for PDU failed: {e}")
        
        if not pdu_set:
            try:
                msg[2] = pdu
                pdu_set = True
            except Exception as e2:
                self.logger.debug(f"Direct assignment for PDU failed: {e2}")
        
        if not pdu_set:
            try:
                if hasattr(msg, 'setPDU'):
                    msg.setPDU(pdu)
                    pdu_set = True
            except Exception as e3:
                self.logger.debug(f"setPDU failed: {e3}")
        
        if not pdu_set:
            raise Exception(f"Could not set PDU on Message")
        
        # Verify message is properly constructed
        if not msg.hasValue():
            raise Exception("Message object has no value after setting components")
        
        # Encode message - use pyasn1 BER encoder (standard for pysnmp 7.x)
        try:
            # Import BER encoder from pyasn1
            from pyasn1.codec.ber import encoder as ber_encoder
            # Encode the message using BER encoder
            encoded_msg = ber_encoder.encode(msg)
            # Ensure it's bytes
            if not isinstance(encoded_msg, bytes):
                encoded_msg = bytes(encoded_msg)
        except ImportError as e:
            self.logger.error(f"Failed to import pyasn1 BER encoder: {e}")
            raise Exception(f"Could not import pyasn1 encoder: {e}")
        except Exception as e:
            self.logger.error(f"Failed to encode SNMP message: {e}")
            # Try alternative: check if message is properly constructed
            try:
                # Verify message has components
                if not msg.hasValue():
                    raise Exception("Message object has no value - components may not be set correctly")
                # Try encoding again with error details
                self.logger.debug(f"Message components: {list(msg.keys()) if hasattr(msg, 'keys') else 'N/A'}")
                encoded_msg = ber_encoder.encode(msg)
                if not isinstance(encoded_msg, bytes):
                    encoded_msg = bytes(encoded_msg)
            except Exception as e2:
                available_methods = [m for m in dir(msg) if not m.startswith('_')]
                raise Exception(f"Could not encode SNMP message: {e2}. Available methods: {available_methods}")
        
        # Send via raw UDP socket (works on both Windows and Linux)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(encoded_msg, (self.target_host, self.target_port))
            self.logger.info(f"Trap sent via raw UDP socket to {self.target_host}:{self.target_port}")
        except Exception as e:
            raise Exception(f"Failed to send UDP packet: {e}")
        finally:
            sock.close()
    
    def send_custom_trap(
        self,
        trap_oid: str,
        message: str,
        additional_vars: Optional[List[Tuple[str, str]]] = None
    ) -> bool:
        """
        Send a custom trap with a message.
        
        Args:
            trap_oid: Trap OID
            message: Message string to include
            additional_vars: Additional (OID, value) pairs as strings
        
        Returns:
            True if trap was sent successfully, False otherwise
        """
        var_binds = []
        
        # Add the message as a variable
        var_binds.append((trap_oid, rfc1902.OctetString(message)))
        
        # Add additional variables if provided
        if additional_vars:
            for oid, value in additional_vars:
                var_binds.append((oid, rfc1902.OctetString(value)))
        
        return self.send_trap(trap_oid=trap_oid, var_binds=var_binds)


def main():
    """Main entry point."""
    import argparse
    
    # Check dependencies first
    try:
        import pysnmp
        import pyasn1
    except ImportError as e:
        print(f"ERROR: Required package not installed: {e}", file=sys.stderr)
        print(f"Please install pysnmp: pip install pysnmp", file=sys.stderr)
        sys.exit(1)
    
    # Log versions for debugging
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python: {python_version}")
    print(f"pysnmp version: {PYSNMP_VERSION}, pyasn1 version: {PYASN1_VERSION}")
    
    parser = argparse.ArgumentParser(
        description='UPS SNMP Trap Sender - Send SNMP traps to a server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Send battery power trap to localhost
  python ups_snmp_trap_sender.py --trap battery_power
  
  # Send power restored trap to specific server
  python ups_snmp_trap_sender.py --trap power_restored --host 192.168.111.137 --port 162
  
  # Send custom trap
  python ups_snmp_trap_sender.py --custom --oid 1.3.6.1.4.1.935.0.9 --message "Utility power has been restored."
  
  # Send to custom port (for testing)
  python ups_snmp_trap_sender.py --trap battery_power --host localhost --port 1162
  
Available predefined traps:
  - battery_power: UPS switched to battery power
  - power_restored: Utility power has been restored
  - battery_low: Battery charge below threshold
  - input_bad: Input voltage/frequency out of tolerance
        """
    )
    
    parser.add_argument(
        '--host', '-H',
        type=str,
        default='localhost',
        help='Target server hostname or IP (default: localhost)'
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=162,
        help='Target server port (default: 162)'
    )
    
    parser.add_argument(
        '--community', '-c',
        type=str,
        default='public',
        help='SNMP community string (default: public)'
    )
    
    parser.add_argument(
        '--trap', '-t',
        type=str,
        choices=list(PREDEFINED_TRAPS.keys()),
        help='Predefined trap to send'
    )
    
    parser.add_argument(
        '--custom',
        action='store_true',
        help='Send custom trap (requires --oid and --message)'
    )
    
    parser.add_argument(
        '--oid', '-o',
        type=str,
        help='Trap OID for custom trap'
    )
    
    parser.add_argument(
        '--message', '-m',
        type=str,
        help='Message for custom trap'
    )
    
    parser.add_argument(
        '--version', '-v',
        type=str,
        choices=['1', '2c'],
        default='2c',
        help='SNMP version (default: 2c)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.custom:
        if not args.oid or not args.message:
            parser.error("--custom requires --oid and --message")
    elif not args.trap:
        parser.error("Either --trap or --custom must be specified")
    
    # Create sender
    try:
        sender = UPSTrapSender(
            target_host=args.host,
            target_port=args.port,
            community=args.community,
            snmp_version=args.version
        )
    except Exception as e:
        print(f"ERROR: Failed to create SNMP trap sender: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Send trap
    try:
        if args.custom:
            success = sender.send_custom_trap(
                trap_oid=args.oid,
                message=args.message
            )
        else:
            success = sender.send_predefined_trap(args.trap)
    except Exception as e:
        print(f"ERROR: Failed to send trap: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup asyncio event loop to prevent warnings
        try:
            import asyncio
            # Close any pending asyncio tasks
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop running
                pass
            
            if loop and not loop.is_closed():
                # Cancel all pending tasks
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                
                # Give tasks a moment to cancel
                if pending:
                    try:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    except:
                        pass
                
                # Close the loop
                try:
                    loop.close()
                except:
                    pass
        except Exception as e:
            # Ignore cleanup errors - they're not critical
            pass
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

