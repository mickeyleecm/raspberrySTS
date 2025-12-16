# UPS SNMP Trap Receiver

A cross-platform Python program to receive and log SNMP traps from UPS (Uninterruptible Power Supply) devices. Works on **Windows** (for development/testing) and **Linux** (Raspberry Pi 4 / Linux-x64 for production).

## Features

- Receives SNMP traps on UDP port 162 (configurable)
- Logs traps to a file with timestamps
- Recognizes standard UPS-MIB (RFC 1628) trap OIDs
- Supports SNMPv1, SNMPv2c, and SNMPv3
- Detailed logging with trap information and variable bindings
- Automatic log level assignment based on trap severity

## Supported UPS Traps

The program recognizes and logs the following UPS alarm conditions:

- **upsTrapOnBattery** - UPS switched to battery power
- **upsAlarmInputBad** - Input voltage/frequency out of tolerance
- **upsAlarmOutputOverload** - Output load exceeds UPS capacity
- **upsAlarmGeneralFault** - General UPS fault detected
- **upsAlarmChargerFailed** - Charger subsystem problem
- **upsAlarmCommunicationsLost** - Communication problem
- **upsTrapTestCompleted** - Diagnostic test completion

## Prerequisites

- Python 3.7 or higher
- **Windows** (for development) or **Linux** (Raspberry Pi 4, Ubuntu, etc. for production)
- Administrator privileges (Windows) or root privileges (Linux) if using port 162, the default SNMP trap port

## Installation

1. Clone or download this repository to your development machine (Windows) or production server (Linux)

2. Install Python dependencies:

**Windows:**
```bash
pip install -r requirements.txt
```

**Linux:**
```bash
pip3 install -r requirements.txt
```

Or install directly:
```bash
# Windows
pip install pysnmp>=4.4.12

# Linux
pip3 install pysnmp>=4.4.12
```

## Usage

### Windows (Development/Testing)

**Basic Usage (Port 162 - Requires Administrator):**

Port 162 is the standard SNMP trap port and requires Administrator privileges:

1. Open PowerShell or Command Prompt as Administrator
2. Run:
```bash
python ups_snmp_trap_receiver.py
```

**Custom Port (No Admin Required):**

If you don't have Administrator privileges or want to use a different port:

```bash
python ups_snmp_trap_receiver.py --port 1162
```

**Custom Log File:**

```bash
python ups_snmp_trap_receiver.py --log-file C:\Logs\ups_traps.log
```

### Linux (Production)

**Basic Usage (Port 162 - Requires Root):**

Port 162 is the standard SNMP trap port and requires root privileges:

```bash
sudo python3 ups_snmp_trap_receiver.py
```

**Custom Port (No Root Required):**

If you don't have root privileges or want to use a different port:

```bash
python3 ups_snmp_trap_receiver.py --port 1162
```

**Note:** If using a custom port, configure your UPS to send traps to that port.

**Custom Log File:**

```bash
sudo python3 ups_snmp_trap_receiver.py --log-file /var/log/ups_traps.log
```

### Command Line Options

```
--port, -p       UDP port to listen on (default: 162)
--log-file, -l   Path to log file (default: ups_traps.log)
```

## UPS Configuration

Configure your UPS device to send SNMP traps to your Raspberry Pi:

1. **IP Address**: Set the trap receiver IP to your Raspberry Pi's IP address
2. **Port**: Use port 162 (default) or your custom port
3. **Community String**: Typically "public" for SNMPv2c (adjust in code if needed)
4. **Enable Traps**: Enable the specific alarm conditions you want to monitor

### Example UPS Configuration (APC)

- SNMP Trap Receiver: `192.168.1.100:162`
- Community String: `public`
- Enable traps for: Battery events, Input alarms, Output overload, etc.

## Log File Format

The log file contains detailed information about each received trap:

```
================================================================================
Timestamp: 2024-01-15 14:30:25
Source: 192.168.1.50:12345
Trap OID: 1.3.6.1.2.1.33.2.1
Trap Name: upsTrapOnBattery
Description: UPS switched to battery power
Variables:
  upsTrapOnBattery: 1
  1.3.6.1.2.1.33.1.2.1.0: 85
  1.3.6.1.2.1.33.1.2.3.0: 12.5
================================================================================
```

## Running as a Service (Systemd)

To run the trap receiver as a systemd service on Linux:

1. Create a service file `/etc/systemd/system/ups-trap-receiver.service`:

```ini
[Unit]
Description=UPS SNMP Trap Receiver
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 /path/to/ups_snmp_trap_receiver.py --log-file /var/log/ups_traps.log
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ups-trap-receiver.service
sudo systemctl start ups-trap-receiver.service
```

3. Check status:

```bash
sudo systemctl status ups-trap-receiver.service
```

## Troubleshooting

### Port Already in Use

If you see "Address already in use" error:
- Another SNMP trap receiver may be running
- **Windows:** Check with: `netstat -ano | findstr :162`
- **Linux:** Check with: `sudo netstat -ulnp | grep 162`
- Stop the conflicting service or use a different port

### Permission Denied

Port 162 requires elevated privileges:
- **Windows:** Run PowerShell/CMD as Administrator or use a port >= 1024
- **Linux:** Run with `sudo` or use a port >= 1024

### No Traps Received

1. Verify UPS is configured to send traps to your machine's IP address
2. Check firewall rules:
   - **Windows:** Allow UDP port 162 in Windows Firewall (Control Panel > Windows Defender Firewall > Advanced Settings)
   - **Linux:** `sudo ufw allow 162/udp`
3. Test with a trap sender tool
4. Check UPS SNMP configuration and community string
5. **Windows:** Ensure Windows Firewall isn't blocking incoming UDP connections

### Testing Trap Reception

You can test the receiver using `snmptrap` command (if snmptrap is installed):

```bash
snmptrap -v 2c -c public localhost:162 '' 1.3.6.1.2.1.33.2.1 1.3.6.1.2.1.33.1.2.1.0 i 85
```

## Security Considerations

- **Community Strings**: The default community string is "public". For production, modify the code to use secure community strings or SNMPv3
- **SNMPv3**: For enhanced security, configure SNMPv3 authentication in the code
- **Firewall**: Only allow SNMP trap traffic from trusted UPS devices
- **Log Rotation**: Implement log rotation to prevent log files from growing too large

## License

This program is provided as-is for use with UPS monitoring on Raspberry Pi 4 and Linux systems.

## Author

Software Engineer - UPS SNMP Trap Receiver for Raspberry Pi 4

