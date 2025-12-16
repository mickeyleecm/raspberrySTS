"""
Configuration file for UPS SNMP Trap Receiver.

This file contains configuration settings that can be modified without changing the main code.

Note: Command-line arguments (--ups-ip) will override settings in this file.
"""

# Web Interface Authentication
WEB_USERNAME = 'admin'
WEB_PASSWORD = 'admin'

# UPS Device Information
# UPS Device IP Address (legacy - kept for backward compatibility)
# The IP address of the UPS device that will send SNMP traps
# This IP will be automatically added to ALLOWED_IPS if ALLOWED_IPS is not explicitly set
# for version 1.0, use this
UPS_IP = '192.168.111.173'

# UPS Name (legacy - kept for backward compatibility)
# Used as default if UPS_DEVICES doesn't have an entry for a source IP
# Example: 'UPS-Server-Room-01', 'Main UPS', 'Data Center UPS A'
# for version 1.0, use this
UPS_NAME = 'UPS Device'

# UPS Location (legacy - kept for backward compatibility)
# Used as default if UPS_DEVICES doesn't have an entry for a source IP
# Example: 'Server Room A', 'Building 1 - Floor 3', 'Data Center - Rack 5'
# for version 1.0, use this
UPS_LOCATION = 'NetSphere Data Center KW-2 Rack 5'

# SNMP Configuration
# SNMP community string for querying UPS status
# Default: 'public' (most UPS devices use this)
# Change this if your UPS device uses a different community string
SNMP_COMMUNITY = 'public'

# SNMP port for querying UPS status
# Default: 161 (standard SNMP port)
# Change this if your UPS device uses a non-standard SNMP port
SNMP_PORT = 161

# UPS Devices Configuration (Multiple UPS Support)
# Dictionary mapping UPS IP addresses to their name and location
# When a trap is received from a UPS, the system will look up the IP in this dictionary
# to get the UPS name and location for notifications
# If an IP is not found in this dictionary, it will use UPS_NAME and UPS_LOCATION as defaults
# Format: { 'IP_ADDRESS': { 'name': 'UPS Name', 'location': 'UPS Location' }, ... }
UPS_DEVICES = {
    '192.168.111.137': {
        'name': 'Temp UPS',
        'location': 'KTT West'
    },
    '192.168.111.173': {
        'name': 'Borri STS32A ',
        'location': 'KW East'
    },
    # Add more UPS devices here as needed
    # '192.168.111.138': {
    #     'name': 'UPS Device 2',
    #           'location': 'NetSphere 數據中心 KW2 機架1'
    # },
    # '192.168.111.139': {
    #     'name': 'UPS Device 3',
    #     'location': 'NetSphere Data Center KW-2 Rack 7'
    # },
}

# Allowed IP addresses list
# Traps will only be accepted from IPs in this list
# If empty list [], all IPs will be accepted
# If None, all IPs will be accepted (UPS_IP will be used as default)
# Command-line argument --ups-ip will override this setting
# If ALLOWED_IPS is None or empty, UPS_IP will be automatically added
# Example: ['192.168.111.137', '192.168.1.100']
ALLOWED_IPS = [
    UPS_IP,  # UPS device IP (from UPS_IP variable above)
    '127.0.0.1',
    '192.168.111.173',  # Borri STS32A ATS device
    # Add more allowed IPs here as needed
    # '192.168.1.100',
    # '10.0.0.50',
]

# Alternative: Accept all IPs (set to empty list or None)
# ALLOWED_IPS = []
# or
# ALLOWED_IPS = None

# GPIO Pin Configuration
# GPIO pins for LED control on Raspberry Pi
# Command-line arguments (--critical-pin, --warning-pin, --info-pin) will override these settings
# Set to None to disable that pin
GPIO_CRITICAL_PIN = 17  # GPIO pin for critical alarms
GPIO_WARNING_PIN = 17   # GPIO pin for warning alarms
GPIO_INFO_PIN = None    # GPIO pin for info alarms (optional)

# GPIO LED Settings
GPIO_BLINK_ENABLED = True   # Enable blinking for alarms (True/False)
GPIO_BLINK_INTERVAL = 0.5   # Blink interval in seconds
GPIO_ACTIVE_HIGH = True     # True if LED is active high, False for active low

# Email Notification Configuration
# Email will be sent when UPS alarms are triggered
# Set EMAIL_ENABLED = False to disable email notifications
EMAIL_ENABLED = False

# SMTP Server Configuration
SMTP_SERVER = '192.168.111.22'      # SMTP server hostname or IP address
SMTP_PORT = 25                       # SMTP server port (default: 25, TLS: 587, SSL: 465)
SMTP_USE_TLS = True                  # Use TLS encryption (True/False)
SMTP_USERNAME = ''                   # SMTP username (leave empty if not required)
SMTP_PASSWORD = ''                   # SMTP password (leave empty if not required)

# Email Sender Information
FROM_EMAIL = 'micky.lee@netsphere.com.hk'  # Sender email address
FROM_NAME = 'Micky.Lee'                    # Sender name (display name)

# Email Recipients (list of email addresses)
# Multiple email addresses can be added to receive UPS alarm notifications
# Example: ['admin@example.com', 'support@example.com', 'manager@example.com']
EMAIL_RECIPIENTS = [
    'micky.lee@netsphere.com.hk',
    # Add more email addresses here as needed
    # 'admin@example.com',
    # 'support@example.com',
]

# SMS Notification Configuration
# SMS will be sent when UPS alarms are triggered
# Set SMS_ENABLED = False to disable SMS notifications
SMS_ENABLED = False

# SMS API URL (base URL without parameters)
SMS_API_URL = 'https://www.mdtechcorp.com/openapi'
#https://www.mdtechcorp.com/openapi?destinatingAddress=92291045&username=69904570&password=8scitb3o6e&SMS=UPS Alarm Testing Message&type=1&returnMode=1        

# SMS API Credentials
SMS_USERNAME = '69904570'
SMS_PASSWORD = '8scitb3o6e'

# Mobile numbers to receive SMS alerts
# Option 1: Simple list (all recipients receive SMS at all times)
# Example: ['92291045', '12345678', '87654321']
# SMS_RECIPIENTS = [
#     '92291045',
#     # Add more mobile numbers here as needed
# ]

# Option 2: Time-based schedule (different recipients at different times)
# Format: List of dictionaries with 'start_time', 'end_time', and 'recipients'
# Time format: 'HH:MM' (24-hour format)
# If SMS_SCHEDULE is defined, it will override SMS_RECIPIENTS
# Example:
SMS_SCHEDULE = [
    {
        'start_time': '00:00',  # Start time (24-hour format)
        'end_time': '08:00',    # End time (24-hour format, exclusive)
        'recipients': ['92291045']  # List of phone numbers for this time period
    },
    {
        'start_time': '08:01',
        'end_time': '14:00',
        'recipients': ['61306195']
    },
    {
        'start_time': '14:01',
        'end_time': '23:59',
        'recipients': ['92291045']
    },
    # Time period 18:00 - 00:00: No recipients (SMS disabled during this time)
    # You can add more time periods as needed
]

# Fallback: Simple list (used if SMS_SCHEDULE is not defined or empty)
# This will be used if SMS_SCHEDULE is None, empty list, or not defined
# for version 1.0, use this
SMS_RECIPIENTS = [
    '92291045',
    # Add more mobile numbers here as needed
    # '12345678',
    # '87654321',
]

# SMS API Parameters
# SMS_TYPE: SMS message type
#   0 = Flash SMS (appears on screen temporarily, then disappears - NOT stored in phone's message list)
#   1 = Normal SMS (standard text message - STORED in phone's message list, can be read later)
#       "Saved to inbox" means the message is kept in your phone's message folder like regular SMS
SMS_TYPE = 1

# SMS_RETURN_MODE: Response mode for SMS API
#   0 = No response / Asynchronous mode (fire and forget, faster)
#   1 = Return response / Synchronous mode (wait for API response, confirms delivery status)
SMS_RETURN_MODE = 1

# Alarm LED Control Configuration
# ALARM_LED_ENABLED: Enable LED 10 when there is an alarm
#   True = LED 10 will be enabled when alarm is triggered (default behavior)
#   False = LED 10 will be disabled even when alarm is triggered
# Note: This controls the visual alarm indicator (LED 10)
ALARM_STATUS = True  # True = there is an alarm, False = there is no alarm 
# Buzzer Control Configuration
# BUZZER_MUTED: Mute the buzzer when there is an alarm (LED 10 enabled)
#   True = Buzzer will be muted (no sound) when alarm is triggered
#   False = Buzzer will sound when alarm is triggered (default behavior)
# Note: LED 10 will still be enabled to indicate alarm, but buzzer will be silent if muted
BUZZER_MUTED = True  # Updated by mute button Updated by mute button Updated by mute button Updated by mute button Updated by mute button Updated by mute button Updated by mute button Updated by mute button Updated by mute button Updated by mute button Updated by mute button Updated by mute button Updated by mute button Updated by mute button True to mute the buzzer, False to unmute the buzzer
BUZZER_VOLUME = 25  # Volume of the buzzer (0-100)

# Load LED Configuration (LEDs 11, 12, 13, 14)
# These LEDs indicate load percentage ranges on the UPS/ATS device
# LED 11: Load overload warning signal (Red) - indicates high load
# LED 12: Load normal status middle (Green) - indicates medium-high load
# LED 13: Load normal status (Green) - indicates medium load
# LED 14: Load normal status low (Green) - indicates low load
#
# Load percentage thresholds for each LED:
# - LED 14: Enabled when load is between LED_14_LOAD_MIN and LED_14_LOAD_MAX (inclusive)
# - LED 13: Enabled when load is between LED_13_LOAD_MIN and LED_13_LOAD_MAX (inclusive)
# - LED 12: Enabled when load is between LED_12_LOAD_MIN and LED_12_LOAD_MAX (inclusive)
# - LED 11: Enabled when load is >= LED_11_LOAD_THRESHOLD (overload warning)
#
# Note: Multiple LEDs can be enabled simultaneously based on overlapping ranges
# Example: If load is 25%, LEDs 12, 13, and 14 might all be enabled

# LED 14 (Low load indicator) - Green LED
L1_LOAD_MIN = 0   # Minimum load percentage to enable LED lEVEL 1 the minimum loading (inclusive)
L1_LOAD_MAX = 5   # Maximum load percentage to enable LED lEVEL 1 the minimum loading (inclusive)

# LED 13 (Medium load indicator) - Green LED
L2_LOAD_MIN = 6  # Minimum load percentage to enable LED lEVEL 2 middle loading (inclusive)
L2_LOAD_MAX = 20  # Maximum load percentage to enable LED lEVEL 2 middle loading (inclusive)

# LED 12 (Medium-high load indicator) - Green LED
L3_LOAD_MIN = 21  # Minimum load percentage to enable LED lEVEL 3 high loading(inclusive)
L3_LOAD_MAX = 28  # Maximum load percentage to enable LED lEVEL 3 high loading (inclusive)

# LED 11 (Overload warning indicator) - Red LED
L4_LOAD_THRESHOLD = 29  # Minimum load percentage to enable lEVEL 4 overload loading (inclusive, >= this value)

