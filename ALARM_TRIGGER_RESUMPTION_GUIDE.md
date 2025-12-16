# Alarm Trigger and Resumption Guide

## Overview

This document explains how the UPS SNMP Trap Receiver distinguishes between **alarm triggers** (when an alarm occurs) and **alarm resumptions** (when an alarm returns to normal).

**Note**: All alarms in this system are from **SMAP SNMP R1e.mib** file only. RFC 1628 UPS MIB alarms have been removed.

## Key Concepts

### Alarm Event Types

The system classifies each trap into one of three event types:

1. **`trigger`** - Alarm is starting/occurring (e.g., `upsOnBattery`, `lowBattery`, `envOverTemperature`)
2. **`resumption`** - Alarm is clearing/returning to normal (e.g., `powerRestored`, `returnFromLowBattery`, `envTemperatureNormal`)
3. **`state`** - Informational state change (e.g., `upsInverterMode`, `upsBypassMode`)

### Alarm-Resumption Mapping

The system maintains mappings that define which alarm triggers are cleared by which resumption events:

```python
ALARM_RESUMPTION_MAP = {
    'upsOnBattery': 'powerRestored',        # Battery power → Power restored
    'lowBattery': 'returnFromLowBattery',          # Low battery → Battery normal
    'upsSleeping': 'upsWokeUp',                     # Sleep mode → Woke up
    'envOverTemperature': 'envTemperatureNormal',  # Over temp → Temp normal
    # ... and more
}
```

## Complete Alarm Reference Table

This table lists all alarms defined in the system with their OID, severity, event type, and description.

**Note**: All alarms are from **SMAP SNMP R1e.mib** file only. RFC 1628 UPS MIB alarms have been removed.

| OID | Alarm Name | Severity | Event Type | Description |
|-----|------------|----------|------------|-------------|
| **SMAP/PPC MIB - Critical Alarms** |
| `1.3.6.1.4.1.935.0.1` | `communicationLost` | critical | trigger | SEVERE: Communication to the UPS has been lost |
| `1.3.6.1.4.1.935.0.2` | `upsOverLoad` | critical | trigger | SEVERE: The UPS has sensed a load greater than 100 percent of its rated capacity |
| `1.3.6.1.4.1.935.0.3` | `upsDiagnosticsFailed` | critical | trigger | SEVERE: The UPS failed its internal diagnostic self-test |
| `1.3.6.1.4.1.935.0.4` | `upsDischarged` | critical | trigger | SEVERE: The UPS just started a runtime calibration discharge |
| `1.3.6.1.4.1.935.0.7` | `lowBattery` | critical | trigger | SEVERE: The UPS batteries are low and will soon be exhausted |
| `1.3.6.1.4.1.935.0.54` | `upsShortCircuitShutdown` | critical | trigger | SEVERE: The UPS short circuit shutdown |
| `1.3.6.1.4.1.935.0.55` | `upsInverterOutputFailShutdown` | critical | trigger | SEVERE: The UPS inverter output fail shutdown |
| `1.3.6.1.4.1.935.0.56` | `upsBypassBreadkerOnShutdown` | critical | trigger | SEVERE: The UPS manual bypass breaker on shutdown |
| `1.3.6.1.4.1.935.0.57` | `upsHighDCShutdown` | critical | trigger | SEVERE: The UPS high DC shutdown |
| `1.3.6.1.4.1.935.0.58` | `upsEmergencyStop` | critical | trigger | SEVERE: The UPS emergency stop |
| `1.3.6.1.4.1.935.0.61` | `upsOverTemperatureShutdown` | critical | trigger | SEVERE: The UPS over temperature shutdown |
| `1.3.6.1.4.1.935.0.62` | `upsOverLoadShutdown` | critical | trigger | SEVERE: The UPS overload shutdown |
| `1.3.6.1.4.1.935.0.67` | `upsLowBatteryShutdown` | critical | trigger | SEVERE: The UPS low battery shutdown |
| **SMAP/PPC MIB - Warning Alarms** |
| `1.3.6.1.4.1.935.0.5` | `upsOnBattery` | warning | trigger | WARNING: The UPS has switched to battery backup power |
| `1.3.6.1.4.1.935.0.6` | `boostOn` | warning | trigger | WARNING: The UPS has enabled Boost |
| `1.3.6.1.4.1.935.0.12` | `upsTurnedOff` | warning | trigger | WARNING: The UPS has been turned off by the management station |
| `1.3.6.1.4.1.935.0.13` | `upsSleeping` | warning | trigger | WARNING: The UPS is entering sleep mode. Power to the load will be cut off |
| `1.3.6.1.4.1.935.0.15` | `upsRebootStarted` | warning | trigger | WARNING: The UPS has started its reboot sequence |
| `1.3.6.1.4.1.935.0.16` | `envOverTemperature` | warning | trigger | WARNING: The environment temperature exceeded the normal value |
| `1.3.6.1.4.1.935.0.18` | `envOverHumidity` | warning | trigger | WARNING: The environment humidity exceeded the normal value |
| `1.3.6.1.4.1.935.0.20` | `envSmokeAbnormal` | warning | trigger | WARNING: Smoke is abnormal |
| `1.3.6.1.4.1.935.0.21` | `envWaterAbnormal` | warning | trigger | WARNING: Water is abnormal |
| `1.3.6.1.4.1.935.0.22` | `envSecurityAbnormal` | warning | trigger | WARNING: Security is abnormal |
| `1.3.6.1.4.1.935.0.26` | `envGasAbnormal` | warning | trigger | WARNING: Gas alarm |
| `1.3.6.1.4.1.935.0.27` | `upsTemp` | warning | trigger | WARNING: UPS temperature overrun |
| `1.3.6.1.4.1.935.0.28` | `upsLoadNormal` | warning | state | WARNING: UPS load normal |
| `1.3.6.1.4.1.935.0.29` | `upsTempNormal` | warning | resumption | WARNING: UPS temperature normal |
| `1.3.6.1.4.1.935.0.30` | `envUnderTemperature` | warning | trigger | WARNING: The environment temperature below the normal value |
| `1.3.6.1.4.1.935.0.31` | `envUnderHumidity` | warning | trigger | WARNING: The environment humidity below the normal value |
| `1.3.6.1.4.1.935.0.32` | `upsBypass` | warning | trigger | WARNING: The UPS is entering bypass mode |
| `1.3.6.1.4.1.935.0.33` | `envSecurity1` | warning | trigger | WARNING: Security1 alarm |
| `1.3.6.1.4.1.935.0.34` | `envSecurity2` | warning | trigger | WARNING: Security2 alarm |
| `1.3.6.1.4.1.935.0.35` | `envSecurity3` | warning | trigger | WARNING: Security3 alarm |
| `1.3.6.1.4.1.935.0.36` | `envSecurity4` | warning | trigger | WARNING: Security4 alarm |
| `1.3.6.1.4.1.935.0.37` | `envSecurity5` | warning | trigger | WARNING: Security5 alarm |
| `1.3.6.1.4.1.935.0.38` | `envSecurity6` | warning | trigger | WARNING: Security6 alarm |
| `1.3.6.1.4.1.935.0.39` | `envSecurity7` | warning | trigger | WARNING: Security7 alarm |
| `1.3.6.1.4.1.935.0.47` | `upsRecroterror` | warning | trigger | WARNING: Rectifier rotation error |
| `1.3.6.1.4.1.935.0.48` | `upsBypassFreFail` | warning | trigger | WARNING: Bypass frequency fail |
| `1.3.6.1.4.1.935.0.49` | `upsBypassacnormal` | warning | resumption | WARNING: Bypass AC normal |
| `1.3.6.1.4.1.935.0.50` | `upsBypassacabnormal` | warning | trigger | WARNING: Bypass AC abnormal |
| `1.3.6.1.4.1.935.0.51` | `upsTest` | warning | trigger | WARNING: UPS test |
| `1.3.6.1.4.1.935.0.52` | `upsScheduleShutdown` | warning | trigger | WARNING: UPS schedule shutdown |
| `1.3.6.1.4.1.935.0.53` | `upsBypassReturn` | warning | resumption | WARNING: The UPS return from bypass mode |
| `1.3.6.1.4.1.935.0.63` | `upsCapacityUnderrun` | warning | trigger | WARNING: The UPS capacity underrun |
| `1.3.6.1.4.1.935.0.68` | `buckOn` | warning | trigger | WARNING: The UPS has enabled Buck |
| `1.3.6.1.4.1.935.0.69` | `returnFromBuck` | warning | resumption | WARNING: The UPS has return from Buck |
| `1.3.6.1.4.1.935.0.70` | `returnFromBoost` | warning | resumption | WARNING: The UPS has return from Boost |
| **SMAP/PPC MIB - Informational Alarms** |
| `1.3.6.1.4.1.935.0.8` | `communicationEstablished` | info | resumption | INFORMATION: Communication with the UPS has been established |
| `1.3.6.1.4.1.935.0.9` | `powerRestored` | info | resumption | INFORMATION: Utility power has been restored |
| `1.3.6.1.4.1.935.0.10` | `upsDiagnosticsPassed` | info | resumption | INFORMATION: The UPS passed its internal self-test |
| `1.3.6.1.4.1.935.0.11` | `returnFromLowBattery` | info | resumption | INFORMATION: The UPS has returned from a low battery condition |
| `1.3.6.1.4.1.935.0.14` | `upsWokeUp` | info | resumption | INFORMATION: The UPS woke up from sleep mode. Power to the load has been restored |
| `1.3.6.1.4.1.935.0.17` | `envTemperatureNormal` | info | resumption | INFORMATION: The environment temperature is normal |
| `1.3.6.1.4.1.935.0.19` | `envHumidityNormal` | info | resumption | INFORMATION: The environment humidity is normal |
| `1.3.6.1.4.1.935.0.24` | `envWaterNormal` | info | resumption | INFORMATION: Water is normal |
| `1.3.6.1.4.1.935.0.59` | `upsInverterMode` | info | state | INFORMATION: The UPS static switch in inverter mode |
| `1.3.6.1.4.1.935.0.60` | `upsBypassMode` | info | state | INFORMATION: The UPS static switch in bypass mode |
| `1.3.6.1.4.1.935.0.64` | `upsCapacityNormal` | info | resumption | INFORMATION: The UPS capacity normal |

## Alarm Trigger and Resumption Pairs

This table shows all alarm trigger events and their corresponding resumption events that clear them.

| Alarm Trigger | Trigger OID | Severity | Resumption Event | Resumption OID | Severity | Description |
|---------------|-------------|----------|------------------|----------------|----------|-------------|
| `upsOnBattery` | `1.3.6.1.4.1.935.0.5` | warning | `powerRestored` | `1.3.6.1.4.1.935.0.9` | info | UPS on battery → Power restored |
| `lowBattery` | `1.3.6.1.4.1.935.0.7` | critical | `returnFromLowBattery` | `1.3.6.1.4.1.935.0.11` | info | Low battery → Battery normal |
| `upsSleeping` | `1.3.6.1.4.1.935.0.13` | warning | `upsWokeUp` | `1.3.6.1.4.1.935.0.14` | info | Sleep mode → Woke up |
| `envOverTemperature` | `1.3.6.1.4.1.935.0.16` | warning | `envTemperatureNormal` | `1.3.6.1.4.1.935.0.17` | info | Over temp → Temp normal |
| `envOverHumidity` | `1.3.6.1.4.1.935.0.18` | warning | `envHumidityNormal` | `1.3.6.1.4.1.935.0.19` | info | Over humidity → Humidity normal |
| `envUnderTemperature` | `1.3.6.1.4.1.935.0.30` | warning | `envTemperatureNormal` | `1.3.6.1.4.1.935.0.17` | info | Under temp → Temp normal |
| `envUnderHumidity` | `1.3.6.1.4.1.935.0.31` | warning | `envHumidityNormal` | `1.3.6.1.4.1.935.0.19` | info | Under humidity → Humidity normal |
| `envWaterAbnormal` | `1.3.6.1.4.1.935.0.21` | warning | `envWaterNormal` | `1.3.6.1.4.1.935.0.24` | info | Water abnormal → Water normal |
| `upsBypass` | `1.3.6.1.4.1.935.0.32` | warning | `upsBypassReturn` | `1.3.6.1.4.1.935.0.53` | warning | Bypass mode → Return from bypass |
| `boostOn` | `1.3.6.1.4.1.935.0.6` | warning | `returnFromBoost` | `1.3.6.1.4.1.935.0.70` | warning | Boost enabled → Return from boost |
| `buckOn` | `1.3.6.1.4.1.935.0.68` | warning | `returnFromBuck` | `1.3.6.1.4.1.935.0.69` | warning | Buck enabled → Return from buck |
| `communicationLost` | `1.3.6.1.4.1.935.0.1` | critical | `communicationEstablished` | `1.3.6.1.4.1.935.0.8` | info | Comm lost → Comm established |
| `upsDiagnosticsFailed` | `1.3.6.1.4.1.935.0.3` | critical | `upsDiagnosticsPassed` | `1.3.6.1.4.1.935.0.10` | info | Test failed → Test passed |
| `upsCapacityUnderrun` | `1.3.6.1.4.1.935.0.63` | warning | `upsCapacityNormal` | `1.3.6.1.4.1.935.0.64` | info | Capacity underrun → Capacity normal |
| `upsLoadNormal` | `1.3.6.1.4.1.935.0.28` | warning | `upsCapacityNormal` | `1.3.6.1.4.1.935.0.64` | info | Load normal → Capacity normal (related) |
| `upsTemp` | `1.3.6.1.4.1.935.0.27` | warning | `upsTempNormal` | `1.3.6.1.4.1.935.0.29` | warning | Temp overrun → Temp normal |
| `upsBypassacabnormal` | `1.3.6.1.4.1.935.0.50` | warning | `upsBypassacnormal` | `1.3.6.1.4.1.935.0.49` | warning | Bypass AC abnormal → Bypass AC normal |
| `upsBypassFreFail` | `1.3.6.1.4.1.935.0.48` | warning | `upsBypassacnormal` | `1.3.6.1.4.1.935.0.49` | warning | Bypass freq fail → Bypass AC normal (related) |

### Notes on Alarm-Resumption Pairs

- **Multiple triggers can share one resumption**: For example, `envTemperatureNormal` clears both `envOverTemperature` and `envUnderTemperature`
- **Some alarms have no resumption**: Critical shutdown alarms (like `upsEmergencyStop`, `upsShortCircuitShutdown`) typically require manual intervention and don't have automatic resumption events
- **Resumption severity may differ**: Some resumptions are `info` (good news) while their triggers are `warning` or `critical`

## How It Works

### 1. When an Alarm Trigger is Received

When a trap with `event_type = 'trigger'` is received:

1. **Logging**: The system logs it as "🔴 ALARM TRIGGERED"
2. **GPIO LED**: If severity is `warning` or `critical`, the LED is **turned ON**
3. **Mapping Info**: The log shows which resumption event will clear this alarm

**Example:**
```
Trap Name: upsOnBattery
Event Type: 🔴 ALARM TRIGGERED (trigger)
Description: WARNING: The UPS has switched to battery backup power.
Will be cleared by: powerRestored
GPIO LED triggered on pin 17 for upsOnBattery (warning) - ALARM TRIGGERED
```

### 2. When a Resumption Event is Received

When a trap with `event_type = 'resumption'` is received:

1. **Logging**: The system logs it as "🟢 ALARM CLEARED/RESUMED"
2. **GPIO LED**: The LED is **turned OFF** for the cleared alarm(s)
3. **Mapping Info**: The log shows which alarm(s) are being cleared

**Example:**
```
Trap Name: powerRestored
Event Type: 🟢 ALARM CLEARED/RESUMED (resumption)
Description: INFORMATION: Utility power has been restored.
Clears Alarm(s): upsOnBattery
GPIO LED cleared for 'upsOnBattery' (warning) - resumption: powerRestored
```

## Code Structure

### Mapping Dictionaries

1. **`ALARM_RESUMPTION_MAP`**: Maps alarm trigger → resumption event
2. **`RESUMPTION_TO_ALARM_MAP`**: Reverse mapping (resumption → list of alarms it clears)
3. **`ALARM_EVENT_TYPE`**: Classifies each trap as `trigger`, `resumption`, or `state`

### GPIO LED Handling

The `log_trap()` method uses these mappings to:

- **Trigger events**: Turn ON LED for `warning`/`critical` alarms
- **Resumption events**: Turn OFF LED for the cleared alarm(s)
- **State events**: No LED action (informational only)

## Finding Alarm Codes

### To Find Which Alarm Triggers a Condition:

1. Look in `ALARM_EVENT_TYPE` for entries with `'trigger'`
2. Check `ALARM_RESUMPTION_MAP` to see which resumption clears it
3. Example: `upsOnBattery` is a trigger, cleared by `upsTrapPowerRestored`

### To Find Which Resumption Clears an Alarm:

1. Look in `ALARM_EVENT_TYPE` for entries with `'resumption'`
2. Check `RESUMPTION_TO_ALARM_MAP` to see which alarms it clears
3. Example: `powerRestored` is a resumption, clears `upsOnBattery`

### To Find Alarm/Resumption Pairs:

1. Check `ALARM_RESUMPTION_MAP` - each key is a trigger, each value is its resumption
2. Example: `'upsOnBattery': 'powerRestored'` means:
   - **Trigger**: `upsOnBattery` (OID: `1.3.6.1.4.1.935.0.5`)
   - **Resumption**: `powerRestored` (OID: `1.3.6.1.4.1.935.0.9`)

## Log Examples

### Alarm Trigger Log:
```
================================================================================
Timestamp: 2024-01-15 14:30:25
Source: 192.168.1.100:162
Trap OID: 1.3.6.1.4.1.935.0.5
Trap Name: upsOnBattery
Event Type: 🔴 ALARM TRIGGERED (trigger)
Description: WARNING: The UPS has switched to battery backup power.
Will be cleared by: powerRestored
Variables:
  1.3.6.1.4.1.935.1.1.1.2.1: 3
================================================================================
GPIO LED triggered on pin 17 for upsOnBattery (warning) - ALARM TRIGGERED
```

### Alarm Resumption Log:
```
================================================================================
Timestamp: 2024-01-15 14:35:10
Source: 192.168.1.100:162
Trap OID: 1.3.6.1.4.1.935.0.9
Trap Name: powerRestored
Event Type: 🟢 ALARM CLEARED/RESUMED (resumption)
Description: INFORMATION: Utility power has been restored.
Clears Alarm(s): upsOnBattery
Variables:
  1.3.6.1.4.1.935.1.1.1.2.1: 2
================================================================================
GPIO LED cleared for 'upsOnBattery' (warning) - resumption: powerRestored
```

## Alarms Without Resumption Events

**Yes, there are many alarms that only trigger but do NOT have resumption events.**

Out of **47 trigger alarms** (all from SMAP SNMP R1e.mib), **30 alarms (64%)** do NOT have resumption events. These alarms typically require manual intervention, system restart, or physical repair.

### Summary Table: Alarms Without Resumption

| Category | Count | Examples |
|----------|-------|----------|
| **Critical Alarms** | 10 | `upsEmergencyStop`, `upsShortCircuitShutdown`, `upsOverLoad`, `upsLowBatteryShutdown` |
| **Warning Alarms** | 20 | `upsTurnedOff`, `envSmokeAbnormal`, `envSecurity1-7`, `upsScheduleShutdown` |
| **Total** | **30** | See detailed list below |

### Critical Alarms Without Resumption (10 alarms)

| Alarm Name | OID | Severity | Reason for No Resumption |
|------------|-----|----------|--------------------------|
| `upsOverLoad` | `1.3.6.1.4.1.935.0.2` | critical | Requires load reduction - manual action |
| `upsDischarged` | `1.3.6.1.4.1.935.0.4` | critical | One-time calibration event |
| `upsShortCircuitShutdown` | `1.3.6.1.4.1.935.0.54` | critical | Requires physical repair |
| `upsInverterOutputFailShutdown` | `1.3.6.1.4.1.935.0.55` | critical | Hardware failure - requires repair |
| `upsBypassBreadkerOnShutdown` | `1.3.6.1.4.1.935.0.56` | critical | Manual breaker operation - requires reset |
| `upsHighDCShutdown` | `1.3.6.1.4.1.935.0.57` | critical | Hardware fault - requires investigation |
| `upsEmergencyStop` | `1.3.6.1.4.1.935.0.58` | critical | Manual emergency stop - requires reset |
| `upsOverTemperatureShutdown` | `1.3.6.1.4.1.935.0.61` | critical | Thermal protection - requires cooling |
| `upsOverLoadShutdown` | `1.3.6.1.4.1.935.0.62` | critical | Overload condition - requires load reduction |
| `upsLowBatteryShutdown` | `1.3.6.1.4.1.935.0.67` | critical | Battery exhausted - requires power restoration |

### Warning Alarms Without Resumption (20 alarms)

| Alarm Name | OID | Severity | Reason for No Resumption |
|------------|-----|----------|--------------------------|
| `upsTurnedOff` | `1.3.6.1.4.1.935.0.12` | warning | Manual action - requires manual turn-on |
| `upsRebootStarted` | `1.3.6.1.4.1.935.0.15` | warning | One-time event - system will restart |
| `envSmokeAbnormal` | `1.3.6.1.4.1.935.0.20` | warning | Safety alarm - requires investigation |
| `envSecurityAbnormal` | `1.3.6.1.4.1.935.0.22` | warning | Security breach - requires investigation |
| `envGasAbnormal` | `1.3.6.1.4.1.935.0.26` | warning | Safety alarm - requires investigation |
| `envSecurity1` | `1.3.6.1.4.1.935.0.33` | warning | Security sensor - requires investigation |
| `envSecurity2` | `1.3.6.1.4.1.935.0.34` | warning | Security sensor - requires investigation |
| `envSecurity3` | `1.3.6.1.4.1.935.0.35` | warning | Security sensor - requires investigation |
| `envSecurity4` | `1.3.6.1.4.1.935.0.36` | warning | Security sensor - requires investigation |
| `envSecurity5` | `1.3.6.1.4.1.935.0.37` | warning | Security sensor - requires investigation |
| `envSecurity6` | `1.3.6.1.4.1.935.0.38` | warning | Security sensor - requires investigation |
| `envSecurity7` | `1.3.6.1.4.1.935.0.39` | warning | Security sensor - requires investigation |
| `upsRecroterror` | `1.3.6.1.4.1.935.0.47` | warning | Hardware error - may require repair |
| `upsTest` | `1.3.6.1.4.1.935.0.51` | warning | One-time test event |
| `upsScheduleShutdown` | `1.3.6.1.4.1.935.0.52` | warning | Scheduled event - requires manual restart |

### Why These Alarms Don't Have Resumptions

1. **Hardware Failures**: Require physical repair (e.g., `upsShortCircuitShutdown`, `upsInverterOutputFailShutdown`)
2. **Manual Interventions**: Require human action (e.g., `upsEmergencyStop`, `upsTurnedOff`)
3. **Safety Alarms**: Require investigation (e.g., `envSmokeAbnormal`, `envGasAbnormal`, `envSecurity1-7`)
4. **One-Time Events**: Don't need clearing (e.g., `upsDischarged`, `upsTest`, `upsRebootStarted`)
5. **Overload Conditions**: Require load reduction (e.g., `upsOverLoad`, `upsOverLoadShutdown`)
6. **Battery Issues**: Require charging or replacement (e.g., `upsLowBatteryShutdown`, `upsAlarmBatteryReplacement`)

### Impact on System Behavior

For alarms **without resumption events**:
- **GPIO LED**: Will turn ON when triggered and **stay ON** until manually cleared or system restarted
- **Sound Alert**: Will play when triggered (may repeat if condition persists)
- **Logging**: Will show "🔴 ALARM TRIGGERED" but **no "Will be cleared by"** message
- **Action Required**: These alarms typically require **manual intervention** to resolve

**See `ALARMS_WITHOUT_RESUMPTION.md` for complete details.**

## Important Notes

1. **Not all alarms have resumptions**: **30 out of 47 trigger alarms (64%)** from SMAP SNMP R1e.mib do NOT have resumption events. These typically require manual intervention, system restart, or physical repair.

2. **Multiple alarms can share a resumption**: For example, `envTemperatureNormal` clears both `envOverTemperature` and `envUnderTemperature`.

3. **Some resumptions are informational**: Events like `upsCapacityNormal` and `upsTempNormal` are logged but may not trigger LED actions if they're just state changes.

4. **Event type determines LED behavior**: Only `trigger` events with `warning`/`critical` severity turn ON LEDs. `resumption` events turn OFF LEDs.

5. **Alarms without resumptions need manual clearing**: Consider implementing a manual clear function or timeout-based clearing for these alarms.

## Troubleshooting

### If an alarm doesn't clear:

1. Check if there's a resumption event defined in `ALARM_RESUMPTION_MAP`
2. Verify the resumption trap is being received (check logs)
3. Check if the resumption event is classified correctly in `ALARM_EVENT_TYPE`

### If LED doesn't turn on/off:

1. Check the event type in the log (`trigger` vs `resumption`)
2. Verify severity is `warning` or `critical` for triggers
3. Check GPIO pin configuration in `gpio_config.json`

