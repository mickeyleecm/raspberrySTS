# Debian Installation Guide

This guide provides specific instructions for installing and running the UPS GPIO LED Controller on Debian systems (including Raspberry Pi OS).

## Installation Steps

### 1. Update Package List
```bash
sudo apt-get update
```

### 2. Install SNMP Python Packages (Debian Package Method)
```bash
sudo apt-get install python3-pysnmp4 python3-pyasn1
```

**Note:** The Debian package `python3-pysnmp4` provides the same `pysnmp` Python module that the program uses. No code changes are needed.

### 3. Install GPIO Library (Raspberry Pi Only)
```bash
pip3 install RPi.GPIO
```

**Note:** This is only needed on Raspberry Pi. On other Debian systems without GPIO, the program will simulate GPIO operations.

### 4. Verify Installation
```bash
python3 -c "import pysnmp; print('pysnmp OK')"
python3 -c "import pyasn1; print('pyasn1 OK')"
python3 -c "import RPi.GPIO; print('RPi.GPIO OK')"  # Only on Raspberry Pi
```

## Running the Program

### Basic Usage
```bash
sudo python3 ups_gpio_led_controller.py --critical-pin 18 --warning-pin 19
```

### With Custom Port (No Root Required)
```bash
python3 ups_gpio_led_controller.py --port 1162 --critical-pin 18 --warning-pin 19
```

## Alternative Installation (Using pip)

If you prefer to use pip instead of Debian packages:

```bash
pip3 install pysnmp pyasn1
pip3 install RPi.GPIO  # Only on Raspberry Pi
```

## Package Information

- **python3-pysnmp4**: Debian package providing pysnmp Python module
- **python3-pyasn1**: Debian package providing pyasn1 Python module
- **RPi.GPIO**: Must be installed via pip (not available as Debian package)

## Troubleshooting

### Package Not Found
If `python3-pysnmp4` is not found:
```bash
# Check available packages
apt-cache search pysnmp

# Or use pip installation instead
pip3 install pysnmp pyasn1
```

### Import Errors
If you get import errors:
```bash
# Verify package installation
dpkg -l | grep pysnmp
dpkg -l | grep pyasn1

# Check Python path
python3 -c "import sys; print(sys.path)"
```

### GPIO Not Available
On non-Raspberry Pi Debian systems, GPIO will be simulated. This is normal and allows the program to run for SNMP trap reception testing.

## Systemd Service (Optional)

To run as a systemd service on Debian:

1. Create service file `/etc/systemd/system/ups-gpio-controller.service`:
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

2. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ups-gpio-controller.service
sudo systemctl start ups-gpio-controller.service
```

3. Check status:
```bash
sudo systemctl status ups-gpio-controller.service
```

## Summary

The program works seamlessly with Debian's `python3-pysnmp4` package. No code changes are required - the Debian package provides the same `pysnmp` Python module that the program imports.

