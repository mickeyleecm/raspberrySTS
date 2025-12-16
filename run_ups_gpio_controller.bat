@echo off
REM UPS GPIO LED Controller - Windows Batch Script
REM This script runs the UPS GPIO LED Controller (GPIO operations will be simulated on Windows)

echo Starting UPS GPIO LED Controller...
echo Note: GPIO operations will be simulated on Windows
echo.

python ups_gpio_led_controller.py --critical-pin 18 --warning-pin 19 --port 1162

pause

