@echo off
REM UPS SNMP Trap Sender - Test with Localhost
REM Sends trap to localhost on port 1162 (for testing with receiver on custom port)
REM
REM Make sure the receiver is running on port 1162:
REM   python ups_snmp_trap_receiver.py --port 1162

set TRAP_TYPE=%1
if "%TRAP_TYPE%"=="" set TRAP_TYPE=battery_power

echo Sending trap: %TRAP_TYPE%
echo Target: localhost:1162
echo.

python ups_snmp_trap_sender.py --trap %TRAP_TYPE% --host localhost --port 1162

pause

