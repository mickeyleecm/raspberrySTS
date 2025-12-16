# UPS GPIO LED Controller

A Python program that receives SNMP traps from UPS devices and controls GPIO pins on Raspberry Pi 4 to trigger LED devices when alarms are detected.

## Features

- Receives SNMP traps from UPS devices
- Detects alarm conditions (critical, warning, info)
- Controls GPIO pins to trigger LED devices
- Supports multiple GPIO pins for different alarm types
- Configurable LED behaviors (on/off, blinking patterns)
- Auto-clear LED after delay (optional)
- Cross-platform: Works on Raspberry Pi 4 (Linux) with GPIO support, gracefully handles Windows (for development/testing)

## Prerequisites

- **Raspberry Pi 4** (or compatible) running **Debian** or Linux
- Python 3.7 or higher
- Root privileges (for port 162) or use custom port
- RPi.GPIO library (only on Raspberry Pi)
- LED devices connected to GPIO pins

## Installation

### 1. Install Python Dependencies

**On Debian/Raspberry Pi (Recommended - using Debian packages):**
```bash
# Install SNMP packages from Debian repositories
sudo apt-get update
sudo apt-get install python3-pysnmp4 python3-pyasn1

# Install GPIO library for Raspberry Pi
pip3 install RPi.GPIO
```

**On Debian/Raspberry Pi (Alternative - using pip):**
```bash
pip3 install -r requirements.txt
pip3 install RPi.GPIO
```

**On Windows (for development/testing):**
```bash
pip install -r requirements.txt
# RPi.GPIO is not needed on Windows - GPIO operations will be simulated
```

**Note:** The Debian package `python3-pysnmp4` provides the `pysnmp` Python module, so the program works without modification. The package name is different, but the Python import (`import pysnmp`) remains the same.

### 2. Hardware Setup

Connect LED devices to GPIO pins on Raspberry Pi:

- **Critical Alarm LED**: Connect to GPIO pin (e.g., GPIO 18)
- **Warning Alarm LED**: Connect to GPIO pin (e.g., GPIO 19)
- **Info Alarm LED**: Connect to GPIO pin (e.g., GPIO 20) - optional

**LED Connection:**
- For active-high LEDs: Connect LED anode to GPIO pin, cathode to GND through a current-limiting resistor (220Ω-1kΩ)
- For active-low LEDs: Connect LED cathode to GPIO pin, anode to 3.3V through a current-limiting resistor

**Common Raspberry Pi GPIO Pins:**
- GPIO 18 (Physical pin 12) - PWM capable
- GPIO 19 (Physical pin 35) - PWM capable
- GPIO 20 (Physical pin 38)
- GPIO 21 (Physical pin 40)

**Note:** Use BCM pin numbering (not physical pin numbers).

## Usage

### Basic Usage

**On Raspberry Pi (requires root for port 162):**
```bash
sudo python3 ups_gpio_led_controller.py --critical-pin 18 --warning-pin 19
```

**Custom Port (no root required):**
```bash
python3 ups_gpio_led_controller.py --port 1162 --critical-pin 18 --warning-pin 19
```

### Command Line Options

```
--port, -p              UDP port to listen on (default: 162)
--critical-pin, -c      GPIO pin for critical alarms (default: 18)
--warning-pin, -w      GPIO pin for warning alarms (default: 19)
--info-pin, -i          GPIO pin for info alarms (optional)
--ups-ip, -u            UPS IP address(es) to accept traps from (comma-separated)
--log-file, -l          Path to log file (default: ups_gpio.log)
--no-blink              Disable blinking (solid LED)
--blink-interval        Blink interval in seconds (default: 0.5)
--active-low            Use active-low logic (LED on with LOW signal)
--auto-clear            Auto-clear LED after delay in seconds
--config                Path to GPIO configuration file
```

### Configuration File

Create a `gpio_config.json` file (see `gpio_config.json.example`):

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

### Examples

**1. Basic setup with blinking LEDs:**
```bash
sudo python3 ups_gpio_led_controller.py --critical-pin 18 --warning-pin 19
```

**2. Solid LEDs (no blinking):**
```bash
sudo python3 ups_gpio_led_controller.py --critical-pin 18 --warning-pin 19 --no-blink
```

**3. Auto-clear LED after 60 seconds:**
```bash
sudo python3 ups_gpio_led_controller.py --critical-pin 18 --auto-clear 60
```

**4. Accept traps only from specific UPS:**
```bash
sudo python3 ups_gpio_led_controller.py --critical-pin 18 --ups-ip 192.168.111.137
```

**5. Custom blink interval:**
```bash
sudo python3 ups_gpio_led_controller.py --critical-pin 18 --blink-interval 1.0
```

**6. Active-low LED (common cathode):**
```bash
sudo python3 ups_gpio_led_controller.py --critical-pin 18 --active-low
```

## Alarm Types and Severity

The controller maps UPS alarm traps to severity levels:

### Critical Alarms (Red LED recommended)
- `upsAlarmOutputOverload` - Output load exceeds UPS capacity
- `upsAlarmGeneralFault` - General UPS fault detected
- `upsAlarmChargerFailed` - Charger subsystem problem
- `upsAlarmCommunicationsLost` - Communication problem
- `upsAlarmBatteryDischarged` - Battery is discharged

### Warning Alarms (Yellow/Orange LED recommended)
- `upsTrapOnBattery` - UPS switched to battery power
- `upsAlarmInputBad` - Input voltage/frequency out of tolerance
- `upsAlarmBatteryLow` - Battery charge below threshold
- `upsAlarmBatteryTestFailure` - Battery test failure
- `upsAlarmBatteryReplacement` - Battery replacement needed
- `upsAlarmBatteryTemperature` - High battery temperature

### Info Alarms (Green/Blue LED recommended)
- `upsTrapTestCompleted` - Diagnostic test completion

## UPS Configuration

Configure your UPS device to send SNMP traps to your Raspberry Pi:

1. **IP Address**: Set the trap receiver IP to your Raspberry Pi's IP address
2. **Port**: Use port 162 (default) or your custom port
3. **Community String**: Typically "public" for SNMPv2c
4. **Enable Traps**: Enable the specific alarm conditions you want to monitor

## Running as a Service (Systemd)

To run the GPIO controller as a systemd service on Raspberry Pi:

1. Create a service file `/etc/systemd/system/ups-gpio-controller.service`:

```ini
[Unit]
Description=UPS GPIO LED Controller
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 /path/to/ups_gpio_led_controller.py --critical-pin 18 --warning-pin 19 --log-file /var/log/ups_gpio.log
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ups-gpio-controller.service
sudo systemctl start ups-gpio-controller.service
```

3. Check status:

```bash
sudo systemctl status ups-gpio-controller.service
```

## Troubleshooting

### GPIO Not Working

1. **Check if running on Raspberry Pi:**
   ```bash
   python3 -c "import RPi.GPIO; print('GPIO available')"
   ```

2. **Check GPIO pin permissions:**
   - Run with `sudo` if needed
   - Ensure user is in `gpio` group: `sudo usermod -a -G gpio $USER`

3. **Verify pin numbers:**
   - Use BCM pin numbering (not physical pin numbers)
   - Check pin availability: `gpio readall` (if wiringpi is installed)

### No Traps Received

1. Verify UPS is configured to send traps to Raspberry Pi's IP
2. Check firewall: `sudo ufw allow 162/udp`
3. Test with trap sender: `python3 ups_snmp_trap_sender.py --trap battery_power --host <raspberry-pi-ip>`
4. Check logs: `tail -f ups_gpio.log`

### LED Not Turning On

1. **Check wiring:**
   - Verify LED polarity (anode/cathode)
   - Check resistor value (220Ω-1kΩ recommended)
   - Verify GPIO pin number

2. **Test GPIO manually:**
   ```python
   import RPi.GPIO as GPIO
   GPIO.setmode(GPIO.BCM)
   GPIO.setup(18, GPIO.OUT)
   GPIO.output(18, GPIO.HIGH)  # Turn on
   GPIO.output(18, GPIO.LOW)   # Turn off
   GPIO.cleanup()
   ```

3. **Check active-high/active-low setting:**
   - Try `--active-low` flag if LED is common cathode

### Windows Development

On Windows, GPIO operations are simulated (logged but not executed). This allows you to:
- Test SNMP trap reception
- Verify alarm detection logic
- Develop and debug without Raspberry Pi hardware

## Security Considerations

- **Community Strings**: The default community string is "public". For production, consider using SNMPv3
- **Firewall**: Only allow SNMP trap traffic from trusted UPS devices
- **GPIO Access**: Run with appropriate permissions (root or gpio group)

## License

This program is provided as-is for use with UPS monitoring on Raspberry Pi 4.

## Author

Software Engineer - UPS GPIO LED Controller for Raspberry Pi 4

