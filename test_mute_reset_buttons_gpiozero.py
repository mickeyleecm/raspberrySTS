#!/usr/bin/env python3
"""
Test Mute and Reset buttons on STS Panel using gpiozero library.
Event-driven approach with built-in debouncing.

Usage:
    python3 test_mute_reset_buttons_gpiozero.py              # Interactive mode
    python3 test_mute_reset_buttons_gpiozero.py --continuous # Continuous monitoring
    
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
    GPIOZERO_AVAILABLE = False
else:
    try:
        from gpiozero import Button
        GPIOZERO_AVAILABLE = True
    except ImportError:
        print("ERROR: gpiozero not available.")
        print("Install with: pip3 install gpiozero")
        print("Or: sudo apt-get install python3-gpiozero")
        GPIOZERO_AVAILABLE = False

# Button configuration
MUTE_PIN = 19
RESET_PIN = 21

# Button state tracking
class ButtonStats:
    def __init__(self, name: str):
        self.name = name
        self.press_count = 0
        self.release_count = 0
        self.last_press_time = 0
        self.last_release_time = 0

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

def create_button_handlers(mute_stats: ButtonStats, reset_stats: ButtonStats):
    """Create event handlers for buttons."""
    
    def mute_pressed():
        """Handler for MUTE button press."""
        mute_stats.press_count += 1
        mute_stats.last_press_time = time.time()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print_success(f"[{timestamp}] MUTE button PRESSED (GPIO {MUTE_PIN})")
        print_info(f"  Total presses: {mute_stats.press_count}")
    
    def mute_released():
        """Handler for MUTE button release."""
        mute_stats.release_count += 1
        mute_stats.last_release_time = time.time()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print_info(f"[{timestamp}] MUTE button RELEASED (GPIO {MUTE_PIN})")
        print_info(f"  Total releases: {mute_stats.release_count}")
    
    def reset_pressed():
        """Handler for RESET button press."""
        reset_stats.press_count += 1
        reset_stats.last_press_time = time.time()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print_success(f"[{timestamp}] RESET button PRESSED (GPIO {RESET_PIN})")
        print_info(f"  Total presses: {reset_stats.press_count}")
    
    def reset_released():
        """Handler for RESET button release."""
        reset_stats.release_count += 1
        reset_stats.last_release_time = time.time()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print_info(f"[{timestamp}] RESET button RELEASED (GPIO {RESET_PIN})")
        print_info(f"  Total releases: {reset_stats.release_count}")
    
    return mute_pressed, mute_released, reset_pressed, reset_released

def run_continuous_monitoring(mute_stats: ButtonStats, reset_stats: ButtonStats):
    """Run continuous button monitoring."""
    print_header("Button Test - Continuous Monitoring (gpiozero)")
    print_info("Monitoring buttons using gpiozero event-driven approach")
    print_info("Press Ctrl+C to exit\n")
    
    if not GPIOZERO_AVAILABLE:
        print_error("gpiozero not available - cannot run")
        return
    
    try:
        # Create button objects with pull-up resistors
        # gpiozero Button class uses pull_up=True by default
        # When button is pressed, pin goes LOW (0)
        # When button is released, pin goes HIGH (1) due to pull-up
        mute_button = Button(MUTE_PIN, pull_up=True, bounce_time=0.01)  # 10ms bounce time
        reset_button = Button(RESET_PIN, pull_up=True, bounce_time=0.01)  # 10ms bounce time
        
        # Get event handlers
        mute_pressed, mute_released, reset_pressed, reset_released = create_button_handlers(
            mute_stats, reset_stats
        )
        
        # Attach event handlers (event-driven)
        mute_button.when_pressed = mute_pressed
        mute_button.when_released = mute_released
        reset_button.when_pressed = reset_pressed
        reset_button.when_released = reset_released
        
        print_success("Button handlers registered")
        print_info(f"Mute button: GPIO {MUTE_PIN} (pull-up, bounce_time=10ms)")
        print_info(f"Reset button: GPIO {RESET_PIN} (pull-up, bounce_time=10ms)")
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
            if 'mute_button' in locals():
                mute_button.close()
            if 'reset_button' in locals():
                reset_button.close()
        except:
            pass

def run_timed_monitoring(mute_stats: ButtonStats, reset_stats: ButtonStats, duration: int = 30):
    """Run button monitoring for a specific duration."""
    print_header(f"Button Test - Timed Monitoring ({duration} seconds)")
    print_info(f"Monitoring buttons for {duration} seconds using gpiozero")
    print_info("Press Ctrl+C to exit early\n")
    
    if not GPIOZERO_AVAILABLE:
        print_error("gpiozero not available - cannot run")
        return
    
    try:
        # Create button objects with pull-up resistors
        mute_button = Button(MUTE_PIN, pull_up=True, bounce_time=0.01)  # 10ms bounce time
        reset_button = Button(RESET_PIN, pull_up=True, bounce_time=0.01)  # 10ms bounce time
        
        # Get event handlers
        mute_pressed, mute_released, reset_pressed, reset_released = create_button_handlers(
            mute_stats, reset_stats
        )
        
        # Attach event handlers (event-driven)
        mute_button.when_pressed = mute_pressed
        mute_button.when_released = mute_released
        reset_button.when_pressed = reset_pressed
        reset_button.when_released = reset_released
        
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
            if 'mute_button' in locals():
                mute_button.close()
            if 'reset_button' in locals():
                reset_button.close()
        except:
            pass

def run_interactive_test(mute_stats: ButtonStats, reset_stats: ButtonStats):
    """Run interactive test menu."""
    print_header("Button Test - Interactive Mode (gpiozero)")
    print_info("Interactive button testing using gpiozero event-driven approach")
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
                if not GPIOZERO_AVAILABLE:
                    print_error("gpiozero not available - cannot check states")
                    continue
                
                try:
                    mute_button = Button(MUTE_PIN, pull_up=True)
                    reset_button = Button(RESET_PIN, pull_up=True)
                    
                    mute_state = "PRESSED" if mute_button.is_pressed else "RELEASED"
                    reset_state = "PRESSED" if reset_button.is_pressed else "RELEASED"
                    
                    print_info(f"\nMute button (GPIO {MUTE_PIN}): {mute_state}")
                    print_info(f"Reset button (GPIO {RESET_PIN}): {reset_state}")
                    
                    mute_button.close()
                    reset_button.close()
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

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Test Mute and Reset buttons on STS Panel using gpiozero',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive test mode
  python3 test_mute_reset_buttons_gpiozero.py
  
  # Continuous monitoring
  python3 test_mute_reset_buttons_gpiozero.py --continuous
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
    
    # Initialize button statistics
    mute_stats = ButtonStats("Mute")
    reset_stats = ButtonStats("Reset")
    
    if not GPIOZERO_AVAILABLE:
        if platform.system() == 'Linux':
            print_error("gpiozero not available. Please install it:")
            print_error("  pip3 install gpiozero")
            print_error("  or: sudo apt-get install python3-gpiozero")
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
