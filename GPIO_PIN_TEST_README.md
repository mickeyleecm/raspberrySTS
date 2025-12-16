# GPIO Pin Testing Tool

A comprehensive tool to test GPIO pins one by one or automatically to verify LED connections and functionality.

## Features

- ✅ Test individual pins manually (one at a time)
- ✅ Test all pins automatically in sequence
- ✅ Support for active-high and active-low LEDs
- ✅ Blink pattern testing
- ✅ Clear visual feedback
- ✅ Safe GPIO cleanup
- ✅ Works on Raspberry Pi (with RPi.GPIO) and simulates on other systems

## Installation

On Raspberry Pi, make sure RPi.GPIO is installed:
```bash
pip3 install RPi.GPIO
```

## Usage

### Test a Single Pin

```bash
# Test pin 18 manually
python3 test_gpio_pins.py --pin 18

# Test pin 18 automatically (no prompts)
python3 test_gpio_pins.py --pin 18 --auto
```

### Test Multiple Pins

```bash
# Test pins 18, 19, 20 manually (one by one with prompts)
python3 test_gpio_pins.py --pins 18,19,20

# Test pins 18, 19, 20 automatically
python3 test_gpio_pins.py --auto --pins 18,19,20
```

### Test with Active-Low Logic

If your LEDs are active-low (common cathode, LED on with LOW signal):

```bash
python3 test_gpio_pins.py --pins 18,19 --active-low
```

### Custom Blink Interval

```bash
# Test with faster blinking (0.3 seconds)
python3 test_gpio_pins.py --auto --pins 18,19,20 --blink-interval 0.3
```

### Custom Delay Between Pins

```bash
# Wait 3 seconds between each pin test
python3 test_gpio_pins.py --auto --pins 18,19,20 --delay 3
```

## Command Line Options

```
--pin, -p              Single GPIO pin number to test (BCM)
--pins                 Comma-separated GPIO pin numbers (e.g., "18,19,20")
--auto, -a             Automatic mode (no user input required)
--active-low           Use active-low logic (LED on with LOW signal)
--blink-interval       Blink interval in seconds (default: 0.5)
--delay                Delay between pin tests in automatic mode (default: 2.0)
```

## Test Sequence

For each pin, the tool performs:

1. **Setup**: Configures pin as output and initializes to OFF
2. **Turn ON**: Sets pin to HIGH (or LOW for active-low) for 1 second
3. **Turn OFF**: Sets pin to LOW (or HIGH for active-low) for 0.5 seconds
4. **Blink Pattern**: Blinks the pin 5 times with the specified interval
5. **Final State**: Sets pin to OFF

## Examples

### Example 1: Quick Test of Critical Alarm Pin

```bash
python3 test_gpio_pins.py --pin 18 --auto
```

### Example 2: Test All Alarm Pins

```bash
# Test critical (18), warning (19), and info (20) pins
python3 test_gpio_pins.py --auto --pins 18,19,20
```

### Example 3: Test with Custom Settings

```bash
python3 test_gpio_pins.py \
    --auto \
    --pins 18,19,20,21 \
    --active-low \
    --blink-interval 0.3 \
    --delay 1.5
```

## Output

The tool provides clear visual feedback:

```
============================================================
Testing GPIO Pin 18 (BCM)
============================================================
  → Turning ON pin 18...
  → Turning OFF pin 18...
  → Blinking pin 18 5 times (interval: 0.5s)...
    ON (1/5)
    OFF (1/5)
    ...
  → Setting pin 18 to OFF (final state)...

✓ Pin 18 test completed successfully!
```

## Troubleshooting

### LED Doesn't Turn On

1. **Check Wiring**:
   - For active-high: LED anode → GPIO pin, cathode → GND (through resistor)
   - For active-low: LED cathode → GPIO pin, anode → 3.3V (through resistor)
   - Use a current-limiting resistor (220Ω-1kΩ)

2. **Try Active-Low**:
   ```bash
   python3 test_gpio_pins.py --pin 18 --active-low
   ```

3. **Check Pin Number**:
   - Make sure you're using BCM pin numbers, not physical pin numbers
   - Common BCM pins: 18, 19, 20, 21, 22, 23, 24, 25

4. **Verify GPIO Access**:
   - On Raspberry Pi, you may need to run with `sudo` if GPIO permissions are restricted
   - Check if RPi.GPIO is installed: `pip3 list | grep RPi.GPIO`

### Permission Errors

If you get permission errors:
```bash
sudo python3 test_gpio_pins.py --pin 18
```

### GPIO Not Available

If running on non-Raspberry Pi:
- The tool will run in simulation mode
- GPIO operations will be logged but not executed
- This is useful for testing the script logic

## Integration with SNMP Trap Receiver

After testing your GPIO pins, configure them in your SNMP trap receiver:

```bash
# Example: Use pin 18 for critical, pin 19 for warning
python3 ups_snmp_trap_receiver_v2.py \
    --critical-pin 18 \
    --warning-pin 19 \
    --info-pin 20
```

Or in configuration file:
```json
{
  "gpio_pins": {
    "critical": 18,
    "warning": 19,
    "info": 20
  }
}
```

## Safety Notes

- The tool automatically cleans up GPIO pins after testing
- All pins are set to OFF state before cleanup
- Press Ctrl+C at any time to safely interrupt and cleanup
- Always use current-limiting resistors with LEDs

