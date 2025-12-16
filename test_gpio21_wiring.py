#!/usr/bin/env python3
"""
Diagnostic script to test GPIO 21 wiring for reset button.

This script will help diagnose if the reset button is properly wired.
"""

import sys
import time
import platform

# Check if running on Raspberry Pi
if platform.system() != 'Linux':
    print("ERROR: This script must run on Raspberry Pi (Linux)")
    sys.exit(1)

try:
    import RPi.GPIO as GPIO
except (ImportError, RuntimeError):
    print("ERROR: RPi.GPIO not available.")
    print("Install with: pip3 install RPi.GPIO")
    sys.exit(1)

RESET_PIN = 21

def test_gpio21_wiring():
    """Test GPIO 21 wiring to diagnose button connection."""
    print("=" * 70)
    print("GPIO 21 Wiring Diagnostic Test")
    print("=" * 70)
    print()
    print("This test will help diagnose if the reset button is properly wired.")
    print()
    print("Expected wiring:")
    print("  - One side of button: Connected to GPIO 21 (BCM pin 21, physical pin 40)")
    print("  - Other side of button: Connected to GND (Ground)")
    print("  - GPIO 21 configured with pull-up resistor (PUD_UP)")
    print()
    print("Expected behavior:")
    print("  - Button NOT pressed: GPIO 21 reads HIGH (1)")
    print("  - Button PRESSED: GPIO 21 reads LOW (0)")
    print()
    print("-" * 70)
    
    try:
        # Cleanup any existing GPIO state
        try:
            GPIO.cleanup()
        except:
            pass
        
        time.sleep(0.1)
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup GPIO 21 as input with pull-up
        GPIO.setup(RESET_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        print(f"GPIO {RESET_PIN} configured as input with pull-up resistor")
        print()
        
        # Test 1: Read initial state
        print("Test 1: Reading initial state (button should NOT be pressed)...")
        initial_reads = []
        for i in range(5):
            state = GPIO.input(RESET_PIN)
            initial_reads.append(state)
            print(f"  Read {i+1}: {state} ({'HIGH' if state == GPIO.HIGH else 'LOW'})")
            time.sleep(0.1)
        
        if all(r == GPIO.HIGH for r in initial_reads):
            print("  ✓ PASS: All reads are HIGH (1) - button is not pressed (correct)")
        else:
            print(f"  ✗ FAIL: Inconsistent reads: {initial_reads}")
            print("  WARNING: GPIO 21 may be floating or button may be stuck pressed")
        print()
        
        # Test 2: Manual button press test
        print("Test 2: Manual button press test")
        print("  Please PRESS and HOLD the reset button now...")
        print("  (Press Enter when you're ready to start the test)")
        input()
        
        print("  Reading GPIO 21 state while button is pressed...")
        pressed_reads = []
        for i in range(20):
            state = GPIO.input(RESET_PIN)
            pressed_reads.append(state)
            status = "LOW (0)" if state == GPIO.LOW else "HIGH (1)"
            print(f"  Read {i+1}/20: {state} ({status})", end='\r')
            time.sleep(0.1)
        print()  # New line after progress
        
        low_count = sum(1 for r in pressed_reads if r == GPIO.LOW)
        high_count = sum(1 for r in pressed_reads if r == GPIO.HIGH)
        
        print()
        print(f"  Results: LOW={low_count}, HIGH={high_count}")
        
        if low_count > 15:
            print("  ✓ PASS: Button press detected! GPIO 21 goes LOW when pressed (correct)")
            print("  The button wiring appears to be correct.")
        elif low_count > 0:
            print("  ⚠ WARNING: Button press partially detected")
            print("  Some reads show LOW, but not consistently.")
            print("  Possible issues:")
            print("    - Loose connection")
            print("    - Button bouncing")
            print("    - Weak connection to GND")
        else:
            print("  ✗ FAIL: Button press NOT detected!")
            print("  GPIO 21 stays HIGH even when button is pressed.")
            print()
            print("  DIAGNOSIS: Wiring problem detected!")
            print("  Possible causes:")
            print("    1. Button is not connected to GPIO 21")
            print("    2. Button is not connected to GND")
            print("    3. Button is faulty (not making contact when pressed)")
            print("    4. Wrong GPIO pin (check if button is connected to GPIO 21)")
            print("    5. Loose or broken wire")
            print()
            print("  SOLUTION:")
            print("    1. Verify button is connected to GPIO 21 (BCM pin 21, physical pin 40)")
            print("    2. Verify button is connected to GND (any ground pin)")
            print("    3. Test button with multimeter (should show continuity when pressed)")
            print("    4. Check for loose connections or broken wires")
        
        print()
        print("Test 3: Release button test")
        print("  Please RELEASE the reset button now...")
        print("  (Press Enter when button is released)")
        input()
        
        released_reads = []
        for i in range(5):
            state = GPIO.input(RESET_PIN)
            released_reads.append(state)
            print(f"  Read {i+1}: {state} ({'HIGH' if state == GPIO.HIGH else 'LOW'})")
            time.sleep(0.1)
        
        if all(r == GPIO.HIGH for r in released_reads):
            print("  ✓ PASS: All reads are HIGH (1) - button is released (correct)")
        else:
            print(f"  ✗ FAIL: Inconsistent reads: {released_reads}")
            print("  WARNING: GPIO 21 may not be returning to HIGH after release")
        
        print()
        print("=" * 70)
        print("Diagnostic test completed")
        print("=" * 70)
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            GPIO.cleanup()
        except:
            pass

if __name__ == '__main__':
    try:
        test_gpio21_wiring()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        try:
            GPIO.cleanup()
        except:
            pass
        sys.exit(0)
