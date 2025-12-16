# Email Notification Logic Explanation

## Overview

The UPS SNMP Trap Receiver sends email notifications **only for specific important alarms**. Not all alarms trigger emails - the system uses pattern matching to identify which alarms are important enough to send email notifications.

## Why Some Alarms Trigger Email and Others Don't

The email notification system uses **pattern matching** on alarm names and trap variables to determine if an email should be sent. This is a **filtering mechanism** to avoid email spam from informational or less critical alarms.

## Email Trigger Conditions

An email is sent **only if** one of the following conditions is met:

### 1. **Battery-Related Alarms** (WARNING severity)

Emails are sent if the trap name contains:
- `'OnBattery'` - UPS switched to battery power
- `'BatteryLow'` - Battery charge is low
- `'BatteryDischarged'` - Battery is discharged
- `'Battery'` - Any other battery-related alarm

**Examples:**
- ✅ `upsOnBattery` → **Email sent** (contains "OnBattery")
- ✅ `lowBattery` → **Email sent** (contains "BatteryLow")
- ✅ `upsLowBatteryShutdown` → **Email sent** (contains "Battery")
- ❌ `upsTemp` → **No email** (no battery-related keywords)
- ❌ `envOverTemperature` → **No email** (no battery-related keywords)

### 2. **Critical Fault Alarms** (CRITICAL severity)

Emails are sent if the trap name contains:
- `'Alarm'` - Any alarm condition
- `'Fault'` - Any fault condition
- `'Failed'` - Any failure condition

**Examples:**
- ✅ `upsDiagnosticsFailed` → **Email sent** (contains "Failed")
- ✅ `communicationLost` → **No email** (doesn't match pattern - **see issue below**)
- ✅ `upsShortCircuitShutdown` → **No email** (doesn't match pattern - **see issue below**)
- ❌ `upsInverterMode` → **No email** (informational state)
- ❌ `upsBypassMode` → **No email** (informational state)

**⚠️ Issue**: Many critical SMAP alarms don't match these patterns:
- `communicationLost` - No email (should send)
- `upsOverLoad` - No email (should send)
- `upsShortCircuitShutdown` - No email (should send)
- `upsEmergencyStop` - No email (should send)
- `upsLowBatteryShutdown` - No email (should send)

### 3. **Power Restoration Events** (INFO severity)

Emails are sent if trap variables contain:
- `'utility power has been restored'`
- `'power has been restored'`

**Examples:**
- ✅ `powerRestored` → **Email sent** (if trap variables contain restoration message)
- ❌ `upsWokeUp` → **No email** (unless variables contain restoration message)

### 4. **Battery Power Events** (WARNING severity)

Emails are sent if trap variables contain:
- `'switched to battery'`
- `'on battery power'`

**Examples:**
- ✅ `upsOnBattery` → **Email sent** (if trap variables contain battery message)
- ❌ `upsSleeping` → **No email** (unless variables contain battery message)

### 5. **Battery-Related OID Detection** (WARNING severity)

Emails are sent if:
- `battery_related=True` (detected from OID patterns)
- AND no other condition has already triggered an email

**Examples:**
- ✅ Battery OID detected → **Email sent** (if no other condition matched)

## Current Email Logic Code

```python
# Determine if this trap should trigger an email
should_send = False
severity = "INFO"
color = "blue"

# Check for specific important traps
if trap_name:
    if 'OnBattery' in trap_name or 'BatteryLow' in trap_name or 'BatteryDischarged' in trap_name:
        should_send = True
        severity = "WARNING"
        color = "orange"
    elif 'Alarm' in trap_name or 'Fault' in trap_name or 'Failed' in trap_name:
        should_send = True
        severity = "CRITICAL"
        color = "red"
    elif 'Battery' in trap_name:
        should_send = True
        severity = "WARNING"
        color = "orange"

# Also check for specific messages in trap variables
for oid, value in trap_vars.items():
    value_str = str(value).lower()
    if 'utility power has been restored' in value_str or 'power has been restored' in value_str:
        should_send = True
        severity = "INFO"
        color = "green"
    elif 'switched to battery' in value_str or 'on battery power' in value_str:
        should_send = True
        severity = "WARNING"
        color = "orange"

# Check if battery-related
if battery_related and not should_send:
    should_send = True
    severity = "WARNING"
    color = "orange"

if not should_send:
    return  # No email sent
```

## Email Cooldown Period

Even if an alarm matches the criteria, emails have a **5-minute cooldown period** to prevent duplicate emails for the same alarm:

```python
cooldown = 300  # 5 minutes
if current_time - last_time < cooldown:
    return  # Skip email (cooldown)
```

This means:
- Same alarm within 5 minutes → **No email** (cooldown)
- Same alarm after 5 minutes → **Email sent** (cooldown expired)

## Summary: Which Alarms Send Email?

### ✅ **Alarms That Send Email:**

| Alarm Name | Reason | Severity |
|------------|--------|----------|
| `upsOnBattery` | Contains "OnBattery" | WARNING |
| `lowBattery` | Contains "BatteryLow" | WARNING |
| `upsLowBatteryShutdown` | Contains "Battery" | WARNING |
| `upsDiagnosticsFailed` | Contains "Failed" | CRITICAL |
| `powerRestored` | Variables contain "power restored" | INFO |
| Battery OID detected | `battery_related=True` | WARNING |

### ❌ **Alarms That DON'T Send Email:**

| Alarm Name | Reason | Severity |
|------------|--------|----------|
| `communicationLost` | No matching pattern | CRITICAL |
| `upsOverLoad` | No matching pattern | CRITICAL |
| `upsShortCircuitShutdown` | No matching pattern | CRITICAL |
| `upsEmergencyStop` | No matching pattern | CRITICAL |
| `upsOverTemperatureShutdown` | No matching pattern | CRITICAL |
| `upsOverLoadShutdown` | No matching pattern | CRITICAL |
| `envOverTemperature` | No matching pattern | WARNING |
| `envSmokeAbnormal` | No matching pattern | WARNING |
| `envWaterAbnormal` | No matching pattern | WARNING |
| `upsBypass` | No matching pattern | WARNING |
| `upsInverterMode` | Informational state | INFO |
| `upsBypassMode` | Informational state | INFO |
| `upsCapacityNormal` | Informational state | INFO |

## Issues with Current Logic

### Problem 1: Many Critical Alarms Don't Send Email

Many critical SMAP alarms don't match the pattern matching logic:
- `communicationLost` - CRITICAL but no email
- `upsOverLoad` - CRITICAL but no email
- `upsShortCircuitShutdown` - CRITICAL but no email
- `upsEmergencyStop` - CRITICAL but no email
- `upsLowBatteryShutdown` - CRITICAL but no email (only matches if contains "Battery")

### Problem 2: Pattern Matching is Too Restrictive

The current logic only checks for:
- `'Alarm'`, `'Fault'`, `'Failed'` in trap name
- But SMAP alarms use different naming conventions:
  - `communicationLost` (not "Alarm")
  - `upsOverLoad` (not "Alarm")
  - `upsShortCircuitShutdown` (not "Alarm")
  - `upsEmergencyStop` (not "Alarm")

### Problem 3: Severity-Based Logic Would Be Better

Instead of pattern matching, the system should use the `ALARM_SEVERITY` dictionary:
- ✅ Send email for all `critical` alarms
- ✅ Send email for all `warning` alarms
- ❌ Don't send email for `info` alarms (or make it optional)

## Recommended Solution

The email notification logic should be **severity-based** instead of pattern-based:

```python
# Get severity from ALARM_SEVERITY dictionary
severity = ALARM_SEVERITY.get(trap_name, 'info')

# Send email for critical and warning alarms
if severity in ['critical', 'warning']:
    should_send = True
    if severity == 'critical':
        email_severity = "CRITICAL"
        color = "red"
    else:
        email_severity = "WARNING"
        color = "orange"
elif severity == 'info' and 'powerRestored' in trap_name:
    # Also send email for power restoration (good news)
    should_send = True
    email_severity = "INFO"
    color = "green"
```

This would ensure:
- ✅ All critical alarms send email
- ✅ All warning alarms send email
- ✅ Power restoration sends email (good news)
- ❌ Info alarms don't send email (unless power restoration)

## Current Behavior Summary

| Alarm Type | Email Sent? | Reason |
|------------|------------|--------|
| **Critical alarms with "Alarm/Fault/Failed"** | ✅ Yes | Pattern match |
| **Critical alarms without pattern** | ❌ No | No pattern match |
| **Warning alarms with "Battery"** | ✅ Yes | Pattern match |
| **Warning alarms without pattern** | ❌ No | No pattern match |
| **Info alarms (power restored)** | ✅ Yes | Variable check |
| **Info alarms (other)** | ❌ No | Not important enough |
| **Battery OID detected** | ✅ Yes | Battery-related flag |

## Configuration

Email notifications require:
1. **Email recipients** configured (`email_recipients`)
2. **SMTP server** configured (`smtp_server`)
3. **From email** configured (`from_email`)
4. **Email sender module** available (`email_sender.py`)

If any of these are missing, no emails will be sent (even if alarm matches criteria).

