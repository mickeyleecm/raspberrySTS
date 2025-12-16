"""
Panel LED and GPIO Pin Mapping for ATS (Automatic Transfer Switch) Control Panel.

This file contains the mapping between panel LED numbers, GPIO pins, and their functions.
This mapping is used by GPIO control scripts to identify which GPIO pins control which LEDs.

Signal Type:
- 'Output' = Raspberry Pi controls it (LEDs, Speaker)
- 'Input' = Raspberry Pi reads its state (Mute, Reset buttons)
"""

# Panel LED and GPIO Pin Mapping
# This mapping defines the relationship between panel LED numbers, GPIO pins, and their functions
# Format: Dictionary with LED number as key, containing GPIO pin, function, signal type, and color
PANEL_LED_MAPPING = {
    1: {
        'gpio_pin': 4,
        'function': 'Source 1 voltage fault detection',
        'signal_type': 'Output',
        'color': 'Red',
        'name': 'MBP1 Fault'
    },
    2: {
        'gpio_pin': 5,
        'function': 'Source 1 voltage normal status',
        'signal_type': 'Output',
        'color': 'Green',
        'name': 'MBP1 Normal'
    },
    3: {
        'gpio_pin': 22,
        'function': 'Synchronization phase indicator 1',
        'signal_type': 'Output',
        'color': 'Green',
        'name': 'SYNC Status 1'
    },
    4: {
        'gpio_pin': 23,
        'function': 'Source 2 voltage normal status',
        'signal_type': 'Output',
        'color': 'Green',
        'name': 'MBP2 Normal'
    },
    5: {
        'gpio_pin': 6,
        'function': 'Source 2 voltage fault detection',
        'signal_type': 'Output',
        'color': 'Red',
        'name': 'MBP2 Fault'
    },
    6: {
        'gpio_pin': 24,
        'function': 'Source 1 is currently active',
        'signal_type': 'Output',
        'color': 'Green',
        'name': 'SYNC Status 1'
    },
    7: {
        'gpio_pin': 25,
        'function': 'Source 2 is currently active',
        'signal_type': 'Output',
        'color': 'Green',
        'name': 'SYNC Status 2'
    },
    8: {
        'gpio_pin': 16,
        'function': 'Overall system operating status',
        'signal_type': 'Output',
        'color': 'Green',
        'name': 'SYSTEM OK'
    },
    9: {
        'gpio_pin': 20,
        'function': 'Output status indicator',
        'signal_type': 'Output',
        'color': 'Green',  # Color not specified
        'name': 'OUTPUT Status'
    },
    10: {
        'gpio_pin': 12,
        'function': 'Critical alarm / fault condition',
        'signal_type': 'Output',
        'color': 'Red',
        'name': 'ALARM'
    },
    11: {
        'gpio_pin': 26,
        'function': 'Load overload warning signal',
        'signal_type': 'Output',
        'color': 'Red',
        'name': 'LOAD Overload'
    },
    12: {
        'gpio_pin': 27,
        'function': 'Load normal status (middle indicator)',
        'signal_type': 'Output',
        'color': 'Green',
        'name': 'LOAD Normal Middle'
    },
    13: {
        'gpio_pin': 11,
        'function': 'Load normal status (lower indicator)',
        'signal_type': 'Output',
        'color': 'Green',
        'name': 'LOAD Normal Lower'
    },
    14: {
        'gpio_pin': 15,
        'function': 'Load normal status (very lower indicator)',
        'signal_type': 'Output',
        'color': 'Green',
        'name': 'LOAD Normal Very Lower'
    },
    # Additional panel components
    'speaker': {
        'gpio_pin': 18,
        'function': 'Sound Alarm (1-4khz)',
        'signal_type': 'Output',
        'color': None,
        'name': 'Speaker/Buzzer'
    },
    'mute': {
        'gpio_pin': 19,
        'function': 'Silence alarm/buzzer',
        'signal_type': 'Input',
        'color': None,
        'name': 'Mute'
    },
    'reset': {
        'gpio_pin': 21,
        'function': 'Reset alarms/faults',
        'signal_type': 'Input',
        'color': None,
        'name': 'Reset'
    },
}


def get_gpio_pin_by_led(led_number):
    """
    Get GPIO pin number for a given LED number.
    
    Args:
        led_number: LED number (1-14) or 'speaker', 'mute', 'reset'
    
    Returns:
        GPIO pin number or None if not found
    
    Example:
        >>> get_gpio_pin_by_led(1)
        4
        >>> get_gpio_pin_by_led('speaker')
        18
    """
    if led_number in PANEL_LED_MAPPING:
        return PANEL_LED_MAPPING[led_number].get('gpio_pin')
    return None


def get_led_info_by_gpio(gpio_pin):
    """
    Get LED information for a given GPIO pin number.
    
    Args:
        gpio_pin: GPIO pin number
    
    Returns:
        Dictionary with LED info (led_number, gpio_pin, function, signal_type, color, name) or None if not found
    
    Example:
        >>> get_led_info_by_gpio(4)
        {'led_number': 1, 'gpio_pin': 4, 'function': 'Source 1 voltage fault detection', 
         'signal_type': 'Output', 'color': 'Red', 'name': 'MBP1 Fault'}
    """
    for led_key, led_info in PANEL_LED_MAPPING.items():
        if led_info.get('gpio_pin') == gpio_pin:
            result = led_info.copy()
            result['led_number'] = led_key
            return result
    return None


def get_all_output_pins():
    """
    Get all GPIO pins that are outputs (LEDs and Speaker).
    
    Returns:
        List of dictionaries with LED info for all output pins
    """
    output_pins = []
    for led_key, led_info in PANEL_LED_MAPPING.items():
        if led_info.get('signal_type') == 'Output':
            result = led_info.copy()
            result['led_number'] = led_key
            output_pins.append(result)
    return output_pins


def get_all_input_pins():
    """
    Get all GPIO pins that are inputs (Mute, Reset).
    
    Returns:
        List of dictionaries with pin info for all input pins
    """
    input_pins = []
    for pin_key, pin_info in PANEL_LED_MAPPING.items():
        if pin_info.get('signal_type') == 'Input':
            result = pin_info.copy()
            result['pin_key'] = pin_key
            input_pins.append(result)
    return input_pins


def get_leds_by_color(color):
    """
    Get all LEDs of a specific color.
    
    Args:
        color: LED color ('Red', 'Green', or None)
    
    Returns:
        List of dictionaries with LED info for LEDs matching the color
    """
    matching_leds = []
    for led_key, led_info in PANEL_LED_MAPPING.items():
        if led_info.get('color') == color and isinstance(led_key, int):
            result = led_info.copy()
            result['led_number'] = led_key
            matching_leds.append(result)
    return matching_leds


def get_all_led_numbers():
    """
    Get list of all LED numbers (1-14).
    
    Returns:
        List of LED numbers (integers 1-14)
    """
    return [led_key for led_key in PANEL_LED_MAPPING.keys() if isinstance(led_key, int)]


def get_all_gpio_pins():
    """
    Get list of all GPIO pin numbers used in the mapping.
    
    Returns:
        List of GPIO pin numbers (integers)
    """
    return [led_info.get('gpio_pin') for led_info in PANEL_LED_MAPPING.values() if led_info.get('gpio_pin') is not None]

