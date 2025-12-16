# Web Interface Restart Setup (No Password)

## Overview

This guide explains how to configure `restart.sh` to work without password when called from the web interface.

## The Problem

- Web interface runs as `www-data` user
- Web interface calls `restart.sh` as `nsluser`
- `restart.sh` needs root privileges (port 162)
- Without configuration, it asks for password (which web can't provide)

## Solution

Configure sudoers so that:
1. `nsluser` can run the scripts without password
2. `www-data` can run `restart.sh` as `nsluser` without password

## Setup Instructions

**Run as root:**

```bash
sudo ./setup_nsluser_sudo.sh
```

This will configure:
- ✅ `nsluser` can run `stop.sh`, `start.sh`, `restart.sh` without password
- ✅ `www-data` can run `restart.sh` as `nsluser` without password

## What Gets Configured

The setup script creates `/etc/sudoers.d/nsluser-raspberryrle` with:

```
# Allow nsluser to run scripts without password
nsluser ALL=(ALL) NOPASSWD: /path/to/stop.sh
nsluser ALL=(ALL) NOPASSWD: /path/to/start.sh
nsluser ALL=(ALL) NOPASSWD: /path/to/restart.sh

# Allow www-data to run restart.sh as nsluser without password
www-data ALL=(nsluser) NOPASSWD: /path/to/restart.sh
www-data ALL=(nsluser) NOPASSWD: /usr/bin/sudo -u nsluser /path/to/restart.sh
```

## How It Works

### From Command Line (nsluser)

```bash
# nsluser runs directly
./restart.sh
# → Detects need for sudo
# → Uses sudo automatically (no password)
# → Works! ✅
```

### From Web Interface (www-data → nsluser)

```php
// PHP code (www-data user)
sudo -u nsluser /path/to/restart.sh
// → www-data has permission to run as nsluser
// → nsluser has permission to use sudo
// → Works without password! ✅
```

## Verification

### Test 1: nsluser can run restart.sh

```bash
# Login as nsluser
su - nsluser

# Test without password
sudo -n ./restart.sh
```

Should work without asking for password.

### Test 2: www-data can run restart.sh as nsluser

```bash
# As root or with sudo
sudo -u www-data sudo -u nsluser /path/to/restart.sh
```

Should work without asking for password.

### Test 3: From web interface

1. Go to web dashboard
2. Click "Restart" button
3. Should work without errors
4. Check output - should see "Restart completed successfully!"

## Troubleshooting

### "sudo: a password is required"

The sudoers configuration is not set up. Run:
```bash
sudo ./setup_nsluser_sudo.sh
```

### "www-data is not in the sudoers file"

The setup script didn't run correctly. Check:
```bash
sudo cat /etc/sudoers.d/nsluser-raspberryrle
```

Should show both `nsluser` and `www-data` entries.

### "Permission denied" when www-data tries to run

Check file permissions:
```bash
ls -la /path/to/restart.sh
chmod +x /path/to/restart.sh
```

### Web interface still fails

Check PHP error logs:
```bash
tail -f /var/log/apache2/error.log
# or
tail -f /var/log/nginx/error.log
```

## Security Note

This configuration is secure because:
- ✅ Only specific scripts can be run without password
- ✅ `www-data` can only run `restart.sh` as `nsluser` (not as root)
- ✅ `nsluser` can only run the 3 management scripts (not arbitrary commands)
- ✅ No full sudo access granted

## Manual Configuration (if setup script doesn't work)

```bash
# Edit sudoers
sudo visudo -f /etc/sudoers.d/nsluser-raspberryrle

# Add these lines (adjust paths):
nsluser ALL=(ALL) NOPASSWD: /usr/local/src/raspberryRle/stop.sh
nsluser ALL=(ALL) NOPASSWD: /usr/local/src/raspberryRle/start.sh
nsluser ALL=(ALL) NOPASSWD: /usr/local/src/raspberryRle/restart.sh
www-data ALL=(nsluser) NOPASSWD: /usr/local/src/raspberryRle/restart.sh

# Save and verify
sudo visudo -c -f /etc/sudoers.d/nsluser-raspberryrle
```

