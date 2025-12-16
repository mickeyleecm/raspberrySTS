# MIB File vs Python Receiver Comparison

## Overview
This document compares the alarm definitions in `SMAP SNMP R1e.mib` with the definitions in `ups_snmp_trap_receiver.py`.

## Key Differences

### 1. OID Base Structure

**SMAP SNMP R1e.mib:**
- Uses **PPC/SMAP enterprise OID**: `1.3.6.1.4.1.935` (enterprises 935)
- Trap OIDs follow pattern: `1.3.6.1.4.1.935.0.{trap_number}`
- Example: `upsOnBattery` = `1.3.6.1.4.1.935.0.5`

**ups_snmp_trap_receiver.py:**
- Uses **RFC 1628 UPS MIB** (standard): `1.3.6.1.2.1.33`
- Also includes some **APC PowerNet MIB**: `1.3.6.1.4.1.935` (same enterprise as SMAP!)
- Example: `upsTrapOnBattery` = `1.3.6.1.2.1.33.2.1`

### 2. Number of Alarm Definitions

**SMAP SNMP R1e.mib:**
- **70 trap definitions** (trap 1 through trap 70, with some gaps)
- Comprehensive coverage including:
  - UPS operational states
  - Battery conditions
  - Environment monitoring (temperature, humidity, smoke, water, security)
  - Three-phase UPS specific alarms
  - Bypass and inverter modes
  - Various shutdown conditions

**ups_snmp_trap_receiver.py:**
- **12 OID definitions** in `UPS_OIDS`
- Limited to basic UPS alarms from RFC 1628 standard
- Missing many SMAP-specific alarms

### 3. Alarm Severity Mapping

**SMAP SNMP R1e.mib:**
- Uses explicit severity levels in comments:
  - `CRITICAL` (SEVERE)
  - `MAJOR` (WARNING)
  - `MINOR` (WARNING)
  - `INFORMATIONAL`
- Examples:
  - `communicationLost` → CRITICAL
  - `upsOnBattery` → MAJOR
  - `boostOn` → MINOR
  - `powerRestored` → INFORMATIONAL

**ups_snmp_trap_receiver.py:**
- Uses simplified severity levels:
  - `critical`
  - `warning`
  - `info`
- Only 12 alarms have severity mappings

## Detailed Alarm Comparison

### Alarms Present in Both (with different OIDs)

| SMAP MIB | SMAP OID | Python Name | Python OID | Match Status |
|----------|----------|-------------|------------|--------------|
| `upsOnBattery` | `1.3.6.1.4.1.935.0.5` | `upsTrapOnBattery` | `1.3.6.1.2.1.33.2.1` | **Different OIDs, same meaning** |
| `powerRestored` | `1.3.6.1.4.1.935.0.9` | `upsTrapPowerRestored` | `1.3.6.1.4.1.935.0.9` | **Same OID!** |
| `lowBattery` | `1.3.6.1.4.1.935.0.7` | `upsAlarmBatteryLow` | `1.3.6.1.2.1.33.1.6.3.1` | Different OIDs |
| `upsDischarged` | `1.3.6.1.4.1.935.0.4` | `upsAlarmBatteryDischarged` | `1.3.6.1.2.1.33.1.6.3.2` | Different OIDs |
| `upsDiagnosticsFailed` | `1.3.6.1.4.1.935.0.3` | `upsAlarmBatteryTestFailure` | `1.3.6.1.2.1.33.1.6.3.3` | Different OIDs |
| `upsOverLoad` | `1.3.6.1.4.1.935.0.2` | `upsAlarmOutputOverload` | `1.3.6.1.2.1.33.1.6.3.8` | Different OIDs |
| `communicationLost` | `1.3.6.1.4.1.935.0.1` | `upsAlarmCommunicationsLost` | `1.3.6.1.2.1.33.1.6.3.20` | Different OIDs |
| `upsDiagnosticsPassed` | `1.3.6.1.4.1.935.0.10` | `upsTrapTestCompleted` | `1.3.6.1.2.1.33.2.2` | Different OIDs |

### Alarms ONLY in SMAP MIB (Missing from Python)

#### Critical/SEVERE Alarms:
1. `upsShortCircuitShutdown` (trap 54)
2. `upsInverterOutputFailShutdown` (trap 55)
3. `upsBypassBreadkerOnShutdown` (trap 56)
4. `upsHighDCShutdown` (trap 57)
5. `upsEmergencyStop` (trap 58)
6. `upsOverTemperatureShutdown` (trap 61)
7. `upsOverLoadShutdown` (trap 62)
8. `upsLowBatteryShutdown` (trap 67)

#### Warning/MAJOR Alarms:
9. `boostOn` (trap 6)
10. `buckOn` (trap 68)
11. `returnFromBuck` (trap 69)
12. `returnFromBoost` (trap 70)
13. `upsTurnedOff` (trap 12)
14. `upsSleeping` (trap 13)
15. `upsRebootStarted` (trap 15)
16. `upsBypass` (trap 32)
17. `upsBypassReturn` (trap 53)
18. `upsRecroterror` (trap 47) - Rectifier Rotation Error
19. `upsBypassFreFail` (trap 48) - Bypass Frequency Fail
20. `upsBypassacnormal` (trap 49)
21. `upsBypassacabnormal` (trap 50)
22. `upsTest` (trap 51)
23. `upsScheduleShutdown` (trap 52)
24. `upsTemp` (trap 27) - UPS Temperature Overrun
25. `upsInverterMode` (trap 59)
26. `upsBypassMode` (trap 60)

#### Informational Alarms:
27. `communicationEstablished` (trap 8)
28. `returnFromLowBattery` (trap 11)
29. `upsWokeUp` (trap 14)
30. `upsLoadNormal` (trap 28)
31. `upsTempNormal` (trap 29)
32. `upsCapacityNormal` (trap 64)

#### Environment Monitoring Alarms:
33. `envOverTemperature` (trap 16)
34. `envTemperatureNormal` (trap 17)
35. `envOverHumidity` (trap 18)
36. `envHumidityNormal` (trap 19)
37. `envSmokeAbnormal` (trap 20)
38. `envWaterAbnormal` (trap 21)
39. `envWaterNormal` (trap 24)
40. `envSecurityAbnormal` (trap 22)
41. `envGasAbnormal` (trap 26)
42. `envUnderTemperature` (trap 30)
43. `envUnderHumidity` (trap 31)
44. `envSecurity1` through `envSecurity7` (traps 33-39)
45. `upsCapacityUnderrun` (trap 63)

### Alarms ONLY in Python (Not in SMAP MIB)
- `upsAlarmInputBad` - Input voltage/frequency out of tolerance
- `upsAlarmGeneralFault` - General UPS fault
- `upsAlarmChargerFailed` - Charger subsystem problem
- `upsAlarmBatteryReplacement` - Battery replacement indicator
- `upsAlarmBatteryTemperature` - High battery temperature

## BATTERY_OID_PATTERNS Comparison

**Python `BATTERY_OID_PATTERNS`:**
```python
BATTERY_OID_PATTERNS = [
    '1.3.6.1.2.1.33.1.2',      # upsBattery group (RFC 1628)
    '1.3.6.1.4.1.318.1.1.1.2',  # APC PowerNet MIB battery
    '1.3.6.1.4.1.534.1',        # Eaton XUPS MIB
]
```

**SMAP MIB Battery OIDs:**
- `1.3.6.1.4.1.935.1.1.1.2` - upsBatteryp (upsBaseBattery, upsSmartBattery)
- `1.3.6.1.4.1.935.1.1.8.1` - upsThreePhaseBatteryGrp

**Missing from Python:** The SMAP battery OID patterns are not included!

## ALARM_SEVERITY Comparison

**Python `ALARM_SEVERITY` mapping:**
- Only 12 alarms have severity mappings
- Uses: `critical`, `warning`, `info`

**SMAP MIB Severity (from comments):**
- `CRITICAL`: communicationLost, upsOverLoad, upsDiagnosticsFailed, upsDischarged, lowBattery
- `MAJOR`: upsOnBattery, upsTurnedOff, upsSleeping, upsRebootStarted, upsBypass, etc.
- `MINOR`: boostOn, buckOn
- `INFORMATIONAL`: communicationEstablished, powerRestored, upsDiagnosticsPassed, returnFromLowBattery, upsWokeUp

## Recommendations

### 1. Add SMAP MIB OIDs to UPS_OIDS
The Python receiver should include SMAP-specific trap OIDs:
```python
# SMAP/PPC MIB traps (1.3.6.1.4.1.935.0.x)
'1.3.6.1.4.1.935.0.1': 'communicationLost',
'1.3.6.1.4.1.935.0.2': 'upsOverLoad',
'1.3.6.1.4.1.935.0.3': 'upsDiagnosticsFailed',
'1.3.6.1.4.1.935.0.4': 'upsDischarged',
'1.3.6.1.4.1.935.0.5': 'upsOnBattery',
'1.3.6.1.4.1.935.0.6': 'boostOn',
'1.3.6.1.4.1.935.0.7': 'lowBattery',
'1.3.6.1.4.1.935.0.8': 'communicationEstablished',
'1.3.6.1.4.1.935.0.9': 'powerRestored',  # Already exists!
'1.3.6.1.4.1.935.0.10': 'upsDiagnosticsPassed',
# ... and many more
```

### 2. Update BATTERY_OID_PATTERNS
Add SMAP battery OID patterns:
```python
BATTERY_OID_PATTERNS = [
    '1.3.6.1.2.1.33.1.2',      # upsBattery group (RFC 1628)
    '1.3.6.1.4.1.318.1.1.1.2',  # APC PowerNet MIB battery
    '1.3.6.1.4.1.534.1',        # Eaton XUPS MIB
    '1.3.6.1.4.1.935.1.1.1.2',  # SMAP upsBatteryp group
    '1.3.6.1.4.1.935.1.1.8.1',  # SMAP ThreePhase Battery Group
]
```

### 3. Expand ALARM_DESCRIPTIONS
Add descriptions for all SMAP MIB alarms.

### 4. Expand ALARM_SEVERITY
Map all SMAP alarms to appropriate severity levels based on MIB comments.

## Summary

The Python receiver is currently configured for **generic RFC 1628 UPS MIB** and some **APC PowerNet MIB** traps, but it's **missing most SMAP-specific alarms** defined in the MIB file. Since the SMAP MIB uses the same enterprise OID (935) as APC, there's already partial compatibility, but many SMAP-specific traps (especially environment monitoring, three-phase UPS, and bypass modes) are not recognized.

**Key Finding:** The receiver will miss approximately **58 out of 70** SMAP trap types, potentially missing critical alarms like emergency stops, short circuits, inverter failures, and environment monitoring alerts.

