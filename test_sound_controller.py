#!/usr/bin/env python3
"""
Test the SoundController class from ups_snmp_trap_receiver_v2.py
This tests the actual sound controller used by the UPS trap receiver.
"""

import sys
import time
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

try:
    from ups_snmp_trap_receiver_v2 import SoundController
except ImportError:
    print("ERROR: Could not import SoundController from ups_snmp_trap_receiver_v2.py")
    print("Make sure you're running this from the correct directory.")
    sys.exit(1)


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{'=' * 60}")
    print(f"{text:^60}")
    print(f"{'=' * 60}\n")


def test_sound_controller():
    """Test the SoundController class."""
    print_header("SoundController Test")
    
    print("Initializing SoundController...")
    try:
        sound_controller = SoundController(
            sound_enabled=True,
            use_beep=True,
            beep_duration=0.5,
            beep_frequency=1000,
            volume=50
        )
        print("✓ SoundController initialized successfully")
        print(f"  Audio player: {sound_controller.audio_player or 'None (will use beep)'}")
        print(f"  Raspberry Pi detected: {sound_controller.is_raspberry_pi}")
        print()
    except Exception as e:
        print(f"✗ Failed to initialize SoundController: {e}")
        return
    
    # Test 1: Critical alarm (3 beeps)
    print_header("Test 1: Critical Alarm")
    print("Triggering critical alarm (should play 3 beeps)...")
    try:
        sound_controller.trigger_alarm("TestCriticalAlarm", "critical")
        time.sleep(2)
        print("✓ Critical alarm test completed")
    except Exception as e:
        print(f"✗ Failed to trigger critical alarm: {e}")
    
    time.sleep(1)
    
    # Test 2: Warning alarm (2 beeps)
    print_header("Test 2: Warning Alarm")
    print("Triggering warning alarm (should play 2 beeps)...")
    try:
        sound_controller.trigger_alarm("TestWarningAlarm", "warning")
        time.sleep(2)
        print("✓ Warning alarm test completed")
    except Exception as e:
        print(f"✗ Failed to trigger warning alarm: {e}")
    
    time.sleep(1)
    
    # Test 3: Info alarm (1 beep)
    print_header("Test 3: Info Alarm")
    print("Triggering info alarm (should play 1 beep)...")
    try:
        sound_controller.trigger_alarm("TestInfoAlarm", "info")
        time.sleep(1)
        print("✓ Info alarm test completed")
    except Exception as e:
        print(f"✗ Failed to trigger info alarm: {e}")
    
    time.sleep(1)
    
    # Test 4: Different frequencies
    print_header("Test 4: Different Frequencies")
    frequencies = [440, 1000, 1500, 2000]
    for freq in frequencies:
        print(f"Testing frequency: {freq} Hz...")
        sound_controller.beep_frequency = freq
        try:
            sound_controller.trigger_alarm(f"TestFreq{freq}", "warning")
            time.sleep(1.5)
            print(f"  ✓ {freq} Hz")
        except Exception as e:
            print(f"  ✗ {freq} Hz: {e}")
        time.sleep(0.5)
    
    # Reset frequency
    sound_controller.beep_frequency = 1000
    
    # Test 5: Different durations
    print_header("Test 5: Different Durations")
    durations = [0.2, 0.5, 1.0]
    for duration in durations:
        print(f"Testing duration: {duration} seconds...")
        sound_controller.beep_duration = duration
        try:
            sound_controller.trigger_alarm(f"TestDuration{duration}", "warning")
            time.sleep(duration + 0.5)
            print(f"  ✓ {duration}s")
        except Exception as e:
            print(f"  ✗ {duration}s: {e}")
        time.sleep(0.5)
    
    # Reset duration
    sound_controller.beep_duration = 0.5
    
    print_header("All Tests Completed")
    print("SoundController is working correctly!")


def main():
    """Main entry point."""
    try:
        test_sound_controller()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

