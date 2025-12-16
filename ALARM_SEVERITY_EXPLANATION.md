# Alarm Severity Levels Explanation

**Note**: All alarms in this system are from **SMAP SNMP R1e.mib** file only. RFC 1628 UPS MIB alarms have been removed.

## Purpose of Alarm Severity

The **alarm severity** system in `ups_snmp_trap_receiver.py` is used to:
1. **Classify the urgency** of each alarm condition
2. **Control GPIO LED behavior** - Different pins/actions for different severities
3. **Control sound alerts** - Different beep patterns for different severities
4. **Prioritize responses** - Helps operators know which alarms need immediate attention
5. **Filter notifications** - Can be used to filter which alarms trigger alerts

## Severity Levels

The system uses three severity levels: **`critical`**, **`warning`**, and **`info`**.

### 🔴 **CRITICAL** (Most Urgent)

**Purpose**: Life-threatening or equipment-damaging conditions that require **immediate action**.

**Characteristics**:
- **Immediate danger** to equipment or operations
- **System may shut down** or fail soon
- **Requires urgent human intervention**
- **Cannot be ignored**

**Examples from the code**:
- `upsEmergencyStop` - Emergency stop activated
- `upsShortCircuitShutdown` - Short circuit detected, system shutting down
- `upsLowBatteryShutdown` - Battery critically low, system will shut down
- `lowBattery` - Batteries low and will soon be exhausted
- `upsOverLoad` - Load exceeds 100% of rated capacity
- `communicationLost` - Communication to UPS lost
- `upsInverterOutputFailShutdown` - Inverter failure, system shutting down

**System Behavior**:
- **GPIO LED**: Triggers on `critical` pin (if configured separately) or shared pin
- **Sound Alert**: **3 beeps** (most attention-grabbing)
- **Logging**: Logged at CRITICAL level
- **Action**: **Immediate response required**

---

### 🟡 **WARNING** (Moderate Urgency)

**Purpose**: Conditions that indicate potential problems but are not immediately dangerous.

**Characteristics**:
- **Potential for problems** if not addressed
- **System is still operational** but in degraded state
- **Should be monitored** and addressed soon
- **May escalate** to critical if ignored

**Examples from the code**:
- `upsOnBattery` - UPS switched to battery power (power outage)
- `upsSleeping` - UPS entering sleep mode
- `envOverTemperature` - Environment temperature exceeded normal
- `envSmokeAbnormal` - Smoke detected
- `envWaterAbnormal` - Water leak detected
- `upsBypass` - UPS entering bypass mode
- `upsTemp` - UPS temperature overrun
- `upsTurnedOff` - UPS turned off by management

**System Behavior**:
- **GPIO LED**: Triggers on `warning` pin (if configured separately) or shared pin
- **Sound Alert**: **2 beeps** (moderate attention)
- **Logging**: Logged at WARNING level
- **Action**: **Monitor and address when possible**

---

### ℹ️ **INFO** (Informational)

**Purpose**: Status changes and normal operational events that are good to know but don't require action.

**Characteristics**:
- **Normal state changes** or positive events
- **No immediate action required**
- **Informational only**
- **System is operating normally**

**Examples from the code**:
- `powerRestored` - Utility power restored (good news!)
- `upsDiagnosticsPassed` - Self-test passed successfully
- `returnFromLowBattery` - Battery returned to normal
- `upsWokeUp` - UPS woke up from sleep mode
- `envTemperatureNormal` - Environment temperature returned to normal
- `communicationEstablished` - Communication with UPS established
- `upsInverterMode` - UPS in normal inverter mode

**System Behavior**:
- **GPIO LED**: **No LED action** (informational only)
- **Sound Alert**: **1 beep** (if enabled, but usually disabled)
- **Logging**: Logged at INFO level
- **Action**: **No action required** - just informational

---

## How Severity is Used in the Code

### 1. **GPIO LED Control**

```python
# Only trigger LED for warning and critical alarms
if severity in ['warning', 'critical']:
    self.led_controller.trigger_alarm(trap_name, severity)
    # Uses different GPIO pins based on severity
    pin = self.gpio_pins.get(severity, 'unknown')
```

**Behavior**:
- **Critical**: LED turns on/blinks on critical pin
- **Warning**: LED turns on/blinks on warning pin
- **Info**: No LED action (informational only)

### 2. **Sound Alert Control**

```python
# Different beep patterns for different severities
if severity_key == 'critical':
    self._play_beep(count=3, duration=self.beep_duration)  # 3 beeps
elif severity_key == 'warning':
    self._play_beep(count=2, duration=self.beep_duration)  # 2 beeps
else:
    self._play_beep(count=1, duration=self.beep_duration)  # 1 beep
```

**Behavior**:
- **Critical**: **3 beeps** (most urgent)
- **Warning**: **2 beeps** (moderate)
- **Info**: **1 beep** (if enabled, usually not)

### 3. **Logging Levels**

```python
# Log level is determined by severity
if 'Alarm' in trap_name or 'Fault' in trap_name or 'Failed' in trap_name:
    log_level = logging.CRITICAL
elif 'OnBattery' in trap_name or 'BatteryLow' in trap_name:
    log_level = logging.WARNING
else:
    log_level = logging.INFO
```

**Behavior**:
- **Critical**: Logged at `logging.CRITICAL` level
- **Warning**: Logged at `logging.WARNING` level
- **Info**: Logged at `logging.INFO` level

### 4. **Alarm Filtering**

The code only triggers alerts (LED/sound) for `warning` and `critical` alarms:

```python
# Only play sound for trigger events with warning/critical severity
if event_type == 'trigger' and severity in ['warning', 'critical']:
    self.sound_controller.trigger_alarm(trap_name, severity)
```

**Info alarms are filtered out** from triggering physical alerts because they're just status updates.

---

## Severity Mapping Examples

### Critical Alarms (from ALARM_SEVERITY dictionary):
```python
'upsEmergencyStop': 'critical',
'upsShortCircuitShutdown': 'critical',
'lowBattery': 'critical',
'upsOverLoad': 'critical',
'communicationLost': 'critical',
'upsInverterOutputFailShutdown': 'critical',
```

### Warning Alarms:
```python
'upsOnBattery': 'warning',
'upsSleeping': 'warning',
'envOverTemperature': 'warning',
'envSmokeAbnormal': 'warning',
'upsBypass': 'warning',
'upsTemp': 'warning',
```

### Info Alarms:
```python
'powerRestored': 'info',
'upsDiagnosticsPassed': 'info',
'returnFromLowBattery': 'info',
'upsWokeUp': 'info',
'envTemperatureNormal': 'info',
```

---

## Summary Table

| Severity | Urgency | GPIO LED | Sound Alert | Log Level | Action Required |
|----------|---------|----------|-------------|-----------|-----------------|
| **CRITICAL** | Immediate | ✅ Triggers | 3 beeps | CRITICAL | **Immediate** |
| **WARNING** | Moderate | ✅ Triggers | 2 beeps | WARNING | **Soon** |
| **INFO** | None | ❌ No action | 1 beep (optional) | INFO | **None** |

---

## Configuration

You can configure different GPIO pins for different severities:

```python
gpio_pins = {
    'critical': 17,  # Red LED for critical alarms
    'warning': 18,   # Yellow LED for warning alarms
    'info': None     # No pin for info (informational only)
}
```

This allows you to have:
- **Red LED** for critical alarms (most urgent)
- **Yellow LED** for warning alarms (moderate)
- **No LED** for info alarms (just logged)

---

## Best Practices

1. **Critical alarms** should always trigger both LED and sound alerts
2. **Warning alarms** should trigger alerts but may use different visual/audio patterns
3. **Info alarms** should only be logged, not trigger physical alerts
4. **Resumption events** (alarm clearing) typically don't trigger alerts, just clear existing alerts
5. **Use severity to prioritize** which alarms need immediate attention vs. monitoring

