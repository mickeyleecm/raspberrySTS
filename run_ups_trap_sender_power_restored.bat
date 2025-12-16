@echo off
REM UPS SNMP Trap Sender - Send Power Restored Trap
REM Sends "Utility power has been restored" trap to the receiver

python ups_snmp_trap_sender.py --trap power_restored --host 192.168.111.137 --port 162

pause

