# Monitoring UPS SNMP Traps with Linux Tools

## Overview
SNMP traps use **UDP** (not TCP), typically on port **162**. Here are several ways to monitor UPS alarms in real-time.

---

## 1. Using Python Script (No Additional Tools Required) ⭐ RECOMMENDED

### Simple Python UDP Monitor
Since you already have Python, use the included `monitor_ups_traps_simple.py`:

```bash
# Monitor port 162 (requires sudo)
sudo python3 monitor_ups_traps_simple.py

# Monitor custom port (no sudo needed)
python3 monitor_ups_traps_simple.py --port 1162

# Filter by UPS IP address
sudo python3 monitor_ups_traps_simple.py --filter-ip 192.168.1.100

# Show help
python3 monitor_ups_traps_simple.py --help
```

### One-Liner Python Monitor
```bash
# Quick one-liner (no file needed)
sudo python3 -c "
import socket, datetime
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', 162))
print('Monitoring port 162...')
while True:
    data, addr = sock.recvfrom(65535)
    print(f'[{datetime.datetime.now()}] Trap from {addr[0]}:{addr[1]} - {len(data)} bytes')
"
```

---

## 2. Using tcpdump (If Available)

### Basic SNMP Trap Monitoring
```bash
# Monitor all SNMP traps on port 162 (requires root/sudo)
sudo tcpdump -i any -n -s 0 -A 'udp port 162'

# Monitor with more readable output
sudo tcpdump -i any -n -s 0 -X 'udp port 162'

# Save to file for later analysis
sudo tcpdump -i any -n -s 0 -w ups_traps.pcap 'udp port 162'
```

### Filter by Source IP (if you know the UPS IP)
```bash
# Monitor traps from specific UPS device
sudo tcpdump -i any -n -s 0 -A 'udp port 162 and host 192.168.1.100'

# Monitor traps from multiple UPS devices
sudo tcpdump -i any -n -s 0 -A 'udp port 162 and (host 192.168.1.100 or host 192.168.1.101)'
```

### Filter by Destination (if monitoring on specific interface)
```bash
# Monitor on specific network interface
sudo tcpdump -i eth0 -n -s 0 -A 'udp port 162'

# Monitor on loopback (localhost)
sudo tcpdump -i lo -n -s 0 -A 'udp port 162'
```

### Advanced Filtering
```bash
# Show only SNMP trap packets with hex dump
sudo tcpdump -i any -n -s 0 -x 'udp port 162'

# Verbose output with timestamps
sudo tcpdump -i any -n -s 0 -v -tttt 'udp port 162'

# Count packets only (no content)
sudo tcpdump -i any -n -c 100 'udp port 162'
```

---

## 3. Using netcat (nc) - Simple UDP Listener (If Available)

### Basic UDP Listener
```bash
# Listen on port 162 (requires root/sudo for ports < 1024)
sudo nc -u -l -p 162

# Listen on custom port (no root needed)
nc -u -l -p 1162

# Listen with verbose output
sudo nc -u -l -v -p 162
```

### Save to File
```bash
# Save received traps to file
sudo nc -u -l -p 162 > ups_traps_raw.txt

# With timestamps
sudo nc -u -l -p 162 | while read line; do echo "$(date): $line"; done >> ups_traps_timestamped.txt
```

---

## 4. Using Built-in Tools (ss, netstat)

### Using ss (Socket Statistics) - Usually Available
```bash
# Check if port 162 is listening
sudo ss -ulnp | grep 162

# Monitor continuously
watch -n 1 'ss -ulnp | grep 162'

# Show all UDP connections
ss -u -a | grep 162
```

### Using netstat (If Available)
```bash
# Check UDP ports
sudo netstat -ulnp | grep 162

# Monitor continuously
watch -n 1 'netstat -ulnp | grep 162'
```

### Using lsof (If Available)
```bash
# Check what's using port 162
sudo lsof -i :162

# Check all UDP connections
sudo lsof -i UDP
```

---

## 5. Using socat (If Available)
```bash
# Install socat (usually available)
# Debian/Ubuntu: sudo apt-get install socat
# RHEL/CentOS: sudo yum install socat

# Listen on UDP port 162
sudo socat UDP-LISTEN:162,fork - | while read line; do echo "$(date): $line"; done

# Save to file
sudo socat UDP-LISTEN:162,fork - >> ups_traps.log
```

---

## 6. Using Wireshark/tshark (GUI and CLI) (If Available)

### Command Line (tshark)
```bash
# Capture SNMP traps
sudo tshark -i any -f 'udp port 162' -Y 'snmp'

# Capture with detailed SNMP decoding
sudo tshark -i any -f 'udp port 162' -Y 'snmp' -V

# Save to file
sudo tshark -i any -f 'udp port 162' -w ups_traps.pcap

# Read from saved file
tshark -r ups_traps.pcap -Y 'snmp' -V
```

### GUI (Wireshark)
```bash
# Launch Wireshark GUI
sudo wireshark

# Then apply filter: udp.port == 162
# Or: snmp
```

---

## 7. Using ss (Socket Statistics) - Already Listed Above

### Check if Port 162 is Listening
```bash
# Check what's listening on port 162
sudo ss -ulnp | grep 162

# Monitor socket connections
watch -n 1 'ss -ulnp | grep 162'
```

---

## 8. Using netstat - Already Listed Above

### Check Listening Ports
```bash
# Check UDP ports
sudo netstat -ulnp | grep 162

# Monitor continuously
watch -n 1 'netstat -ulnp | grep 162'
```

---

## 9. Using snmptrapd (SNMP Trap Daemon) (If Available)

### Install snmptrapd
```bash
# Debian/Ubuntu
sudo apt-get install snmptrapd snmp

# RHEL/CentOS
sudo yum install net-snmp net-snmp-utils
```

### Configure and Run
```bash
# Edit configuration
sudo nano /etc/snmp/snmptrapd.conf

# Add this line to log all traps:
authCommunity log public

# Start snmptrapd
sudo snmptrapd -f -Lo -p /var/run/snmptrapd.pid

# Or run in foreground with logging
sudo snmptrapd -f -Lo
```

---

## 10. Real-time Monitoring Script (Python-based)

Create a simple monitoring script:

```bash
#!/bin/bash
# monitor_ups_traps.sh

UPS_IP="192.168.1.100"  # Change to your UPS IP
PORT=162

echo "Monitoring SNMP traps from $UPS_IP on port $PORT"
echo "Press Ctrl+C to stop"
echo "----------------------------------------"

sudo tcpdump -i any -n -s 0 -A "udp port $PORT and host $UPS_IP" | \
while read line; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $line"
done
```

Make it executable:
```bash
chmod +x monitor_ups_traps.sh
sudo ./monitor_ups_traps.sh
```

---

## 11. Monitoring Your Python Receiver

### Check if Your Receiver is Running
```bash
# Check if process is listening on port 162
sudo lsof -i :162

# Or
sudo ss -ulnp | grep python
```

### Monitor While Your Receiver Runs
```bash
# Terminal 1: Run your receiver
python3 ups_snmp_trap_receiver.py

# Terminal 2: Monitor with tcpdump
sudo tcpdump -i any -n -s 0 -A 'udp port 162'
```

---

## 12. Decoding SNMP Traps (If snmptrapd Available)

### Using snmptrapd with MIBs
```bash
# Install MIB files
sudo apt-get install snmp-mibs-downloader
sudo download-mibs

# Run snmptrapd with MIB support
sudo snmptrapd -f -Lo -m ALL
```

### Using snmptrapdecode
```bash
# Decode trap from pcap file
tshark -r ups_traps.pcap -Y 'snmp' -T fields -e snmp.trap.oid.0 | \
xargs -I {} snmptranslate -On {}
```

---

## 13. Useful One-Liners (Python-based)

```bash
# Count traps per minute
sudo tcpdump -i any -n -c 0 'udp port 162' 2>&1 | \
awk '/packets received/ {print strftime("%Y-%m-%d %H:%M:%S"), $1, "traps"}'

# Monitor and log with rotation
sudo tcpdump -i any -n -s 0 -w /var/log/ups_traps_$(date +%Y%m%d_%H%M%S).pcap -G 3600 'udp port 162'

# Alert on trap reception
sudo tcpdump -i any -n 'udp port 162' | while read line; do
    echo "ALERT: UPS Trap received at $(date)"
    # Add your notification here (email, etc.)
done
```

---

## Troubleshooting

### Permission Issues
```bash
# Port 162 requires root privileges
# Always use sudo for port 162

# Alternative: Use port >= 1024
# Modify your receiver to use port 1162
```

### No Traps Received
```bash
# Check firewall
sudo iptables -L -n | grep 162
sudo ufw status | grep 162

# Test with test trap sender
python3 ups_snmp_trap_sender.py
```

### Interface Not Found
```bash
# List available interfaces
ip link show
# Or
ifconfig

# Use 'any' to capture on all interfaces
sudo tcpdump -i any 'udp port 162'
```

---

## Quick Reference

### No Additional Tools Required (Python Only)
| Command | Purpose |
|---------|---------|
| `sudo python3 monitor_ups_traps_simple.py` | Monitor all SNMP traps (Python) |
| `sudo python3 monitor_ups_traps_simple.py --filter-ip 192.168.1.100` | Filter by source IP |
| `python3 monitor_ups_traps_simple.py --port 1162` | Use custom port (no sudo) |

### Built-in Linux Tools (Usually Available)
| Command | Purpose |
|---------|---------|
| `sudo ss -ulnp \| grep 162` | Check listening ports |
| `watch -n 1 'ss -ulnp \| grep 162'` | Monitor port continuously |
| `sudo lsof -i :162` | Check what's using port 162 |

### If Tools Are Installed
| Command | Purpose |
|---------|---------|
| `sudo tcpdump -i any -n -A 'udp port 162'` | Monitor all SNMP traps |
| `sudo nc -u -l -p 162` | Simple UDP listener |
| `sudo tshark -i any -f 'udp port 162'` | Wireshark CLI |

---

## Notes

- **SNMP traps use UDP, not TCP**
- **Port 162 requires root/sudo privileges** (privileged port < 1024)
- **Use port 1162 or higher** if you don't have root access
- **Python monitor (`monitor_ups_traps_simple.py`)** works with standard library only - no additional tools needed
- **ss/netstat** are usually available on most Linux systems
- **Your Python receiver** (`ups_snmp_trap_receiver.py`) already handles trap reception - use the monitor to verify traps are being sent

## Installation-Free Solutions (Recommended)

1. **Python monitor** (`monitor_ups_traps_simple.py`) - Uses only standard Python library
2. **ss command** - Usually pre-installed on Linux
3. **lsof** - Often pre-installed
4. **socat** - Lightweight, easy to install: `sudo apt-get install socat` or `sudo yum install socat`

