#!/usr/bin/env python3
"""
UPS/ATS SNMP Trap Receiver v3
Receives SNMP traps from UPS/ATS devices and logs them to a file.
Cross-platform: Windows and Linux (Raspberry Pi 4 / Linux-x64).

UPS/ATS GPIO LED Controller
Receives SNMP traps from UPS/ATS devices and controls GPIO pins on Raspberry Pi to trigger LED devices.
Cross-platform: Works on Raspberry Pi 4 (Linux/Debian) with GPIO support, gracefully handles Windows (for development).

Features:
- Receives SNMP traps from UPS/ATS devices (using SNMPv2c protocol)
- Detects alarm conditions
- Controls GPIO pins to trigger LED devices
- Supports multiple GPIO pins for different alarm types
- Configurable LED behaviors (on/off, blinking patterns)
- Alarm definitions are from the ATS_Stork_V1_05 - Borri STS32A.MIB file

ROOT CAUSE AND PROBLEM:
-----------------------
The MIB file (ATS_Stork_V1_05 - Borri STS32A.MIB) defines atsAgent(3), which results in
trap OID paths like: 1.3.6.1.4.1.37662.1.2.3.1.2.x
However, the actual device firmware uses atsAgent(2), which may result in trap OID paths:
1.3.6.1.4.1.37662.1.2.2.1.2.x

This mismatch was discovered when:
1. Device sysObjectID (1.3.6.1.2.1.1.2.0) returned: 1.3.6.1.4.1.37662.1.2.2.1
2. Status queries using MIB-defined OIDs (with atsAgent=3) failed
3. Device sends traps with OIDs in format: 1.3.6.1.4.1.37662.1.2.2.1.2.0.X

SOLUTION:
---------
The trap receiver includes OID normalization logic that converts atsAgent(2) trap OIDs
to atsAgent(3) for lookup in TrapIDTable.py. This allows the receiver to recognize
traps regardless of which atsAgent version the device firmware uses.

TrapIDTable.py uses MIB-defined trap OIDs (atsAgent=3) for consistency with the MIB
file, but the receiver handles both patterns transparently.
"""

import asyncio
import json
import logging
import os
import platform
import signal
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import ntfrcv
from pysnmp.proto import rfc1902

# Import trap ID tables from TrapIDTable module
from TrapIDTable import (
    UPS_OIDS,
    ALARM_DESCRIPTIONS,
    BATTERY_OID_PATTERNS,
    ALARM_SEVERITY,
    ALARM_RESUMPTION_MAP,
    ALARM_EVENT_TYPE,
    RESUMPTION_TO_ALARM_MAP,
    ALARM_TO_LED_MAP,  # Alarm to LED mapping (based on AlarmMap.py)
    RESUMPTION_TO_LED_MAP  # Resumption to LED mapping (disable red, enable green)
)

# Import EmailSender for email notifications
try:
    from email_sender import EmailSender
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False

# Import GPIO LED Controller for Raspberry Pi
try:
    from ups_gpio_led_controller import GPIOLEDController
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    GPIOLEDController = None

# Import RPi.GPIO for button handling
try:
    import RPi.GPIO as GPIO
    RPI_GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    RPI_GPIO_AVAILABLE = False
    GPIO = None

# Import Panel LED Controller for AlarmMap-based LED control
try:
    from panel_led_controller import PanelLEDController
    PANEL_LED_CONTROLLER_AVAILABLE = True
except ImportError:
    PANEL_LED_CONTROLLER_AVAILABLE = False
    PanelLEDController = None

# Import GetUPSStatus for periodic status checking
try:
    from GetUPSStatus import GetUPSStatus
    GET_UPS_STATUS_AVAILABLE = True
except ImportError:
    GET_UPS_STATUS_AVAILABLE = False
    GetUPSStatus = None


class ThrottledLogFilter(logging.Filter):
    """Filter to throttle specific log messages (e.g., show once per minute)."""
    
    def __init__(self, pattern: str, throttle_seconds: int = 60):
        """
        Initialize throttled log filter.
        
        Args:
            pattern: Message pattern to match (case-insensitive)
            throttle_seconds: Minimum seconds between allowing the same message (default: 60)
        """
        super().__init__()
        self.pattern = pattern.lower()
        self.throttle_seconds = throttle_seconds
        self.last_logged = {}  # Track last time each message was logged
    
    def filter(self, record):
        """Filter log records - return False to suppress, True to allow."""
        message = record.getMessage().lower()
        
        # Check if this message matches our pattern
        if self.pattern in message:
            current_time = time.time()
            message_key = message  # Use full message as key
            
            # Check if we've logged this message recently
            if message_key in self.last_logged:
                time_since_last = current_time - self.last_logged[message_key]
                if time_since_last < self.throttle_seconds:
                    # Suppress this message (don't log it)
                    return False
            
            # Update last logged time
            self.last_logged[message_key] = current_time
        
        # Allow all other messages
        return True


class SoundController:
    """Controls audio alerts for UPS alarm conditions on Raspberry Pi."""
    
    def __init__(
        self,
        sound_enabled: bool = True,
        sound_files: Optional[Dict[str, str]] = None,
        use_beep: bool = True,
        beep_duration: float = 0.5,
        beep_frequency: int = 1000,
        volume: int = 50
    ):
        """
        Initialize Sound Controller.
        
        Args:
            sound_enabled: Enable sound alerts (default: True)
            sound_files: Dictionary mapping severity to sound file paths
                       Example: {'critical': '/path/to/critical.wav', 'warning': '/path/to/warning.wav'}
            use_beep: Use system beep if sound files not available (default: True)
            beep_duration: Beep duration in seconds (default: 0.5)
            beep_frequency: Beep frequency in Hz (default: 1000)
            volume: Volume level 0-100 (default: 50)
        """
        self.sound_enabled = sound_enabled
        self.sound_files = sound_files if sound_files else {}
        self.use_beep = use_beep
        self.beep_duration = beep_duration
        self.beep_frequency = beep_frequency
        self.volume = max(0, min(100, volume))  # Clamp to 0-100
        self.is_windows = platform.system() == 'Windows'
        self.is_raspberry_pi = self._detect_raspberry_pi()
        
        # Detect available audio players
        self.audio_player = self._detect_audio_player()
        
        # Track active sounds to prevent overlapping
        self.active_sounds = {}
        self.sound_lock = threading.Lock()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        if not self.sound_enabled:
            self.logger.info("Sound alerts disabled")
        elif self.audio_player:
            self.logger.info(f"Sound controller initialized - using {self.audio_player}")
        else:
            self.logger.warning("No audio player detected - sound alerts will be simulated")
    
    def _detect_raspberry_pi(self) -> bool:
        """Detect if running on Raspberry Pi."""
        if self.is_windows:
            return False
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                return 'Raspberry Pi' in cpuinfo or 'BCM' in cpuinfo
        except:
            return False
    
    def _detect_audio_player(self) -> Optional[str]:
        """Detect available audio player on the system."""
        if self.is_windows:
            return None  # Windows support can be added later
        
        # Try aplay (ALSA - most common on Raspberry Pi)
        if self._check_command('aplay'):
            return 'aplay'
        
        # Try paplay (PulseAudio)
        if self._check_command('paplay'):
            return 'paplay'
        
        # Try omxplayer (older Raspberry Pi models)
        if self._check_command('omxplayer'):
            return 'omxplayer'
        
        # Try speaker-test (for beep)
        if self._check_command('speaker-test'):
            return 'speaker-test'
        
        return None
    
    def _check_command(self, command: str) -> bool:
        """Check if a command is available."""
        try:
            result = subprocess.run(
                ['which', command],
                capture_output=True,
                timeout=1
            )
            return result.returncode == 0
        except:
            return False
    
    def _play_sound_file(self, sound_file: str) -> bool:
        """Play a sound file using the detected audio player."""
        if not self.audio_player:
            return False
        
        if not os.path.exists(sound_file):
            self.logger.warning(f"Sound file not found: {sound_file}")
            return False
        
        try:
            if self.audio_player == 'aplay':
                # aplay with volume control
                cmd = ['aplay', '-q', sound_file]
            elif self.audio_player == 'paplay':
                # paplay with volume control
                volume_arg = f'{self.volume}%'
                cmd = ['paplay', '--volume', volume_arg, sound_file]
            elif self.audio_player == 'omxplayer':
                # omxplayer (no volume control in basic usage)
                cmd = ['omxplayer', '-o', 'local', sound_file]
            else:
                return False
            
            # Play sound in background (non-blocking)
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Store process to track it
            with self.sound_lock:
                self.active_sounds[process.pid] = process
            
            # Clean up after sound finishes
            def cleanup():
                process.wait()
                with self.sound_lock:
                    if process.pid in self.active_sounds:
                        del self.active_sounds[process.pid]
            
            threading.Thread(target=cleanup, daemon=True).start()
            return True
            
        except Exception as e:
            self.logger.error(f"Error playing sound file {sound_file}: {e}")
            return False
    
    def _play_beep(self, count: int = 1, duration: float = None) -> bool:
        """Play system beep."""
        if not self.use_beep:
            return False
        
        duration = duration or self.beep_duration
        
        try:
            if self.is_windows:
                # Windows beep
                import winsound
                for _ in range(count):
                    winsound.Beep(self.beep_frequency, int(duration * 1000))
                return True
            else:
                # Linux beep using speaker-test or beep command
                if self._check_command('beep'):
                    # Use beep command if available
                    cmd = ['beep', '-f', str(self.beep_frequency), '-l', str(int(duration * 1000))]
                    for _ in range(count - 1):
                        cmd.extend(['-n', '-f', str(self.beep_frequency), '-l', str(int(duration * 1000))])
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True
                elif self.audio_player == 'speaker-test':
                    # Use speaker-test for beep
                    for _ in range(count):
                        cmd = [
                            'speaker-test', '-t', 'sine', '-f', str(self.beep_frequency),
                            '-l', '1', '-s', '1', '-c', '1'
                        ]
                        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        if count > 1:
                            time.sleep(duration)
                    return True
                else:
                    # Fallback: print bell character (may not work on all systems)
                    for _ in range(count):
                        print('\a', end='', flush=True)
                        if count > 1:
                            time.sleep(duration)
                    return True
        except Exception as e:
            self.logger.error(f"Error playing beep: {e}")
            return False
    
    def trigger_alarm(self, alarm_type: str, severity: str = None):
        """
        Trigger sound alert for an alarm.
        
        Args:
            alarm_type: Alarm type name
            severity: Severity level ('critical', 'warning', 'info')
        """
        if not self.sound_enabled:
            return
        
        # Determine severity
        severity_key = severity if severity else 'warning'
        
        # Try to play sound file first
        sound_file = self.sound_files.get(severity_key)
        if sound_file and self._play_sound_file(sound_file):
            self.logger.info(f"Playing sound file for {alarm_type} ({severity_key}): {sound_file}")
            return
        
        # Fallback to beep
        if self.use_beep:
            # Different beep patterns for different severities
            if severity_key == 'critical':
                # Critical: 3 beeps
                self._play_beep(count=3, duration=self.beep_duration)
                self.logger.info(f"Playing critical beep (3x) for {alarm_type}")
            elif severity_key == 'warning':
                # Warning: 2 beeps
                self._play_beep(count=2, duration=self.beep_duration)
                self.logger.info(f"Playing warning beep (2x) for {alarm_type}")
            else:
                # Info: 1 beep
                self._play_beep(count=1, duration=self.beep_duration)
                self.logger.info(f"Playing info beep (1x) for {alarm_type}")
        else:
            if self.is_windows:
                self.logger.info(f"[SIMULATED] Sound alert for {alarm_type} ({severity_key})")
            else:
                self.logger.warning(f"No sound method available for {alarm_type} ({severity_key})")
    
    def clear_alarm(self, alarm_type: str = None):
        """
        Stop sound alert (if playing continuously).
        
        Args:
            alarm_type: Alarm type to clear (optional)
        """
        # For now, we don't need to stop sounds as they play once
        # But we can stop any active sound processes if needed
        with self.sound_lock:
            for pid, process in list(self.active_sounds.items()):
                try:
                    if process.poll() is None:  # Still running
                        process.terminate()
                        process.wait(timeout=1)
                except:
                    pass
                del self.active_sounds[pid]
        
        if alarm_type:
            self.logger.debug(f"Cleared sound for {alarm_type}")
        else:
            self.logger.debug("Cleared all sounds")

# Trap ID tables are now imported from TrapIDTable.py
# See TrapIDTable.py for UPS_OIDS, ALARM_DESCRIPTIONS, BATTERY_OID_PATTERNS,
# ALARM_SEVERITY, ALARM_RESUMPTION_MAP, ALARM_EVENT_TYPE, and RESUMPTION_TO_ALARM_MAP


def get_log_filename(base_name: str = 'ups_traps', extension: str = '.log') -> str:
    """
    Generate a log filename with the current date.
    
    Args:
        base_name: Base name for the log file (default: 'ups_traps')
        extension: File extension (default: '.log')
    
    Returns:
        Filename in format: base_nameYYYYMMDD.extension
        Example: 'ups_traps20251128.log'
    """
    date_str = datetime.now().strftime('%Y%m%d')
    return f"{base_name}{date_str}{extension}"


class UPSTrapReceiver:
    """SNMP Trap Receiver for UPS/ATS devices (using SNMPv2c protocol).
    
    Supports ATS_Stork_V1_05 - Borri STS32A.MIB trap definitions.
    
    ROOT CAUSE AND PROBLEM:
    -----------------------
    The MIB file (ATS_Stork_V1_05 - Borri STS32A.MIB) defines atsAgent(3), which
    results in trap OID paths like: 1.3.6.1.4.1.37662.1.2.3.1.2.x
    However, the actual device firmware uses atsAgent(2), which may result in
    trap OID paths: 1.3.6.1.4.1.37662.1.2.2.1.2.x
    
    This mismatch was discovered when:
    1. Device sysObjectID (1.3.6.1.2.1.1.2.0) returned: 1.3.6.1.4.1.37662.1.2.2.1
    2. Status queries using MIB-defined OIDs (with atsAgent=3) failed
    3. Device sends traps with OIDs in format: 1.3.6.1.4.1.37662.1.2.2.1.2.0.X
    
    SOLUTION:
    ---------
    The trap receiver normalizes trap OIDs by converting atsAgent(2) to atsAgent(3)
    for lookup in TrapIDTable.py, which uses MIB-defined OIDs (atsAgent=3).
    This allows the receiver to recognize traps regardless of which atsAgent
    version the device firmware uses.
    
    Note: TrapIDTable.py uses MIB-defined trap OIDs (atsAgent=3) for consistency
    with the MIB file, but the receiver handles both patterns.
    """
    
    def __init__(
        self,
        log_file: str = None,  # Will default to dated filename if None
        port: int = 162,
        allowed_ips: Optional[list] = None,
        email_recipients: Optional[List[str]] = None,
        smtp_server: Optional[str] = None,
        smtp_port: int = 25,
        smtp_use_tls: bool = True,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        gpio_pins: Optional[Dict[str, int]] = None,
        gpio_blink_enabled: bool = True,
        gpio_blink_interval: float = 0.5,
        gpio_active_high: bool = True,
        sound_enabled: bool = True,
        sound_files: Optional[Dict[str, str]] = None,
        sound_use_beep: bool = True,
        sound_beep_duration: float = 0.5,
        sound_beep_frequency: int = 1000,
        sound_volume: int = 50,
        pid_file: Optional[str] = None
    ):
        """
        Initialize the UPS/ATS SNMP Trap Receiver (SNMPv2c protocol).
        
        Args:
            log_file: Path to the log file
            port: UDP port to listen on (default 162, requires admin/root privileges)
            allowed_ips: List of allowed source IP addresses (None = accept all)
            email_recipients: List of email addresses to send notifications to
            smtp_server: SMTP server hostname or IP
            smtp_port: SMTP server port (default 25)
            smtp_use_tls: Use TLS encryption (default True)
            smtp_username: SMTP username (optional)
            smtp_password: SMTP password (optional)
            from_email: Sender email address
            from_name: Sender name
            gpio_pins: Dictionary mapping alarm types to GPIO pin numbers (e.g., {'critical': 17, 'warning': 17})
            gpio_blink_enabled: Enable blinking for alarms (default: True)
            gpio_blink_interval: Blink interval in seconds (default: 0.5)
            gpio_active_high: True if LED is active high (default: True)
            sound_enabled: Enable sound alerts (default: True)
            sound_files: Dictionary mapping severity to sound file paths (e.g., {'critical': '/path/to/critical.wav'})
            sound_use_beep: Use system beep if sound files not available (default: True)
            sound_beep_duration: Beep duration in seconds (default: 0.5)
            sound_beep_frequency: Beep frequency in Hz (default: 1000)
            sound_volume: Volume level 0-100 (default: 50)
        """
        # Set default log file with date if not provided
        if log_file is None:
            log_file = f"logs/{get_log_filename()}"
        self.log_file = Path(log_file)
        
        # Set up email and SMS log file paths (same directory as main log file)
        # Resolve the log file path to get the correct directory
        if not self.log_file.is_absolute():
            self.log_file = Path(__file__).parent / self.log_file
        log_dir = self.log_file.parent
        self.email_log_file = log_dir / get_log_filename('ups_email', '.log')
        self.sms_log_file = log_dir / get_log_filename('ups_sms', '.log')
        
        self.port = port
        self.allowed_ips = allowed_ips if allowed_ips else []
        self.is_windows = platform.system() == 'Windows'
        self.pid_file = Path(pid_file) if pid_file else None
        self._shutdown_requested = False
        self.setup_logging()
        self.snmp_engine = None
        # Dictionary to store source addresses by stateReference
        self._source_address_cache = {}
        
        # Setup signal handlers for graceful shutdown (Linux only)
        if not self.is_windows:
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
        
        # Load configuration from config.py first (for enabled flags and settings)
        self.ups_name = 'UPS Device'  # Default, will be loaded from config.py (legacy)
        self.ups_location = 'Unknown Location'  # Default, will be loaded from config.py (legacy)
        self.ups_devices = {}  # Dictionary mapping IP to UPS info (name, location)
        
        self.email_enabled = True  # Default to enabled, will be loaded from config.py
        self.email_recipients = []
        self.smtp_server = None
        self.smtp_port = 25
        self.smtp_use_tls = True
        self.smtp_username = None
        self.smtp_password = None
        self.from_email = None
        self.from_name = None
        
        self.sms_enabled = False
        self.sms_api_url = None
        self.sms_username = None
        self.sms_password = None
        self.sms_recipients = []  # Fallback simple list
        self.sms_schedule = None  # Time-based schedule (list of time ranges)
        self.sms_type = 1
        self.sms_return_mode = 1
        
        self.alarm_led_enabled = True  # Default to enabled, will be loaded from config.py
        self.buzzer_muted = False  # Default to not muted, will be loaded from config.py
        
        try:
            import importlib.util
            config_path = Path(__file__).parent / 'config.py'
            if config_path.exists():
                spec = importlib.util.spec_from_file_location("ups_config", config_path)
                ups_config = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(ups_config)
                
                # Load UPS information from config.py (legacy - for backward compatibility)
                if hasattr(ups_config, 'UPS_NAME'):
                    self.ups_name = ups_config.UPS_NAME
                if hasattr(ups_config, 'UPS_LOCATION'):
                    self.ups_location = ups_config.UPS_LOCATION
                
                # Load UPS_DEVICES dictionary (multiple UPS support)
                if hasattr(ups_config, 'UPS_DEVICES'):
                    self.ups_devices = ups_config.UPS_DEVICES if isinstance(ups_config.UPS_DEVICES, dict) else {}
                else:
                    self.ups_devices = {}
                
                # Automatically add all IPs from UPS_DEVICES to allowed_ips
                if self.ups_devices:
                    ups_device_ips = list(self.ups_devices.keys())
                    # Add to allowed_ips if not already present
                    for ip in ups_device_ips:
                        if ip not in self.allowed_ips:
                            self.allowed_ips.append(ip)
                            self.logger.info(f"Auto-added UPS device IP to allowed list: {ip}")
                    if ups_device_ips:
                        self.logger.info(f"Allowed IPs now include {len(ups_device_ips)} UPS device(s): {', '.join(ups_device_ips)}")
                
                # Load EMAIL_ENABLED from config.py
                if hasattr(ups_config, 'EMAIL_ENABLED'):
                    self.email_enabled = ups_config.EMAIL_ENABLED
                
                # Load email configuration from config.py
                if hasattr(ups_config, 'EMAIL_RECIPIENTS'):
                    self.email_recipients = ups_config.EMAIL_RECIPIENTS if isinstance(ups_config.EMAIL_RECIPIENTS, list) else [ups_config.EMAIL_RECIPIENTS]
                if hasattr(ups_config, 'SMTP_SERVER'):
                    self.smtp_server = ups_config.SMTP_SERVER
                if hasattr(ups_config, 'SMTP_PORT'):
                    self.smtp_port = ups_config.SMTP_PORT
                if hasattr(ups_config, 'SMTP_USE_TLS'):
                    self.smtp_use_tls = ups_config.SMTP_USE_TLS
                if hasattr(ups_config, 'SMTP_USERNAME'):
                    self.smtp_username = ups_config.SMTP_USERNAME
                if hasattr(ups_config, 'SMTP_PASSWORD'):
                    self.smtp_password = ups_config.SMTP_PASSWORD
                if hasattr(ups_config, 'FROM_EMAIL'):
                    self.from_email = ups_config.FROM_EMAIL
                if hasattr(ups_config, 'FROM_NAME'):
                    self.from_name = ups_config.FROM_NAME
                
                # Load SMS configuration from config.py
                if hasattr(ups_config, 'SMS_ENABLED'):
                    self.sms_enabled = ups_config.SMS_ENABLED
                if hasattr(ups_config, 'SMS_API_URL'):
                    self.sms_api_url = ups_config.SMS_API_URL
                if hasattr(ups_config, 'SMS_USERNAME'):
                    self.sms_username = ups_config.SMS_USERNAME
                if hasattr(ups_config, 'SMS_PASSWORD'):
                    self.sms_password = ups_config.SMS_PASSWORD
                # Load SMS schedule (time-based routing) - takes precedence over SMS_RECIPIENTS
                if hasattr(ups_config, 'SMS_SCHEDULE'):
                    schedule = ups_config.SMS_SCHEDULE
                    if schedule and isinstance(schedule, list) and len(schedule) > 0:
                        self.sms_schedule = schedule
                        self.logger.info(f"SMS time-based schedule configured with {len(schedule)} time period(s)")
                        # Log schedule details
                        for idx, period in enumerate(schedule, 1):
                            start = period.get('start_time', 'N/A')
                            end = period.get('end_time', 'N/A')
                            recipients = period.get('recipients', [])
                            self.logger.info(f"  Period {idx}: {start} - {end} -> {len(recipients)} recipient(s): {recipients}")
                    else:
                        self.sms_schedule = None
                
                # Load SMS_RECIPIENTS (fallback if SMS_SCHEDULE is not used)
                if hasattr(ups_config, 'SMS_RECIPIENTS'):
                    self.sms_recipients = ups_config.SMS_RECIPIENTS if isinstance(ups_config.SMS_RECIPIENTS, list) else [ups_config.SMS_RECIPIENTS]
                
                if hasattr(ups_config, 'SMS_TYPE'):
                    self.sms_type = ups_config.SMS_TYPE
                if hasattr(ups_config, 'SMS_RETURN_MODE'):
                    self.sms_return_mode = ups_config.SMS_RETURN_MODE
                
                # Load ALARM_LED_ENABLED from config.py
                if hasattr(ups_config, 'ALARM_LED_ENABLED'):
                    self.alarm_led_enabled = ups_config.ALARM_LED_ENABLED
                    if self.alarm_led_enabled:
                        self.logger.info("Alarm LED (LED 10) is ENABLED - LED 10 will be enabled during alarms")
                    else:
                        self.logger.info("Alarm LED (LED 10) is DISABLED - LED 10 will not be enabled during alarms")
                else:
                    self.alarm_led_enabled = True  # Default to enabled
                
                # Load BUZZER_MUTED from config.py
                if hasattr(ups_config, 'BUZZER_MUTED'):
                    self.buzzer_muted = ups_config.BUZZER_MUTED
                    if self.buzzer_muted:
                        self.logger.info("Buzzer is MUTED - buzzer will not sound during alarms (LED 10 will still indicate alarm if enabled)")
                    else:
                        self.logger.info("Buzzer is ENABLED - buzzer will sound during alarms")
                else:
                    self.buzzer_muted = False  # Default to not muted
                
                # Load LED load threshold parameters from config.py
                # L1 (LED 14): Low load indicator
                self.l1_load_min = getattr(ups_config, 'L1_LOAD_MIN', 0)
                self.l1_load_max = getattr(ups_config, 'L1_LOAD_MAX', 5)
                # L2 (LED 13): Medium load indicator
                self.l2_load_min = getattr(ups_config, 'L2_LOAD_MIN', 10)
                self.l2_load_max = getattr(ups_config, 'L2_LOAD_MAX', 20)
                # L3 (LED 12): Medium-high load indicator
                self.l3_load_min = getattr(ups_config, 'L3_LOAD_MIN', 20)
                self.l3_load_max = getattr(ups_config, 'L3_LOAD_MAX', 26)
                # L4 (LED 11): Overload warning indicator
                self.l4_load_threshold = getattr(ups_config, 'L4_LOAD_THRESHOLD', 29)
                
                self.logger.info(f"LED load thresholds loaded from config: L1={self.l1_load_min}-{self.l1_load_max}%, L2={self.l2_load_min}-{self.l2_load_max}%, L3={self.l3_load_min}-{self.l3_load_max}%, L4>={self.l4_load_threshold}%")
                
                # SMS configuration status logging
                if self.sms_enabled and self.sms_api_url and self.sms_username and self.sms_password:
                    if self.sms_schedule:
                        # Time-based schedule is configured
                        total_recipients = set()
                        for period in self.sms_schedule:
                            total_recipients.update(period.get('recipients', []))
                        self.logger.info(f"SMS notifications enabled with time-based schedule ({len(total_recipients)} unique recipient(s) across all periods)")
                        self.logger.info(f"SMS API URL: {self.sms_api_url}")
                    elif self.sms_recipients:
                        # Simple list is configured
                        self.logger.info(f"SMS notifications enabled for {len(self.sms_recipients)} recipient(s) (all times)")
                        self.logger.info(f"SMS API URL: {self.sms_api_url}")
                    else:
                        self.logger.warning("SMS enabled but no recipients configured (neither SMS_SCHEDULE nor SMS_RECIPIENTS)")
                        self.sms_enabled = False
                elif self.sms_enabled:
                    self.logger.warning("SMS enabled in config but missing required settings (API URL, username, or password)")
                    self.sms_enabled = False
        except Exception as e:
            self.logger.warning(f"Error loading config from config.py: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
        
        # Set default LED load thresholds if not loaded from config
        if not hasattr(self, 'l1_load_min'):
            self.l1_load_min = 0
            self.l1_load_max = 5
            self.l2_load_min = 10
            self.l2_load_max = 20
            self.l3_load_min = 20
            self.l3_load_max = 26
            self.l4_load_threshold = 29
            self.logger.info("Using default LED load thresholds (config.py not loaded or missing parameters)")
        
        # Override email settings with function parameters if provided (for backward compatibility)
        # Function parameters take precedence over config.py values
        if email_recipients:
            self.email_recipients = email_recipients if isinstance(email_recipients, list) else [email_recipients]
        if smtp_server:
            self.smtp_server = smtp_server
        if smtp_port:
            self.smtp_port = smtp_port
        if smtp_use_tls is not None:
            self.smtp_use_tls = smtp_use_tls
        if smtp_username is not None:
            self.smtp_username = smtp_username
        if smtp_password is not None:
            self.smtp_password = smtp_password
        if from_email:
            self.from_email = from_email
        if from_name:
            self.from_name = from_name
        
        # Email sender initialization
        self.email_sender = None
        
        # Only initialize email sender if email is enabled
        if self.email_enabled and self.email_recipients and EMAIL_AVAILABLE:
            if self.smtp_server and self.from_email:
                try:
                    self.email_sender = EmailSender(
                        smtp_server=self.smtp_server,
                        smtp_port=self.smtp_port,
                        use_tls=self.smtp_use_tls,
                        username=self.smtp_username,
                        password=self.smtp_password,
                        from_email=self.from_email,
                        from_name=self.from_name
                    )
                    self.logger.info(f"Email notifications enabled for {len(self.email_recipients)} recipient(s)")
                except Exception as e:
                    self.logger.warning(f"Failed to initialize email sender: {e}")
                    self.email_sender = None
            else:
                self.logger.warning("Email recipients specified but SMTP server or from_email not provided")
        elif self.email_enabled and self.email_recipients and not EMAIL_AVAILABLE:
            self.logger.warning("Email recipients specified but email_sender module not available")
        elif not self.email_enabled:
            self.logger.info("Email notifications disabled (EMAIL_ENABLED = False in config.py)")
        
        # Track last email sent time to avoid duplicates (cooldown: 5 minutes)
        self._last_email_times = {}
        
        # Track last SMS sent time to avoid duplicates (cooldown: 5 minutes)
        self._last_sms_times = {}
        
        # GPIO LED controller configuration
        self.gpio_pins = gpio_pins if gpio_pins else {}
        self.led_controller = None
        
        if self.gpio_pins:
            self.logger.info(f"GPIO pins configured: {self.gpio_pins}")
            if GPIO_AVAILABLE:
                try:
                    self.led_controller = GPIOLEDController(
                        gpio_pins=self.gpio_pins,
                        blink_enabled=gpio_blink_enabled,
                        blink_interval=gpio_blink_interval,
                        active_high=gpio_active_high
                    )
                    self.logger.info(f"GPIO LED controller initialized successfully with pins: {self.gpio_pins}")
                except Exception as e:
                    self.logger.error(f"Failed to initialize GPIO LED controller: {e}", exc_info=True)
                    self.led_controller = None
            else:
                self.logger.warning("GPIO pins specified but GPIO controller not available (RPi.GPIO not installed or not on Raspberry Pi)")
                self.logger.warning("GPIO_AVAILABLE = False, check if RPi.GPIO is installed and running on Raspberry Pi")
        
        # Panel LED Controller (for AlarmMap-based control)
        self.panel_led_controller = None
        if PANEL_LED_CONTROLLER_AVAILABLE and not self.is_windows:
            try:
                self.panel_led_controller = PanelLEDController(
                    active_high=gpio_active_high
                )
                self.logger.info("Panel LED Controller initialized successfully (AlarmMap-based LED control)")
                
                # Initialize LEDs on startup:
                # 1. Enable all green LEDs
                # 2. Disable all red LEDs
                # 3. Disable the buzzer/speaker
                try:
                    # Enable all green LEDs
                    self.panel_led_controller.enable_all_green_leds()
                    self.logger.info("All green LEDs enabled on startup (from AlarmMap.PANEL_LED_MAPPING)")
                    
                    # Disable all red LEDs
                    self.panel_led_controller.disable_all_red_leds()
                    self.logger.info("All red LEDs disabled on startup (from AlarmMap.PANEL_LED_MAPPING)")
                    
                    # Disable the buzzer/speaker (GPIO pin 18 from AlarmMap)
                    # Use disable_buzzer() method which properly handles GPIO initialization
                    try:
                        if hasattr(self.panel_led_controller, 'disable_buzzer'):
                            # Use the dedicated disable_buzzer() method (handles GPIO properly)
                            if self.panel_led_controller.disable_buzzer():
                                from AlarmMap import get_gpio_pin_by_led
                                try:
                                    speaker_pin = get_gpio_pin_by_led('speaker')
                                    self.logger.info(f"Buzzer/speaker disabled on startup using disable_buzzer() (GPIO pin {speaker_pin})")
                                except:
                                    self.logger.info("Buzzer/speaker disabled on startup using disable_buzzer()")
                            else:
                                # Fallback to disable_led('speaker')
                                if self.panel_led_controller.disable_led('speaker'):
                                    from AlarmMap import get_gpio_pin_by_led
                                    try:
                                        speaker_pin = get_gpio_pin_by_led('speaker')
                                        self.logger.info(f"Buzzer/speaker disabled on startup using disable_led('speaker') (GPIO pin {speaker_pin})")
                                    except:
                                        self.logger.info("Buzzer/speaker disabled on startup using disable_led('speaker')")
                        else:
                            # PanelLEDController doesn't have disable_buzzer(), use disable_led()
                            if self.panel_led_controller.disable_led('speaker'):
                                from AlarmMap import get_gpio_pin_by_led
                                try:
                                    speaker_pin = get_gpio_pin_by_led('speaker')
                                    self.logger.info(f"Buzzer/speaker disabled on startup (GPIO pin {speaker_pin})")
                                except:
                                    self.logger.info("Buzzer/speaker disabled on startup")
                    except Exception as e:
                        self.logger.warning(f"Failed to disable buzzer/speaker on startup: {e}")
                        
                except Exception as e:
                    self.logger.warning(f"Failed to initialize LEDs on startup: {e}")
            except Exception as e:
                self.logger.error(f"Failed to initialize Panel LED Controller: {e}", exc_info=True)
                self.panel_led_controller = None
        
        # Button configuration (Mute and Reset buttons)
        self.mute_button_pin = 19  # GPIO pin for mute button
        self.reset_button_pin = 21  # GPIO pin for reset button
        self.mute_button_thread = None
        self.reset_button_thread = None
        self.mute_button_running = False
        self.reset_button_running = False
        self.mute_button_last_state = None
        self.reset_button_last_state = None
        self.mute_button_debounce_time = 0.01  # 10ms debounce time (reduced for faster response)
        self.reset_button_debounce_time = 0.01  # 10ms debounce time
        self.mute_button_last_change_time = 0
        self.reset_button_last_change_time = 0
        # Additional state tracking for event-driven approach (GPIO.BOTH)
        self.mute_button_last_callback_time = 0
        self.mute_button_last_callback_state = None
        self.reset_button_last_callback_time = 0
        self.reset_button_last_callback_state = None
        self._reset_sequence_running = False  # Flag to prevent multiple reset sequences
        self.alarm_status = False  # Will be loaded from config.py
        self._last_led_10_state = None  # Track LED 10 state to detect changes
        
        # Load ALARM_STATUS from config.py
        try:
            import importlib.util
            config_path = Path(__file__).parent / 'config.py'
            if config_path.exists():
                spec = importlib.util.spec_from_file_location("ups_config", config_path)
                ups_config = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(ups_config)
                if hasattr(ups_config, 'ALARM_STATUS'):
                    self.alarm_status = ups_config.ALARM_STATUS
                    self.logger.info(f"ALARM_STATUS loaded from config: {self.alarm_status}")
        except Exception as e:
            self.logger.debug(f"Could not load ALARM_STATUS from config: {e}")
            self.alarm_status = False
        
        # Sound controller configuration
        self.sound_controller = None
        if sound_enabled:
            try:
                self.sound_controller = SoundController(
                    sound_enabled=sound_enabled,
                    sound_files=sound_files,
                    use_beep=sound_use_beep,
                    beep_duration=sound_beep_duration,
                    beep_frequency=sound_beep_frequency,
                    volume=sound_volume
                )
                self.logger.info("Sound controller initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize sound controller: {e}", exc_info=True)
                self.sound_controller = None
        else:
            self.logger.info("Sound alerts disabled")
        
        # UPS Status Checker initialization (for periodic status queries)
        self.ups_status_checker = None
        self.ups_host = None
        self.ups_status_thread = None
        self._status_check_running = False
        self.snmp_community = 'public'  # Default SNMP community string
        self.snmp_port = 161  # Default SNMP port
        
        # Determine UPS host from allowed_ips or config
        # PRIORITY: Use ATS device (192.168.111.173) if in allowed_ips, otherwise use first non-localhost IP
        self.ups_host = None
        if self.allowed_ips:
            # First, check if ATS device IP is in allowed_ips (preferred)
            if '192.168.111.173' in self.allowed_ips:
                self.ups_host = '192.168.111.173'
                self.logger.info(f"Using ATS device IP from allowed_ips: {self.ups_host}")
            else:
                # Use first allowed IP that's not localhost
                for ip in self.allowed_ips:
                    if ip and ip != '127.0.0.1' and ip != '1':
                        self.ups_host = ip
                        self.logger.info(f"Using first non-localhost IP from allowed_ips: {self.ups_host}")
                        break
        if not self.ups_host:
            # Fallback to UPS_IP from config
            try:
                import importlib.util
                config_path = Path(__file__).parent / 'config.py'
                if config_path.exists():
                    spec = importlib.util.spec_from_file_location("ups_config", config_path)
                    ups_config = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(ups_config)
                    if hasattr(ups_config, 'UPS_IP'):
                        self.ups_host = ups_config.UPS_IP
                    
                    # Load SNMP community string from config (if available)
                    if hasattr(ups_config, 'SNMP_COMMUNITY'):
                        self.snmp_community = ups_config.SNMP_COMMUNITY
                        self.logger.info(f"SNMP community string loaded from config: {self.snmp_community}")
                    else:
                        self.logger.debug(f"SNMP_COMMUNITY not found in config, using default: {self.snmp_community}")
                    
                    # Load SNMP port from config (if available)
                    if hasattr(ups_config, 'SNMP_PORT'):
                        self.snmp_port = ups_config.SNMP_PORT
                        self.logger.info(f"SNMP port loaded from config: {self.snmp_port}")
                    else:
                        self.logger.debug(f"SNMP_PORT not found in config, using default: {self.snmp_port}")
            except Exception as e:
                self.logger.debug(f"Could not load UPS_IP/SNMP settings from config: {e}")
        
        if GET_UPS_STATUS_AVAILABLE and self.ups_host:
            try:
                self.ups_status_checker = GetUPSStatus(self.ups_host, community=self.snmp_community, port=self.snmp_port)
                self.logger.info(f"Initializing UPS status checker for host: {self.ups_host} (community: {self.snmp_community}, port: {self.snmp_port})")
                # Test connectivity
                if self.ups_status_checker.test_connectivity():
                    self.logger.info(f"UPS status checker initialized successfully for host: {self.ups_host}")
                else:
                    self.logger.warning(f"UPS status checker initialized but connectivity test failed for {self.ups_host} (community: {self.snmp_community}, port: {self.snmp_port})")
                    self.logger.warning("This may indicate incorrect SNMP community string or network connectivity issues")
            except Exception as e:
                self.logger.error(f"Failed to initialize UPS status checker: {e}", exc_info=True)
                self.ups_status_checker = None
        else:
            if not GET_UPS_STATUS_AVAILABLE:
                self.logger.debug("GetUPSStatus not available (GetUPSStatus module not found)")
            if not self.ups_host:
                self.logger.debug("UPS host not determined (no allowed_ips or UPS_IP configured)")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self._shutdown_requested = True
        
        # Stop button monitoring threads
        self.mute_button_running = False
        self.reset_button_running = False
        
        # Close dispatcher to interrupt run_dispatcher() blocking call
        if self.snmp_engine and hasattr(self.snmp_engine, 'transport_dispatcher'):
            try:
                self.snmp_engine.transport_dispatcher.close_dispatcher()
            except Exception as e:
                self.logger.debug(f"Error closing dispatcher from signal handler: {e}")
    
    def _write_pid_file(self):
        """Write PID to file."""
        if self.pid_file:
            try:
                self.pid_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.pid_file, 'w') as f:
                    f.write(str(os.getpid()))
                self.logger.info(f"PID file written: {self.pid_file}")
            except Exception as e:
                self.logger.error(f"Failed to write PID file: {e}")
    
    def _remove_pid_file(self):
        """Remove PID file."""
        if self.pid_file and self.pid_file.exists():
            try:
                self.pid_file.unlink()
                self.logger.info(f"PID file removed: {self.pid_file}")
            except Exception as e:
                self.logger.error(f"Failed to remove PID file: {e}")
    
    def _read_pid_file(self) -> Optional[int]:
        """Read PID from file."""
        if self.pid_file and self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    return int(f.read().strip())
            except (ValueError, IOError) as e:
                self.logger.warning(f"Failed to read PID file: {e}")
        return None
    
    def _is_running(self) -> bool:
        """Check if process is running based on PID file."""
        pid = self._read_pid_file()
        if pid is None:
            return False
        try:
            # Check if process exists (sends signal 0, doesn't kill)
            os.kill(pid, 0)
            return True
        except OSError:
            # Process doesn't exist
            return False
        
    def setup_logging(self):
        """Configure logging to both file and console."""
        try:
            # Create log directory if it doesn't exist
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            print(f"Log file path: {self.log_file.absolute()}", flush=True)
            
            # Test if we can write to the log file
            try:
                test_file = open(self.log_file, 'a')
                test_file.write(f"# Log file test write at {datetime.now()}\n")
                test_file.flush()
                test_file.close()
                print(f"✓ Log file is writable: {self.log_file.absolute()}", flush=True)
            except Exception as e:
                print(f"✗ ERROR: Cannot write to log file {self.log_file.absolute()}: {e}", file=sys.stderr, flush=True)
                # Try to use a fallback location
                fallback_log = Path.home() / get_log_filename()
                print(f"  Trying fallback location: {fallback_log}", flush=True)
                self.log_file = fallback_log
                self.log_file.parent.mkdir(parents=True, exist_ok=True)
                # Update email and SMS log files to use same fallback directory
                log_dir = self.log_file.parent
                self.email_log_file = log_dir / get_log_filename('ups_email', '.log')
                self.sms_log_file = log_dir / get_log_filename('ups_sms', '.log')
            
            # Configure logging - use DEBUG level to capture all debug messages
            # Clear any existing handlers first
            root_logger = logging.getLogger()
            root_logger.handlers = []
            
            # Create throttled filter for verbose asyncio messages
            epoll_filter = ThrottledLogFilter("Using selector: EpollSelector", throttle_seconds=60)
            
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(self.log_file, mode='a', encoding='utf-8'),
                    logging.StreamHandler(sys.stdout)
                ],
                force=True  # Override any existing configuration
            )
            
            # Add filter to root logger to throttle asyncio messages
            root_logger.addFilter(epoll_filter)
            
            # Also add filter to asyncio logger specifically
            asyncio_logger = logging.getLogger('asyncio')
            asyncio_logger.addFilter(epoll_filter)
            
            self.logger = logging.getLogger(__name__)
            
            # Create separate loggers for email and SMS
            # Email logger
            self.email_logger = logging.getLogger(f"{__name__}.email")
            self.email_logger.setLevel(logging.DEBUG)
            # Remove any existing handlers
            self.email_logger.handlers = []
            # Add file handler for email log
            email_handler = logging.FileHandler(self.email_log_file, mode='a', encoding='utf-8')
            email_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.email_logger.addHandler(email_handler)
            # Prevent propagation to root logger to avoid duplicate logs
            self.email_logger.propagate = False
            
            # SMS logger
            self.sms_logger = logging.getLogger(f"{__name__}.sms")
            self.sms_logger.setLevel(logging.DEBUG)
            # Remove any existing handlers
            self.sms_logger.handlers = []
            # Add file handler for SMS log
            sms_handler = logging.FileHandler(self.sms_log_file, mode='a', encoding='utf-8')
            sms_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.sms_logger.addHandler(sms_handler)
            # Prevent propagation to root logger to avoid duplicate logs
            self.sms_logger.propagate = False
            
            # Log initialization for email and SMS loggers
            self.email_logger.info("=" * 80)
            self.email_logger.info(f"EMAIL NOTIFICATION LOG - INITIALIZATION")
            self.email_logger.info(f"Initialization Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.email_logger.info(f"Email Log File: {self.email_log_file.absolute()}")
            self.email_logger.info("=" * 80)
            
            self.sms_logger.info("=" * 80)
            self.sms_logger.info(f"SMS NOTIFICATION LOG - INITIALIZATION")
            self.sms_logger.info(f"Initialization Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.sms_logger.info(f"SMS Log File: {self.sms_log_file.absolute()}")
            self.sms_logger.info("=" * 80)
            
            # Log initial START event when logging is first set up
            init_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.logger.info("=" * 80)
            self.logger.info(f"UPS/ATS SNMP TRAP RECEIVER v3 - INITIALIZATION EVENT (SNMPv2c)")
            self.logger.info(f"Initialization Time: {init_time}")
            self.logger.info(f"Log File: {self.log_file.absolute()}")
            self.logger.info("=" * 80)
            
            # Set console handler to INFO to reduce console noise, but keep DEBUG in file
            for handler in self.logger.handlers:
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                    handler.setLevel(logging.INFO)
            
            # Verify logging is working - write test messages
            self.logger.info("=" * 70)
            self.logger.info("UPS/ATS SNMP Trap Receiver v3 - Logging initialized (SNMPv2c)")
            self.logger.info(f"Log file: {self.log_file.absolute()}")
            self.logger.info(f"Log file exists: {self.log_file.exists()}")
            self.logger.info(f"Log file writable: {os.access(self.log_file, os.W_OK) if self.log_file.exists() else 'N/A'}")
            print(f"✓ Logging initialized successfully", flush=True)
            
        except Exception as e:
            print(f"✗ CRITICAL ERROR in setup_logging: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc()
            # Create a minimal logger that at least writes to console
            logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
            self.logger = logging.getLogger(__name__)
            self.logger.error(f"Failed to setup file logging: {e}")
        
    def _get_ups_info(self, source_ip):
        """
        Get UPS name and location for a given source IP address.
        
        Args:
            source_ip: IP address of the UPS device sending the trap
            
        Returns:
            tuple: (ups_name, ups_location) - Name and location of the UPS device
        """
        if source_ip and self.ups_devices and source_ip in self.ups_devices:
            ups_info = self.ups_devices[source_ip]
            ups_name = ups_info.get('name', self.ups_name)
            ups_location = ups_info.get('location', self.ups_location)
            return (ups_name, ups_location)
        else:
            # Use default values if IP not found in UPS_DEVICES
            return (self.ups_name, self.ups_location)
    
    def _get_sms_recipients_for_current_time(self):
        """
        Get SMS recipients based on current time and SMS schedule.
        
        Returns:
            List of recipient phone numbers for the current time period.
            Returns empty list if no recipients are configured for current time.
            Returns SMS_RECIPIENTS if SMS_SCHEDULE is not configured (backward compatibility).
        """
        from datetime import datetime
        
        # If no schedule is configured, use simple SMS_RECIPIENTS list (backward compatibility)
        if not self.sms_schedule:
            return self.sms_recipients if self.sms_recipients else []
        
        # Get current time
        now = datetime.now()
        current_time = now.time()
        current_hour = current_time.hour
        current_minute = current_time.minute
        current_minutes = current_hour * 60 + current_minute
        
        # Find matching time period
        for period in self.sms_schedule:
            start_time_str = period.get('start_time', '00:00')
            end_time_str = period.get('end_time', '23:59')
            recipients = period.get('recipients', [])
            
            # Parse start and end times
            try:
                start_parts = start_time_str.split(':')
                start_hour = int(start_parts[0])
                start_minute = int(start_parts[1]) if len(start_parts) > 1 else 0
                start_minutes = start_hour * 60 + start_minute
                
                end_parts = end_time_str.split(':')
                end_hour = int(end_parts[0])
                end_minute = int(end_parts[1]) if len(end_parts) > 1 else 0
                end_minutes = end_hour * 60 + end_minute
                
                # Handle time ranges that cross midnight (e.g., 18:00 - 00:00)
                if end_minutes <= start_minutes:
                    # Time range crosses midnight
                    if current_minutes >= start_minutes or current_minutes < end_minutes:
                        return recipients if recipients else []
                else:
                    # Normal time range within same day
                    if start_minutes <= current_minutes < end_minutes:
                        return recipients if recipients else []
            except (ValueError, IndexError) as e:
                self.logger.warning(f"Invalid time format in SMS schedule: start_time={start_time_str}, end_time={end_time_str}, error={e}")
                continue
        
        # No matching time period found - return empty list (no SMS during this time)
        return []
    
    def cbFun(self, snmpEngine, stateReference, contextName, varBinds, cbCtx, *args):
        """
        Callback function to process received SNMP traps.
        
        Args:
            snmpEngine: SNMP engine instance
            stateReference: State reference
            contextName: Context name
            varBinds: Variable bindings from the trap
            cbCtx: Callback context
            *args: Additional arguments (for compatibility with different pysnmp versions)
        """
        try:
            # Debug: Log contextName and initial trap information
            self.logger.info(f"=== SNMP Trap Received (Callback Triggered) ===")
            self.logger.debug(f"Context Name: {contextName}")
            self.logger.debug(f"State Reference: {stateReference} (type: {type(stateReference).__name__})")
            self.logger.debug(f"Callback Context type: {type(cbCtx).__name__}")
            self.logger.debug(f"Additional Args: {args}")
            self.logger.debug(f"varBinds parameter count: {len(varBinds) if varBinds else 0}")
            
            # IMPORTANT: In some pysnmp versions, varBinds might be empty but cbCtx contains the data!
            # Extract variable bindings from cbCtx if varBinds is empty
            actual_varBinds = varBinds
            if (not varBinds or len(varBinds) == 0) and cbCtx:
                self.logger.debug("varBinds is empty, checking cbCtx for variable bindings...")
                if isinstance(cbCtx, (list, tuple)) and len(cbCtx) > 0:
                    # Check if cbCtx contains variable bindings (list of (oid, value) tuples)
                    if isinstance(cbCtx[0], (list, tuple)) and len(cbCtx[0]) == 2:
                        actual_varBinds = cbCtx
                        self.logger.debug(f"Found {len(actual_varBinds)} variable bindings in cbCtx")
                    elif hasattr(cbCtx, '__iter__'):
                        # Try to extract from iterable
                        try:
                            actual_varBinds = list(cbCtx)
                            self.logger.debug(f"Extracted {len(actual_varBinds)} variable bindings from cbCtx iterable")
                        except:
                            pass
            
            # Log all variable bindings in debug mode
            if actual_varBinds:
                self.logger.debug(f"Variable Bindings (raw) - Total: {len(actual_varBinds)}")
                for idx, binding in enumerate(actual_varBinds):
                    try:
                        if isinstance(binding, (list, tuple)) and len(binding) >= 2:
                            oid, val = binding[0], binding[1]
                            oid_str = str(oid)
                            val_type = type(val).__name__
                            val_repr = repr(val)[:100]  # Limit length
                            self.logger.debug(f"  [{idx}] OID: {oid_str}, Type: {val_type}, Value: {val_repr}")
                        else:
                            self.logger.debug(f"  [{idx}] Unexpected binding format: {type(binding)}")
                    except Exception as e:
                        self.logger.debug(f"  [{idx}] Error logging variable: {e}")
            
            # Get trap information - try modern API first, fallback to old API
            source_ip = None
            source_port = None
            source_address = "unknown:unknown"
            
            # Try multiple methods to get source address (compatibility with different pysnmp versions)
            transportAddress = None
            
            # Method 0: Try to get from our captured source addresses (most recent, within last second)
            if hasattr(self, '_last_src_addr') and self._last_src_addr:
                import time
                current_time = time.time()
                # Get addresses from the last second (should be very recent)
                recent_addrs = {k: v for k, v in self._last_src_addr.items() if current_time - k < 1.0}
                if recent_addrs:
                    # Get the most recent one
                    most_recent_time = max(recent_addrs.keys())
                    transportAddress = recent_addrs[most_recent_time]
                    self.logger.debug(f"Found source address from capture cache: {transportAddress} (age: {current_time - most_recent_time:.3f}s)")
                    # Clean up old entries (keep last 5 seconds)
                    self._last_src_addr = {k: v for k, v in self._last_src_addr.items() if current_time - k < 5.0}
            
            # Method 1: Try to get from transport dispatcher's internal receive queue (for asyncio UDP)
            # The asyncio transport stores source address with each received datagram
            try:
                if hasattr(snmpEngine, 'transport_dispatcher'):
                    transport_disp = snmpEngine.transport_dispatcher
                    # Check if there's a receive queue or message buffer
                    for attr_name in ['_recvQueue', '_msgQueue', '_pendingRecv', 'recvQueue']:
                        if hasattr(transport_disp, attr_name):
                            recv_queue = getattr(transport_disp, attr_name)
                            if recv_queue:
                                # Try to get the most recent message with source info
                                if isinstance(recv_queue, (list, tuple)) and len(recv_queue) > 0:
                                    # Get last item (most recent)
                                    last_msg = recv_queue[-1]
                                    if isinstance(last_msg, dict):
                                        transportAddress = last_msg.get('src_addr') or last_msg.get('address') or last_msg.get('transportAddress')
                                    elif hasattr(last_msg, 'src_addr'):
                                        transportAddress = last_msg.src_addr
                                    elif hasattr(last_msg, 'address'):
                                        transportAddress = last_msg.address
                                    if transportAddress:
                                        break
            except (AttributeError, KeyError, TypeError, IndexError):
                pass
            
            # Method 2: Try to get from transport endpoint's receive buffer (for UDP asyncio transport)
            try:
                if hasattr(snmpEngine, 'transport_dispatcher'):
                    transport_dispatcher = snmpEngine.transport_dispatcher
                    # For UDP, the source address is stored with each received datagram
                    # Check if transport dispatcher has a message cache with source info
                    if hasattr(transport_dispatcher, '_recvCallbacks'):
                        # The receive callbacks might have source address info
                        for callback_info in transport_dispatcher._recvCallbacks.values():
                            if hasattr(callback_info, 'transportAddress'):
                                transportAddress = callback_info.transportAddress
                                break
                    # Also check transport map for endpoint info
                    if not transportAddress and hasattr(transport_dispatcher, '_transportMap'):
                        for transport_endpoint in transport_dispatcher._transportMap.values():
                            # For UDP, check if there's a pending message with source info
                            if hasattr(transport_endpoint, '_pendingMessages'):
                                for msg in transport_endpoint._pendingMessages:
                                    if hasattr(msg, 'transportAddress'):
                                        transportAddress = msg.transportAddress
                                        break
                                if transportAddress:
                                    break
            except (AttributeError, KeyError, TypeError):
                pass
            
            # Method 3: Try accessing through message dispatcher's internal state
            if not transportAddress:
                try:
                    # Check if stateReference has transport info stored
                    if hasattr(stateReference, '__dict__'):
                        # Look for transport-related attributes
                        for attr_name in ['transportAddress', '_transportAddress', 'transport_address', 'peer', 'address']:
                            if hasattr(stateReference, attr_name):
                                addr = getattr(stateReference, attr_name)
                                if addr:
                                    transportAddress = addr
                                    break
                    # Also check all attributes for debugging (only log once)
                    if not transportAddress and not hasattr(self, '_debug_logged'):
                        self._debug_logged = True
                        state_attrs = [attr for attr in dir(stateReference) if not attr.startswith('__')]
                        self.logger.debug(f"stateReference attributes: {state_attrs[:10]}")  # Log first 10
                except (AttributeError, TypeError):
                    pass
            
            # Method 4: Try modern API - message_dispatcher
            if not transportAddress:
                try:
                    if hasattr(snmpEngine, 'message_dispatcher'):
                        # Try different method names
                        for method_name in ['get_execution_context', 'getExecutionContext', 'getContext']:
                            if hasattr(snmpEngine.message_dispatcher, method_name):
                                try:
                                    execContext = getattr(snmpEngine.message_dispatcher, method_name)(stateReference)
                                    if isinstance(execContext, dict):
                                        transportAddress = execContext.get('transportAddress')
                                    elif hasattr(execContext, 'transportAddress'):
                                        transportAddress = execContext.transportAddress
                                    if transportAddress:
                                        break
                                except (AttributeError, KeyError, TypeError):
                                    continue
                except (AttributeError, TypeError):
                    pass
            
            # Method 5: Try old deprecated API (with warning suppression)
            if not transportAddress:
                try:
                    import warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", DeprecationWarning)
                        if hasattr(snmpEngine, 'msgAndPduDsp'):
                            for method_name in ['getExecutionContext', 'get_execution_context']:
                                if hasattr(snmpEngine.msgAndPduDsp, method_name):
                                    try:
                                        execContext = getattr(snmpEngine.msgAndPduDsp, method_name)(stateReference)
                                        if isinstance(execContext, dict):
                                            transportAddress = execContext.get('transportAddress')
                                        elif hasattr(execContext, 'transportAddress'):
                                            transportAddress = execContext.transportAddress
                                        if transportAddress:
                                            break
                                    except (AttributeError, KeyError, TypeError):
                                        continue
                except (AttributeError, TypeError):
                    pass
            
            # Method 6: Try to extract from transport_dispatcher's message cache or state
            if not transportAddress:
                try:
                    if hasattr(snmpEngine, 'transport_dispatcher'):
                        transport_disp = snmpEngine.transport_dispatcher
                        # Check various internal structures
                        for attr_name in ['_msgMap', '_stateMap', '_transportState', 'stateMap']:
                            if hasattr(transport_disp, attr_name):
                                state_map = getattr(transport_disp, attr_name)
                                if isinstance(state_map, dict):
                                    state_info = state_map.get(stateReference, None)
                                    if state_info:
                                        # Try to get transport address from state info
                                        if isinstance(state_info, dict):
                                            transportAddress = state_info.get('transportAddress') or state_info.get('address')
                                        elif hasattr(state_info, 'transportAddress'):
                                            transportAddress = state_info.transportAddress
                                        elif hasattr(state_info, 'address'):
                                            transportAddress = state_info.address
                                        if transportAddress:
                                            break
                except (AttributeError, KeyError, TypeError):
                    pass
            
            # Method 7: Try to get from message processing pipeline
            if not transportAddress:
                try:
                    # The message might have transport info in its metadata
                    if hasattr(snmpEngine, 'message_dispatcher'):
                        # Check if there's a message cache
                        if hasattr(snmpEngine.message_dispatcher, '_msgCache'):
                            msg_data = snmpEngine.message_dispatcher._msgCache.get(stateReference, None)
                            if msg_data and isinstance(msg_data, dict):
                                transportAddress = msg_data.get('transportAddress') or msg_data.get('address')
                except (AttributeError, KeyError, TypeError):
                    pass
            
            # Method 8: Try to inspect transport endpoint's socket directly (for asyncio UDP)
            if not transportAddress:
                try:
                    if hasattr(snmpEngine, 'transport_dispatcher'):
                        transport_disp = snmpEngine.transport_dispatcher
                        # Get transport endpoint
                        if hasattr(transport_disp, '_transportMap'):
                            for transport_endpoint in transport_disp._transportMap.values():
                                # Check if endpoint has socket with source address info
                                if hasattr(transport_endpoint, 'socket'):
                                    socket_obj = transport_endpoint.socket
                                    # For UDP, check if there's a way to get last received address
                                    # Some asyncio implementations store this
                                    if hasattr(transport_endpoint, '_last_addr'):
                                        transportAddress = transport_endpoint._last_addr
                                        break
                                    # Check if socket has a way to get peer info (unlikely for UDP, but try)
                                    try:
                                        if hasattr(socket_obj, 'getpeername'):
                                            transportAddress = socket_obj.getpeername()
                                            break
                                    except (OSError, AttributeError):
                                        pass
                                # Check endpoint's internal state
                                for attr in ['_src_addr', '_address', '_peer', 'src_addr', 'address']:
                                    if hasattr(transport_endpoint, attr):
                                        addr = getattr(transport_endpoint, attr)
                                        if addr:
                                            transportAddress = addr
                                            break
                                    if transportAddress:
                                        break
                except (AttributeError, KeyError, TypeError):
                    pass
            
            # Extract IP and port from transportAddress
            if transportAddress:
                try:
                    if isinstance(transportAddress, (tuple, list)) and len(transportAddress) >= 2:
                        source_ip = str(transportAddress[0])
                        source_port = str(transportAddress[1])
                        source_address = f"{source_ip}:{source_port}"
                    elif isinstance(transportAddress, str):
                        # Handle string format like "192.168.1.1:12345"
                        if ':' in transportAddress:
                            parts = transportAddress.split(':')
                            source_ip = parts[0]
                            source_port = parts[1] if len(parts) > 1 else 'unknown'
                            source_address = f"{source_ip}:{source_port}"
                        else:
                            source_ip = transportAddress
                            source_port = 'unknown'
                            source_address = f"{source_ip}:{source_port}"
                    else:
                        source_address = str(transportAddress)
                        source_ip = source_address.split(':')[0] if ':' in source_address else None
                except (IndexError, TypeError, AttributeError) as e:
                    self.logger.debug(f"Error parsing transportAddress {transportAddress}: {e}")
                    source_address = str(transportAddress)
                    source_ip = source_address.split(':')[0] if ':' in source_address else None
            else:
                # Last resort: try to get from callback context if available
                if cbCtx and hasattr(cbCtx, 'transportAddress'):
                    try:
                        transportAddress = cbCtx.transportAddress
                        if isinstance(transportAddress, (tuple, list)) and len(transportAddress) >= 2:
                            source_ip = str(transportAddress[0])
                            source_port = str(transportAddress[1])
                            source_address = f"{source_ip}:{source_port}"
                        else:
                            source_address = str(transportAddress)
                            source_ip = source_address.split(':')[0] if ':' in source_address else None
                    except (AttributeError, TypeError, IndexError):
                        self.logger.warning("Could not extract source address from trap")
                        source_address = "unknown:unknown"
                        source_ip = None
                else:
                    self.logger.warning("Could not extract source address from trap")
                    # Debug: Log why we couldn't extract it
                    self.logger.debug("Source address extraction failed. Debug info:")
                    self.logger.debug(f"  - Has _last_src_addr: {hasattr(self, '_last_src_addr')}")
                    if hasattr(self, '_last_src_addr'):
                        self.logger.debug(f"  - _last_src_addr entries: {len(self._last_src_addr)}")
                    self.logger.debug(f"  - Has transport_dispatcher: {hasattr(snmpEngine, 'transport_dispatcher')}")
                    if hasattr(snmpEngine, 'transport_dispatcher'):
                        td = snmpEngine.transport_dispatcher
                        self.logger.debug(f"  - Transport dispatcher type: {type(td).__name__}")
                        self.logger.debug(f"  - Transport dispatcher attributes: {[a for a in dir(td) if not a.startswith('__')][:15]}")
                    source_address = "unknown:unknown"
                    source_ip = None
            
            # Log source IP detection result
            self.logger.info(f"Source IP detected: {source_ip} (from {source_address})")
            self.logger.info(f"Allowed IPs: {self.allowed_ips}")
            
            # Filter by allowed IP addresses if configured
            if self.allowed_ips:
                if source_ip is None:
                    # If we can't determine source IP, log detailed debug info and decide based on security policy
                    # For now, we'll allow it with a strong warning (you can change this to reject if needed)
                    self.logger.warning(
                        f"SECURITY WARNING: Could not determine source IP for trap. "
                        f"Processing trap anyway (source address: {source_address}). "
                        f"Expected source: {', '.join(self.allowed_ips)}"
                    )
                    # Uncomment the next line to reject traps when source IP cannot be determined:
                    # return
                elif source_ip not in self.allowed_ips:
                    self.logger.warning(
                        f"Rejected trap from unauthorized source: {source_address} "
                        f"(not in allowed list: {', '.join(self.allowed_ips)})"
                    )
                    self.logger.warning(f"To allow this IP, add '{source_ip}' to ALLOWED_IPS in config.py or UPS_DEVICES")
                    return  # Ignore trap from unauthorized source
                else:
                    self.logger.info(f"Source IP {source_ip} is in allowed list - processing trap")
            
            # Get UPS name and location based on source IP
            ups_name, ups_location = self._get_ups_info(source_ip)
            if source_ip:
                self.logger.debug(f"UPS info for {source_ip}: name='{ups_name}', location='{ups_location}'")
            
            # Extract trap OID and variables
            trap_oid = None
            trap_vars = {}
            battery_related = False
            snmp_trap_oid = None  # Standard SNMP trap OID (1.3.6.1.6.3.1.1.4.1.0)
            
            # Helper function to normalize ATS trap OIDs
            # Converts atsAgent(2) OIDs to atsAgent(3) for lookup in TrapIDTable.py
            # Device firmware uses atsAgent(2) but TrapIDTable uses MIB-defined atsAgent(3)
            def normalize_ats_trap_oid(oid_str):
                """
                Normalize ATS trap OID by converting atsAgent(2) to atsAgent(3).
                
                Args:
                    oid_str: Trap OID string
                
                Returns:
                    Normalized OID string (atsAgent(2) -> atsAgent(3)) or original if not ATS
                """
                if not oid_str or not isinstance(oid_str, str):
                    return oid_str
                
                # Check if this is an ATS trap OID with atsAgent(2)
                # Pattern: 1.3.6.1.4.1.37662.1.2.2.1.2.x (atsAgent=2)
                # Convert to: 1.3.6.1.4.1.37662.1.2.3.1.2.x (atsAgent=3)
                if oid_str.startswith('1.3.6.1.4.1.37662.1.2.2.1.2.'):
                    # Replace atsAgent(2) with atsAgent(3) for lookup
                    normalized = oid_str.replace('1.3.6.1.4.1.37662.1.2.2.1.2.', '1.3.6.1.4.1.37662.1.2.3.1.2.', 1)
                    self.logger.debug(f"  -> Normalized ATS trap OID: {oid_str} -> {normalized} (atsAgent(2) -> atsAgent(3))")
                    return normalized
                
                return oid_str
            
            # Process variable bindings (use actual_varBinds which may come from cbCtx)
            if actual_varBinds:
                self.logger.debug("Processing variable bindings...")
                for binding in actual_varBinds:
                    # Handle different binding formats
                    if isinstance(binding, (list, tuple)) and len(binding) >= 2:
                        oid, val = binding[0], binding[1]
                    else:
                        self.logger.warning(f"Unexpected binding format: {binding}")
                        continue
                    try:
                        oid_str = str(oid)
                        val_str = self.format_snmp_value(val)
                        
                        self.logger.debug(f"Processing OID: {oid_str} = {val_str} (type: {type(val).__name__})")
                        
                        # Check for standard SNMP trap OID (snmpTrapOID) - some UPS devices send trap OID here
                        if oid_str == '1.3.6.1.6.3.1.1.4.1.0':
                            # The value of snmpTrapOID is the actual trap OID (may be ObjectIdentifier or string)
                            # Convert to string to ensure proper comparison
                            if isinstance(val, rfc1902.ObjectIdentifier):
                                snmp_trap_oid = str(val)
                            else:
                                snmp_trap_oid = str(val_str)
                            self.logger.info(f"  -> Found snmpTrapOID: {snmp_trap_oid} (type: {type(val).__name__})")
                            
                            # Normalize ATS trap OID (convert atsAgent(2) to atsAgent(3) for lookup)
                            normalized_trap_oid = normalize_ats_trap_oid(snmp_trap_oid)
                            
                            # Check if this snmpTrapOID matches a known UPS trap (try normalized first)
                            if normalized_trap_oid in UPS_OIDS:
                                trap_oid = normalized_trap_oid
                                trap_name = UPS_OIDS[normalized_trap_oid]
                                self.logger.info(f"  -> snmpTrapOID matches known UPS trap (normalized): {trap_name}")
                                # Check if it's battery-related
                                if 'Battery' in trap_name or 'battery' in trap_name.lower() or 'Power' in trap_name:
                                    battery_related = True
                                    self.logger.debug(f"  -> Marked as battery/power-related")
                            elif snmp_trap_oid in UPS_OIDS:
                                # Try original OID as fallback
                                trap_oid = snmp_trap_oid
                                trap_name = UPS_OIDS[snmp_trap_oid]
                                self.logger.info(f"  -> snmpTrapOID matches known UPS trap: {trap_name}")
                                # Check if it's battery-related
                                if 'Battery' in trap_name or 'battery' in trap_name.lower() or 'Power' in trap_name:
                                    battery_related = True
                                    self.logger.debug(f"  -> Marked as battery/power-related")
                            else:
                                self.logger.warning(f"  -> snmpTrapOID {snmp_trap_oid} not in UPS_OIDS (will check later)")
                        
                        # Normalize OID for lookup (convert atsAgent(2) to atsAgent(3))
                        normalized_oid = normalize_ats_trap_oid(oid_str)
                        
                        # Check if this is a known UPS trap OID (try normalized first, then original)
                        if normalized_oid in UPS_OIDS:
                            trap_oid = normalized_oid
                            trap_name = UPS_OIDS[normalized_oid]
                            trap_vars[trap_name] = val_str
                            self.logger.debug(f"  -> Matched known UPS trap (normalized): {trap_name}")
                            # Check if it's battery-related
                            if 'Battery' in trap_name or 'battery' in trap_name.lower() or 'Power' in trap_name:
                                battery_related = True
                                self.logger.debug(f"  -> Marked as battery/power-related")
                        elif oid_str in UPS_OIDS:
                            trap_oid = oid_str
                            trap_name = UPS_OIDS[oid_str]
                            trap_vars[trap_name] = val_str
                            self.logger.debug(f"  -> Matched known UPS trap: {trap_name}")
                            # Check if it's battery-related
                            if 'Battery' in trap_name or 'battery' in trap_name.lower() or 'Power' in trap_name:
                                battery_related = True
                                self.logger.debug(f"  -> Marked as battery/power-related")
                        else:
                            # Check if OID matches battery-related patterns
                            for pattern in BATTERY_OID_PATTERNS:
                                if oid_str.startswith(pattern):
                                    battery_related = True
                                    self.logger.debug(f"  -> Matched battery pattern: {pattern}")
                                    break
                            # Check if OID is ATS MIB (1.3.6.1.4.1.37662) - Borri STS32A
                            if oid_str.startswith('1.3.6.1.4.1.37662'):
                                battery_related = True
                                self.logger.debug(f"  -> Matched ATS MIB pattern (Borri STS32A)")
                            # Also check for legacy APC PowerNet MIB (1.3.6.1.4.1.935) for backward compatibility
                            elif oid_str.startswith('1.3.6.1.4.1.935'):
                                battery_related = True
                                self.logger.debug(f"  -> Matched legacy APC PowerNet MIB pattern")
                            # Store other variables
                            trap_vars[oid_str] = val_str
                            self.logger.debug(f"  -> Stored as generic variable")
                    except Exception as e:
                        self.logger.warning(f"Error processing variable binding {oid}: {e}", exc_info=True)
                        # Still try to store it
                        try:
                            trap_vars[str(oid)] = str(val)
                            self.logger.debug(f"  -> Stored as string fallback")
                        except Exception as e2:
                            self.logger.error(f"  -> Failed to store variable: {e2}")
                self.logger.debug(f"Processed {len(trap_vars)} variables total")
                
                # If we didn't find trap_oid directly but found snmpTrapOID, use it
                if not trap_oid and snmp_trap_oid:
                    # Normalize ATS trap OID (convert atsAgent(2) to atsAgent(3) for lookup)
                    normalized_trap_oid = normalize_ats_trap_oid(snmp_trap_oid)
                    
                    if normalized_trap_oid in UPS_OIDS:
                        trap_oid = normalized_trap_oid
                        trap_name = UPS_OIDS[normalized_trap_oid]
                        self.logger.info(f"Using snmpTrapOID as trap_oid (normalized): {trap_oid} -> {trap_name}")
                        # Mark as battery/power related if appropriate
                        if 'Battery' in trap_name or 'battery' in trap_name.lower() or 'Power' in trap_name:
                            battery_related = True
                    elif snmp_trap_oid in UPS_OIDS:
                        # Try original OID as fallback
                        trap_oid = snmp_trap_oid
                        trap_name = UPS_OIDS[snmp_trap_oid]
                        self.logger.info(f"Using snmpTrapOID as trap_oid: {trap_oid} -> {trap_name}")
                        # Mark as battery/power related if appropriate
                        if 'Battery' in trap_name or 'battery' in trap_name.lower() or 'Power' in trap_name:
                            battery_related = True
                    else:
                        self.logger.warning(f"snmpTrapOID {snmp_trap_oid} not in UPS_OIDS dictionary (normalized: {normalized_trap_oid})")
                        # Even if not recognized, if it's an ATS OID, mark as battery-related
                        if snmp_trap_oid.startswith('1.3.6.1.4.1.37662'):
                            battery_related = True
                            self.logger.info(f"ATS trap OID detected (not in dictionary): {snmp_trap_oid} - treating as battery/power-related")
                        # Also check for legacy APC PowerNet MIB for backward compatibility
                        elif snmp_trap_oid.startswith('1.3.6.1.4.1.935'):
                            battery_related = True
                            self.logger.info(f"Legacy APC trap OID detected (not in dictionary): {snmp_trap_oid} - treating as battery/power-related")
            else:
                self.logger.warning("No variable bindings found in trap")
            
            # Debug: Log summary before final processing
            self.logger.debug(f"Trap Summary - OID: {trap_oid}, Source: {source_address}, Variables: {len(trap_vars)}, Battery-related: {battery_related}")
            
            # Log the trap
            self.log_trap(source_address, trap_oid, trap_vars, battery_related, contextName)
            
            self.logger.debug("=== Trap Processing Complete ===\n")
            
        except Exception as e:
            self.logger.error(f"Error processing trap: {e}", exc_info=True)
            self.logger.debug(f"Error context - ContextName: {contextName}, varBinds count: {len(varBinds) if varBinds else 0}")
    
    def format_snmp_value(self, value):
        """Format SNMP value for logging."""
        if isinstance(value, rfc1902.Integer):
            return int(value)
        elif isinstance(value, rfc1902.OctetString):
            return value.prettyPrint()
        elif isinstance(value, rfc1902.ObjectIdentifier):
            return str(value)
        elif isinstance(value, rfc1902.TimeTicks):
            return f"{int(value)} timeticks"
        elif isinstance(value, rfc1902.Counter32) or isinstance(value, rfc1902.Counter64):
            return int(value)
        elif isinstance(value, rfc1902.Gauge32):
            return int(value)
        else:
            return str(value)
    
    def log_trap(self, source_address: str, trap_oid: Optional[str], trap_vars: dict, battery_related: bool = False, contextName: Optional[str] = None):
        """
        Log trap information to file and console.
        
        Args:
            source_address: Source IP address and port
            trap_oid: Trap OID if known
            trap_vars: Dictionary of trap variables
            battery_related: Whether trap is battery-related
            contextName: SNMP context name
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Extract IP address from source_address (format: "IP:port")
        source_ip = source_address.split(':')[0] if ':' in source_address else source_address
        
        # Get UPS name and location based on source IP
        ups_name, ups_location = self._get_ups_info(source_ip)
        
        # Build log message
        log_lines = [
            f"{'='*80}",
            f"Timestamp: {timestamp}",
            f"Source: {source_address}",
        ]
        
        # Add context name if available
        if contextName:
            log_lines.append(f"Context Name: {contextName}")
        
        if trap_oid:
            trap_name = UPS_OIDS.get(trap_oid, 'Unknown')
            description = ALARM_DESCRIPTIONS.get(trap_name, 'No description available')
            event_type = ALARM_EVENT_TYPE.get(trap_name, 'unknown')
            severity = ALARM_SEVERITY.get(trap_name, 'info')
            event_type_label = {
                'trigger': '🔴 ALARM TRIGGERED',
                'resumption': '🟢 ALARM CLEARED/RESUMED',
                'state': 'ℹ️ STATE CHANGE',
                'unknown': '❓ UNKNOWN EVENT TYPE'
            }.get(event_type, '❓ UNKNOWN EVENT TYPE')
            
            # Severity label with emoji
            severity_label = {
                'critical': '🔴 CRITICAL',
                'warning': '🟡 WARNING',
                'info': 'ℹ️ INFO'
            }.get(severity, f'❓ {severity.upper()}')
            
            log_lines.extend([
                f"Trap OID: {trap_oid}",
                f"Trap Name: {trap_name}",
                f"Event Type: {event_type_label} ({event_type})",
                f"Severity: {severity_label} ({severity})",
                f"Description: {description}",
            ])
            
            # Add alarm/resumption mapping info if applicable
            if event_type == 'resumption':
                cleared_alarms = RESUMPTION_TO_ALARM_MAP.get(trap_name, [])
                if cleared_alarms:
                    log_lines.append(f"Clears Alarm(s): {', '.join(cleared_alarms)}")
            elif event_type == 'trigger':
                resumption = ALARM_RESUMPTION_MAP.get(trap_name)
                if resumption:
                    log_lines.append(f"Will be cleared by: {resumption}")
        else:
            trap_type = "Battery-Related SNMP Trap" if battery_related else "Unknown/Generic SNMP Trap"
            log_lines.append(f"Trap Type: {trap_type}")
            # Add severity for battery-related traps without recognized OID
            if battery_related:
                severity = 'warning'
                severity_label = '🟡 WARNING'
                log_lines.append(f"Severity: {severity_label} ({severity}) - Battery-related trap detected")
        
        # Add battery-related indicator if applicable
        if battery_related and not trap_oid:
            log_lines.append("Note: This trap appears to be battery-related based on OID patterns")
        
        log_lines.append("Variables:")
        for oid, value in trap_vars.items():
            # Try to identify battery capacity, temperature, etc. from variable names
            var_name = oid
            if 'battery' in oid.lower() or '1.3.6.1.2.1.33.1.2' in oid:
                var_name = f"{oid} [Battery Status]"
            log_lines.append(f"  {var_name}: {value}")
        
        log_lines.append(f"{'='*80}\n")
        
        log_message = "\n".join(log_lines)
        
        # Determine log level based on trap type
        if trap_oid:
            trap_name = UPS_OIDS.get(trap_oid, '')
            if 'Alarm' in trap_name or 'Fault' in trap_name or 'Failed' in trap_name:
                log_level = logging.CRITICAL
            elif 'OnBattery' in trap_name or 'BatteryLow' in trap_name or 'BatteryDischarged' in trap_name:
                log_level = logging.WARNING
            elif 'Battery' in trap_name:
                log_level = logging.WARNING
            else:
                log_level = logging.INFO
        elif battery_related:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO
        
        self.logger.log(log_level, log_message)
        
        # Send email notification if enabled, configured and this is an important trap
        if self.email_enabled and self.email_sender and self.email_recipients:
            self._send_email_notification(
                trap_oid=trap_oid,
                trap_vars=trap_vars,
                source_address=source_address,
                timestamp=timestamp,
                trap_name=UPS_OIDS.get(trap_oid, 'Unknown') if trap_oid else None,
                description=ALARM_DESCRIPTIONS.get(UPS_OIDS.get(trap_oid, ''), '') if trap_oid else None,
                battery_related=battery_related,
                ups_name=ups_name,
                ups_location=ups_location
            )
        else:
            # Log why email is not being sent
            if not self.email_enabled:
                self.logger.debug("Email notifications disabled (EMAIL_ENABLED = False in config.py)")
        
        # Send SMS notification if configured and this is an important trap
        if self.sms_enabled:
            self._send_sms_notification(
                trap_oid=trap_oid,
                trap_vars=trap_vars,
                source_address=source_address,
                timestamp=timestamp,
                trap_name=UPS_OIDS.get(trap_oid, 'Unknown') if trap_oid else None,
                description=ALARM_DESCRIPTIONS.get(UPS_OIDS.get(trap_oid, ''), '') if trap_oid else None,
                battery_related=battery_related,
                ups_name=ups_name,
                ups_location=ups_location
            )
        else:
            # Log why SMS is not being sent
            if not self.sms_enabled:
                self.logger.debug("SMS notifications disabled (SMS_ENABLED = False in config.py)")
            elif not self.sms_api_url:
                self.logger.debug("SMS API URL not configured")
            elif not self.sms_username:
                self.logger.debug("SMS username not configured")
            elif not self.sms_password:
                self.logger.debug("SMS password not configured")
            elif not self.sms_recipients:
                self.logger.debug("SMS recipients not configured")
        
        # Trigger GPIO LED if configured and this is an alarm
        if self.led_controller:
            self.logger.info(f"GPIO LED controller available, trap_oid: {trap_oid}, battery_related: {battery_related}")
            if trap_oid:
                trap_name = UPS_OIDS.get(trap_oid, None)
                self.logger.info(f"Trap name from OID: {trap_name}")
                if trap_name:
                    severity = ALARM_SEVERITY.get(trap_name, 'info')
                    event_type = ALARM_EVENT_TYPE.get(trap_name, 'unknown')
                    self.logger.info(f"Alarm severity: {severity}, Event type: {event_type}, GPIO pins: {self.gpio_pins}")
                    
                    # Handle resumption events (alarm clearing)
                    if event_type == 'resumption':
                        # Find which alarm(s) this resumption clears
                        cleared_alarms = RESUMPTION_TO_ALARM_MAP.get(trap_name, [])
                        if cleared_alarms:
                            self.logger.info(f"Resumption event '{trap_name}' clears alarm(s): {', '.join(cleared_alarms)}")
                        else:
                            # Some resumptions don't have explicit mappings but still clear alarms
                            # (e.g., powerRestored clears battery-related alarms)
                            if trap_name == 'powerRestored':
                                cleared_alarms = ['upsOnBattery']  # Power restored clears on-battery alarm
                            self.logger.info(f"Resumption event '{trap_name}' - clearing related alarms")
                        
                        try:
                            # Use RESUMPTION_TO_LED_MAP to disable red LED and enable green LED
                            if self.panel_led_controller:
                                led_action = RESUMPTION_TO_LED_MAP.get(trap_name)
                                if led_action:
                                    # Disable the red LED(s) (alarm LED)
                                    disable_led = led_action.get('disable_led')
                                    if disable_led:
                                        # Support both single LED and list of LEDs
                                        if isinstance(disable_led, list):
                                            for led in disable_led:
                                                self.panel_led_controller.disable_led(led)
                                                self.logger.info(f"Disabled LED {led} (red alarm LED) for resumption: {trap_name}")
                                        else:
                                            self.panel_led_controller.disable_led(disable_led)
                                            self.logger.info(f"Disabled LED {disable_led} (red alarm LED) for resumption: {trap_name}")
                                    
                                    # Enable the green LED(s) (normal status LED)
                                    enable_led = led_action.get('enable_led')
                                    if enable_led:
                                        # Support both single LED and list of LEDs
                                        if isinstance(enable_led, list):
                                            for led in enable_led:
                                                self.panel_led_controller.enable_led(led)
                                                self.logger.info(f"Enabled LED {led} (green normal LED) for resumption: {trap_name}")
                                        else:
                                            self.panel_led_controller.enable_led(enable_led)
                                            self.logger.info(f"Enabled LED {enable_led} (green normal LED) for resumption: {trap_name}")
                                else:
                                    # Fallback: disable LED based on cleared alarms
                                    if cleared_alarms:
                                        for cleared_alarm in cleared_alarms:
                                            cleared_led = ALARM_TO_LED_MAP.get(cleared_alarm)
                                            if cleared_led:
                                                self.panel_led_controller.disable_led(cleared_led)
                                                self.logger.info(f"Disabled LED {cleared_led} for cleared alarm: {cleared_alarm}")
                            
                            # Clear the LED for the cleared alarm(s) using existing GPIO controller
                            if cleared_alarms:
                                # Clear specific alarm severity if we can determine it
                                for cleared_alarm in cleared_alarms:
                                    cleared_severity = ALARM_SEVERITY.get(cleared_alarm, severity)
                                    if self.led_controller:
                                        self.led_controller.clear_alarm(cleared_severity)
                                    self.logger.info(f"GPIO LED cleared for '{cleared_alarm}' ({cleared_severity}) - resumption: {trap_name}")
                            else:
                                # Generic clear - clear all LEDs
                                if self.led_controller:
                                    self.led_controller.clear_alarm()
                                self.logger.info(f"GPIO LED cleared (all) - resumption: {trap_name}")
                        except Exception as e:
                            self.logger.error(f"Failed to clear GPIO LED: {e}", exc_info=True)
                    
                    # Handle trigger events (alarm starting)
                    elif event_type == 'trigger':
                        if severity in ['warning', 'critical']:
                            try:
                                # Use existing GPIO controller if available
                                if self.led_controller:
                                    self.led_controller.trigger_alarm(trap_name, severity)
                                    pin = self.gpio_pins.get(severity, 'unknown')
                                    self.logger.info(f"GPIO LED triggered on pin {pin} for {trap_name} ({severity}) - ALARM TRIGGERED")
                                
                                # Enable specific LED from AlarmMap based on alarm type
                                if self.panel_led_controller:
                                    led_action = ALARM_TO_LED_MAP.get(trap_name)
                                    if led_action:
                                        # Check if it's a dictionary (disable + enable) or just a number (enable only)
                                        if isinstance(led_action, dict):
                                            # Advanced format: disable LED(s) and enable LED(s)
                                            disable_led = led_action.get('disable_led')
                                            enable_led = led_action.get('enable_led')
                                            
                                            if disable_led:
                                                # Support both single LED and list of LEDs
                                                if isinstance(disable_led, list):
                                                    for led in disable_led:
                                                        self.panel_led_controller.disable_led(led)
                                                        self.logger.info(f"Disabled LED {led} for alarm: {trap_name} ({severity})")
                                                else:
                                                    self.panel_led_controller.disable_led(disable_led)
                                                    self.logger.info(f"Disabled LED {disable_led} for alarm: {trap_name} ({severity})")
                                            
                                            if enable_led:
                                                # Support both single LED and list of LEDs
                                                if isinstance(enable_led, list):
                                                    for led in enable_led:
                                                        self.panel_led_controller.enable_led(led)
                                                        self.logger.info(f"Enabled LED {led} for alarm: {trap_name} ({severity})")
                                                else:
                                                    self.panel_led_controller.enable_led(enable_led)
                                                    self.logger.info(f"Enabled LED {enable_led} for alarm: {trap_name} ({severity})")
                                        else:
                                            # Simple format: just enable the LED
                                            self.panel_led_controller.enable_led(led_action)
                                            self.logger.info(f"Enabled LED {led_action} for alarm: {trap_name} ({severity})")
                                    else:
                                        self.logger.debug(f"No LED mapping found for alarm: {trap_name} - using default LED 10")
                                        # Fallback: use LED 10 for unmapped critical alarms
                                        if severity == 'critical':
                                            if self.alarm_led_enabled:
                                                self.panel_led_controller.enable_led(10)
                                                self.logger.info(f"Enabled default LED 10 for unmapped critical alarm: {trap_name}")
                                            else:
                                                self.logger.info(f"Alarm LED disabled - LED 10 not enabled for unmapped critical alarm: {trap_name}")
                                        
                            except Exception as e:
                                self.logger.error(f"Failed to trigger GPIO LED: {e}", exc_info=True)
                        else:
                            self.logger.debug(f"Skipping LED trigger for {trap_name} (severity: {severity}, event_type: {event_type})")
                    
                    # Handle state events (informational)
                    elif event_type == 'state':
                        # Optional: Enable status LEDs for state changes (Source A/B active indicators)
                        if self.panel_led_controller:
                            # Source A active -> enable LED 6 (Source 1 is currently active - Green)
                            if trap_name == 'atsLoadOnSourceA':
                                self.panel_led_controller.enable_led(6)
                                self.panel_led_controller.disable_led(7)  # Disable Source B active
                                self.logger.info(f"Enabled LED 6 (Source A active) for state: {trap_name}")
                            # Source B active -> enable LED 7 (Source 2 is currently active - Green)
                            elif trap_name == 'atsLoadOnSourceB':
                                self.panel_led_controller.enable_led(7)
                                self.panel_led_controller.disable_led(6)  # Disable Source A active
                                self.logger.info(f"Enabled LED 7 (Source B active) for state: {trap_name}")
                        self.logger.debug(f"State event '{trap_name}' - LED action completed")
                    
                    # Fallback for unknown event types
                    else:
                        # Legacy behavior: trigger LED for warning/critical, clear for power restored
                        if trap_name == 'powerRestored':
                            self.logger.info("Utility power restored detected - clearing all LED alarms")
                            try:
                                if self.led_controller:
                                    self.led_controller.clear_alarm()
                                
                                # Disable all red LEDs and enable system OK LED
                                if self.panel_led_controller:
                                    # Disable common alarm LEDs
                                    self.panel_led_controller.disable_led(10)  # ALARM LED
                                    self.panel_led_controller.disable_led(11)  # LOAD Overload LED
                                    # Enable system OK LED
                                    self.panel_led_controller.enable_led(8)  # SYSTEM OK LED
                                    self.logger.info("Disabled alarm LEDs and enabled LED 8 (SYSTEM OK) - power restored")
                                
                                self.logger.info("GPIO LED cleared (turned OFF) - power restored")
                            except Exception as e:
                                self.logger.error(f"Failed to clear GPIO LED: {e}", exc_info=True)

                else:
                    self.logger.warning(f"Trap OID {trap_oid} not found in UPS_OIDS dictionary - LED not triggered")
                    self.logger.info(f"Available OIDs: {list(UPS_OIDS.keys())[:5]}...")  # Show first 5
            elif battery_related:
                # Even if trap_oid is not found, if it's battery-related, trigger warning LED
                self.logger.info("Battery-related trap detected but OID not recognized - triggering warning LED")
                try:
                    if self.led_controller:
                        self.led_controller.trigger_alarm('BatteryRelated', 'warning')
                        pin = self.gpio_pins.get('warning', self.gpio_pins.get('critical', 'unknown'))
                        self.logger.info(f"GPIO LED triggered on pin {pin} for battery-related trap (warning)")
                    
                    # Enable default alarm LED (LED 10) for battery-related alarm
                    if self.panel_led_controller:
                        if self.alarm_led_enabled:
                            self.panel_led_controller.enable_led(10)
                            self.logger.info("Enabled LED 10 (default alarm LED) for battery-related alarm")
                        else:
                            self.logger.info("Alarm LED disabled - LED 10 not enabled for battery-related alarm")
                        
                except Exception as e:
                    self.logger.error(f"Failed to trigger GPIO LED for battery trap: {e}", exc_info=True)
            else:
                self.logger.debug("No trap_oid found and not battery-related, cannot trigger GPIO LED")
        
        # Trigger sound alert if configured and this is an alarm
        if self.sound_controller:
            if trap_oid:
                trap_name = UPS_OIDS.get(trap_oid, None)
                if trap_name:
                    severity = ALARM_SEVERITY.get(trap_name, 'info')
                    event_type = ALARM_EVENT_TYPE.get(trap_name, 'unknown')
                    
                    # Only play sound for trigger events (alarm starting), not resumptions
                    if event_type == 'trigger' and severity in ['warning', 'critical']:
                        try:
                            self.sound_controller.trigger_alarm(trap_name, severity)
                            self.logger.info(f"Sound alert triggered for {trap_name} ({severity})")
                        except Exception as e:
                            self.logger.error(f"Failed to trigger sound alert: {e}", exc_info=True)
                    elif event_type == 'resumption':
                        # Optionally play a different sound for resumptions (success sound)
                        # For now, we don't play sound on resumption
                        self.logger.debug(f"Resumption event '{trap_name}' - no sound alert")
            elif battery_related:
                # Battery-related trap but OID not recognized - play warning sound
                try:
                    self.sound_controller.trigger_alarm('BatteryRelated', 'warning')
                    self.logger.info("Sound alert triggered for battery-related trap (warning)")
                except Exception as e:
                    self.logger.error(f"Failed to trigger sound alert for battery trap: {e}", exc_info=True)
        else:
            if self.gpio_pins:
                self.logger.warning("GPIO pins configured but LED controller not initialized - check for errors above")
            else:
                self.logger.debug("No GPIO pins configured, skipping LED trigger")
    
    def _send_email_notification(
        self,
        trap_oid: Optional[str],
        trap_vars: dict,
        source_address: str,
        timestamp: str,
        trap_name: Optional[str],
        description: Optional[str],
        battery_related: bool,
        ups_name: Optional[str] = None,
        ups_location: Optional[str] = None
    ):
        """
        Send email notification for important traps.
        
        Args:
            trap_oid: Trap OID
            trap_vars: Trap variables
            source_address: Source IP address
            timestamp: Timestamp string
            trap_name: Trap name
            description: Trap description
            battery_related: Whether trap is battery-related
            ups_name: UPS device name (if None, uses self.ups_name)
            ups_location: UPS device location (if None, uses self.ups_location)
        """
        # Check if email is properly configured
        if not self.email_enabled:
            self.logger.debug("Email notification skipped: Email is disabled")
            return
        if not self.email_sender:
            self.logger.warning("Email notification skipped: Email sender not configured")
            return
        if not self.email_recipients:
            self.logger.warning("Email notification skipped: Email recipients not configured")
            return
        
        # Use provided UPS info or fall back to defaults
        if ups_name is None:
            ups_name = self.ups_name
        if ups_location is None:
            ups_location = self.ups_location
        import time
        
        # Determine if this trap should trigger an email
        should_send = False
        severity = "INFO"
        color = "blue"
        
        # Check for specific important traps
        if trap_name:
            if 'OnBattery' in trap_name or 'BatteryLow' in trap_name or 'BatteryDischarged' in trap_name:
                should_send = True
                severity = "WARNING"
                color = "orange"
            elif 'Alarm' in trap_name or 'Fault' in trap_name or 'Failed' in trap_name:
                should_send = True
                severity = "CRITICAL"
                color = "red"
            elif 'Battery' in trap_name:
                should_send = True
                severity = "WARNING"
                color = "orange"
        
        # Also check for specific messages in trap variables
        for oid, value in trap_vars.items():
            value_str = str(value).lower()
            if 'utility power has been restored' in value_str or 'power has been restored' in value_str:
                should_send = True
                severity = "INFO"
                color = "green"
            elif 'switched to battery' in value_str or 'on battery power' in value_str:
                should_send = True
                severity = "WARNING"
                color = "orange"
        
        # Check if battery-related
        if battery_related and not should_send:
            should_send = True
            severity = "WARNING"
            color = "orange"
        
        if not should_send:
            return
        
        # Generate a unique trap key for cooldown tracking
        # Use trap_oid if available, otherwise create key from message content
        if trap_oid:
            trap_key = trap_oid
        else:
            # Create key from trap content to distinguish different trap types
            key_parts = []
            if trap_name:
                key_parts.append(trap_name)
            if battery_related:
                key_parts.append("battery")
            # Check for specific messages in variables
            for oid, value in trap_vars.items():
                value_str = str(value).lower()
                if 'utility power has been restored' in value_str:
                    key_parts.append("power_restored")
                    break
                elif 'switched to battery' in value_str or 'on battery power' in value_str:
                    key_parts.append("battery_power")
                    break
            trap_key = "_".join(key_parts) if key_parts else f"unknown_{battery_related}"
        
        # Cooldown check (5 minutes) to avoid duplicate emails
        current_time = time.time()
        last_time = self._last_email_times.get(trap_key, 0)
        cooldown = 300  # 5 minutes
        
        if current_time - last_time < cooldown:
            self.logger.debug(f"Email notification skipped (cooldown): {trap_name or trap_key}")
            return
        
        self._last_email_times[trap_key] = current_time
        
        # Build email subject and body
        ups_info = f"{ups_name}"
        if ups_location and ups_location != 'Unknown Location':
            ups_info = f"{ups_name} ({ups_location})"
        
        if trap_name:
            subject = f"UPS Alert [{ups_info}]: {trap_name}"
        elif battery_related:
            subject = f"UPS Alert [{ups_info}]: Battery-Related Trap"
        else:
            subject = f"UPS Alert [{ups_info}]: SNMP Trap Received"
        
        # Build plain text body
        body_lines = [
            f"UPS SNMP Trap Alert",
            f"",
            f"UPS Name: {ups_name}",
            f"UPS Location: {ups_location}",
            f"",
            f"Severity: {severity}",
            f"Timestamp: {timestamp}",
            f"Source: {source_address}",
        ]
        
        if trap_name:
            body_lines.append(f"Trap Name: {trap_name}")
        if description:
            body_lines.append(f"Description: {description}")
        if trap_oid:
            body_lines.append(f"Trap OID: {trap_oid}")
        
        body_lines.append("")
        body_lines.append("Trap Variables:")
        for oid, value in trap_vars.items():
            body_lines.append(f"  {oid}: {value}")
        
        body_lines.append("")
        body_lines.append("Please check your UPS system if necessary.")
        
        body = "\n".join(body_lines)
        
        # Build HTML body
        body_html = f"""
        <html>
            <body>
                <h2 style="color: {color};">UPS SNMP Trap Alert</h2>
                <table border="1" cellpadding="5" style="border-collapse: collapse;">
                    <tr><td><b>UPS Name:</b></td><td><b>{ups_name}</b></td></tr>
                    <tr><td><b>UPS Location:</b></td><td><b>{ups_location}</b></td></tr>
                    <tr><td><b>Severity:</b></td><td><b style="color: {color};">{severity}</b></td></tr>
                    <tr><td><b>Timestamp:</b></td><td>{timestamp}</td></tr>
                    <tr><td><b>Source:</b></td><td>{source_address}</td></tr>
        """
        
        if trap_name:
            body_html += f'<tr><td><b>Trap Name:</b></td><td>{trap_name}</td></tr>'
        if description:
            body_html += f'<tr><td><b>Description:</b></td><td>{description}</td></tr>'
        if trap_oid:
            body_html += f'<tr><td><b>Trap OID:</b></td><td>{trap_oid}</td></tr>'
        
        body_html += """
                </table>
                <h3>Trap Variables:</h3>
                <table border="1" cellpadding="5" style="border-collapse: collapse;">
        """
        
        for oid, value in trap_vars.items():
            body_html += f'<tr><td>{oid}</td><td>{value}</td></tr>'
        
        body_html += """
                </table>
                <p>Please check your UPS system if necessary.</p>
            </body>
        </html>
        """
        
        # Log email attempt to email log file
        self.email_logger.info("=" * 80)
        self.email_logger.info(f"EMAIL NOTIFICATION ATTEMPT")
        self.email_logger.info(f"Timestamp: {timestamp}")
        self.email_logger.info(f"UPS Name: {ups_name}")
        self.email_logger.info(f"UPS Location: {ups_location}")
        self.email_logger.info(f"Source: {source_address}")
        self.email_logger.info(f"Trap Name: {trap_name or 'Unknown'}")
        self.email_logger.info(f"Severity: {severity}")
        self.email_logger.info(f"Subject: {subject}")
        self.email_logger.info(f"Recipients: {', '.join(self.email_recipients)}")
        
        # Send email
        try:
            success = self.email_sender.send_email(
                to_emails=self.email_recipients,
                subject=subject,
                body=body,
                body_html=body_html
            )
            
            if success:
                self.logger.info(f"Email notification sent to {len(self.email_recipients)} recipient(s)")
                self.email_logger.info(f"RESULT: SUCCESS - Email sent to {len(self.email_recipients)} recipient(s)")
            else:
                self.logger.error("Failed to send email notification")
                self.email_logger.error("RESULT: FAILED - Email sending failed")
        except Exception as e:
            self.logger.error(f"Error sending email notification: {e}", exc_info=True)
            self.email_logger.error(f"RESULT: ERROR - {e}", exc_info=True)
        
        self.email_logger.info("=" * 80)
    
    def _send_sms_notification(
        self,
        trap_oid: Optional[str],
        trap_vars: dict,
        source_address: str,
        timestamp: str,
        trap_name: Optional[str],
        description: Optional[str],
        battery_related: bool,
        ups_name: Optional[str] = None,
        ups_location: Optional[str] = None
    ):
        """
        Send SMS notification for important traps.
        
        Args:
            trap_oid: Trap OID
            trap_vars: Trap variables
            source_address: Source IP address
            timestamp: Timestamp string
            trap_name: Trap name
            description: Trap description
            battery_related: Whether trap is battery-related
            ups_name: UPS device name (if None, uses self.ups_name)
            ups_location: UPS device location (if None, uses self.ups_location)
        """
        # Use provided UPS info or fall back to defaults
        if ups_name is None:
            ups_name = self.ups_name
        if ups_location is None:
            ups_location = self.ups_location
        # Check if SMS is properly configured
        if not self.sms_enabled:
            self.logger.debug("SMS notification skipped: SMS is disabled")
            return
        if not self.sms_api_url:
            self.logger.warning("SMS notification skipped: SMS API URL not configured")
            return
        if not self.sms_username:
            self.logger.warning("SMS notification skipped: SMS username not configured")
            return
        if not self.sms_password:
            self.logger.warning("SMS notification skipped: SMS password not configured")
            return
        
        # Get recipients for current time (time-based schedule or fallback to simple list)
        current_recipients = self._get_sms_recipients_for_current_time()
        if not current_recipients:
            # Check if schedule is configured or if simple list is empty
            if self.sms_schedule:
                self.logger.info("SMS notification skipped: No recipients configured for current time period")
            else:
                self.logger.warning("SMS notification skipped: SMS recipients not configured")
            return
        
        # Determine if this trap should trigger an SMS
        should_send = False
        severity = "INFO"
        
        # Log SMS evaluation
        self.logger.info(f"SMS Evaluation - Trap: '{trap_name or 'Unknown'}', Battery-related: {battery_related}")
        
        # Exclude test events from SMS notifications (these are routine tests, not actual alarms)
        test_events = {'upsTest', 'upsDiagnosticsPassed'}
        if trap_name in test_events:
            self.logger.info(f"  -> SMS notification skipped: '{trap_name}' is a test event (routine test, not an alarm)")
            return
        
        # Send SMS for all traps - check alarm severity from ALARM_SEVERITY mapping
        if trap_name:
            alarm_severity = ALARM_SEVERITY.get(trap_name, 'info')
            event_type = ALARM_EVENT_TYPE.get(trap_name, 'unknown')
            
            self.logger.info(f"  -> Alarm severity: {alarm_severity}, Event type: {event_type}")
            
            # Send SMS for all alarms regardless of severity (critical, warning, info) and all event types
            if event_type == 'trigger':
                should_send = True
                # Map severity to uppercase for SMS message
                if alarm_severity == 'critical':
                    severity = "CRITICAL"
                elif alarm_severity == 'warning':
                    severity = "WARNING"
                else:  # info or unknown
                    severity = "INFO"
                self.logger.info(f"  -> SMS trigger: {severity} alarm detected (severity: {alarm_severity})")
            elif event_type == 'resumption':
                # Send SMS for resumptions (alarm cleared) as well
                should_send = True
                # Preserve original severity for resumption events
                if alarm_severity == 'critical':
                    severity = "CRITICAL"
                elif alarm_severity == 'warning':
                    severity = "WARNING"
                else:
                    severity = "INFO"
                self.logger.info(f"  -> SMS trigger: Alarm resumption detected (alarm cleared) - {severity} severity")
            elif event_type == 'state':
                # Send SMS for state changes as well
                should_send = True
                severity = "INFO"
                self.logger.info(f"  -> SMS trigger: State change event detected")
            else:
                # Unknown event type - send SMS anyway
                should_send = True
                severity = "INFO"
                self.logger.info(f"  -> SMS trigger: Unknown event type '{event_type}' - sending SMS")
        
        # Also check for specific messages in trap variables (fallback)
        if not should_send:
            for oid, value in trap_vars.items():
                value_str = str(value).lower()
                if 'utility power has been restored' in value_str or 'power has been restored' in value_str:
                    should_send = True
                    severity = "INFO"
                    self.logger.info(f"  -> SMS trigger: Power restored message detected in trap variables")
                    break
                elif 'switched to battery' in value_str or 'on battery power' in value_str:
                    should_send = True
                    severity = "WARNING"
                    self.logger.info(f"  -> SMS trigger: Battery power message detected in trap variables")
                    break
        
        # Fallback: If trap_name is not recognized but trap exists, send SMS anyway
        if not trap_name and not should_send:
            # Unrecognized trap - send SMS if battery-related or if it's any trap
            should_send = True
            severity = "WARNING" if battery_related else "INFO"
            self.logger.info(f"  -> SMS trigger: Unrecognized trap detected (battery-related: {battery_related})")
        elif trap_name and not should_send:
            # Trap name exists but didn't match any criteria - send SMS anyway
            should_send = True
            severity = "INFO"
            self.logger.info(f"  -> SMS trigger: Trap '{trap_name}' detected (sending SMS for all traps)")
        
        # All traps should now trigger SMS - this check should rarely be needed
        if not should_send:
            self.logger.warning(f"SMS notification skipped: Trap '{trap_name or 'Unknown'}' - unexpected condition")
            return
        
        # Generate a unique trap key for cooldown tracking
        if trap_oid:
            trap_key = trap_oid
        else:
            key_parts = []
            if trap_name:
                key_parts.append(trap_name)
            if battery_related:
                key_parts.append("battery")
            trap_key = "_".join(key_parts) if key_parts else f"unknown_{battery_related}"
        
        # Cooldown check (5 minutes) to avoid duplicate SMS
        current_time = time.time()
        last_time = self._last_sms_times.get(trap_key, 0)
        cooldown = 300  # 5 minutes
        
        if current_time - last_time < cooldown:
            self.logger.debug(f"SMS notification skipped (cooldown): {trap_name or trap_key}")
            return
        
        self._last_sms_times[trap_key] = current_time
        
        # Build SMS message with UPS name and location
        # Format: <name> - <location> (name first, then location)
        if ups_location and ups_location != 'Unknown Location':
            if ups_name:
                ups_info = f"{ups_name} - {ups_location}"
            else:
                ups_info = f"Unknown - {ups_location}"
        else:
            ups_info = f"{ups_name}" if ups_name else "Unknown"
        
        if trap_name:
            sms_message = f"[{ups_info}] {trap_name}"
            if description:
                # Truncate description if too long (SMS has character limits)
                desc_short = description[:80] if len(description) > 80 else description
                sms_message = f"{sms_message} - {desc_short}"
        elif battery_related:
            sms_message = f"[{ups_info}] Battery-Related Trap"
        else:
            sms_message = f"[{ups_info}] SNMP Trap Received"
        
        # Add severity and timestamp (keep it short for SMS)
        sms_message = f"[{severity}] {sms_message} ({timestamp})"
        
        # Log SMS sending attempt to main logger and SMS logger
        from datetime import datetime
        current_time_str = datetime.now().strftime('%H:%M')
        schedule_info = f" (Time: {current_time_str})" if self.sms_schedule else ""
        
        self.logger.info("=" * 80)
        self.logger.info("SMS Notification - Attempting to send SMS")
        self.logger.info(f"  Trap Name: {trap_name or 'Unknown'}")
        self.logger.info(f"  Severity: {severity}")
        self.logger.info(f"  Message: {sms_message}")
        self.logger.info(f"  Recipients: {', '.join(current_recipients)}{schedule_info}")
        self.logger.info(f"  API URL: {self.sms_api_url}")
        
        # Log to SMS log file
        self.sms_logger.info("=" * 80)
        self.sms_logger.info(f"SMS NOTIFICATION ATTEMPT")
        self.sms_logger.info(f"Timestamp: {timestamp}")
        self.sms_logger.info(f"Current Time: {current_time_str}")
        self.sms_logger.info(f"UPS Name: {ups_name}")
        self.sms_logger.info(f"UPS Location: {ups_location}")
        self.sms_logger.info(f"Source: {source_address}")
        self.sms_logger.info(f"Trap Name: {trap_name or 'Unknown'}")
        self.sms_logger.info(f"Severity: {severity}")
        self.sms_logger.info(f"Message: {sms_message}")
        self.sms_logger.info(f"Recipients: {', '.join(current_recipients)}{schedule_info}")
        self.sms_logger.info(f"API URL: {self.sms_api_url}")
        
        # Send SMS to all recipients for current time period
        success_count = 0
        failed_recipients = []
        
        for recipient in current_recipients:
            try:
                # Build URL with parameters
                # Use urlencode which properly handles UTF-8 encoding for all parameters
                params = {
                    'destinatingAddress': recipient,
                    'username': self.sms_username,
                    'password': self.sms_password,
                    'SMS': sms_message,  # urlencode will handle UTF-8 encoding automatically
                    'type': str(self.sms_type),
                    'returnMode': str(self.sms_return_mode)
                }
                
                # Encode parameters using urlencode (handles UTF-8 encoding automatically)
                query_string = urllib.parse.urlencode(params, encoding='utf-8')
                full_url = f"{self.sms_api_url}?{query_string}"
                
                # Log SMS sending attempt (sanitize URL for security - hide password)
                sanitized_url = full_url.replace(self.sms_password, '***')
                self.logger.info(f"  Attempting to send SMS to {recipient}...")
                self.logger.debug(f"  Full URL (sanitized): {sanitized_url}")
                self.sms_logger.info(f"Attempting to send SMS to {recipient}...")
                self.sms_logger.debug(f"Full URL (sanitized): {sanitized_url}")
                
                # Send HTTP GET request
                with urllib.request.urlopen(full_url, timeout=10) as response:
                    # Get HTTP status code
                    status_code = response.getcode()
                    response_data = response.read().decode('utf-8')
                    
                    # Log detailed SMS sending result to both loggers
                    self.logger.info(f"  SMS to {recipient}:")
                    self.logger.info(f"    Status Code: {status_code}")
                    self.logger.info(f"    Response: {response_data}")
                    
                    self.sms_logger.info(f"SMS to {recipient}:")
                    self.sms_logger.info(f"  Status Code: {status_code}")
                    self.sms_logger.info(f"  Response: {response_data}")
                    
                    # Check if status code indicates success (200-299)
                    if 200 <= status_code < 300:
                        result_msg = f"SUCCESS - SMS sent to {recipient}"
                        self.logger.info(f"    Result: {result_msg}")
                        self.sms_logger.info(f"  Result: {result_msg}")
                        success_count += 1
                    else:
                        result_msg = f"FAILED - HTTP status {status_code} for {recipient}"
                        self.logger.warning(f"    Result: {result_msg}")
                        self.logger.warning(f"    Response: {response_data}")
                        self.sms_logger.warning(f"  Result: {result_msg}")
                        self.sms_logger.warning(f"  Response: {response_data}")
                        failed_recipients.append((recipient, f"HTTP {status_code}: {response_data}"))
                    
            except urllib.error.HTTPError as e:
                # HTTP error with status code
                status_code = e.code
                error_msg = str(e)
                try:
                    error_response = e.read().decode('utf-8')
                except:
                    error_response = "No response body"
                
                self.logger.error(f"  SMS to {recipient}:")
                self.logger.error(f"    Status Code: {status_code}")
                self.logger.error(f"    Error: {error_msg}")
                self.logger.error(f"    Response: {error_response}")
                self.logger.error(f"    Result: FAILED - HTTP error {status_code}")
                
                self.sms_logger.error(f"SMS to {recipient}:")
                self.sms_logger.error(f"  Status Code: {status_code}")
                self.sms_logger.error(f"  Error: {error_msg}")
                self.sms_logger.error(f"  Response: {error_response}")
                self.sms_logger.error(f"  Result: FAILED - HTTP error {status_code}")
                
                failed_recipients.append((recipient, f"HTTP {status_code}: {error_msg}"))
                
            except urllib.error.URLError as e:
                # URL/Network error
                error_msg = str(e)
                if hasattr(e, 'reason'):
                    error_msg += f" (Reason: {e.reason})"
                if hasattr(e, 'code'):
                    error_msg += f" (Code: {e.code})"
                
                self.logger.error(f"  SMS to {recipient}:")
                self.logger.error(f"    Error Type: URL/Network Error")
                self.logger.error(f"    Error: {error_msg}")
                self.logger.error(f"    Result: FAILED - Network/URL error")
                
                self.sms_logger.error(f"SMS to {recipient}:")
                self.sms_logger.error(f"  Error Type: URL/Network Error")
                self.sms_logger.error(f"  Error: {error_msg}")
                self.sms_logger.error(f"  Result: FAILED - Network/URL error")
                
                failed_recipients.append((recipient, f"Network Error: {error_msg}"))
                
            except Exception as e:
                # Other unexpected errors
                error_msg = str(e)
                self.logger.error(f"  SMS to {recipient}:")
                self.logger.error(f"    Error Type: Unexpected Error")
                self.logger.error(f"    Error: {error_msg}")
                self.logger.error(f"    Result: FAILED - Unexpected error", exc_info=True)
                
                self.sms_logger.error(f"SMS to {recipient}:")
                self.sms_logger.error(f"  Error Type: Unexpected Error")
                self.sms_logger.error(f"  Error: {error_msg}")
                self.sms_logger.error(f"  Result: FAILED - Unexpected error", exc_info=True)
                
                failed_recipients.append((recipient, f"Unexpected Error: {error_msg}"))
        
        # Log summary to both main logger and SMS logger
        self.logger.info("=" * 80)
        self.logger.info("SMS Notification Summary")
        self.logger.info(f"  Total Recipients (current time): {len(current_recipients)}")
        self.logger.info(f"  Successful: {success_count}")
        self.logger.info(f"  Failed: {len(failed_recipients)}")
        
        self.sms_logger.info("SMS Notification Summary")
        self.sms_logger.info(f"Total Recipients (current time): {len(current_recipients)}")
        self.sms_logger.info(f"Successful: {success_count}")
        self.sms_logger.info(f"Failed: {len(failed_recipients)}")
        
        if success_count > 0:
            status_msg = f"PARTIAL SUCCESS - {success_count}/{len(current_recipients)} SMS sent"
            self.logger.info(f"  Status: {status_msg}")
            self.sms_logger.info(f"RESULT: {status_msg}")
        else:
            status_msg = "FAILED - No SMS sent to any recipients"
            self.logger.error(f"  Status: {status_msg}")
            self.sms_logger.error(f"RESULT: {status_msg}")
        
        if failed_recipients:
            self.logger.warning("  Failed Recipients:")
            self.sms_logger.warning("Failed Recipients:")
            for recipient, error in failed_recipients:
                self.logger.warning(f"    - {recipient}: {error}")
                self.sms_logger.warning(f"  - {recipient}: {error}")
        
        self.logger.info("=" * 80)
        self.sms_logger.info("=" * 80)
    
    def _check_ups_status(self):
        """Check UPS status and log Source A and Source B status."""
        if not self.ups_status_checker:
            return
        
        try:
            # Detect device type
            device_type = None
            try:
                device_type = self.ups_status_checker.detect_device_type()
                self.logger.info(f"Detected device type: {device_type}")
            except Exception as e:
                self.logger.warning(f"Device type detection failed: {e}")
                # If detection fails, try to determine from sysObjectID
                try:
                    sys_oid = self.ups_status_checker.query_oid('1.3.6.1.2.1.1.2.0', try_without_zero=True)
                    if sys_oid:
                        sys_oid_str = str(sys_oid)
                        if '1.3.6.1.4.1.37662' in sys_oid_str:
                            device_type = 'ats'
                            self.logger.info(f"Device type determined from sysObjectID: {device_type}")
                        elif '1.3.6.1.4.1.935' in sys_oid_str or '1.3.6.1.2.1.33' in sys_oid_str:
                            device_type = 'ups'
                            self.logger.info(f"Device type determined from sysObjectID: {device_type}")
                except Exception as e2:
                    self.logger.debug(f"Could not determine device type from sysObjectID: {e2}")
            
            # Use detected device type - don't force 'ats' anymore
            # If device_type is still None, try 'ats' first (most common), then fallback to 'ups'
            if device_type is None:
                self.logger.warning("Device type is None, will try 'ats' first, then 'ups' if that fails")
                device_type = 'ats'  # Try ATS first as default
            
            # Get input status (Source A/B) and output status with timeout to prevent hanging
            input_status = None
            output_status = None
            status_error = None
            try:
                def _get_input():
                    nonlocal input_status, status_error, device_type
                    # Always try ATS first for input status (Source A/B) since that's what we need
                    # If device_type is 'ups', still try ATS to get Source A/B
                    try:
                        # Try ATS first to get Source A/B
                        input_status = self.ups_status_checker.get_input_status(device_type='ats')
                        if input_status and isinstance(input_status, dict):
                            # Check if we got valid Source A/B data
                            if 'source_a' in input_status or 'source_b' in input_status:
                                self.logger.debug("Successfully got input status as ATS (Source A/B found)")
                                device_type = 'ats'  # Update device_type if ATS worked
                            else:
                                # ATS query succeeded but no Source A/B - might be UPS, try UPS
                                self.logger.debug("ATS input status query succeeded but no Source A/B found, trying UPS...")
                                try:
                                    ups_input = self.ups_status_checker.get_input_status(device_type='ups')
                                    if ups_input and isinstance(ups_input, dict):
                                        input_status = ups_input
                                        self.logger.debug("Using UPS input status")
                                except:
                                    pass  # Keep ATS result even if it doesn't have Source A/B
                        else:
                            # ATS query failed or returned empty, try UPS
                            self.logger.debug("ATS input status query failed or empty, trying UPS...")
                            try:
                                input_status = self.ups_status_checker.get_input_status(device_type='ups')
                            except:
                                input_status = {}
                    except ValueError as ve:
                        # Handle parsing errors (e.g., empty string to int conversion)
                        status_error = f"ValueError in get_input_status: {ve}"
                        self.logger.debug(f"ValueError getting input status: {ve}")
                        # Try UPS as fallback
                        try:
                            input_status = self.ups_status_checker.get_input_status(device_type='ups')
                        except:
                            input_status = {}
                    except Exception as e:
                        status_error = f"Error getting input status: {e}"
                        self.logger.warning(f"Error getting input status: {e}")
                        # Try UPS as fallback
                        try:
                            input_status = self.ups_status_checker.get_input_status(device_type='ups')
                        except:
                            input_status = {}
                
                def _get_output():
                    nonlocal output_status, device_type
                    # Store original device_type to check if input thread found ATS
                    original_device_type = device_type
                    try:
                        output_status = self.ups_status_checker.get_output_status(device_type=device_type)
                        # Check if we got valid data - if not, try the other device type
                        if output_status and isinstance(output_status, dict):
                            # Check if we got "No Such Object" errors
                            output_source = output_status.get('source', '') or output_status.get('status', '')
                            if 'No Such Object' in str(output_source):
                                # ATS OIDs failed, try UPS
                                if device_type == 'ats':
                                    self.logger.info("ATS output status query returned 'No Such Object', trying UPS device type...")
                                    try:
                                        output_status = self.ups_status_checker.get_output_status(device_type='ups')
                                        if output_status and isinstance(output_status, dict):
                                            new_source = output_status.get('source', '') or output_status.get('status', '')
                                            if 'No Such Object' not in str(new_source):
                                                device_type = 'ups'
                                                self.logger.info(f"Successfully queried output status as UPS device type")
                                    except Exception as e2:
                                        self.logger.debug(f"Error trying UPS output status: {e2}")
                                # Check if output_source indicates UPS but device should be ATS
                                # UPS status values: 'onLine', 'onBattery', 'onBoost', etc.
                                # ATS status values: 'Source A', 'Source B', 'Bypass Source A', etc.
                                # If we got UPS status but need Source A/B, try ATS
                                output_source_check = output_status.get('source', '') or output_status.get('status', '')
                                if output_source_check and output_source_check.lower() in ['online', 'onbattery', 'onboost', 'onbypass', 'sleeping', 'rebooting', 'standby', 'onbuck']:
                                    # This looks like a UPS status - but if device is actually ATS, we need to query as ATS
                                    # Try ATS to see if we get Source A/B information
                                    self.logger.info(f"Output source '{output_source_check}' indicates UPS status, but trying ATS to get Source A/B...")
                                    try:
                                        ats_output = self.ups_status_checker.get_output_status(device_type='ats')
                                        if ats_output and isinstance(ats_output, dict):
                                            ats_source = ats_output.get('source', '')
                                            if ats_source and 'No Such Object' not in str(ats_source) and ats_source.lower() not in ['online', 'onbattery', 'onboost']:
                                                # Got valid ATS source (e.g., "Source A", "Source B")
                                                output_status = ats_output
                                                device_type = 'ats'
                                                self.logger.info(f"Successfully queried output status as ATS device type (source: {ats_source})")
                                            else:
                                                # ATS query didn't give us valid ATS source, keep UPS result
                                                self.logger.debug(f"ATS query returned '{ats_source}', keeping UPS result")
                                    except Exception as e2:
                                        self.logger.debug(f"Error trying ATS output status: {e2}")
                        else:
                            # Try fallback device type
                            if device_type == 'ats':
                                try:
                                    self.logger.info("Trying UPS device type as fallback...")
                                    output_status = self.ups_status_checker.get_output_status(device_type='ups')
                                    device_type = 'ups'
                                except:
                                    output_status = {}
                            elif device_type == 'ups':
                                try:
                                    self.logger.info("Trying ATS device type as fallback...")
                                    output_status = self.ups_status_checker.get_output_status(device_type='ats')
                                    device_type = 'ats'
                                except:
                                    output_status = {}
                            else:
                                output_status = {}
                    except Exception as e:
                        self.logger.debug(f"Error getting output status: {e}")
                        # Try fallback device type
                        if device_type == 'ats':
                            try:
                                self.logger.info("Trying UPS device type as fallback...")
                                output_status = self.ups_status_checker.get_output_status(device_type='ups')
                                device_type = 'ups'
                            except:
                                output_status = {}
                        elif device_type == 'ups':
                            try:
                                self.logger.info("Trying ATS device type as fallback...")
                                output_status = self.ups_status_checker.get_output_status(device_type='ats')
                                device_type = 'ats'
                            except:
                                output_status = {}
                        else:
                            output_status = {}
                
                # Get both input and output status in parallel
                input_thread = threading.Thread(target=_get_input, daemon=True)
                output_thread = threading.Thread(target=_get_output, daemon=True)
                
                input_thread.start()
                output_thread.start()
                
                input_thread.join(timeout=10.0)  # 10 second timeout
                output_thread.join(timeout=10.0)  # 10 second timeout
                
                if input_thread.is_alive():
                    self.logger.warning("get_input_status() timed out after 10 seconds")
                    
                    # Control LEDs on timeout: disable LEDs 2,3,4,6,7,8,9,11,12,13,14 and enable LED 10
                    if self.panel_led_controller:
                        try:
                            # Get previous LED 10 state to detect changes
                            previous_led_10_state = self._last_led_10_state
                            if previous_led_10_state is None:
                                try:
                                    previous_led_10_state = self.panel_led_controller.get_led_state(10)
                                except:
                                    previous_led_10_state = False
                            
                            # Disable LEDs: 2, 3, 4, 6, 7, 8, 9, 11, 12, 13, 14
                            leds_to_disable = [2, 3, 4, 6, 7, 8, 9, 11, 12, 13, 14]
                            for led in leds_to_disable:
                                self.panel_led_controller.disable_led(led)
                            
                            # Enable LED 10 (alarm LED) on timeout
                            self.panel_led_controller.enable_led(10)
                            self.logger.info(f"TIMEOUT detected - Disabled LEDs {leds_to_disable}, Enabled LED 10")
                            
                            # Update config.py only if LED 10 state changed
                            current_led_10_state = True
                            if previous_led_10_state is not None and previous_led_10_state != current_led_10_state:
                                # LED 10 changed from disabled to enabled -> ALARM_STATUS = True
                                self._update_alarm_status_config(True)
                                self.logger.info("TIMEOUT: LED 10 changed from disabled to enabled -> ALARM_STATUS = True")
                            elif previous_led_10_state is None:
                                # First time - update config
                                self._update_alarm_status_config(True)
                            
                            # Update tracked LED 10 state
                            self._last_led_10_state = current_led_10_state
                            
                            # Enable buzzer with beep pattern (LED 10 is enabled) - unless muted
                            # (Buzzer is enabled if LED 10 OR LED 11 is enabled)
                            if not self.buzzer_muted:
                                if hasattr(self.panel_led_controller, 'enable_buzzer'):
                                    self.panel_led_controller.enable_buzzer(
                                        continuous=True,
                                        beep_pattern=True,
                                        beep_duration=0.2,
                                        beep_pause=0.5,
                                        volume=75
                                    )
                                    self.logger.info("TIMEOUT detected - Buzzer enabled with beep pattern (volume: 75%, LED 10 enabled)")
                            else:
                                # Buzzer is muted - ensure it's disabled
                                if hasattr(self.panel_led_controller, 'disable_buzzer'):
                                    self.panel_led_controller.disable_buzzer()
                                self.logger.info("TIMEOUT detected - Buzzer is MUTED (alarm LED active, but no sound)")
                        except Exception as e:
                            self.logger.warning(f"Error controlling LEDs on timeout: {e}")
                    
                    # Log status check with timeout message
                    self.logger.info("=" * 80)
                    self.logger.info("UPS STATUS CHECK")
                    self.logger.info("-" * 80)
                    self.logger.info("Source A Status: TIMEOUT | Source B Status: TIMEOUT | Output Source: N/A | Output Current: N/A | Output Load: N/A")
                    self.logger.info("-" * 80)
                    return
                
            except Exception as e:
                self.logger.error(f"Error in status check thread: {e}", exc_info=True)
                # Log status check with error message
                self.logger.info("=" * 80)
                self.logger.info("UPS STATUS CHECK")
                self.logger.info("-" * 80)
                self.logger.info("Source A Status: ERROR | Source B Status: ERROR | Output Source: N/A | Output Current: N/A | Output Load: N/A")
                self.logger.info(f"Error: {e}")
                self.logger.info("-" * 80)
                return
            
            # Extract Source A and Source B status
            source_a_status = 'N/A'
            source_b_status = 'N/A'
            
            # Initialize output variables early to avoid UnboundLocalError
            output_source = 'N/A'
            output_current = 'N/A'
            output_load = 'N/A'
            output_load_percent = None  # Numeric value for LED control
            
            # Try to extract status even if input_status is empty or partial
            if input_status and isinstance(input_status, dict):
                # Check if input_status has ATS structure (source_a, source_b)
                if 'source_a' in input_status or 'source_b' in input_status:
                    # ATS structure: input_status has 'source_a' and 'source_b' dictionaries
                    device_type = 'ats'  # Update device_type since we have ATS structure
                    self.logger.debug("Input status has ATS structure (source_a/source_b), using device_type='ats'")
                    
                    if 'source_a' in input_status:
                        source_a = input_status['source_a']
                        if isinstance(source_a, dict):
                            # Get status, but handle None and empty string
                            raw_status = source_a.get('status')
                            if raw_status is None or (isinstance(raw_status, str) and not raw_status.strip()):
                                source_a_status = 'N/A'
                            else:
                                source_a_status = str(raw_status).strip()
                            self.logger.debug(f"Extracted Source A status: '{source_a_status}' (raw: {raw_status})")
                        else:
                            source_a_status = str(source_a).strip() if source_a else 'N/A'
                    else:
                        source_a_status = 'N/A'
                        self.logger.debug("Source A not found in input_status")
                    
                    if 'source_b' in input_status:
                        source_b = input_status['source_b']
                        if isinstance(source_b, dict):
                            # Get status, but handle None and empty string
                            raw_status = source_b.get('status')
                            if raw_status is None or (isinstance(raw_status, str) and not raw_status.strip()):
                                source_b_status = 'N/A'
                            else:
                                source_b_status = str(raw_status).strip()
                            self.logger.debug(f"Extracted Source B status: '{source_b_status}' (raw: {raw_status})")
                        else:
                            source_b_status = str(source_b).strip() if source_b else 'N/A'
                    else:
                        source_b_status = 'N/A'
                        self.logger.debug("Source B not found in input_status")
                else:
                    # UPS structure or fallback: try to get status directly
                    source_a_status = input_status.get('source_a_status', input_status.get('sourceA_status', 'N/A'))
                    source_b_status = input_status.get('source_b_status', input_status.get('sourceB_status', 'N/A'))
                    # Handle None and empty strings
                    if source_a_status is None or (isinstance(source_a_status, str) and not source_a_status.strip()):
                        source_a_status = 'N/A'
                    if source_b_status is None or (isinstance(source_b_status, str) and not source_b_status.strip()):
                        source_b_status = 'N/A'
                    if source_a_status == 'N/A' and source_b_status == 'N/A':
                        self.logger.debug("Input status does not have Source A/B structure - device might be UPS or ATS query failed")
            else:
                self.logger.debug(f"input_status is empty or not a dict: {input_status}")
            
            # If we got an error but still want to log, mark status accordingly
            if status_error and (source_a_status == 'N/A' and source_b_status == 'N/A'):
                # If we have an error and no status, log the error
                source_a_status = 'ERROR'
                source_b_status = 'ERROR'
            
            # Export UPS status to UPSState.txt file (only if we have valid status)
            # Skip export on timeout, ERROR, or if both statuses are N/A (no data available)
            should_export = not (
                source_a_status == 'TIMEOUT' or 
                source_a_status == 'ERROR' or 
                (source_a_status == 'N/A' and source_b_status == 'N/A' and output_source == 'N/A')
            )
            
            if should_export:
                try:
                    # Determine output file path (same directory as script)
                    script_dir = Path(__file__).parent
                    ups_state_file = script_dir / 'UPSState.txt'
                    
                    # Export status to file using GetUPSStatus's export method
                    if hasattr(self.ups_status_checker, 'export_to_ups_state_file'):
                        self.logger.debug(f"Attempting to export UPS status to {ups_state_file.absolute()}...")
                        try:
                            # Try to export using GetUPSStatus's method
                            # This will call get_all_status() which may fail if SNMP queries fail
                            export_success = self.ups_status_checker.export_to_ups_state_file(device_type=device_type, output_file=str(ups_state_file))
                            if export_success:
                                self.logger.info(f"UPS status exported successfully to {ups_state_file.absolute()}")
                            else:
                                # Export failed - log warning but don't treat as critical error
                                # This can happen if SNMP queries fail (e.g., "No Such Object" errors)
                                self.logger.warning(f"Failed to export UPS status to {ups_state_file.absolute()} (export method returned False - check if SNMP queries are working)")
                        except Exception as export_error:
                            # Log the full exception to understand what's failing
                            self.logger.error(f"Exception during UPS status export to {ups_state_file.absolute()}: {export_error}", exc_info=True)
                    else:
                        self.logger.debug("GetUPSStatus does not have export_to_ups_state_file method")
                except Exception as e:
                    self.logger.error(f"Error exporting UPS status to file: {e}", exc_info=True)
            else:
                self.logger.debug(f"Skipping UPS status export (source_a_status={source_a_status}, source_b_status={source_b_status}, output_source={output_source})")
            
            # Extract Output Source, Output Current, and Output Load
            # Note: These variables are already initialized above to avoid UnboundLocalError
            # Log the device type being used for output status extraction
            self.logger.debug(f"Extracting output status using device_type: {device_type}")
            
            # If we have Source A/B status but output_source is UPS status (e.g., "onLine"),
            # we should query output_status as ATS instead
            if (source_a_status != 'N/A' or source_b_status != 'N/A') and output_status:
                output_source_check = output_status.get('source', '') or output_status.get('status', '')
                if output_source_check and output_source_check.lower() in ['online', 'onbattery', 'onboost', 'onbypass', 'sleeping', 'rebooting', 'standby', 'onbuck']:
                    # We have Source A/B but output is UPS status - try to get ATS output status
                    self.logger.info(f"Have Source A/B status but output_source is '{output_source_check}' (UPS status), trying ATS output status...")
                    try:
                        ats_output = self.ups_status_checker.get_output_status(device_type='ats')
                        if ats_output and isinstance(ats_output, dict):
                            ats_source = ats_output.get('source', '')
                            if ats_source and 'No Such Object' not in str(ats_source) and ats_source.lower() not in ['online', 'onbattery', 'onboost']:
                                # Got valid ATS source
                                output_status = ats_output
                                device_type = 'ats'
                                self.logger.info(f"Updated to ATS device type (output source: {ats_source})")
                    except Exception as e:
                        self.logger.debug(f"Error trying ATS output status when we have Source A/B: {e}")
            
            if output_status and isinstance(output_status, dict):
                if device_type == 'ats':
                    # ATS structure
                    output_source = output_status.get('source', 'N/A')
                    output_current = output_status.get('current', 'N/A')
                    output_load = output_status.get('load', 'N/A')
                    # Try to get raw load value for percentage calculation
                    # ATS load may be in 0.1% units (e.g., 420 = 42.0%) OR already in percentage units (e.g., 25.0 = 25.0%)
                    output_load_raw = output_status.get('load_raw', None)
                    if output_load_raw is not None:
                        try:
                            load_raw_val = float(output_load_raw)
                            # Parse formatted load string to compare
                            load_from_string = None
                            try:
                                load_str = str(output_load).replace('%', '').strip()
                                load_from_string = float(load_str)
                            except (ValueError, TypeError):
                                pass
                            
                            # Determine if load_raw is already in percentage units or 0.1% units
                            # If load_raw matches the formatted string (within 0.1%), it's already in percentage units
                            # If load_raw >= 100, it's likely in 0.1% units and needs division by 10
                            if load_from_string is not None and abs(load_raw_val - load_from_string) < 0.1:
                                # load_raw already matches the formatted percentage, use it directly
                                output_load_percent = load_raw_val
                                self.logger.debug(f"ATS load_raw={load_raw_val} (matches formatted '{output_load}', using directly): {output_load_percent}%")
                            elif load_raw_val < 100:
                                # If raw value is less than 100, it's likely already in percentage units
                                output_load_percent = load_raw_val
                                self.logger.debug(f"ATS load_raw={load_raw_val} (<100, using as percentage): {output_load_percent}%")
                            else:
                                # ATS load is in 0.1% units (e.g., 420 = 42.0%), so divide by 10
                                output_load_percent = load_raw_val / 10.0
                                self.logger.debug(f"ATS load_raw={load_raw_val} (>=100, dividing by 10): {output_load_percent}%")
                        except (ValueError, TypeError) as e:
                            self.logger.debug(f"Failed to parse ATS load_raw '{output_load_raw}': {e}")
                            # Try to parse from formatted string (e.g., "45%")
                            try:
                                load_str = str(output_load).replace('%', '').strip()
                                output_load_percent = float(load_str)
                                self.logger.debug(f"Parsed ATS load from string '{output_load}': {output_load_percent}%")
                            except (ValueError, TypeError) as e2:
                                self.logger.debug(f"Failed to parse ATS load from string '{output_load}': {e2}")
                    else:
                        # No load_raw, try to parse from formatted string
                        try:
                            load_str = str(output_load).replace('%', '').strip()
                            output_load_percent = float(load_str)
                            self.logger.debug(f"Parsed ATS load from string (no load_raw): '{output_load}' -> {output_load_percent}%")
                        except (ValueError, TypeError) as e:
                            self.logger.debug(f"Failed to parse ATS load from string '{output_load}': {e}")
                else:
                    # UPS structure
                    output_source = output_status.get('status', 'N/A')
                    output_current = 'N/A'  # UPS may not have current in output status
                    output_load = output_status.get('load', 'N/A')
                    # Try to get raw load value for percentage calculation
                    output_load_raw = output_status.get('load_raw', None)
                    if output_load_raw is not None:
                        try:
                            output_load_percent = float(output_load_raw)
                            self.logger.debug(f"UPS load_raw={output_load_raw}, percent={output_load_percent}%")
                        except (ValueError, TypeError) as e:
                            self.logger.debug(f"Failed to parse UPS load_raw '{output_load_raw}': {e}")
                            # Try to parse from formatted string (e.g., "45%")
                            try:
                                load_str = str(output_load).replace('%', '').strip()
                                output_load_percent = float(load_str)
                                self.logger.debug(f"Parsed UPS load from string '{output_load}': {output_load_percent}%")
                            except (ValueError, TypeError) as e2:
                                self.logger.debug(f"Failed to parse UPS load from string '{output_load}': {e2}")
                    else:
                        # No load_raw, try to parse from formatted string
                        try:
                            load_str = str(output_load).replace('%', '').strip()
                            output_load_percent = float(load_str)
                            self.logger.debug(f"Parsed UPS load from string (no load_raw): '{output_load}' -> {output_load_percent}%")
                        except (ValueError, TypeError) as e:
                            self.logger.debug(f"Failed to parse UPS load from string '{output_load}': {e}")
            
            # Reorganized LED Control Logic based on UPS Status
            if self.panel_led_controller:
                try:
                    # Get current LED 10 state before changes (to detect state changes)
                    previous_led_10_state = self._last_led_10_state
                    if previous_led_10_state is None:
                        # First time - get current state
                        try:
                            previous_led_10_state = self.panel_led_controller.get_led_state(10)
                        except:
                            previous_led_10_state = False
                    
                    # Normalize status values for comparison
                    source_a_status_lower = str(source_a_status).lower().strip()
                    source_b_status_lower = str(source_b_status).lower().strip()
                    output_source_lower = str(output_source).lower().strip()
                    
                    # Check for timeout or both sources fail (highest priority - overrides everything)
                    is_timeout = (source_a_status_lower == 'timeout' or source_b_status_lower == 'timeout')
                    both_sources_fail = (source_a_status_lower == 'fail' and source_b_status_lower == 'fail')
                    
                    if is_timeout or both_sources_fail:
                        # Timeout OR both sources fail: disable LEDs 2,3,4,6,7,8,9,11,12,13,14 and enable LED 10
                        leds_to_disable = [2, 3, 4, 6, 7, 8, 9, 11, 12, 13, 14]
                        for led in leds_to_disable:
                            self.panel_led_controller.disable_led(led)
                        # Enable LED 10 (alarm LED)
                        self.panel_led_controller.enable_led(10)
                        self.logger.info(f"{'TIMEOUT' if is_timeout else 'Both sources fail'} - Disabled LEDs {leds_to_disable}, Enabled LED 10")
                    else:
                        # Normal operation - control LEDs based on status
                        
                        # 1. Control LEDs based on Source A Status
                        if source_a_status_lower == 'ok':
                            # Source A is ok: enable LED 2, 9
                            self.panel_led_controller.enable_led(2)
                            self.panel_led_controller.enable_led(9)
                            self.logger.debug(f"Source A Status: ok - Enabled LEDs 2, 9")
                        elif source_a_status_lower == 'fail':
                            # Source A is fail: disable LED 2, 3
                            self.panel_led_controller.disable_led(2)
                            self.panel_led_controller.disable_led(3)
                            self.logger.debug(f"Source A Status: fail - Disabled LEDs 2, 3")
                        
                        # 2. Control LEDs based on Source B Status
                        if source_b_status_lower == 'ok':
                            # Source B is ok: enable LED 4, 9
                            self.panel_led_controller.enable_led(4)
                            self.panel_led_controller.enable_led(9)
                            self.logger.debug(f"Source B Status: ok - Enabled LEDs 4, 9")
                        elif source_b_status_lower == 'fail':
                            # Source B is fail: disable LED 4, 3
                            self.panel_led_controller.disable_led(4)
                            self.panel_led_controller.disable_led(3)
                            self.logger.debug(f"Source B Status: fail - Disabled LEDs 4, 3")
                        
                        # 3. Control LED 10 based on Source A OR Source B fail
                        if source_a_status_lower == 'fail' or source_b_status_lower == 'fail':
                            # Source A OR Source B is fail: enable LED 10
                            self.panel_led_controller.enable_led(10)
                            self.logger.debug(f"Source A or Source B fail - Enabled LED 10")
                        
                        # 4. Control LED 3, 8, and 10 based on combined Source A and Source B status
                        if source_a_status_lower == 'ok' and source_b_status_lower == 'ok':
                            # Both sources are ok: enable LED 3, 8, disable LED 10
                            self.panel_led_controller.enable_led(3)
                            self.panel_led_controller.enable_led(8)
                            self.panel_led_controller.disable_led(10)
                            self.logger.debug(f"Both sources ok - Enabled LEDs 3, 8, Disabled LED 10")
                        
                        # 5. Control LEDs based on Output Source
                        if 'source a' in output_source_lower or output_source_lower == 'a':
                            # Output Source is Source A: enable LED 6, disable LED 7
                            self.panel_led_controller.enable_led(6)
                            self.panel_led_controller.disable_led(7)
                            self.logger.debug(f"Output Source: Source A - Enabled LED 6, Disabled LED 7")
                        elif 'source b' in output_source_lower or output_source_lower == 'b':
                            # Output Source is Source B: enable LED 7, disable LED 6
                            self.panel_led_controller.enable_led(7)
                            self.panel_led_controller.disable_led(6)
                            self.logger.debug(f"Output Source: Source B - Enabled LED 7, Disabled LED 6")
                        
                        # 6. Control LEDs based on Output Load percentage (using config.py thresholds)
                        self.logger.debug(f"[LED Control] output_load_percent={output_load_percent}, output_load={output_load}")
                        if output_load_percent is not None:
                            try:
                                # Parse load percentage to integer
                                load_int = int(output_load_percent)
                                self.logger.info(f"[LED Control] Load percentage: {output_load_percent}% -> integer: {load_int}")
                                
                                # Control LEDs based on load ranges from config.py
                                # L1: between L1_LOAD_MIN and L1_LOAD_MAX -> enable LED 14, disable 11,12,13
                                if self.l1_load_min <= load_int <= self.l1_load_max:
                                    self.panel_led_controller.enable_led(14)
                                    self.panel_led_controller.disable_led(11)
                                    self.panel_led_controller.disable_led(12)
                                    self.panel_led_controller.disable_led(13)
                                    self.logger.debug(f"Load {load_int}% (L1: {self.l1_load_min}-{self.l1_load_max}%): LED 14=ON, LED 11=OFF, LED 12=OFF, LED 13=OFF")
                                # L2: between L2_LOAD_MIN and L2_LOAD_MAX -> enable LED 13,14, disable 11,12
                                elif self.l2_load_min <= load_int <= self.l2_load_max:
                                    self.panel_led_controller.enable_led(13)
                                    self.panel_led_controller.enable_led(14)
                                    self.panel_led_controller.disable_led(11)
                                    self.panel_led_controller.disable_led(12)
                                    self.logger.debug(f"Load {load_int}% (L2: {self.l2_load_min}-{self.l2_load_max}%): LED 13=ON, LED 14=ON, LED 11=OFF, LED 12=OFF")
                                # L3: between L3_LOAD_MIN and L3_LOAD_MAX -> enable LED 12,13,14, disable 11
                                elif self.l3_load_min <= load_int <= self.l3_load_max:
                                    self.panel_led_controller.enable_led(12)
                                    self.panel_led_controller.enable_led(13)
                                    self.panel_led_controller.enable_led(14)
                                    self.panel_led_controller.disable_led(11)
                                    self.logger.debug(f"Load {load_int}% (L3: {self.l3_load_min}-{self.l3_load_max}%): LED 12=ON, LED 13=ON, LED 14=ON, LED 11=OFF")
                                # L4: >= L4_LOAD_THRESHOLD -> enable LED 11,12,13,14
                                elif load_int >= self.l4_load_threshold:
                                    self.panel_led_controller.enable_led(11)
                                    self.panel_led_controller.enable_led(12)
                                    self.panel_led_controller.enable_led(13)
                                    self.panel_led_controller.enable_led(14)
                                    self.logger.info(f"Load {load_int}% (L4: >={self.l4_load_threshold}%): Enabled LEDs 11, 12, 13, 14")
                                else:
                                    # Load outside all ranges: all load LEDs off (safety fallback)
                                    self.panel_led_controller.disable_led(14)
                                    self.panel_led_controller.disable_led(13)
                                    self.panel_led_controller.disable_led(12)
                                    self.panel_led_controller.disable_led(11)
                                    self.logger.debug(f"Load {load_int}%: All load LEDs OFF (outside valid range)")
                            except (ValueError, TypeError) as e:
                                self.logger.warning(f"Could not parse load percentage '{output_load_percent}': {e}")
                        else:
                            self.logger.warning(f"output_load_percent is None - cannot control load-based LEDs. output_load='{output_load}'")
                    
                    # 7. Control buzzer based on LED 10, LED 11, and LED 8 states
                    # This runs after all LED control to ensure buzzer state matches LED states
                    try:
                        led_10_state = self.panel_led_controller.get_led_state(10)
                        led_11_state = self.panel_led_controller.get_led_state(11)
                        led_8_state = self.panel_led_controller.get_led_state(8)
                        
                        # Buzzer control logic:
                        # - Enable buzzer if LED 10 OR LED 11 is enabled
                        # - Disable buzzer if LED 10 is disabled AND LED 8 is enabled
                        
                        if led_10_state is True or led_11_state is True:
                            # LED 10 OR LED 11 is enabled: enable buzzer with beep pattern (unless muted)
                            if not self.buzzer_muted:
                                if hasattr(self.panel_led_controller, 'enable_buzzer'):
                                    self.panel_led_controller.enable_buzzer(
                                        continuous=True,
                                        beep_pattern=True,
                                        beep_duration=0.2,
                                        beep_pause=0.5,
                                        volume=75
                                    )
                                    led_status = []
                                    if led_10_state is True:
                                        led_status.append("LED 10")
                                    if led_11_state is True:
                                        led_status.append("LED 11")
                                    self.logger.info(f"{' and '.join(led_status)} enabled - Buzzer enabled with beep pattern (volume: 75%)")
                            else:
                                # Buzzer is muted - ensure it's disabled
                                if hasattr(self.panel_led_controller, 'disable_buzzer'):
                                    self.panel_led_controller.disable_buzzer()
                                led_status = []
                                if led_10_state is True:
                                    led_status.append("LED 10")
                                if led_11_state is True:
                                    led_status.append("LED 11")
                                self.logger.info(f"{' and '.join(led_status)} enabled - Buzzer is MUTED (alarm LEDs active, but no sound)")
                        elif led_10_state is False and led_8_state is True:
                            # LED 10 is disabled AND LED 8 is enabled: disable buzzer
                            if hasattr(self.panel_led_controller, 'disable_buzzer'):
                                self.panel_led_controller.disable_buzzer()
                                self.logger.info("LED 10 disabled and LED 8 enabled - Buzzer disabled")
                        else:
                            # Other cases: disable buzzer (safety)
                            if hasattr(self.panel_led_controller, 'disable_buzzer'):
                                self.panel_led_controller.disable_buzzer()
                                self.logger.debug(f"Buzzer disabled (LED 10={led_10_state}, LED 11={led_11_state}, LED 8={led_8_state})")
                        
                        # 8. Update config.py based on LED 10 state changes (only when state changes)
                        if previous_led_10_state is not None and previous_led_10_state != led_10_state:
                            # LED 10 state changed
                            if led_10_state is True:
                                # LED 10 changed from disabled to enabled -> ALARM_STATUS = True
                                self._update_alarm_status_config(True)
                                self.logger.info("LED 10 changed from disabled to enabled -> ALARM_STATUS = True")
                            elif led_10_state is False:
                                # LED 10 changed from enabled to disabled -> ALARM_STATUS = False, BUZZER_MUTED = False
                                self._update_alarm_status_config(False)
                                self._update_buzzer_muted_config(False)
                                self.buzzer_muted = False
                                self.alarm_status = False
                                self.logger.info("LED 10 changed from enabled to disabled -> ALARM_STATUS = False, BUZZER_MUTED = False")
                        elif previous_led_10_state is None:
                            # First time - update config based on current state
                            if led_10_state is True:
                                self._update_alarm_status_config(True)
                            else:
                                self._update_alarm_status_config(False)
                                self._update_buzzer_muted_config(False)
                        
                        # Update tracked LED 10 state
                        self._last_led_10_state = led_10_state
                    except Exception as e:
                        self.logger.debug(f"Error controlling buzzer: {e}")
                except Exception as e:
                    self.logger.warning(f"Error controlling LEDs: {e}")
            
            # Log to file with INFO level - all in one line
            self.logger.info("=" * 80)
            self.logger.info("UPS STATUS CHECK")
            self.logger.info("-" * 80)
            self.logger.info(f"Source A Status: {source_a_status} | Source B Status: {source_b_status} | Output Source: {output_source} | Output Current: {output_current} | Output Load: {output_load}")
            if status_error:
                self.logger.info(f"Note: {status_error}")
            self.logger.info("-" * 80)
            
        except Exception as e:
            self.logger.error(f"Error in _check_ups_status: {e}", exc_info=True)
    
    def _update_buzzer_muted_config(self, new_value: bool) -> bool:
        """
        Update BUZZER_MUTED in config.py file.
        
        Args:
            new_value: New value for BUZZER_MUTED (True or False)
        
        Returns:
            True if update was successful, False otherwise
        """
        try:
            config_path = Path(__file__).parent / 'config.py'
            if not config_path.exists():
                self.logger.error(f"config.py not found at {config_path}")
                return False
            
            # Read current config file
            with open(config_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find and update BUZZER_MUTED line
            updated = False
            for i, line in enumerate(lines):
                if line.strip().startswith('BUZZER_MUTED'):
                    # Replace the line with new value
                    # Preserve comments if any
                    comment = ''
                    if '#' in line:
                        comment = ' ' + line.split('#', 1)[1].strip()
                    lines[i] = f"BUZZER_MUTED = {new_value}  # Updated by mute button{comment}\n"
                    updated = True
                    break
            
            if updated:
                # Write updated config back to file
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                self.logger.info(f"[BUTTON] Updated BUZZER_MUTED in config.py to {new_value} (file written successfully)")
                return True
            else:
                self.logger.warning(f"[BUTTON] Could not find BUZZER_MUTED in config.py at {config_path}")
                # Log all lines that start with BUZZER for debugging
                buzzer_lines = [line.strip() for line in lines if 'BUZZER' in line.upper()]
                self.logger.warning(f"[BUTTON] Found BUZZER-related lines: {buzzer_lines}")
                return False
                
        except Exception as e:
            self.logger.error(f"[BUTTON] Error updating BUZZER_MUTED in config.py: {e}", exc_info=True)
            import traceback
            self.logger.error(f"[BUTTON] Traceback: {traceback.format_exc()}")
            return False
    
    def _update_alarm_status_config(self, new_value: bool) -> bool:
        """
        Update ALARM_STATUS in config.py file.
        
        Args:
            new_value: New value for ALARM_STATUS (True or False)
        
        Returns:
            True if update was successful, False otherwise
        """
        try:
            config_path = Path(__file__).parent / 'config.py'
            if not config_path.exists():
                self.logger.error(f"config.py not found at {config_path}")
                return False
            
            # Read current config file
            with open(config_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find and update ALARM_STATUS line
            updated = False
            for i, line in enumerate(lines):
                if line.strip().startswith('ALARM_STATUS'):
                    # Replace the line with new value
                    # Preserve comments if any
                    comment = ''
                    if '#' in line:
                        comment = ' ' + line.split('#', 1)[1].strip()
                    lines[i] = f"ALARM_STATUS = {new_value}  # Updated automatically{comment}\n"
                    updated = True
                    break
            
            if updated:
                # Write updated config back to file
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                self.logger.info(f"Updated ALARM_STATUS in config.py to {new_value}")
                return True
            else:
                self.logger.warning("Could not find ALARM_STATUS in config.py")
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating ALARM_STATUS in config.py: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return False
    
    def _mute_button_callback(self, channel: int):
        """Callback function for mute button (GPIO interrupt, event-driven with GPIO.BOTH)."""
        # Print to stderr FIRST to ensure we see it even if logger fails
        print(f"[BUTTON-CALLBACK] Mute button callback triggered on GPIO {channel}", file=sys.stderr, flush=True)
        try:
            # Log that callback was triggered (for debugging) - use INFO level to ensure it's visible
            self.logger.info(f"[BUTTON] Mute button callback triggered on GPIO {channel}")
            # Force immediate flush to log file for button events
            for handler in self.logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.flush()
            
            current_time = time.time()
            
            # Read button state (LOW = pressed, HIGH = released)
            if not RPI_GPIO_AVAILABLE:
                self.logger.warning("[BUTTON] Mute button callback: RPi.GPIO not available")
                return
            
            button_state = GPIO.input(channel)
            is_pressed = (button_state == GPIO.LOW)
            
            self.logger.info(f"[BUTTON] Mute button state: {button_state} (LOW={GPIO.LOW}, HIGH={GPIO.HIGH}), is_pressed={is_pressed}")
            
            # Calculate time since last callback
            time_since_last = current_time - self.mute_button_last_callback_time
            
            # Only process if state actually changed from last known state
            # This prevents duplicate events from bouncing
            if self.mute_button_last_callback_state is not None:
                if self.mute_button_last_callback_state == is_pressed:
                    # State hasn't changed - this is likely a bounce or duplicate event
                    # Only ignore if it's very recent (within debounce window)
                    if time_since_last < self.mute_button_debounce_time:
                        self.logger.info(f"[BUTTON] Mute button: Ignoring duplicate state (time_since_last={time_since_last:.3f}s < {self.mute_button_debounce_time}s)")
                        return  # Ignore duplicate state within debounce window
                else:
                    self.logger.info(f"[BUTTON] Mute button state changed: {self.mute_button_last_callback_state} -> {is_pressed}")
            
            # State changed or first event - update tracking
            self.mute_button_last_callback_time = current_time
            self.mute_button_last_callback_state = is_pressed
            
            # Only process button press (LOW), not release (HIGH)
            if is_pressed:
                self.logger.info("[BUTTON] Mute button PRESSED detected - processing toggle...")
                # Force immediate flush to log file for button press
                for handler in self.logger.handlers:
                    if isinstance(handler, logging.FileHandler):
                        handler.flush()
                # Toggle BUZZER_MUTED
                old_value = self.buzzer_muted
                new_value = not old_value
                
                self.logger.info(f"[BUTTON] Mute button pressed - Toggling BUZZER_MUTED from {old_value} to {new_value}")
                
                # Update config.py
                self.logger.info(f"[BUTTON] Calling _update_buzzer_muted_config({new_value})...")
                update_success = self._update_buzzer_muted_config(new_value)
                self.logger.info(f"[BUTTON] Config update result: {update_success}")
                
                if update_success:
                    # Update internal state
                    self.buzzer_muted = new_value
                    self.mute_button_last_change_time = current_time
                    
                    self.logger.info(f"[BUTTON] Mute button pressed - BUZZER_MUTED changed from {old_value} to {new_value} (config.py updated successfully)")
                    
                    # Handle buzzer based on new mute state
                    if new_value:
                        # Muted (BUZZER_MUTED = True): disable buzzer
                        if self.panel_led_controller and hasattr(self.panel_led_controller, 'disable_buzzer'):
                            self.panel_led_controller.disable_buzzer()
                            self.logger.info("Buzzer disabled (muted)")
                    else:
                        # Unmuted (BUZZER_MUTED = False): 
                        # If BUZZER_MUTED changed from True to False (unmuting) AND ALARM_STATUS is True, enable buzzer
                        # Reload ALARM_STATUS from config to get latest value
                        try:
                            import importlib.util
                            config_path = Path(__file__).parent / 'config.py'
                            if config_path.exists():
                                spec = importlib.util.spec_from_file_location("ups_config", config_path)
                                ups_config = importlib.util.module_from_spec(spec)
                                spec.loader.exec_module(ups_config)
                                if hasattr(ups_config, 'ALARM_STATUS'):
                                    self.alarm_status = ups_config.ALARM_STATUS
                        except:
                            pass
                        
                        # Check if we're unmuting (changed from True to False) and alarm is active
                        if old_value and not new_value and self.alarm_status:
                            # Changed from muted (True) to unmuted (False) AND alarm is active
                            if self.panel_led_controller and hasattr(self.panel_led_controller, 'enable_buzzer'):
                                self.panel_led_controller.enable_buzzer(
                                    continuous=True,
                                    beep_pattern=True,
                                    beep_duration=0.2,
                                    beep_pause=0.5,
                                    volume=75
                                )
                                self.logger.info("Buzzer enabled (unmuted, ALARM_STATUS is True)")
                        else:
                            # Just unmuted but no alarm, or other state - ensure buzzer is off
                            if self.panel_led_controller and hasattr(self.panel_led_controller, 'disable_buzzer'):
                                self.panel_led_controller.disable_buzzer()
                                self.logger.debug(f"Buzzer disabled (unmuted but ALARM_STATUS={self.alarm_status})")
                else:
                    self.logger.error("[BUTTON] Failed to update BUZZER_MUTED in config.py - _update_buzzer_muted_config returned False")
            else:
                self.logger.info(f"[BUTTON] Mute button event: is_pressed={is_pressed} (release event, ignoring)")
                    
        except Exception as e:
            self.logger.error(f"[BUTTON] Error in mute button callback: {e}", exc_info=True)
            import traceback
            self.logger.error(f"[BUTTON] Traceback: {traceback.format_exc()}")
    
    def _reset_button_callback(self, channel: int):
        """Callback function for reset button (GPIO interrupt, event-driven with GPIO.BOTH)."""
        # Print to stderr FIRST to ensure we see it even if logger fails
        print(f"[BUTTON-CALLBACK] Reset button callback triggered on GPIO {channel}", file=sys.stderr, flush=True)
        try:
            current_time = time.time()
            
            # Read button state (LOW = pressed, HIGH = released)
            if not RPI_GPIO_AVAILABLE:
                return
            
            button_state = GPIO.input(channel)
            is_pressed = (button_state == GPIO.LOW)
            
            # Calculate time since last callback
            time_since_last = current_time - self.reset_button_last_callback_time
            
            # Only process if state actually changed from last known state
            # This prevents duplicate events from bouncing
            if self.reset_button_last_callback_state is not None:
                if self.reset_button_last_callback_state == is_pressed:
                    # State hasn't changed - this is likely a bounce or duplicate event
                    # Only ignore if it's very recent (within debounce window)
                    if time_since_last < self.reset_button_debounce_time:
                        return  # Ignore duplicate state within debounce window
            
            # State changed or first event - update tracking
            self.reset_button_last_callback_time = current_time
            self.reset_button_last_callback_state = is_pressed
            
            # Only process button press (LOW), not release (HIGH)
            if is_pressed:
                self.reset_button_last_change_time = current_time
                self.logger.info("Reset button pressed (functionality to be implemented)")
                # TODO: Implement reset functionality
                
        except Exception as e:
            self.logger.error(f"Error in reset button callback: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
    
    def _mute_button_monitor_thread(self):
        """Background thread to monitor mute button (GPIO 19) and reset button (GPIO 21) (event-driven with GPIO.BOTH + polling fallback)."""
        if not RPI_GPIO_AVAILABLE:
            self.logger.warning("[BUTTON] RPi.GPIO not available - mute button monitoring disabled")
            return
        
        if GPIO is None:
            self.logger.error("[BUTTON] GPIO module is None - mute button monitoring disabled")
            return
        
        self.logger.info(f"[BUTTON] Starting mute button monitor thread for GPIO {self.mute_button_pin}")
        
        # Verify GPIO module is actually functional and check current mode
        current_gpio_mode = None
        try:
            current_gpio_mode = GPIO.getmode()
            # GPIO.BCM = 10, GPIO.BOARD = 11
            if current_gpio_mode == GPIO.BCM:
                mode_name = "BCM"
            elif current_gpio_mode == GPIO.BOARD:
                mode_name = "BOARD"
            else:
                mode_name = "UNKNOWN"
            self.logger.info(f"[BUTTON] Current GPIO mode: {current_gpio_mode} ({mode_name})")
        except Exception as e:
            self.logger.warning(f"[BUTTON] Could not read GPIO mode: {e}")
        
        try:
            # Remove any existing event detection first (same as test program)
            try:
                GPIO.remove_event_detect(self.mute_button_pin)
                self.logger.info(f"[BUTTON] Removed existing event detection on GPIO {self.mute_button_pin}")
            except:
                pass
            
            # Reset callback state tracking (same as test program)
            self.mute_button_last_callback_time = 0
            self.mute_button_last_callback_state = None
            
            # Setup GPIO pin for mute button
            # CRITICAL: GPIO mode must be BCM for button pins 19 and 21 to work correctly
            # In BOARD mode, pin 19 = physical pin 19 (BCM GPIO 10), pin 21 = physical pin 21 (BCM GPIO 9)
            # We need BCM GPIO 19 (physical pin 35) and GPIO 21 (physical pin 40)
            if current_gpio_mode is None:
                try:
                    GPIO.setmode(GPIO.BCM)
                    GPIO.setwarnings(False)
                    self.logger.info(f"[BUTTON] GPIO mode set to BCM (was not set)")
                    current_gpio_mode = GPIO.BCM
                except RuntimeError as e:
                    self.logger.error(f"[BUTTON] CRITICAL: Failed to set GPIO mode to BCM: {e}")
                    self.logger.error(f"[BUTTON] Button monitoring will not work correctly!")
                    raise  # Stop thread initialization
            elif current_gpio_mode == GPIO.BOARD:
                # GPIO mode is BOARD - this is a CRITICAL problem!
                # We need to convert pin numbers or fail
                self.logger.error(f"[BUTTON] CRITICAL: GPIO mode is BOARD, but button pins are configured for BCM mode!")
                self.logger.error(f"[BUTTON] In BOARD mode, pin {self.mute_button_pin} = physical pin {self.mute_button_pin} (BCM GPIO 10)")
                self.logger.error(f"[BUTTON] We need BCM GPIO {self.mute_button_pin} = physical pin 35 in BOARD mode")
                self.logger.error(f"[BUTTON] SOLUTION: Ensure panel_led_controller initializes with BCM mode BEFORE button threads start")
                self.logger.error(f"[BUTTON] Button monitoring DISABLED - GPIO mode conflict!")
                GPIO.setwarnings(False)
                return  # Exit thread - buttons won't work with BOARD mode
            else:
                # GPIO mode is BCM - correct!
                GPIO.setwarnings(False)
                self.logger.info(f"[BUTTON] GPIO mode is BCM - button pin {self.mute_button_pin} is correct for BCM mode.")
            
            # Remove any existing event detection and cleanup pin first (Mute button)
            try:
                GPIO.remove_event_detect(self.mute_button_pin)
                self.logger.debug(f"[BUTTON] Removed existing event detection on GPIO {self.mute_button_pin}")
            except:
                pass
            
            # Remove any existing event detection and cleanup pin first (Reset button)
            try:
                GPIO.remove_event_detect(self.reset_button_pin)
                self.logger.debug(f"[BUTTON] Removed existing event detection on GPIO {self.reset_button_pin}")
            except:
                pass
            
            # Try to cleanup and reconfigure the pin to ensure it's in the correct state (Mute button)
            try:
                # Note: GPIO.cleanup(pin) doesn't exist, but we can try to setup the pin fresh
                # If pin is already configured, GPIO.setup will reconfigure it
                GPIO.setup(self.mute_button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                self.logger.info(f"[BUTTON] GPIO {self.mute_button_pin} (Mute) configured as input with pull-up")
            except Exception as e:
                self.logger.error(f"[BUTTON] Failed to setup GPIO {self.mute_button_pin} (Mute) as input: {e}", exc_info=True)
                raise  # Re-raise to stop thread initialization
            
            # Setup reset button GPIO pin
            try:
                GPIO.setup(self.reset_button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                self.logger.info(f"[BUTTON] GPIO {self.reset_button_pin} (Reset) configured as input with pull-up")
            except Exception as e:
                self.logger.error(f"[BUTTON] Failed to setup GPIO {self.reset_button_pin} (Reset) as input: {e}", exc_info=True)
                raise  # Re-raise to stop thread initialization
            
            # Initialize button state to current physical state (same as test program) - Mute button
            init_time = time.time()
            self.mute_button_last_state = GPIO.input(self.mute_button_pin)
            is_pressed_initial = (self.mute_button_last_state == GPIO.LOW)
            self.mute_button_last_callback_state = is_pressed_initial
            self.mute_button_last_callback_time = init_time - (self.mute_button_debounce_time * 2)
            
            self.logger.info(f"[BUTTON] Initial mute button state: {self.mute_button_last_state} (LOW={GPIO.LOW}, HIGH={GPIO.HIGH})")
            self.logger.info(f"[BUTTON] Initial mute callback state (is_pressed): {is_pressed_initial}")
            self.logger.info(f"[BUTTON] Debounce time: {self.mute_button_debounce_time}s ({int(self.mute_button_debounce_time * 1000)}ms)")
            
            # Initialize reset button state
            self.reset_button_last_state = GPIO.input(self.reset_button_pin)
            is_pressed_initial_reset = (self.reset_button_last_state == GPIO.LOW)
            self.reset_button_last_callback_state = is_pressed_initial_reset
            self.reset_button_last_callback_time = init_time - (self.reset_button_debounce_time * 2)
            
            self.logger.info(f"[BUTTON] Initial reset button state: {self.reset_button_last_state} (LOW={GPIO.LOW}, HIGH={GPIO.HIGH})")
            self.logger.info(f"[BUTTON] Initial reset callback state (is_pressed): {is_pressed_initial_reset}")
            
            # Test GPIO read to verify it's working
            test_read = GPIO.input(self.mute_button_pin)
            self.logger.info(f"[BUTTON] Test GPIO read: {test_read} (should be {GPIO.HIGH} if button not pressed)")
            
            # Additional hardware test: read pin multiple times to verify it's stable
            test_reads = [GPIO.input(self.mute_button_pin) for _ in range(5)]
            self.logger.info(f"[BUTTON] Hardware test - 5 consecutive reads: {test_reads} (all should be {GPIO.HIGH} if button not pressed)")
            
            # Verify GPIO constants
            self.logger.info(f"[BUTTON] GPIO constants: LOW={GPIO.LOW}, HIGH={GPIO.HIGH}, IN={GPIO.IN}, PUD_UP={GPIO.PUD_UP}")
            
            # Create standalone callback function inside thread (not a method) - matches test program pattern
            # This captures 'self' in a closure, making it a regular function from RPi.GPIO's perspective
            def mute_button_callback_wrapper(channel: int):
                """Standalone callback wrapper that calls the instance method."""
                try:
                    self._mute_button_callback(channel)
                except Exception as e:
                    self.logger.error(f"[BUTTON] Error in mute button callback wrapper: {e}", exc_info=True)
            
            # Setup interrupt callback with debouncing (GPIO.BOTH for event-driven approach)
            # Use standalone function like test program (not a method) to ensure proper binding
            GPIO.add_event_detect(
                self.mute_button_pin,
                GPIO.BOTH,  # Detect both rising and falling edges (event-driven)
                callback=mute_button_callback_wrapper,  # Standalone function (not method) like test program
                bouncetime=int(self.mute_button_debounce_time * 1000)  # Convert to milliseconds (10ms)
            )
            
            # Verify event detection was registered
            try:
                # Check if event detection is active (this is a read-only check)
                # RPi.GPIO doesn't provide a direct way to check, but we can verify the pin is set up correctly
                pin_state = GPIO.input(self.mute_button_pin)
                self.logger.info(f"[BUTTON] Mute button monitoring started on GPIO {self.mute_button_pin} (event-driven, GPIO.BOTH, bouncetime={int(self.mute_button_debounce_time * 1000)}ms)")
                self.logger.info(f"[BUTTON] Event detection registered - current pin state: {pin_state} (LOW={GPIO.LOW}, HIGH={GPIO.HIGH})")
            except Exception as e:
                self.logger.warning(f"[BUTTON] Could not verify event detection registration: {e}")
            
            # Keep thread alive and use hybrid approach: event detection + polling fallback
            # Polling fallback ensures we catch button presses even if event detection fails
            # CRITICAL: Use very short poll interval and explicit thread yielding to ensure
            # we catch button presses even when other threads are blocking
            last_poll_time = time.time()
            last_state = self.mute_button_last_state
            last_state_reset = self.reset_button_last_state
            poll_interval = 0.005  # Poll every 5ms (faster than debounce time for better responsiveness)
            consecutive_same_state_count = 0  # Track how many times we've seen the same state
            consecutive_same_state_count_reset = 0  # Track reset button state
            consecutive_gpio_errors = 0  # Track consecutive GPIO read errors
            last_successful_read_time = time.time()  # Track when we last successfully read GPIO
            
            self.logger.info(f"[BUTTON] Starting polling loop for GPIO {self.mute_button_pin} (Mute) and GPIO {self.reset_button_pin} (Reset) (poll_interval={poll_interval}s)")
            self.logger.info(f"[BUTTON] Initial states - Mute: {last_state}, Reset: {last_state_reset}")
            
            while self.mute_button_running and not self._shutdown_requested:
                # Use shorter sleep and explicit yield to ensure we get CPU time
                time.sleep(poll_interval)
                # Explicitly yield to other threads to prevent blocking
                threading.Event().wait(0)  # Yield to other threads
                # CRITICAL: Force GIL release by doing I/O operation
                # This ensures we get CPU time even when asyncio event loop is blocking
                try:
                    # Force a context switch by accessing thread state
                    _ = threading.current_thread().ident
                    # Small I/O operation to force GIL release
                    import sys
                    sys.stdout.flush()  # This forces GIL release
                except:
                    pass  # Ignore errors in yielding mechanism
                
                # Health check: If we haven't successfully read GPIO in 10 seconds, something is wrong
                if time.time() - last_successful_read_time > 10.0:
                    import sys
                    print(f"[BUTTON-WARNING] No successful GPIO read in 10 seconds! Last successful: {last_successful_read_time:.2f}, Current: {time.time():.2f}", file=sys.stderr, flush=True)
                    self.logger.warning(f"[BUTTON-WARNING] No successful GPIO read in 10 seconds! Attempting recovery...")
                    # Try to recover by re-initializing GPIO
                    try:
                        GPIO.remove_event_detect(self.mute_button_pin)
                        GPIO.setup(self.mute_button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                        GPIO.add_event_detect(
                            self.mute_button_pin,
                            GPIO.BOTH,
                            callback=mute_button_callback_wrapper,
                            bouncetime=int(self.mute_button_debounce_time * 1000)
                        )
                        # Test read
                        test_read = GPIO.input(self.mute_button_pin)
                        last_successful_read_time = time.time()
                        consecutive_gpio_errors = 0
                        self.logger.info(f"[BUTTON] GPIO recovery successful, test read: {test_read}")
                    except Exception as recovery_error:
                        self.logger.error(f"[BUTTON] GPIO recovery failed: {recovery_error}", exc_info=True)
                
                # Polling fallback: manually check button state and trigger callback if changed
                # This ensures we catch button presses even if event detection isn't working
                try:
                    # ========== MUTE BUTTON MONITORING ==========
                    # Read GPIO pin multiple times rapidly to catch brief button presses
                    # This helps catch very brief presses that might be missed by single reads
                    rapid_reads = []
                    try:
                        for _ in range(3):  # Read 3 times rapidly
                            rapid_reads.append(GPIO.input(self.mute_button_pin))
                        # Successfully read GPIO - update tracking
                        last_successful_read_time = time.time()
                        consecutive_gpio_errors = 0
                    except Exception as gpio_read_error:
                        # If GPIO read fails, log it and try to recover
                        consecutive_gpio_errors += 1
                        import sys
                        if consecutive_gpio_errors <= 3:  # Only log first few errors to avoid spam
                            print(f"[BUTTON-ERROR] GPIO read failed for pin {self.mute_button_pin} (error #{consecutive_gpio_errors}): {gpio_read_error}", file=sys.stderr, flush=True)
                            self.logger.error(f"[BUTTON-ERROR] GPIO read failed for pin {self.mute_button_pin} (error #{consecutive_gpio_errors}): {gpio_read_error}")
                        # Try to recover by re-reading once
                        recovery_attempted = False
                        try:
                            rapid_reads = [GPIO.input(self.mute_button_pin) for _ in range(3)]
                            last_successful_read_time = time.time()
                            errors_before_recovery = consecutive_gpio_errors
                            consecutive_gpio_errors = 0
                            recovery_attempted = True
                            if errors_before_recovery > 0:
                                self.logger.info(f"[BUTTON] GPIO read recovery successful after {errors_before_recovery} errors")
                        except:
                            # If recovery fails, use last known state and continue
                            if consecutive_gpio_errors == 1:  # Only log first failure
                                self.logger.warning(f"[BUTTON] GPIO read recovery failed, using last known state: {last_state}")
                            rapid_reads = [last_state, last_state, last_state]
                    # Use majority vote (2 out of 3) to determine state - more reliable than "any LOW"
                    low_count = rapid_reads.count(GPIO.LOW)
                    high_count = rapid_reads.count(GPIO.HIGH)
                    if low_count >= 2:
                        current_state = GPIO.LOW  # At least 2 reads show LOW, button is pressed
                    else:
                        current_state = GPIO.HIGH  # At least 2 reads show HIGH, button is not pressed
                    is_pressed_now = (current_state == GPIO.LOW)
                    
                    # CRITICAL DEBUGGING: Only log on state changes or when readings are unstable
                    if current_state != last_state or len(set(rapid_reads)) > 1:
                        # State changed or readings are unstable - log for debugging
                        if current_state != last_state:
                            self.logger.info(f"[BUTTON-DEBUG] GPIO {self.mute_button_pin} STATE CHANGE: rapid_reads={rapid_reads} (LOW={low_count}, HIGH={high_count}), current_state={current_state}, last_state={last_state}")
                        elif len(set(rapid_reads)) > 1:
                            # Readings are unstable but state hasn't changed yet - might be transitioning
                            self.logger.warning(f"[BUTTON-DEBUG] GPIO {self.mute_button_pin} UNSTABLE: rapid_reads={rapid_reads} (LOW={low_count}, HIGH={high_count}), current_state={current_state}, last_state={last_state}")
                        # Force immediate flush
                        for handler in self.logger.handlers:
                            if isinstance(handler, logging.FileHandler):
                                handler.flush()
                    
                    # Check if state changed (polling fallback)
                    if current_state != last_state:
                        # State changed - trigger callback manually (polling fallback)
                        # CRITICAL: Log immediately to stderr for immediate visibility
                        import sys
                        print(f"[BUTTON-PRESS] MUTE BUTTON STATE CHANGE DETECTED: GPIO {self.mute_button_pin} {last_state} -> {current_state} (pressed={is_pressed_now})", file=sys.stderr, flush=True)
                        self.logger.error(f"[BUTTON-PRESS] MUTE BUTTON STATE CHANGE DETECTED: GPIO {self.mute_button_pin} {last_state} -> {current_state} (pressed={is_pressed_now}, consecutive_same={consecutive_same_state_count})")
                        # Force immediate flush to log file for button events
                        for handler in self.logger.handlers:
                            if isinstance(handler, logging.FileHandler):
                                handler.flush()
                        consecutive_same_state_count = 0
                        # IMPORTANT: Update last_state BEFORE calling callback to prevent missing rapid presses
                        last_state = current_state
                        try:
                            print(f"[BUTTON-PRESS] Calling mute_button_callback_wrapper({self.mute_button_pin})...", file=sys.stderr, flush=True)
                            self.logger.error(f"[BUTTON-PRESS] Calling mute_button_callback_wrapper({self.mute_button_pin})...")
                            for handler in self.logger.handlers:
                                if isinstance(handler, logging.FileHandler):
                                    handler.flush()
                            mute_button_callback_wrapper(self.mute_button_pin)
                            print(f"[BUTTON-PRESS] mute_button_callback_wrapper completed", file=sys.stderr, flush=True)
                            self.logger.error(f"[BUTTON-PRESS] mute_button_callback_wrapper completed")
                            # Force immediate flush after callback
                            for handler in self.logger.handlers:
                                if isinstance(handler, logging.FileHandler):
                                    handler.flush()
                        except Exception as e:
                            print(f"[BUTTON-ERROR] Error in polling fallback callback: {e}", file=sys.stderr, flush=True)
                            self.logger.error(f"[BUTTON-ERROR] Error in polling fallback callback: {e}", exc_info=True)
                            # Even if callback fails, we've already updated last_state, so polling continues
                    else:
                        consecutive_same_state_count += 1
                    
                    # ========== RESET BUTTON MONITORING ==========
                    # Read reset button GPIO pin multiple times rapidly
                    rapid_reads_reset = []
                    for _ in range(3):  # Read 3 times rapidly
                        rapid_reads_reset.append(GPIO.input(self.reset_button_pin))
                    # Use majority vote (2 out of 3) to determine state
                    low_count_reset = rapid_reads_reset.count(GPIO.LOW)
                    high_count_reset = rapid_reads_reset.count(GPIO.HIGH)
                    if low_count_reset >= 2:
                        current_state_reset = GPIO.LOW  # Button is pressed
                    else:
                        current_state_reset = GPIO.HIGH  # Button is not pressed
                    is_pressed_now_reset = (current_state_reset == GPIO.LOW)
                    
                    # Log reset button state changes
                    if current_state_reset != last_state_reset or len(set(rapid_reads_reset)) > 1:
                        if current_state_reset != last_state_reset:
                            self.logger.info(f"[BUTTON-DEBUG] GPIO {self.reset_button_pin} (Reset) STATE CHANGE: rapid_reads={rapid_reads_reset} (LOW={low_count_reset}, HIGH={high_count_reset}), current_state={current_state_reset}, last_state={last_state_reset}")
                        elif len(set(rapid_reads_reset)) > 1:
                            self.logger.warning(f"[BUTTON-DEBUG] GPIO {self.reset_button_pin} (Reset) UNSTABLE: rapid_reads={rapid_reads_reset} (LOW={low_count_reset}, HIGH={high_count_reset}), current_state={current_state_reset}, last_state={last_state_reset}")
                        # Force immediate flush
                        for handler in self.logger.handlers:
                            if isinstance(handler, logging.FileHandler):
                                handler.flush()
                    
                    # Check if reset button state changed
                    if current_state_reset != last_state_reset:
                        # State changed - log the event
                        self.logger.info(f"[BUTTON] Reset button state change detected on GPIO {self.reset_button_pin}: {last_state_reset} -> {current_state_reset} (pressed={is_pressed_now_reset}, consecutive_same={consecutive_same_state_count_reset})")
                        # Force immediate flush to log file for button events
                        for handler in self.logger.handlers:
                            if isinstance(handler, logging.FileHandler):
                                handler.flush()
                        consecutive_same_state_count_reset = 0
                        # Update last_state BEFORE any future callback to prevent missing rapid presses
                        last_state_reset = current_state_reset
                        
                        # Reset button pressed - execute reset sequence
                        if is_pressed_now_reset:
                            # Only start reset sequence if one isn't already running
                            if not self._reset_sequence_running:
                                self._reset_sequence_running = True
                                self.logger.info(f"[BUTTON] Reset button press detected - executing reset sequence")
                                # Run reset sequence in a separate thread to avoid blocking button monitoring
                                def reset_sequence():
                                    """Execute reset sequence: blink all LEDs for 5 seconds, then turn off all except LED 10."""
                                    try:
                                        if not self.panel_led_controller:
                                            self.logger.error("[BUTTON] Reset sequence: Panel LED controller not available")
                                            self._reset_sequence_running = False
                                            return
                                        
                                        self.logger.info("[BUTTON] Reset sequence started: Blinking all LEDs for 5 seconds...")
                                        
                                        # Blink all LEDs on and off for 5 seconds
                                        blink_duration = 5.0  # 5 seconds
                                        blink_interval = 0.2  # 200ms on/off interval
                                        start_time = time.time()
                                        led_state = True  # Start with LEDs on
                                        
                                        while (time.time() - start_time) < blink_duration:
                                            if led_state:
                                                # Turn all LEDs on
                                                self.panel_led_controller.enable_all_green_leds()
                                                self.panel_led_controller.enable_all_red_leds()
                                            else:
                                                # Turn all LEDs off
                                                self.panel_led_controller.disable_all_green_leds()
                                                self.panel_led_controller.disable_all_red_leds()
                                            
                                            led_state = not led_state
                                            time.sleep(blink_interval)
                                            
                                            # Check if shutdown requested
                                            if self._shutdown_requested:
                                                self.logger.info("[BUTTON] Reset sequence interrupted by shutdown")
                                                self._reset_sequence_running = False
                                                return
                                        
                                        # After 5 seconds, turn off all LEDs except LED 10
                                        self.logger.info("[BUTTON] Reset sequence: Turning off all LEDs except LED 10...")
                                        
                                        # Disable all LEDs
                                        self.panel_led_controller.disable_all_green_leds()
                                        self.panel_led_controller.disable_all_red_leds()
                                        
                                        # Enable only LED 10
                                        self.panel_led_controller.enable_led(10)
                                        self.logger.info("[BUTTON] Reset sequence completed: All LEDs off except LED 10")
                                        
                                    except Exception as e:
                                        self.logger.error(f"[BUTTON] Error in reset sequence: {e}", exc_info=True)
                                    finally:
                                        # Always clear the flag when sequence completes or errors
                                        self._reset_sequence_running = False
                                        self.logger.debug("[BUTTON] Reset sequence flag cleared")
                                
                                # Start reset sequence in a daemon thread
                                reset_thread = threading.Thread(target=reset_sequence, daemon=True, name="Reset-Sequence")
                                reset_thread.start()
                                self.logger.info("[BUTTON] Reset sequence thread started")
                            else:
                                self.logger.debug("[BUTTON] Reset sequence already running - ignoring button press")
                    else:
                        consecutive_same_state_count_reset += 1
                    
                    # Periodic diagnostic: log state every 5 seconds with more detail
                    current_time = time.time()
                    if current_time - last_poll_time >= 5.0:
                        time_since_last_success = current_time - last_successful_read_time
                        self.logger.info(f"[BUTTON] Periodic check - GPIO {self.mute_button_pin} (Mute): state={current_state} (pressed={is_pressed_now}), last_state={last_state}, unchanged_count={consecutive_same_state_count}, consecutive_errors={consecutive_gpio_errors}, time_since_last_success={time_since_last_success:.2f}s")
                        self.logger.info(f"[BUTTON] Periodic check - GPIO {self.reset_button_pin} (Reset): state={current_state_reset} (pressed={is_pressed_now_reset}), last_state={last_state_reset}, unchanged_count={consecutive_same_state_count_reset}")
                        # Also verify GPIO is still configured correctly
                        try:
                            # Try to read pins again to verify they're working
                            verify_read_mute = GPIO.input(self.mute_button_pin)
                            verify_read_reset = GPIO.input(self.reset_button_pin)
                            if verify_read_mute != current_state:
                                self.logger.warning(f"[BUTTON] Mute GPIO read inconsistency: current_state={current_state}, verify_read={verify_read_mute}")
                            if verify_read_reset != current_state_reset:
                                self.logger.warning(f"[BUTTON] Reset GPIO read inconsistency: current_state={current_state_reset}, verify_read={verify_read_reset}")
                        except Exception as e:
                            self.logger.error(f"[BUTTON] GPIO read failed during periodic check: {e}")
                        last_poll_time = current_time
                        
                except Exception as e:
                    # Log error with full details
                    import sys
                    print(f"[BUTTON-ERROR] Error in polling fallback: {e}", file=sys.stderr, flush=True)
                    self.logger.error(f"[BUTTON-ERROR] Error in polling fallback: {e}", exc_info=True)
                    # Try to recover by re-initializing GPIO pin if it's a GPIO-related error
                    if 'GPIO' in str(type(e).__name__) or 'RuntimeError' in str(type(e).__name__):
                        try:
                            self.logger.warning(f"[BUTTON] GPIO error detected, attempting to re-initialize GPIO pin {self.mute_button_pin}...")
                            # Remove event detection
                            try:
                                GPIO.remove_event_detect(self.mute_button_pin)
                            except:
                                pass
                            # Re-setup the pin
                            GPIO.setup(self.mute_button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                            # Re-add event detection
                            GPIO.add_event_detect(
                                self.mute_button_pin,
                                GPIO.BOTH,
                                callback=mute_button_callback_wrapper,
                                bouncetime=int(self.mute_button_debounce_time * 1000)
                            )
                            # Reset state tracking
                            self.mute_button_last_state = GPIO.input(self.mute_button_pin)
                            last_state = self.mute_button_last_state
                            self.logger.info(f"[BUTTON] GPIO pin {self.mute_button_pin} re-initialized successfully")
                        except Exception as recovery_error:
                            self.logger.error(f"[BUTTON] Failed to recover GPIO pin {self.mute_button_pin}: {recovery_error}", exc_info=True)
                    # Continue polling even after error - don't let one error stop the thread
                    time.sleep(0.01)  # Small delay before retrying
                
        except Exception as e:
            import sys
            print(f"[BUTTON-FATAL] Fatal error in mute button monitor thread: {e}", file=sys.stderr, flush=True)
            self.logger.error(f"[BUTTON-FATAL] Fatal error in mute button monitor thread: {e}", exc_info=True)
            import traceback
            self.logger.error(f"[BUTTON-FATAL] Traceback: {traceback.format_exc()}")
        finally:
            try:
                if RPI_GPIO_AVAILABLE:
                    GPIO.remove_event_detect(self.mute_button_pin)
                    self.logger.info(f"[BUTTON] Removed event detection on GPIO {self.mute_button_pin}")
            except:
                pass
            self.logger.info("[BUTTON] Button monitoring stopped (Mute and Reset)")
    
    def _reset_button_monitor_thread(self):
        """Background thread to monitor reset button (event-driven with GPIO.BOTH)."""
        if not RPI_GPIO_AVAILABLE:
            self.logger.warning("[BUTTON] RPi.GPIO not available - reset button monitoring disabled")
            return
        
        if GPIO is None:
            self.logger.error("[BUTTON] GPIO module is None - reset button monitoring disabled")
            return
        
        self.logger.info(f"[BUTTON] Starting reset button monitor thread for GPIO {self.reset_button_pin}")
        
        # Verify GPIO module is actually functional and check current mode
        current_gpio_mode = None
        try:
            current_gpio_mode = GPIO.getmode()
            # GPIO.BCM = 10, GPIO.BOARD = 11
            if current_gpio_mode == GPIO.BCM:
                mode_name = "BCM"
            elif current_gpio_mode == GPIO.BOARD:
                mode_name = "BOARD"
            else:
                mode_name = "UNKNOWN"
            self.logger.info(f"[BUTTON] Current GPIO mode: {current_gpio_mode} ({mode_name})")
        except Exception as e:
            self.logger.warning(f"[BUTTON] Could not read GPIO mode: {e}")
        
        try:
            # Remove any existing event detection first (same as test program)
            try:
                GPIO.remove_event_detect(self.reset_button_pin)
                self.logger.info(f"[BUTTON] Removed existing event detection on GPIO {self.reset_button_pin}")
            except:
                pass
            
            # Reset callback state tracking (same as test program)
            self.reset_button_last_callback_time = 0
            self.reset_button_last_callback_state = None
            
            # Setup GPIO pin for reset button
            # CRITICAL: GPIO mode must be BCM for button pins 19 and 21 to work correctly
            # In BOARD mode, pin 19 = physical pin 19 (BCM GPIO 10), pin 21 = physical pin 21 (BCM GPIO 9)
            # We need BCM GPIO 19 (physical pin 35) and GPIO 21 (physical pin 40)
            if current_gpio_mode is None:
                try:
                    GPIO.setmode(GPIO.BCM)
                    GPIO.setwarnings(False)
                    self.logger.info(f"[BUTTON] GPIO mode set to BCM (was not set)")
                    current_gpio_mode = GPIO.BCM
                except RuntimeError as e:
                    self.logger.error(f"[BUTTON] CRITICAL: Failed to set GPIO mode to BCM: {e}")
                    self.logger.error(f"[BUTTON] Button monitoring will not work correctly!")
                    raise  # Stop thread initialization
            elif current_gpio_mode == GPIO.BOARD:
                # GPIO mode is BOARD - this is a CRITICAL problem!
                # We need to convert pin numbers or fail
                self.logger.error(f"[BUTTON] CRITICAL: GPIO mode is BOARD, but button pins are configured for BCM mode!")
                self.logger.error(f"[BUTTON] In BOARD mode, pin {self.reset_button_pin} = physical pin {self.reset_button_pin} (BCM GPIO 9)")
                self.logger.error(f"[BUTTON] We need BCM GPIO {self.reset_button_pin} = physical pin 40 in BOARD mode")
                self.logger.error(f"[BUTTON] SOLUTION: Ensure panel_led_controller initializes with BCM mode BEFORE button threads start")
                self.logger.error(f"[BUTTON] Button monitoring DISABLED - GPIO mode conflict!")
                GPIO.setwarnings(False)
                return  # Exit thread - buttons won't work with BOARD mode
            else:
                # GPIO mode is BCM - correct!
                GPIO.setwarnings(False)
                self.logger.info(f"[BUTTON] GPIO mode is BCM - button pin {self.reset_button_pin} is correct for BCM mode.")
            
            # Remove any existing event detection and cleanup pin first
            try:
                GPIO.remove_event_detect(self.reset_button_pin)
                self.logger.debug(f"[BUTTON] Removed existing event detection on GPIO {self.reset_button_pin}")
            except:
                pass
            
            # Try to cleanup and reconfigure the pin to ensure it's in the correct state
            try:
                # Note: GPIO.cleanup(pin) doesn't exist, but we can try to setup the pin fresh
                # If pin is already configured, GPIO.setup will reconfigure it
                GPIO.setup(self.reset_button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                self.logger.info(f"[BUTTON] GPIO {self.reset_button_pin} configured as input with pull-up")
            except Exception as e:
                self.logger.error(f"[BUTTON] Failed to setup GPIO {self.reset_button_pin} as input: {e}", exc_info=True)
                raise  # Re-raise to stop thread initialization
            
            # Initialize button state to current physical state (same as test program)
            init_time = time.time()
            self.reset_button_last_state = GPIO.input(self.reset_button_pin)
            is_pressed_initial = (self.reset_button_last_state == GPIO.LOW)
            self.reset_button_last_callback_state = is_pressed_initial
            self.reset_button_last_callback_time = init_time - (self.reset_button_debounce_time * 2)
            
            self.logger.info(f"[BUTTON] Initial reset button state: {self.reset_button_last_state} (LOW={GPIO.LOW}, HIGH={GPIO.HIGH})")
            self.logger.info(f"[BUTTON] Initial callback state (is_pressed): {is_pressed_initial}")
            self.logger.info(f"[BUTTON] Debounce time: {self.reset_button_debounce_time}s ({int(self.reset_button_debounce_time * 1000)}ms)")
            
            # Test GPIO read to verify it's working
            test_read = GPIO.input(self.reset_button_pin)
            self.logger.info(f"[BUTTON] Test GPIO read: {test_read} (should be {GPIO.HIGH} if button not pressed)")
            
            # Additional hardware test: read pin multiple times to verify it's stable
            test_reads = [GPIO.input(self.reset_button_pin) for _ in range(5)]
            self.logger.info(f"[BUTTON] Hardware test - 5 consecutive reads: {test_reads} (all should be {GPIO.HIGH} if button not pressed)")
            
            # Verify GPIO constants
            self.logger.info(f"[BUTTON] GPIO constants: LOW={GPIO.LOW}, HIGH={GPIO.HIGH}, IN={GPIO.IN}, PUD_UP={GPIO.PUD_UP}")
            
            # Create standalone callback function inside thread (not a method) - matches test program pattern
            # This captures 'self' in a closure, making it a regular function from RPi.GPIO's perspective
            def reset_button_callback_wrapper(channel: int):
                """Standalone callback wrapper that calls the instance method."""
                try:
                    self._reset_button_callback(channel)
                except Exception as e:
                    self.logger.error(f"[BUTTON] Error in reset button callback wrapper: {e}", exc_info=True)
            
            # Setup interrupt callback with debouncing (GPIO.BOTH for event-driven approach)
            # Use standalone function like test program (not a method) to ensure proper binding
            GPIO.add_event_detect(
                self.reset_button_pin,
                GPIO.BOTH,  # Detect both rising and falling edges (event-driven)
                callback=reset_button_callback_wrapper,  # Standalone function (not method) like test program
                bouncetime=int(self.reset_button_debounce_time * 1000)  # Convert to milliseconds (10ms)
            )
            
            # Verify event detection was registered
            try:
                pin_state = GPIO.input(self.reset_button_pin)
                self.logger.info(f"[BUTTON] Reset button monitoring started on GPIO {self.reset_button_pin} (event-driven, GPIO.BOTH, bouncetime={int(self.reset_button_debounce_time * 1000)}ms)")
                self.logger.info(f"[BUTTON] Event detection registered - current pin state: {pin_state} (LOW={GPIO.LOW}, HIGH={GPIO.HIGH})")
            except Exception as e:
                self.logger.warning(f"[BUTTON] Could not verify event detection registration: {e}")
            
            # Keep thread alive and use hybrid approach: event detection + polling fallback
            # Polling fallback ensures we catch button presses even if event detection fails
            last_poll_time = time.time()
            last_state = self.reset_button_last_state
            poll_interval = 0.01  # Poll every 10ms (same as debounce time)
            consecutive_same_state_count = 0  # Track how many times we've seen the same state
            
            self.logger.info(f"[BUTTON] Starting polling loop for GPIO {self.reset_button_pin} (poll_interval={poll_interval}s, initial_state={last_state})")
            
            while self.reset_button_running and not self._shutdown_requested:
                time.sleep(poll_interval)
                
                # Polling fallback: manually check button state and trigger callback if changed
                # This ensures we catch button presses even if event detection isn't working
                try:
                    # Read GPIO pin multiple times rapidly to catch brief button presses
                    # This helps catch very brief presses that might be missed by single reads
                    rapid_reads = []
                    for _ in range(3):  # Read 3 times rapidly
                        rapid_reads.append(GPIO.input(self.reset_button_pin))
                    # Use majority vote (2 out of 3) to determine state - more reliable than "any LOW"
                    low_count = rapid_reads.count(GPIO.LOW)
                    high_count = rapid_reads.count(GPIO.HIGH)
                    if low_count >= 2:
                        current_state = GPIO.LOW  # At least 2 reads show LOW, button is pressed
                    else:
                        current_state = GPIO.HIGH  # At least 2 reads show HIGH, button is not pressed
                    is_pressed_now = (current_state == GPIO.LOW)
                    
                    # CRITICAL DEBUGGING: Only log on state changes or when readings are unstable
                    if current_state != last_state or len(set(rapid_reads)) > 1:
                        # State changed or readings are unstable - log for debugging
                        if current_state != last_state:
                            self.logger.info(f"[BUTTON-DEBUG] GPIO {self.reset_button_pin} STATE CHANGE: rapid_reads={rapid_reads} (LOW={low_count}, HIGH={high_count}), current_state={current_state}, last_state={last_state}")
                        elif len(set(rapid_reads)) > 1:
                            # Readings are unstable but state hasn't changed yet - might be transitioning
                            self.logger.warning(f"[BUTTON-DEBUG] GPIO {self.reset_button_pin} UNSTABLE: rapid_reads={rapid_reads} (LOW={low_count}, HIGH={high_count}), current_state={current_state}, last_state={last_state}")
                        # Force immediate flush
                        for handler in self.logger.handlers:
                            if isinstance(handler, logging.FileHandler):
                                handler.flush()
                    
                    # Check if state changed (polling fallback)
                    if current_state != last_state:
                        # State changed - trigger callback manually (polling fallback)
                        self.logger.info(f"[BUTTON] Polling fallback detected state change on GPIO {self.reset_button_pin}: {last_state} -> {current_state} (pressed={is_pressed_now}, consecutive_same={consecutive_same_state_count})")
                        # Force immediate flush to log file for button events
                        for handler in self.logger.handlers:
                            if isinstance(handler, logging.FileHandler):
                                handler.flush()
                        consecutive_same_state_count = 0
                        # IMPORTANT: Update last_state BEFORE calling callback to prevent missing rapid presses
                        last_state = current_state
                        try:
                            self.logger.info(f"[BUTTON] Calling reset_button_callback_wrapper({self.reset_button_pin})...")
                            for handler in self.logger.handlers:
                                if isinstance(handler, logging.FileHandler):
                                    handler.flush()
                            reset_button_callback_wrapper(self.reset_button_pin)
                            self.logger.info(f"[BUTTON] reset_button_callback_wrapper completed")
                            # Force immediate flush after callback
                            for handler in self.logger.handlers:
                                if isinstance(handler, logging.FileHandler):
                                    handler.flush()
                        except Exception as e:
                            self.logger.error(f"[BUTTON] Error in polling fallback callback: {e}", exc_info=True)
                            # Even if callback fails, we've already updated last_state, so polling continues
                    else:
                        consecutive_same_state_count += 1
                    
                    # Periodic diagnostic: log state every 5 seconds with more detail
                    current_time = time.time()
                    if current_time - last_poll_time >= 5.0:
                        self.logger.info(f"[BUTTON] Periodic check - GPIO {self.reset_button_pin}: state={current_state} (pressed={is_pressed_now}), last_state={last_state}, unchanged_count={consecutive_same_state_count}")
                        # Also verify GPIO is still configured correctly
                        try:
                            # Try to read pin again to verify it's working
                            verify_read = GPIO.input(self.reset_button_pin)
                            if verify_read != current_state:
                                self.logger.warning(f"[BUTTON] GPIO read inconsistency: current_state={current_state}, verify_read={verify_read}")
                        except Exception as e:
                            self.logger.error(f"[BUTTON] GPIO read failed during periodic check: {e}")
                        last_poll_time = current_time
                        
                except Exception as e:
                    self.logger.error(f"[BUTTON] Error in polling fallback: {e}", exc_info=True)
                
        except Exception as e:
            self.logger.error(f"[BUTTON] Error in reset button monitor thread: {e}", exc_info=True)
            import traceback
            self.logger.error(f"[BUTTON] Traceback: {traceback.format_exc()}")
        finally:
            try:
                if RPI_GPIO_AVAILABLE:
                    GPIO.remove_event_detect(self.reset_button_pin)
                    self.logger.info(f"[BUTTON] Removed event detection on GPIO {self.reset_button_pin}")
            except:
                pass
            self.logger.info("[BUTTON] Reset button monitoring stopped")
    
    def _ups_status_check_thread(self):
        """Background thread to check UPS status every 10 seconds."""
        self.logger.info("UPS status check thread started (checking every 10 seconds)")
        while not self._shutdown_requested and self._status_check_running:
            try:
                self._check_ups_status()
            except Exception as e:
                self.logger.error(f"Error in UPS status check: {e}", exc_info=True)
            
            # Sleep in small increments to check shutdown flag more frequently
            for _ in range(100):  # 100 * 0.1 = 10 seconds
                if self._shutdown_requested or not self._status_check_running:
                    break
                time.sleep(0.1)
        
        self.logger.info("UPS status check thread stopped")
    
    def start(self):
        """Start the SNMP trap receiver."""
        try:
            # Log START event
            start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.logger.info("=" * 80)
            self.logger.info(f"UPS/ATS SNMP TRAP RECEIVER v3 - START EVENT (SNMPv2c)")
            self.logger.info(f"Start Time: {start_time}")
            self.logger.info("=" * 80)
            
            platform_name = "Windows" if self.is_windows else "Linux"
            self.logger.info(f"Starting UPS/ATS SNMP Trap Receiver v3 on {platform_name}")
            self.logger.info(f"Protocol: SNMPv2c (primary), SNMPv1 (backward compatibility)")
            self.logger.info(f"MIB: ATS_Stork_V1_05 - Borri STS32A.MIB")
            self.logger.info(f"Listening on port: {self.port}")
            self.logger.info(f"Logging to: {self.log_file.absolute()}")
            if self.allowed_ips:
                self.logger.info(f"Filtering: Only accepting traps from: {', '.join(self.allowed_ips)}")
            else:
                self.logger.info("Filtering: Accepting traps from all sources")
            if not self._shutdown_requested:
                self.logger.info("Press Ctrl+C to stop")
            
            # Write PID file
            self._write_pid_file()
            
            # Ensure buzzer is turned off on startup
            if self.panel_led_controller:
                try:
                    # Use disable_buzzer() method if available (handles GPIO properly)
                    if hasattr(self.panel_led_controller, 'disable_buzzer'):
                        if self.panel_led_controller.disable_buzzer():
                            from AlarmMap import get_gpio_pin_by_led
                            try:
                                speaker_pin = get_gpio_pin_by_led('speaker')
                                self.logger.info(f"Buzzer/speaker disabled on service start using disable_buzzer() (GPIO pin {speaker_pin})")
                            except:
                                self.logger.info("Buzzer/speaker disabled on service start using disable_buzzer()")
                        else:
                            # Fallback to disable_led()
                            if self.panel_led_controller.disable_led('speaker'):
                                self.logger.info("Buzzer/speaker disabled on service start using disable_led('speaker')")
                    else:
                        # Use disable_led() if disable_buzzer() not available
                        if self.panel_led_controller.disable_led('speaker'):
                            self.logger.info("Buzzer/speaker disabled on service start")
                        else:
                            # Try alternative names
                            for buzzer_name in ['buzzer', 'Buzzer', 'Buzzer/Speaker']:
                                if self.panel_led_controller.disable_led(buzzer_name):
                                    self.logger.info(f"Buzzer/speaker disabled on service start using '{buzzer_name}'")
                                    break
                except Exception as e:
                    self.logger.debug(f"Could not disable buzzer on service start: {e}")
            
            # Start UPS status check thread if available
            if self.ups_status_checker:
                self._status_check_running = True
                self.ups_status_thread = threading.Thread(target=self._ups_status_check_thread, daemon=True)
                self.ups_status_thread.start()
                self.logger.info(f"UPS status check thread started (checking every 10 seconds)")
            elif GET_UPS_STATUS_AVAILABLE:
                self.logger.warning("GetUPSStatus available but UPS host not configured - status checking disabled")
            
            # Start button monitoring threads (Mute and Reset buttons)
            self.logger.info(f"[BUTTON] Checking button monitoring conditions: RPI_GPIO_AVAILABLE={RPI_GPIO_AVAILABLE}, is_windows={self.is_windows}")
            if RPI_GPIO_AVAILABLE and not self.is_windows:
                # Start mute button monitoring thread
                # CRITICAL: Use daemon=False to ensure button thread gets CPU time even when SNMP is idle
                # Daemon threads can be starved when other threads are blocking
                try:
                    self.mute_button_running = True
                    self.mute_button_thread = threading.Thread(target=self._mute_button_monitor_thread, daemon=False, name="Button-Monitor")
                    self.mute_button_thread.start()
                    self.logger.info(f"Button monitoring thread started (Mute: GPIO {self.mute_button_pin}, Reset: GPIO {self.reset_button_pin}) [NON-DAEMON]")
                except Exception as e:
                    self.logger.error(f"Failed to start mute button monitoring thread: {e}")
                    self.mute_button_running = False
                
                # DEBUG: Reset button monitoring thread DISABLED for debug purposes
                # Start reset button monitoring thread
                # try:
                #     self.reset_button_running = True
                #     self.reset_button_thread = threading.Thread(target=self._reset_button_monitor_thread, daemon=True)
                #     self.reset_button_thread.start()
                #     self.logger.info(f"Reset button monitoring thread started (GPIO {self.reset_button_pin})")
                # except Exception as e:
                #     self.logger.error(f"Failed to start reset button monitoring thread: {e}")
                #     self.reset_button_running = False
                self.logger.info("[BUTTON] Reset button monitoring thread DISABLED (for debug purposes)")
            else:
                if self.is_windows:
                    self.logger.info("Button monitoring disabled (Windows platform)")
                elif not RPI_GPIO_AVAILABLE:
                    self.logger.info("Button monitoring disabled (RPi.GPIO not available)")
            
            # Create SNMP engine
            self.snmp_engine = engine.SnmpEngine()
            
            # Ensure asyncio event loop exists for pysnmp's asyncio transport
            # pysnmp's asyncio UDP transport requires an event loop to be running
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    # Loop is closed, create a new one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    self.logger.debug("Created new asyncio event loop (previous loop was closed)")
            except RuntimeError:
                # No event loop exists, create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self.logger.debug("Created new asyncio event loop (no existing loop)")
            
            # Configure transport with source address capture
            # Create a custom transport wrapper to capture source addresses
            transport = udp.UdpTransport().open_server_mode(('0.0.0.0', self.port))
            
            # Store reference to transport for source address extraction
            self._transport = transport
            
            # Try to intercept the receive callback to capture source address
            # For asyncio transport, we need to wrap the datagram_received method or socket callback
            import time
            if not hasattr(self, '_last_src_addr'):
                self._last_src_addr = {}
            
            # Method 1: Try to wrap datagram_received (asyncio UDP transport)
            if hasattr(transport, 'datagram_received'):
                original_datagram_received = transport.datagram_received
                
                def datagram_received_wrapper(data, addr):
                    # Capture source address
                    if addr:
                        timestamp = time.time()
                        self._last_src_addr[timestamp] = addr
                        self.logger.debug(f"Captured source address from datagram_received: {addr}")
                    # Call original method
                    return original_datagram_received(data, addr)
                
                transport.datagram_received = datagram_received_wrapper
                self.logger.debug("Wrapped datagram_received to capture source address")
            
            # Method 2: Try to wrap _cbFun (lower-level callback)
            if hasattr(transport, '_cbFun'):
                original_cbFun = transport._cbFun
                
                def cbFun_wrapper(transport_obj, src_addr, data):
                    # Capture source address
                    if src_addr:
                        timestamp = time.time()
                        self._last_src_addr[timestamp] = src_addr
                        self.logger.debug(f"Captured source address from _cbFun: {src_addr}")
                    # Call original callback
                    return original_cbFun(transport_obj, src_addr, data)
                
                transport._cbFun = cbFun_wrapper
                self.logger.debug("Wrapped _cbFun to capture source address")
            
            # Method 3: Try to access socket directly and monitor receives
            if hasattr(transport, 'socket') and transport.socket:
                socket_obj = transport.socket
                self.logger.debug(f"Transport has socket: {type(socket_obj).__name__}")
                # For asyncio, the socket might be a DatagramProtocol
                # We can't easily intercept at this level, but we've tried the callbacks above
            
            config.add_transport(
                self.snmp_engine,
                udp.DOMAIN_NAME + (1,),
                transport
            )
            
            # Configure SNMPv2c community (primary protocol for receiving traps)
            # Note: Trap receivers typically accept traps without explicit community configuration
            # However, some pysnmp versions may require it, so we configure it with fallbacks
            # SNMPv2c is the primary protocol for ATS_Stork_V1_05 - Borri STS32A.MIB traps
            
            # Configure SNMPv2c - primary protocol for ATS traps
            v2c_configured = False
            try:
                config.add_v2c_system(self.snmp_engine, 'my-area', 'public')
                v2c_configured = True
                self.logger.info("SNMPv2c system configured successfully (primary protocol)")
            except AttributeError:
                try:
                    # Try old camelCase name
                    config.addV2cSystem(self.snmp_engine, 'my-area', 'public')
                    v2c_configured = True
                    self.logger.info("SNMPv2c system configured successfully (primary protocol, using legacy API)")
                except AttributeError:
                    # v2c traps don't require explicit configuration in most cases
                    # The NotificationReceiver will accept v2c traps regardless
                    self.logger.debug("SNMPv2c explicit configuration not available (will accept v2c traps by default)")
            
            # Configure SNMPv1 (optional, for backward compatibility with older devices)
            # Note: ATS_Stork_V1_05 - Borri STS32A.MIB uses SNMPv2c, but we keep v1 support for legacy devices
            try:
                config.add_v1_system(self.snmp_engine, 'my-area', 'public')
                self.logger.debug("SNMPv1 system configured (backward compatibility)")
            except AttributeError:
                try:
                    # Fallback to old camelCase API
                    config.addV1System(self.snmp_engine, 'my-area', 'public')
                    self.logger.debug("SNMPv1 system configured (backward compatibility, using legacy API)")
                except AttributeError:
                    self.logger.debug("SNMPv1 system configuration not available (v2c is primary)")
            
            if v2c_configured:
                self.logger.info("SNMP trap receiver configured for SNMPv2c (primary) and SNMPv1 (backward compatibility)")
            else:
                # This is normal - SNMPv2c traps don't require explicit configuration
                # The NotificationReceiver will accept v2c traps regardless
                self.logger.info("SNMP trap receiver will accept SNMPv2c traps (default behavior)")
            
            # Configure SNMPv3 (optional, for secure traps)
            # config.add_v3_user(
            #     self.snmp_engine, 'usr-sha-aes128',
            #     config.usmHMACSHAAuthProtocol, 'authkey1',
            #     config.usmAesCfb128Protocol, 'privkey1'
            # )
            
            # Register callback for trap reception
            ntfrcv.NotificationReceiver(self.snmp_engine, self.cbFun)
            
            # Start the engine
            self.snmp_engine.transport_dispatcher.job_started(1)
            
            # Run the dispatcher in a separate thread to prevent blocking the button monitoring thread
            # CRITICAL: When run_dispatcher() blocks in the main thread, it prevents the button thread
            # from getting CPU time. Moving it to a separate thread allows the button thread to run
            # even when SNMP is idle.
            def run_dispatcher_thread():
                """Run SNMP dispatcher in a separate thread with periodic yielding."""
                try:
                    self.logger.info("[SNMP] Starting SNMP dispatcher in separate thread...")
                    # CRITICAL: We can't directly modify run_dispatcher() to yield,
                    # but we can wrap it in a way that periodically checks for other threads
                    # However, run_dispatcher() is blocking, so we need a different approach
                    # The watchdog thread will help, but we also need to ensure this thread
                    # doesn't hold the GIL indefinitely
                    
                    # Set thread priority hint (if available)
                    try:
                        import sys
                        # Force periodic GIL releases by doing small operations
                        # This is a workaround for asyncio event loop blocking
                        self.logger.info("[SNMP] Dispatcher thread running (with watchdog support)")
                    except:
                        pass
                    
                    # Run the dispatcher (this will block)
                    self.snmp_engine.transport_dispatcher.run_dispatcher()
                    self.logger.info("[SNMP] SNMP dispatcher thread exited")
                except Exception as e:
                    # If shutdown was requested, this exception is expected when dispatcher closes
                    # The dispatcher may raise an exception when closed, which is normal
                    if not self._shutdown_requested:
                        self.logger.error(f"[SNMP] Error in dispatcher thread: {e}", exc_info=True)
                        # Only raise if shutdown wasn't requested
                        raise
            
            # Start dispatcher in a non-daemon thread (daemon=False) so it keeps running
            dispatcher_thread = threading.Thread(target=run_dispatcher_thread, daemon=False, name="SNMP-Dispatcher")
            dispatcher_thread.start()
            self.logger.info("[SNMP] SNMP dispatcher thread started (non-blocking)")
            
            # CRITICAL FIX: Add a watchdog thread that periodically forces thread context switches
            # This ensures the button thread gets CPU time even when SNMP dispatcher is blocking
            # The asyncio event loop in run_dispatcher() can block in a way that starves other threads
            def watchdog_thread():
                """Watchdog thread that periodically forces thread context switches."""
                self.logger.info("[WATCHDOG] Watchdog thread started (ensuring button thread gets CPU time)")
                while not self._shutdown_requested:
                    try:
                        # Sleep for 50ms, then force a context switch
                        time.sleep(0.05)  # 50ms intervals
                        # Force thread context switch by accessing thread state
                        _ = threading.current_thread()
                        # Explicitly yield to other threads
                        threading.Event().wait(0)
                        # Log periodically (every 10 seconds) to show watchdog is alive
                        if hasattr(self, '_watchdog_count'):
                            self._watchdog_count += 1
                        else:
                            self._watchdog_count = 1
                        if self._watchdog_count % 200 == 0:  # Every 10 seconds (200 * 0.05s)
                            self.logger.debug(f"[WATCHDOG] Watchdog heartbeat (count: {self._watchdog_count})")
                    except Exception as e:
                        self.logger.error(f"[WATCHDOG] Error in watchdog thread: {e}")
                        time.sleep(0.1)  # Wait before retrying
            
            watchdog = threading.Thread(target=watchdog_thread, daemon=True, name="Thread-Watchdog")
            watchdog.start()
            self.logger.info("[WATCHDOG] Watchdog thread started (daemon)")
            
            # Keep main thread alive and allow button thread to run
            # This ensures the button monitoring thread gets CPU time even when SNMP is idle
            # CRITICAL: Use shorter sleep intervals and explicit thread yielding to ensure
            # button thread gets CPU time even when SNMP dispatcher is blocking
            # The issue: When SNMP is idle, run_dispatcher() blocks in asyncio event loop,
            # which can starve other threads. We need aggressive yielding here.
            try:
                loop_count = 0
                while not self._shutdown_requested:
                    # Use very short sleep (0.01s = 10ms) for more frequent thread switching
                    time.sleep(0.01)  # Very short sleep allows frequent thread switching
                    # Explicitly yield to other threads multiple times
                    threading.Event().wait(0)  # Yield to other threads
                    # Force thread context switch by doing a small operation
                    _ = threading.current_thread()
                    # Every 10 loops (100ms), do additional yielding
                    loop_count += 1
                    if loop_count >= 10:
                        loop_count = 0
                        # Force a more aggressive yield
                        threading.Event().wait(0.001)  # 1ms wait to force context switch
                    # Check if dispatcher thread is still alive
                    if not dispatcher_thread.is_alive():
                        self.logger.warning("[SNMP] Dispatcher thread has exited unexpectedly")
                        break
                    # Check if button thread is still alive
                    if self.mute_button_thread and not self.mute_button_thread.is_alive():
                        self.logger.warning("[BUTTON] Button monitoring thread has exited unexpectedly")
                        break
            except KeyboardInterrupt:
                self.logger.info("[MAIN] Received keyboard interrupt in main thread")
            except Exception as e:
                self.logger.error(f"[MAIN] Error in main thread loop: {e}", exc_info=True)
            
            # Wait for dispatcher thread to finish
            self.logger.info("[SNMP] Waiting for dispatcher thread to finish...")
            dispatcher_thread.join(timeout=5.0)
            if dispatcher_thread.is_alive():
                self.logger.warning("[SNMP] Dispatcher thread did not finish within timeout")
            
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
            # Windows uses error code 10048, Linux uses 98 for "Address already in use"
            error_code = getattr(e, 'winerror', getattr(e, 'errno', None))
            if error_code == 10048 or error_code == 98:  # Address already in use
                self.logger.error(
                    f"Port {self.port} is already in use. "
                    f"Another SNMP trap receiver may be running."
                )
            else:
                self.logger.error(f"OS Error: {e} (Error code: {error_code})")
            sys.exit(1)
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            if not self._shutdown_requested:
                self.logger.error(f"Unexpected error: {e}", exc_info=True)
                sys.exit(1)
        finally:
            self.stop()
            self._remove_pid_file()
            # Stop event is already logged in stop() method
    
    def stop(self):
        """Stop the SNMP trap receiver."""
        # Log STOP event
        stop_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.logger.info("=" * 80)
        self.logger.info(f"UPS/ATS SNMP TRAP RECEIVER v3 - STOP EVENT (SNMPv2c)")
        self.logger.info(f"Stop Time: {stop_time}")
        self.logger.info("=" * 80)
        
        # Stop button monitoring threads FIRST (before other GPIO cleanup)
        # This ensures button pins are properly released
        if hasattr(self, 'mute_button_running') and self.mute_button_running:
            self.logger.info("[BUTTON] Stopping mute button monitoring thread...")
            self.mute_button_running = False
            if hasattr(self, 'mute_button_thread') and self.mute_button_thread and self.mute_button_thread.is_alive():
                self.mute_button_thread.join(timeout=2.0)
                if self.mute_button_thread.is_alive():
                    self.logger.warning("[BUTTON] Mute button thread did not stop within timeout")
        
        # DEBUG: Reset button thread stop DISABLED (thread not started)
        # if hasattr(self, 'reset_button_running') and self.reset_button_running:
        #     self.logger.info("[BUTTON] Stopping reset button monitoring thread...")
        #     self.reset_button_running = False
        #     if hasattr(self, 'reset_button_thread') and self.reset_button_thread and self.reset_button_thread.is_alive():
        #         self.reset_button_thread.join(timeout=2.0)
        #         if self.reset_button_thread.is_alive():
        #             self.logger.warning("[BUTTON] Reset button thread did not stop within timeout")
        
        # Remove GPIO event detection for buttons (critical for proper cleanup)
        if RPI_GPIO_AVAILABLE:
            try:
                if hasattr(self, 'mute_button_pin'):
                    try:
                        GPIO.remove_event_detect(self.mute_button_pin)
                        self.logger.info(f"[BUTTON] Removed event detection from GPIO {self.mute_button_pin}")
                    except Exception as e:
                        self.logger.debug(f"[BUTTON] Error removing event detection from GPIO {self.mute_button_pin}: {e}")
                
                # DEBUG: Reset button GPIO cleanup DISABLED (thread not started)
                # if hasattr(self, 'reset_button_pin'):
                #     try:
                #         GPIO.remove_event_detect(self.reset_button_pin)
                #         self.logger.info(f"[BUTTON] Removed event detection from GPIO {self.reset_button_pin}")
                #     except Exception as e:
                #         self.logger.debug(f"[BUTTON] Error removing event detection from GPIO {self.reset_button_pin}: {e}")
            except Exception as e:
                self.logger.debug(f"[BUTTON] Error during GPIO event detection cleanup: {e}")
        
        # Stop UPS status check thread
        if self._status_check_running:
            self._status_check_running = False
            if self.ups_status_thread and self.ups_status_thread.is_alive():
                self.logger.info("Stopping UPS status check thread...")
                self.ups_status_thread.join(timeout=2.0)
                if self.ups_status_thread.is_alive():
                    self.logger.warning("UPS status check thread did not stop within timeout")
        
        # Cleanup Panel LED Controller (this may also use GPIO, so clean up after buttons)
        if self.panel_led_controller:
            try:
                self.panel_led_controller.cleanup()
                self.logger.info("Panel LED Controller cleaned up")
            except Exception as e:
                self.logger.error(f"Error cleaning up Panel LED Controller: {e}")
        
        if self.snmp_engine:
            try:
                self.snmp_engine.transport_dispatcher.close_dispatcher()
            except Exception as e:
                self.logger.debug(f"Error closing dispatcher: {e}")
        
        # Cleanup GPIO LED Controller
        if self.led_controller:
            try:
                self.led_controller.cleanup()
            except Exception as e:
                self.logger.debug(f"Error cleaning up GPIO: {e}")
        
        # Final GPIO cleanup - ensure all pins are reset
        # Note: We don't call GPIO.cleanup() here because panel_led_controller may have already done it
        # and GPIO.cleanup() affects ALL pins, which might interfere with other processes
        # Instead, we rely on proper cleanup of individual pins above


def load_email_config(config_file: str = 'email_config.json') -> Optional[Dict[str, Any]]:
    """
    Load email configuration from JSON file.
    
    Args:
        config_file: Path to configuration file
    
    Returns:
        Dictionary with email configuration or None if file doesn't exist or is invalid
    """
    config_path = Path(config_file)
    if not config_path.exists():
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except (json.JSONDecodeError, IOError) as e:
        logging.warning(f"Failed to load email config from {config_file}: {e}")
        return None


def main():
    """Main entry point."""
    import argparse
    
    # Print early to verify program starts (before logging is set up)
    print("UPS/ATS SNMP Trap Receiver v3 - Starting... (SNMPv2c protocol)", flush=True)
    
    is_windows = platform.system() == 'Windows'
    platform_desc = "Windows/Linux" if is_windows else "Linux (Raspberry Pi 4)"
    
    parser = argparse.ArgumentParser(
        description=f'UPS/ATS SNMP Trap Receiver v3 - Cross-platform ({platform_desc}) - SNMPv2c protocol',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Windows:
    # Run on default port 162 (requires Administrator)
    Run PowerShell as Administrator: python ups_snmp_trap_receiver.py
    
    # Run on custom port (no admin required)
    python ups_snmp_trap_receiver.py --port 1162
    
    # Specify custom log file
    python ups_snmp_trap_receiver.py --log-file C:\\Logs\\ups_traps.log
    
    # Accept traps only from specific UPS IP
    python ups_snmp_trap_receiver.py --ups-ip 192.168.111.137
    
    # Enable email notifications (using config file)
    python ups_snmp_trap_receiver.py
    
    # Enable email notifications (command-line override)
    python ups_snmp_trap_receiver.py --email-recipients admin@example.com,user@example.com --smtp-server 192.168.111.22 --from-email micky.lee@netsphere.com.hk
    
    # Use custom config file
    python ups_snmp_trap_receiver.py --email-config C:\\Config\\email_config.json
  
  Linux:
    # Run on default port 162 (requires root)
    sudo python3 ups_snmp_trap_receiver.py
    
    # Run on custom port (no root required)
    python3 ups_snmp_trap_receiver.py --port 1162
    
    # Specify custom log file
    python3 ups_snmp_trap_receiver.py --log-file /var/log/ups_traps.log
    
    # Accept traps only from specific UPS IP
    python3 ups_snmp_trap_receiver.py --ups-ip 192.168.111.137
    
    # Enable email notifications (using config file - recommended)
    python3 ups_snmp_trap_receiver.py
    
    # Enable email notifications (command-line override)
    python3 ups_snmp_trap_receiver.py --email-recipients admin@example.com,user@example.com --smtp-server 192.168.111.22 --smtp-port 25 --from-email micky.lee@netsphere.com.hk --from-name "UPS Monitor"
    
    # Use custom config file
    python3 ups_snmp_trap_receiver.py --email-config /etc/ups/email_config.json
        """
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=162,
        help='UDP port to listen on (default: 162, requires root)'
    )
    
    parser.add_argument(
        '--log-file', '-l',
        type=str,
        default=f'logs/{get_log_filename()}',
        help=f'Path to log file (default: logs/{get_log_filename()} - includes date in filename)'
    )
    
    parser.add_argument(
        '--ups-ip', '-u',
        type=str,
        default=None,
        help='UPS IP address to accept traps from (default: accept all). Can specify multiple IPs separated by commas.'
    )
    
    # Email notification arguments
    parser.add_argument(
        '--email-recipients', '-e',
        type=str,
        default=None,
        help='Comma-separated list of email addresses to send notifications to'
    )
    
    parser.add_argument(
        '--smtp-server',
        type=str,
        default=None,
        help='SMTP server hostname or IP address'
    )
    
    parser.add_argument(
        '--smtp-port',
        type=int,
        default=25,
        help='SMTP server port (default: 25)'
    )
    
    parser.add_argument(
        '--smtp-no-tls',
        action='store_true',
        help='Disable TLS for SMTP (default: TLS enabled)'
    )
    
    parser.add_argument(
        '--smtp-username',
        type=str,
        default=None,
        help='SMTP username (optional)'
    )
    
    parser.add_argument(
        '--smtp-password',
        type=str,
        default=None,
        help='SMTP password (optional)'
    )
    
    parser.add_argument(
        '--from-email',
        type=str,
        default=None,
        help='Sender email address'
    )
    
    parser.add_argument(
        '--from-name',
        type=str,
        default=None,
        help='Sender name (optional)'
    )
    
    parser.add_argument(
        '--email-config', '-c',
        type=str,
        default='email_config.json',
        help='Path to email configuration file (default: email_config.json)'
    )
    
    # GPIO LED control arguments
    parser.add_argument(
        '--critical-pin', '-C',
        type=int,
        default=None,
        help='GPIO pin for critical alarms (e.g., 17). Requires ups_gpio_led_controller.py'
    )
    
    parser.add_argument(
        '--warning-pin', '-W',
        type=int,
        default=None,
        help='GPIO pin for warning alarms (e.g., 17). Requires ups_gpio_led_controller.py'
    )
    
    parser.add_argument(
        '--info-pin', '-I',
        type=int,
        default=None,
        help='GPIO pin for info alarms (optional). Requires ups_gpio_led_controller.py'
    )
    
    parser.add_argument(
        '--gpio-no-blink',
        action='store_true',
        help='Disable blinking for GPIO LED (solid LED)'
    )
    
    parser.add_argument(
        '--gpio-blink-interval',
        type=float,
        default=0.5,
        help='GPIO LED blink interval in seconds (default: 0.5)'
    )
    
    parser.add_argument(
        '--gpio-active-low',
        action='store_true',
        help='Use active-low logic for GPIO LED (LED on with LOW signal)'
    )
    
    parser.add_argument(
        '--daemon', '-d',
        action='store_true',
        help='Run as daemon (background process). Linux only.'
    )
    
    parser.add_argument(
        '--pid-file',
        type=str,
        default='ups_trap_receiver.pid',
        help='Path to PID file (default: ups_trap_receiver.pid)'
    )
    
    args = parser.parse_args()
    
    # Parse allowed IP addresses - Command-line is primary method (Option 2)
    allowed_ips = None
    
    # First, try command-line argument (primary method)
    if args.ups_ip:
        allowed_ips = [ip.strip() for ip in args.ups_ip.split(',')]
        logging.info(f"Using allowed IPs from command-line: {allowed_ips}")
    else:
        # Fallback to config.py if command-line not provided
        try:
            # Use importlib to avoid conflict with pysnmp.entity.config
            import importlib.util
            config_path = Path(__file__).parent / 'config.py'
            if config_path.exists():
                spec = importlib.util.spec_from_file_location("ups_config", config_path)
                ups_config = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(ups_config)
                
                # Check for UPS_IP first (dedicated UPS IP address)
                ups_ip = None
                if hasattr(ups_config, 'UPS_IP') and ups_config.UPS_IP:
                    ups_ip = ups_config.UPS_IP
                    logging.info(f"Found UPS_IP in config.py: {ups_ip}")
                
                # Check for ALLOWED_IPS
                if hasattr(ups_config, 'ALLOWED_IPS'):
                    config_allowed_ips = ups_config.ALLOWED_IPS
                    if config_allowed_ips is None:
                        # None means accept all IPs, but if UPS_IP is set, use it
                        if ups_ip:
                            allowed_ips = [ups_ip]
                            logging.info(f"ALLOWED_IPS is None, using UPS_IP from config.py: {allowed_ips}")
                        else:
                            allowed_ips = None
                            logging.info("Loaded config.py (fallback): All IPs allowed (ALLOWED_IPS is None)")
                    elif isinstance(config_allowed_ips, list):
                        # Empty list means accept all IPs, but if UPS_IP is set, use it
                        if config_allowed_ips:
                            allowed_ips = config_allowed_ips.copy()  # Make a copy to avoid modifying the original
                            logging.info(f"Loaded allowed IPs from config.py (fallback): {allowed_ips}")
                        else:
                            # Empty list - use UPS_IP if available
                            if ups_ip:
                                allowed_ips = [ups_ip]
                                logging.info(f"ALLOWED_IPS is empty, using UPS_IP from config.py: {allowed_ips}")
                            else:
                                allowed_ips = None
                                logging.info("Loaded config.py (fallback): All IPs allowed (ALLOWED_IPS is empty)")
                    else:
                        # Convert single string to list
                        allowed_ips = [config_allowed_ips] if config_allowed_ips else None
                        if allowed_ips:
                            logging.info(f"Loaded allowed IPs from config.py (fallback): {allowed_ips}")
                elif ups_ip:
                    # No ALLOWED_IPS but UPS_IP exists - use UPS_IP
                    allowed_ips = [ups_ip]
                    logging.info(f"No ALLOWED_IPS in config.py, using UPS_IP: {allowed_ips}")
                else:
                    allowed_ips = []
                    logging.debug("No ALLOWED_IPS or UPS_IP in config.py, starting with empty allowed list")
                
                # Automatically add all IPs from UPS_DEVICES to allowed_ips
                if hasattr(ups_config, 'UPS_DEVICES') and isinstance(ups_config.UPS_DEVICES, dict):
                    ups_device_ips = list(ups_config.UPS_DEVICES.keys())
                    if ups_device_ips:
                        if allowed_ips is None:
                            allowed_ips = []
                        for ip in ups_device_ips:
                            if ip not in allowed_ips:
                                allowed_ips.append(ip)
                                logging.info(f"Auto-added UPS device IP to allowed list: {ip}")
                        logging.info(f"Allowed IPs now include {len(ups_device_ips)} UPS device(s) from UPS_DEVICES: {', '.join(ups_device_ips)}")
            else:
                logging.debug("config.py not found, no IP filtering (accepting all IPs)")
        except Exception as e:
            logging.debug(f"Error loading config.py: {e}, no IP filtering (accepting all IPs)")
    
    # Load email configuration: config.py first, then email_config.json as fallback
    email_recipients = None
    smtp_server = None
    smtp_port = 25
    smtp_use_tls = True
    smtp_username = None
    smtp_password = None
    from_email = None
    from_name = None
    
    # Try to load from config.py first
    try:
        import importlib.util
        config_path = Path(__file__).parent / 'config.py'
        if config_path.exists():
            spec = importlib.util.spec_from_file_location("ups_config", config_path)
            ups_config = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ups_config)
            
            if hasattr(ups_config, 'EMAIL_RECIPIENTS'):
                email_recipients = ups_config.EMAIL_RECIPIENTS if isinstance(ups_config.EMAIL_RECIPIENTS, list) else [ups_config.EMAIL_RECIPIENTS]
            if hasattr(ups_config, 'SMTP_SERVER'):
                smtp_server = ups_config.SMTP_SERVER
            if hasattr(ups_config, 'SMTP_PORT'):
                smtp_port = ups_config.SMTP_PORT
            if hasattr(ups_config, 'SMTP_USE_TLS'):
                smtp_use_tls = ups_config.SMTP_USE_TLS
            if hasattr(ups_config, 'SMTP_USERNAME'):
                smtp_username = ups_config.SMTP_USERNAME
            if hasattr(ups_config, 'SMTP_PASSWORD'):
                smtp_password = ups_config.SMTP_PASSWORD
            if hasattr(ups_config, 'FROM_EMAIL'):
                from_email = ups_config.FROM_EMAIL
            if hasattr(ups_config, 'FROM_NAME'):
                from_name = ups_config.FROM_NAME
    except Exception as e:
        logging.debug(f"Error loading email config from config.py: {e}")
    
    # Fall back to email_config.json if config.py doesn't have email settings
    if not email_recipients or not smtp_server or not from_email:
        email_config = load_email_config(args.email_config)
        if email_config:
            # Only use values from email_config.json if not already set from config.py
            if not email_recipients:
                email_recipients = email_config.get('email_recipients')
            if not smtp_server:
                smtp_server = email_config.get('smtp_server')
            if smtp_port == 25:  # Only use default if not set
                smtp_port = email_config.get('smtp_port', 25)
            if smtp_use_tls:  # Only use default if not set
                smtp_use_tls = email_config.get('smtp_use_tls', True)
            if not smtp_username:
                smtp_username = email_config.get('smtp_username')
            if not smtp_password:
                smtp_password = email_config.get('smtp_password')
            if not from_email:
                from_email = email_config.get('from_email')
            if not from_name:
                from_name = email_config.get('from_name')
    
    # Override with command-line arguments if provided (command-line has highest priority)
    if args.email_recipients:
        email_recipients = [email.strip() for email in args.email_recipients.split(',')]
    if args.smtp_server:
        smtp_server = args.smtp_server
    if args.smtp_port:
        smtp_port = args.smtp_port
    if args.smtp_no_tls:
        smtp_use_tls = False
    if args.smtp_username:
        smtp_username = args.smtp_username
    if args.smtp_password:
        smtp_password = args.smtp_password
    if args.from_email:
        from_email = args.from_email
    if args.from_name:
        from_name = args.from_name
    
    # Build GPIO pins dictionary - Command-line is primary method
    gpio_pins = {}
    gpio_blink_enabled = True
    gpio_blink_interval = 0.5
    gpio_active_high = True
    
    # Load GPIO settings from config.py first (as defaults)
    try:
        import importlib.util
        config_path = Path(__file__).parent / 'config.py'
        if config_path.exists():
            spec = importlib.util.spec_from_file_location("ups_config", config_path)
            ups_config = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ups_config)
            
            # Load GPIO pins from config (fallback if not in command-line)
            if hasattr(ups_config, 'GPIO_CRITICAL_PIN') and ups_config.GPIO_CRITICAL_PIN is not None:
                gpio_pins['critical'] = ups_config.GPIO_CRITICAL_PIN
            if hasattr(ups_config, 'GPIO_WARNING_PIN') and ups_config.GPIO_WARNING_PIN is not None:
                gpio_pins['warning'] = ups_config.GPIO_WARNING_PIN
            if hasattr(ups_config, 'GPIO_INFO_PIN') and ups_config.GPIO_INFO_PIN is not None:
                gpio_pins['info'] = ups_config.GPIO_INFO_PIN
            
            # Load GPIO settings from config (as defaults)
            if hasattr(ups_config, 'GPIO_BLINK_ENABLED'):
                gpio_blink_enabled = ups_config.GPIO_BLINK_ENABLED
            if hasattr(ups_config, 'GPIO_BLINK_INTERVAL'):
                gpio_blink_interval = ups_config.GPIO_BLINK_INTERVAL
            if hasattr(ups_config, 'GPIO_ACTIVE_HIGH'):
                gpio_active_high = ups_config.GPIO_ACTIVE_HIGH
    except Exception as e:
        logging.debug(f"Error loading GPIO config from config.py: {e}")
    
    # Override with command-line arguments (command-line takes precedence)
    if args.critical_pin:
        gpio_pins['critical'] = args.critical_pin
    if args.warning_pin:
        gpio_pins['warning'] = args.warning_pin
    if args.info_pin:
        gpio_pins['info'] = args.info_pin
    if args.gpio_no_blink:
        gpio_blink_enabled = False
    if args.gpio_blink_interval:
        gpio_blink_interval = args.gpio_blink_interval
    if args.gpio_active_low:
        gpio_active_high = False
    
    if gpio_pins:
        logging.info(f"GPIO pins configured: {gpio_pins} (blink={gpio_blink_enabled}, interval={gpio_blink_interval}s, active_high={gpio_active_high})")
    
    # Handle daemon mode (Linux only)
    if args.daemon:
        if is_windows:
            print("ERROR: Daemon mode is not supported on Windows", file=sys.stderr)
            sys.exit(1)
        
        # Convert PID file and log file paths to absolute before daemonization
        # (daemonization changes working directory to /)
        # But use script directory as base, not hardcoded absolute paths
        script_dir = Path(__file__).parent.absolute()
        current_dir = Path.cwd()
        
        pid_file_path = Path(args.pid_file)
        if not pid_file_path.is_absolute():
            # Make it relative to script directory (where script is located)
            # If it's just a filename, use it directly; if it has path components, resolve relative to script_dir
            if '/' in str(pid_file_path) or '\\' in str(pid_file_path):
                # Has path components - resolve relative to script_dir
                pid_file_path = (script_dir / pid_file_path).resolve()
            else:
                # Just a filename - place in script directory
                pid_file_path = script_dir / pid_file_path
        args.pid_file = str(pid_file_path)
        
        # Also make log file path absolute (relative to script directory)
        log_file_path = Path(args.log_file)
        if not log_file_path.is_absolute():
            # If path contains directory separators, resolve relative to script_dir
            if '/' in str(log_file_path) or '\\' in str(log_file_path):
                # Path like "logs/ups_traps.log" - resolve relative to script_dir
                log_file_path = (script_dir / log_file_path).resolve()
            else:
                # If just a filename, place in logs subdirectory
                log_file_path = script_dir / "logs" / log_file_path
        # Ensure logs directory exists (create it if it doesn't)
        try:
            log_file_path.parent.mkdir(parents=True, exist_ok=True)
            # Verify the directory was created
            if not log_file_path.parent.exists():
                print(f"ERROR: Failed to create logs directory: {log_file_path.parent}", file=sys.stderr)
        except Exception as e:
            print(f"WARNING: Could not create logs directory: {e}", file=sys.stderr)
        args.log_file = str(log_file_path)
        
        # Create an initial log entry file to verify the logs directory is accessible
        # This helps debug if the log file can't be created
        try:
            # Create a test entry in the log file to verify it's writable
            with open(log_file_path, 'a') as test_log:
                test_log.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] UPS SNMP Trap Receiver - Starting daemon initialization...\n")
                test_log.flush()
        except Exception as log_test_err:
            print(f"WARNING: Could not write initial log entry to {log_file_path}: {log_test_err}", file=sys.stderr)
        
        # Debug: Print the resolved log file path (only in non-daemon mode)
        if not args.daemon:
            print(f"Log file will be written to: {log_file_path}", flush=True)
        
        # Check if already running - use atomic file locking to prevent race conditions
        daemon_lock_fd = None
        daemon_lock_file = None
        
        try:
            import fcntl
            
            # Create a lock file for atomic PID file checking
            lock_file_path = pid_file_path.with_suffix('.lock')
            daemon_lock_file = str(lock_file_path)
            
            # Debug: Show lock file path
            try:
                rel_path = lock_file_path.relative_to(script_dir)
                lock_path_display = str(rel_path)
            except ValueError:
                lock_path_display = str(lock_file_path)
            print(f"DEBUG: Lock file path: {lock_path_display} (absolute: {lock_file_path})", flush=True)
            
            # Also check for lock files in old locations (in case of moved installation)
            old_lock_locations = [
                script_dir / "ups_trap_receiver.lock",
                script_dir.parent / "ups_trap_receiver.lock",
            ]
            # Check common old paths
            try:
                home_dir = Path.home()
                old_lock_locations.extend([
                    home_dir / "project" / "raspberry" / "ups_trap_receiver.lock",
                    Path("/home/mickylee/project/raspberry/ups_trap_receiver.lock"),
                ])
            except:
                pass
            
            # Clean up stale lock files in old locations
            for old_lock in old_lock_locations:
                if old_lock.exists() and old_lock != lock_file_path:
                    try:
                        with open(old_lock, 'r') as f:
                            old_pid_str = f.read().strip()
                            if old_pid_str.isdigit():
                                old_pid = int(old_pid_str)
                                try:
                                    os.kill(old_pid, 0)
                                    # Process is running - don't remove
                                    continue
                                except OSError:
                                    # Process doesn't exist - remove stale lock
                                    try:
                                        old_lock.unlink()
                                        print(f"Removed stale lock file from old location: {old_lock}", flush=True)
                                    except:
                                        pass
                    except:
                        # Can't read - try to remove anyway
                        try:
                            old_lock.unlink()
                        except:
                            pass
            
            # Check if lock file exists and try to read PID from it (if it contains a PID)
            # This helps detect stale locks
            print(f"DEBUG: Checking if lock file exists before acquiring lock: {lock_file_path.exists()}", flush=True)
            if lock_file_path.exists():
                print(f"DEBUG: Lock file exists, reading PID from it...", flush=True)
                try:
                    with open(lock_file_path, 'r') as f:
                        lock_pid_str = f.read().strip()
                        print(f"DEBUG: Read PID string from lock file: '{lock_pid_str}'", flush=True)
                        if lock_pid_str.isdigit():
                            lock_pid = int(lock_pid_str)
                            print(f"DEBUG: Parsed PID: {lock_pid}", flush=True)
                            # Check if the process that created the lock is still running
                            print(f"DEBUG: Checking if PID {lock_pid} is running...", flush=True)
                            
                            # Use multiple methods to verify PID is actually running
                            pid_is_running = False
                            
                            # Method 1: Check /proc (most reliable on Linux)
                            proc_path = Path(f"/proc/{lock_pid}/stat")
                            if proc_path.exists():
                                print(f"DEBUG: PID {lock_pid} found in /proc - verifying it's still valid...", flush=True)
                                try:
                                    # Try to read the stat file to ensure it's a real process
                                    with open(proc_path, 'r') as f:
                                        stat_data = f.read()
                                        # Parse process name from stat file (second field, in parentheses)
                                        import re
                                        match = re.match(r'(\d+) \((.+?)\)', stat_data)
                                        proc_name = None
                                        if match:
                                            proc_name = match.group(2)
                                            print(f"DEBUG: PID {lock_pid} process name: '{proc_name}'", flush=True)
                                            
                                            # Check if it's a zombie process (state 'Z') - check before process name validation
                                            if ' Z ' in stat_data:
                                                print(f"DEBUG: PID {lock_pid} is a zombie process - treating as stale", flush=True)
                                                pid_is_running = False
                                            else:
                                                # Check if it's actually our trap receiver process
                                                if 'ups_snmp_trap_receiver' in proc_name or 'python' in proc_name.lower():
                                                    print(f"DEBUG: PID {lock_pid} appears to be our trap receiver process", flush=True)
                                                    pid_is_running = True
                                                else:
                                                    print(f"DEBUG: WARNING - PID {lock_pid} is '{proc_name}', not our trap receiver - treating as stale", flush=True)
                                                    pid_is_running = False
                                        else:
                                            print(f"DEBUG: Could not parse process name from stat file", flush=True)
                                            # If we can't parse, assume it's running if /proc exists (conservative approach)
                                            pid_is_running = True
                                except Exception as proc_err:
                                    print(f"DEBUG: Could not read /proc/{lock_pid}/stat: {proc_err} - treating as stale", flush=True)
                                    pid_is_running = False
                            else:
                                print(f"DEBUG: PID {lock_pid} NOT found in /proc - treating as stale", flush=True)
                                pid_is_running = False
                            
                            # Method 2: Double-check with os.kill (but don't trust it alone)
                            if pid_is_running:
                                try:
                                    os.kill(lock_pid, 0)
                                    print(f"DEBUG: os.kill also confirms PID {lock_pid} is running", flush=True)
                                except OSError as kill_err:
                                    print(f"DEBUG: WARNING - /proc says running but os.kill failed: {kill_err} - treating as stale", flush=True)
                                    pid_is_running = False
                            
                            if pid_is_running:
                                # Process is running - lock is valid
                                print(f"DEBUG: PID {lock_pid} IS running - lock is valid, exiting", flush=True)
                                # Show relative path if possible
                                try:
                                    rel_path = lock_file_path.relative_to(script_dir)
                                    lock_path_display = str(rel_path)
                                except ValueError:
                                    lock_path_display = str(lock_file_path)
                                print(f"ERROR: Another instance is starting (PID: {lock_pid}). Please wait or check: {lock_path_display}", file=sys.stderr)
                                print(f"DEBUG: To verify, run: ps -p {lock_pid} || kill -0 {lock_pid}", file=sys.stderr)
                                sys.exit(1)
                            else:
                                # Process doesn't exist - stale lock, remove it
                                print(f"DEBUG: PID {lock_pid} is NOT running - removing stale lock", flush=True)
                                try:
                                    lock_file_path.unlink()
                                    try:
                                        rel_path = lock_file_path.relative_to(script_dir)
                                        lock_path_display = str(rel_path)
                                    except ValueError:
                                        lock_path_display = str(lock_file_path)
                                    print(f"Removed stale lock file: {lock_path_display} (PID: {lock_pid} not running)", flush=True)
                                except Exception as unlink_err:
                                    print(f"DEBUG: Failed to remove stale lock file: {unlink_err}", flush=True)
                                    pass
                        else:
                            print(f"DEBUG: Lock file contains non-numeric PID: '{lock_pid_str}' - will try to remove", flush=True)
                            try:
                                lock_file_path.unlink()
                                print(f"DEBUG: Removed lock file with invalid PID content", flush=True)
                            except:
                                pass
                except Exception as read_err:
                    print(f"DEBUG: Failed to read lock file: {read_err}", flush=True)
                    # Try to remove invalid lock file
                    try:
                        lock_file_path.unlink()
                        print(f"DEBUG: Removed unreadable lock file", flush=True)
                    except:
                        pass
            else:
                print(f"DEBUG: Lock file does not exist yet - will create it", flush=True)
            
            # Try to acquire exclusive lock (non-blocking)
            # Retry loop to handle stale locks
            max_retries = 2
            retry_count = 0
            lock_acquired = False
            
            while retry_count < max_retries and not lock_acquired:
                print(f"DEBUG: Attempt {retry_count + 1}/{max_retries} - Opening lock file: {daemon_lock_file}", flush=True)
                lock_fd = os.open(daemon_lock_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
                print(f"DEBUG: Lock file opened, file descriptor: {lock_fd}", flush=True)
                try:
                    print(f"DEBUG: Attempting to acquire exclusive lock (non-blocking)...", flush=True)
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    # Got the lock - write our PID
                    current_pid = os.getpid()
                    print(f"DEBUG: Lock acquired successfully! Writing PID {current_pid} to lock file...", flush=True)
                    try:
                        os.write(lock_fd, str(current_pid).encode())
                        os.fsync(lock_fd)
                        print(f"DEBUG: PID {current_pid} written to lock file: {daemon_lock_file}", flush=True)
                    except Exception as write_err:
                        print(f"DEBUG: Warning - Failed to write PID to lock file: {write_err}", flush=True)
                    daemon_lock_fd = lock_fd
                    lock_acquired = True
                    print(f"DEBUG: Lock file created and locked successfully", flush=True)
                    break
                except (IOError, OSError) as e:
                    # Lock is held by another process
                    print(f"DEBUG: Failed to acquire lock (attempt {retry_count + 1}): {e}", flush=True)
                    os.close(lock_fd)
                    
                    # Check if lock file exists and read PID
                    print(f"DEBUG: Checking if lock file exists: {lock_file_path.exists()}", flush=True)
                    lock_pid = None
                    if lock_file_path.exists():
                        print(f"DEBUG: Lock file exists, reading PID from it...", flush=True)
                        try:
                            with open(lock_file_path, 'r') as f:
                                lock_pid_str = f.read().strip()
                                if lock_pid_str.isdigit():
                                    lock_pid = int(lock_pid_str)
                                    print(f"DEBUG: Read PID {lock_pid} from lock file", flush=True)
                                else:
                                    print(f"DEBUG: Lock file contains non-numeric value: '{lock_pid_str}'", flush=True)
                        except Exception as read_err:
                            print(f"DEBUG: Failed to read PID from lock file: {read_err}", flush=True)
                    
                    # Check if the process is actually running
                    if lock_pid is not None:
                        print(f"DEBUG: Checking if PID {lock_pid} is running...", flush=True)
                        try:
                            os.kill(lock_pid, 0)
                            # Process IS running - lock is valid, exit
                            print(f"DEBUG: PID {lock_pid} IS running - lock is valid", flush=True)
                            try:
                                rel_path = lock_file_path.relative_to(script_dir)
                                lock_path_display = str(rel_path)
                            except ValueError:
                                lock_path_display = str(lock_file_path)
                            print(f"ERROR: Another instance is starting (PID: {lock_pid}). Please wait or check: {lock_path_display}", file=sys.stderr)
                            print(f"       To stop it, run: kill {lock_pid} or ./stop.sh", file=sys.stderr)
                            sys.exit(1)
                        except OSError:
                            # Process does NOT exist - stale lock, remove it
                            print(f"DEBUG: PID {lock_pid} is NOT running - removing stale lock", flush=True)
                            try:
                                if lock_file_path.exists():
                                    lock_file_path.unlink()
                                try:
                                    rel_path = lock_file_path.relative_to(script_dir)
                                    lock_path_display = str(rel_path)
                                except ValueError:
                                    lock_path_display = str(lock_file_path)
                                print(f"Removed stale lock file: {lock_path_display} (PID: {lock_pid} not running)", flush=True)
                                print(f"DEBUG: Will retry acquiring lock (retry {retry_count + 1}/{max_retries})", flush=True)
                                retry_count += 1
                                # Retry acquiring lock
                                continue
                            except Exception as cleanup_error:
                                # Couldn't remove - suggest manual removal
                                try:
                                    rel_path = lock_file_path.relative_to(script_dir)
                                    lock_path_display = str(rel_path)
                                except ValueError:
                                    lock_path_display = str(lock_file_path)
                                print(f"ERROR: Lock file exists but process (PID: {lock_pid}) is not running.", file=sys.stderr)
                                print(f"       Could not automatically remove stale lock: {lock_path_display}", file=sys.stderr)
                                print(f"       Please remove manually: rm -f {lock_path_display}", file=sys.stderr)
                                sys.exit(1)
                    else:
                        # Lock file doesn't exist or can't read PID - try to remove and retry
                        if lock_file_path.exists():
                            try:
                                lock_file_path.unlink()
                                try:
                                    rel_path = lock_file_path.relative_to(script_dir)
                                    lock_path_display = str(rel_path)
                                except ValueError:
                                    lock_path_display = str(lock_file_path)
                                print(f"Removed lock file with invalid PID: {lock_path_display}", flush=True)
                                retry_count += 1
                                continue
                            except:
                                pass
                        # If we can't remove it, exit with error
                        try:
                            rel_path = lock_file_path.relative_to(script_dir)
                            lock_path_display = str(rel_path)
                        except ValueError:
                            lock_path_display = str(lock_file_path)
                        print(f"ERROR: Could not acquire lock. Another process may be starting.", file=sys.stderr)
                        print(f"       Lock file: {lock_path_display}", file=sys.stderr)
                        print(f"       Try again in a moment or remove manually: rm -f {lock_path_display}", file=sys.stderr)
                        sys.exit(1)
            
            if not lock_acquired:
                # Should not reach here, but just in case
                print(f"DEBUG: Failed to acquire lock after {max_retries} attempts", flush=True)
                print(f"ERROR: Could not acquire lock after {max_retries} attempts.", file=sys.stderr)
                sys.exit(1)
            else:
                print(f"DEBUG: Lock acquisition completed successfully", flush=True)
            
            # We have the lock, now check PID file
            print(f"DEBUG: Proceeding to check PID file...", flush=True)
            if pid_file_path.exists():
                try:
                    with open(pid_file_path, 'r') as f:
                        old_pid = int(f.read().strip())
                    # Check if process is still running
                    try:
                        os.kill(old_pid, 0)
                        # Process exists - release lock and exit
                        fcntl.flock(lock_fd, fcntl.LOCK_UN)
                        os.close(lock_fd)
                        if lock_file_path.exists():
                            lock_file_path.unlink()
                        print(f"ERROR: Process is already running (PID: {old_pid})", file=sys.stderr)
                        print(f"       If not, remove PID file: {pid_file_path}", file=sys.stderr)
                        sys.exit(1)
                    except OSError:
                        # Process doesn't exist, remove stale PID file
                        pid_file_path.unlink()
                        print(f"Removed stale PID file: {pid_file_path}", flush=True)
                except (ValueError, IOError):
                    # Invalid PID file, remove it
                    pid_file_path.unlink()
            
            # Keep lock until after daemonization and PID file is written
            # Store for later release (file descriptor is inherited by child process after fork)
            daemon_lock_fd = lock_fd
            
        except (ImportError, AttributeError):
            # fcntl not available (Windows or unsupported system)
            # Fall back to simple check without locking
            if pid_file_path.exists():
                try:
                    with open(pid_file_path, 'r') as f:
                        old_pid = int(f.read().strip())
                    # Check if process is still running
                    try:
                        os.kill(old_pid, 0)
                        print(f"ERROR: Process is already running (PID: {old_pid})", file=sys.stderr)
                        print(f"       If not, remove PID file: {pid_file_path}", file=sys.stderr)
                        sys.exit(1)
                    except OSError:
                        # Process doesn't exist, remove stale PID file
                        pid_file_path.unlink()
                        print(f"Removed stale PID file: {pid_file_path}", flush=True)
                except (ValueError, IOError):
                    # Invalid PID file, remove it
                    pid_file_path.unlink()
            daemon_lock_fd = None
            daemon_lock_file = None
        
        # Fork to create daemon
        # Suppress fork warning for multi-threaded process (we handle it safely)
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=DeprecationWarning, message='.*fork.*')
            try:
                # First fork
                pid = os.fork()
                if pid > 0:
                    # Parent process - exit
                    sys.exit(0)
            except OSError as e:
                print(f"ERROR: First fork failed: {e}", file=sys.stderr)
                sys.exit(1)
        
        # Decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)
        
        # Second fork
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=DeprecationWarning, message='.*fork.*')
            try:
                pid = os.fork()
                if pid > 0:
                    # Parent process - exit
                    sys.exit(0)
            except OSError as e:
                print(f"ERROR: Second fork failed: {e}", file=sys.stderr)
                sys.exit(1)
        
        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Close file descriptors (optional, but good practice)
        try:
            si = open(os.devnull, 'r')
            so = open(os.devnull, 'a+')
            se = open(os.devnull, 'a+')
            os.dup2(si.fileno(), sys.stdin.fileno())
            os.dup2(so.fileno(), sys.stdout.fileno())
            os.dup2(se.fileno(), sys.stderr.fileno())
        except Exception:
            pass  # Ignore errors
        
        # Write PID file immediately after daemonization
        # (before creating UPSTrapReceiver, so we can catch early errors)
        try:
            pid_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(pid_file_path, 'w') as f:
                f.write(str(os.getpid()))
            
            # Release the lock now that PID file is written
            # Note: After fork, the file descriptor is still valid in child process
            if daemon_lock_fd is not None:
                try:
                    import fcntl
                    fcntl.flock(daemon_lock_fd, fcntl.LOCK_UN)
                    os.close(daemon_lock_fd)
                    # Remove lock file
                    if daemon_lock_file and os.path.exists(daemon_lock_file):
                        os.unlink(daemon_lock_file)
                except:
                    pass
        except Exception as e:
            # Release lock on error
            if daemon_lock_fd is not None:
                try:
                    import fcntl
                    fcntl.flock(daemon_lock_fd, fcntl.LOCK_UN)
                    os.close(daemon_lock_fd)
                    if daemon_lock_file and os.path.exists(daemon_lock_file):
                        os.unlink(daemon_lock_file)
                except:
                    pass
            # Can't use logger yet, write to log file directly
            # Write error to the log file location (in logs directory)
            try:
                # Use the log file path that was configured (args.log_file is set earlier in daemon mode)
                if 'args' in globals() and hasattr(args, 'log_file'):
                    error_log_path = Path(args.log_file)
                else:
                    # Fallback to default logs location
                    error_log_path = script_dir / "logs" / get_log_filename()
                # Ensure logs directory exists
                error_log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(error_log_path, 'a') as err_file:
                    err_file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Failed to write PID file: {e}\n")
                    err_file.flush()
            except Exception as log_err:
                # If we can't write to log file, at least try to write to stderr
                # (though it's redirected to /dev/null in daemon mode)
                try:
                    print(f"ERROR: Failed to write PID file: {e}", file=sys.stderr, flush=True)
                    print(f"ERROR: Also failed to write to log file ({error_log_path}): {log_err}", file=sys.stderr, flush=True)
                except:
                    pass
            sys.exit(1)
    
    # Create and start receiver
    try:
        if not args.daemon:
            print(f"Creating UPSTrapReceiver instance...", flush=True)
        receiver = UPSTrapReceiver(
            log_file=args.log_file, 
            port=args.port,
            allowed_ips=allowed_ips,
            email_recipients=email_recipients,
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            smtp_use_tls=smtp_use_tls,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
            from_email=from_email,
            from_name=from_name,
            gpio_pins=gpio_pins if gpio_pins else None,
            gpio_blink_enabled=gpio_blink_enabled,
            gpio_blink_interval=gpio_blink_interval,
            gpio_active_high=gpio_active_high,
            pid_file=args.pid_file
        )
        if not args.daemon:
            print(f"Starting receiver on port {args.port}...", flush=True)
        receiver.start()
    except Exception as e:
        # Log error to log file if possible
        try:
            error_log_path = Path(args.log_file) if hasattr(args, 'log_file') else script_dir / "logs" / get_log_filename()
            error_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(error_log_path, 'a') as err_file:
                err_file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Failed to start receiver: {e}\n")
                import traceback
                err_file.write(traceback.format_exc())
                err_file.flush()
        except:
            pass
        
        if not args.daemon:
            print(f"ERROR: Failed to start receiver: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc()
        
        # Remove PID file if it exists (cleanup)
        if args.pid_file and Path(args.pid_file).exists():
            try:
                Path(args.pid_file).unlink()
            except:
                pass
        
        sys.exit(1)


if __name__ == '__main__':
    main()

