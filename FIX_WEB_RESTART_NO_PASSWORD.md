# Fix Web Interface Restart (No Password Required)

## Problem

When the web interface tries to restart the daemon, it shows:
- "Password:" prompt
- "[WARNING] Root privileges required. Using sudo..."
- Failed to kill root-owned processes
- Error: "spawn su nsluser -c cd ... && ./restart.sh"

## Root Cause

The PHP code (`php/api/restart.php`) tries multiple methods to run `restart.sh`:
1. **Method 1**: `sudo -u nsluser` (should work but wasn't configured correctly)
2. **Method 2**: `runuser -u nsluser`
3. **Method 3**: SSH key
4. **Method 4**: `expect` with `su` (requires password - this was being used)

Method 1 wasn't working because sudoers wasn't configured properly, so it fell back to Method 4 which requires a password.

## Solution

### Step 1: Run the Setup Script (as root)

```bash
sudo ./setup_nsluser_sudo.sh
```

This configures:
- ✅ `nsluser` can run `stop.sh`, `start.sh`, `restart.sh` without password
- ✅ `www-data` can run `restart.sh` as `nsluser` without password

### Step 2: Verify Configuration

Check the sudoers file was created:

```bash
sudo cat /etc/sudoers.d/nsluser-raspberryrle
```

Should show:
```
nsluser ALL=(ALL) NOPASSWD: /path/to/stop.sh
nsluser ALL=(ALL) NOPASSWD: /path/to/start.sh
nsluser ALL=(ALL) NOPASSWD: /path/to/restart.sh
www-data ALL=(nsluser) NOPASSWD: /path/to/restart.sh
```

### Step 3: Test from Command Line

Test that www-data can run restart.sh as nsluser:

```bash
sudo -u www-data sudo -u nsluser /path/to/restart.sh
```

Should work without password.

### Step 4: Test from Web Interface

1. Go to web dashboard
2. Click "Restart" button
3. Should work without errors
4. Should see "Restart completed successfully!"

## What Was Fixed

### 1. Updated `setup_nsluser_sudo.sh`
- Now configures `www-data` to run `restart.sh` as `nsluser` without password
- Uses absolute path (restart.sh changes to its own directory anyway)

### 2. Updated `php/api/restart.php`
- Improved Method 1 (sudo) detection
- Tries direct execution first: `sudo -u nsluser /absolute/path/to/restart.sh`
- Falls back to `sh -c` method if needed
- Better error detection and logging

### 3. How It Works Now

**From Web Interface:**
```
www-data → sudo -u nsluser /path/to/restart.sh
         → nsluser runs restart.sh
         → restart.sh uses sudo (passwordless) to stop/start
         → Success! ✅
```

## Troubleshooting

### Still Asking for Password?

1. **Check sudoers file exists:**
   ```bash
   sudo ls -la /etc/sudoers.d/nsluser-raspberryrle
   ```

2. **Verify syntax:**
   ```bash
   sudo visudo -c -f /etc/sudoers.d/nsluser-raspberryrle
   ```

3. **Check file permissions:**
   ```bash
   ls -la /etc/sudoers.d/nsluser-raspberryrle
   # Should be: -r--r----- (0440)
   ```

4. **Test manually:**
   ```bash
   sudo -u www-data sudo -n -u nsluser /path/to/restart.sh
   ```

### "Permission denied" Error?

Check script permissions:
```bash
ls -la /path/to/restart.sh
chmod +x /path/to/restart.sh
```

### Still Using expect Method?

Check PHP error logs:
```bash
tail -f /var/log/apache2/error.log
# or
tail -f /var/log/nginx/error.log
```

Look for: "Passwordless sudo not configured" - this means Method 1 failed.

## Security Note

This configuration is secure:
- ✅ Only specific scripts can be run without password
- ✅ `www-data` can only run `restart.sh` as `nsluser` (not as root)
- ✅ `nsluser` can only run the 3 management scripts (not arbitrary commands)
- ✅ No full sudo access granted

## After Setup

Once configured:
- ✅ Web interface can restart without password
- ✅ `nsluser` can run `./restart.sh` without password
- ✅ No password prompts
- ✅ Works automatically

