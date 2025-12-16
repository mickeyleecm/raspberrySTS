# How to Run the UPS SNMP Trap Receiver

## Method 1: Using VS Code Run Menu (Recommended for Development)

### Setup (One-time):
1. Open the project in VS Code
2. The `.vscode/launch.json` file is already configured with run configurations

### Running:
1. Press `F5` or go to **Run > Start Debugging**
2. Select one of these configurations from the dropdown:
   - **"UPS Trap Receiver (Port 1162)"** - Runs on port 1162 (no admin needed)
   - **"UPS Trap Receiver (Port 162 - Admin)"** - Runs on port 162 (requires admin)
   - **"UPS Trap Receiver (Custom Port & Log)"** - Custom configuration

### Alternative: Run without Debugging
1. Go to **Run > Run Without Debugging** (or press `Ctrl+F5`)
2. Select the configuration from the dropdown

---

## Method 2: Using Batch Files (Windows - Easiest)

### Quick Run (Port 1162):
1. Double-click `run_ups_receiver.bat`
   - This runs on port 1162 (no administrator needed)

### Run on Port 162:
1. Right-click `run_ups_receiver_port162.bat`
2. Select **"Run as Administrator"**
   - This runs on port 162 (requires admin privileges)

---

## Method 3: Command Line / PowerShell

### PowerShell or Command Prompt:
```bash
# Port 1162 (no admin needed)
python ups_snmp_trap_receiver.py --port 1162

# Port 162 (requires Administrator)
# Right-click PowerShell > Run as Administrator, then:
python ups_snmp_trap_receiver.py --port 162

# With custom log file
python ups_snmp_trap_receiver.py --port 1162 --log-file C:\Logs\ups_traps.log
```

### Short form (using -p instead of --port):
```bash
python ups_snmp_trap_receiver.py -p 1162
```

---

## Method 4: Windows Run Dialog (Win+R)

1. Press `Win + R` to open Run dialog
2. Type:
   ```
   cmd /k python "C:\Project\Raspberfry\Program\ups_snmp_trap_receiver.py" --port 1162
   ```
   (Adjust the path to match your actual file location)
3. Press Enter

---

## Method 5: Create a Desktop Shortcut

1. Right-click on `run_ups_receiver.bat`
2. Select **"Create shortcut"**
3. Move the shortcut to your Desktop
4. Double-click to run anytime!

---

## Quick Reference

| Method | Port 1162 | Port 162 | Admin Required? |
|--------|-----------|----------|-----------------|
| VS Code Run Menu | ✅ Yes | ✅ Yes | Port 162 only |
| Batch File | ✅ `run_ups_receiver.bat` | ✅ `run_ups_receiver_port162.bat` | Port 162 only |
| Command Line | ✅ `python ... --port 1162` | ✅ `python ... --port 162` | Port 162 only |
| Windows Run | ✅ Yes (with full path) | ✅ Yes (with full path) | Port 162 only |

---

## Tips

- **For Development/Testing**: Use port 1162 (no admin needed)
- **For Production**: Use port 162 (standard SNMP trap port)
- **Check if running**: Look for "Starting UPS SNMP Trap Receiver" message
- **Stop the program**: Press `Ctrl+C` in the terminal

