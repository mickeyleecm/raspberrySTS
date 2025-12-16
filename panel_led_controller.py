#!/usr/bin/env python3
"""
Panel LED Controller
Controls panel LEDs based on AlarmMap configuration.

This module provides a class to control individual LEDs or groups of LEDs
(by color) based on the PANEL_LED_MAPPING in AlarmMap.py.

Features:
- Enable/disable individual LEDs by LED number
- Enable/disable all green LEDs
- Enable all red LEDs
- Read LED configuration from AlarmMap.py
- Support for active-high and active-low GPIO logic

Usage Examples:
==============

1. As a Python Module (for use in other programs like ups_snmp_trap_receiver_v3.py):
   ---------------------------------------------------------------------------------
   from panel_led_controller import PanelLEDController
   
   # Create controller instance
   controller = PanelLEDController(active_high=True)
   
   # Enable all green LEDs on startup
   controller.enable_all_green_leds()
   
   # Enable a specific LED (LED 2)
   controller.enable_led(2)
   
   # Disable a specific LED (LED 2)
   controller.disable_led(2)
   
   # Enable all red LEDs
   controller.enable_all_red_leds()
   
   # Disable all green LEDs
   controller.disable_all_green_leds()
   
   # List all green LEDs
   controller.list_leds(color='Green')
   
   # Get LED state
   state = controller.get_led_state(2)  # Returns True/False/None
   
   # Enable buzzer - one-time beep pattern (3 beeps)
   controller.enable_buzzer(continuous=False)
   
   # Enable continuous buzzer (continuous tone)
   controller.enable_buzzer(continuous=True, frequency=1000)
   
   # Enable continuous beep pattern (beep, pause, beep, pause...)
   controller.enable_buzzer(continuous=True, beep_pattern=True, frequency=1000, beep_duration=0.3, beep_pause=0.3)
   
   # Enable continuous beep pattern with custom timing
   controller.enable_buzzer(continuous=True, beep_pattern=True, frequency=2000, beep_duration=0.2, beep_pause=0.5)
   
   # Disable buzzer (stops continuous tone or beep pattern)
   controller.disable_buzzer()
   
   # Cleanup GPIO (optional)
   controller.cleanup()
   

2. As a Standalone Program (command-line):
   ----------------------------------------
   # Enable all green LEDs
   python panel_led_controller.py --enable-all-green
   
   # Disable all green LEDs
   python panel_led_controller.py --disable-all-green
   
   # Enable all red LEDs
   python panel_led_controller.py --enable-all-red
   
   # Disable all red LEDs
   python panel_led_controller.py --disable-all-red

   # Enable the buzzer/speaker (plays critical alarm: 3 beeps)
   python panel_led_controller.py --enable-buzzer

   # Disable the buzzer/speaker
   python panel_led_controller.py --disable-buzzer

   # Play beep patterns
   python panel_led_controller.py --play-beep 1      # Play 1 beep
   python panel_led_controller.py --play-beep 2      # Play 2 beeps
   python panel_led_controller.py --play-beep 5      # Play 5 beeps

   # Play alarm patterns
   python panel_led_controller.py --play-critical    # Play critical alarm (3 beeps)
   python panel_led_controller.py --play-warning    # Play warning alarm (2 beeps)
   python panel_led_controller.py --play-info        # Play info beep (1 beep)

   # Play custom tone
   python panel_led_controller.py --play-tone 1000 0.5    # Play 1000Hz for 0.5 seconds
   python panel_led_controller.py --play-tone 2000 1.0    # Play 2000Hz for 1.0 second

   # Enable continuous buzzer (continuous tone)
   python panel_led_controller.py --enable-buzzer-continuous

   # Enable continuous buzzer with custom frequency
   python panel_led_controller.py --enable-buzzer-continuous --buzzer-frequency 2000

   # Enable continuous beep pattern (beep, pause, beep, pause...)
   python panel_led_controller.py --enable-buzzer-continuous --buzzer-beep-pattern

   # Enable continuous beep pattern with custom timing
   python panel_led_controller.py --enable-buzzer-continuous --buzzer-beep-pattern --beep-duration 0.2 --beep-pause 0.5

   # Enable continuous beep pattern with custom frequency and timing
   python panel_led_controller.py --enable-buzzer-continuous --buzzer-beep-pattern --buzzer-frequency 2000 --beep-duration 0.3 --beep-pause 0.3

   # Stop buzzer (stops continuous tone or beep pattern)
   python panel_led_controller.py --disable-buzzer
   # Note: For continuous buzzer, press Ctrl+C to stop, or use --disable-buzzer in another terminal


   # Enable a specific LED (LED 2)
   python panel_led_controller.py --enable-led 2
   
   # Disable a specific LED (LED 2)
   python panel_led_controller.py --disable-led 2
   
   # List all green LEDs
   python panel_led_controller.py --list --color green
   
   # List all red LEDs
   python panel_led_controller.py --list --color red
   
   # List all LEDs
   python panel_led_controller.py --list
   
   # Use active-low logic (LED on with LOW signal)
   python panel_led_controller.py --enable-all-green --active-low
   
   # Use active-high logic (LED on with HIGH signal) - default
   python panel_led_controller.py --enable-all-green --active-high
   
   # Enable verbose logging
   python panel_led_controller.py --enable-all-green --verbose
   
   # Multiple operations in one command
   python panel_led_controller.py --enable-all-green --enable-led 2 --list

3. Integration with ups_snmp_trap_receiver_v3.py:
   -----------------------------------------------
   from panel_led_controller import PanelLEDController
   
   # In __init__ method:
   self.led_controller = PanelLEDController(active_high=self.gpio_active_high)
   
   # In start() method:
   self.led_controller.enable_all_green_leds()  # Enable all green LEDs on startup
   
   # In trap processing:
   if alarm_condition:
       self.led_controller.enable_all_red_leds()
   else:
       self.led_controller.enable_all_green_leds()
"""

import sys
import argparse
import logging
import time
import threading
from typing import Optional, List, Dict, Any

# Buzzer configuration constants (matching test_speaker_pin.py)
PWM_FREQUENCY = 1000  # Hz
BEEP_DURATION = 0.3  # seconds
BEEP_PAUSE = 0.1  # seconds

# Try to import BUZZER_VOLUME from config.py
try:
    import config
    DEFAULT_VOLUME = getattr(config, 'BUZZER_VOLUME', 50)  # Use BUZZER_VOLUME from config.py, default to 50 if not found
except (ImportError, AttributeError):
    DEFAULT_VOLUME = 50  # 50% duty cycle (0-100), controls volume (fallback if config.py not available)

# Try to import AlarmMap
try:
    from AlarmMap import (
        PANEL_LED_MAPPING,
        get_leds_by_color,
        get_gpio_pin_by_led,
        get_led_info_by_gpio
    )
    ALARMMAP_AVAILABLE = True
except ImportError:
    ALARMMAP_AVAILABLE = False
    PANEL_LED_MAPPING = {}
    get_leds_by_color = None
    get_gpio_pin_by_led = None
    get_led_info_by_gpio = None
    print("WARNING: AlarmMap.py not found. LED control will be limited.", file=sys.stderr)

# Try to import RPi.GPIO
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False
    GPIO = None
    print("WARNING: RPi.GPIO not available. GPIO operations will be simulated.", file=sys.stderr)


class PanelLEDController:
    """
    Controller for panel LEDs based on AlarmMap configuration.
    
    This class provides methods to control individual LEDs or groups of LEDs
    based on their color (Green, Red) as defined in AlarmMap.PANEL_LED_MAPPING.
    
    Example:
        >>> controller = PanelLEDController(active_high=True)
        >>> controller.enable_led(2)  # Enable LED 2
        >>> controller.enable_all_green_leds()  # Enable all green LEDs
        >>> controller.enable_all_red_leds()  # Enable all red LEDs
        >>> controller.disable_led(2)  # Disable LED 2
        >>> controller.cleanup()  # Cleanup GPIO
    """
    
    def __init__(self, active_high: bool = True, gpio_mode: int = None, blink_interval: float = 0.5):
        """
        Initialize Panel LED Controller.
        
        Args:
            active_high: True if LEDs are active-high (LED on with HIGH signal),
                        False if active-low (LED on with LOW signal). Default: True
            gpio_mode: GPIO mode (GPIO.BCM or GPIO.BOARD). If None, uses GPIO.BCM. Default: None
            blink_interval: Blink interval in seconds for red LEDs (default: 0.5)
        """
        self.active_high = active_high
        self.gpio_mode = gpio_mode if gpio_mode is not None else (GPIO.BCM if GPIO_AVAILABLE else None)
        self.gpio_initialized = False
        self.led_states = {}  # Track LED states: {led_number: bool}
        self.blink_interval = blink_interval  # Blink interval for red LEDs
        self.blink_threads = {}  # Track blink threads: {led_number: Thread}
        self.blink_stop_flags = {}  # Track blink stop events: {led_number: threading.Event}
        
        # Buzzer continuous tone tracking
        self._buzzer_thread = None  # Track continuous buzzer thread
        self._buzzer_stop_event = None  # Event to stop continuous buzzer
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        if not ALARMMAP_AVAILABLE:
            self.logger.warning("AlarmMap not available - LED control will be limited")
        
        if not GPIO_AVAILABLE:
            self.logger.warning("RPi.GPIO not available - GPIO operations will be simulated")
        else:
            self._init_gpio()
    
    def _init_gpio(self):
        """Initialize GPIO if available."""
        if not GPIO_AVAILABLE:
            return
        
        try:
            GPIO.setmode(self.gpio_mode)
            GPIO.setwarnings(False)
            self.gpio_initialized = True
            self.logger.info(f"GPIO initialized (mode: {'BCM' if self.gpio_mode == GPIO.BCM else 'BOARD'}, active_high: {self.active_high})")
        except Exception as e:
            self.logger.error(f"Failed to initialize GPIO: {e}")
            self.gpio_initialized = False
    
    def _get_led_info(self, led_number: int) -> Optional[Dict[str, Any]]:
        """
        Get LED information from AlarmMap.
        
        Args:
            led_number: LED number (1-14) or 'speaker', 'mute', 'reset'
        
        Returns:
            Dictionary with LED info or None if not found
        """
        if not ALARMMAP_AVAILABLE:
            return None
        
        if led_number not in PANEL_LED_MAPPING:
            return None
        
        led_info = PANEL_LED_MAPPING[led_number].copy()
        led_info['led_number'] = led_number
        return led_info
    
    def _set_gpio_pin(self, gpio_pin: int, state: bool):
        """
        Set GPIO pin state.
        
        Args:
            gpio_pin: GPIO pin number
            state: True to enable LED, False to disable
        """
        if not GPIO_AVAILABLE:
            self.logger.debug(f"[SIMULATED] GPIO pin {gpio_pin} -> {'HIGH' if (state and self.active_high) or (not state and not self.active_high) else 'LOW'}")
            return
        
        if not self.gpio_initialized:
            self._init_gpio()
            if not self.gpio_initialized:
                self.logger.error("GPIO not initialized - cannot set pin")
                return
        
        try:
            # Setup pin as output if not already set
            GPIO.setup(gpio_pin, GPIO.OUT)
            
            # Set pin state based on active_high logic
            if self.active_high:
                GPIO.output(gpio_pin, GPIO.HIGH if state else GPIO.LOW)
            else:
                GPIO.output(gpio_pin, GPIO.LOW if state else GPIO.HIGH)
            
            self.logger.debug(f"GPIO pin {gpio_pin} set to {'ON' if state else 'OFF'} (active_high: {self.active_high})")
        except Exception as e:
            self.logger.error(f"Failed to set GPIO pin {gpio_pin}: {e}")
    
    def _start_blink(self, led_number: int, gpio_pin: int):
        """
        Start blinking a LED in a separate thread.
        
        Args:
            led_number: LED number
            gpio_pin: GPIO pin number
        """
        # Stop any existing blink for this LED
        self._stop_blink(led_number)
        
        # Create stop event for this LED
        stop_event = threading.Event()
        self.blink_stop_flags[led_number] = stop_event
        
        def blink_loop():
            state = False
            while not stop_event.is_set():
                try:
                    self._set_gpio_pin(gpio_pin, state)
                    state = not state
                    # Wait for blink interval, but check if stop event is set
                    if stop_event.wait(self.blink_interval):
                        break
                except Exception as e:
                    self.logger.error(f"Error in blink loop for LED {led_number}: {e}")
                    break
        
        # Create and start blink thread
        thread = threading.Thread(target=blink_loop, daemon=True)
        self.blink_threads[led_number] = thread
        thread.start()
        self.led_states[led_number] = True  # Mark as enabled (blinking)
    
    def _stop_blink(self, led_number: int):
        """
        Stop blinking for a specific LED.
        
        Args:
            led_number: LED number
        """
        if led_number in self.blink_stop_flags:
            self.blink_stop_flags[led_number].set()
        
        if led_number in self.blink_threads:
            thread = self.blink_threads[led_number]
            if thread.is_alive():
                thread.join(timeout=1.0)
            del self.blink_threads[led_number]
        
        if led_number in self.blink_stop_flags:
            del self.blink_stop_flags[led_number]
    
    def enable_led(self, led_number: int) -> bool:
        """
        Enable a single LED by LED number.
        
        Args:
            led_number: LED number (1-14) or 'speaker', 'mute', 'reset'
        
        Returns:
            True if LED was enabled, False otherwise
        """
        led_info = self._get_led_info(led_number)
        if not led_info:
            self.logger.error(f"LED {led_number} not found in AlarmMap")
            return False
        
        gpio_pin = led_info.get('gpio_pin')
        if gpio_pin is None:
            self.logger.error(f"LED {led_number} has no GPIO pin configured")
            return False
        
        signal_type = led_info.get('signal_type')
        if signal_type != 'Output':
            self.logger.warning(f"LED {led_number} is not an output (signal_type: {signal_type}) - skipping")
            return False
        
        led_name = led_info.get('name', f'LED {led_number}')
        color = led_info.get('color', 'Unknown')
        
        try:
            # Stop any existing blinking for this LED first
            self._stop_blink(led_number)
            
            # If LED is red, make it blink; otherwise, turn it on solid
            if color and color.lower() == 'red':
                self._start_blink(led_number, gpio_pin)
                self.logger.info(f"Enabled LED {led_number} ({led_name}, {color}) on GPIO pin {gpio_pin} - BLINKING")
            else:
                self._set_gpio_pin(gpio_pin, True)
                self.led_states[led_number] = True
                self.logger.info(f"Enabled LED {led_number} ({led_name}, {color}) on GPIO pin {gpio_pin}")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to enable LED {led_number}: {e}")
            return False
    
    def disable_led(self, led_number: int) -> bool:
        """
        Disable a single LED by LED number.
        Stops blinking if the LED was blinking.
        
        Args:
            led_number: LED number (1-14) or 'speaker', 'mute', 'reset'
        
        Returns:
            True if LED was disabled, False otherwise
        """
        led_info = self._get_led_info(led_number)
        if not led_info:
            self.logger.error(f"LED {led_number} not found in AlarmMap")
            return False
        
        gpio_pin = led_info.get('gpio_pin')
        if gpio_pin is None:
            self.logger.error(f"LED {led_number} has no GPIO pin configured")
            return False
        
        signal_type = led_info.get('signal_type')
        if signal_type != 'Output':
            self.logger.warning(f"LED {led_number} is not an output (signal_type: {signal_type}) - skipping")
            return False
        
        led_name = led_info.get('name', f'LED {led_number}')
        color = led_info.get('color', 'Unknown')
        
        try:
            # Stop blinking first (if it was blinking)
            self._stop_blink(led_number)
            
            # Turn off the LED
            self._set_gpio_pin(gpio_pin, False)
            self.led_states[led_number] = False
            self.logger.info(f"Disabled LED {led_number} ({led_name}, {color}) on GPIO pin {gpio_pin}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to disable LED {led_number}: {e}")
            return False
    
    def enable_all_green_leds(self) -> int:
        """
        Enable all green LEDs from AlarmMap.
        
        Returns:
            Number of green LEDs enabled
        """
        if not ALARMMAP_AVAILABLE or get_leds_by_color is None:
            self.logger.error("AlarmMap not available - cannot enable green LEDs")
            return 0
        
        green_leds = get_leds_by_color('Green')
        if not green_leds:
            self.logger.info("No green LEDs found in AlarmMap")
            return 0
        
        self.logger.info(f"Enabling {len(green_leds)} green LED(s)...")
        enabled_count = 0
        
        for led_info in green_leds:
            led_number = led_info.get('led_number')
            gpio_pin = led_info.get('gpio_pin')
            led_name = led_info.get('name', f'LED {led_number}')
            
            if gpio_pin is None:
                self.logger.warning(f"Green LED {led_number} ({led_name}) has no GPIO pin - skipping")
                continue
            
            signal_type = led_info.get('signal_type')
            if signal_type != 'Output':
                self.logger.warning(f"Green LED {led_number} ({led_name}) is not an output - skipping")
                continue
            
            try:
                self._set_gpio_pin(gpio_pin, True)
                self.led_states[led_number] = True
                enabled_count += 1
                self.logger.info(f"  Enabled green LED {led_number} ({led_name}) on GPIO pin {gpio_pin}")
            except Exception as e:
                self.logger.error(f"Failed to enable green LED {led_number} ({led_name}): {e}")
        
        self.logger.info(f"Successfully enabled {enabled_count} green LED(s)")
        return enabled_count
    
    def disable_all_green_leds(self) -> int:
        """
        Disable all green LEDs from AlarmMap.
        
        Returns:
            Number of green LEDs disabled
        """
        if not ALARMMAP_AVAILABLE or get_leds_by_color is None:
            self.logger.error("AlarmMap not available - cannot disable green LEDs")
            return 0
        
        green_leds = get_leds_by_color('Green')
        if not green_leds:
            self.logger.info("No green LEDs found in AlarmMap")
            return 0
        
        self.logger.info(f"Disabling {len(green_leds)} green LED(s)...")
        disabled_count = 0
        
        for led_info in green_leds:
            led_number = led_info.get('led_number')
            gpio_pin = led_info.get('gpio_pin')
            led_name = led_info.get('name', f'LED {led_number}')
            
            if gpio_pin is None:
                self.logger.warning(f"Green LED {led_number} ({led_name}) has no GPIO pin - skipping")
                continue
            
            signal_type = led_info.get('signal_type')
            if signal_type != 'Output':
                self.logger.warning(f"Green LED {led_number} ({led_name}) is not an output - skipping")
                continue
            
            try:
                self._set_gpio_pin(gpio_pin, False)
                self.led_states[led_number] = False
                disabled_count += 1
                self.logger.info(f"  Disabled green LED {led_number} ({led_name}) on GPIO pin {gpio_pin}")
            except Exception as e:
                self.logger.error(f"Failed to disable green LED {led_number} ({led_name}): {e}")
        
        self.logger.info(f"Successfully disabled {disabled_count} green LED(s)")
        return disabled_count
    
    def enable_all_red_leds(self) -> int:
        """
        Enable all red LEDs from AlarmMap.
        
        Returns:
            Number of red LEDs enabled
        """
        if not ALARMMAP_AVAILABLE or get_leds_by_color is None:
            self.logger.error("AlarmMap not available - cannot enable red LEDs")
            return 0
        
        red_leds = get_leds_by_color('Red')
        if not red_leds:
            self.logger.info("No red LEDs found in AlarmMap")
            return 0
        
        self.logger.info(f"Enabling {len(red_leds)} red LED(s)...")
        enabled_count = 0
        
        for led_info in red_leds:
            led_number = led_info.get('led_number')
            gpio_pin = led_info.get('gpio_pin')
            led_name = led_info.get('name', f'LED {led_number}')
            
            if gpio_pin is None:
                self.logger.warning(f"Red LED {led_number} ({led_name}) has no GPIO pin - skipping")
                continue
            
            signal_type = led_info.get('signal_type')
            if signal_type != 'Output':
                self.logger.warning(f"Red LED {led_number} ({led_name}) is not an output - skipping")
                continue
            
            try:
                # Red LEDs should blink, so use _start_blink instead of _set_gpio_pin
                self._start_blink(led_number, gpio_pin)
                enabled_count += 1
                self.logger.info(f"  Enabled red LED {led_number} ({led_name}) on GPIO pin {gpio_pin} - BLINKING")
            except Exception as e:
                self.logger.error(f"Failed to enable red LED {led_number} ({led_name}): {e}")
        
        self.logger.info(f"Successfully enabled {enabled_count} red LED(s) (all blinking)")
        return enabled_count
    
    def disable_all_red_leds(self) -> int:
        """
        Disable all red LEDs from AlarmMap.
        
        Returns:
            Number of red LEDs disabled
        """
        if not ALARMMAP_AVAILABLE or get_leds_by_color is None:
            self.logger.error("AlarmMap not available - cannot disable red LEDs")
            return 0
        
        red_leds = get_leds_by_color('Red')
        if not red_leds:
            self.logger.info("No red LEDs found in AlarmMap")
            return 0
        
        self.logger.info(f"Disabling {len(red_leds)} red LED(s)...")
        disabled_count = 0
        
        for led_info in red_leds:
            led_number = led_info.get('led_number')
            gpio_pin = led_info.get('gpio_pin')
            led_name = led_info.get('name', f'LED {led_number}')
            
            if gpio_pin is None:
                self.logger.warning(f"Red LED {led_number} ({led_name}) has no GPIO pin - skipping")
                continue
            
            signal_type = led_info.get('signal_type')
            if signal_type != 'Output':
                self.logger.warning(f"Red LED {led_number} ({led_name}) is not an output - skipping")
                continue
            
            try:
                # Stop blinking first (if it was blinking)
                self._stop_blink(led_number)
                # Turn off the LED
                self._set_gpio_pin(gpio_pin, False)
                self.led_states[led_number] = False
                disabled_count += 1
                self.logger.info(f"  Disabled red LED {led_number} ({led_name}) on GPIO pin {gpio_pin}")
            except Exception as e:
                self.logger.error(f"Failed to disable red LED {led_number} ({led_name}): {e}")
        
        self.logger.info(f"Successfully disabled {disabled_count} red LED(s)")
        return disabled_count
    
    def enable_buzzer(self, continuous: bool = False, frequency: int = None, beep_pattern: bool = False, beep_duration: float = None, beep_pause: float = None, volume: int = None) -> bool:
        """
        Enable the buzzer/speaker.
        
        Args:
            continuous: If True, play continuous tone or beep pattern. If False, play critical alarm pattern (3 beeps). Default: False
            frequency: PWM frequency in Hz (only used if continuous=True). Default: PWM_FREQUENCY
            beep_pattern: If True, play repeating beep pattern (beep, pause, beep, pause...). If False, play continuous tone. Default: False
            beep_duration: Duration of each beep in seconds (only used if beep_pattern=True). Default: BEEP_DURATION
            beep_pause: Duration of pause between beeps in seconds (only used if beep_pattern=True). Default: BEEP_DURATION
            volume: Volume/duty cycle (0-100). Higher = louder. Default: BUZZER_VOLUME from config.py
        
        Returns:
            True if buzzer was enabled successfully, False otherwise
        """
        # Validate and set default volume
        if volume is None:
            volume = DEFAULT_VOLUME
        elif volume < 0 or volume > 100:
            self.logger.warning(f"Volume {volume} out of range (0-100), using default {DEFAULT_VOLUME}")
            volume = DEFAULT_VOLUME
        
        # Stop any existing continuous tone first
        if self._buzzer_thread and self._buzzer_thread.is_alive():
            self.disable_buzzer()
            time.sleep(0.1)  # Give it time to stop
        
        if continuous:
            # Play continuous tone or beep pattern
            if frequency is None:
                frequency = PWM_FREQUENCY
            
            # Create stop event for continuous tone/pattern
            self._buzzer_stop_event = threading.Event()
            
            if beep_pattern:
                # Start continuous beep pattern
                if beep_duration is None:
                    beep_duration = BEEP_DURATION
                if beep_pause is None:
                    beep_pause = BEEP_DURATION
                
                result = self.play_continuous_beep_pattern(
                    frequency=frequency, 
                    beep_duration=beep_duration,
                    beep_pause=beep_pause,
                    stop_event=self._buzzer_stop_event,
                    volume=volume
                )
            else:
                # Start continuous tone
                result = self.play_continuous_tone(frequency=frequency, stop_event=self._buzzer_stop_event, volume=volume)
            
            if result:
                self.led_states['speaker'] = True
            return result
        else:
            # Play critical alarm pattern (3 beeps) - original behavior
            result = self.play_critical_alarm(volume=volume)
            if result:
                self.led_states['speaker'] = True
            return result
    
    def disable_buzzer(self) -> bool:
        """
        Disable the buzzer/speaker.
        
        This method:
        - Stops continuous tone if playing
        - Initializes GPIO fresh (GPIO.setmode, GPIO.setwarnings, GPIO.setup)
        - Sets pin to HIGH (same as test_speaker_pin.py does after beeps)
        
        Returns:
            True if buzzer was disabled, False otherwise
        """
        # Stop continuous tone if playing
        if self._buzzer_stop_event:
            self._buzzer_stop_event.set()
            self._buzzer_stop_event = None
        
        if self._buzzer_thread and self._buzzer_thread.is_alive():
            # Wait a bit for thread to stop
            self._buzzer_thread.join(timeout=0.5)
            self._buzzer_thread = None
        
        if not ALARMMAP_AVAILABLE:
            self.logger.error("AlarmMap not available - cannot disable buzzer")
            return False
        
        buzzer_info = self._get_led_info('speaker')
        if not buzzer_info:
            self.logger.error("Buzzer/speaker not found in AlarmMap")
            return False
        
        gpio_pin = buzzer_info.get('gpio_pin')
        if gpio_pin is None:
            self.logger.error("Buzzer/speaker has no GPIO pin configured")
            return False
        
        signal_type = buzzer_info.get('signal_type')
        if signal_type != 'Output':
            self.logger.warning(f"Buzzer/speaker is not an output (signal_type: {signal_type}) - skipping")
            return False
        
        buzzer_name = buzzer_info.get('name', 'Speaker/Buzzer')
        
        if not GPIO_AVAILABLE:
            self.logger.debug(f"[SIMULATED] Disabling buzzer/speaker on GPIO pin {gpio_pin}")
            self.led_states['speaker'] = False
            return True
        
        try:
            # Match test_speaker_pin.py setup_gpio() exactly:
            # Initialize GPIO fresh (same as test_speaker_pin.py does)
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(gpio_pin, GPIO.OUT)
            # Set pin to HIGH to disable buzzer (matching test_speaker_pin.py)
            GPIO.output(gpio_pin, GPIO.HIGH)
            
            self.led_states['speaker'] = False
            self.logger.info(f"Disabled buzzer/speaker ({buzzer_name}) on GPIO pin {gpio_pin} (set to HIGH)")
            return True
        except Exception as e:
            self.logger.error(f"Failed to disable buzzer/speaker: {e}")
            # Try again with fresh GPIO initialization
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                GPIO.setup(gpio_pin, GPIO.OUT)
                GPIO.output(gpio_pin, GPIO.HIGH)
                self.logger.info(f"Set buzzer pin {gpio_pin} to HIGH using GPIO reinitialize method")
                self.led_states['speaker'] = False
                return True
            except Exception as fallback_error:
                self.logger.error(f"Failed to set pin to HIGH as fallback: {fallback_error}")
                return False
    
    def play_beep(self, count: int = 1, duration: float = None, frequency: int = None, volume: int = None) -> bool:
        """
        Play beep pattern on the buzzer.
        
        Args:
            count: Number of beeps (default: 1)
            duration: Duration of each beep in seconds (default: BEEP_DURATION)
            frequency: PWM frequency in Hz (default: PWM_FREQUENCY)
            volume: Volume/duty cycle (0-100). Higher = louder. Default: BUZZER_VOLUME from config.py
        
        Returns:
            True if beeps were played successfully, False otherwise
        """
        if duration is None:
            duration = BEEP_DURATION
        if frequency is None:
            frequency = PWM_FREQUENCY
        if volume is None:
            volume = DEFAULT_VOLUME
        elif volume < 0 or volume > 100:
            self.logger.warning(f"Volume {volume} out of range (0-100), using default {DEFAULT_VOLUME}")
            volume = DEFAULT_VOLUME
        
        if not ALARMMAP_AVAILABLE:
            self.logger.error("AlarmMap not available - cannot play beep")
            return False
        
        buzzer_info = self._get_led_info('speaker')
        if not buzzer_info:
            self.logger.error("Buzzer/speaker not found in AlarmMap")
            return False
        
        gpio_pin = buzzer_info.get('gpio_pin')
        if gpio_pin is None:
            self.logger.error("Buzzer/speaker has no GPIO pin configured")
            return False
        
        if not GPIO_AVAILABLE:
            self.logger.debug(f"[SIMULATED] Playing {count} beep(s) on GPIO pin {gpio_pin}")
            return True
        
        try:
            # Initialize GPIO fresh
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(gpio_pin, GPIO.OUT, initial=GPIO.HIGH)
            
            self.logger.info(f"Playing {count} beep(s) on GPIO pin {gpio_pin} (frequency: {frequency}Hz, volume: {volume}%)")
            
            for i in range(count):
                # Use PWM for tone
                pwm = GPIO.PWM(gpio_pin, frequency)
                pwm.start(volume)  # Use volume parameter
                time.sleep(duration)
                pwm.stop()
                
                # Reset pin to output mode and set HIGH
                GPIO.setup(gpio_pin, GPIO.OUT)
                GPIO.output(gpio_pin, GPIO.HIGH)
                time.sleep(0.05)  # Small delay to ensure PWM is fully stopped
                
                # Pause between beeps (except after last beep)
                if i < count - 1:
                    time.sleep(BEEP_PAUSE)
            
            # Final ensure pin is HIGH
            GPIO.output(gpio_pin, GPIO.HIGH)
            self.logger.info(f"Beep pattern played successfully ({count} beep(s))")
            return True
        except Exception as e:
            self.logger.error(f"Failed to play beep: {e}")
            # Ensure pin is HIGH even on error
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                GPIO.setup(gpio_pin, GPIO.OUT)
                GPIO.output(gpio_pin, GPIO.HIGH)
            except:
                pass
            return False
    
    def play_critical_alarm(self, volume: int = None) -> bool:
        """
        Play critical alarm pattern (3 beeps).
        
        Args:
            volume: Volume/duty cycle (0-100). Higher = louder. Default: BUZZER_VOLUME from config.py
        
        Returns:
            True if alarm was played successfully, False otherwise
        """
        return self.play_beep(count=3, duration=BEEP_DURATION, frequency=PWM_FREQUENCY, volume=volume)
    
    def play_warning_alarm(self, volume: int = None) -> bool:
        """
        Play warning alarm pattern (2 beeps).
        
        Args:
            volume: Volume/duty cycle (0-100). Higher = louder. Default: BUZZER_VOLUME from config.py
        
        Returns:
            True if alarm was played successfully, False otherwise
        """
        return self.play_beep(count=2, duration=BEEP_DURATION, frequency=PWM_FREQUENCY, volume=volume)
    
    def play_info_beep(self, volume: int = None) -> bool:
        """
        Play info beep pattern (1 beep).
        
        Args:
            volume: Volume/duty cycle (0-100). Higher = louder. Default: BUZZER_VOLUME from config.py
        
        Returns:
            True if beep was played successfully, False otherwise
        """
        return self.play_beep(count=1, duration=BEEP_DURATION, frequency=PWM_FREQUENCY, volume=volume)
    
    def play_tone(self, frequency: int, duration: float, volume: int = None) -> bool:
        """
        Play a tone at a specific frequency for a specific duration.
        
        Args:
            frequency: PWM frequency in Hz
            duration: Duration in seconds
            volume: Volume/duty cycle (0-100). Higher = louder. Default: BUZZER_VOLUME from config.py
        
        Returns:
            True if tone was played successfully, False otherwise
        """
        if not ALARMMAP_AVAILABLE:
            self.logger.error("AlarmMap not available - cannot play tone")
            return False
        
        buzzer_info = self._get_led_info('speaker')
        if not buzzer_info:
            self.logger.error("Buzzer/speaker not found in AlarmMap")
            return False
        
        gpio_pin = buzzer_info.get('gpio_pin')
        if gpio_pin is None:
            self.logger.error("Buzzer/speaker has no GPIO pin configured")
            return False
        
        if not GPIO_AVAILABLE:
            self.logger.debug(f"[SIMULATED] Playing tone {frequency}Hz for {duration}s on GPIO pin {gpio_pin}")
            return True
        
        if volume is None:
            volume = DEFAULT_VOLUME
        elif volume < 0 or volume > 100:
            self.logger.warning(f"Volume {volume} out of range (0-100), using default {DEFAULT_VOLUME}")
            volume = DEFAULT_VOLUME
        
        try:
            # Initialize GPIO fresh
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(gpio_pin, GPIO.OUT, initial=GPIO.HIGH)
            
            self.logger.info(f"Playing tone {frequency}Hz for {duration}s on GPIO pin {gpio_pin} (volume: {volume}%)")
            
            # Use PWM for tone
            pwm = GPIO.PWM(gpio_pin, frequency)
            pwm.start(volume)  # Use volume parameter
            time.sleep(duration)
            pwm.stop()
            
            # Ensure pin is HIGH after tone
            time.sleep(0.05)  # Small delay to ensure PWM is fully stopped
            GPIO.output(gpio_pin, GPIO.HIGH)
            time.sleep(0.05)  # Additional delay to ensure state is stable
            
            self.logger.info(f"Tone played successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to play tone: {e}")
            # Ensure pin is HIGH even on error
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                GPIO.setup(gpio_pin, GPIO.OUT)
                GPIO.output(gpio_pin, GPIO.HIGH)
            except:
                pass
            return False
    
    def play_continuous_tone(self, frequency: int = None, stop_event: threading.Event = None, volume: int = None) -> bool:
        """
        Play a continuous tone until stopped.
        
        Args:
            frequency: PWM frequency in Hz (default: PWM_FREQUENCY)
            stop_event: threading.Event to signal when to stop (optional)
            volume: Volume/duty cycle (0-100). Higher = louder. Default: BUZZER_VOLUME from config.py
        
        Returns:
            True if tone was started successfully, False otherwise
        
        Note:
            This method starts the tone in a background thread. Call disable_buzzer()
            or set stop_event to stop the tone.
        """
        if frequency is None:
            frequency = PWM_FREQUENCY
        if volume is None:
            volume = DEFAULT_VOLUME
        elif volume < 0 or volume > 100:
            self.logger.warning(f"Volume {volume} out of range (0-100), using default {DEFAULT_VOLUME}")
            volume = DEFAULT_VOLUME
        
        if not ALARMMAP_AVAILABLE:
            self.logger.error("AlarmMap not available - cannot play continuous tone")
            return False
        
        buzzer_info = self._get_led_info('speaker')
        if not buzzer_info:
            self.logger.error("Buzzer/speaker not found in AlarmMap")
            return False
        
        gpio_pin = buzzer_info.get('gpio_pin')
        if gpio_pin is None:
            self.logger.error("Buzzer/speaker has no GPIO pin configured")
            return False
        
        if not GPIO_AVAILABLE:
            self.logger.debug(f"[SIMULATED] Playing continuous tone {frequency}Hz on GPIO pin {gpio_pin}")
            return True
        
        def _play_continuous():
            """Background thread function to play continuous tone."""
            try:
                # Initialize GPIO fresh
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                GPIO.setup(gpio_pin, GPIO.OUT, initial=GPIO.HIGH)
                
                self.logger.info(f"Playing continuous tone {frequency}Hz on GPIO pin {gpio_pin} (volume: {volume}%)")
                
                # Use PWM for tone
                pwm = GPIO.PWM(gpio_pin, frequency)
                pwm.start(volume)  # Use volume parameter
                
                # Wait until stop event is set
                if stop_event:
                    stop_event.wait()
                else:
                    # If no stop event, play indefinitely (caller must call disable_buzzer())
                    while True:
                        time.sleep(1)
                
                # Stop PWM
                pwm.stop()
                time.sleep(0.05)
                GPIO.output(gpio_pin, GPIO.HIGH)
                self.logger.info(f"Continuous tone stopped")
            except Exception as e:
                self.logger.error(f"Error in continuous tone thread: {e}")
                # Ensure pin is HIGH even on error
                try:
                    GPIO.setmode(GPIO.BCM)
                    GPIO.setwarnings(False)
                    GPIO.setup(gpio_pin, GPIO.OUT)
                    GPIO.output(gpio_pin, GPIO.HIGH)
                except:
                    pass
        
        # Start tone in background thread
        tone_thread = threading.Thread(target=_play_continuous, daemon=True)
        tone_thread.start()
        
        # Store thread reference for later stopping
        self._buzzer_thread = tone_thread
        
        return True
    
    def play_continuous_beep_pattern(self, frequency: int = None, beep_duration: float = None, beep_pause: float = None, stop_event: threading.Event = None, volume: int = None) -> bool:
        """
        Play a continuous beep pattern (beep, pause, beep, pause...) until stopped.
        
        Args:
            frequency: PWM frequency in Hz (default: PWM_FREQUENCY)
            beep_duration: Duration of each beep in seconds (default: BEEP_DURATION)
            beep_pause: Duration of pause between beeps in seconds (default: BEEP_DURATION)
            stop_event: threading.Event to signal when to stop (optional)
            volume: Volume/duty cycle (0-100). Higher = louder. Default: BUZZER_VOLUME from config.py
        
        Returns:
            True if beep pattern was started successfully, False otherwise
        
        Note:
            This method starts the beep pattern in a background thread. Call disable_buzzer()
            or set stop_event to stop the pattern.
        """
        if frequency is None:
            frequency = PWM_FREQUENCY
        if beep_duration is None:
            beep_duration = BEEP_DURATION
        if beep_pause is None:
            beep_pause = BEEP_DURATION
        if volume is None:
            volume = DEFAULT_VOLUME
        elif volume < 0 or volume > 100:
            self.logger.warning(f"Volume {volume} out of range (0-100), using default {DEFAULT_VOLUME}")
            volume = DEFAULT_VOLUME
        
        if not ALARMMAP_AVAILABLE:
            self.logger.error("AlarmMap not available - cannot play continuous beep pattern")
            return False
        
        buzzer_info = self._get_led_info('speaker')
        if not buzzer_info:
            self.logger.error("Buzzer/speaker not found in AlarmMap")
            return False
        
        gpio_pin = buzzer_info.get('gpio_pin')
        if gpio_pin is None:
            self.logger.error("Buzzer/speaker has no GPIO pin configured")
            return False
        
        if not GPIO_AVAILABLE:
            self.logger.debug(f"[SIMULATED] Playing continuous beep pattern {frequency}Hz on GPIO pin {gpio_pin} (beep: {beep_duration}s, pause: {beep_pause}s)")
            return True
        
        def _play_continuous_beep():
            """Background thread function to play continuous beep pattern."""
            try:
                # Initialize GPIO fresh
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                GPIO.setup(gpio_pin, GPIO.OUT, initial=GPIO.HIGH)
                
                self.logger.info(f"Playing continuous beep pattern {frequency}Hz on GPIO pin {gpio_pin} (beep: {beep_duration}s, pause: {beep_pause}s, volume: {volume}%)")
                
                # Use PWM for tone
                pwm = GPIO.PWM(gpio_pin, frequency)
                
                # Play beep pattern until stopped
                while True:
                    # Check if stop event is set
                    if stop_event and stop_event.is_set():
                        break
                    
                    # Play beep with specified volume (duty cycle)
                    pwm.start(volume)  # Use volume parameter (duty cycle 0-100)
                    time.sleep(beep_duration)
                    pwm.stop()
                    
                    # Check if stop event is set again
                    if stop_event and stop_event.is_set():
                        break
                    
                    # Pause between beeps
                    time.sleep(beep_pause)
                
                # Stop PWM and set pin HIGH
                try:
                    pwm.stop()
                except:
                    pass
                time.sleep(0.05)
                GPIO.output(gpio_pin, GPIO.HIGH)
                self.logger.info(f"Continuous beep pattern stopped")
            except Exception as e:
                self.logger.error(f"Error in continuous beep pattern thread: {e}")
                # Ensure pin is HIGH even on error
                try:
                    GPIO.setmode(GPIO.BCM)
                    GPIO.setwarnings(False)
                    GPIO.setup(gpio_pin, GPIO.OUT)
                    GPIO.output(gpio_pin, GPIO.HIGH)
                except:
                    pass
        
        # Start beep pattern in background thread
        beep_thread = threading.Thread(target=_play_continuous_beep, daemon=True)
        beep_thread.start()
        
        # Store thread reference for later stopping
        self._buzzer_thread = beep_thread
        
        return True
    
    def get_led_state(self, led_number: int) -> Optional[bool]:
        """
        Get current state of an LED.
        
        Args:
            led_number: LED number (1-14)
        
        Returns:
            True if enabled, False if disabled, None if unknown or not found
        """
        return self.led_states.get(led_number)
    
    def list_leds(self, color: Optional[str] = None):
        """
        List all LEDs or LEDs of a specific color.
        
        Args:
            color: Optional color filter ('Green', 'Red', or None for all)
        """
        if not ALARMMAP_AVAILABLE:
            self.logger.error("AlarmMap not available - cannot list LEDs")
            return
        
        if color:
            leds = get_leds_by_color(color) if get_leds_by_color else []
            self.logger.info(f"\n{color} LEDs in AlarmMap:")
        else:
            leds = []
            for led_key, led_info in PANEL_LED_MAPPING.items():
                if isinstance(led_key, int):  # Only numeric LED numbers
                    info = led_info.copy()
                    info['led_number'] = led_key
                    leds.append(info)
            self.logger.info(f"\nAll LEDs in AlarmMap:")
        
        if not leds:
            self.logger.info("  No LEDs found")
            return
        
        for led_info in leds:
            led_number = led_info.get('led_number')
            gpio_pin = led_info.get('gpio_pin')
            led_name = led_info.get('name', f'LED {led_number}')
            color_info = led_info.get('color', 'Unknown')
            signal_type = led_info.get('signal_type', 'Unknown')
            function = led_info.get('function', 'Unknown')
            state = "ON" if self.led_states.get(led_number) else "OFF"
            
            self.logger.info(f"  LED {led_number}: {led_name}")
            self.logger.info(f"    GPIO Pin: {gpio_pin}")
            self.logger.info(f"    Color: {color_info}")
            self.logger.info(f"    Signal Type: {signal_type}")
            self.logger.info(f"    Function: {function}")
            self.logger.info(f"    Current State: {state}")
            self.logger.info("")
    
    def cleanup(self):
        """Cleanup GPIO resources."""
        # Stop all blinking threads
        for led_number in list(self.blink_threads.keys()):
            self._stop_blink(led_number)
        
        # Cleanup GPIO
        if GPIO_AVAILABLE and self.gpio_initialized:
            try:
                GPIO.cleanup()
                self.gpio_initialized = False
                self.logger.info("GPIO cleaned up")
            except Exception as e:
                self.logger.error(f"Error cleaning up GPIO: {e}")


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description='Panel LED Controller - Control LEDs based on AlarmMap configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Enable all green LEDs
  python panel_led_controller.py --enable-all-green
  
  # Disable all green LEDs
  python panel_led_controller.py --disable-all-green
  
  # Enable all red LEDs
  python panel_led_controller.py --enable-all-red
  
  # Enable the buzzer/speaker (plays critical alarm: 3 beeps)
  python panel_led_controller.py --enable-buzzer
  
  # Disable the buzzer/speaker
  python panel_led_controller.py --disable-buzzer
  
  # Enable continuous buzzer (continuous tone)
  python panel_led_controller.py --enable-buzzer-continuous
  
  # Enable continuous buzzer with custom frequency
  python panel_led_controller.py --enable-buzzer-continuous --buzzer-frequency 2000
  
  # Enable continuous beep pattern (beep, pause, beep, pause...)
  python panel_led_controller.py --enable-buzzer-continuous --buzzer-beep-pattern
  
  # Enable continuous beep pattern with custom timing
  python panel_led_controller.py --enable-buzzer-continuous --buzzer-beep-pattern --beep-duration 0.2 --beep-pause 0.5
  
  # Enable continuous beep pattern with custom frequency and timing
  python panel_led_controller.py --enable-buzzer-continuous --buzzer-beep-pattern --buzzer-frequency 2000 --beep-duration 0.3 --beep-pause 0.3
  
  # Stop buzzer (stops continuous tone or beep pattern)
  python panel_led_controller.py --disable-buzzer
  
  # Enable a specific LED (LED 2)
  python panel_led_controller.py --enable-led 2
  
  # Disable a specific LED (LED 2)
  python panel_led_controller.py --disable-led 2
  
  # List all green LEDs
  python panel_led_controller.py --list --color green
  
  # List all LEDs
  python panel_led_controller.py --list
  
  # Use active-low logic
  python panel_led_controller.py --enable-all-green --active-low
        """
    )
    
    parser.add_argument(
        '--enable-led',
        type=int,
        metavar='N',
        help='Enable LED number N (1-14)'
    )
    
    parser.add_argument(
        '--disable-led',
        type=int,
        metavar='N',
        help='Disable LED number N (1-14)'
    )
    
    parser.add_argument(
        '--enable-all-green',
        action='store_true',
        help='Enable all green LEDs'
    )
    
    parser.add_argument(
        '--disable-all-green',
        action='store_true',
        help='Disable all green LEDs'
    )
    
    parser.add_argument(
        '--enable-all-red',
        action='store_true',
        help='Enable all red LEDs'
    )
    
    parser.add_argument(
        '--disable-all-red',
        action='store_true',
        help='Disable all red LEDs'
    )
    
    parser.add_argument(
        '--enable-buzzer',
        action='store_true',
        help='Enable the buzzer/speaker (plays critical alarm: 3 beeps)'
    )
    
    parser.add_argument(
        '--disable-buzzer',
        action='store_true',
        help='Disable the buzzer/speaker'
    )
    
    parser.add_argument(
        '--enable-buzzer-continuous',
        action='store_true',
        help='Enable the buzzer/speaker continuously (until disabled)'
    )
    
    parser.add_argument(
        '--buzzer-frequency',
        type=int,
        default=None,
        help='PWM frequency in Hz for continuous buzzer (default: 1000)'
    )
    
    parser.add_argument(
        '--buzzer-beep-pattern',
        action='store_true',
        help='Play continuous beep pattern (beep, pause, beep, pause...) instead of continuous tone'
    )
    
    parser.add_argument(
        '--beep-duration',
        type=float,
        default=None,
        help='Duration of each beep in seconds for beep pattern (default: 0.3)'
    )
    
    parser.add_argument(
        '--beep-pause',
        type=float,
        default=None,
        help='Duration of pause between beeps in seconds for beep pattern (default: 0.3)'
    )
    
    parser.add_argument(
        '--buzzer-volume',
        type=int,
        default=None,
        help='Volume/duty cycle (0-100) for buzzer. Higher = louder. Default: BUZZER_VOLUME from config.py'
    )
    
    parser.add_argument(
        '--play-beep',
        type=int,
        metavar='COUNT',
        help='Play beep pattern (specify number of beeps, e.g., --play-beep 2)'
    )
    
    parser.add_argument(
        '--play-critical',
        action='store_true',
        help='Play critical alarm pattern (3 beeps)'
    )
    
    parser.add_argument(
        '--play-warning',
        action='store_true',
        help='Play warning alarm pattern (2 beeps)'
    )
    
    parser.add_argument(
        '--play-info',
        action='store_true',
        help='Play info beep pattern (1 beep)'
    )
    
    parser.add_argument(
        '--play-tone',
        nargs=2,
        metavar=('FREQUENCY', 'DURATION'),
        help='Play a tone (frequency in Hz, duration in seconds, e.g., --play-tone 1000 0.5)'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List LEDs (use --color to filter by color)'
    )
    
    parser.add_argument(
        '--color',
        type=str,
        choices=['green', 'red', 'Green', 'Red'],
        help='Color filter for --list (green or red)'
    )
    
    parser.add_argument(
        '--active-low',
        action='store_true',
        help='Use active-low logic (LED on with LOW signal)'
    )
    
    parser.add_argument(
        '--active-high',
        action='store_true',
        help='Use active-high logic (LED on with HIGH signal) - default'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Determine active_high setting
    active_high = True  # Default
    if args.active_low:
        active_high = False
    elif args.active_high:
        active_high = True
    
    # Create controller
    controller = PanelLEDController(active_high=active_high)
    
    try:
        # Execute requested actions
        if args.enable_led:
            controller.enable_led(args.enable_led)
        
        if args.disable_led:
            controller.disable_led(args.disable_led)
        
        if args.enable_all_green:
            controller.enable_all_green_leds()
        
        if args.disable_all_green:
            controller.disable_all_green_leds()
        
        if args.enable_all_red:
            controller.enable_all_red_leds()
        
        if args.disable_all_red:
            controller.disable_all_red_leds()
        
        if args.enable_buzzer:
            volume = args.buzzer_volume if args.buzzer_volume is not None else None
            controller.enable_buzzer(continuous=False, volume=volume)
        
        if args.enable_buzzer_continuous:
            freq = args.buzzer_frequency if args.buzzer_frequency else None
            beep_duration = args.beep_duration if args.beep_duration else None
            beep_pause = args.beep_pause if args.beep_pause else None
            volume = args.buzzer_volume if args.buzzer_volume is not None else None
            
            if args.buzzer_beep_pattern:
                # Beep pattern mode
                if controller.enable_buzzer(continuous=True, frequency=freq, beep_pattern=True, beep_duration=beep_duration, beep_pause=beep_pause, volume=volume):
                    pattern_info = f"frequency: {freq or PWM_FREQUENCY}Hz, beep: {beep_duration or BEEP_DURATION}s, pause: {beep_pause or BEEP_DURATION}s, volume: {volume or DEFAULT_VOLUME}%"
                    print(f"Continuous beep pattern started ({pattern_info})")
                    print("Press Ctrl+C to stop...")
                    try:
                        # Keep main thread alive while buzzer is playing
                        while controller._buzzer_thread and controller._buzzer_thread.is_alive():
                            time.sleep(0.5)
                    except KeyboardInterrupt:
                        print("\nStopping continuous beep pattern...")
                        controller.disable_buzzer()
                        time.sleep(0.2)  # Give it time to stop
                else:
                    print("ERROR: Failed to start continuous beep pattern", file=sys.stderr)
                    return 1
            else:
                # Continuous tone mode
                if controller.enable_buzzer(continuous=True, frequency=freq, volume=volume):
                    print(f"Continuous buzzer started (frequency: {freq or PWM_FREQUENCY}Hz, volume: {volume or DEFAULT_VOLUME}%)")
                    print("Press Ctrl+C to stop...")
                    try:
                        # Keep main thread alive while buzzer is playing
                        while controller._buzzer_thread and controller._buzzer_thread.is_alive():
                            time.sleep(0.5)
                    except KeyboardInterrupt:
                        print("\nStopping continuous buzzer...")
                        controller.disable_buzzer()
                        time.sleep(0.2)  # Give it time to stop
                else:
                    print("ERROR: Failed to start continuous buzzer", file=sys.stderr)
                    return 1
        
        if args.disable_buzzer:
            controller.disable_buzzer()
        
        if args.play_beep is not None:
            volume = args.buzzer_volume if args.buzzer_volume is not None else None
            controller.play_beep(count=args.play_beep, volume=volume)
        
        if args.play_critical:
            volume = args.buzzer_volume if args.buzzer_volume is not None else None
            controller.play_critical_alarm(volume=volume)
        
        if args.play_warning:
            volume = args.buzzer_volume if args.buzzer_volume is not None else None
            controller.play_warning_alarm(volume=volume)
        
        if args.play_info:
            volume = args.buzzer_volume if args.buzzer_volume is not None else None
            controller.play_info_beep(volume=volume)
        
        if args.play_tone:
            try:
                frequency = int(args.play_tone[0])
                duration = float(args.play_tone[1])
                volume = args.buzzer_volume if args.buzzer_volume is not None else None
                controller.play_tone(frequency, duration, volume=volume)
            except (ValueError, IndexError):
                print("ERROR: --play-tone requires two arguments: frequency (int) and duration (float)")
                sys.exit(1)
        
        if args.list:
            color_filter = args.color.capitalize() if args.color else None
            controller.list_leds(color=color_filter)
        
        # If no action specified, show help
        if not any([
            args.enable_led, args.disable_led,
            args.enable_all_green, args.disable_all_green,
            args.enable_all_red, args.disable_all_red,
            args.enable_buzzer, args.enable_buzzer_continuous, args.disable_buzzer,
            args.play_beep is not None, args.play_critical, args.play_warning, args.play_info,
            args.play_tone, args.list
        ]):
            parser.print_help()
            return 1
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Always cleanup GPIO on exit (like test_speaker_pin.py does)
        # This ensures GPIO pins are reset and PWM is stopped
        controller.cleanup()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

