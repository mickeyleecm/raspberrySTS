#!/usr/bin/env python3
"""
Test script to manually trigger the LED on GPIO pin 17.
This simulates receiving an SNMP trap to test the LED controller.
"""

import sys
import time

# Import the LED controller
try:
    from ups_gpio_led_controller import GPIOLEDController
except ImportError as e:
    print(f"ERROR: Could not import LED controller: {e}")
    print("Make sure ups_gpio_led_controller.py is in the same directory")
    sys.exit(1)

print("Testing LED trigger on GPIO pin 17...")
print("This simulates receiving an SNMP trap alarm")
print("")

# Create LED controller with pin 17
gpio_pins = {
    'critical': 17,
    'warning': 17
}

try:
    controller = GPIOLEDController(
        gpio_pins=gpio_pins,
        blink_enabled=True,
        blink_interval=0.5,
        active_high=True
    )
    
    print("LED controller initialized")
    print("Triggering CRITICAL alarm (LED should blink)...")
    controller.trigger_alarm('critical', 'critical')
    time.sleep(5)
    
    print("Clearing alarm (LED should turn OFF)...")
    controller.clear_alarm('critical')
    time.sleep(2)
    
    print("Triggering WARNING alarm (LED should blink)...")
    controller.trigger_alarm('warning', 'warning')
    time.sleep(5)
    
    print("Clearing alarm (LED should turn OFF)...")
    controller.clear_alarm('warning')
    time.sleep(2)
    
    print("\nTest completed!")
    print("\nIf the LED worked, your GPIO controller is functioning correctly.")
    print("Now make sure:")
    print("  1. UPS is configured to send SNMP traps to your Raspberry Pi IP")
    print("  2. Run: sudo python3 ups_gpio_led_controller.py --critical-pin 17 --warning-pin 17")
    print("  3. Send a test trap or wait for UPS to send an alarm")
    
except KeyboardInterrupt:
    print("\n\nTest interrupted")
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    try:
        controller.cleanup()
        print("GPIO cleaned up")
    except:
        pass

