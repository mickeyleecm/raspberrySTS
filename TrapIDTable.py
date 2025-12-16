"""
Trap ID Table for ATS (Automatic Transfer Switch) SNMP Trap Receiver.

This file contains all trap OID mappings, alarm descriptions, severity levels,
resumption mappings, and event type classifications for ATS_Stork_V1_05 - Borri STS32A.MIB traps.

All alarms are from ATS_Stork_V1_05 - Borri STS32A.MIB file only.
Base OID: 1.3.6.1.4.1.37662.1.2.3.1.2 (atsTrapGroup)

Note: Some OIDs are manually added based on log file analysis when device sends
traps in atsAgent(2) format that are not being recognized after normalization.
These are marked in MANUALLY_ADDED_OIDS list below.
"""


# ATS MIB OID mappings (ATS_Stork_V1_05 - Borri STS32A.MIB only)
# Base OID: 1.3.6.1.4.1.37662.1.2.3.1.2 (atsTrapGroup)
# All alarms are from ATS_Stork_V1_05 - Borri STS32A.MIB file
# Note: Device may send OIDs with .0 suffix (e.g., 1.3.6.1.4.1.37662.1.2.3.1.2.0.4)
# We include both formats for compatibility
UPS_OIDS = {
    # ATS MIB Traps (1.3.6.1.4.1.37662.1.2.3.1.2.x) - Borri STS32A ATS
    # Warning/MAJOR Alarms
    '1.3.6.1.4.1.37662.1.2.3.1.2.1': 'atsAtsAlarm',  # WARNING: ATS Alarm
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.1': 'atsAtsAlarm',  # WARNING: ATS Alarm (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.2': 'atsSourceAvoltageAbnormal',  # WARNING: Source A Voltage Abnormal
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.2': 'atsSourceAvoltageAbnormal',  # WARNING: Source A Voltage Abnormal (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.3': 'atsSourceBvoltageAbnormal',  # WARNING: Source B Voltage Abnormal
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.3': 'atsSourceBvoltageAbnormal',  # WARNING: Source B Voltage Abnormal (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.4': 'atsSourceAfrequencyAbnormal',  # WARNING: Source A Frequency Abnormal
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.4': 'atsSourceAfrequencyAbnormal',  # WARNING: Source A Frequency Abnormal (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.5': 'atsSourceBfrequencyAbnormal',  # WARNING: Source B Frequency Abnormal
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.5': 'atsSourceBfrequencyAbnormal',  # WARNING: Source B Frequency Abnormal (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.9': 'atsOverTemperature',  # WARNING: Cabinet over temperature
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.9': 'atsOverTemperature',  # WARNING: Cabinet over temperature (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.15': 'atsUserSetOverLoad',  # WARNING: User defined load pre-alarm
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.15': 'atsUserSetOverLoad',  # WARNING: User defined load pre-alarm (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.17': 'atsEpoAlarm',  # WARNING: EPO Alarm
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.17': 'atsEpoAlarm',  # WARNING: EPO Alarm (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.38': 'emdmTemperatureTooHighWarn',  # WARNING: EMD Temperature over high set warning point
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.38': 'emdmTemperatureTooHighWarn',  # WARNING: EMD Temperature over high set warning point (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.40': 'emdmTemperatureTooLowWarn',  # WARNING: EMD Temperature under low set warning point
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.40': 'emdmTemperatureTooLowWarn',  # WARNING: EMD Temperature under low set warning point (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.42': 'emdmTemperatureTooHighCrit',  # WARNING: EMD Temperature over high set critical point
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.42': 'emdmTemperatureTooHighCrit',  # WARNING: EMD Temperature over high set critical point (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.44': 'emdmTemperatureTooLowCrit',  # WARNING: EMD Temperature under low set critical point
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.44': 'emdmTemperatureTooLowCrit',  # WARNING: EMD Temperature under low set critical point (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.46': 'emdmHumidityTooHighWarn',  # WARNING: EMD Humidity over high set warning point
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.46': 'emdmHumidityTooHighWarn',  # WARNING: EMD Humidity over high set warning point (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.48': 'emdmHumidityTooLowWarn',  # WARNING: EMD Humidity under low set warning point
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.48': 'emdmHumidityTooLowWarn',  # WARNING: EMD Humidity under low set warning point (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.50': 'emdmHumidityTooHighCrit',  # WARNING: EMD Humidity over high set critical point
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.50': 'emdmHumidityTooHighCrit',  # WARNING: EMD Humidity over high set critical point (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.52': 'emdmHumidityTooLowCrit',  # WARNING: EMD Humidity under low set critical point
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.52': 'emdmHumidityTooLowCrit',  # WARNING: EMD Humidity under low set critical point (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.54': 'emdmAlarm1Active',  # WARNING: EMD Alarm-1 activated
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.54': 'emdmAlarm1Active',  # WARNING: EMD Alarm-1 activated (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.56': 'emdmAlarm2Active',  # WARNING: EMD Alarm-2 activated
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.56': 'emdmAlarm2Active',  # WARNING: EMD Alarm-2 activated (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.58': 'emdmCommunicationLose',  # WARNING: EMD communication lost
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.58': 'emdmCommunicationLose',  # WARNING: EMD communication lost (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.61': 'emdmUpdateFail',  # WARNING: EMD Firmware update fail
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.61': 'emdmUpdateFail',  # WARNING: EMD Firmware update fail (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.68': 'atsLoadOff',  # WARNING: The Load disconnected
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.68': 'atsLoadOff',  # WARNING: The Load disconnected (with .0 suffix)
    
    # Critical/SEVERE Alarms
    '1.3.6.1.4.1.37662.1.2.3.1.2.6': 'atsOutputOverLoad',  # SEVERE: Output Over Load
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.6': 'atsOutputOverLoad',  # SEVERE: Output Over Load (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.7': 'atsWorkPowerAabnormal',  # SEVERE: Unit fault (Working power A abnormal)
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.7': 'atsWorkPowerAabnormal',  # SEVERE: Unit fault (Working power A abnormal) (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.8': 'atsWorkPowerBabnormal',  # SEVERE: Unit fault (Working power B abnormal)
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.8': 'atsWorkPowerBabnormal',  # SEVERE: Unit fault (Working power B abnormal) (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.10': 'atsDcOffsetAbnormal',  # SEVERE: Unit fault (Sensor circuit abnormal)
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.10': 'atsDcOffsetAbnormal',  # SEVERE: Unit fault (Sensor circuit abnormal) (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.11': 'atsEepromAbnormal',  # SEVERE: Unit fault (EEPROM data abnormal)
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.11': 'atsEepromAbnormal',  # SEVERE: Unit fault (EEPROM data abnormal) (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.12': 'atsLcdNotConnect',  # SEVERE: LCD panel connection abnormal
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.12': 'atsLcdNotConnect',  # SEVERE: LCD panel connection abnormal (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.13': 'atsOutputExceedsOverloadTime',  # SEVERE: Overload time out, Output off, Reset needed
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.13': 'atsOutputExceedsOverloadTime',  # SEVERE: Overload time out, Output off, Reset needed (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.14': 'atsInputPhaseDifference',  # SEVERE: Phase difference between resources exceed user defined value, Output off, Reset needed
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.14': 'atsInputPhaseDifference',  # SEVERE: Phase difference between resources exceed user defined value, Output off, Reset needed (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.16': 'atsCommunicationAbnormal',  # SEVERE: Communication connection abnormal
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.16': 'atsCommunicationAbnormal',  # SEVERE: Communication connection abnormal (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.35': 'atsCommunicationLost',  # SEVERE: Communication to the ATS has been lost
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.35': 'atsCommunicationLost',  # SEVERE: Communication to the ATS has been lost (with .0 suffix)
    
    # Informational Alarms (Resumption/State events)
    '1.3.6.1.4.1.37662.1.2.3.1.2.18': 'atsAtsAlarmToNormal',  # INFORMATION: ATS Alarm Normal
    '1.3.6.1.4.1.37662.1.2.3.1.2.19': 'atsSourceAvoltageAbnormalToNormal',  # INFORMATION: Source A Voltage Normal
    '1.3.6.1.4.1.37662.1.2.3.1.2.20': 'atsSourceBvoltageAbnormalToNormal',  # INFORMATION: Source B Voltage Normal
    '1.3.6.1.4.1.37662.1.2.3.1.2.21': 'atsSourceAfrequencyAbnormalToNormal',  # INFORMATION: Source A Frequency Normal
    '1.3.6.1.4.1.37662.1.2.3.1.2.22': 'atsSourceBfrequencyAbnormalToNormal',  # INFORMATION: Source B Frequency Normal
    '1.3.6.1.4.1.37662.1.2.3.1.2.23': 'atsOutputOverLoadToNormal',  # INFORMATION: Output Load Normal
    '1.3.6.1.4.1.37662.1.2.3.1.2.24': 'atsWorkPowerAabnormalToNormal',  # INFORMATION: Unit Normal (Working power A normal)
    '1.3.6.1.4.1.37662.1.2.3.1.2.25': 'atsWorkPowerBabnormalToNormal',  # INFORMATION: Unit Normal (Working power B normal)
    '1.3.6.1.4.1.37662.1.2.3.1.2.26': 'atsOverTemperatureToNormal',  # INFORMATION: Cabinet temperature Normal
    '1.3.6.1.4.1.37662.1.2.3.1.2.27': 'atsDcOffsetAbnormalToNormal',  # INFORMATION: Unit Normal (Sensor circuit normal)
    '1.3.6.1.4.1.37662.1.2.3.1.2.28': 'atsEepromAbnormalToNormal',  # INFORMATION: Unit Normal (EEPROM data normal)
    '1.3.6.1.4.1.37662.1.2.3.1.2.29': 'atsLcdNotConnectToNormal',  # INFORMATION: LCD panel connection normal
    '1.3.6.1.4.1.37662.1.2.3.1.2.30': 'atsOutputExceedsOverloadTimeToNormal',  # INFORMATION: Overload time out Normal
    '1.3.6.1.4.1.37662.1.2.3.1.2.31': 'atsInputPhaseDifferenceToNormal',  # INFORMATION: Input sources return to normal phase
    '1.3.6.1.4.1.37662.1.2.3.1.2.32': 'atsUserSetOverLoadToNormal',  # INFORMATION: User defined load return to Normal
    '1.3.6.1.4.1.37662.1.2.3.1.2.33': 'atsCommunicationToNormal',  # INFORMATION: Communication connection normal
    '1.3.6.1.4.1.37662.1.2.3.1.2.34': 'atsEpoToNormal',  # INFORMATION: EPO Alarm Normal
    '1.3.6.1.4.1.37662.1.2.3.1.2.36': 'atsCommunicationEstablished',  # INFORMATION: Communication with the ATS has been established
    '1.3.6.1.4.1.37662.1.2.3.1.2.37': 'emdmTemperatureNotHighWarn',  # INFORMATION: EMD Temperature not over high set warning point
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.37': 'emdmTemperatureNotHighWarn',  # INFORMATION: EMD Temperature not over high set warning point (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.39': 'emdmTemperatureNotLowWarn',  # INFORMATION: EMD Temperature not under low set warning point
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.39': 'emdmTemperatureNotLowWarn',  # INFORMATION: EMD Temperature not under low set warning point (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.41': 'emdmTemperatureNotHighCrit',  # INFORMATION: EMD Temperature not over high set critical point
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.41': 'emdmTemperatureNotHighCrit',  # INFORMATION: EMD Temperature not over high set critical point (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.43': 'emdmTemperatureNotLowCrit',  # INFORMATION: EMD Temperature not under low set critical point
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.43': 'emdmTemperatureNotLowCrit',  # INFORMATION: EMD Temperature not under low set critical point (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.45': 'emdmHumidityNotHighWarn',  # INFORMATION: EMD Humidity not over high set warning point
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.45': 'emdmHumidityNotHighWarn',  # INFORMATION: EMD Humidity not over high set warning point (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.47': 'emdmHumidityNotLowWarn',  # INFORMATION: EMD Humidity not under low set warning point
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.47': 'emdmHumidityNotLowWarn',  # INFORMATION: EMD Humidity not under low set warning point (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.49': 'emdmHumidityNotHighCrit',  # INFORMATION: EMD Humidity not over high set critical point
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.49': 'emdmHumidityNotHighCrit',  # INFORMATION: EMD Humidity not over high set critical point (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.51': 'emdmHumidityNotLowCrit',  # INFORMATION: EMD Humidity not under low set critical point
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.51': 'emdmHumidityNotLowCrit',  # INFORMATION: EMD Humidity not under low set critical point (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.53': 'emdmAlarm1Normal',  # INFORMATION: EMD Alarm-1 not active
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.53': 'emdmAlarm1Normal',  # INFORMATION: EMD Alarm-1 not active (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.55': 'emdmAlarm2Normal',  # INFORMATION: EMD Alarm-2 not active
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.55': 'emdmAlarm2Normal',  # INFORMATION: EMD Alarm-2 not active (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.57': 'emdmCommunicationSuccess',  # INFORMATION: EMD communication succeeded
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.57': 'emdmCommunicationSuccess',  # INFORMATION: EMD communication succeeded (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.59': 'emdLogClear',  # INFORMATION: EMD history log cleared
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.59': 'emdLogClear',  # INFORMATION: EMD history log cleared (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.60': 'emdmUpdateSuccess',  # INFORMATION: EMD Firmware update success
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.60': 'emdmUpdateSuccess',  # INFORMATION: EMD Firmware update success (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.62': 'atsLoadOnSourceA',  # INFORMATION: The Load is supplied by Source A
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.62': 'atsLoadOnSourceA',  # INFORMATION: The Load is supplied by Source A (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.63': 'atsLoadOnSourceB',  # INFORMATION: The Load is supplied by Source B
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.63': 'atsLoadOnSourceB',  # INFORMATION: The Load is supplied by Source B (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.64': 'atsSourceAPreferred',  # INFORMATION: Source A set as preferred source
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.64': 'atsSourceAPreferred',  # INFORMATION: Source A set as preferred source (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.65': 'atsSourceBPreferred',  # INFORMATION: Source B set as preferred source
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.65': 'atsSourceBPreferred',  # INFORMATION: Source B set as preferred source (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.66': 'atsLoadOnBypassA',  # INFORMATION: The Load is supplied by Bypass A
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.66': 'atsLoadOnBypassA',  # INFORMATION: The Load is supplied by Bypass A (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.67': 'atsLoadOnBypassB',  # INFORMATION: The Load is supplied by Bypass B
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.67': 'atsLoadOnBypassB',  # INFORMATION: The Load is supplied by Bypass B (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.69': 'atsSendTestTrapEvent',  # INFORMATION: Send test trap
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.69': 'atsSendTestTrapEvent',  # INFORMATION: Send test trap (with .0 suffix)
    '1.3.6.1.4.1.37662.1.2.3.1.2.70': 'atsSendTestMailEvent',  # INFORMATION: Send test mail
    '1.3.6.1.4.1.37662.1.2.3.1.2.0.70': 'atsSendTestMailEvent',  # INFORMATION: Send test mail (with .0 suffix)
    
    # ============================================================================
    # MANUALLY ADDED OIDs (not from MIB file, discovered from log file analysis)
    # These OIDs are in atsAgent(2) format that device sends but normalization
    # may not always work correctly. Added based on log file: logs/ups_traps20251209.log
    # ============================================================================
    # Note: Variable bindings show messages that help identify the correct trap mapping
    # Warning/MAJOR Alarms (atsAgent=2 format)
    '1.3.6.1.4.1.37662.1.2.2.1.2.1': 'atsAtsAlarm',  # WARNING: ATS Alarm (atsAgent=2, message: "ATS Alarm")
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.1': 'atsAtsAlarm',  # WARNING: ATS Alarm (atsAgent=2 with .0 suffix, message: "ATS Alarm")
    '1.3.6.1.4.1.37662.1.2.2.1.2.2': 'atsSourceAvoltageAbnormal',  # WARNING: Source A Voltage Abnormal (atsAgent=2, message: "Source A Voltage Abnormal")
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.2': 'atsSourceAvoltageAbnormal',  # WARNING: Source A Voltage Abnormal (atsAgent=2 with .0 suffix, message: "Source A Voltage Abnormal")
    '1.3.6.1.4.1.37662.1.2.2.1.2.3': 'atsSourceBvoltageAbnormal',  # WARNING: Source B Voltage Abnormal (atsAgent=2, message: "Source B Voltage Abnormal")
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.3': 'atsSourceBvoltageAbnormal',  # WARNING: Source B Voltage Abnormal (atsAgent=2 with .0 suffix, message: "Source B Voltage Abnormal")
    '1.3.6.1.4.1.37662.1.2.2.1.2.4': 'atsSourceAfrequencyAbnormal',  # WARNING: Source A Frequency Abnormal (atsAgent=2, message: "Source A Frequency Abnormal")
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.4': 'atsSourceAfrequencyAbnormal',  # WARNING: Source A Frequency Abnormal (atsAgent=2 with .0 suffix, message: "Source A Frequency Abnormal")
    '1.3.6.1.4.1.37662.1.2.2.1.2.5': 'atsSourceBfrequencyAbnormal',  # WARNING: Source B Frequency Abnormal (atsAgent=2, message: "Source B Frequency Abnormal")
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.5': 'atsSourceBfrequencyAbnormal',  # WARNING: Source B Frequency Abnormal (atsAgent=2 with .0 suffix, message: "Source B Frequency Abnormal")
    
    # Informational/Resumption events (atsAgent=2 format)
    # Note: Device sends trap numbers that don't match MIB exactly - using message content to identify correct trap
    # OID 0.16 with message "ATS Normal" - device sends trap 16 but message indicates atsAtsAlarmToNormal (trap 18)
    '1.3.6.1.4.1.37662.1.2.2.1.2.16': 'atsCommunicationAbnormal',  # SEVERE: Communication connection abnormal (atsAgent=2, but message may say "ATS Normal" - device inconsistency)
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.16': 'atsAtsAlarmToNormal',  # INFORMATION: ATS Alarm Normal (atsAgent=2 with .0 suffix, message: "ATS Normal" - device sends trap 16 but message indicates trap 18)
    '1.3.6.1.4.1.37662.1.2.2.1.2.17': 'atsSourceAvoltageAbnormalToNormal',  # INFORMATION: Source A Voltage Normal (atsAgent=2, message: "Source A Voltage Normal")
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.17': 'atsSourceAvoltageAbnormalToNormal',  # INFORMATION: Source A Voltage Normal (atsAgent=2 with .0 suffix, message: "Source A Voltage Normal")
    '1.3.6.1.4.1.37662.1.2.2.1.2.18': 'atsSourceBvoltageAbnormalToNormal',  # INFORMATION: Source B Voltage Normal (atsAgent=2, message: "Source B Voltage Normal")
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.18': 'atsSourceBvoltageAbnormalToNormal',  # INFORMATION: Source B Voltage Normal (atsAgent=2 with .0 suffix, message: "Source B Voltage Normal")
    '1.3.6.1.4.1.37662.1.2.2.1.2.19': 'atsSourceAfrequencyAbnormalToNormal',  # INFORMATION: Source A Frequency Normal (atsAgent=2, message: "Source A Frequency Normal" - device sends trap 19 but MIB says trap 21)
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.19': 'atsSourceAfrequencyAbnormalToNormal',  # INFORMATION: Source A Frequency Normal (atsAgent=2 with .0 suffix, message: "Source A Frequency Normal" - device sends trap 19 but MIB says trap 21)
    '1.3.6.1.4.1.37662.1.2.2.1.2.20': 'atsSourceBvoltageAbnormalToNormal',  # INFORMATION: Source B Voltage Normal (atsAgent=2, message: "Source B Voltage Normal" - device sends trap 20, matches MIB trap 20)
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.20': 'atsSourceBvoltageAbnormalToNormal',  # INFORMATION: Source B Voltage Normal (atsAgent=2 with .0 suffix, message: "Source B Voltage Normal" - device sends trap 20, matches MIB trap 20)
    '1.3.6.1.4.1.37662.1.2.2.1.2.21': 'atsSourceAfrequencyAbnormalToNormal',  # INFORMATION: Source A Frequency Normal (atsAgent=2, message: "Source A Frequency Normal" - matches MIB trap 21)
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.21': 'atsSourceAfrequencyAbnormalToNormal',  # INFORMATION: Source A Frequency Normal (atsAgent=2 with .0 suffix, message: "Source A Frequency Normal" - matches MIB trap 21)
    '1.3.6.1.4.1.37662.1.2.2.1.2.22': 'atsSourceBfrequencyAbnormalToNormal',  # INFORMATION: Source B Frequency Normal (atsAgent=2, message: "Source B Frequency Normal" - matches MIB trap 22)
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.22': 'atsSourceBfrequencyAbnormalToNormal',  # INFORMATION: Source B Frequency Normal (atsAgent=2 with .0 suffix, message: "Source B Frequency Normal" - matches MIB trap 22)
}

# List of OIDs that were manually added (not from MIB file)
# These were discovered from log file analysis when device sends traps in atsAgent(2) format
# that are not being recognized after normalization
MANUALLY_ADDED_OIDS = [
    # atsAgent(2) format OIDs (device firmware uses atsAgent(2) instead of atsAgent(3))
    '1.3.6.1.4.1.37662.1.2.2.1.2.1',
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.1',
    '1.3.6.1.4.1.37662.1.2.2.1.2.2',
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.2',
    '1.3.6.1.4.1.37662.1.2.2.1.2.3',
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.3',
    '1.3.6.1.4.1.37662.1.2.2.1.2.4',
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.4',
    '1.3.6.1.4.1.37662.1.2.2.1.2.5',
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.5',
    '1.3.6.1.4.1.37662.1.2.2.1.2.16',
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.16',  # Note: Device sends trap 16 but message says "ATS Normal" (trap 18) - mapped to atsAtsAlarmToNormal
    '1.3.6.1.4.1.37662.1.2.2.1.2.17',
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.17',
    '1.3.6.1.4.1.37662.1.2.2.1.2.18',
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.18',
    '1.3.6.1.4.1.37662.1.2.2.1.2.19',  # Note: Device sends trap 19 but message says "Source A Frequency Normal" (trap 21) - mapped to atsSourceAfrequencyAbnormalToNormal
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.19',  # Note: Device sends trap 19 but message says "Source A Frequency Normal" (trap 21) - mapped to atsSourceAfrequencyAbnormalToNormal
    '1.3.6.1.4.1.37662.1.2.2.1.2.20',
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.20',
    '1.3.6.1.4.1.37662.1.2.2.1.2.21',
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.21',
    '1.3.6.1.4.1.37662.1.2.2.1.2.22',
    '1.3.6.1.4.1.37662.1.2.2.1.2.0.22',
]

# Common alarm descriptions (from ATS_Stork_V1_05 - Borri STS32A.MIB only)
ALARM_DESCRIPTIONS = {
    # ATS MIB - Warning/MAJOR Alarms
    'atsAtsAlarm': 'WARNING: ATS Alarm.',
    'atsSourceAvoltageAbnormal': 'WARNING: Source A Voltage Abnormal.',
    'atsSourceBvoltageAbnormal': 'WARNING: Source B Voltage Abnormal.',
    'atsSourceAfrequencyAbnormal': 'WARNING: Source A Frequency Abnormal.',
    'atsSourceBfrequencyAbnormal': 'WARNING: Source B Frequency Abnormal.',
    'atsOverTemperature': 'WARNING: Cabinet over temperature.',
    'atsUserSetOverLoad': 'WARNING: User defined load pre-alarm.',
    'atsEpoAlarm': 'WARNING: EPO Alarm.',
    'emdmTemperatureTooHighWarn': 'WARNING: EMD Temperature over high set warning point.',
    'emdmTemperatureTooLowWarn': 'WARNING: EMD Temperature under low set warning point.',
    'emdmTemperatureTooHighCrit': 'WARNING: EMD Temperature over high set critical point.',
    'emdmTemperatureTooLowCrit': 'WARNING: EMD Temperature under low set critical point.',
    'emdmHumidityTooHighWarn': 'WARNING: EMD Humidity over high set warning point.',
    'emdmHumidityTooLowWarn': 'WARNING: EMD Humidity under low set warning point.',
    'emdmHumidityTooHighCrit': 'WARNING: EMD Humidity over high set critical point.',
    'emdmHumidityTooLowCrit': 'WARNING: EMD Humidity under low set critical point.',
    'emdmAlarm1Active': 'WARNING: EMD Alarm-1 activated.',
    'emdmAlarm2Active': 'WARNING: EMD Alarm-2 activated.',
    'emdmCommunicationLose': 'WARNING: EMD communication lost.',
    'emdmUpdateFail': 'WARNING: EMD Firmware update fail.',
    'atsLoadOff': 'WARNING: The Load disconnected.',
    
    # ATS MIB - Critical/SEVERE Alarms
    'atsOutputOverLoad': 'SEVERE: Output Over Load.',
    'atsWorkPowerAabnormal': 'SEVERE: Unit fault (Working power A abnormal).',
    'atsWorkPowerBabnormal': 'SEVERE: Unit fault (Working power B abnormal).',
    'atsDcOffsetAbnormal': 'SEVERE: Unit fault (Sensor circuit abnormal).',
    'atsEepromAbnormal': 'SEVERE: Unit fault (EEPROM data abnormal).',
    'atsLcdNotConnect': 'SEVERE: LCD panel connection abnormal.',
    'atsOutputExceedsOverloadTime': 'SEVERE: Overload time out, Output off, Reset needed.',
    'atsInputPhaseDifference': 'SEVERE: Phase difference between resources exceed user defined value, Output off, Reset needed.',
    'atsCommunicationAbnormal': 'SEVERE: Communication connection abnormal.',
    'atsCommunicationLost': 'SEVERE: Communication to the ATS has been lost.',
    
    # ATS MIB - Informational Alarms
    'atsAtsAlarmToNormal': 'INFORMATION: ATS Alarm Normal.',
    'atsSourceAvoltageAbnormalToNormal': 'INFORMATION: Source A Voltage Normal.',
    'atsSourceBvoltageAbnormalToNormal': 'INFORMATION: Source B Voltage Normal.',
    'atsSourceAfrequencyAbnormalToNormal': 'INFORMATION: Source A Frequency Normal.',
    'atsSourceBfrequencyAbnormalToNormal': 'INFORMATION: Source B Frequency Normal.',
    'atsOutputOverLoadToNormal': 'INFORMATION: Output Load Normal.',
    'atsWorkPowerAabnormalToNormal': 'INFORMATION: Unit Normal (Working power A normal).',
    'atsWorkPowerBabnormalToNormal': 'INFORMATION: Unit Normal (Working power B normal).',
    'atsOverTemperatureToNormal': 'INFORMATION: Cabinet temperature Normal.',
    'atsDcOffsetAbnormalToNormal': 'INFORMATION: Unit Normal (Sensor circuit normal).',
    'atsEepromAbnormalToNormal': 'INFORMATION: Unit Normal (EEPROM data normal).',
    'atsLcdNotConnectToNormal': 'INFORMATION: LCD panel connection normal.',
    'atsOutputExceedsOverloadTimeToNormal': 'INFORMATION: Overload time out Normal.',
    'atsInputPhaseDifferenceToNormal': 'INFORMATION: Input sources return to normal phase.',
    'atsUserSetOverLoadToNormal': 'INFORMATION: User defined load return to Normal.',
    'atsCommunicationToNormal': 'INFORMATION: Communication connection normal.',
    'atsEpoToNormal': 'INFORMATION: EPO Alarm Normal.',
    'atsCommunicationEstablished': 'INFORMATION: Communication with the ATS has been established.',
    'emdmTemperatureNotHighWarn': 'INFORMATION: EMD Temperature not over high set warning point.',
    'emdmTemperatureNotLowWarn': 'INFORMATION: EMD Temperature not under low set warning point.',
    'emdmTemperatureNotHighCrit': 'INFORMATION: EMD Temperature not over high set critical point.',
    'emdmTemperatureNotLowCrit': 'INFORMATION: EMD Temperature not under low set critical point.',
    'emdmHumidityNotHighWarn': 'INFORMATION: EMD Humidity not over high set warning point.',
    'emdmHumidityNotLowWarn': 'INFORMATION: EMD Humidity not under low set warning point.',
    'emdmHumidityNotHighCrit': 'INFORMATION: EMD Humidity not over high set critical point.',
    'emdmHumidityNotLowCrit': 'INFORMATION: EMD Humidity not under low set critical point.',
    'emdmAlarm1Normal': 'INFORMATION: EMD Alarm-1 not active.',
    'emdmAlarm2Normal': 'INFORMATION: EMD Alarm-2 not active.',
    'emdmCommunicationSuccess': 'INFORMATION: EMD communication succeeded.',
    'emdLogClear': 'INFORMATION: EMD history log cleared.',
    'emdmUpdateSuccess': 'INFORMATION: EMD Firmware update success.',
    'atsLoadOnSourceA': 'INFORMATION: The Load is supplied by Source A.',
    'atsLoadOnSourceB': 'INFORMATION: The Load is supplied by Source B.',
    'atsSourceAPreferred': 'INFORMATION: Source A set as preferred source.',
    'atsSourceBPreferred': 'INFORMATION: Source B set as preferred source.',
    'atsLoadOnBypassA': 'INFORMATION: The Load is supplied by Bypass A.',
    'atsLoadOnBypassB': 'INFORMATION: The Load is supplied by Bypass B.',
    'atsSendTestTrapEvent': 'INFORMATION: Send test trap.',
    'atsSendTestMailEvent': 'INFORMATION: Send test mail.',
}

# Battery-related OID patterns (for vendor-specific MIBs)
# Note: ATS is a Static Transfer Switch, not a UPS, so battery patterns may not apply
# Keeping for compatibility with existing code
BATTERY_OID_PATTERNS = [
    '1.3.6.1.2.1.33.1.2',  # RFC 1628 upsBattery group
    '1.3.6.1.4.1.318.1.1.1.2',  # APC PowerNet MIB battery
    '1.3.6.1.4.1.534.1',  # Eaton XUPS MIB
    '1.3.6.1.4.1.935.1.1.1.2',  # SMAP/PPC upsBatteryp group
    '1.3.6.1.4.1.37662.1.2.3.1.2',  # ATS Trap Group (may contain load fault info)
]

# Alarm severity levels for GPIO LED control (from ATS_Stork_V1_05 - Borri STS32A.MIB only)
ALARM_SEVERITY = {
    # ATS MIB - Warning/MAJOR Alarms (WARNING severity)
    'atsAtsAlarm': 'warning',
    'atsSourceAvoltageAbnormal': 'warning',
    'atsSourceBvoltageAbnormal': 'warning',
    'atsSourceAfrequencyAbnormal': 'warning',
    'atsSourceBfrequencyAbnormal': 'warning',
    'atsOverTemperature': 'warning',
    'atsUserSetOverLoad': 'warning',
    'atsEpoAlarm': 'warning',
    'emdmTemperatureTooHighWarn': 'warning',
    'emdmTemperatureTooLowWarn': 'warning',
    'emdmTemperatureTooHighCrit': 'warning',
    'emdmTemperatureTooLowCrit': 'warning',
    'emdmHumidityTooHighWarn': 'warning',
    'emdmHumidityTooLowWarn': 'warning',
    'emdmHumidityTooHighCrit': 'warning',
    'emdmHumidityTooLowCrit': 'warning',
    'emdmAlarm1Active': 'warning',
    'emdmAlarm2Active': 'warning',
    'emdmCommunicationLose': 'warning',
    'emdmUpdateFail': 'warning',
    'atsLoadOff': 'warning',
    
    # ATS MIB - Critical/SEVERE Alarms (CRITICAL severity)
    'atsOutputOverLoad': 'critical',
    'atsWorkPowerAabnormal': 'critical',
    'atsWorkPowerBabnormal': 'critical',
    'atsDcOffsetAbnormal': 'critical',
    'atsEepromAbnormal': 'critical',
    'atsLcdNotConnect': 'critical',
    'atsOutputExceedsOverloadTime': 'critical',
    'atsInputPhaseDifference': 'critical',
    'atsCommunicationAbnormal': 'critical',
    'atsCommunicationLost': 'critical',
    
    # ATS MIB - Informational Alarms (INFO severity)
    'atsAtsAlarmToNormal': 'info',
    'atsSourceAvoltageAbnormalToNormal': 'info',
    'atsSourceBvoltageAbnormalToNormal': 'info',
    'atsSourceAfrequencyAbnormalToNormal': 'info',
    'atsSourceBfrequencyAbnormalToNormal': 'info',
    'atsOutputOverLoadToNormal': 'info',
    'atsWorkPowerAabnormalToNormal': 'info',
    'atsWorkPowerBabnormalToNormal': 'info',
    'atsOverTemperatureToNormal': 'info',
    'atsDcOffsetAbnormalToNormal': 'info',
    'atsEepromAbnormalToNormal': 'info',
    'atsLcdNotConnectToNormal': 'info',
    'atsOutputExceedsOverloadTimeToNormal': 'info',
    'atsInputPhaseDifferenceToNormal': 'info',
    'atsUserSetOverLoadToNormal': 'info',
    'atsCommunicationToNormal': 'info',
    'atsEpoToNormal': 'info',
    'atsCommunicationEstablished': 'info',
    'emdmTemperatureNotHighWarn': 'info',
    'emdmTemperatureNotLowWarn': 'info',
    'emdmTemperatureNotHighCrit': 'info',
    'emdmTemperatureNotLowCrit': 'info',
    'emdmHumidityNotHighWarn': 'info',
    'emdmHumidityNotLowWarn': 'info',
    'emdmHumidityNotHighCrit': 'info',
    'emdmHumidityNotLowCrit': 'info',
    'emdmAlarm1Normal': 'info',
    'emdmAlarm2Normal': 'info',
    'emdmCommunicationSuccess': 'info',
    'emdLogClear': 'info',
    'emdmUpdateSuccess': 'info',
    'atsLoadOnSourceA': 'info',
    'atsLoadOnSourceB': 'info',
    'atsSourceAPreferred': 'info',
    'atsSourceBPreferred': 'info',
    'atsLoadOnBypassA': 'info',
    'atsLoadOnBypassB': 'info',
    'atsSendTestTrapEvent': 'info',
    'atsSendTestMailEvent': 'info',
}

# Alarm trigger to resumption mapping
# Maps alarm trigger names to their corresponding resumption/clear event names
# This allows the system to know which alarm is being cleared when a resumption event occurs
ALARM_RESUMPTION_MAP = {
    # Alarm Trigger → Resumption Event
    'atsAtsAlarm': 'atsAtsAlarmToNormal',  # ATS Alarm → ATS Alarm Normal
    'atsSourceAvoltageAbnormal': 'atsSourceAvoltageAbnormalToNormal',  # Source A Voltage Abnormal → Source A Voltage Normal
    'atsSourceBvoltageAbnormal': 'atsSourceBvoltageAbnormalToNormal',  # Source B Voltage Abnormal → Source B Voltage Normal
    'atsSourceAfrequencyAbnormal': 'atsSourceAfrequencyAbnormalToNormal',  # Source A Frequency Abnormal → Source A Frequency Normal
    'atsSourceBfrequencyAbnormal': 'atsSourceBfrequencyAbnormalToNormal',  # Source B Frequency Abnormal → Source B Frequency Normal
    'atsOutputOverLoad': 'atsOutputOverLoadToNormal',  # Output Over Load → Output Load Normal
    'atsWorkPowerAabnormal': 'atsWorkPowerAabnormalToNormal',  # Working power A abnormal → Working power A normal
    'atsWorkPowerBabnormal': 'atsWorkPowerBabnormalToNormal',  # Working power B abnormal → Working power B normal
    'atsOverTemperature': 'atsOverTemperatureToNormal',  # Over temperature → Temperature Normal
    'atsDcOffsetAbnormal': 'atsDcOffsetAbnormalToNormal',  # DC Offset abnormal → DC Offset normal
    'atsEepromAbnormal': 'atsEepromAbnormalToNormal',  # EEPROM abnormal → EEPROM normal
    'atsLcdNotConnect': 'atsLcdNotConnectToNormal',  # LCD not connect → LCD connection normal
    'atsOutputExceedsOverloadTime': 'atsOutputExceedsOverloadTimeToNormal',  # Overload time out → Overload time out Normal
    'atsInputPhaseDifference': 'atsInputPhaseDifferenceToNormal',  # Phase difference → Phase normal
    'atsUserSetOverLoad': 'atsUserSetOverLoadToNormal',  # User set overload → User set load Normal
    'atsCommunicationAbnormal': 'atsCommunicationToNormal',  # Communication abnormal → Communication normal
    'atsCommunicationLost': 'atsCommunicationEstablished',  # Communication lost → Communication established
    'atsEpoAlarm': 'atsEpoToNormal',  # EPO Alarm → EPO Alarm Normal
    'emdmTemperatureTooHighWarn': 'emdmTemperatureNotHighWarn',  # Temp too high warn → Temp not high warn
    'emdmTemperatureTooLowWarn': 'emdmTemperatureNotLowWarn',  # Temp too low warn → Temp not low warn
    'emdmTemperatureTooHighCrit': 'emdmTemperatureNotHighCrit',  # Temp too high crit → Temp not high crit
    'emdmTemperatureTooLowCrit': 'emdmTemperatureNotLowCrit',  # Temp too low crit → Temp not low crit
    'emdmHumidityTooHighWarn': 'emdmHumidityNotHighWarn',  # Humidity too high warn → Humidity not high warn
    'emdmHumidityTooLowWarn': 'emdmHumidityNotLowWarn',  # Humidity too low warn → Humidity not low warn
    'emdmHumidityTooHighCrit': 'emdmHumidityNotHighCrit',  # Humidity too high crit → Humidity not high crit
    'emdmHumidityTooLowCrit': 'emdmHumidityNotLowCrit',  # Humidity too low crit → Humidity not low crit
    'emdmAlarm1Active': 'emdmAlarm1Normal',  # EMD Alarm-1 active → EMD Alarm-1 normal
    'emdmAlarm2Active': 'emdmAlarm2Normal',  # EMD Alarm-2 active → EMD Alarm-2 normal
    'emdmCommunicationLose': 'emdmCommunicationSuccess',  # EMD communication lose → EMD communication success
}

# Reverse mapping: Resumption Event → Alarm Trigger(s)
# This allows finding which alarm(s) should be cleared when a resumption event occurs
RESUMPTION_TO_ALARM_MAP = {}
for alarm, resumption in ALARM_RESUMPTION_MAP.items():
    if resumption not in RESUMPTION_TO_ALARM_MAP:
        RESUMPTION_TO_ALARM_MAP[resumption] = []
    RESUMPTION_TO_ALARM_MAP[resumption].append(alarm)

# Alarm event type classification
# 'trigger' = alarm is occurring/starting
# 'resumption' = alarm is clearing/returning to normal
# 'state' = informational state change (not necessarily alarm/resumption)
ALARM_EVENT_TYPE = {
    # Trigger events (alarms starting)
    'atsAtsAlarm': 'trigger',
    'atsSourceAvoltageAbnormal': 'trigger',
    'atsSourceBvoltageAbnormal': 'trigger',
    'atsSourceAfrequencyAbnormal': 'trigger',
    'atsSourceBfrequencyAbnormal': 'trigger',
    'atsOutputOverLoad': 'trigger',
    'atsWorkPowerAabnormal': 'trigger',
    'atsWorkPowerBabnormal': 'trigger',
    'atsOverTemperature': 'trigger',
    'atsDcOffsetAbnormal': 'trigger',
    'atsEepromAbnormal': 'trigger',
    'atsLcdNotConnect': 'trigger',
    'atsOutputExceedsOverloadTime': 'trigger',
    'atsInputPhaseDifference': 'trigger',
    'atsUserSetOverLoad': 'trigger',
    'atsCommunicationAbnormal': 'trigger',
    'atsCommunicationLost': 'trigger',
    'atsEpoAlarm': 'trigger',
    'emdmTemperatureTooHighWarn': 'trigger',
    'emdmTemperatureTooLowWarn': 'trigger',
    'emdmTemperatureTooHighCrit': 'trigger',
    'emdmTemperatureTooLowCrit': 'trigger',
    'emdmHumidityTooHighWarn': 'trigger',
    'emdmHumidityTooLowWarn': 'trigger',
    'emdmHumidityTooHighCrit': 'trigger',
    'emdmHumidityTooLowCrit': 'trigger',
    'emdmAlarm1Active': 'trigger',
    'emdmAlarm2Active': 'trigger',
    'emdmCommunicationLose': 'trigger',
    'emdmUpdateFail': 'trigger',
    'atsLoadOff': 'trigger',
    
    # Resumption events (alarms clearing)
    'atsAtsAlarmToNormal': 'resumption',
    'atsSourceAvoltageAbnormalToNormal': 'resumption',
    'atsSourceBvoltageAbnormalToNormal': 'resumption',
    'atsSourceAfrequencyAbnormalToNormal': 'resumption',
    'atsSourceBfrequencyAbnormalToNormal': 'resumption',
    'atsOutputOverLoadToNormal': 'resumption',
    'atsWorkPowerAabnormalToNormal': 'resumption',
    'atsWorkPowerBabnormalToNormal': 'resumption',
    'atsOverTemperatureToNormal': 'resumption',
    'atsDcOffsetAbnormalToNormal': 'resumption',
    'atsEepromAbnormalToNormal': 'resumption',
    'atsLcdNotConnectToNormal': 'resumption',
    'atsOutputExceedsOverloadTimeToNormal': 'resumption',
    'atsInputPhaseDifferenceToNormal': 'resumption',
    'atsUserSetOverLoadToNormal': 'resumption',
    'atsCommunicationToNormal': 'resumption',
    'atsEpoToNormal': 'resumption',
    'atsCommunicationEstablished': 'resumption',
    'emdmTemperatureNotHighWarn': 'resumption',
    'emdmTemperatureNotLowWarn': 'resumption',
    'emdmTemperatureNotHighCrit': 'resumption',
    'emdmTemperatureNotLowCrit': 'resumption',
    'emdmHumidityNotHighWarn': 'resumption',
    'emdmHumidityNotLowWarn': 'resumption',
    'emdmHumidityNotHighCrit': 'resumption',
    'emdmHumidityNotLowCrit': 'resumption',
    'emdmAlarm1Normal': 'resumption',
    'emdmAlarm2Normal': 'resumption',
    'emdmCommunicationSuccess': 'resumption',
    
    # State events (informational, not alarm/resumption)
    'atsLoadOnSourceA': 'state',
    'atsLoadOnSourceB': 'state',
    'atsSourceAPreferred': 'state',
    'atsSourceBPreferred': 'state',
    'atsLoadOnBypassA': 'state',
    'atsLoadOnBypassB': 'state',
    'atsSendTestTrapEvent': 'state',
    'atsSendTestMailEvent': 'state',
    'emdLogClear': 'state',
    'emdmUpdateSuccess': 'state',
}

# Alarm to LED mapping (based on AlarmMap.py PANEL_LED_MAPPING)
# Maps alarm trap names to LED actions for panel LED control
# Format: 
#   - Simple format: {trap_name: led_number} - only enables the LED
#   - Advanced format: {trap_name: {'disable_led': led_number, 'enable_led': led_number}} - disables one LED and enables another
# LED numbers reference:
#   LED 1: Source 1 voltage fault detection (Red) - MBP1 Fault
#   LED 2: Source 1 voltage normal status (Green) - MBP1 Normal
#   LED 4: Source 2 voltage normal status (Green) - MBP2 Normal
#   LED 5: Source 2 voltage fault detection (Red) - MBP2 Fault
#   LED 8: Overall system operating status (Green) - SYSTEM OK
#   LED 10: Critical alarm / fault condition (Red) - ALARM
#   LED 11: Load overload warning signal (Red) - LOAD Overload
#   LED 12: Load normal status middle (Green) - LOAD Normal Middle
ALARM_TO_LED_MAP = {
    # Source A (Source 1) voltage faults -> disable LED 2 (normal), enable LED 10 (alarm)
    'atsSourceAvoltageAbnormal': {'disable_led': [2,6,8,3], 'enable_led': 10},
    # Source A (Source 1) frequency faults -> disable LED 2 (normal) and LED 6 (Source 1 active), enable LED 10 (alarm)
    'atsSourceAfrequencyAbnormal': {'disable_led': [2,6,8,3], 'enable_led': 10},
    
    # Source B (Source 2) voltage/frequency faults -> disable LED 4 (normal), enable LED 5 (fault - Red)
    'atsSourceBvoltageAbnormal': {'disable_led': [4,7,8,3], 'enable_led': 10},
    'atsSourceBfrequencyAbnormal': {'disable_led': [4,7,8,3], 'enable_led': 10},
    
    # Load overload alarms -> LED 11 (Load overload warning signal - Red)
    'atsOutputOverLoad': 11,
    'atsUserSetOverLoad': 11,
    'atsOutputExceedsOverloadTime': 11,
    
    # General critical alarms -> LED 10 (Critical alarm / fault condition - Red)
    'atsAtsAlarm': 10,
    'atsWorkPowerAabnormal': 10,
    'atsWorkPowerBabnormal': 10,
    'atsDcOffsetAbnormal': 10,
    'atsEepromAbnormal': 10,
    'atsLcdNotConnect': 10,
    'atsInputPhaseDifference': 10,
    'atsCommunicationAbnormal': 10,
    'atsCommunicationLost': 10,
    'atsOverTemperature': 10,
    'atsEpoAlarm': 10,
    'atsLoadOff': 10,
    
    # EMD alarms -> LED 10 (general alarm LED)
    'emdmTemperatureTooHighWarn': 10,
    'emdmTemperatureTooLowWarn': 10,
    'emdmTemperatureTooHighCrit': 10,
    'emdmTemperatureTooLowCrit': 10,
    'emdmHumidityTooHighWarn': 10,
    'emdmHumidityTooLowWarn': 10,
    'emdmHumidityTooHighCrit': 10,
    'emdmHumidityTooLowCrit': 10,
    'emdmAlarm1Active': 10,
    'emdmAlarm2Active': 10,
    'emdmCommunicationLose': 10,
    'emdmUpdateFail': 10,
}

# Resumption event to LED mapping
# Maps resumption events to LEDs that should be enabled (green LEDs) and disabled (red LEDs)
# Format: {resumption_trap_name: {'disable_led': led_number, 'enable_led': led_number}}
# When a resumption event occurs:
#   - disable_led: The red LED (alarm LED) that should be turned OFF
#   - enable_led: The green LED (normal status LED) that should be turned ON
RESUMPTION_TO_LED_MAP = {
    # Source A voltage normal -> disable LED 1 (fault), enable LED 2 (normal - Green)
    'atsSourceAvoltageAbnormalToNormal': {'disable_led': [10], 'enable_led': [2]},
    # Source A frequency normal -> disable LED 10 (alarm), enable LED 1 (fault cleared) and LED 6 (Source 1 active - Green)
    'atsSourceAfrequencyAbnormalToNormal': {'disable_led': [10], 'enable_led': [2]},
    
    # Source B voltage/frequency normal -> disable LED 5 (fault), enable LED 4 (normal - Green)
    'atsSourceBvoltageAbnormalToNormal': {'disable_led': [10], 'enable_led': [4]},
    'atsSourceBfrequencyAbnormalToNormal': {'disable_led': [10], 'enable_led': [4]},
    
    # Load normal -> disable LED 11 (overload), enable LED 12 (load normal - Green)
    'atsOutputOverLoadToNormal': {'disable_led': 11, 'enable_led': [12]},
    'atsUserSetOverLoadToNormal': {'disable_led': 11, 'enable_led': [12]},
    'atsOutputExceedsOverloadTimeToNormal': {'disable_led': 11, 'enable_led': [12]},
    
    # ATS Alarm normal -> disable LED 10 (alarm), enable LED 2 (Source 1 voltage normal status - Green)
    'atsAtsAlarmToNormal': {'disable_led': 10, 'enable_led': [2,6,8]},
    
    # General unit faults normal -> disable LED 10 (alarm), enable LED 8 (system OK)
    'atsWorkPowerAabnormalToNormal': {'disable_led': 10},
    'atsWorkPowerBabnormalToNormal': {'disable_led': 10},
    'atsDcOffsetAbnormalToNormal': {'disable_led': 10},
    'atsEepromAbnormalToNormal': {'disable_led': 10},
    'atsLcdNotConnectToNormal': {'disable_led': 10},
    'atsInputPhaseDifferenceToNormal': {'disable_led': 10},
    'atsCommunicationToNormal': {'disable_led': 10},
    'atsCommunicationEstablished': {'disable_led': 10},
    'atsOverTemperatureToNormal': {'disable_led': 10},
    'atsEpoToNormal': {'disable_led': 10},
    
    # EMD alarms normal -> disable LED 10 (alarm), enable LED 8 (system OK)
    'emdmTemperatureNotHighWarn': {'disable_led': 10},
    'emdmTemperatureNotLowWarn': {'disable_led': 10},
    'emdmTemperatureNotHighCrit': {'disable_led': 10},
    'emdmTemperatureNotLowCrit': {'disable_led': 10},
    'emdmHumidityNotHighWarn': {'disable_led': 10},
    'emdmHumidityNotLowWarn': {'disable_led': 10},
    'emdmHumidityNotHighCrit': {'disable_led': 10},
    'emdmHumidityNotLowCrit': {'disable_led': 10},
    'emdmAlarm1Normal': {'disable_led': 10},
    'emdmAlarm2Normal': {'disable_led': 10},
    'emdmCommunicationSuccess': {'disable_led': 10},
}
