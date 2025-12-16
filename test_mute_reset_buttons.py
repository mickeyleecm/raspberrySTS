#!/usr/bin/env python3
"""
Test Mute and Reset buttons on STS Panel.
Monitors GPIO pins 19 (Mute) and 21 (Reset) for button presses.

Usage:
    python3 test_mute_reset_buttons.py              # Interactive mode
    python3 test_mute_reset_buttons.py --continuous # Continuous monitoring
    python3 test_mute_reset_buttons.py --polling    # Polling mode (default)
    python3 test_mute_reset_buttons.py --interrupt  # Interrupt mode
"""

import sys
import time
import platform
import argparse
from datetime import datetime
from typing import Optional, Callable

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

# Button configuration from AlarmMap.py
MUTE_PIN = 19
RESET_PIN = 21

# Debouncing configuration
DEBOUNCE_TIME = 0.01  # 10ms debounce time (reduced for faster response)
POLLING_INTERVAL = 0.01  # 10ms polling interval

# Button state tracking
class ButtonState:
    def __init__(self, pin: int, name: str):
        self.pin = pin
        self.name = name
        self.last_state = None
        self.last_change_time = 0
        self.press_count = 0
        self.release_count = 0
        self.pending_state = None  # For debouncing in polling mode
        self.pending_state_time = 0  # Time when pending state was first detected
        self.last_callback_time = 0  # For debouncing in interrupt mode
        self.last_callback_state = None  # Last state reported in callback
        self.last_edge_type = None  # Last edge type ('press' or 'release') for interrupt mode

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

def setup_gpio_inputs(mute_pin: int, reset_pin: int) -> bool:
    """Setup GPIO pins as inputs with pull-up resistors."""
    if not GPIO_AVAILABLE:
        print_warning("GPIO not available - simulating")
        return False
    
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
        
        # Setup pins as inputs with pull-up resistors
        # When button is pressed, pin goes LOW (0)
        # When button is released, pin goes HIGH (1) due to pull-up
        GPIO.setup(mute_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(reset_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        print_success(f"GPIO pins configured:")
        print_success(f"  Mute button: GPIO {mute_pin} (Input, Pull-up)")
        print_success(f"  Reset button: GPIO {reset_pin} (Input, Pull-up)")
        print_info("Button logic: Pressed = LOW (0), Released = HIGH (1)")
        
        return True
    except Exception as e:
        print_error(f"Failed to setup GPIO: {e}")
        return False

def read_button_state(pin: int, verbose: bool = False) -> bool:
    """Read button state. Returns True if pressed (LOW), False if released (HIGH)."""
    if not GPIO_AVAILABLE:
        if verbose:
            print_warning(f"GPIO not available - simulating pin {pin}")
        return False
    
    try:
        # With pull-up: LOW (0) = pressed, HIGH (1) = released
        state = GPIO.input(pin)
        raw_value = state  # Store raw value for debugging
        is_pressed = state == GPIO.LOW
        
        if verbose:
            print_info(f"  GPIO {pin} raw value: {raw_value} ({'LOW' if raw_value == GPIO.LOW else 'HIGH'})")
        
        return is_pressed
    except RuntimeError as e:
        if verbose:
            print_error(f"RuntimeError reading pin {pin}: {e}")
            print_error(f"  Pin {pin} may not be configured as input")
        return False
    except Exception as e:
        if verbose:
            print_error(f"Error reading pin {pin}: {e}")
            import traceback
            traceback.print_exc()
        return False

def cleanup_gpio():
    """Cleanup GPIO resources."""
    if GPIO_AVAILABLE:
        try:
            GPIO.cleanup()
            print_info("GPIO cleaned up")
        except:
            pass

def detect_button_press(
    button_state: ButtonState,
    debounce_time: float = DEBOUNCE_TIME
) -> Optional[str]:
    """
    Detect button press with debouncing.
    Returns 'pressed' or 'released' if state changed, None otherwise.
    """
    current_state = read_button_state(button_state.pin)
    current_time = time.time()
    
    # Initialize last_state if None
    if button_state.last_state is None:
        button_state.last_state = current_state
        button_state.last_change_time = current_time
        button_state.pending_state = None
        button_state.pending_state_time = 0
        return None
    
    # Check if state changed from last confirmed state
    if current_state != button_state.last_state:
        # State is different - check if we have a pending state change
        if button_state.pending_state is None:
            # First time seeing this new state - record it as pending
            button_state.pending_state = current_state
            button_state.pending_state_time = current_time
            return None
        elif button_state.pending_state == current_state:
            # Same pending state - check if debounce time has passed
            time_since_pending = current_time - button_state.pending_state_time
            if time_since_pending >= debounce_time:
                # Debounce time passed - confirm state change
            button_state.last_state = current_state
            button_state.last_change_time = current_time
                button_state.pending_state = None
                button_state.pending_state_time = 0
            
            if current_state:  # Button pressed (LOW)
                button_state.press_count += 1
                return 'pressed'
            else:  # Button released (HIGH)
                button_state.release_count += 1
                return 'released'
            # Still debouncing - wait more
            return None
        else:
            # State changed again before debounce completed - reset pending
            button_state.pending_state = current_state
            button_state.pending_state_time = current_time
            return None
    else:
        # State matches last confirmed state - clear any pending state
        if button_state.pending_state is not None:
            button_state.pending_state = None
            button_state.pending_state_time = 0
    
    return None

def button_callback(channel: int, button_name: str, button_state: ButtonState):
    """Callback function for button interrupt with minimal debouncing."""
    current_time_sec = time.time()
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    # Read current state FIRST
    # With GPIO.BOTH, the callback is triggered on both edges, so we need to read
    # the actual state to determine if it's a press or release
    state = read_button_state(channel)
    edge_type = 'press' if state else 'release'
    
    # Calculate time since last callback
    time_since_last = current_time_sec - button_state.last_callback_time
    
    # Only process if state actually changed from last known state
    # This is the key - we only care about state transitions, not repeated states
    if button_state.last_callback_state is not None:
        if button_state.last_callback_state == state:
            # State hasn't changed - this is likely a bounce or duplicate event
            # Only ignore if it's very recent (within debounce window)
            if time_since_last < DEBOUNCE_TIME:
                return  # Ignore duplicate state within debounce window
        # State changed - always process (hardware bouncetime already handled initial debouncing)
    
    # State changed or first event - process it
    button_state.last_callback_time = current_time_sec
    button_state.last_edge_type = edge_type
    button_state.last_callback_state = state
    
    # Process the event
    if state:  # Button pressed (LOW)
        button_state.press_count += 1
        print_success(f"[{current_time_str}] {button_name} button PRESSED (GPIO {channel})")
        print_info(f"  Total presses: {button_state.press_count}")
    else:  # Button released (HIGH)
        button_state.release_count += 1
        print_info(f"[{current_time_str}] {button_name} button RELEASED (GPIO {channel})")
        print_info(f"  Total releases: {button_state.release_count}")

def run_polling_mode(mute_state: ButtonState, reset_state: ButtonState, continuous: bool = False):
    """Run button monitoring in polling mode."""
    print_header("Button Test - Polling Mode")
    print_info("Monitoring buttons using polling (checking every 10ms)")
    print_info("Press Ctrl+C to exit\n")
    
    try:
        while True:
            # Check Mute button
            mute_event = detect_button_press(mute_state)
            if mute_event == 'pressed':
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                print_success(f"[{timestamp}] MUTE button PRESSED (GPIO {MUTE_PIN})")
                print_info(f"  Total presses: {mute_state.press_count}")
            elif mute_event == 'released':
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                print_info(f"[{timestamp}] MUTE button RELEASED (GPIO {MUTE_PIN})")
            
            # Check Reset button
            reset_event = detect_button_press(reset_state)
            if reset_event == 'pressed':
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                print_success(f"[{timestamp}] RESET button PRESSED (GPIO {RESET_PIN})")
                print_info(f"  Total presses: {reset_state.press_count}")
            elif reset_event == 'released':
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                print_info(f"[{timestamp}] RESET button RELEASED (GPIO {RESET_PIN})")
            
            # Show current state periodically (every 5 seconds) if in continuous mode
            if continuous:
                current_time = time.time()
                if not hasattr(run_polling_mode, 'last_status_time'):
                    run_polling_mode.last_status_time = current_time
                
                if current_time - run_polling_mode.last_status_time >= 5.0:
                    mute_current = "PRESSED" if read_button_state(MUTE_PIN) else "RELEASED"
                    reset_current = "PRESSED" if read_button_state(RESET_PIN) else "RELEASED"
                    print_info(f"Status: Mute={mute_current}, Reset={reset_current} | "
                             f"Mute presses: {mute_state.press_count}, Reset presses: {reset_state.press_count}")
                    run_polling_mode.last_status_time = current_time
            
            time.sleep(POLLING_INTERVAL)
    
    except KeyboardInterrupt:
        print_info("\n\nMonitoring stopped by user")
    except Exception as e:
        print_error(f"Error in polling mode: {e}")
        import traceback
        traceback.print_exc()

def run_interrupt_mode(mute_state: ButtonState, reset_state: ButtonState):
    """Run button monitoring in interrupt mode."""
    print_header("Button Test - Interrupt Mode")
    print_info("Monitoring buttons using GPIO interrupts")
    print_info("Press Ctrl+C to exit\n")
    
    if not GPIO_AVAILABLE:
        print_error("GPIO not available - cannot use interrupt mode")
        return
    
    try:
        # Remove any existing event detection first
        try:
            GPIO.remove_event_detect(MUTE_PIN)
        except:
            pass
        try:
            GPIO.remove_event_detect(RESET_PIN)
        except:
            pass
        
        # Reset callback state tracking
        mute_state.last_callback_time = 0
        mute_state.last_callback_state = None
        mute_state.last_edge_type = None
        reset_state.last_callback_time = 0
        reset_state.last_callback_state = None
        reset_state.last_edge_type = None
        
        # Initialize button state to current physical state to prevent false initial events
        # Set time to allow first legitimate event to pass through immediately
        init_time = time.time()
        mute_state.last_callback_state = read_button_state(MUTE_PIN)
        reset_state.last_callback_state = read_button_state(RESET_PIN)
        # Set to past time to ensure first state change is always processed
        mute_state.last_callback_time = init_time - (DEBOUNCE_TIME * 2)
        reset_state.last_callback_time = init_time - (DEBOUNCE_TIME * 2)
        
        # Setup interrupt callbacks with debouncing
        GPIO.add_event_detect(
            MUTE_PIN,
            GPIO.BOTH,  # Detect both rising and falling edges
            callback=lambda channel: button_callback(channel, "MUTE", mute_state),
            bouncetime=10  # 10ms hardware debounce (matches DEBOUNCE_TIME)
        )
        
        GPIO.add_event_detect(
            RESET_PIN,
            GPIO.BOTH,
            callback=lambda channel: button_callback(channel, "RESET", reset_state),
            bouncetime=10  # 10ms hardware debounce (matches DEBOUNCE_TIME)
        )
        
        print_success("Interrupt handlers registered")
        print_info("Waiting for button presses...\n")
        
        # Keep program running
        while True:
            time.sleep(1)
            # Show status every 10 seconds
            if not hasattr(run_interrupt_mode, 'last_status_time'):
                run_interrupt_mode.last_status_time = time.time()
            
            current_time = time.time()
            if current_time - run_interrupt_mode.last_status_time >= 10.0:
                print_info(f"Status: Mute presses: {mute_state.press_count}, "
                         f"Reset presses: {reset_state.press_count}")
                run_interrupt_mode.last_status_time = current_time
    
    except KeyboardInterrupt:
        print_info("\n\nMonitoring stopped by user")
    except Exception as e:
        print_error(f"Error in interrupt mode: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Remove event detection
        try:
            GPIO.remove_event_detect(MUTE_PIN)
            GPIO.remove_event_detect(RESET_PIN)
        except:
            pass

def run_interactive_test(mute_state: ButtonState, reset_state: ButtonState):
    """Run interactive test menu."""
    print_header("Button Test - Interactive Mode")
    print_info("Interactive button testing")
    print_info("Press buttons on the panel and see the results\n")
    
    try:
        while True:
            print("\n" + "=" * 70)
            print("Test Menu")
            print("=" * 70)
            print("1. Check current button states")
            print("2. Monitor buttons (polling mode, 30 seconds)")
            print("3. Monitor buttons (interrupt mode, 30 seconds)")
            print("4. Show statistics")
            print("5. Re-setup GPIO pins")
            print("0. Exit")
            print("=" * 70)
            
            try:
                choice = input("\nEnter your choice: ").strip()
            except (EOFError, KeyboardInterrupt):
                print_info("\nExiting...")
                break
            
            if choice == '0':
                print_info("Exiting test program.")
                break
            elif choice == '1':
                print_info("Checking current button states...")
                print_info(f"\nReading Mute button (GPIO {MUTE_PIN}):")
                mute_pressed = read_button_state(MUTE_PIN, verbose=True)
                print_info(f"  Result: {'PRESSED' if mute_pressed else 'RELEASED'}")
                
                print_info(f"\nReading Reset button (GPIO {RESET_PIN}):")
                reset_pressed = read_button_state(RESET_PIN, verbose=True)
                print_info(f"  Result: {'PRESSED' if reset_pressed else 'RELEASED'}")
                
                # Summary
                print_info(f"\nSummary:")
                print_info(f"  Mute button (GPIO {MUTE_PIN}): {'PRESSED' if mute_pressed else 'RELEASED'}")
                print_info(f"  Reset button (GPIO {RESET_PIN}): {'PRESSED' if reset_pressed else 'RELEASED'}")
                
                # Additional diagnostics
                if GPIO_AVAILABLE:
                    try:
                        # Try to verify pin configuration
                        print_info(f"\nPin Configuration Check:")
                        # Note: RPi.GPIO doesn't have a direct way to check pin mode,
                        # but we can try reading it multiple times to see if it's stable
                        mute_values = []
                        reset_values = []
                        for i in range(5):
                            mute_values.append(GPIO.input(MUTE_PIN))
                            reset_values.append(GPIO.input(RESET_PIN))
                            time.sleep(0.01)
                        
                        mute_stable = len(set(mute_values)) == 1
                        reset_stable = len(set(reset_values)) == 1
                        
                        print_info(f"  Mute pin {MUTE_PIN} stability: {'STABLE' if mute_stable else 'UNSTABLE'} (values: {mute_values})")
                        print_info(f"  Reset pin {RESET_PIN} stability: {'STABLE' if reset_stable else 'UNSTABLE'} (values: {reset_values})")
                        
                        if not reset_stable:
                            print_warning(f"  Reset pin {RESET_PIN} readings are unstable - check wiring/connection")
                    except Exception as e:
                        print_warning(f"  Could not perform pin diagnostics: {e}")
            elif choice == '2':
                print_info("Monitoring buttons for 30 seconds (polling mode)...")
                start_time = time.time()
                while time.time() - start_time < 30:
                    mute_event = detect_button_press(mute_state)
                    if mute_event == 'pressed':
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        print_success(f"[{timestamp}] MUTE PRESSED")
                    elif mute_event == 'released':
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        print_info(f"[{timestamp}] MUTE RELEASED")
                    
                    reset_event = detect_button_press(reset_state)
                    if reset_event == 'pressed':
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        print_success(f"[{timestamp}] RESET PRESSED")
                    elif reset_event == 'released':
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        print_info(f"[{timestamp}] RESET RELEASED")
                    
                    time.sleep(POLLING_INTERVAL)
                print_success("30-second monitoring completed!")
            elif choice == '3':
                if not GPIO_AVAILABLE:
                    print_error("GPIO not available - cannot use interrupt mode")
                    continue
                print_info("Monitoring buttons for 30 seconds (interrupt mode)...")
                # Remove any existing event detection first
                try:
                    GPIO.remove_event_detect(MUTE_PIN)
                except:
                    pass
                try:
                    GPIO.remove_event_detect(RESET_PIN)
                except:
                    pass
                # Reset callback state tracking
                mute_state.last_callback_time = 0
                mute_state.last_callback_state = None
                mute_state.last_edge_type = None
                reset_state.last_callback_time = 0
                reset_state.last_callback_state = None
                reset_state.last_edge_type = None
                
                # Initialize button state to current physical state to prevent false initial events
                # Set time to allow first legitimate event to pass through immediately
                init_time = time.time()
                mute_state.last_callback_state = read_button_state(MUTE_PIN)
                reset_state.last_callback_state = read_button_state(RESET_PIN)
                # Set to past time to ensure first state change is always processed
                mute_state.last_callback_time = init_time - (DEBOUNCE_TIME * 2)
                reset_state.last_callback_time = init_time - (DEBOUNCE_TIME * 2)
                
                # Setup new event detection
                GPIO.add_event_detect(
                    MUTE_PIN, GPIO.BOTH,
                    callback=lambda ch: button_callback(ch, "MUTE", mute_state),
                    bouncetime=10  # 10ms hardware debounce (matches DEBOUNCE_TIME)
                )
                GPIO.add_event_detect(
                    RESET_PIN, GPIO.BOTH,
                    callback=lambda ch: button_callback(ch, "RESET", reset_state),
                    bouncetime=10  # 10ms hardware debounce (matches DEBOUNCE_TIME)
                )
                print_success("Interrupt handlers registered - monitoring for 30 seconds...")
                time.sleep(30)
                GPIO.remove_event_detect(MUTE_PIN)
                GPIO.remove_event_detect(RESET_PIN)
                print_success("30-second monitoring completed!")
            elif choice == '4':
                print_header("Button Statistics")
                print_info(f"Mute button (GPIO {MUTE_PIN}):")
                print_info(f"  Total presses: {mute_state.press_count}")
                print_info(f"  Total releases: {mute_state.release_count}")
                print_info(f"Reset button (GPIO {RESET_PIN}):")
                print_info(f"  Total presses: {reset_state.press_count}")
                print_info(f"  Total releases: {reset_state.release_count}")
            elif choice == '5':
                print_info("Re-setting up GPIO pins...")
                if setup_gpio_inputs(MUTE_PIN, RESET_PIN):
                    print_success("GPIO pins re-configured successfully")
                    # Reset button states
                    mute_state.last_state = None
                    mute_state.pending_state = None
                    mute_state.pending_state_time = 0
                    mute_state.last_callback_time = 0
                    mute_state.last_callback_state = None
                    mute_state.last_edge_type = None
                    reset_state.last_state = None
                    reset_state.pending_state = None
                    reset_state.pending_state_time = 0
                    reset_state.last_callback_time = 0
                    reset_state.last_callback_state = None
                    reset_state.last_edge_type = None
                else:
                    print_error("Failed to re-setup GPIO pins")
            else:
                print_warning("Invalid choice. Please try again.")
    
    except KeyboardInterrupt:
        print_info("\n\nTest interrupted by user")
    except Exception as e:
        print_error(f"Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Test Mute and Reset buttons on STS Panel',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive test mode
  python3 test_mute_reset_buttons.py
  
  # Continuous monitoring (polling mode)
  python3 test_mute_reset_buttons.py --continuous --polling
  
  # Continuous monitoring (interrupt mode)
  python3 test_mute_reset_buttons.py --continuous --interrupt
        """
    )
    
    parser.add_argument(
        '--continuous', '-c',
        action='store_true',
        help='Run continuous monitoring (default: interactive mode)'
    )
    
    parser.add_argument(
        '--polling', '-p',
        action='store_true',
        help='Use polling mode (default)'
    )
    
    parser.add_argument(
        '--interrupt', '-i',
        action='store_true',
        help='Use interrupt mode (requires GPIO)'
    )
    
    parser.add_argument(
        '--debounce', '-d',
        type=float,
        default=DEBOUNCE_TIME,
        help=f'Debounce time in seconds (default: {DEBOUNCE_TIME})'
    )
    
    args = parser.parse_args()
    
    # Initialize button states
    mute_state = ButtonState(MUTE_PIN, "Mute")
    reset_state = ButtonState(RESET_PIN, "Reset")
    
    # Setup GPIO
    if not setup_gpio_inputs(MUTE_PIN, RESET_PIN):
        if not GPIO_AVAILABLE:
            print_warning("Running in simulation mode (no actual GPIO access)")
        else:
            print_error("Failed to setup GPIO. Exiting.")
            sys.exit(1)
    
    try:
        # Determine mode
        if args.continuous:
            if args.interrupt:
                run_interrupt_mode(mute_state, reset_state)
            else:
                run_polling_mode(mute_state, reset_state, continuous=True)
        else:
            if args.interrupt:
                print_warning("Interrupt mode requires --continuous flag")
                print_info("Falling back to interactive mode")
            run_interactive_test(mute_state, reset_state)
    
    finally:
        cleanup_gpio()
        print_header("Test Summary")
        print_info(f"Mute button: {mute_state.press_count} presses, {mute_state.release_count} releases")
        print_info(f"Reset button: {reset_state.press_count} presses, {reset_state.release_count} releases")

if __name__ == '__main__':
    main()

