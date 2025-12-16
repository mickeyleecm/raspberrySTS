# Mute Button Fix - Issue Resolution

## Problem Statement

The mute button on the STS panel (GPIO pin 19) only worked when there was an active alarm. When pressed without an alarm or after an alarm resolved, the button failed to properly toggle the mute state.

## Root Cause

In `ups_snmp_trap_receiver_v3.py`, the `_mute_button_callback()` function had conditional logic that only enabled the buzzer when unmuting IF `self.alarm_status` was True. This caused the following issues:

1. **With active alarm**: Mute/unmute worked as expected
2. **Without alarm**: Button appeared to not work because:
   - When muting: buzzer was already off (no alarm), so no visible change
   - When unmuting: buzzer remained off because no alarm was active
3. **After alarm resolves**: Same as "without alarm" scenario

The code at lines 3627-3642 had this problematic logic:
```python
# Check if we're unmuting (changed from True to False) and alarm is active
if old_value and not new_value and self.alarm_status:
    # Only enabled buzzer if alarm was active
    ...
else:
    # Otherwise disabled buzzer (even when just toggling state)
    ...
```

## Solution

Simplified the mute button callback logic to properly handle all scenarios:

**Before:**
- Complex conditional logic that checked both old/new values AND alarm status
- Only enabled buzzer when unmuting IF alarm was active
- Disabled buzzer in all other cases

**After:**
- Clean, straightforward logic:
  - **When muting (BUZZER_MUTED = True)**: Disable buzzer regardless of alarm state
  - **When unmuting (BUZZER_MUTED = False)**: 
    - If alarm is active → Enable buzzer
    - If no alarm → Keep buzzer disabled
    
This ensures the mute state is always properly toggled, and the buzzer behavior correctly reflects both the mute state AND the alarm state.

## Code Changes

**File**: `ups_snmp_trap_receiver_v3.py`  
**Lines**: 3597-3642

### Changed Logic:

```python
# Update buzzer state based on BOTH buzzer_muted AND alarm_status
# Buzzer should be enabled ONLY when: (1) not muted AND (2) alarm is active
if new_value:
    # Muted (BUZZER_MUTED = True): disable buzzer regardless of alarm state
    if self.panel_led_controller and hasattr(self.panel_led_controller, 'disable_buzzer'):
        self.panel_led_controller.disable_buzzer()
        self.logger.info(f"Buzzer disabled (muted) - ALARM_STATUS={self.alarm_status}")
else:
    # Unmuted (BUZZER_MUTED = False): enable buzzer ONLY if alarm is active
    if self.alarm_status:
        # Alarm is active - enable buzzer
        if self.panel_led_controller and hasattr(self.panel_led_controller, 'enable_buzzer'):
            self.panel_led_controller.enable_buzzer(
                continuous=True,
                beep_pattern=True,
                beep_duration=0.2,
                beep_pause=0.5,
                volume=75
            )
            self.logger.info(f"Buzzer enabled (unmuted and ALARM_STATUS is True)")
    else:
        # No active alarm - ensure buzzer is disabled
        if self.panel_led_controller and hasattr(self.panel_led_controller, 'disable_buzzer'):
            self.panel_led_controller.disable_buzzer()
            self.logger.info(f"Buzzer disabled (unmuted but no active alarm - ALARM_STATUS is False)")
```

## Testing Scenarios

To validate the fix, test these scenarios on the Raspberry Pi 4 with the STS panel:

### Scenario 1: Mute button with active alarm
1. Trigger an alarm on the Borri STS (e.g., simulate power loss)
2. Verify buzzer is sounding
3. Press mute button
4. **Expected**: Buzzer stops, `BUZZER_MUTED = True` in config.py
5. Press mute button again
6. **Expected**: Buzzer resumes, `BUZZER_MUTED = False` in config.py

### Scenario 2: Mute button without alarm
1. Ensure no active alarm (normal operation)
2. Verify buzzer is off
3. Press mute button multiple times
4. **Expected**: 
   - `BUZZER_MUTED` toggles in config.py (True → False → True...)
   - Buzzer remains off (correct, since no alarm)
   - Button works properly (state changes are logged)

### Scenario 3: Mute button after alarm resolves
1. Trigger an alarm, then mute the buzzer
2. Resolve the alarm (e.g., restore power)
3. Press mute button to unmute
4. **Expected**:
   - `BUZZER_MUTED = False` in config.py
   - Buzzer remains off (correct, since alarm resolved)
   - Button works properly (state changes are logged)

### Scenario 4: Unmute before new alarm
1. Ensure no alarm and buzzer is muted (`BUZZER_MUTED = True`)
2. Press mute button to unmute
3. Trigger a new alarm
4. **Expected**:
   - Step 2: `BUZZER_MUTED = False`, buzzer stays off
   - Step 3: Buzzer sounds immediately (not muted, alarm active)

## Verification

Check the logs in `/home/runner/work/raspberrySTS/raspberrySTS/logs/ups_trapsYYYYMMDD.log` for:

1. Button press events:
   ```
   [BUTTON] Mute button PRESSED detected - processing toggle...
   [BUTTON] Mute button pressed - BUZZER_MUTED changed from False to True (config.py updated successfully)
   ```

2. Buzzer state changes:
   ```
   Buzzer disabled (muted) - ALARM_STATUS=True
   Buzzer enabled (unmuted and ALARM_STATUS is True)
   Buzzer disabled (unmuted but no active alarm - ALARM_STATUS is False)
   ```

3. Config.py updates:
   ```python
   BUZZER_MUTED = True  # or False
   ```

## Related Code

The mute button fix is consistent with alarm handling logic elsewhere in the code:

- **Line 2966**: Alarm triggers check `if not self.buzzer_muted` before enabling buzzer
- **Line 3358**: LED state changes check `if not self.buzzer_muted` before enabling buzzer
- **Line 3626**: Mute button callback checks `if self.alarm_status` when unmuting

All locations properly respect both the mute state AND alarm state.

## Hardware Requirements

- Raspberry Pi 4 with GPIO access
- Borri STS 32A panel with mute button on GPIO pin 19
- Buzzer/speaker connected to GPIO pin 18

## Future Improvements

Consider adding:
1. Visual feedback (LED) to indicate mute state
2. Audio confirmation (short beep) when toggling mute
3. Persistence of mute state across system restarts (already implemented via config.py)
