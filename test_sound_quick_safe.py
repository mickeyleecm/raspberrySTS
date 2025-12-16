#!/usr/bin/env python3
"""
Safe Sound Test for Raspberry Pi
Uses only GPIO-based audio (no speaker-test) to avoid network conflicts.
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

# Configuration - Test common GPIO pins for speakers
# These are safe pins that don't conflict with network
SAFE_SPEAKER_PINS = [18, 19, 21, 22, 23, 24, 25, 27]  # Common PWM-capable pins
PWM_FREQUENCY = 1000  # Hz
BEEP_DURATION = 0.3  # seconds

def test_speaker_gpio(pin: int, frequency: int = 1000, duration: float = 0.3):
    """Test speaker using GPIO PWM (safe method)."""
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(pin, GPIO.OUT)
        
        # Use PWM for tone generation
        pwm = GPIO.PWM(pin, frequency)
        pwm.start(50)  # 50% duty cycle
        time.sleep(duration)
        pwm.stop()
        
        GPIO.output(pin, GPIO.LOW)
        return True
    except Exception as e:
        print(f"  Error on pin {pin}: {e}")
        return False

def main():
    """Safe sound test using GPIO only."""
    print("=" * 70)
    print("Safe Raspberry Pi Sound Test (GPIO Only)")
    print("=" * 70)
    print()
    print("This version uses GPIO PWM only (no speaker-test)")
    print("to avoid network conflicts.")
    print()
    
    if not GPIO_AVAILABLE:
        print("ERROR: RPi.GPIO not available")
        sys.exit(1)
    
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        print("Testing common speaker GPIO pins...")
        print("Listen for sound on each pin.\n")
        
        for pin in SAFE_SPEAKER_PINS:
            print(f"Testing GPIO pin {pin}...", end='', flush=True)
            if test_speaker_gpio(pin, PWM_FREQUENCY, BEEP_DURATION):
                print(" ✓")
            else:
                print(" ✗")
            time.sleep(0.5)
        
        print()
        print("=" * 70)
        print("Test Complete!")
        print("=" * 70)
        print()
        print("If you heard sound, note which GPIO pin it was.")
        print("Then you can use that pin in your UPS trap receiver.")
        print()
        print("To test a specific pin, use:")
        print("  python3 test_speaker_find_pin.py")
        
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

if __name__ == '__main__':
    main()

