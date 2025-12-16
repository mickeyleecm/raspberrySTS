#!/usr/bin/env python3
"""
Raspberry Pi Sound/Speaker Test Program
Tests the speaker/audio system on Raspberry Pi with various beep patterns and frequencies.
"""

import sys
import time
import subprocess
import platform
from typing import Optional

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text:^60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}\n")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.GREEN}[INFO]{Colors.RESET} {text}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}[WARNING]{Colors.RESET} {text}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {text}")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} {text}")


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


def detect_raspberry_pi() -> bool:
    """Detect if running on Raspberry Pi."""
    if platform.system() == 'Windows':
        return False
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
            return 'Raspberry Pi' in cpuinfo or 'BCM' in cpuinfo
    except:
        return False


def detect_audio_players() -> dict:
    """Detect available audio players."""
    players = {}
    
    if check_command('aplay'):
        players['aplay'] = 'ALSA audio player (most common on Raspberry Pi)'
    if check_command('paplay'):
        players['paplay'] = 'PulseAudio player'
    if check_command('omxplayer'):
        players['omxplayer'] = 'OMX player (older Raspberry Pi models)'
    if check_command('speaker-test'):
        players['speaker-test'] = 'ALSA speaker test utility'
    if check_command('beep'):
        players['beep'] = 'Beep utility (requires beep package)'
    
    return players


def play_beep_with_beep(frequency: int, duration_ms: int, count: int = 1) -> bool:
    """Play beep using the 'beep' command."""
    try:
        cmd = ['beep', '-f', str(frequency), '-l', str(duration_ms)]
        for _ in range(count - 1):
            cmd.extend(['-n', '-f', str(frequency), '-l', str(duration_ms)])
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        return True
    except Exception as e:
        print_error(f"Failed to play beep with 'beep' command: {e}")
        return False


def play_beep_with_speaker_test(frequency: int, duration: float, count: int = 1) -> bool:
    """Play beep using speaker-test."""
    try:
        for i in range(count):
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
            if i < count - 1:
                time.sleep(0.2)  # Small pause between beeps
        return True
    except Exception as e:
        print_error(f"Failed to play beep with speaker-test: {e}")
        return False


def play_beep_with_aplay(frequency: int, duration: float, count: int = 1) -> bool:
    """Play beep using aplay (generate sine wave)."""
    try:
        import wave
        import struct
        import math
        import tempfile
        
        sample_rate = 44100
        num_samples = int(sample_rate * duration)
        
        for beep_num in range(count):
            # Generate sine wave
            samples = []
            for i in range(num_samples):
                t = float(i) / sample_rate
                wave_value = int(32767.0 * math.sin(2 * math.pi * frequency * t))
                samples.append(struct.pack('<h', wave_value))
            
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                tmp_path = tmp_file.name
                
                # Write WAV header
                with wave.open(tmp_path, 'wb') as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(b''.join(samples))
                
                # Play the WAV file
                subprocess.run(
                    ['aplay', '-q', tmp_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=10
                )
                
                # Clean up
                import os
                os.unlink(tmp_path)
            
            if beep_num < count - 1:
                time.sleep(0.2)  # Small pause between beeps
        
        return True
    except ImportError:
        print_warning("wave module not available, cannot use aplay method")
        return False
    except Exception as e:
        print_error(f"Failed to play beep with aplay: {e}")
        return False


def play_beep(frequency: int = 1000, duration: float = 0.5, count: int = 1, method: Optional[str] = None) -> bool:
    """
    Play a beep sound.
    
    Args:
        frequency: Frequency in Hz (default: 1000)
        duration: Duration in seconds (default: 0.5)
        count: Number of beeps (default: 1)
        method: Preferred method ('beep', 'speaker-test', 'aplay', or None for auto)
    """
    duration_ms = int(duration * 1000)
    
    # Try preferred method first
    if method == 'beep' and check_command('beep'):
        return play_beep_with_beep(frequency, duration_ms, count)
    elif method == 'speaker-test' and check_command('speaker-test'):
        return play_beep_with_speaker_test(frequency, duration, count)
    elif method == 'aplay' and check_command('aplay'):
        return play_beep_with_aplay(frequency, duration, count)
    
    # Auto-detect method
    if check_command('beep'):
        return play_beep_with_beep(frequency, duration_ms, count)
    elif check_command('speaker-test'):
        return play_beep_with_speaker_test(frequency, duration, count)
    elif check_command('aplay'):
        return play_beep_with_aplay(frequency, duration, count)
    else:
        print_error("No audio method available. Install 'beep', 'speaker-test', or ensure 'aplay' is available.")
        return False


def test_single_beep():
    """Test 1: Single beep."""
    print_header("Test 1: Single Beep")
    print_info("Playing a single beep at 1000 Hz for 0.5 seconds...")
    if play_beep(frequency=1000, duration=0.5, count=1):
        print_success("Beep played successfully!")
    else:
        print_error("Failed to play beep")


def test_frequency_range():
    """Test 2: Frequency range test."""
    print_header("Test 2: Frequency Range Test")
    print_info("Playing beeps at different frequencies...")
    frequencies = [440, 500, 1000, 1500, 2000, 2500]
    
    for freq in frequencies:
        print_info(f"Playing {freq} Hz...")
        if play_beep(frequency=freq, duration=0.3, count=1):
            print_success(f"  ✓ {freq} Hz")
        else:
            print_error(f"  ✗ {freq} Hz")
        time.sleep(0.5)


def test_critical_alarm():
    """Test 3: Critical alarm pattern (3 beeps)."""
    print_header("Test 3: Critical Alarm Pattern")
    print_info("Playing critical alarm pattern (3 beeps)...")
    if play_beep(frequency=1000, duration=0.5, count=3):
        print_success("Critical alarm pattern played successfully!")
    else:
        print_error("Failed to play critical alarm pattern")


def test_warning_alarm():
    """Test 4: Warning alarm pattern (2 beeps)."""
    print_header("Test 4: Warning Alarm Pattern")
    print_info("Playing warning alarm pattern (2 beeps)...")
    if play_beep(frequency=1000, duration=0.5, count=2):
        print_success("Warning alarm pattern played successfully!")
    else:
        print_error("Failed to play warning alarm pattern")


def test_info_alarm():
    """Test 5: Info alarm pattern (1 beep)."""
    print_header("Test 5: Info Alarm Pattern")
    print_info("Playing info alarm pattern (1 beep)...")
    if play_beep(frequency=1000, duration=0.5, count=1):
        print_success("Info alarm pattern played successfully!")
    else:
        print_error("Failed to play info alarm pattern")


def test_custom_beep():
    """Test 6: Custom beep parameters."""
    print_header("Test 6: Custom Beep Parameters")
    try:
        print("Enter custom beep parameters:")
        frequency = int(input("  Frequency (Hz, e.g., 1000): ") or "1000")
        duration = float(input("  Duration (seconds, e.g., 0.5): ") or "0.5")
        count = int(input("  Count (number of beeps, e.g., 1): ") or "1")
        
        print_info(f"Playing {count} beep(s) at {frequency} Hz for {duration} seconds...")
        if play_beep(frequency=frequency, duration=duration, count=count):
            print_success("Custom beep played successfully!")
        else:
            print_error("Failed to play custom beep")
    except ValueError:
        print_error("Invalid input. Please enter numbers.")
    except KeyboardInterrupt:
        print_warning("\nTest cancelled by user")


def test_musical_scale():
    """Test 7: Musical scale test."""
    print_header("Test 7: Musical Scale Test")
    print_info("Playing a musical scale (C major)...")
    
    # C major scale frequencies
    notes = {
        'C': 261.63,
        'D': 293.66,
        'E': 329.63,
        'F': 349.23,
        'G': 392.00,
        'A': 440.00,
        'B': 493.88,
        'C2': 523.25
    }
    
    for note, freq in notes.items():
        print_info(f"Playing note {note} ({freq:.2f} Hz)...")
        play_beep(frequency=int(freq), duration=0.3, count=1)
        time.sleep(0.1)


def test_sos_pattern():
    """Test 8: SOS pattern (3 short, 3 long, 3 short)."""
    print_header("Test 8: SOS Pattern")
    print_info("Playing SOS pattern (3 short, 3 long, 3 short beeps)...")
    
    # 3 short beeps
    for _ in range(3):
        play_beep(frequency=1000, duration=0.2, count=1)
        time.sleep(0.1)
    
    time.sleep(0.3)
    
    # 3 long beeps
    for _ in range(3):
        play_beep(frequency=1000, duration=0.6, count=1)
        time.sleep(0.1)
    
    time.sleep(0.3)
    
    # 3 short beeps
    for _ in range(3):
        play_beep(frequency=1000, duration=0.2, count=1)
        time.sleep(0.1)
    
    print_success("SOS pattern played successfully!")


def show_system_info():
    """Show system and audio information."""
    print_header("System Information")
    
    print_info(f"Platform: {platform.system()} {platform.release()}")
    print_info(f"Python version: {sys.version.split()[0]}")
    
    is_rpi = detect_raspberry_pi()
    if is_rpi:
        print_success("Running on Raspberry Pi")
    else:
        print_warning("Not detected as Raspberry Pi (may still work)")
    
    print("\nAvailable audio players:")
    players = detect_audio_players()
    if players:
        for player, description in players.items():
            print_success(f"  ✓ {player}: {description}")
    else:
        print_error("  ✗ No audio players detected!")
        print_warning("  Install one of: beep, speaker-test, or ensure aplay is available")
    
    # Check audio devices
    if check_command('aplay'):
        print("\nAudio devices (aplay -l):")
        try:
            result = subprocess.run(
                ['aplay', '-l'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        print(f"  {line}")
            else:
                print_warning("Could not list audio devices")
        except Exception as e:
            print_warning(f"Could not check audio devices: {e}")


def main_menu():
    """Display main menu and handle user input."""
    while True:
        print_header("Raspberry Pi Sound/Speaker Test Program")
        print("Select a test to run:")
        print(f"  {Colors.CYAN}1{Colors.RESET}. Single Beep Test")
        print(f"  {Colors.CYAN}2{Colors.RESET}. Frequency Range Test")
        print(f"  {Colors.CYAN}3{Colors.RESET}. Critical Alarm Pattern (3 beeps)")
        print(f"  {Colors.CYAN}4{Colors.RESET}. Warning Alarm Pattern (2 beeps)")
        print(f"  {Colors.CYAN}5{Colors.RESET}. Info Alarm Pattern (1 beep)")
        print(f"  {Colors.CYAN}6{Colors.RESET}. Custom Beep Parameters")
        print(f"  {Colors.CYAN}7{Colors.RESET}. Musical Scale Test")
        print(f"  {Colors.CYAN}8{Colors.RESET}. SOS Pattern")
        print(f"  {Colors.CYAN}9{Colors.RESET}. System Information")
        print(f"  {Colors.CYAN}0{Colors.RESET}. Exit")
        
        try:
            choice = input(f"\n{Colors.BOLD}Enter your choice (0-9): {Colors.RESET}").strip()
            
            if choice == '0':
                print_info("Exiting...")
                break
            elif choice == '1':
                test_single_beep()
            elif choice == '2':
                test_frequency_range()
            elif choice == '3':
                test_critical_alarm()
            elif choice == '4':
                test_warning_alarm()
            elif choice == '5':
                test_info_alarm()
            elif choice == '6':
                test_custom_beep()
            elif choice == '7':
                test_musical_scale()
            elif choice == '8':
                test_sos_pattern()
            elif choice == '9':
                show_system_info()
            else:
                print_error("Invalid choice. Please enter a number between 0-9.")
            
            if choice != '0':
                input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
        
        except KeyboardInterrupt:
            print_warning("\n\nExiting...")
            break
        except Exception as e:
            print_error(f"An error occurred: {e}")


def main():
    """Main entry point."""
    # Check if running on Linux (Raspberry Pi)
    if platform.system() != 'Linux':
        print_warning("This program is designed for Linux/Raspberry Pi")
        print_warning("Some features may not work on other platforms")
        response = input("Continue anyway? (y/n): ").strip().lower()
        if response != 'y':
            sys.exit(0)
    
    # Show system info first
    show_system_info()
    input(f"\n{Colors.CYAN}Press Enter to continue to main menu...{Colors.RESET}")
    
    # Run main menu
    main_menu()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print_warning("\n\nProgram interrupted by user")
        sys.exit(0)

