#!/bin/bash
# Test script to verify SNMP trap reception

echo "Testing SNMP trap reception..."
echo ""

# Check if port 162 is in use
echo "1. Checking if port 162 is available..."
if sudo netstat -ulnp 2>/dev/null | grep -q ":162 "; then
    echo "   WARNING: Port 162 is already in use!"
    echo "   Another SNMP trap receiver may be running"
    sudo netstat -ulnp 2>/dev/null | grep ":162 "
else
    echo "   OK: Port 162 is available"
fi

echo ""
echo "2. Testing trap sender..."
echo "   Run this in Terminal 1:"
echo "   sudo python3 ups_gpio_led_controller.py --critical-pin 17 --warning-pin 17"
echo ""
echo "   Then in Terminal 2, run:"
echo "   python3 ups_snmp_trap_sender.py --trap battery_power --host localhost --port 162"
echo ""
echo "   Or try with 127.0.0.1:"
echo "   python3 ups_snmp_trap_sender.py --trap battery_power --host 127.0.0.1 --port 162"
echo ""

# Get local IP
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo "3. Your Raspberry Pi IP address: $LOCAL_IP"
echo "   You can also send traps to this IP:"
echo "   python3 ups_snmp_trap_sender.py --trap battery_power --host $LOCAL_IP --port 162"
echo ""

echo "4. Check firewall:"
echo "   sudo ufw status | grep 162"
echo "   If blocked, allow it: sudo ufw allow 162/udp"
echo ""

