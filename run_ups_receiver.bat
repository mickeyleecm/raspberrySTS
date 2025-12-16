@echo off
REM UPS SNMP Trap Receiver - Windows Batch File
REM Run on port 162 (REQUIRES Administrator privileges)
REM Only accepts traps from UPS at 192.168.111.137
REM
REM IMPORTANT: Right-click this file and select "Run as Administrator"

python ups_snmp_trap_receiver.py --port 162 --ups-ip 192.168.111.137

pause

