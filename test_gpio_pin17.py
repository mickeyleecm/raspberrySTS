#!/usr/bin/env python3
"""
Test script to verify GPIO pin 17 is working correctly.
Run this to test if your LED hardware is connected properly.
"""

import sys
import time

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    print("ERROR: RPi.GPIO not available. Make sure you're running on Raspberry Pi.")
    sys.exit(1)

PIN = 17

print(f"Testing GPIO pin {PIN}...")
print("Press Ctrl+C to stop")

try:
    # Setup GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(PIN, GPIO.OUT)
    
    print(f"GPIO pin {PIN} configured as output")
    print("\nTurning LED ON for 2 seconds...")
    GPIO.output(PIN, GPIO.HIGH)
    time.sleep(2)
    
    print("Turning LED OFF for 2 seconds...")
    GPIO.output(PIN, GPIO.LOW)
    time.sleep(2)
    
    print("\nBlinking LED 5 times...")
    for i in range(5):
        GPIO.output(PIN, GPIO.HIGH)
        print(f"  ON ({i+1}/5)")
        time.sleep(0.5)
        GPIO.output(PIN, GPIO.LOW)
        print(f"  OFF ({i+1}/5)")
        time.sleep(0.5)
    
    print("\nTest completed!")
    print("\nIf the LED didn't turn on, check:")
    print("  1. LED is connected to GPIO 17 (BCM) with a current-limiting resistor (220Ω-1kΩ)")
    print("  2. LED cathode is connected to GND")
    print("  3. Try --active-low flag if LED is common cathode")
    
except KeyboardInterrupt:
    print("\n\nTest interrupted")
except Exception as e:
    print(f"\nERROR: {e}")
finally:
    GPIO.cleanup()
    print("GPIO cleaned up")

