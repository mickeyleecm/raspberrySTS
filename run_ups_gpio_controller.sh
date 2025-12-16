#!/bin/bash
# UPS GPIO LED Controller - Linux/Debian/Raspberry Pi Shell Script
# This script runs the UPS GPIO LED Controller on Debian/Raspberry Pi
#
# Prerequisites:
#   On Debian: sudo apt-get install python3-pysnmp4 python3-pyasn1
#   On Raspberry Pi: pip3 install RPi.GPIO

echo "Starting UPS GPIO LED Controller..."
echo "Note: Requires root privileges for port 162"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Warning: Not running as root. Using port 1162 instead of 162"
    PORT=1162
else
    PORT=162
fi

# Run the controller
python3 ups_gpio_led_controller.py \
    --critical-pin 18 \
    --warning-pin 19 \
    --port $PORT \
    --log-file ups_gpio.log

