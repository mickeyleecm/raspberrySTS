@echo off
REM UPS SNMP Trap Sender - General Purpose
REM 
REM Usage examples:
REM   run_ups_trap_sender.bat battery_power
REM   run_ups_trap_sender.bat power_restored
REM   run_ups_trap_sender.bat battery_low
REM   run_ups_trap_sender.bat input_bad
REM
REM Default: sends battery_power trap to 192.168.111.137:162
REM
REM You can also modify the host and port below

set TRAP_TYPE=%1
if "%TRAP_TYPE%"=="" set TRAP_TYPE=battery_power

set TARGET_HOST=192.168.111.76
set TARGET_PORT=162

echo Sending trap: %TRAP_TYPE%
echo Target: %TARGET_HOST%:%TARGET_PORT%
echo.

python ups_snmp_trap_sender.py --trap %TRAP_TYPE% --host %TARGET_HOST% --port %TARGET_PORT%

pause

