# UPS GPIO LED Controller - Quick Start Guide

## Overview

The `ups_gpio_led_controller.py` program receives SNMP traps from your UPS device and controls GPIO pins on Raspberry Pi 4 to trigger LED devices when alarms are detected.

## Quick Setup (Raspberry Pi / Debian)

### 1. Install Dependencies

**On Debian (Recommended - using Debian packages):**
```bash
sudo apt-get update
sudo apt-get install python3-pysnmp4 python3-pyasn1
pip3 install RPi.GPIO
```

**Alternative (using pip):**
```bash
pip3 install pysnmp pyasn1 RPi.GPIO
```

**Note:** The Debian package `python3-pysnmp4` provides the same `pysnmp` Python module, so the program works without any code changes.

### 2. Connect Hardware
- Connect LED to GPIO 18 (critical alarms) through a 220Ω-1kΩ resistor
- Connect LED to GPIO 19 (warning alarms) through a 220Ω-1kΩ resistor
- Connect LED cathodes to GND

### 3. Run the Program
```bash
sudo python3 ups_gpio_led_controller.py --critical-pin 18 --warning-pin 19
```

## GPIO Pin Mapping

| Alarm Severity | Default GPIO Pin | Physical Pin | Description |
|---------------|------------------|-------------|-------------|
| Critical      | 18               | 12          | Critical faults (general fault, charger failed, etc.) |
| Warning       | 19               | 35          | Warnings (on battery, battery low, etc.) |
| Info          | 20 (optional)    | 38          | Info messages (test completed) |

## Common Commands

**Basic usage:**
```bash
sudo python3 ups_gpio_led_controller.py --critical-pin 18 --warning-pin 19
```

**With auto-clear (LED turns off after 60 seconds):**
```bash
sudo python3 ups_gpio_led_controller.py --critical-pin 18 --warning-pin 19 --auto-clear 60
```

**Solid LED (no blinking):**
```bash
sudo python3 ups_gpio_led_controller.py --critical-pin 18 --warning-pin 19 --no-blink
```

**Custom port (no root required):**
```bash
python3 ups_gpio_led_controller.py --port 1162 --critical-pin 18 --warning-pin 19
```

**Accept traps only from specific UPS:**
```bash
sudo python3 ups_gpio_led_controller.py --critical-pin 18 --ups-ip 192.168.111.137
```

## Testing on Windows

The program works on Windows for development/testing. GPIO operations are simulated (logged but not executed):

```bash
python ups_gpio_led_controller.py --critical-pin 18 --warning-pin 19 --port 1162
```

## Alarm Types

### Critical Alarms (Red LED)
- Output overload
- General fault
- Charger failed
- Communications lost
- Battery discharged

### Warning Alarms (Yellow/Orange LED)
- On battery power
- Input bad
- Battery low
- Battery test failure
- Battery replacement needed
- Battery temperature high

### Info Alarms (Green/Blue LED)
- Test completed

## Configuration File

Create `gpio_config.json`:
```json
{
  "gpio_pins": {
    "critical": 18,
    "warning": 19,
    "info": 20
  },
  "blink_enabled": true,
  "blink_interval": 0.5,
  "active_high": true,
  "auto_clear_delay": null
}
```

Then run:
```bash
sudo python3 ups_gpio_led_controller.py --config gpio_config.json
```

## Troubleshooting

**LED not working?**
1. Check wiring and resistor
2. Verify GPIO pin number (use BCM numbering)
3. Test GPIO manually with Python
4. Try `--active-low` flag if LED is common cathode

**No traps received?**
1. Verify UPS is configured to send traps to Raspberry Pi IP
2. Check firewall: `sudo ufw allow 162/udp`
3. Test with trap sender: `python3 ups_snmp_trap_sender.py --trap battery_power --host <raspberry-pi-ip>`

**GPIO not available?**
- Ensure RPi.GPIO is installed: `pip3 install RPi.GPIO`
- Run with `sudo` if needed
- Check if running on Raspberry Pi (not Windows)

## More Information

See `UPS_GPIO_CONTROLLER_README.md` for detailed documentation.

