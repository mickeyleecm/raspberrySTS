#!/usr/bin/env python3
"""
Test Mute and Reset buttons on STS Panel using RPi.GPIO library.
Event-driven approach (interrupt mode) with GPIO.BOTH edge detection.

Usage:
    python3 test_mute_reset_buttons_rpigpio.py              # Interactive mode
    python3 test_mute_reset_buttons_rpigpio.py --continuous # Continuous monitoring
"""

import sys
import time
import platform
import argparse
from datetime import datetime
from typing import Optional

# Check if running on Raspberry Pi
if platform.system() != 'Linux':
    print("WARNING: This script is designed for Raspberry Pi (Linux)")
    print("GPIO operations will be simulated.")
    GPIO_AVAILABLE = False
else:
    try:
        import RPi.GPIO as GPIO
        GPIO_AVAILABLE = True
    except ImportError:
        print("ERROR: RPi.GPIO not available.")
        print("Install with: pip3 install RPi.GPIO")
        print("Or: sudo apt-get install python3-rpi.gpio")
        GPIO_AVAILABLE = False

# Button configuration
MUTE_PIN = 19
RESET_PIN = 21
DEBOUNCE_TIME = 0.01  # 10ms debounce time (in seconds)

# Button state tracking
class ButtonStats:
    def __init__(self, name: str):
        self.name = name
        self.press_count = 0
        self.release_count = 0
        self.last_press_time = 0
        self.last_release_time = 0
        self.last_callback_time = 0
        self.last_callback_state = None
        self.last_edge_type = None

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

def read_button_state(pin: int) -> bool:
    """Read button state. Returns True if pressed (LOW), False if released (HIGH)."""
    if not GPIO_AVAILABLE:
        return False
    
    try:
        # With pull-up: LOW (0) = pressed, HIGH (1) = released
        state = GPIO.input(pin)
        is_pressed = state == GPIO.LOW
        return is_pressed
    except Exception as e:
        print_error(f"Error reading pin {pin}: {e}")
        return False

def button_callback(channel: int, button_name: str, button_state: ButtonStats):
    """Callback function for button interrupt with debouncing."""
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
        button_state.last_press_time = current_time_sec
        print_success(f"[{current_time_str}] {button_name} button PRESSED (GPIO {channel})")
        print_info(f"  Total presses: {button_state.press_count}")
    else:  # Button released (HIGH)
        button_state.release_count += 1
        button_state.last_release_time = current_time_sec
        print_info(f"[{current_time_str}] {button_name} button RELEASED (GPIO {channel})")
        print_info(f"  Total releases: {button_state.release_count}")

def run_continuous_monitoring(mute_stats: ButtonStats, reset_stats: ButtonStats):
    """Run continuous button monitoring using RPi.GPIO interrupt mode."""
    print_header("Button Test - Continuous Monitoring (RPi.GPIO Event-Driven)")
    print_info("Monitoring buttons using RPi.GPIO interrupt mode (GPIO.BOTH)")
    print_info("Press Ctrl+C to exit\n")
    
    if not GPIO_AVAILABLE:
        print_error("RPi.GPIO not available - cannot run")
        return
    
    try:
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup pins as inputs with pull-up resistors
        GPIO.setup(MUTE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(RESET_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
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
        mute_stats.last_callback_time = 0
        mute_stats.last_callback_state = None
        mute_stats.last_edge_type = None
        reset_stats.last_callback_time = 0
        reset_stats.last_callback_state = None
        reset_stats.last_edge_type = None
        
        # Initialize button state to current physical state to prevent false initial events
        init_time = time.time()
        mute_stats.last_callback_state = read_button_state(MUTE_PIN)
        reset_stats.last_callback_state = read_button_state(RESET_PIN)
        # Set to past time to ensure first state change is always processed
        mute_stats.last_callback_time = init_time - (DEBOUNCE_TIME * 2)
        reset_stats.last_callback_time = init_time - (DEBOUNCE_TIME * 2)
        
        # Setup interrupt callbacks with debouncing (GPIO.BOTH for event-driven approach)
        GPIO.add_event_detect(
            MUTE_PIN,
            GPIO.BOTH,  # Detect both rising and falling edges
            callback=lambda channel: button_callback(channel, "MUTE", mute_stats),
            bouncetime=int(DEBOUNCE_TIME * 1000)  # 10ms hardware debounce
        )
        
        GPIO.add_event_detect(
            RESET_PIN,
            GPIO.BOTH,
            callback=lambda channel: button_callback(channel, "RESET", reset_stats),
            bouncetime=int(DEBOUNCE_TIME * 1000)  # 10ms hardware debounce
        )
        
        print_success("Button handlers registered")
        print_info(f"Mute button: GPIO {MUTE_PIN} (pull-up, bounce_time={int(DEBOUNCE_TIME * 1000)}ms)")
        print_info(f"Reset button: GPIO {RESET_PIN} (pull-up, bounce_time={int(DEBOUNCE_TIME * 1000)}ms)")
        print_info("Waiting for button presses...\n")
        
        # Keep program running
        while True:
            time.sleep(1)
            # Show status every 10 seconds
            if not hasattr(run_continuous_monitoring, 'last_status_time'):
                run_continuous_monitoring.last_status_time = time.time()
            
            current_time = time.time()
            if current_time - run_continuous_monitoring.last_status_time >= 10.0:
                print_info(f"Status: Mute presses: {mute_stats.press_count}, "
                         f"Reset presses: {reset_stats.press_count}")
                run_continuous_monitoring.last_status_time = current_time
    
    except KeyboardInterrupt:
        print_info("\n\nMonitoring stopped by user")
    except Exception as e:
        print_error(f"Error in monitoring: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        try:
            if GPIO_AVAILABLE:
                GPIO.remove_event_detect(MUTE_PIN)
                GPIO.remove_event_detect(RESET_PIN)
                GPIO.cleanup()
        except:
            pass

def run_timed_monitoring(mute_stats: ButtonStats, reset_stats: ButtonStats, duration: int = 30):
    """Run button monitoring for a specific duration."""
    print_header(f"Button Test - Timed Monitoring ({duration} seconds)")
    print_info(f"Monitoring buttons for {duration} seconds using RPi.GPIO interrupt mode")
    print_info("Press Ctrl+C to exit early\n")
    
    if not GPIO_AVAILABLE:
        print_error("RPi.GPIO not available - cannot run")
        return
    
    try:
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup pins as inputs with pull-up resistors
        GPIO.setup(MUTE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(RESET_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
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
        mute_stats.last_callback_time = 0
        mute_stats.last_callback_state = None
        mute_stats.last_edge_type = None
        reset_stats.last_callback_time = 0
        reset_stats.last_callback_state = None
        reset_stats.last_edge_type = None
        
        # Initialize button state to current physical state
        init_time = time.time()
        mute_stats.last_callback_state = read_button_state(MUTE_PIN)
        reset_stats.last_callback_state = read_button_state(RESET_PIN)
        mute_stats.last_callback_time = init_time - (DEBOUNCE_TIME * 2)
        reset_stats.last_callback_time = init_time - (DEBOUNCE_TIME * 2)
        
        # Setup interrupt callbacks with debouncing
        GPIO.add_event_detect(
            MUTE_PIN,
            GPIO.BOTH,
            callback=lambda channel: button_callback(channel, "MUTE", mute_stats),
            bouncetime=int(DEBOUNCE_TIME * 1000)
        )
        
        GPIO.add_event_detect(
            RESET_PIN,
            GPIO.BOTH,
            callback=lambda channel: button_callback(channel, "RESET", reset_stats),
            bouncetime=int(DEBOUNCE_TIME * 1000)
        )
        
        print_success("Button handlers registered - monitoring for {} seconds...".format(duration))
        
        # Wait for specified duration
        time.sleep(duration)
        
        print_success(f"{duration}-second monitoring completed!")
    
    except KeyboardInterrupt:
        print_info("\n\nMonitoring stopped by user")
    except Exception as e:
        print_error(f"Error in monitoring: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        try:
            if GPIO_AVAILABLE:
                GPIO.remove_event_detect(MUTE_PIN)
                GPIO.remove_event_detect(RESET_PIN)
                GPIO.cleanup()
        except:
            pass

def run_interactive_test(mute_stats: ButtonStats, reset_stats: ButtonStats):
    """Run interactive test menu."""
    print_header("Button Test - Interactive Mode (RPi.GPIO Event-Driven)")
    print_info("Interactive button testing using RPi.GPIO interrupt mode")
    print_info("Press buttons on the panel and see the results\n")
    
    try:
        while True:
            print("\n" + "=" * 70)
            print("Test Menu")
            print("=" * 70)
            print("1. Check current button states")
            print("2. Monitor buttons (30 seconds)")
            print("3. Monitor buttons (60 seconds)")
            print("4. Monitor buttons (custom duration)")
            print("5. Show statistics")
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
                if not GPIO_AVAILABLE:
                    print_error("RPi.GPIO not available - cannot check states")
                    continue
                
                try:
                    GPIO.setmode(GPIO.BCM)
                    GPIO.setwarnings(False)
                    GPIO.setup(MUTE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                    GPIO.setup(RESET_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                    
                    mute_state = read_button_state(MUTE_PIN)
                    reset_state = read_button_state(RESET_PIN)
                    
                    mute_str = "PRESSED" if mute_state else "RELEASED"
                    reset_str = "PRESSED" if reset_state else "RELEASED"
                    
                    print_info(f"\nMute button (GPIO {MUTE_PIN}): {mute_str}")
                    print_info(f"Reset button (GPIO {RESET_PIN}): {reset_str}")
                    
                    GPIO.cleanup()
                except Exception as e:
                    print_error(f"Error checking states: {e}")
            elif choice == '2':
                run_timed_monitoring(mute_stats, reset_stats, duration=30)
            elif choice == '3':
                run_timed_monitoring(mute_stats, reset_stats, duration=60)
            elif choice == '4':
                try:
                    duration = int(input("Enter duration in seconds: "))
                    if duration > 0:
                        run_timed_monitoring(mute_stats, reset_stats, duration=duration)
                    else:
                        print_warning("Duration must be positive")
                except ValueError:
                    print_warning("Invalid duration. Please enter a number.")
            elif choice == '5':
                print_header("Button Statistics")
                print_info(f"Mute button (GPIO {MUTE_PIN}):")
                print_info(f"  Total presses: {mute_stats.press_count}")
                print_info(f"  Total releases: {mute_stats.release_count}")
                if mute_stats.last_press_time > 0:
                    last_press = datetime.fromtimestamp(mute_stats.last_press_time).strftime("%Y-%m-%d %H:%M:%S")
                    print_info(f"  Last press: {last_press}")
                if mute_stats.last_release_time > 0:
                    last_release = datetime.fromtimestamp(mute_stats.last_release_time).strftime("%Y-%m-%d %H:%M:%S")
                    print_info(f"  Last release: {last_release}")
                
                print_info(f"\nReset button (GPIO {RESET_PIN}):")
                print_info(f"  Total presses: {reset_stats.press_count}")
                print_info(f"  Total releases: {reset_stats.release_count}")
                if reset_stats.last_press_time > 0:
                    last_press = datetime.fromtimestamp(reset_stats.last_press_time).strftime("%Y-%m-%d %H:%M:%S")
                    print_info(f"  Last press: {last_press}")
                if reset_stats.last_release_time > 0:
                    last_release = datetime.fromtimestamp(reset_stats.last_release_time).strftime("%Y-%m-%d %H:%M:%S")
                    print_info(f"  Last release: {last_release}")
            else:
                print_warning("Invalid choice. Please try again.")
    
    except KeyboardInterrupt:
        print_info("\n\nTest interrupted by user")
    except Exception as e:
        print_error(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup GPIO on exit
        try:
            if GPIO_AVAILABLE:
                GPIO.cleanup()
        except:
            pass

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Test Mute and Reset buttons on STS Panel using RPi.GPIO (Event-Driven)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive test mode
  python3 test_mute_reset_buttons_rpigpio.py
  
  # Continuous monitoring
  python3 test_mute_reset_buttons_rpigpio.py --continuous
        """
    )
    
    parser.add_argument(
        '--continuous', '-c',
        action='store_true',
        help='Run continuous monitoring (default: interactive mode)'
    )
    
    parser.add_argument(
        '--bounce-time', '-b',
        type=float,
        default=0.01,
        help='Button bounce time in seconds (default: 0.01 = 10ms)'
    )
    
    args = parser.parse_args()
    
    # Update debounce time if specified
    global DEBOUNCE_TIME
    if args.bounce_time > 0:
        DEBOUNCE_TIME = args.bounce_time
    
    # Initialize button statistics
    mute_stats = ButtonStats("Mute")
    reset_stats = ButtonStats("Reset")
    
    if not GPIO_AVAILABLE:
        if platform.system() == 'Linux':
            print_error("RPi.GPIO not available. Please install it:")
            print_error("  pip3 install RPi.GPIO")
            print_error("  or: sudo apt-get install python3-rpi.gpio")
            sys.exit(1)
        else:
            print_warning("Running in simulation mode (not on Raspberry Pi)")
    
    try:
        # Determine mode
        if args.continuous:
            run_continuous_monitoring(mute_stats, reset_stats)
        else:
            run_interactive_test(mute_stats, reset_stats)
    
    finally:
        print_header("Test Summary")
        print_info(f"Mute button: {mute_stats.press_count} presses, {mute_stats.release_count} releases")
        print_info(f"Reset button: {reset_stats.press_count} presses, {reset_stats.release_count} releases")

if __name__ == '__main__':
    main()
