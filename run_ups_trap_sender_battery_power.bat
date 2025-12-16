@echo off
REM UPS SNMP Trap Sender - Send Battery Power Trap
REM Sends "UPS switched to battery power" trap to the receiver

python ups_snmp_trap_sender.py --trap battery_power --host 192.168.111.137 --port 162

pause

