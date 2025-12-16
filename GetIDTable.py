"""
Status Query OID Table for UPS/ATS/i-STS SNMP Status Queries.

This file contains all status query OID mappings for reading device information
via SNMP GET operations. These OIDs are used by ups_status_query.py to query
current device status, identification, battery, input/output power, etc.

Unlike TrapIDTable.py which contains TRAP OIDs (device-initiated notifications),
this file contains GET OIDs (query-initiated status reads).

MIB Files:
- RFC 1628 UPS-MIB
- SMAP SNMP R1e.mib (APC PowerNet MIB)
- ATS_Stork_V1_05 - Borri STS32A.MIB
- i-STS snmp-mib.mib
"""

# ============================================================================
# UPS MIB OID Definitions (RFC 1628 and SMAP extensions)
# ============================================================================

# 1. UPS Identification Information
# RFC 1628 Base OID: 1.3.6.1.2.1.33.1.1.x
UPS_IDENT_OIDS = {
    'upsIdentModel': '1.3.6.1.2.1.33.1.1.1.0',           # Model Name
    'upsIdentUPSName': '1.3.6.1.2.1.33.1.1.2.0',         # UPS Name (8-byte identifier)
    'upsIdentFirmwareRevision': '1.3.6.1.2.1.33.1.1.3.0', # Firmware Revision
    'upsIdentDateOfManufacture': '1.3.6.1.2.1.33.1.1.4.0', # Date of Manufacture (mm/dd/yy)
    'upsIdentSerialNumber': '1.3.6.1.2.1.33.1.1.5.0',     # Serial Number
    'upsIdentAgentFirmwareRevision': '1.3.6.1.2.1.33.1.1.6.0', # Agent Firmware Revision
}

# SMAP-specific identification OIDs (from SMAP SNMP R1e.mib)
# Base path: 1.3.6.1.4.1.935.1.1.1.1 (upsIdentp)
# upsBaseIdent = { upsIdentp 1 } = 1.3.6.1.4.1.935.1.1.1.1.1
# upsSmartIdent = { upsIdentp 2 } = 1.3.6.1.4.1.935.1.1.1.1.2
SMAP_IDENT_OIDS = {
    'upsBaseIdentModel': '1.3.6.1.4.1.935.1.1.1.1.1.1.0',      # Model Name (upsBaseIdent 1)
    'upsBaseIdentUpsName': '1.3.6.1.4.1.935.1.1.1.1.1.2.0',    # UPS Name (upsBaseIdent 2)
    'upsSmartIdentFirmwareRevision': '1.3.6.1.4.1.935.1.1.1.1.2.1.0', # Firmware Revision (upsSmartIdent 1)
    'upsSmartIdentDateOfManufacture': '1.3.6.1.4.1.935.1.1.1.1.2.2.0', # Date of Manufacture (upsSmartIdent 2)
    'upsSmartIdentUpsSerialNumber': '1.3.6.1.4.1.935.1.1.1.1.2.3.0', # Serial Number (upsSmartIdent 3)
    'upsSmartIdentAgentFirmwareRevision': '1.3.6.1.4.1.935.1.1.1.1.2.4.0', # Agent Firmware (upsSmartIdent 4)
}

# 2. Battery Status and Health
# RFC 1628 Base OID: 1.3.6.1.2.1.33.1.2.x
# SMAP Base OID: 1.3.6.1.4.1.935.1.1.1.2.x
BATTERY_OIDS = {
    # RFC 1628 Battery OIDs
    'upsBatteryStatus': '1.3.6.1.2.1.33.1.2.1.0',              # Battery Status
    'upsSecondsOnBattery': '1.3.6.1.2.1.33.1.2.2.0',          # Time on Battery (seconds)
    'upsEstimatedMinutesRemaining': '1.3.6.1.2.1.33.1.2.3.0', # Runtime Remaining (minutes)
    'upsEstimatedChargeRemaining': '1.3.6.1.2.1.33.1.2.4.0',  # Battery Capacity (%)
    'upsBatteryVoltage': '1.3.6.1.2.1.33.1.2.5.0',            # Battery Voltage (1/10 VDC)
    'upsBatteryTemperature': '1.3.6.1.2.1.33.1.2.6.0',        # Battery Temperature (1/10 °C)
    'upsBatteryTestResult': '1.3.6.1.2.1.33.1.2.7.0',         # Battery Test Result
    
    # SMAP-specific Battery OIDs
    'upsBaseBatteryStatus': '1.3.6.1.4.1.935.1.1.1.2.1.1.0',  # Battery Status
    'upsBaseBatteryTimeOnBattery': '1.3.6.1.4.1.935.1.1.1.2.1.2.0', # Time on Battery
    'upsSmartBatteryCapacity': '1.3.6.1.4.1.935.1.1.1.2.2.1.0', # Battery Capacity (%)
    'upsSmartBatteryVoltage': '1.3.6.1.4.1.935.1.1.1.2.2.2.0', # Battery Voltage (1/10 VDC)
    'upsSmartBatteryTemperature': '1.3.6.1.4.1.935.1.1.1.2.2.3.0', # Battery Temperature (1/10 °C)
    'upsSmartBatteryRunTimeRemaining': '1.3.6.1.4.1.935.1.1.1.2.2.4.0', # Runtime Remaining (seconds)
    'upsSmartBatteryReplaceIndicator': '1.3.6.1.4.1.935.1.1.1.2.2.5.0', # Replace Indicator
    'upsSmartBatteryFullChargeVoltage': '1.3.6.1.4.1.935.1.1.1.2.2.6.0', # Full Charge Voltage
    'upsSmartBatteryCurrent': '1.3.6.1.4.1.935.1.1.1.2.2.7.0', # Battery Current (%)
    'upsBaseBatteryLastReplaceDate': '1.3.6.1.4.1.935.1.1.1.2.1.3.0', # Last Replace Date
}

# 3. Input Power Monitoring
# RFC 1628 Base OID: 1.3.6.1.2.1.33.1.3.x
# SMAP Base OID: 1.3.6.1.4.1.935.1.1.1.3.x
INPUT_OIDS = {
    # RFC 1628 Input OIDs
    'upsInputLineBads': '1.3.6.1.2.1.33.1.3.2.1.5.1',        # Line Fail Count
    'upsInputVoltage': '1.3.6.1.2.1.33.1.3.3.1.3.1',         # Line Voltage (1/10 VAC)
    'upsInputFrequency': '1.3.6.1.2.1.33.1.3.3.1.2.1',       # Input Frequency (1/10 Hz)
    'upsInputCurrent': '1.3.6.1.2.1.33.1.3.3.1.4.1',         # Input Current (1/10 A)
    
    # SMAP-specific Input OIDs (from SMAP SNMP R1e.mib)
    # upsBaseInput = { upsInputp 1 } = 1.3.6.1.4.1.935.1.1.1.3.1
    # upsSmartInput = { upsInputp 2 } = 1.3.6.1.4.1.935.1.1.1.3.2
    'upsBaseInputPhase': '1.3.6.1.4.1.935.1.1.1.3.1.1.0',     # Input Phase (upsBaseInput 1)
    'upsSmartInputLineVoltage': '1.3.6.1.4.1.935.1.1.1.3.2.1.0', # Line Voltage (1/10 VAC) (upsSmartInput 1)
    'upsSmartInputMaxLineVoltage': '1.3.6.1.4.1.935.1.1.1.3.2.2.0', # Max Line Voltage (1/10 VAC) (upsSmartInput 2)
    'upsSmartInputMinLineVoltage': '1.3.6.1.4.1.935.1.1.1.3.2.3.0', # Min Line Voltage (1/10 VAC) (upsSmartInput 3)
    'upsSmartInputFrequency': '1.3.6.1.4.1.935.1.1.1.3.2.4.0', # Input Frequency (1/10 Hz) (upsSmartInput 4)
    'upsSmartInputLineFailCause': '1.3.6.1.4.1.935.1.1.1.3.2.5.0', # Line Fail Cause (upsSmartInput 5)
}

# 4. Output Power Status
# RFC 1628 Base OID: 1.3.6.1.2.1.33.1.4.x
# SMAP Base OID: 1.3.6.1.4.1.935.1.1.1.4.x
OUTPUT_OIDS = {
    # RFC 1628 Output OIDs
    'upsOutputSource': '1.3.6.1.2.1.33.1.4.1.0',              # Output Status
    'upsOutputVoltage': '1.3.6.1.2.1.33.1.4.4.1.2.1',        # Output Voltage (1/10 VAC)
    'upsOutputFrequency': '1.3.6.1.2.1.33.1.4.2.0',          # Output Frequency (1/10 Hz)
    'upsOutputLoad': '1.3.6.1.2.1.33.1.4.4.1.3.1',           # Output Load (%)
    'upsOutputCurrent': '1.3.6.1.2.1.33.1.4.4.1.4.1',         # Output Current (1/10 A)
    
    # SMAP-specific Output OIDs (from SMAP SNMP R1e.mib)
    # upsBaseOutput = { upsOutputp 1 } = 1.3.6.1.4.1.935.1.1.1.4.1
    # upsSmartOutput = { upsOutputp 2 } = 1.3.6.1.4.1.935.1.1.1.4.2
    'upsBaseOutputStatus': '1.3.6.1.4.1.935.1.1.1.4.1.1.0',  # Output Status (upsBaseOutput 1)
    'upsBaseOutputPhase': '1.3.6.1.4.1.935.1.1.1.4.1.2.0',    # Output Phase (upsBaseOutput 2)
    'upsSmartOutputVoltage': '1.3.6.1.4.1.935.1.1.1.4.2.1.0', # Output Voltage (1/10 VAC) (upsSmartOutput 1)
    'upsSmartOutputFrequency': '1.3.6.1.4.1.935.1.1.1.4.2.2.0', # Output Frequency (1/10 Hz) (upsSmartOutput 2)
    'upsSmartOutputLoad': '1.3.6.1.4.1.935.1.1.1.4.2.3.0',    # Output Load (%) (upsSmartOutput 3)
}

# 5. Three-Phase UPS Support (from SMAP SNMP R1e.mib)
# Base path: 1.3.6.1.4.1.935.1.1.1.8 (upsThreePhase)
# upsThreePhaseInputGrp = { upsThreePhase 2 } = 1.3.6.1.4.1.935.1.1.1.8.2
# upsThreePhaseOutputGrp = { upsThreePhase 3 } = 1.3.6.1.4.1.935.1.1.1.8.3
# upsThreePhaseBypassGrp = { upsThreePhase 4 } = 1.3.6.1.4.1.935.1.1.1.8.4
# upsThreePhaseDCandRectifierStatusGrp = { upsThreePhase 5 } = 1.3.6.1.4.1.935.1.1.1.8.5
# upsThreePhaseFaultStatusGrp = { upsThreePhase 7 } = 1.3.6.1.4.1.935.1.1.1.8.7
THREE_PHASE_OIDS = {
    # Input Phase Readings (upsThreePhaseInputGrp)
    'upsThreePhaseInputFrequency': '1.3.6.1.4.1.935.1.1.1.8.2.1.0', # Input Frequency (upsThreePhaseInputGrp 1)
    'upsThreePhaseInputVoltageR': '1.3.6.1.4.1.935.1.1.1.8.2.2.0', # Input Voltage R phase (upsThreePhaseInputGrp 2)
    'upsThreePhaseInputVoltageS': '1.3.6.1.4.1.935.1.1.1.8.2.3.0', # Input Voltage S phase (upsThreePhaseInputGrp 3)
    'upsThreePhaseInputVoltageT': '1.3.6.1.4.1.935.1.1.1.8.2.4.0', # Input Voltage T phase (upsThreePhaseInputGrp 4)
    
    # Output Phase Readings (upsThreePhaseOutputGrp)
    'upsThreePhaseOutputFrequency': '1.3.6.1.4.1.935.1.1.1.8.3.1.0', # Output Frequency (upsThreePhaseOutputGrp 1)
    'upsThreePhaseOutputVoltageR': '1.3.6.1.4.1.935.1.1.1.8.3.2.0', # Output Voltage R phase (upsThreePhaseOutputGrp 2)
    'upsThreePhaseOutputVoltageS': '1.3.6.1.4.1.935.1.1.1.8.3.3.0', # Output Voltage S phase (upsThreePhaseOutputGrp 3)
    'upsThreePhaseOutputVoltageT': '1.3.6.1.4.1.935.1.1.1.8.3.4.0', # Output Voltage T phase (upsThreePhaseOutputGrp 4)
    'upsThreePhaseOutputLoadR': '1.3.6.1.4.1.935.1.1.1.8.3.5.0',    # Load R phase (%) (upsThreePhaseOutputGrp 5)
    'upsThreePhaseOutputLoadS': '1.3.6.1.4.1.935.1.1.1.8.3.6.0',    # Load S phase (%) (upsThreePhaseOutputGrp 6)
    'upsThreePhaseOutputLoadT': '1.3.6.1.4.1.935.1.1.1.8.3.7.0',    # Load T phase (%) (upsThreePhaseOutputGrp 7)
    
    # Bypass Source (upsThreePhaseBypassGrp)
    'upsThreePhaseBypassFrequency': '1.3.6.1.4.1.935.1.1.1.8.4.1.0', # Bypass Frequency (upsThreePhaseBypassGrp 1)
    'upsThreePhaseBypassVoltageR': '1.3.6.1.4.1.935.1.1.1.8.4.2.0', # Bypass Voltage R phase (upsThreePhaseBypassGrp 2)
    'upsThreePhaseBypassVoltageS': '1.3.6.1.4.1.935.1.1.1.8.4.3.0', # Bypass Voltage S phase (upsThreePhaseBypassGrp 3)
    'upsThreePhaseBypassVoltageT': '1.3.6.1.4.1.935.1.1.1.8.4.4.0', # Bypass Voltage T phase (upsThreePhaseBypassGrp 4)
    
    # DC and Rectifier Status (upsThreePhaseDCandRectifierStatusGrp)
    'upsThreePhaseRectifierRotationError': '1.3.6.1.4.1.935.1.1.1.8.5.1.0', # Rectifier Rotation Error (upsThreePhaseDCandRectifierStatusGrp 1)
    'upsThreePhaseLowBatteryShutdown': '1.3.6.1.4.1.935.1.1.1.8.5.2.0', # Low Battery Shutdown (upsThreePhaseDCandRectifierStatusGrp 2)
    'upsThreePhaseChargeStatus': '1.3.6.1.4.1.935.1.1.1.8.5.6.0', # Charge Status (upsThreePhaseDCandRectifierStatusGrp 6)
    'upsThreePhaseRectifierOperatingStatus': '1.3.6.1.4.1.935.1.1.1.8.5.7.0', # Rectifier Operating Status (upsThreePhaseDCandRectifierStatusGrp 7)
    'upsThreePhaseInOutConfiguration': '1.3.6.1.4.1.935.1.1.1.8.5.4.0', # In/Out Configuration (upsThreePhaseDCandRectifierStatusGrp 4)
    
    # Fault Status Indicators (upsThreePhaseFaultStatusGrp)
    'upsThreePhaseEmergencyStop': '1.3.6.1.4.1.935.1.1.1.8.7.1.0', # Emergency Stop (upsThreePhaseFaultStatusGrp 1)
    'upsThreePhaseHighDCShutdown': '1.3.6.1.4.1.935.1.1.1.8.7.2.0', # High DC Shutdown (upsThreePhaseFaultStatusGrp 2)
    'upsThreePhaseBypassBreaker': '1.3.6.1.4.1.935.1.1.1.8.7.3.0', # Bypass Breaker (upsThreePhaseFaultStatusGrp 3)
    'upsThreePhaseOverLoad': '1.3.6.1.4.1.935.1.1.1.8.7.4.0', # Over Load (upsThreePhaseFaultStatusGrp 4)
    'upsThreePhaseInverterOutputFail': '1.3.6.1.4.1.935.1.1.1.8.7.5.0', # Inverter Output Fail (upsThreePhaseFaultStatusGrp 5)
    'upsThreePhaseOverTemperature': '1.3.6.1.4.1.935.1.1.1.8.7.6.0', # Over Temperature (upsThreePhaseFaultStatusGrp 6)
    'upsThreePhaseShortCircuit': '1.3.6.1.4.1.935.1.1.1.8.7.7.0', # Short Circuit (upsThreePhaseFaultStatusGrp 7)
}

# ============================================================================
# ATS (Automatic Transfer Switch) MIB Definitions
# Based on ATS_Stork_V1_05 - Borri STS32A.MIB
#
# ROOT CAUSE AND PROBLEM:
# -----------------------
# The MIB file (ATS_Stork_V1_05 - Borri STS32A.MIB) defines atsAgent(3), which
# results in OID paths like: 1.3.6.1.4.1.37662.1.2.3.1.1.x
# However, the actual device firmware uses atsAgent(2), resulting in OID paths:
# 1.3.6.1.4.1.37662.1.2.2.1.1.x
#
# This mismatch was discovered when:
# 1. Querying sysObjectID (1.3.6.1.2.1.1.2.0) returned: 1.3.6.1.4.1.37662.1.2.2.1
# 2. All status queries using MIB-defined OIDs (with atsAgent=3) failed with "noSuchName"
# 3. Debug file analysis showed the device uses atsAgent(2) path structure
#
# SOLUTION:
# ---------
# All ATS status OIDs have been updated to use atsAgent(2) path:
# - OLD (MIB v1.05): 1.3.6.1.4.1.37662.1.2.3.1.1.x
# - NEW (Device):    1.3.6.1.4.1.37662.1.2.2.1.1.x
#
# The code also includes auto-detection logic to check sysObjectID and try both
# paths if needed for backward compatibility.
#
# Base OID: 1.3.6.1.4.1.37662.1.2.2.1.1 (atsObjectGroup with atsAgent=2)
# sysObjectID: 1.3.6.1.4.1.37662.1.2.2.1 (confirmed from device)
# ============================================================================

# ATS Identification Group (atsIdentGroup = 1.3.6.1.4.1.37662.1.2.2.1.1.1)
ATS_IDENT_OIDS = {
    'atsIdentGroupModel': '1.3.6.1.4.1.37662.1.2.2.1.1.1.1.0',              # Model Name
    'atsIdentGroupSerialNumber': '1.3.6.1.4.1.37662.1.2.2.1.1.1.2.0',      # Serial Number
    'atsIdentGroupManufacturer': '1.3.6.1.4.1.37662.1.2.2.1.1.1.3.0',       # Manufacturer
    'atsIdentGroupFirmwareRevision': '1.3.6.1.4.1.37662.1.2.2.1.1.1.4.0',   # Firmware Revision
    'atsIdentGroupAgentFirmwareRevision': '1.3.6.1.4.1.37662.1.2.2.1.1.1.5.0', # Agent Firmware Revision
}

# ATS Input Group (atsInputGroup = 1.3.6.1.4.1.37662.1.2.2.1.1.2)
ATS_INPUT_OIDS = {
    'atsInputGroupPreference': '1.3.6.1.4.1.37662.1.2.2.1.1.2.1.0',         # Output Source Priority
    'atsInputGroupSourceAstatus': '1.3.6.1.4.1.37662.1.2.2.1.1.2.2.0',      # Source A Status (1=fail, 2=ok)
    'atsInputGroupSourceAinputVoltage': '1.3.6.1.4.1.37662.1.2.2.1.1.2.3.0', # Source A Voltage (0.1 V)
    'atsInputGroupSourceAinputFrequency': '1.3.6.1.4.1.37662.1.2.2.1.1.2.4.0', # Source A Frequency (0.1 Hz)
    'atsInputGroupSourceBstatus': '1.3.6.1.4.1.37662.1.2.2.1.1.2.5.0',      # Source B Status (1=fail, 2=ok)
    'atsInputGroupSourceBinputVoltage': '1.3.6.1.4.1.37662.1.2.2.1.1.2.6.0', # Source B Voltage (0.1 V)
    'atsInputGroupSourceBinputFrequency': '1.3.6.1.4.1.37662.1.2.2.1.1.2.7.0', # Source B Frequency (0.1 Hz)
    'atsInputGroupSourceAvoltageUpperLimit': '1.3.6.1.4.1.37662.1.2.2.1.1.2.8.0', # Source A Voltage Upper Limit (0.1 V)
    'atsInputGroupSourceAvoltageLowerLimit': '1.3.6.1.4.1.37662.1.2.2.1.1.2.9.0', # Source A Voltage Lower Limit (0.1 V)
    'atsInputGroupSourceAfrequencyUpperLimit': '1.3.6.1.4.1.37662.1.2.2.1.1.2.10.0', # Source A Frequency Upper Limit (0.1 Hz)
    'atsInputGroupSourceAfrequencyLowerLimit': '1.3.6.1.4.1.37662.1.2.2.1.1.2.11.0', # Source A Frequency Lower Limit (0.1 Hz)
    'atsInputGroupSourceBvoltageUpperLimit': '1.3.6.1.4.1.37662.1.2.2.1.1.2.12.0', # Source B Voltage Upper Limit (0.1 V)
    'atsInputGroupSourceBvoltageLowerLimit': '1.3.6.1.4.1.37662.1.2.2.1.1.2.13.0', # Source B Voltage Lower Limit (0.1 V)
    'atsInputGroupSourceBfrequencyUpperLimit': '1.3.6.1.4.1.37662.1.2.2.1.1.2.14.0', # Source B Frequency Upper Limit (0.1 Hz)
    'atsInputGroupSourceBfrequencyLowerLimit': '1.3.6.1.4.1.37662.1.2.2.1.1.2.15.0', # Source B Frequency Lower Limit (0.1 Hz)
}

# ATS Output Group (atsOutputGroup = 1.3.6.1.4.1.37662.1.2.2.1.1.3)
ATS_OUTPUT_OIDS = {
    'atsOutputGroupOutputSource': '1.3.6.1.4.1.37662.1.2.2.1.1.3.1.0',     # Output Source (Source A/B/Bypass A/B)
    'atsOutputGroupOutputVoltage': '1.3.6.1.4.1.37662.1.2.2.1.1.3.2.0',    # Output Voltage (0.1 V)
    'atsOutputGroupOutputFequency': '1.3.6.1.4.1.37662.1.2.2.1.1.3.3.0',   # Output Frequency (0.1 Hz)
    'atsOutputGroupOutputCurrent': '1.3.6.1.4.1.37662.1.2.2.1.1.3.4.0',    # Output Current (0.1 A)
    'atsOutputGroupLoad': '1.3.6.1.4.1.37662.1.2.2.1.1.3.5.0',             # Output Load (0.1 %)
}

# ATS HMI Switch Group (atsHmiSwitchGroup = 1.3.6.1.4.1.37662.1.2.2.1.1.4)
ATS_HMI_SWITCH_OIDS = {
    'atsHmiSwitchGroupBuzzer': '1.3.6.1.4.1.37662.1.2.2.1.1.4.1.0',        # Buzzer Status (1=disabled, 2=enabled)
    'atsHmiSwitchGroupAtsAlarm': '1.3.6.1.4.1.37662.1.2.2.1.1.4.2.0',      # ATS Alarm (1=nothing, 2=alarm)
    'atsHmiSwitchGroupAutoReturn': '1.3.6.1.4.1.37662.1.2.2.1.1.4.3.0',    # Auto Return (1=off, 2=on)
    'atsHmiSwitchGroupSourceTransferByLoad': '1.3.6.1.4.1.37662.1.2.2.1.1.4.4.0', # Transfer by Load (1=off, 2=on)
    'atsHmiSwitchGroupSourceTransferByPhase': '1.3.6.1.4.1.37662.1.2.2.1.1.4.5.0', # Transfer by Phase (1=off, 2=on)
}

# ATS Miscellaneous Group (atsMiscellaneousGroup = 1.3.6.1.4.1.37662.1.2.2.1.1.5)
ATS_MISC_OIDS = {
    'atsMiscellaneousGroupAtsSystemTemperture': '1.3.6.1.4.1.37662.1.2.2.1.1.5.1.0', # System Temperature (°C)
    'atsMiscellaneousGroupSystemMaxCurrent': '1.3.6.1.4.1.37662.1.2.2.1.1.5.2.0',   # System Max Current (0.1 A)
}

# ATS Base OID for walking entire tree
ATS_BASE_OID = '1.3.6.1.4.1.37662'  # Base ATS enterprise OID
ATS_OBJECT_GROUP_BASE = '1.3.6.1.4.1.37662.1.2.2.1.1'  # atsObjectGroup base (with atsAgent=2)

# ============================================================================
# i-STS MIB Definitions
# Based on i-STS snmp-mib.mib
# Base OID: 43.6.1.4.1.32796 (ISTS enterprise OID)
# Note: The MIB uses 43.6.1.4.1.32796 format (non-standard, may need conversion to 1.3.6.1.4.1.32796)
# ============================================================================

# i-STS Product Information (43.6.1.4.1.32796.1.x)
ISTS_PRODUCT_OIDS = {
    'istsProductName': '43.6.1.4.1.32796.1.1',        # Product Name
    'istsProductVersion': '43.6.1.4.1.32796.1.2',    # Product Version
    'istsVersionDate': '43.6.1.4.1.32796.1.3',       # Version Date
}

# i-STS Control/Operation Variables (43.6.1.4.1.32796.3.1.x)
ISTS_CONTROL_OIDS = {
    'istsActiveSupply': '43.6.1.4.1.32796.3.1.1',     # Active Supply (1=Supply1, 2=Supply2)
    'istsPreferredSupply': '43.6.1.4.1.32796.3.1.2', # Preferred Supply (1=Supply1, 2=Supply2)
    'istsFreq1': '43.6.1.4.1.32796.3.1.3',           # Supply 1 Frequency (0.1 Hz)
    'istsFreq2': '43.6.1.4.1.32796.3.1.4',           # Supply 2 Frequency (0.1 Hz)
    'istsSync': '43.6.1.4.1.32796.3.1.5',            # Sync Status (WORD)
    'istsNeutralI': '43.6.1.4.1.32796.3.1.6',        # Neutral Current (WORD)
}

# i-STS Input Variables (43.6.1.4.1.32796.3.2.x) - SEQUENCE/TABLE
# Note: These are table entries, may need to walk with index
ISTS_INPUT_BASE_OID = '43.6.1.4.1.32796.3.2'  # Base for walking input table

# i-STS Output Variables (43.6.1.4.1.32796.3.3.x) - SEQUENCE/TABLE
ISTS_OUTPUT_BASE_OID = '43.6.1.4.1.32796.3.3'  # Base for walking output table

# i-STS Event Log (43.6.1.4.1.32796.3.4.x) - SEQUENCE/TABLE
ISTS_EVENT_LOG_BASE_OID = '43.6.1.4.1.32796.3.4'  # Base for walking event log table

# i-STS Alarms (43.6.1.4.1.32796.3.5.1)
ISTS_ALARMS_OID = '43.6.1.4.1.32796.3.5.1'  # ALARMS (WORD, bit-mapped)

# i-STS Utilisation/Statistics (43.6.1.4.1.32796.3.6.x)
ISTS_UTILISATION_OIDS = {
    'istsHours1': '43.6.1.4.1.32796.3.6.1',         # Hours on Supply 1 (WORD)
    'istsHours2': '43.6.1.4.1.32796.3.6.2',         # Hours on Supply 2 (WORD)
    'istsHoursPreferred': '43.6.1.4.1.32796.3.6.3', # Hours on Preferred Supply (WORD)
    'istsHoursOperation': '43.6.1.4.1.32796.3.6.4',  # Total Hours of Operation (WORD)
    'istsHoursNoOutput': '43.6.1.4.1.32796.3.6.5',  # Hours with No Output (WORD)
    'istsNumForcedXfers': '43.6.1.4.1.32796.3.6.6', # Number of Forced Transfers (WORD)
    'istsNumSyncLosses': '43.6.1.4.1.32796.3.6.7',   # Number of Sync Losses (WORD)
    'istsLastLoadFault': '43.6.1.4.1.32796.3.6.8',  # Last Load Fault Time (TIME_TICKS)
    'istsNumSupplyOuts': '43.6.1.4.1.32796.3.6.9',  # Number of Supply Outages (WORD)
    'istsLastSupplyOut': '43.6.1.4.1.32796.3.6.10', # Last Supply Out Time (TIME_TICKS)
}

# i-STS Base OID for walking entire tree
ISTS_BASE_OID = '43.6.1.4.1.32796'  # Base i-STS enterprise OID

# ============================================================================
# Enumeration Mappings
# ============================================================================

# Battery Status Enumeration
BATTERY_STATUS = {
    1: 'unknown',
    2: 'batteryNormal',
    3: 'batteryLow',
}

# Line Fail Cause Enumeration
LINE_FAIL_CAUSE = {
    1: 'noTransfer',
    2: 'highLineVoltage',
    3: 'brownout',
    4: 'blackout',
    5: 'smallMomentarySag',
    6: 'deepMomentarySag',
    7: 'smallMomentarySpike',
    8: 'largeMomentarySpike',
}

# Output Status Enumeration
OUTPUT_STATUS = {
    1: 'unknown',
    2: 'onLine',
    3: 'onBattery',
    4: 'onBoost',
    5: 'sleeping',
    6: 'onBypass',
    7: 'rebooting',
    8: 'standBy',
    9: 'onBuck',
}

# Charge Status Enumeration
CHARGE_STATUS = {
    1: 'boost',
    2: 'float',
    3: 'no',
}

# Rectifier Operating Status Enumeration
RECTIFIER_STATUS = {
    1: 'unknown',
    2: 'normal',
    3: 'abnormal',
}

# In/Out Configuration Enumeration
IN_OUT_CONFIG = {
    1: '3-in-1-out',
    2: '3-in-3-out',
}

# Fault Status (typically boolean: 1 = active, 2 = inactive)
FAULT_STATUS = {
    1: 'Active',
    2: 'Inactive',
}

# Source Status Enumeration (for ATS)
SOURCE_STATUS = {
    1: 'fail',
    2: 'ok',
}

# Supply Status Enumeration (for i-STS)
ISTS_SUPPLY_STATUS = {
    1: 'Supply1',
    2: 'Supply2',
}

# Alarm Bit Flags (from MIB comments - bit positions)
# ALARMS is a WORD with bit-mapped fields
ISTS_ALARM_FLAGS = {
    0: 'SUPPLY_1_BAD',
    1: 'SUPPLY_2_BAD',
    2: 'NOT_ON_PREFERRED',
    3: 'SYNC_LOSS',
    4: 'LOAD_FAULT',
    5: 'HIGH_TEMP',
    6: 'FORCED',
}

# ============================================================================
# Helper Functions
# ============================================================================

def get_oid_by_name(oid_name: str, device_type: str = 'ups') -> str:
    """
    Get OID string by name for a given device type.
    
    Args:
        oid_name: OID name (e.g., 'upsIdentModel', 'atsIdentGroupModel')
        device_type: Device type ('ups', 'ats', 'ists')
    
    Returns:
        OID string or None if not found
    
    Example:
        >>> get_oid_by_name('upsIdentModel', 'ups')
        '1.3.6.1.2.1.33.1.1.1.0'
        >>> get_oid_by_name('atsIdentGroupModel', 'ats')
        '1.3.6.1.4.1.37662.1.2.2.1.1.1.1.0'
    """
    oid_mappings = {
        'ups': {
            **UPS_IDENT_OIDS,
            **SMAP_IDENT_OIDS,
            **BATTERY_OIDS,
            **INPUT_OIDS,
            **OUTPUT_OIDS,
            **THREE_PHASE_OIDS,
        },
        'ats': {
            **ATS_IDENT_OIDS,
            **ATS_INPUT_OIDS,
            **ATS_OUTPUT_OIDS,
            **ATS_HMI_SWITCH_OIDS,
            **ATS_MISC_OIDS,
        },
        'ists': {
            **ISTS_PRODUCT_OIDS,
            **ISTS_CONTROL_OIDS,
            **ISTS_UTILISATION_OIDS,
        }
    }
    
    device_oids = oid_mappings.get(device_type.lower(), {})
    return device_oids.get(oid_name)


def get_all_oids_by_device_type(device_type: str) -> dict:
    """
    Get all OIDs for a given device type.
    
    Args:
        device_type: Device type ('ups', 'ats', 'ists')
    
    Returns:
        Dictionary mapping OID names to OID strings
    """
    oid_mappings = {
        'ups': {
            **UPS_IDENT_OIDS,
            **SMAP_IDENT_OIDS,
            **BATTERY_OIDS,
            **INPUT_OIDS,
            **OUTPUT_OIDS,
            **THREE_PHASE_OIDS,
        },
        'ats': {
            **ATS_IDENT_OIDS,
            **ATS_INPUT_OIDS,
            **ATS_OUTPUT_OIDS,
            **ATS_HMI_SWITCH_OIDS,
            **ATS_MISC_OIDS,
        },
        'ists': {
            **ISTS_PRODUCT_OIDS,
            **ISTS_CONTROL_OIDS,
            **ISTS_UTILISATION_OIDS,
        }
    }
    
    return oid_mappings.get(device_type.lower(), {})


def get_oid_group(group_name: str) -> dict:
    """
    Get OID group by name.
    
    Args:
        group_name: Group name (e.g., 'UPS_IDENT_OIDS', 'ATS_INPUT_OIDS')
    
    Returns:
        Dictionary mapping OID names to OID strings
    
    Example:
        >>> get_oid_group('UPS_IDENT_OIDS')
        {'upsIdentModel': '1.3.6.1.2.1.33.1.1.1.0', ...}
    """
    groups = {
        'UPS_IDENT_OIDS': UPS_IDENT_OIDS,
        'SMAP_IDENT_OIDS': SMAP_IDENT_OIDS,
        'BATTERY_OIDS': BATTERY_OIDS,
        'INPUT_OIDS': INPUT_OIDS,
        'OUTPUT_OIDS': OUTPUT_OIDS,
        'THREE_PHASE_OIDS': THREE_PHASE_OIDS,
        'ATS_IDENT_OIDS': ATS_IDENT_OIDS,
        'ATS_INPUT_OIDS': ATS_INPUT_OIDS,
        'ATS_OUTPUT_OIDS': ATS_OUTPUT_OIDS,
        'ATS_HMI_SWITCH_OIDS': ATS_HMI_SWITCH_OIDS,
        'ATS_MISC_OIDS': ATS_MISC_OIDS,
        'ISTS_PRODUCT_OIDS': ISTS_PRODUCT_OIDS,
        'ISTS_CONTROL_OIDS': ISTS_CONTROL_OIDS,
        'ISTS_UTILISATION_OIDS': ISTS_UTILISATION_OIDS,
    }
    
    return groups.get(group_name, {})


def get_enumeration(enum_name: str) -> dict:
    """
    Get enumeration mapping by name.
    
    Args:
        enum_name: Enumeration name (e.g., 'BATTERY_STATUS', 'OUTPUT_STATUS')
    
    Returns:
        Dictionary mapping integer values to string descriptions
    
    Example:
        >>> get_enumeration('BATTERY_STATUS')
        {1: 'unknown', 2: 'batteryNormal', 3: 'batteryLow'}
    """
    enums = {
        'BATTERY_STATUS': BATTERY_STATUS,
        'LINE_FAIL_CAUSE': LINE_FAIL_CAUSE,
        'OUTPUT_STATUS': OUTPUT_STATUS,
        'CHARGE_STATUS': CHARGE_STATUS,
        'RECTIFIER_STATUS': RECTIFIER_STATUS,
        'IN_OUT_CONFIG': IN_OUT_CONFIG,
        'FAULT_STATUS': FAULT_STATUS,
        'SOURCE_STATUS': SOURCE_STATUS,
        'ISTS_SUPPLY_STATUS': ISTS_SUPPLY_STATUS,
        'ISTS_ALARM_FLAGS': ISTS_ALARM_FLAGS,
    }
    
    return enums.get(enum_name, {})

