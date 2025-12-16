# Raspberry Pi 4 GPIO Pin Reference

## Overview

The Raspberry Pi 4 has a **40-pin GPIO header** with:
- **26 usable GPIO pins** (BCM numbering: 2-27)
- **2 power pins**: 5V (pins 2, 4) and 3.3V (pins 1, 17)
- **8 ground pins** (GND)
- **2 reserved pins**: ID_SD and ID_SC (for HAT identification)

## GPIO Pins (BCM Numbering)

### All Available GPIO Pins
```
GPIO 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 
18, 19, 20, 21, 22, 23, 24, 25, 26, 27
```

**Total: 26 GPIO pins**

## Physical Pin Layout (40-pin Header)

```
    3.3V  [1]  [2]  5V
   GPIO2  [3]  [4]  5V
   GPIO3  [5]  [6]  GND
   GPIO4  [7]  [8]  GPIO14
     GND  [9]  [10] GPIO15
  GPIO17  [11] [12] GPIO18
  GPIO27  [13] [14] GND
  GPIO22  [15] [16] GPIO23
    3.3V  [17] [18] GPIO24
  GPIO10  [19] [20] GND
   GPIO9  [21] [22] GPIO25
  GPIO11  [23] [24] GPIO8
     GND  [25] [26] GPIO7
   GPIO0  [27] [28] GPIO1
   GPIO5  [29] [30] GND
   GPIO6  [31] [32] GPIO12
  GPIO13  [33] [34] GND
  GPIO19  [35] [36] GPIO16
  GPIO26  [37] [38] GPIO20
     GND  [39] [40] GPIO21
```

## Special Function Pins

### I2C Pins
- **GPIO 2 (SDA)**: I2C Data line
- **GPIO 3 (SCL)**: I2C Clock line
- Both have built-in pull-up resistors

### UART Pins
- **GPIO 14 (TXD)**: UART Transmit
- **GPIO 15 (RXD)**: UART Receive

### Hardware PWM Pins
- **GPIO 12**: Hardware PWM channel 0
- **GPIO 13**: Hardware PWM channel 1
- **GPIO 18**: Hardware PWM channel 0 (alternative)
- **GPIO 19**: Hardware PWM channel 1 (alternative)

### SPI Pins
- **GPIO 7 (CE1)**: SPI Chip Select 1
- **GPIO 8 (CE0)**: SPI Chip Select 0
- **GPIO 9 (MISO)**: SPI Master In Slave Out
- **GPIO 10 (MOSI)**: SPI Master Out Slave In
- **GPIO 11 (SCLK)**: SPI Serial Clock

## Recommended Pins for LED Control

For simple LED control (ON/OFF), you can use any GPIO pin. Common choices:

### General Purpose (No Special Functions)
- **GPIO 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 16, 17, 20, 21, 22, 23, 24, 25, 26, 27**

### Popular Choices for LED Projects
- **GPIO 18**: Often used (PWM capable, but works fine for simple ON/OFF)
- **GPIO 19**: Often used (PWM capable)
- **GPIO 20, 21**: Good general-purpose pins
- **GPIO 22, 23**: Good general-purpose pins
- **GPIO 24, 25**: Good general-purpose pins

### Avoid for Simple LED Control
- **GPIO 2, 3**: I2C (may interfere with I2C devices)
- **GPIO 14, 15**: UART (may interfere with serial communication)
- **GPIO 0, 1**: Reserved for HAT identification

## Power Specifications

- **3.3V pins**: Provide 3.3V (max ~50mA per pin, ~200mA total)
- **5V pins**: Provide 5V (limited by USB power supply, typically 2.5A total)
- **GND pins**: Ground reference

## Important Notes

1. **BCM vs Physical**: Always use BCM (Broadcom) pin numbering in code, not physical pin numbers
2. **Current Limits**: Each GPIO pin can source/sink up to 16mA (recommended: 8mA)
3. **Voltage Levels**: GPIO pins are 3.3V logic (NOT 5V tolerant)
4. **Pull-up/Pull-down**: Most GPIO pins have software-configurable pull-up/pull-down resistors
5. **PWM**: Hardware PWM available on GPIO 12, 13, 18, 19

## Example: Using GPIO Pins in Python

```python
import RPi.GPIO as GPIO

# Use BCM numbering (not physical pin numbers)
GPIO.setmode(GPIO.BCM)

# Setup pin 18 as output
GPIO.setup(18, GPIO.OUT)

# Turn ON
GPIO.output(18, GPIO.HIGH)

# Turn OFF
GPIO.output(18, GPIO.LOW)

# Cleanup
GPIO.cleanup()
```

## Testing All GPIO Pins

You can test all 26 GPIO pins using the test tool:

```bash
# Test all GPIO pins automatically
python3 test_gpio_pins.py --auto --pins 2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27
```

Or test specific pins:

```bash
# Test commonly used pins for LED control
python3 test_gpio_pins.py --auto --pins 4,5,6,17,18,19,20,21,22,23,24,25,26,27
```

## Summary

- **Total GPIO pins**: 26 (BCM 2-27)
- **Best for LED control**: GPIO 4, 5, 6, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27
- **Avoid for LEDs**: GPIO 2, 3 (I2C), GPIO 14, 15 (UART), GPIO 0, 1 (HAT ID)

