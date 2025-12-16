#!/usr/bin/env python3
"""
Quick test program to find which GPIO pin a speaker/buzzer is connected to.
Tests pins 18 to 60 automatically with short beeps.
"""

import sys
import time
import platform

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    print("ERROR: RPi.GPIO not available.")
    print("Install with: pip3 install RPi.GPIO")
    sys.exit(1)

# Configuration
START_PIN = 18
END_PIN = 60
BEEP_DURATION = 0.2  # seconds per beep
PWM_FREQUENCY = 1000  # Hz
PAUSE_BETWEEN_PINS = 0.1  # seconds

print("=" * 70)
print("Quick Speaker Pin Finder - GPIO Pins 18-60")
print("=" * 70)
print()
print("This will test each pin quickly. Listen for the speaker sound.")
print("Press Ctrl+C to stop at any time.")
print()

try:
    # Setup GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    print("Starting test...\n")
    
    found_pins = []
    total_pins = END_PIN - START_PIN + 1
    
    for idx, pin in enumerate(range(START_PIN, END_PIN + 1), 1):
        try:
            # Skip known problematic pins
            if pin in [27, 28]:  # I2C pins
                continue
            
            print(f"[{idx:2d}/{total_pins}] Testing GPIO pin {pin:2d}...", end='', flush=True)
            
            # Setup pin
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)
            
            # Test 1: Simple on/off (active buzzer)
            GPIO.output(pin, GPIO.HIGH)
            time.sleep(BEEP_DURATION)
            GPIO.output(pin, GPIO.LOW)
            time.sleep(0.05)
            
            # Test 2: PWM tone (passive speaker)
            try:
                pwm = GPIO.PWM(pin, PWM_FREQUENCY)
                pwm.start(50)
                time.sleep(BEEP_DURATION)
                pwm.stop()
            except:
                pass  # PWM might not work on all pins
            
            GPIO.output(pin, GPIO.LOW)
            print(" ✓")
            
            time.sleep(PAUSE_BETWEEN_PINS)
            
        except ValueError:
            # Pin not available on this model
            print(" ✗ (not available)")
            continue
        except Exception as e:
            print(f" ✗ (error: {e})")
            continue
    
    print()
    print("=" * 70)
    print("Test Complete!")
    print("=" * 70)
    print()
    print("If you heard sound, note which pin number it was.")
    print("Common GPIO pins for speakers:")
    print("  - GPIO 18 (PWM capable)")
    print("  - GPIO 19 (PWM capable)")
    print("  - GPIO 21 (PWM capable)")
    print("  - GPIO 22 (PWM capable)")
    print("  - GPIO 23 (PWM capable)")
    print("  - GPIO 24 (PWM capable)")
    print("  - GPIO 25 (PWM capable)")
    print()
    print("To confirm a specific pin, run:")
    print("  python3 test_speaker_find_pin.py")
    print("  (Choose option 2 for manual mode)")

except KeyboardInterrupt:
    print("\n\nTest interrupted by user")
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    try:
        GPIO.cleanup()
        print("\nGPIO cleaned up")
    except:
        pass

