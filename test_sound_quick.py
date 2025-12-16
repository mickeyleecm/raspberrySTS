#!/usr/bin/env python3
"""
Quick Sound Test for Raspberry Pi
Simple script to quickly test if the speaker is working.
"""

import sys
import subprocess
import time
import platform


def check_command(command: str) -> bool:
    """Check if a command is available."""
    try:
        result = subprocess.run(
            ['which', command],
            capture_output=True,
            timeout=1
        )
        return result.returncode == 0
    except:
        return False


def play_beep_simple(frequency: int = 1000, duration: float = 0.5):
    """Play a simple beep."""
    if check_command('beep'):
        # Use beep command
        duration_ms = int(duration * 1000)
        subprocess.run(
            ['beep', '-f', str(frequency), '-l', str(duration_ms)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    elif check_command('speaker-test'):
        # Use speaker-test
        cmd = [
            'speaker-test', '-t', 'sine', '-f', str(frequency),
            '-l', '1', '-s', '1', '-c', '1'
        ]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(duration)
        process.terminate()
        process.wait(timeout=1)
        return True
    else:
        print("ERROR: No audio method available.")
        print("Install 'beep' or ensure 'speaker-test' is available.")
        return False


def main():
    """Quick sound test."""
    print("=" * 50)
    print("Raspberry Pi Quick Sound Test")
    print("=" * 50)
    print()
    print("⚠️  WARNING: This script uses 'speaker-test' which can cause")
    print("   network disconnection on Raspberry Pi due to GPIO conflicts.")
    print()
    print("   For GPIO-connected speakers, use instead:")
    print("     python3 test_sound_quick_safe.py")
    print()
    print("   Continue anyway? (y/n): ", end='', flush=True)
    try:
        response = input().strip().lower()
        if response != 'y':
            print("Cancelled. Use test_sound_quick_safe.py for GPIO speakers.")
            return
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return
    print()
    
    # Check platform
    if platform.system() != 'Linux':
        print("WARNING: This script is designed for Linux/Raspberry Pi")
        print()
    
    # Check available methods
    print("Checking audio methods...")
    if check_command('beep'):
        print("  ✓ beep command available")
    if check_command('speaker-test'):
        print("  ✓ speaker-test available")
    if check_command('aplay'):
        print("  ✓ aplay available")
    
    print()
    print("Playing test beeps...")
    print("  Test 1: Single beep (1000 Hz, 0.5s)")
    play_beep_simple(1000, 0.5)
    time.sleep(0.5)
    
    print("  Test 2: Critical alarm (3 beeps)")
    for _ in range(3):
        play_beep_simple(1000, 0.5)
        time.sleep(0.2)
    time.sleep(0.5)
    
    print("  Test 3: Warning alarm (2 beeps)")
    for _ in range(2):
        play_beep_simple(1000, 0.5)
        time.sleep(0.2)
    
    print()
    print("=" * 50)
    print("Sound test completed!")
    print("=" * 50)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(0)

