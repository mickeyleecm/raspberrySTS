#!/usr/bin/env python3
"""
GPIO Pin Testing Tool
Tests GPIO pins one by one or automatically to verify LED connections and functionality.

Features:
- Test individual pins manually (one at a time)
- Test all pins automatically in sequence
- Support for active-high and active-low LEDs
- Blink pattern testing
- Clear visual feedback
- Safe GPIO cleanup

Usage:
    # Test a single pin
    python3 test_gpio_pins.py --pin 18
    
    # Test multiple pins one by one
    python3 test_gpio_pins.py --pins 18,19,20
    
    # Test all pins automatically
    python3 test_gpio_pins.py --auto --pins 18,19,20,21
    
    # Test with active-low logic
    python3 test_gpio_pins.py --pins 18,19 --active-low
    
    # Test with custom blink interval
    python3 test_gpio_pins.py --pins 18,19 --blink-interval 0.3
"""

import sys
import time
import argparse
import platform
from typing import List, Optional

# Check if running on Raspberry Pi
IS_RASPBERRY_PI = platform.system() != 'Windows'

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False
    if IS_RASPBERRY_PI:
        print("WARNING: RPi.GPIO not available. Install with: pip3 install RPi.GPIO")
    else:
        print("INFO: Running on non-Raspberry Pi system. GPIO operations will be simulated.")


class GPIOPinTester:
    """GPIO Pin Tester for LED testing."""
    
    def __init__(self, active_high: bool = True, blink_interval: float = 0.5):
        """
        Initialize GPIO Pin Tester.
        
        Args:
            active_high: True for active-high LEDs (default), False for active-low
            blink_interval: Blink interval in seconds (default: 0.5)
        """
        self.active_high = active_high
        self.blink_interval = blink_interval
        self.gpio_available = GPIO_AVAILABLE
        self.tested_pins = []
        
        if self.gpio_available:
            try:
                GPIO.setmode(GPIO.BCM)  # Use BCM pin numbering
                GPIO.setwarnings(False)  # Disable warnings
                print("✓ GPIO initialized (BCM mode)")
            except Exception as e:
                print(f"✗ Failed to initialize GPIO: {e}")
                self.gpio_available = False
        else:
            print("⚠ GPIO simulation mode (RPi.GPIO not available)")
    
    def setup_pin(self, pin: int) -> bool:
        """
        Setup a GPIO pin as output.
        
        Args:
            pin: GPIO pin number (BCM)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.gpio_available:
            print(f"  [SIM] Pin {pin} would be set as output")
            return True
        
        try:
            GPIO.setup(pin, GPIO.OUT)
            # Initialize to OFF state
            GPIO.output(pin, GPIO.LOW if self.active_high else GPIO.HIGH)
            return True
        except Exception as e:
            print(f"  ✗ Failed to setup pin {pin}: {e}")
            return False
    
    def set_pin_state(self, pin: int, state: bool):
        """
        Set GPIO pin state (ON/OFF).
        
        Args:
            pin: GPIO pin number (BCM)
            state: True for ON, False for OFF
        """
        if not self.gpio_available:
            state_str = "ON" if state else "OFF"
            print(f"  [SIM] Pin {pin} → {state_str}")
            return
        
        try:
            if self.active_high:
                GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)
            else:
                GPIO.output(pin, GPIO.LOW if state else GPIO.HIGH)
        except Exception as e:
            print(f"  ✗ Failed to set pin {pin} state: {e}")
    
    def test_pin(self, pin: int, auto_mode: bool = False) -> bool:
        """
        Test a single GPIO pin with various patterns.
        
        Args:
            pin: GPIO pin number (BCM)
            auto_mode: If True, runs automatically without user input
            
        Returns:
            True if test passed, False otherwise
        """
        print(f"\n{'='*60}")
        print(f"Testing GPIO Pin {pin} (BCM)")
        print(f"{'='*60}")
        
        if not self.setup_pin(pin):
            return False
        
        try:
            # Test 1: Turn ON
            if not auto_mode:
                input(f"Press Enter to turn ON pin {pin}...")
            print(f"  → Turning ON pin {pin}...")
            self.set_pin_state(pin, True)
            time.sleep(1)
            
            # Test 2: Turn OFF
            if not auto_mode:
                input(f"Press Enter to turn OFF pin {pin}...")
            print(f"  → Turning OFF pin {pin}...")
            self.set_pin_state(pin, False)
            time.sleep(0.5)
            
            # Test 3: Blink pattern
            if not auto_mode:
                input(f"Press Enter to start blinking pin {pin} (5 times)...")
            print(f"  → Blinking pin {pin} 5 times (interval: {self.blink_interval}s)...")
            for i in range(5):
                self.set_pin_state(pin, True)
                print(f"    ON ({i+1}/5)")
                time.sleep(self.blink_interval)
                self.set_pin_state(pin, False)
                print(f"    OFF ({i+1}/5)")
                time.sleep(self.blink_interval)
            
            # Test 4: Final state check
            print(f"  → Setting pin {pin} to OFF (final state)...")
            self.set_pin_state(pin, False)
            time.sleep(0.5)
            
            print(f"\n✓ Pin {pin} test completed successfully!")
            self.tested_pins.append(pin)
            return True
            
        except KeyboardInterrupt:
            print(f"\n⚠ Test interrupted for pin {pin}")
            self.set_pin_state(pin, False)
            return False
        except Exception as e:
            print(f"\n✗ Error testing pin {pin}: {e}")
            return False
    
    def test_pins_auto(self, pins: List[int], delay: float = 2.0):
        """
        Test multiple pins automatically in sequence.
        
        Args:
            pins: List of GPIO pin numbers to test
            delay: Delay between pin tests in seconds
        """
        print(f"\n{'#'*60}")
        print(f"AUTOMATIC MODE: Testing {len(pins)} pin(s)")
        print(f"Pins: {', '.join(map(str, pins))}")
        print(f"Active-high: {self.active_high}")
        print(f"Blink interval: {self.blink_interval}s")
        print(f"Delay between pins: {delay}s")
        print(f"{'#'*60}")
        
        # Setup all pins first
        print("\nSetting up all pins...")
        for pin in pins:
            self.setup_pin(pin)
        time.sleep(1)
        
        # Test each pin
        for i, pin in enumerate(pins, 1):
            print(f"\n[{i}/{len(pins)}] Testing pin {pin}...")
            self.test_pin(pin, auto_mode=True)
            
            if i < len(pins):
                print(f"\nWaiting {delay} seconds before next pin...")
                time.sleep(delay)
        
        # Summary
        print(f"\n{'#'*60}")
        print("TEST SUMMARY")
        print(f"{'#'*60}")
        print(f"Total pins tested: {len(self.tested_pins)}")
        print(f"Successfully tested: {', '.join(map(str, self.tested_pins))}")
        print(f"\n✓ All tests completed!")
    
    def test_pins_manual(self, pins: List[int]):
        """
        Test multiple pins manually (one by one with user input).
        
        Args:
            pins: List of GPIO pin numbers to test
        """
        print(f"\n{'#'*60}")
        print(f"MANUAL MODE: Testing {len(pins)} pin(s)")
        print(f"Pins: {', '.join(map(str, pins))}")
        print(f"Active-high: {self.active_high}")
        print(f"Blink interval: {self.blink_interval}s")
        print(f"{'#'*60}")
        print("\nYou will be prompted to press Enter for each test step.")
        print("Press Ctrl+C at any time to skip to next pin or exit.\n")
        
        for i, pin in enumerate(pins, 1):
            try:
                print(f"\n[{i}/{len(pins)}] Ready to test pin {pin}")
                input("Press Enter to start testing this pin...")
                self.test_pin(pin, auto_mode=False)
                
                if i < len(pins):
                    next_pin = pins[i]
                    input(f"\nPress Enter to continue to pin {next_pin}...")
                    
            except KeyboardInterrupt:
                print(f"\n⚠ Skipping pin {pin}")
                continue
        
        # Summary
        print(f"\n{'#'*60}")
        print("TEST SUMMARY")
        print(f"{'#'*60}")
        print(f"Total pins tested: {len(self.tested_pins)}")
        print(f"Successfully tested: {', '.join(map(str, self.tested_pins))}")
        print(f"\n✓ All tests completed!")
    
    def cleanup(self):
        """Cleanup GPIO resources."""
        if self.gpio_available:
            try:
                # Turn off all tested pins
                for pin in self.tested_pins:
                    try:
                        self.set_pin_state(pin, False)
                    except:
                        pass
                GPIO.cleanup()
                print("\n✓ GPIO cleaned up")
            except Exception as e:
                print(f"\n⚠ Error during cleanup: {e}")
        else:
            print("\n✓ Simulation mode cleanup")


def parse_pins(pins_str: str) -> List[int]:
    """
    Parse comma-separated pin numbers.
    
    Args:
        pins_str: Comma-separated pin numbers (e.g., "18,19,20")
        
    Returns:
        List of pin numbers
    """
    try:
        pins = [int(p.strip()) for p in pins_str.split(',')]
        # Validate pin numbers (BCM pins are typically 2-27)
        valid_pins = [p for p in pins if 2 <= p <= 27]
        if len(valid_pins) != len(pins):
            invalid = [p for p in pins if p not in valid_pins]
            print(f"⚠ Warning: Invalid pin numbers ignored: {invalid}")
        return valid_pins
    except ValueError as e:
        print(f"✗ Error parsing pins: {e}")
        sys.exit(1)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Test GPIO pins for LED connections',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test single pin manually
  python3 test_gpio_pins.py --pin 18
  
  # Test multiple pins automatically
  python3 test_gpio_pins.py --auto --pins 18,19,20
  
  # Test with active-low logic
  python3 test_gpio_pins.py --pins 18,19 --active-low
  
  # Test with custom settings
  python3 test_gpio_pins.py --auto --pins 18,19,20 --blink-interval 0.3 --delay 3
        """
    )
    
    pin_group = parser.add_mutually_exclusive_group(required=True)
    pin_group.add_argument(
        '--pin', '-p',
        type=int,
        help='Single GPIO pin number to test (BCM)'
    )
    pin_group.add_argument(
        '--pins',
        type=str,
        help='Comma-separated GPIO pin numbers to test (e.g., "18,19,20")'
    )
    
    parser.add_argument(
        '--auto', '-a',
        action='store_true',
        help='Automatic mode (no user input required)'
    )
    parser.add_argument(
        '--active-low',
        action='store_true',
        help='Use active-low logic (LED on with LOW signal)'
    )
    parser.add_argument(
        '--blink-interval',
        type=float,
        default=0.5,
        help='Blink interval in seconds (default: 0.5)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='Delay between pin tests in automatic mode (default: 2.0 seconds)'
    )
    
    args = parser.parse_args()
    
    # Parse pins
    if args.pin:
        pins = [args.pin]
    else:
        pins = parse_pins(args.pins)
    
    if not pins:
        print("✗ No valid pins to test")
        sys.exit(1)
    
    # Create tester
    tester = GPIOPinTester(
        active_high=not args.active_low,
        blink_interval=args.blink_interval
    )
    
    try:
        # Run tests
        if args.auto or len(pins) == 1:
            # Auto mode or single pin (always auto for single pin)
            tester.test_pins_auto(pins, delay=args.delay)
        else:
            # Manual mode for multiple pins
            tester.test_pins_manual(pins)
            
    except KeyboardInterrupt:
        print("\n\n⚠ Test interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        tester.cleanup()


if __name__ == '__main__':
    main()

