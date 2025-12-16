#!/usr/bin/env python3
"""
Test speaker/buzzer on a specific GPIO pin.
Usage: python3 test_speaker_pin.py [pin_number]
Example: python3 test_speaker_pin.py 27
"""

import sys
import time
import platform
import argparse

# Check if running on Raspberry Pi
if platform.system() != 'Linux':
    print("WARNING: This script is designed for Raspberry Pi (Linux)")
    print("GPIO operations will be simulated.")
    GPIO_AVAILABLE = False
else:
    try:
        import RPi.GPIO as GPIO
        GPIO_AVAILABLE = True
    except (ImportError, RuntimeError):
        print("ERROR: RPi.GPIO not available.")
        print("Install with: pip3 install RPi.GPIO")
        print("Or: sudo apt-get install python3-rpi.gpio")
        GPIO_AVAILABLE = False

# Default configuration
DEFAULT_PIN = 27
PWM_FREQUENCY = 1000  # Hz
BEEP_DURATION = 0.3  # seconds
BEEP_PAUSE = 0.1  # seconds
DEFAULT_VOLUME = 50  # PWM duty cycle percentage (0-100)

def print_header(text):
    """Print a formatted header."""
    print(f"\n{'=' * 70}")
    print(f"{text:^70}")
    print(f"{'=' * 70}\n")

def print_info(text):
    """Print info message."""
    print(f"[INFO] {text}")

def print_success(text):
    """Print success message."""
    print(f"[SUCCESS] {text}")

def print_warning(text):
    """Print warning message."""
    print(f"[WARNING] {text}")

def print_error(text):
    """Print error message."""
    print(f"[ERROR] {text}")

def force_disable_buzzer_immediate(pin: int):
    """Aggressively disable buzzer BEFORE any setup - handles existing GPIO state."""
    if not GPIO_AVAILABLE:
        return
    
    # Try multiple approaches to ensure buzzer is off
    # Approach 1: Try to set pin LOW if GPIO is already configured
    try:
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(0.01)
        GPIO.output(pin, GPIO.HIGH)
    except:
        pass
    
    # Approach 2: Try to setup pin quickly and set to LOW
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)  # Set initial state to LOW
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(0.01)
        GPIO.output(pin, GPIO.HIGH)
    except:
        pass
    
    # Approach 3: Cleanup and re-setup
    try:
        GPIO.cleanup()
        time.sleep(0.05)
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(0.05)
        GPIO.output(pin, GPIO.HIGH)
    except:
        pass

def setup_gpio(pin: int):
    """Setup GPIO pin as output and ensure it's OFF."""
    if not GPIO_AVAILABLE:
        print_warning("GPIO not available - simulating")
        return False
    
    # FIRST: Aggressively disable buzzer before any setup
#    force_disable_buzzer_immediate(pin)
    
    try:
        # Cleanup any existing GPIO state
        try:
#            GPIO.cleanup()
            i = 1
        except:
            pass
        
        # Small delay to ensure cleanup is complete
        time.sleep(0.1)
        
        # Setup GPIO with initial state LOW
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)  # Set initial state to LOW during setup
        
        # Immediately set to LOW (should already be LOW, but be explicit)
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(0.05)  # Small delay to ensure state is stable
        GPIO.output(pin, GPIO.HIGH)  # Set again to be sure
        time.sleep(0.05)  # Additional delay
        
        return True
    except ValueError as e:
        print_error(f"Invalid GPIO pin {pin}: {e}")
        return False
    except Exception as e:
        print_error(f"Failed to setup GPIO pin {pin}: {e}")
        # Even on error, try to disable buzzer
        try:
            GPIO.output(pin, GPIO.HIGH)
        except:
            pass
        return False

def disable_buzzer(pin: int):
    """Explicitly disable buzzer by setting pin to LOW."""
    if not GPIO_AVAILABLE:
        return
    
    try:
        # Try to set pin to LOW multiple times to ensure it's off
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(0.05)
        GPIO.output(pin, GPIO.HIGH)
    except:
        # If pin is not set up, try to set it up and then set to LOW
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.HIGH)
            time.sleep(0.05)
            GPIO.output(pin, GPIO.HIGH)
        except:
            pass

def cleanup_gpio():
    """Cleanup GPIO resources and ensure buzzer is OFF."""
    if GPIO_AVAILABLE:
        try:
            # Try to stop any PWM that might be running
            # Note: We can't directly access PWM objects here, but cleanup should handle it
            # First, try to set all pins to LOW if possible
            try:
                # Get the current mode to know which pins might be in use
                # Since we can't track PWM objects globally, we'll rely on cleanup
                pass
            except:
                pass
            
            # Cleanup will reset all GPIO pins
            GPIO.cleanup()
            
            # Small delay to ensure cleanup is complete
            time.sleep(0.1)
        except:
            pass

def play_tone_with_volume(pin: int, frequency: int, duration: float = 0.5, volume: int = DEFAULT_VOLUME):
    """
    Play a tone with specified volume (PWM duty cycle).
    
    Args:
        pin: GPIO pin number (BCM)
        frequency: Frequency in Hz
        duration: Duration in seconds
        volume: Volume as PWM duty cycle percentage (0-100)
                0% = silent, 50% = medium, 100% = maximum
    
    Returns:
        PWM object if successful, None otherwise
    """
    # Clamp volume to valid range
    volume = max(0, min(100, volume))
    
    if not GPIO_AVAILABLE:
        print_warning(f"Simulating tone on pin {pin} at {frequency}Hz, volume {volume}%")
        time.sleep(duration)
        return None
    
    try:
        pwm = GPIO.PWM(pin, frequency)
        pwm.start(volume)  # Start with specified volume (duty cycle)
        time.sleep(duration)
        pwm.stop()
        time.sleep(0.05)  # Small delay to ensure PWM is fully stopped
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(0.05)  # Additional delay to ensure state is stable
        return pwm
    except Exception as e:
        print_error(f"Error playing tone with volume: {e}")
        # Ensure pin is LOW even on error
        try:
            GPIO.output(pin, GPIO.HIGH)
        except:
            pass
        return None

def test_simple_on_off(pin: int, duration: float = 0.5):
    """Test pin with simple on/off (for active buzzers)."""
    if not GPIO_AVAILABLE:
        print_warning(f"Simulating simple on/off on pin {pin}")
        time.sleep(duration)
        return True
    
    try:
        print_info(f"Turning ON pin {pin}...")
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(duration)
        print_info(f"Turning OFF pin {pin}...")
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(duration)
        return True
    except Exception as e:
        print_error(f"Error in simple on/off test: {e}")
        return False

def test_pwm_tone(pin: int, frequency: int, duration: float = 0.5, volume: int = DEFAULT_VOLUME):
    """
    Test pin with PWM tone (for passive speakers/buzzers).
    
    Volume is controlled by PWM duty cycle:
    - 0% = silent (no sound)
    - 25% = quiet
    - 50% = medium (default)
    - 75% = loud
    - 100% = maximum volume
    """
    if not GPIO_AVAILABLE:
        print_warning(f"Simulating PWM tone on pin {pin} at {frequency}Hz, volume {volume}%")
        time.sleep(duration)
        return True
    
    try:
        print_info(f"Playing PWM tone {frequency}Hz on pin {pin} at {volume}% volume...")
        play_tone_with_volume(pin, frequency, duration, volume)
        return True
    except Exception as e:
        print_error(f"Error in PWM test: {e}")
        return False

def test_beep_pattern(pin: int, count: int, duration: float = 0.3, frequency: int = None):
    """Test beep pattern (multiple beeps)."""
    if not GPIO_AVAILABLE:
        print_warning(f"Simulating {count} beeps on pin {pin}")
        time.sleep(count * duration)
        return True
    
    try:
        print_info(f"Playing {count} beep(s) on pin {pin}...")
        for i in range(count):
            if frequency:
                # Use PWM for tone
                pwm = GPIO.PWM(pin, frequency)
                pwm.start(50)
                time.sleep(duration)
                pwm.stop()
                # Ensure pin is LOW after PWM stops
                GPIO.output(pin, GPIO.HIGH)
                time.sleep(0.05)  # Small delay to ensure PWM is fully stopped
            else:
                # Simple on/off
                GPIO.output(pin, GPIO.HIGH)
                time.sleep(duration)
                GPIO.output(pin, GPIO.HIGH)
            
            if i < count - 1:
                time.sleep(BEEP_PAUSE)
        
        # Final ensure pin is LOW
        GPIO.output(pin, GPIO.HIGH)
        test_simple_on_off(pin, duration=1.0)
        return True
    except Exception as e:
        print_error(f"Error in beep pattern test: {e}")
        return False

def test_frequency_sweep(pin: int, start_freq: int = 500, end_freq: int = 2000, step: int = 100):
    """Test different frequencies (frequency sweep)."""
    if not GPIO_AVAILABLE:
        print_warning(f"Simulating frequency sweep on pin {pin}")
        return True
    
    try:
        print_info(f"Frequency sweep on pin {pin} ({start_freq}Hz to {end_freq}Hz)...")
        pwm = GPIO.PWM(pin, start_freq)
        pwm.start(50)
        
        for freq in range(start_freq, end_freq + 1, step):
            pwm.ChangeFrequency(freq)
            print_info(f"  Playing {freq}Hz...")
            time.sleep(0.2)
        
        pwm.stop()
        time.sleep(0.05)  # Small delay to ensure PWM is fully stopped
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(0.05)  # Additional delay to ensure state is stable
        return True
    except Exception as e:
        print_error(f"Error in frequency sweep: {e}")
        # Ensure pin is LOW even on error
        try:
            GPIO.output(pin, GPIO.HIGH)
        except:
            pass
        return False

def test_continuous_tone(pin: int, frequency: int, duration: float = 2.0):
    """Test continuous tone."""
    if not GPIO_AVAILABLE:
        print_warning(f"Simulating continuous tone on pin {pin}")
        time.sleep(duration)
        return True
    
    try:
        print_info(f"Playing continuous tone {frequency}Hz for {duration}s on pin {pin}...")
        print_info("Press Ctrl+C to stop early")
        pwm = GPIO.PWM(pin, frequency)
        pwm.start(50)
        
        try:
            time.sleep(duration)
        except KeyboardInterrupt:
            print_info("\nStopped early by user")
        
        pwm.stop()
        time.sleep(0.05)  # Small delay to ensure PWM is fully stopped
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(0.05)  # Additional delay to ensure state is stable
        return True
    except Exception as e:
        print_error(f"Error in continuous tone test: {e}")
        # Ensure pin is LOW even on error
        try:
            GPIO.output(pin, GPIO.HIGH)
        except:
            pass
        return False

def test_volume(pin: int, frequency: int = None, duration: float = 0.5):
    """Test buzzer volume by varying PWM duty cycle (0% to 100%)."""
    if frequency is None:
        frequency = PWM_FREQUENCY
    
    if not GPIO_AVAILABLE:
        print_warning(f"Simulating volume test on pin {pin}")
        print_warning("Volume levels: 0%, 25%, 50%, 75%, 100%")
        time.sleep(duration * 5)
        return True
    
    try:
        print_info(f"Volume test on pin {pin} at {frequency}Hz")
        print_info("Testing different volume levels (duty cycles)...")
        
        # Test different duty cycles: 0%, 25%, 50%, 75%, 100%
        volume_levels = [0, 25, 50, 75, 100]
        
        pwm = GPIO.PWM(pin, frequency)
        pwm.start(0)  # Start at 0% (silent)
        
        for duty_cycle in volume_levels:
            print_info(f"  Volume: {duty_cycle}% (duty cycle)")
            pwm.ChangeDutyCycle(duty_cycle)
            time.sleep(duration)
        
        # Stop PWM
        pwm.stop()
        time.sleep(0.05)  # Small delay to ensure PWM is fully stopped
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(0.05)  # Additional delay to ensure state is stable
        return True
    except Exception as e:
        print_error(f"Error in volume test: {e}")
        # Ensure pin is LOW even on error
        try:
            pwm.stop()
            GPIO.output(pin, GPIO.HIGH)
        except:
            pass
        return False

def run_interactive_test(pin: int):
    """Run interactive test menu."""
    # FIRST THING: Aggressively disable buzzer before anything else
#    if GPIO_AVAILABLE:
#        force_disable_buzzer_immediate(pin)
    print_header(f"Speaker Test - GPIO Pin {pin}")
    print_info(f"Testing speaker/buzzer on GPIO pin {pin} (BCM)")
    print_info("Physical pin mapping depends on your Raspberry Pi model")
    print()
    if not GPIO_AVAILABLE:
        print_error("RPi.GPIO not available. Running in simulation mode.")
        print_error("Make sure you are on a Raspberry Pi and RPi.GPIO is installed.")
        return
    
    if not setup_gpio(pin):
        print_error("Failed to setup GPIO")
        return

    
    # Ensure buzzer is OFF at startup (redundant but safe)
#    disable_buzzer(pin)
    
    try:
        while True:
            print("\n" + "=" * 70)
            print("Test Menu")
            print("=" * 70)
            print("1. Simple ON/OFF test (for active buzzers)")
            print("2. PWM tone test (for passive speakers)")
            print("3. Single beep")
            print("4. Critical alarm pattern (3 beeps)")
            print("5. Warning alarm pattern (2 beeps)")
            print("6. Info beep (1 beep)")
            print("7. Frequency sweep (500Hz to 2000Hz)")
            print("8. Custom frequency test")
            print("9. Continuous tone (Press Ctrl+C to stop)")
            print("10. Volume test (test different volume levels)")
            print("11. Play tone with custom volume")
            print("0. Exit")
            print("=" * 70)
            
            try:
                choice = input("\nEnter your choice: ").strip()
            except (EOFError, KeyboardInterrupt):
                print_info("\nExiting...")
                break
            
            if choice == '0':
                print_info("Exiting test program.")
                # Ensure buzzer is OFF before exiting
                disable_buzzer(pin)
                break
            elif choice == '1':
                print_info("Test 1: Simple ON/OFF (1 second each)")
                test_simple_on_off(pin, duration=1.0)
                print_success("Simple ON/OFF test completed!")
            elif choice == '2':
                print_info(f"Test 2: PWM tone ({PWM_FREQUENCY}Hz for 1 second)")
                test_pwm_tone(pin, PWM_FREQUENCY, duration=1.0)
                print_success("PWM tone test completed!")
            elif choice == '3':
                print_info("Test 3: Single beep")
                test_beep_pattern(pin, count=1, duration=BEEP_DURATION, frequency=PWM_FREQUENCY)
                print_success("Single beep completed!")
            elif choice == '4':
                print_info("Test 4: Critical alarm pattern (3 beeps)")
                test_beep_pattern(pin, count=3, duration=BEEP_DURATION, frequency=PWM_FREQUENCY)
                print_success("Critical alarm pattern completed!")
            elif choice == '5':
                print_info("Test 5: Warning alarm pattern (2 beeps)")
                test_beep_pattern(pin, count=2, duration=BEEP_DURATION, frequency=PWM_FREQUENCY)
                print_success("Warning alarm pattern completed!")
            elif choice == '6':
                print_info("Test 6: Info beep (1 beep)")
                test_beep_pattern(pin, count=1, duration=BEEP_DURATION, frequency=PWM_FREQUENCY)
                print_success("Info beep completed!")
            elif choice == '7':
                print_info("Test 7: Frequency sweep")
                test_frequency_sweep(pin, start_freq=500, end_freq=2000, step=100)
                print_success("Frequency sweep completed!")
            elif choice == '8':
                try:
                    freq = int(input("Enter frequency (Hz, e.g., 1000): "))
                    dur = float(input("Enter duration (seconds, e.g., 0.5): "))
                    vol_input = input(f"Enter volume (0-100%, default {DEFAULT_VOLUME}%): ").strip()
                    vol = int(vol_input) if vol_input else DEFAULT_VOLUME
                    vol = max(0, min(100, vol))  # Clamp to valid range
                    print_info(f"Test 8: Custom frequency {freq}Hz for {dur}s at {vol}% volume")
                    test_pwm_tone(pin, freq, duration=dur, volume=vol)
                    print_success("Custom frequency test completed!")
                except ValueError:
                    print_error("Invalid input. Please enter numbers.")
            elif choice == '9':
                try:
                    freq = int(input(f"Enter frequency (Hz, default {PWM_FREQUENCY}): ") or PWM_FREQUENCY)
                    dur = float(input("Enter duration (seconds, default 5): ") or "5")
                    test_continuous_tone(pin, freq, duration=dur)
                    print_success("Continuous tone test completed!")
                except ValueError:
                    print_error("Invalid input. Please enter numbers.")
            elif choice == '10':
                try:
                    freq_input = input(f"Enter frequency (Hz, default {PWM_FREQUENCY}): ").strip()
                    freq = int(freq_input) if freq_input else PWM_FREQUENCY
                    dur_input = input("Enter duration per volume level (seconds, default 0.5): ").strip()
                    dur = float(dur_input) if dur_input else 0.5
                    print_info("Test 10: Volume test (testing 0%, 25%, 50%, 75%, 100% duty cycles)")
                    test_volume(pin, frequency=freq, duration=dur)
                    print_success("Volume test completed!")
                except ValueError:
                    print_error("Invalid input. Please enter numbers.")
            elif choice == '11':
                try:
                    freq_input = input(f"Enter frequency (Hz, default {PWM_FREQUENCY}): ").strip()
                    freq = int(freq_input) if freq_input else PWM_FREQUENCY
                    dur_input = input("Enter duration (seconds, default 1.0): ").strip()
                    dur = float(dur_input) if dur_input else 1.0
                    vol_input = input(f"Enter volume/duty cycle (0-100%, default {DEFAULT_VOLUME}%): ").strip()
                    vol = int(vol_input) if vol_input else DEFAULT_VOLUME
                    # Clamp volume to valid range
                    vol = max(0, min(100, vol))
                    print_info(f"Test 11: Playing tone at {freq}Hz, {dur}s, volume {vol}%")
                    play_tone_with_volume(pin, freq, dur, vol)
                    print_success("Custom volume tone completed!")
                except ValueError:
                    print_error("Invalid input. Please enter numbers.")
            else:
                print_warning("Invalid choice. Please try again.")
    
    except KeyboardInterrupt:
        print_info("\n\nTest interrupted by user")
    except Exception as e:
        print_error(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup_gpio()
        print_info("GPIO cleaned up")

def run_quick_test(pin: int):
    """Run quick automated test."""
    # FIRST THING: Aggressively disable buzzer before anything else
    if GPIO_AVAILABLE:
        force_disable_buzzer_immediate(pin)
    
    print_header(f"Quick Speaker Test - GPIO Pin {pin}")
    print_info(f"Testing speaker/buzzer on GPIO pin {pin} (BCM)\n")
    
    if not GPIO_AVAILABLE:
        print_error("RPi.GPIO not available. Running in simulation mode.")
        return
    
    if not setup_gpio(pin):
        print_error("Failed to setup GPIO")
        return
    
    try:
        print("Running quick tests...\n")
        
        # Test 1: Simple on/off
        print("Test 1: Simple ON/OFF (1 second each)")
        test_simple_on_off(pin, duration=1.0)
        time.sleep(0.5)
        
        # Test 2: PWM tone
        print("\nTest 2: PWM tone (1000Hz for 1 second)")
        test_pwm_tone(pin, PWM_FREQUENCY, duration=1.0)
        time.sleep(0.5)
        
        # Test 3: Beep patterns
        print("\nTest 3: Critical alarm (3 beeps)")
        test_beep_pattern(pin, count=3, duration=BEEP_DURATION, frequency=PWM_FREQUENCY)
        time.sleep(0.5)
        
        print("\nTest 4: Warning alarm (2 beeps)")
        test_beep_pattern(pin, count=2, duration=BEEP_DURATION, frequency=PWM_FREQUENCY)
        time.sleep(0.5)
        
        print("\nTest 5: Info beep (1 beep)")
        test_beep_pattern(pin, count=1, duration=BEEP_DURATION, frequency=PWM_FREQUENCY)
        
        print_header("Quick Test Complete")
        print_success("All tests completed!")
        print()
        print("If you didn't hear any sound, check:")
        print("  1. Speaker/buzzer is connected to GPIO pin", pin, "(BCM)")
        print("  2. Ground (GND) is connected properly")
        print("  3. For active buzzers: Check power requirements (3.3V or 5V)")
        print("  4. For passive buzzers: PWM frequency control is required")
        print("  5. Try adjusting the duty cycle or frequency")
    
    except KeyboardInterrupt:
        print_info("\n\nTest interrupted by user")
    except Exception as e:
        print_error(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup_gpio()
        print_info("GPIO cleaned up")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Test speaker/buzzer on a specific GPIO pin',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive test on pin 27
  python3 test_speaker_pin.py 27
  
  # Quick test on pin 27
  python3 test_speaker_pin.py 27 --quick
  
  # Test on pin 18
  python3 test_speaker_pin.py 18
        """
    )
    
    parser.add_argument(
        'pin',
        type=int,
        nargs='?',
        default=None,
        help=f'GPIO pin number (BCM). Default: {DEFAULT_PIN}'
    )
    
    parser.add_argument(
        '--quick', '-q',
        action='store_true',
        help='Run quick automated test instead of interactive menu'
    )
    
    parser.add_argument(
        '--frequency', '-f',
        type=int,
        default=PWM_FREQUENCY,
        help=f'PWM frequency in Hz (default: {PWM_FREQUENCY})'
    )
    
    parser.add_argument(
        '--duration', '-d',
        type=float,
        default=BEEP_DURATION,
        help=f'Beep duration in seconds (default: {BEEP_DURATION})'
    )
    
    args = parser.parse_args()
    
    # Determine pin number
    if args.pin is not None:
        pin = args.pin
    else:
        # Try to get from user input
        try:
            pin_str = input(f"Enter GPIO pin number (BCM, default {DEFAULT_PIN}): ").strip()
            pin = int(pin_str) if pin_str else DEFAULT_PIN
        except (EOFError, KeyboardInterrupt, ValueError):
            pin = DEFAULT_PIN
            print_info(f"Using default pin: {pin}")
    
    # Validate pin number
    if pin < 0 or pin > 40:
        print_error(f"Invalid GPIO pin number: {pin}")
        print_error("GPIO pins are typically 0-40 on Raspberry Pi")
        sys.exit(1)   
    # Run test
    if args.quick:
        run_quick_test(pin)
    else:
        run_interactive_test(pin)

if __name__ == '__main__':
    main()

