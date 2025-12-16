#!/usr/bin/env python3
"""
UPS GPIO LED Controller
Receives SNMP traps from UPS devices and controls GPIO pins on Raspberry Pi to trigger LED devices.
Cross-platform: Works on Raspberry Pi 4 (Linux/Debian) with GPIO support, gracefully handles Windows (for development).

Features:
- Receives SNMP traps from UPS
- Detects alarm conditions
- Controls GPIO pins to trigger LED devices
- Supports multiple GPIO pins for different alarm types
- Configurable LED behaviors (on/off, blinking patterns)

Installation on Debian:
  sudo apt-get install python3-pysnmp4 python3-pyasn1
  pip3 install RPi.GPIO  # For GPIO support on Raspberry Pi
"""

import json
import logging
import platform
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

# Ensure importlib.util is available before pysnmp imports
# Some pysnmp versions (especially Debian python3-pysnmp4) may need this
try:
    import importlib.util
    import importlib.machinery
except ImportError:
    # Python < 3.4 doesn't have importlib.util, but we require Python 3.7+
    pass

# Compatibility shim for Python 3.12+ where 'imp' module was removed
# The Debian python3-pysnmp4 package uses the deprecated 'imp' module
if sys.version_info >= (3, 12):
    try:
        import imp
    except ImportError:
        # Python 3.12+ removed 'imp' module - provide compatibility shim
        # Create a minimal shim that pysnmp can use
        import types
        
        class ImpShim:
            """Minimal compatibility shim for deprecated 'imp' module."""
            PY_SOURCE = 1
            PY_COMPILED = 2
            C_EXTENSION = 3
            PY_RESOURCE = 4
            PKG_DIRECTORY = 5
            C_BUILTIN = 6
            PY_FROZEN = 7
            
            @staticmethod
            def find_module(name, path=None):
                """Minimal find_module implementation."""
                try:
                    spec = importlib.util.find_spec(name, path)
                    if spec is None:
                        return None
                    if spec.loader is None:
                        return None
                    return spec.loader
                except (ImportError, ValueError, AttributeError):
                    return None
            
            @staticmethod
            def load_module(name, file=None, pathname=None, description=None):
                """Minimal load_module implementation."""
                if file is None and pathname:
                    spec = importlib.util.spec_from_file_location(name, pathname)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        return module
                # Fallback to importlib
                return importlib.import_module(name)
        
        # Inject the shim into sys.modules so pysnmp can use it
        imp_module = types.ModuleType('imp')
        for attr in ['PY_SOURCE', 'PY_COMPILED', 'C_EXTENSION', 'PY_RESOURCE', 
                     'PKG_DIRECTORY', 'C_BUILTIN', 'PY_FROZEN']:
            setattr(imp_module, attr, getattr(ImpShim, attr))
        imp_module.find_module = ImpShim.find_module
        imp_module.load_module = ImpShim.load_module
        sys.modules['imp'] = imp_module

# Import pysnmp - works with both pip install and Debian package python3-pysnmp4
# Handle compatibility: Debian python3-pysnmp4 uses old asyncio API incompatible with Python 3.11+
USE_ASYNCIO = False
USE_TWISTED = False

# First, try to import base pysnmp modules
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import ntfrcv
from pysnmp.proto import rfc1902


# Now try to import transport - this is separate so we can give better error messages
# Check Python version - Python 3.11+ removed asyncio.coroutine
python_version = sys.version_info
is_python_311_plus = python_version >= (3, 11)

# Try twisted transport first if Python 3.11+ (avoids asyncio.coroutine issue)
if is_python_311_plus:
    try:
        from pysnmp.carrier.twisted.dgram import udp
        USE_TWISTED = True
    except ImportError:
        # Twisted not available, try asyncio (might work with newer pysnmp)
        try:
            from pysnmp.carrier.asyncio.dgram import udp
            USE_ASYNCIO = True
        except (ImportError, AttributeError) as e:
            error_msg = str(e).lower()
            if "coroutine" in error_msg or "asyncio" in error_msg or "has no attribute" in error_msg:
                print("ERROR: The Debian python3-pysnmp4 package is incompatible with Python 3.11+", file=sys.stderr)
                print(f"Error details: {e}", file=sys.stderr)
                print("", file=sys.stderr)
                print("Solution: Install pysnmp via pip instead:", file=sys.stderr)
                print("  sudo apt-get remove python3-pysnmp4", file=sys.stderr)
                print("  pip3 install --upgrade pysnmp pyasn1", file=sys.stderr)
                print("", file=sys.stderr)
                print("Or install twisted for alternative transport:", file=sys.stderr)
                print("  pip3 install twisted", file=sys.stderr)
                sys.exit(1)
            else:
                print(f"ERROR: Could not import pysnmp transport: {e}", file=sys.stderr)
                print("Try: pip3 install --upgrade pysnmp pyasn1", file=sys.stderr)
                sys.exit(1)
else:
    # Python < 3.11: Try asyncio first, then twisted
    try:
        from pysnmp.carrier.asyncio.dgram import udp
        USE_ASYNCIO = True
    except (ImportError, AttributeError) as e:
        # Fall back to twisted
        try:
            from pysnmp.carrier.twisted.dgram import udp
            USE_TWISTED = True
        except ImportError:
            print(f"ERROR: Could not import any compatible pysnmp transport: {e}", file=sys.stderr)
            print("Try: pip3 install --upgrade pysnmp pyasn1", file=sys.stderr)
            sys.exit(1)

# Verify we have a transport
if not USE_ASYNCIO and not USE_TWISTED:
    print("ERROR: No pysnmp transport could be imported", file=sys.stderr)
    print("Try: pip3 install --upgrade pysnmp pyasn1", file=sys.stderr)
    sys.exit(1)

# Try to import RPi.GPIO for Raspberry Pi
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    # GPIO not available (Windows or not on Raspberry Pi)
    GPIO_AVAILABLE = False
    GPIO = None

# UPS-MIB OID mappings (RFC 1628) - same as in trap receiver
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

# Alarm severity levels
ALARM_SEVERITY = {
    'upsTrapOnBattery': 'warning',
    'upsAlarmInputBad': 'warning',
    'upsAlarmOutputOverload': 'critical',
    'upsAlarmGeneralFault': 'critical',
    'upsAlarmChargerFailed': 'critical',
    'upsAlarmCommunicationsLost': 'critical',
    'upsTrapTestCompleted': 'info',
    'upsAlarmBatteryLow': 'warning',
    'upsAlarmBatteryDischarged': 'critical',
    'upsAlarmBatteryTestFailure': 'warning',
    'upsAlarmBatteryReplacement': 'warning',
    'upsAlarmBatteryTemperature': 'warning',
}


class GPIOLEDController:
    """Controls GPIO pins for LED devices based on UPS alarm conditions."""
    
    def __init__(
        self,
        gpio_pins: Dict[str, int],
        blink_enabled: bool = True,
        blink_interval: float = 0.5,
        active_high: bool = True
    ):
        """
        Initialize GPIO LED Controller.
        
        Args:
            gpio_pins: Dictionary mapping alarm types to GPIO pin numbers
                      Example: {'critical': 18, 'warning': 19, 'info': 20}
            blink_enabled: Enable blinking for alarms (default: True)
            blink_interval: Blink interval in seconds (default: 0.5)
            active_high: True if LED is active high (default: True)
        """
        self.gpio_pins = gpio_pins
        self.blink_enabled = blink_enabled
        self.blink_interval = blink_interval
        self.active_high = active_high
        self.is_windows = platform.system() == 'Windows'
        self.gpio_available = GPIO_AVAILABLE and not self.is_windows
        
        # Track LED states and blink threads
        self.led_states = {}  # pin -> state (True/False)
        self.blink_threads = {}  # pin -> Thread
        self.blink_stop_flags = {}  # pin -> threading.Event
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize GPIO if available
        if self.gpio_available:
            try:
                GPIO.setmode(GPIO.BCM)  # Use BCM pin numbering
                GPIO.setwarnings(False)  # Disable warnings
                
                # Setup all GPIO pins as outputs
                for pin in self.gpio_pins.values():
                    GPIO.setup(pin, GPIO.OUT)
                    # Initialize all LEDs to OFF
                    GPIO.output(pin, GPIO.LOW if self.active_high else GPIO.HIGH)
                    self.led_states[pin] = False
                    self.logger.info(f"GPIO pin {pin} configured as output (initialized to OFF)")
                
                self.logger.info(f"GPIO initialized successfully on {len(self.gpio_pins)} pin(s)")
            except Exception as e:
                self.logger.error(f"Failed to initialize GPIO: {e}")
                self.gpio_available = False
        else:
            if self.is_windows:
                self.logger.warning("Running on Windows - GPIO operations will be simulated")
            else:
                self.logger.warning("RPi.GPIO not available - GPIO operations will be simulated")
    
    def _set_led(self, pin: int, state: bool):
        """
        Set LED state (internal method).
        
        Args:
            pin: GPIO pin number
            state: True for ON, False for OFF
        """
        if not self.gpio_available:
            # Simulate on Windows or when GPIO not available
            self.logger.info(f"[SIMULATED] GPIO pin {pin} -> {'ON' if state else 'OFF'}")
            return
        
        try:
            if self.active_high:
                GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)
            else:
                GPIO.output(pin, GPIO.LOW if state else GPIO.HIGH)
            self.led_states[pin] = state
        except Exception as e:
            self.logger.error(f"Error setting GPIO pin {pin}: {e}")
    
    def _stop_blink(self, pin: int):
        """Stop blinking for a specific pin."""
        if pin in self.blink_stop_flags:
            self.blink_stop_flags[pin].set()
        if pin in self.blink_threads:
            thread = self.blink_threads[pin]
            if thread.is_alive():
                thread.join(timeout=1.0)
            del self.blink_threads[pin]
        if pin in self.blink_stop_flags:
            del self.blink_stop_flags[pin]
    
    def _blink_led(self, pin: int):
        """Blink LED in a separate thread."""
        stop_event = threading.Event()
        self.blink_stop_flags[pin] = stop_event
        
        def blink_loop():
            state = False
            while not stop_event.is_set():
                self._set_led(pin, state)
                state = not state
                if stop_event.wait(self.blink_interval):
                    break
        
        thread = threading.Thread(target=blink_loop, daemon=True)
        self.blink_threads[pin] = thread
        thread.start()
    
    def trigger_alarm(self, alarm_type: str, severity: str = None):
        """
        Trigger LED for an alarm.
        
        Args:
            alarm_type: Alarm type (e.g., 'critical', 'warning', 'info')
            severity: Severity level (overrides alarm_type if provided)
        """
        # Determine which pin to use
        pin_key = severity if severity else alarm_type
        
        # Map to available pins
        if pin_key not in self.gpio_pins:
            # Try to find a matching pin
            if 'critical' in self.gpio_pins:
                pin_key = 'critical'
            elif 'warning' in self.gpio_pins:
                pin_key = 'warning'
            elif len(self.gpio_pins) > 0:
                # Use first available pin
                pin_key = list(self.gpio_pins.keys())[0]
            else:
                self.logger.warning(f"No GPIO pin configured for alarm type: {alarm_type}")
                return
        
        pin = self.gpio_pins[pin_key]
        
        # Stop any existing blink for this pin
        self._stop_blink(pin)
        
        # Turn on LED
        if self.blink_enabled:
            self._blink_led(pin)
            self.logger.info(f"Triggered blinking LED on GPIO pin {pin} for {alarm_type} alarm")
        else:
            self._set_led(pin, True)
            self.logger.info(f"Triggered LED ON on GPIO pin {pin} for {alarm_type} alarm")
    
    def clear_alarm(self, alarm_type: str = None, pin: int = None):
        """
        Clear LED alarm (turn off).
        
        Args:
            alarm_type: Alarm type to clear (optional)
            pin: Specific GPIO pin to clear (optional)
        """
        if pin is not None:
            # Clear specific pin
            self._stop_blink(pin)
            self._set_led(pin, False)
            self.logger.info(f"Cleared LED on GPIO pin {pin}")
        elif alarm_type:
            # Clear by alarm type
            pin_key = alarm_type
            if pin_key in self.gpio_pins:
                pin = self.gpio_pins[pin_key]
                self._stop_blink(pin)
                self._set_led(pin, False)
                self.logger.info(f"Cleared LED on GPIO pin {pin} for {alarm_type} alarm")
        else:
            # Clear all LEDs
            for pin in self.gpio_pins.values():
                self._stop_blink(pin)
                self._set_led(pin, False)
            self.logger.info("Cleared all LEDs")
    
    def cleanup(self):
        """Cleanup GPIO resources."""
        # Stop all blinking
        for pin in list(self.gpio_pins.values()):
            self._stop_blink(pin)
        
        # Turn off all LEDs
        self.clear_alarm()
        
        # Cleanup GPIO
        if self.gpio_available:
            try:
                GPIO.cleanup()
                self.logger.info("GPIO cleanup completed")
            except Exception as e:
                self.logger.error(f"Error during GPIO cleanup: {e}")


class UPSGPIOController:
    """Main controller that receives SNMP traps and controls GPIO LEDs."""
    
    def __init__(
        self,
        gpio_pins: Dict[str, int],
        port: int = 162,
        allowed_ips: Optional[List[str]] = None,
        log_file: str = 'ups_gpio.log',
        blink_enabled: bool = True,
        blink_interval: float = 0.5,
        active_high: bool = True,
        auto_clear_delay: Optional[float] = None
    ):
        """
        Initialize UPS GPIO Controller.
        
        Args:
            gpio_pins: Dictionary mapping alarm types to GPIO pin numbers
                      Example: {'critical': 18, 'warning': 19}
            port: UDP port to listen on (default 162)
            allowed_ips: List of allowed source IP addresses (None = accept all)
            log_file: Path to log file
            blink_enabled: Enable blinking for alarms
            blink_interval: Blink interval in seconds
            active_high: True if LED is active high
            auto_clear_delay: Auto-clear LED after delay in seconds (None = manual clear)
        """
        self.port = port
        self.allowed_ips = allowed_ips if allowed_ips else []
        self.log_file = Path(log_file)
        self.is_windows = platform.system() == 'Windows'
        self.auto_clear_delay = auto_clear_delay
        
        # Setup logging
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        # Use DEBUG level to see all trap processing
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, mode='a'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        # Set console handler to INFO to reduce noise, but keep DEBUG in file
        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                handler.setLevel(logging.INFO)
        
        # Initialize GPIO LED controller
        self.led_controller = GPIOLEDController(
            gpio_pins=gpio_pins,
            blink_enabled=blink_enabled,
            blink_interval=blink_interval,
            active_high=active_high
        )
        
        # SNMP engine
        self.snmp_engine = None
        self._last_src_addr = {}
        
        # Track active alarms
        self.active_alarms = {}  # trap_name -> timestamp
        
        self.logger.info("UPS GPIO Controller initialized")
        self.logger.info(f"GPIO pins configured: {gpio_pins}")
        self.logger.info(f"Blink enabled: {blink_enabled}")
        if self.auto_clear_delay:
            self.logger.info(f"Auto-clear delay: {self.auto_clear_delay} seconds")
    
    def _get_source_address(self, snmpEngine, stateReference):
        """Extract source address from SNMP trap (simplified version)."""
        # Try to get from cached source addresses
        import time
        current_time = time.time()
        if hasattr(self, '_last_src_addr') and self._last_src_addr:
            recent_addrs = {k: v for k, v in self._last_src_addr.items() if current_time - k < 1.0}
            if recent_addrs:
                most_recent_time = max(recent_addrs.keys())
                return recent_addrs[most_recent_time]
        return None
    
    def cbFun(self, snmpEngine, stateReference, contextName, varBinds, cbCtx, *args):
        """Callback function to process received SNMP traps."""
        # Log that callback was triggered
        self.logger.info("=== SNMP Trap Callback Triggered ===")
        self.logger.debug(f"varBinds count: {len(varBinds) if varBinds else 0}")
        self.logger.debug(f"cbCtx type: {type(cbCtx).__name__ if cbCtx else 'None'}")
        
        try:
            # Extract variable bindings
            actual_varBinds = varBinds
            if (not varBinds or len(varBinds) == 0) and cbCtx:
                if isinstance(cbCtx, (list, tuple)) and len(cbCtx) > 0:
                    if isinstance(cbCtx[0], (list, tuple)) and len(cbCtx[0]) == 2:
                        actual_varBinds = cbCtx
                        self.logger.debug("Extracted varBinds from cbCtx")
            
            if not actual_varBinds:
                self.logger.warning("No variable bindings found in trap")
            
            # Get source address
            source_address = "unknown"
            transportAddress = self._get_source_address(snmpEngine, stateReference)
            if transportAddress:
                if isinstance(transportAddress, (tuple, list)) and len(transportAddress) >= 2:
                    source_ip = str(transportAddress[0])
                    source_address = f"{source_ip}:{transportAddress[1]}"
            
            # Filter by allowed IP addresses
            if self.allowed_ips:
                source_ip = source_address.split(':')[0] if ':' in source_address else None
                if source_ip and source_ip not in self.allowed_ips:
                    self.logger.warning(f"Rejected trap from unauthorized source: {source_address}")
                    return
            
            # Process trap
            trap_oid = None
            trap_name = None
            trap_vars = {}
            snmp_trap_oid = None  # Standard SNMP trap OID (1.3.6.1.6.3.1.1.4.1.0)
            
            if actual_varBinds:
                self.logger.debug(f"Processing {len(actual_varBinds)} variable bindings")
                for binding in actual_varBinds:
                    if isinstance(binding, (list, tuple)) and len(binding) >= 2:
                        oid, val = binding[0], binding[1]
                        oid_str = str(oid)
                        val_str = self._format_snmp_value(val)
                        
                        # Check for standard SNMP trap OID (snmpTrapOID)
                        if oid_str == '1.3.6.1.6.3.1.1.4.1.0':
                            snmp_trap_oid = val_str
                            self.logger.debug(f"Found snmpTrapOID: {val_str}")
                        
                        # Check if this is a known UPS trap OID
                        if oid_str in UPS_OIDS:
                            trap_oid = oid_str
                            trap_name = UPS_OIDS[oid_str]
                            trap_vars[trap_name] = val_str
                            self.logger.debug(f"Matched known UPS OID: {trap_name}")
                        
                        # Store all variables for logging
                        trap_vars[oid_str] = val_str
                
                # Log all received OIDs for debugging
                if len(trap_vars) > 0:
                    self.logger.debug(f"All trap variables: {list(trap_vars.keys())[:5]}...")  # Log first 5
            
            # Determine if this is an alarm (even if not recognized)
            is_alarm = False
            severity = 'info'
            
            if trap_name:
                # Known trap - use mapped severity
                severity = ALARM_SEVERITY.get(trap_name, 'info')
                is_alarm = True
                self.logger.info(f"Received known trap: {trap_name} (severity: {severity}) from {source_address}")
            elif snmp_trap_oid:
                # Unknown trap but has snmpTrapOID - treat as warning
                is_alarm = True
                severity = 'warning'
                trap_name = f"UnknownTrap_{snmp_trap_oid.replace('.', '_')}"
                self.logger.warning(f"Received unknown trap OID: {snmp_trap_oid} from {source_address}")
                self.logger.info(f"Triggering LED for unknown trap (treating as warning)")
            elif len(trap_vars) > 0:
                # Trap received but no recognized OID - still trigger LED
                is_alarm = True
                severity = 'warning'
                trap_name = "UnknownTrap"
                self.logger.warning(f"Received trap with unrecognized format from {source_address}")
                self.logger.info(f"Trap variables: {list(trap_vars.keys())[:3]}...")  # Show first 3 OIDs
                self.logger.info(f"Triggering LED for unrecognized trap (treating as warning)")
            else:
                # No trap data - just log
                self.logger.warning(f"Received trap with no variable bindings from {source_address}")
            
            # Process alarm - trigger LED for any trap
            if is_alarm:
                # Trigger LED
                self.led_controller.trigger_alarm(trap_name, severity)
                
                # Track active alarm
                alarm_key = trap_name if trap_name else f"trap_{time.time()}"
                self.active_alarms[alarm_key] = time.time()
                
                # Auto-clear if configured
                if self.auto_clear_delay:
                    def auto_clear():
                        time.sleep(self.auto_clear_delay)
                        if alarm_key in self.active_alarms:
                            self.led_controller.clear_alarm(severity)
                            del self.active_alarms[alarm_key]
                            self.logger.info(f"Auto-cleared LED for {alarm_key}")
                    
                    threading.Thread(target=auto_clear, daemon=True).start()
                
                # Log trap details
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.logger.info(
                    f"Trap processed - Time: {timestamp}, "
                    f"Source: {source_address}, "
                    f"Trap: {trap_name or 'Unknown'}, "
                    f"Severity: {severity}, "
                    f"GPIO triggered"
                )
            else:
                # Log that we received something but couldn't process it
                self.logger.debug(f"Received SNMP message from {source_address} but couldn't identify as trap")
        
        except Exception as e:
            self.logger.error(f"Error processing trap: {e}", exc_info=True)
            self.logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _format_snmp_value(self, value):
        """Format SNMP value for logging."""
        if isinstance(value, rfc1902.Integer):
            return int(value)
        elif isinstance(value, rfc1902.OctetString):
            return value.prettyPrint()
        elif isinstance(value, rfc1902.ObjectIdentifier):
            return str(value)
        else:
            return str(value)
    
    def start(self):
        """Start the SNMP trap receiver and GPIO controller."""
        try:
            platform_name = "Windows" if self.is_windows else "Linux"
            self.logger.info(f"Starting UPS GPIO Controller on {platform_name}")
            self.logger.info(f"Listening on port: {self.port}")
            self.logger.info(f"Logging to: {self.log_file.absolute()}")
            if self.allowed_ips:
                self.logger.info(f"Filtering: Only accepting traps from: {', '.join(self.allowed_ips)}")
            else:
                self.logger.info("Accepting traps from ALL IP addresses")
            self.logger.info("Waiting for SNMP traps...")
            self.logger.info("Press Ctrl+C to stop")
            
            # Create SNMP engine
            self.snmp_engine = engine.SnmpEngine()
            
            # Configure transport based on available transport type
            transport = udp.UdpTransport().open_server_mode(('0.0.0.0', self.port))
            self._transport = transport
            
            # Capture source addresses
            import time
            if not hasattr(self, '_last_src_addr'):
                self._last_src_addr = {}
            
            if hasattr(transport, 'datagram_received'):
                original_datagram_received = transport.datagram_received
                
                def datagram_received_wrapper(data, addr):
                    if addr:
                        timestamp = time.time()
                        self._last_src_addr[timestamp] = addr
                    return original_datagram_received(data, addr)
                
                transport.datagram_received = datagram_received_wrapper
            
            config.add_transport(
                self.snmp_engine,
                udp.DOMAIN_NAME + (1,),
                transport
            )
            
            # Configure SNMPv1/v2c
            try:
                config.add_v1_system(self.snmp_engine, 'my-area', 'public')
            except AttributeError:
                try:
                    config.addV1System(self.snmp_engine, 'my-area', 'public')
                except AttributeError:
                    pass
            
            try:
                config.add_v2c_system(self.snmp_engine, 'my-area', 'public')
            except AttributeError:
                try:
                    config.addV2cSystem(self.snmp_engine, 'my-area', 'public')
                except AttributeError:
                    pass
            
            # Register callback
            ntfrcv.NotificationReceiver(self.snmp_engine, self.cbFun)
            
            # Start engine - handle different transport types
            self.snmp_engine.transport_dispatcher.job_started(1)
            
            # For twisted transport, we need to start the reactor
            if 'USE_TWISTED' in globals() and USE_TWISTED:
                try:
                    from twisted.internet import reactor
                    self.logger.info("Using Twisted reactor for SNMP transport")
                    reactor.run()
                except ImportError:
                    self.logger.error("Twisted transport requires twisted package. Install with: pip3 install twisted")
                    sys.exit(1)
            else:
                # For asyncio or socketpair transport
                self.snmp_engine.transport_dispatcher.run_dispatcher()
        
        except PermissionError:
            if self.is_windows:
                self.logger.error(
                    f"Permission denied: Port {self.port} requires Administrator privileges. "
                    f"Please run as Administrator or use a port >= 1024"
                )
            else:
                self.logger.error(
                    f"Permission denied: Port {self.port} requires root privileges. "
                    f"Please run with sudo or use a port >= 1024"
                )
            sys.exit(1)
        except OSError as e:
            error_code = getattr(e, 'winerror', getattr(e, 'errno', None))
            if error_code == 10048 or error_code == 98:
                self.logger.error(f"Port {self.port} is already in use.")
            else:
                self.logger.error(f"OS Error: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}", exc_info=True)
            sys.exit(1)
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources."""
        if self.snmp_engine:
            try:
                self.snmp_engine.transport_dispatcher.close_dispatcher()
            except Exception as e:
                self.logger.debug(f"Error closing dispatcher: {e}")
        
        self.led_controller.cleanup()
        self.logger.info("UPS GPIO Controller stopped")


def load_gpio_config(config_file: str = 'gpio_config.json') -> Optional[Dict[str, Any]]:
    """Load GPIO configuration from JSON file."""
    config_path = Path(config_file)
    if not config_path.exists():
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except (json.JSONDecodeError, IOError) as e:
        logging.warning(f"Failed to load GPIO config from {config_file}: {e}")
        return None


def main():
    """Main entry point."""
    import argparse
    
    is_windows = platform.system() == 'Windows'
    platform_desc = "Windows/Linux" if is_windows else "Linux (Raspberry Pi 4)"
    
    parser = argparse.ArgumentParser(
        description=f'UPS GPIO LED Controller - Cross-platform ({platform_desc})',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with default GPIO pins (18 for critical, 19 for warning)
  sudo python3 ups_gpio_led_controller.py --critical-pin 18 --warning-pin 19
  
  # Custom port and GPIO pins
  sudo python3 ups_gpio_led_controller.py --port 162 --critical-pin 18 --warning-pin 19 --info-pin 20
  
  # Disable blinking (solid LED)
  sudo python3 ups_gpio_led_controller.py --critical-pin 18 --no-blink
  
  # Auto-clear LED after 60 seconds
  sudo python3 ups_gpio_led_controller.py --critical-pin 18 --auto-clear 60
  
  # Accept traps only from specific UPS IP
  sudo python3 ups_gpio_led_controller.py --critical-pin 18 --ups-ip 192.168.111.137
  
  # Use configuration file
  sudo python3 ups_gpio_led_controller.py --config gpio_config.json

GPIO Pin Configuration:
  - critical: GPIO pin for critical alarms (e.g., general fault, charger failed)
  - warning: GPIO pin for warning alarms (e.g., on battery, battery low)
  - info: GPIO pin for info alarms (e.g., test completed)

Common Raspberry Pi GPIO Pins:
  - GPIO 18 (Physical pin 12) - PWM capable
  - GPIO 19 (Physical pin 35) - PWM capable
  - GPIO 20 (Physical pin 38)
  - GPIO 21 (Physical pin 40)

Note: Use BCM pin numbering (not physical pin numbers).
        """
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=162,
        help='UDP port to listen on (default: 162, requires root)'
    )
    
    parser.add_argument(
        '--critical-pin', '-c',
        type=int,
        default=18,
        help='GPIO pin for critical alarms (default: 18)'
    )
    
    parser.add_argument(
        '--warning-pin', '-w',
        type=int,
        default=19,
        help='GPIO pin for warning alarms (default: 19)'
    )
    
    parser.add_argument(
        '--info-pin', '-i',
        type=int,
        default=None,
        help='GPIO pin for info alarms (optional)'
    )
    
    parser.add_argument(
        '--ups-ip', '-u',
        type=str,
        default=None,
        help='UPS IP address to accept traps from (default: accept all). Can specify multiple IPs separated by commas.'
    )
    
    parser.add_argument(
        '--log-file', '-l',
        type=str,
        default='ups_gpio.log',
        help='Path to log file (default: ups_gpio.log)'
    )
    
    parser.add_argument(
        '--no-blink',
        action='store_true',
        help='Disable blinking (solid LED)'
    )
    
    parser.add_argument(
        '--blink-interval',
        type=float,
        default=0.5,
        help='Blink interval in seconds (default: 0.5)'
    )
    
    parser.add_argument(
        '--active-low',
        action='store_true',
        help='Use active-low logic (LED turns on with LOW signal)'
    )
    
    parser.add_argument(
        '--auto-clear',
        type=float,
        default=None,
        help='Auto-clear LED after delay in seconds (default: manual clear)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='gpio_config.json',
        help='Path to GPIO configuration file (default: gpio_config.json)'
    )
    
    args = parser.parse_args()
    
    # Load GPIO configuration from file
    gpio_config = load_gpio_config(args.config)
    
    # Build GPIO pins dictionary
    gpio_pins = {}
    
    if gpio_config and 'gpio_pins' in gpio_config:
        # Load from config file
        gpio_pins = gpio_config['gpio_pins']
    else:
        # Use command-line arguments
        if args.critical_pin:
            gpio_pins['critical'] = args.critical_pin
        if args.warning_pin:
            gpio_pins['warning'] = args.warning_pin
        if args.info_pin:
            gpio_pins['info'] = args.info_pin
    
    if not gpio_pins:
        parser.error("At least one GPIO pin must be specified (--critical-pin, --warning-pin, or --info-pin)")
    
    # Parse allowed IP addresses
    allowed_ips = None
    if args.ups_ip:
        allowed_ips = [ip.strip() for ip in args.ups_ip.split(',')]
    
    # Get other settings from config file or command line
    blink_enabled = not args.no_blink
    if gpio_config and 'blink_enabled' in gpio_config:
        blink_enabled = gpio_config['blink_enabled'] and not args.no_blink
    
    blink_interval = args.blink_interval
    if gpio_config and 'blink_interval' in gpio_config:
        blink_interval = gpio_config['blink_interval']
    
    active_high = not args.active_low
    if gpio_config and 'active_high' in gpio_config:
        active_high = gpio_config['active_high'] and not args.active_low
    
    auto_clear_delay = args.auto_clear
    if gpio_config and 'auto_clear_delay' in gpio_config:
        auto_clear_delay = gpio_config['auto_clear_delay'] or args.auto_clear
    
    # Create and start controller
    controller = UPSGPIOController(
        gpio_pins=gpio_pins,
        port=args.port,
        allowed_ips=allowed_ips,
        log_file=args.log_file,
        blink_enabled=blink_enabled,
        blink_interval=blink_interval,
        active_high=active_high,
        auto_clear_delay=auto_clear_delay
    )
    
    controller.start()


if __name__ == '__main__':
    main()

