# MIB Cleanup Summary

## Overview

Reviewed and cleaned up `ups_snmp_trap_receiver.py` to ensure **all alarms come from SMAP SNMP R1e.mib file only**. Removed all RFC 1628 UPS MIB alarms that are not defined in the SMAP MIB.

## Changes Made

### 1. Removed RFC 1628 UPS MIB Alarms (12 alarms removed)

The following RFC 1628 standard alarms were removed as they are not in SMAP SNMP R1e.mib:

| OID | Alarm Name | Reason |
|-----|------------|--------|
| `1.3.6.1.2.1.33.2.1` | `upsTrapOnBattery` | Not in SMAP MIB |
| `1.3.6.1.2.1.33.1.6.3.6` | `upsAlarmInputBad` | Not in SMAP MIB |
| `1.3.6.1.2.1.33.1.6.3.8` | `upsAlarmOutputOverload` | Not in SMAP MIB |
| `1.3.6.1.2.1.33.1.6.3.18` | `upsAlarmGeneralFault` | Not in SMAP MIB |
| `1.3.6.1.2.1.33.1.6.3.13` | `upsAlarmChargerFailed` | Not in SMAP MIB |
| `1.3.6.1.2.1.33.1.6.3.20` | `upsAlarmCommunicationsLost` | Not in SMAP MIB |
| `1.3.6.1.2.1.33.2.2` | `upsTrapTestCompleted` | Not in SMAP MIB |
| `1.3.6.1.2.1.33.1.6.3.1` | `upsAlarmBatteryLow` | Not in SMAP MIB |
| `1.3.6.1.2.1.33.1.6.3.2` | `upsAlarmBatteryDischarged` | Not in SMAP MIB |
| `1.3.6.1.2.1.33.1.6.3.3` | `upsAlarmBatteryTestFailure` | Not in SMAP MIB |
| `1.3.6.1.2.1.33.1.6.3.4` | `upsAlarmBatteryReplacement` | Not in SMAP MIB |
| `1.3.6.1.2.1.33.1.6.3.5` | `upsAlarmBatteryTemperature` | Not in SMAP MIB |

### 2. Updated Alarm Name Mapping

Changed `upsTrapPowerRestored` to `powerRestored` to match the SMAP MIB file:
- **MIB File**: `powerRestored NOTIFICATION-TYPE` (trap 9)
- **Previous Code**: `upsTrapPowerRestored`
- **Updated Code**: `powerRestored`

### 3. Files Updated

#### `UPS_OIDS` Dictionary
- ✅ Removed all RFC 1628 UPS MIB entries
- ✅ Kept only SMAP/PPC MIB traps (1.3.6.1.4.1.935.0.x)
- ✅ Updated `powerRestored` name

#### `ALARM_DESCRIPTIONS` Dictionary
- ✅ Removed all RFC 1628 UPS MIB descriptions
- ✅ Updated `powerRestored` description

#### `ALARM_SEVERITY` Dictionary
- ✅ Removed all RFC 1628 UPS MIB severity mappings
- ✅ Updated `powerRestored` severity mapping

#### `ALARM_EVENT_TYPE` Dictionary
- ✅ Removed `upsTrapTestCompleted` (not in SMAP MIB)
- ✅ Updated `upsTrapPowerRestored` → `powerRestored`

#### `ALARM_RESUMPTION_MAP` Dictionary
- ✅ Updated `upsOnBattery` → `powerRestored` (was `upsTrapPowerRestored`)

#### Code References
- ✅ Updated all references from `upsTrapPowerRestored` to `powerRestored`
- ✅ Updated fallback logic to use `powerRestored`

## Remaining Alarms (All from SMAP SNMP R1e.mib)

### Total: 59 alarms (all from SMAP MIB)

#### Critical Alarms (13):
1. `communicationLost` (trap 1)
2. `upsOverLoad` (trap 2)
3. `upsDiagnosticsFailed` (trap 3)
4. `upsDischarged` (trap 4)
5. `lowBattery` (trap 7)
6. `upsShortCircuitShutdown` (trap 54)
7. `upsInverterOutputFailShutdown` (trap 55)
8. `upsBypassBreadkerOnShutdown` (trap 56)
9. `upsHighDCShutdown` (trap 57)
10. `upsEmergencyStop` (trap 58)
11. `upsOverTemperatureShutdown` (trap 61)
12. `upsOverLoadShutdown` (trap 62)
13. `upsLowBatteryShutdown` (trap 67)

#### Warning Alarms (35):
1. `upsOnBattery` (trap 5)
2. `boostOn` (trap 6)
3. `upsTurnedOff` (trap 12)
4. `upsSleeping` (trap 13)
5. `upsRebootStarted` (trap 15)
6. `envOverTemperature` (trap 16)
7. `envOverHumidity` (trap 18)
8. `envSmokeAbnormal` (trap 20)
9. `envWaterAbnormal` (trap 21)
10. `envSecurityAbnormal` (trap 22)
11. `envGasAbnormal` (trap 26)
12. `upsTemp` (trap 27)
13. `upsLoadNormal` (trap 28)
14. `upsTempNormal` (trap 29)
15. `envUnderTemperature` (trap 30)
16. `envUnderHumidity` (trap 31)
17. `upsBypass` (trap 32)
18. `envSecurity1` (trap 33)
19. `envSecurity2` (trap 34)
20. `envSecurity3` (trap 35)
21. `envSecurity4` (trap 36)
22. `envSecurity5` (trap 37)
23. `envSecurity6` (trap 38)
24. `envSecurity7` (trap 39)
25. `upsRecroterror` (trap 47)
26. `upsBypassFreFail` (trap 48)
27. `upsBypassacnormal` (trap 49)
28. `upsBypassacabnormal` (trap 50)
29. `upsTest` (trap 51)
30. `upsScheduleShutdown` (trap 52)
31. `upsBypassReturn` (trap 53)
32. `upsCapacityUnderrun` (trap 63)
33. `buckOn` (trap 68)
34. `returnFromBuck` (trap 69)
35. `returnFromBoost` (trap 70)

#### Informational Alarms (11):
1. `communicationEstablished` (trap 8)
2. `powerRestored` (trap 9) - **Name updated from `upsTrapPowerRestored`**
3. `upsDiagnosticsPassed` (trap 10)
4. `returnFromLowBattery` (trap 11)
5. `upsWokeUp` (trap 14)
6. `envTemperatureNormal` (trap 17)
7. `envHumidityNormal` (trap 19)
8. `envWaterNormal` (trap 24)
9. `upsInverterMode` (trap 59)
10. `upsBypassMode` (trap 60)
11. `upsCapacityNormal` (trap 64)

## Verification

✅ All alarms in `UPS_OIDS` now match SMAP SNMP R1e.mib file
✅ All alarm names match MIB file definitions
✅ Code compiles without errors
✅ No linter errors

## Notes

- **BATTERY_OID_PATTERNS** still includes RFC 1628 patterns for pattern matching purposes (not specific alarms)
- This is acceptable as it's used for detecting battery-related OIDs in general, not for specific alarm definitions
- All specific alarm definitions now come exclusively from SMAP SNMP R1e.mib

## Impact

- **Before**: 71 alarms (12 RFC 1628 + 59 SMAP)
- **After**: 59 alarms (all SMAP MIB only)
- **Removed**: 12 RFC 1628 alarms
- **Updated**: 1 alarm name (`upsTrapPowerRestored` → `powerRestored`)

