# Setup Guide for nsluser (No Sudo Access)

## Problem

You're logged in as `nsluser` and don't have sudo access, but the daemon needs to run as root (because port 162 requires root privileges).

## Solution

Configure sudoers to allow `nsluser` to run the management scripts (`stop.sh`, `start.sh`, `restart.sh`) **without a password**. This is a secure, common pattern for service management.

## Quick Setup

**Option 1: Use the setup script (Recommended)**

Ask someone with root access to run:

```bash
sudo ./setup_nsluser_sudo.sh
```

This script will:
- Verify the scripts exist
- Make them executable
- Create a sudoers configuration file
- Verify the configuration works

**Option 2: Manual setup**

If you have root access temporarily, or can ask someone to do this:

```bash
# 1. Get the full path to the scripts
cd /usr/local/src/raspberryRle  # or wherever your scripts are
SCRIPT_DIR=$(pwd)

# 2. Create sudoers file
sudo nano /etc/sudoers.d/nsluser-raspberryrle

# 3. Add these lines (replace /usr/local/src/raspberryRle with your actual path):
nsluser ALL=(ALL) NOPASSWD: /usr/local/src/raspberryRle/stop.sh
nsluser ALL=(ALL) NOPASSWD: /usr/local/src/raspberryRle/start.sh
nsluser ALL=(ALL) NOPASSWD: /usr/local/src/raspberryRle/restart.sh

# 4. Save and exit (Ctrl+X, Y, Enter)

# 5. Set correct permissions
sudo chmod 0440 /etc/sudoers.d/nsluser-raspberryrle

# 6. Verify syntax
sudo visudo -c -f /etc/sudoers.d/nsluser-raspberryrle
```

## After Setup

Once configured, you can run:

```bash
./restart.sh
```

The script will automatically use `sudo` when needed, **without asking for a password**.

## Verify It Works

Test that sudo works without password:

```bash
# This should work without asking for password
sudo ./stop.sh

# Or test with sudo -n (no prompt)
sudo -n ./stop.sh
```

If it works, you're all set!

## Troubleshooting

### "sudo: a password is required"

This means the sudoers configuration isn't set up yet. You need to:
1. Have someone with root access run `sudo ./setup_nsluser_sudo.sh`
2. Or manually configure sudoers as shown above

### "sudo: command not found"

Sudo is not installed. This is unusual on Debian/Raspberry Pi OS. You may need to install it, but typically it's pre-installed.

### "permission denied" when running scripts

Make sure the scripts are executable:
```bash
chmod +x stop.sh start.sh restart.sh
```

### Scripts can't find each other

Make sure you're running the scripts from the correct directory:
```bash
cd /usr/local/src/raspberryRle  # or your actual path
./restart.sh
```

## Security Note

This configuration only allows `nsluser` to run these **specific scripts** without a password. It does NOT give full sudo access. This is a secure, limited privilege escalation that's commonly used for service management.

## Alternative: If You Can't Configure Sudoers

If you absolutely cannot configure sudoers, you have these options:

1. **Ask someone with root access** to stop/start the daemon manually
2. **Use a different port** (above 1024) that doesn't require root - but this may not work for SNMP traps
3. **Run the daemon as a different user** with appropriate capabilities (requires system configuration)

The sudoers approach is the recommended solution.



