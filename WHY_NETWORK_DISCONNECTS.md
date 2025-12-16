# Why Network Disconnects When Running test_sound_quick.py

## Problem

When running `test_sound_quick.py`, the network connection disconnects. This happens because:

## Root Cause

### 1. **`speaker-test` Uses GPIO Pins for Audio**

On Raspberry Pi, the `speaker-test` command uses **GPIO pins for PWM audio output**. Specifically:
- GPIO 18 and GPIO 19 are commonly used for PWM audio
- These pins are shared with other system functions

### 2. **GPIO Pin Conflicts**

When `speaker-test` activates GPIO pins for audio:
- It can interfere with network controller hardware
- Some GPIO pins are shared with Ethernet/USB controllers
- PWM audio on certain pins can cause system instability

### 3. **Hardware Conflicts**

Possible conflicts:
- **GPIO 18/19**: Used by PWM audio, can conflict with network
- **Power supply**: Speaker drawing too much current
- **Hardware short**: Incorrect wiring causing system reset

## Solution

### Option 1: Use GPIO-Based Testing (Recommended)

**Use `test_sound_quick_safe.py` instead:**
```bash
python3 test_sound_quick_safe.py
```

This version:
- Uses only GPIO PWM (no `speaker-test`)
- Tests safe GPIO pins that don't conflict with network
- More reliable and won't disconnect network

### Option 2: Find Your Speaker Pin First

**Use the pin finder program:**
```bash
python3 test_speaker_find_pin_quick.py
```

This will test GPIO pins 18-60 to find which pin your speaker is connected to.

### Option 3: Avoid `speaker-test` Command

**Don't use `speaker-test` if:**
- You have a GPIO-connected speaker
- Network is critical
- You're testing on a production system

## Safe GPIO Pins for Speakers

These pins are generally safe and don't conflict with network:

- **GPIO 18** (PWM capable) - Physical pin 12
- **GPIO 19** (PWM capable) - Physical pin 35
- **GPIO 21** (PWM capable) - Physical pin 40
- **GPIO 22** (PWM capable) - Physical pin 15
- **GPIO 23** (PWM capable) - Physical pin 16
- **GPIO 24** (PWM capable) - Physical pin 18
- **GPIO 25** (PWM capable) - Physical pin 22

## Pins to Avoid

- **GPIO 0/1**: I2C (used by system)
- **GPIO 14/15**: UART (serial console)
- **GPIO 27/28**: I2C (can cause issues)

## Recommended Approach

1. **First, find which GPIO pin your speaker is on:**
   ```bash
   python3 test_speaker_find_pin_quick.py
   ```

2. **Then test that specific pin safely:**
   ```bash
   python3 test_sound_quick_safe.py
   ```

3. **Use GPIO-based audio in your UPS trap receiver:**
   - Configure the speaker pin in `config.py`
   - Use `SoundController` with GPIO PWM instead of `speaker-test`

## Prevention

To prevent network disconnection:
- ✅ Use GPIO PWM directly (not `speaker-test`)
- ✅ Test pins individually before running full tests
- ✅ Use safe GPIO pins (18, 19, 21-25)
- ✅ Ensure proper power supply (use external power for speaker if needed)
- ✅ Check wiring for shorts or incorrect connections

## Alternative: Use System Audio (HDMI/3.5mm)

If you need system audio (not GPIO):
- Use HDMI audio output
- Use 3.5mm audio jack
- These don't use GPIO pins and won't conflict with network

