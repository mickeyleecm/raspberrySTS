# Alarms Without Resumption Events

This document lists all alarms that are **trigger events** but **do NOT have a corresponding resumption event** to clear them.

## Summary

Out of **47 trigger alarms**, **30 alarms** do NOT have resumption events. These alarms typically require:
- Manual intervention
- System restart
- Physical repair
- Or they represent one-time events that don't automatically clear

## Alarms WITH Resumption Events (17 alarms)

These alarms have automatic resumption events:

| Alarm Trigger | Resumption Event | Status |
|---------------|------------------|--------|
| `upsOnBattery` | `upsTrapPowerRestored` | ✅ Has resumption |
| `lowBattery` | `returnFromLowBattery` | ✅ Has resumption |
| `upsSleeping` | `upsWokeUp` | ✅ Has resumption |
| `envOverTemperature` | `envTemperatureNormal` | ✅ Has resumption |
| `envOverHumidity` | `envHumidityNormal` | ✅ Has resumption |
| `envUnderTemperature` | `envTemperatureNormal` | ✅ Has resumption |
| `envUnderHumidity` | `envHumidityNormal` | ✅ Has resumption |
| `envWaterAbnormal` | `envWaterNormal` | ✅ Has resumption |
| `upsBypass` | `upsBypassReturn` | ✅ Has resumption |
| `boostOn` | `returnFromBoost` | ✅ Has resumption |
| `buckOn` | `returnFromBuck` | ✅ Has resumption |
| `communicationLost` | `communicationEstablished` | ✅ Has resumption |
| `upsDiagnosticsFailed` | `upsDiagnosticsPassed` | ✅ Has resumption |
| `upsCapacityUnderrun` | `upsCapacityNormal` | ✅ Has resumption |
| `upsTemp` | `upsTempNormal` | ✅ Has resumption |
| `upsBypassacabnormal` | `upsBypassacnormal` | ✅ Has resumption |
| `upsBypassFreFail` | `upsBypassacnormal` | ✅ Has resumption |

## Alarms WITHOUT Resumption Events (30 alarms)

### 🔴 Critical Alarms Without Resumption (13 alarms)

These are the most serious alarms that typically require manual intervention:

| OID | Alarm Name | Severity | Description | Why No Resumption? |
|-----|------------|----------|-------------|-------------------|
| `1.3.6.1.4.1.935.0.2` | `upsOverLoad` | critical | SEVERE: Load > 100% of rated capacity | Requires load reduction - manual action |
| `1.3.6.1.4.1.935.0.4` | `upsDischarged` | critical | SEVERE: Runtime calibration discharge started | One-time calibration event |
| `1.3.6.1.4.1.935.0.54` | `upsShortCircuitShutdown` | critical | SEVERE: Short circuit shutdown | Requires physical repair - manual intervention |
| `1.3.6.1.4.1.935.0.55` | `upsInverterOutputFailShutdown` | critical | SEVERE: Inverter output fail shutdown | Hardware failure - requires repair |
| `1.3.6.1.4.1.935.0.56` | `upsBypassBreadkerOnShutdown` | critical | SEVERE: Manual bypass breaker on shutdown | Manual breaker operation - requires reset |
| `1.3.6.1.4.1.935.0.57` | `upsHighDCShutdown` | critical | SEVERE: High DC shutdown | Hardware fault - requires investigation |
| `1.3.6.1.4.1.935.0.58` | `upsEmergencyStop` | critical | SEVERE: Emergency stop | Manual emergency stop - requires reset |
| `1.3.6.1.4.1.935.0.61` | `upsOverTemperatureShutdown` | critical | SEVERE: Over temperature shutdown | Thermal protection - requires cooling |
| `1.3.6.1.4.1.935.0.62` | `upsOverLoadShutdown` | critical | SEVERE: Overload shutdown | Overload condition - requires load reduction |
| `1.3.6.1.4.1.935.0.67` | `upsLowBatteryShutdown` | critical | SEVERE: Low battery shutdown | Battery exhausted - requires power restoration |
| `1.3.6.1.2.1.33.1.6.3.8` | `upsAlarmOutputOverload` | critical | Output load exceeds UPS capacity | Requires load reduction |
| `1.3.6.1.2.1.33.1.6.3.18` | `upsAlarmGeneralFault` | critical | General UPS fault detected | Generic fault - requires investigation |
| `1.3.6.1.2.1.33.1.6.3.13` | `upsAlarmChargerFailed` | critical | Charger subsystem problem | Hardware failure - requires repair |
| `1.3.6.1.2.1.33.1.6.3.20` | `upsAlarmCommunicationsLost` | critical | Communication problem between agent and UPS | May auto-recover, but no explicit resumption |
| `1.3.6.1.2.1.33.1.6.3.2` | `upsAlarmBatteryDischarged` | critical | Battery is discharged | Requires charging - no explicit resumption |

### 🟡 Warning Alarms Without Resumption (17 alarms)

| OID | Alarm Name | Severity | Description | Why No Resumption? |
|-----|------------|----------|-------------|-------------------|
| `1.3.6.1.4.1.935.0.12` | `upsTurnedOff` | warning | WARNING: UPS turned off by management station | Manual action - requires manual turn-on |
| `1.3.6.1.4.1.935.0.15` | `upsRebootStarted` | warning | WARNING: Reboot sequence started | One-time event - system will restart |
| `1.3.6.1.4.1.935.0.20` | `envSmokeAbnormal` | warning | WARNING: Smoke is abnormal | Safety alarm - requires investigation |
| `1.3.6.1.4.1.935.0.22` | `envSecurityAbnormal` | warning | WARNING: Security is abnormal | Security breach - requires investigation |
| `1.3.6.1.4.1.935.0.26` | `envGasAbnormal` | warning | WARNING: Gas alarm | Safety alarm - requires investigation |
| `1.3.6.1.4.1.935.0.33` | `envSecurity1` | warning | WARNING: Security1 alarm | Security sensor - requires investigation |
| `1.3.6.1.4.1.935.0.34` | `envSecurity2` | warning | WARNING: Security2 alarm | Security sensor - requires investigation |
| `1.3.6.1.4.1.935.0.35` | `envSecurity3` | warning | WARNING: Security3 alarm | Security sensor - requires investigation |
| `1.3.6.1.4.1.935.0.36` | `envSecurity4` | warning | WARNING: Security4 alarm | Security sensor - requires investigation |
| `1.3.6.1.4.1.935.0.37` | `envSecurity5` | warning | WARNING: Security5 alarm | Security sensor - requires investigation |
| `1.3.6.1.4.1.935.0.38` | `envSecurity6` | warning | WARNING: Security6 alarm | Security sensor - requires investigation |
| `1.3.6.1.4.1.935.0.39` | `envSecurity7` | warning | WARNING: Security7 alarm | Security sensor - requires investigation |
| `1.3.6.1.4.1.935.0.47` | `upsRecroterror` | warning | WARNING: Rectifier rotation error | Hardware error - may require repair |
| `1.3.6.1.4.1.935.0.51` | `upsTest` | warning | WARNING: UPS test | One-time test event |
| `1.3.6.1.4.1.935.0.52` | `upsScheduleShutdown` | warning | WARNING: UPS schedule shutdown | Scheduled event - requires manual restart |
| `1.3.6.1.2.1.33.1.6.3.6` | `upsAlarmInputBad` | warning | Input voltage/frequency out of tolerance | May auto-recover, but no explicit resumption |
| `1.3.6.1.2.1.33.1.6.3.1` | `upsAlarmBatteryLow` | warning | Battery charge below acceptable threshold | May recover, but no explicit resumption |
| `1.3.6.1.2.1.33.1.6.3.3` | `upsAlarmBatteryTestFailure` | warning | Battery test failure detected | Test failure - requires investigation |
| `1.3.6.1.2.1.33.1.6.3.4` | `upsAlarmBatteryReplacement` | warning | Battery replacement indicator | Requires battery replacement |
| `1.3.6.1.2.1.33.1.6.3.5` | `upsAlarmBatteryTemperature` | warning | High battery temperature condition | May recover, but no explicit resumption |

## Why Some Alarms Don't Have Resumptions

### 1. **Hardware Failures**
- `upsShortCircuitShutdown` - Physical short circuit requires repair
- `upsInverterOutputFailShutdown` - Inverter hardware failure
- `upsChargerFailed` - Charger subsystem hardware failure
- `upsRecroterror` - Rectifier hardware error

### 2. **Manual Interventions Required**
- `upsEmergencyStop` - Emergency stop button pressed (manual reset needed)
- `upsTurnedOff` - UPS manually turned off (manual turn-on needed)
- `upsBypassBreadkerOnShutdown` - Manual bypass breaker operation
- `upsScheduleShutdown` - Scheduled shutdown (manual restart needed)

### 3. **Safety Alarms**
- `envSmokeAbnormal` - Smoke detection (requires investigation)
- `envGasAbnormal` - Gas detection (requires investigation)
- `envSecurity1-7` - Security sensor alarms (requires investigation)

### 4. **One-Time Events**
- `upsDischarged` - Runtime calibration (one-time test)
- `upsTest` - UPS test event
- `upsRebootStarted` - Reboot sequence (system will restart)

### 5. **Overload Conditions**
- `upsOverLoad` - Load exceeds capacity (requires load reduction)
- `upsOverLoadShutdown` - Overload shutdown (requires load reduction)
- `upsAlarmOutputOverload` - Output overload (requires load reduction)

### 6. **Thermal Protection**
- `upsOverTemperatureShutdown` - Over temperature (requires cooling)
- `upsAlarmBatteryTemperature` - High battery temp (may recover naturally)

### 7. **Battery Issues**
- `upsLowBatteryShutdown` - Battery exhausted (requires power restoration)
- `upsAlarmBatteryDischarged` - Battery discharged (requires charging)
- `upsAlarmBatteryReplacement` - Battery needs replacement

## Handling Alarms Without Resumptions

### For GPIO LED Control

Alarms without resumptions will:
- **Turn ON** the LED when triggered
- **Stay ON** until manually cleared or system restarted
- **Require manual intervention** to clear the LED

**Recommendation**: Implement a manual clear function or auto-clear after a timeout period.

### For Sound Alerts

Sound alerts will:
- **Play once** when the alarm triggers
- **Not automatically stop** (since there's no resumption event)
- **May repeat** if the alarm condition persists

**Recommendation**: Implement a cooldown period to prevent sound spam.

### For Logging

All alarms are logged regardless of whether they have resumptions. The log will show:
- **Event Type**: `🔴 ALARM TRIGGERED (trigger)`
- **No "Will be cleared by"** message (since there's no resumption)

## Recommendations

1. **Manual Clear Function**: Add a function to manually clear alarms that don't have resumptions
2. **Timeout-Based Clearing**: Auto-clear alarms after a configurable timeout period
3. **Status Monitoring**: Periodically check if alarm conditions still exist
4. **User Notification**: Clearly indicate which alarms require manual intervention
5. **Documentation**: Document which alarms require what type of intervention

## Complete List Summary

**Total Trigger Alarms**: 47
- **With Resumption**: 17 (36%)
- **Without Resumption**: 30 (64%)

**By Severity**:
- **Critical without resumption**: 15 alarms
- **Warning without resumption**: 17 alarms

