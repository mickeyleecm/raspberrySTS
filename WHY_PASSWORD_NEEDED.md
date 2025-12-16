# Why Password is Needed

## The Problem

When you run `./start.sh` or `./restart.sh`, you're prompted for a password because:

1. **Port 162 requires root privileges** - SNMP trap port (162) is a privileged port (< 1024)
2. **The daemon must run as root** - Only root can bind to port 162
3. **Your user (nsluser) is not root** - So the script uses `sudo` to gain root privileges
4. **Sudoers is not configured yet** - So sudo asks for your password

## The Solution

Configure sudoers to allow `nsluser` to run these specific scripts **without a password**.

### Quick Fix

Ask someone with root access to run:

```bash
sudo ./setup_nsluser_sudo.sh
```

This will configure passwordless sudo for:
- `stop.sh`
- `start.sh`  
- `restart.sh`

### After Configuration

Once configured, you can run:

```bash
./start.sh
./restart.sh
```

**No password will be asked!** ✅

## Why This is Safe

The sudoers configuration only allows `nsluser` to run these **specific scripts** without a password. It does NOT give full sudo access. This is a secure, limited privilege escalation commonly used for service management.

## Current Situation

Right now, when you run `./start.sh`:
- ✅ Script detects port 162 needs root
- ✅ Script tries to use `sudo`
- ❌ Sudoers not configured → **Password prompt appears**

After running `sudo ./setup_nsluser_sudo.sh`:
- ✅ Script detects port 162 needs root
- ✅ Script uses `sudo`
- ✅ Sudoers configured → **No password needed!**

## Alternative: Enter Password Each Time

If you can't configure sudoers, you can:
1. Enter your password when prompted (if you have sudo access)
2. Or ask someone with root access to start/stop the daemon

But configuring sudoers is the recommended solution for convenience.

## Check If Already Configured

Test if passwordless sudo is already set up:

```bash
sudo -n ./start.sh
```

- If it works without asking for password → ✅ Already configured!
- If it asks for password → ❌ Need to run setup script



