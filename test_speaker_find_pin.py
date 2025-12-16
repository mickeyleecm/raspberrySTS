#!/usr/bin/env python3
"""
Test program to find which GPIO pin a speaker/buzzer is connected to.
Tests pins 18 to 60 sequentially.
"""

import sys
import time
import platform

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

# Configuration
START_PIN = 18
END_PIN = 60
TEST_DURATION = 1.0  # seconds per pin
PWM_FREQUENCY = 1000  # Hz for PWM tone generation
PAUSE_BETWEEN_PINS = 0.5  # seconds

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

def test_pin_simple(pin: int, duration: float = 0.5):
    """Test pin with simple on/off (for active buzzers)."""
    if not GPIO_AVAILABLE:
        return False
    
    try:
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(pin, GPIO.LOW)
        return True
    except Exception as e:
        print_error(f"Error testing pin {pin} (simple): {e}")
        return False

def test_pin_pwm(pin: int, frequency: int, duration: float = 0.5):
    """Test pin with PWM tone (for passive speakers/buzzers)."""
    if not GPIO_AVAILABLE:
        return False
    
    try:
        pwm = GPIO.PWM(pin, frequency)
        pwm.start(50)  # 50% duty cycle
        time.sleep(duration)
        pwm.stop()
        return True
    except Exception as e:
        print_error(f"Error testing pin {pin} (PWM): {e}")
        return False

def setup_gpio():
    """Setup GPIO mode."""
    if not GPIO_AVAILABLE:
        return False
    
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        return True
    except Exception as e:
        print_error(f"Failed to setup GPIO: {e}")
        return False

def cleanup_gpio():
    """Cleanup GPIO resources."""
    if GPIO_AVAILABLE:
        try:
            GPIO.cleanup()
        except:
            pass

def test_single_pin(pin: int, test_mode: str = 'both'):
    """
    Test a single GPIO pin.
    
    Args:
        pin: GPIO pin number (BCM)
        test_mode: 'simple', 'pwm', or 'both'
    
    Returns:
        True if pin was tested successfully, False otherwise
    """
    if not GPIO_AVAILABLE:
        print_warning(f"Simulating test on pin {pin}")
        return True
    
    # Check if pin is valid
    # Some pins are reserved or not available on all Raspberry Pi models
    invalid_pins = [27, 28]  # I2C pins that might cause issues
    if pin in invalid_pins:
        print_warning(f"Skipping pin {pin} (reserved/I2C)")
        return False
    
    try:
        # Setup pin as output
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)  # Start with LOW
        
        success = False
        
        if test_mode in ['simple', 'both']:
            # Test 1: Simple on/off (for active buzzers)
            print(f"  Testing pin {pin:2d} (simple on/off)...", end='', flush=True)
            if test_pin_simple(pin, duration=0.3):
                print(" ✓")
                success = True
            else:
                print(" ✗")
        
        if test_mode in ['pwm', 'both']:
            # Test 2: PWM tone (for passive speakers)
            print(f"  Testing pin {pin:2d} (PWM tone {PWM_FREQUENCY}Hz)...", end='', flush=True)
            if test_pin_pwm(pin, PWM_FREQUENCY, duration=0.3):
                print(" ✓")
                success = True
            else:
                print(" ✗")
        
        # Reset pin to LOW
        GPIO.output(pin, GPIO.LOW)
        
        return success
        
    except ValueError as e:
        # Pin not available on this Raspberry Pi model
        print_warning(f"Pin {pin} not available: {e}")
        return False
    except Exception as e:
        print_error(f"Error testing pin {pin}: {e}")
        return False

def test_all_pins_auto(start_pin: int, end_pin: int, test_mode: str = 'both'):
    """
    Automatically test all pins from start to end.
    
    Args:
        start_pin: Starting GPIO pin number
        end_pin: Ending GPIO pin number
        test_mode: 'simple', 'pwm', or 'both'
    """
    print_header("Automatic Pin Testing Mode")
    print_info(f"Testing pins {start_pin} to {end_pin}")
    print_info(f"Test mode: {test_mode}")
    print_info("Listen for the speaker sound on each pin")
    print_info("Press Ctrl+C to stop at any time\n")
    
    found_pins = []
    
    for pin in range(start_pin, end_pin + 1):
        try:
            print(f"\n[{pin - start_pin + 1}/{end_pin - start_pin + 1}] Testing GPIO pin {pin} (BCM)...")
            
            if test_single_pin(pin, test_mode):
                print_success(f"Pin {pin} tested - Did you hear sound? (y/n/q to quit)")
                
                # Wait for user input (non-blocking would be better, but simple for now)
                try:
                    response = input().strip().lower()
                    if response == 'q':
                        print_info("Testing stopped by user")
                        break
                    elif response == 'y':
                        found_pins.append(pin)
                        print_success(f"✓ Pin {pin} CONFIRMED - Speaker found!")
                        print_info("Continue testing other pins? (y/n)")
                        continue_test = input().strip().lower()
                        if continue_test != 'y':
                            break
                except (EOFError, KeyboardInterrupt):
                    print_info("\nTesting interrupted")
                    break
            else:
                print_warning(f"Pin {pin} test failed or skipped")
            
            time.sleep(PAUSE_BETWEEN_PINS)
            
        except KeyboardInterrupt:
            print_info("\n\nTesting interrupted by user")
            break
        except Exception as e:
            print_error(f"Unexpected error testing pin {pin}: {e}")
            continue
    
    # Summary
    print_header("Testing Summary")
    if found_pins:
        print_success(f"Speaker found on GPIO pin(s): {', '.join(map(str, found_pins))}")
        print_info("Physical pin mapping:")
        for pin in found_pins:
            # Common physical pin mappings (40-pin header)
            # This is approximate - actual mapping depends on Raspberry Pi model
            print_info(f"  GPIO {pin} (BCM) = Physical pin (check your wiring diagram)")
    else:
        print_warning("No speaker found in tested pins")
        print_info("Possible reasons:")
        print_info("  1. Speaker is connected to a pin outside range 18-60")
        print_info("  2. Speaker requires different test method")
        print_info("  3. Speaker is not properly connected")
        print_info("  4. Speaker requires external power")

def test_all_pins_manual(start_pin: int, end_pin: int, test_mode: str = 'both'):
    """
    Manual testing mode - user controls when to test each pin.
    
    Args:
        start_pin: Starting GPIO pin number
        end_pin: Ending GPIO pin number
        test_mode: 'simple', 'pwm', or 'both'
    """
    print_header("Manual Pin Testing Mode")
    print_info(f"Pins available: {start_pin} to {end_pin}")
    print_info(f"Test mode: {test_mode}")
    print_info("Commands:")
    print_info("  <number> - Test specific pin")
    print_info("  n/next   - Test next pin")
    print_info("  a/auto    - Switch to automatic mode")
    print_info("  q/quit    - Quit")
    print()
    
    current_pin = start_pin
    found_pins = []
    
    while current_pin <= end_pin:
        try:
            command = input(f"Test pin {current_pin}? (y/n/next/auto/quit): ").strip().lower()
            
            if command in ['q', 'quit']:
                break
            elif command in ['a', 'auto']:
                print_info("Switching to automatic mode...")
                test_all_pins_auto(current_pin, end_pin, test_mode)
                break
            elif command in ['n', 'next']:
                current_pin += 1
                continue
            elif command in ['y', 'yes', '']:
                print(f"\nTesting GPIO pin {current_pin} (BCM)...")
                if test_single_pin(current_pin, test_mode):
                    response = input("Did you hear sound? (y/n): ").strip().lower()
                    if response == 'y':
                        found_pins.append(current_pin)
                        print_success(f"✓ Pin {current_pin} CONFIRMED - Speaker found!")
                current_pin += 1
            elif command.isdigit():
                # Test specific pin
                test_pin = int(command)
                if start_pin <= test_pin <= end_pin:
                    print(f"\nTesting GPIO pin {test_pin} (BCM)...")
                    if test_single_pin(test_pin, test_mode):
                        response = input("Did you hear sound? (y/n): ").strip().lower()
                        if response == 'y':
                            if test_pin not in found_pins:
                                found_pins.append(test_pin)
                            print_success(f"✓ Pin {test_pin} CONFIRMED - Speaker found!")
                    current_pin = test_pin + 1
                else:
                    print_error(f"Pin {test_pin} is outside range {start_pin}-{end_pin}")
            else:
                print_warning("Invalid command. Use: y/n/next/auto/quit or pin number")
                
        except (EOFError, KeyboardInterrupt):
            print_info("\n\nTesting interrupted")
            break
        except Exception as e:
            print_error(f"Error: {e}")
    
    # Summary
    print_header("Testing Summary")
    if found_pins:
        print_success(f"Speaker found on GPIO pin(s): {', '.join(map(str, found_pins))}")
    else:
        print_warning("No speaker found")

def main():
    """Main function."""
    print_header("Raspberry Pi Speaker Pin Finder")
    print_info("This program tests GPIO pins 18-60 to find which pin your speaker is connected to")
    print()
    
    if not GPIO_AVAILABLE:
        print_error("RPi.GPIO not available. Running in simulation mode.")
        print_error("Make sure you are on a Raspberry Pi and RPi.GPIO is installed.")
        sys.exit(1)
    
    if not setup_gpio():
        print_error("Failed to setup GPIO")
        sys.exit(1)
    
    try:
        print("Select testing mode:")
        print("  1. Automatic (tests all pins sequentially)")
        print("  2. Manual (you control which pin to test)")
        print("  3. Quick test (tests all pins quickly, no interaction)")
        
        choice = input("\nEnter choice (1/2/3): ").strip()
        
        print("\nSelect test method:")
        print("  1. Simple on/off (for active buzzers)")
        print("  2. PWM tone (for passive speakers)")
        print("  3. Both methods")
        
        test_choice = input("Enter choice (1/2/3, default=3): ").strip() or '3'
        
        if test_choice == '1':
            test_mode = 'simple'
        elif test_choice == '2':
            test_mode = 'pwm'
        else:
            test_mode = 'both'
        
        if choice == '1':
            test_all_pins_auto(START_PIN, END_PIN, test_mode)
        elif choice == '2':
            test_all_pins_manual(START_PIN, END_PIN, test_mode)
        elif choice == '3':
            # Quick test - test all pins without interaction
            print_header("Quick Test Mode")
            print_info("Testing all pins quickly - listen for sound")
            print_info("Press Ctrl+C to stop\n")
            
            found_pins = []
            for pin in range(START_PIN, END_PIN + 1):
                try:
                    print(f"Testing pin {pin}...", end='', flush=True)
                    if test_single_pin(pin, test_mode):
                        print(" ✓")
                        time.sleep(0.2)  # Short pause
                    else:
                        print(" ✗")
                except KeyboardInterrupt:
                    print("\n\nQuick test interrupted")
                    break
                except Exception as e:
                    print(f" Error: {e}")
            
            print_header("Quick Test Complete")
            print_info("If you heard sound, note which pin number it was")
            print_info("Run in manual mode to confirm specific pins")
        else:
            print_error("Invalid choice")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print_info("\n\nTest interrupted by user")
    except Exception as e:
        print_error(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup_gpio()
        print_info("GPIO cleaned up")

if __name__ == '__main__':
    main()

