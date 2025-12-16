# Raspberry Pi Sound/Speaker Test Programs

This directory contains test programs to verify that the speaker/audio system on your Raspberry Pi is working correctly.

## Available Test Programs

### 1. `test_raspberry_sound.py` - Comprehensive Test Suite
A full-featured menu-driven test program with multiple test options.

**Features:**
- Single beep test
- Frequency range test (440 Hz to 2500 Hz)
- Critical alarm pattern (3 beeps)
- Warning alarm pattern (2 beeps)
- Info alarm pattern (1 beep)
- Custom beep parameters
- Musical scale test
- SOS pattern test
- System information display

**Usage:**
```bash
python3 test_raspberry_sound.py
```

Then select a test option from the menu (1-9).

### 2. `test_sound_quick.py` - Quick Test
A simple script that runs a quick sound test without menus.

**Usage:**
```bash
python3 test_sound_quick.py
```

This will automatically play:
- A single beep
- Critical alarm pattern (3 beeps)
- Warning alarm pattern (2 beeps)

### 3. `test_sound_controller.py` - SoundController Class Test
Tests the actual `SoundController` class used by the UPS trap receiver.

**Usage:**
```bash
python3 test_sound_controller.py
```

This tests:
- Critical, warning, and info alarm patterns
- Different frequencies
- Different durations
- Integration with the actual SoundController class

## Prerequisites

### Required Audio Tools

The test programs will try to use one of these audio tools (in order of preference):

1. **beep** - Simple beep utility (recommended)
   ```bash
   sudo apt-get install beep
   ```

2. **speaker-test** - ALSA speaker test utility (usually pre-installed)
   ```bash
   # Usually already installed, but if not:
   sudo apt-get install alsa-utils
   ```

3. **aplay** - ALSA audio player (usually pre-installed)
   ```bash
   # Usually already installed, but if not:
   sudo apt-get install alsa-utils
   ```

### Installing beep (Recommended)

The `beep` utility is the most reliable for simple beep sounds:

```bash
sudo apt-get update
sudo apt-get install beep
```

**Note:** On some systems, you may need to load the `pcspkr` module:
```bash
sudo modprobe pcspkr
```

To make it permanent, add to `/etc/modules`:
```bash
echo "pcspkr" | sudo tee -a /etc/modules
```

## Audio Configuration

### Check Audio Devices

To see available audio devices:
```bash
aplay -l
```

### Set Default Audio Output

If you have multiple audio outputs, you may need to set the default:
```bash
# List audio outputs
pactl list short sinks

# Set default sink (replace X with your sink number)
pactl set-default-sink X
```

### Test Audio Output

Quick test with speaker-test:
```bash
speaker-test -t sine -f 1000 -l 1 -s 1
```

Press Ctrl+C to stop.

## Troubleshooting

### No Sound Output

1. **Check if audio is muted:**
   ```bash
   alsamixer
   ```
   Press `M` to unmute, use arrow keys to adjust volume.

2. **Check audio service:**
   ```bash
   systemctl status pulseaudio
   ```

3. **Test with aplay:**
   ```bash
   # Generate a test tone
   speaker-test -t sine -f 1000 -l 1
   ```

4. **Check audio device:**
   ```bash
   aplay -l
   ```

### Permission Issues

If you get permission errors, you may need to:
- Run with `sudo` (not recommended for long-term use)
- Add your user to the `audio` group:
  ```bash
  sudo usermod -a -G audio $USER
  ```
  Then log out and log back in.

### beep Command Not Found

Install beep:
```bash
sudo apt-get install beep
```

If beep still doesn't work, check if the pcspkr module is loaded:
```bash
lsmod | grep pcspkr
```

If not loaded:
```bash
sudo modprobe pcspkr
```

## Expected Behavior

### Critical Alarm Pattern
- **3 beeps** at 1000 Hz
- Each beep: 0.5 seconds
- Pause between beeps: ~0.2 seconds

### Warning Alarm Pattern
- **2 beeps** at 1000 Hz
- Each beep: 0.5 seconds
- Pause between beeps: ~0.2 seconds

### Info Alarm Pattern
- **1 beep** at 1000 Hz
- Beep duration: 0.5 seconds

## Integration with UPS Trap Receiver

The `SoundController` class is used by `ups_snmp_trap_receiver_v2.py` to play sound alerts when UPS alarms are detected. The test programs help verify that:

1. The audio system is working
2. The SoundController can successfully play beeps
3. Different alarm patterns are distinguishable

## Notes

- All test programs are designed to work on Raspberry Pi (Linux)
- They will attempt to work on other platforms but may have limited functionality
- The programs use non-blocking sound playback so they won't freeze if audio fails
- Volume control may vary depending on the audio method used

## Quick Start

1. Install beep (recommended):
   ```bash
   sudo apt-get install beep
   ```

2. Run the quick test:
   ```bash
   python3 test_sound_quick.py
   ```

3. If that works, try the comprehensive test:
   ```bash
   python3 test_raspberry_sound.py
   ```

4. Test the actual SoundController:
   ```bash
   python3 test_sound_controller.py
   ```

If all tests pass, your speaker/audio system is ready for use with the UPS trap receiver!

