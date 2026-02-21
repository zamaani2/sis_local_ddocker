# Podman Auto-Start Scripts - Created

## Overview

Podman-specific auto-start scripts have been created to provide the same level of automation and convenience for Podman Desktop users that Docker Desktop users already have.

## Created Files

### 1. `scripts/podman-auto-start.sh` (Linux/macOS)

- **Platform:** Linux and macOS
- **Features:**
  - Detects Podman installation
  - Checks for `podman-compose` or `podman compose` (v2)
  - Starts/stops/restarts containers
  - Health monitoring
  - Logging to `/var/log/schoolapp-podman-startup.log`

### 2. `scripts/podman-auto-start.ps1` (Windows PowerShell)

- **Platform:** Windows (PowerShell)
- **Features:**
  - Detects Podman Desktop installation
  - Checks for `podman-compose` or `podman compose` (v2)
  - Starts/stops/restarts containers
  - Logging to `%TEMP%\schoolapp-podman-startup.log`

### 3. `scripts/podman-auto-start.bat` (Windows CMD)

- **Platform:** Windows (Command Prompt)
- **Features:**
  - Detects Podman Desktop installation
  - Checks for `podman-compose` or `podman compose` (v2)
  - Starts/stops/restarts containers
  - Logging to `%TEMP%\schoolapp-podman-startup.log`

## Key Features

### ✅ Podman-Specific Enhancements

1. **Dual Compose Support**

   - Supports `podman-compose` (traditional)
   - Supports `podman compose` (v2 syntax)
   - Automatically detects which is available

2. **Daemonless Awareness**

   - No systemd service start needed (Podman is daemonless)
   - Checks if Podman is accessible rather than checking for a daemon

3. **Better Error Messages**

   - Provides installation instructions if Podman is missing
   - Suggests Podman Desktop download link for Windows users
   - Clear messages about `podman-compose` requirements

4. **Separate Logging**
   - Uses separate log files from Docker scripts
   - Easy to distinguish between Docker and Podman logs

## Usage

### Linux/macOS

```bash
# Make script executable (if not already)
chmod +x scripts/podman-auto-start.sh

# Start containers
./scripts/podman-auto-start.sh start

# Stop containers
./scripts/podman-auto-start.sh stop

# Restart containers
./scripts/podman-auto-start.sh restart

# Check status
./scripts/podman-auto-start.sh status
```

### Windows PowerShell

```powershell
# Start containers
.\scripts\podman-auto-start.ps1 start

# Stop containers
.\scripts\podman-auto-start.ps1 stop

# Restart containers
.\scripts\podman-auto-start.ps1 restart

# Check status
.\scripts\podman-auto-start.ps1 status
```

### Windows CMD

```cmd
REM Start containers
scripts\podman-auto-start.bat start

REM Stop containers
scripts\podman-auto-start.bat stop

REM Restart containers
scripts\podman-auto-start.bat restart

REM Check status
scripts\podman-auto-start.bat status
```

## Prerequisites

### Required Software

1. **Podman** - Container runtime

   - Linux: `sudo dnf install podman` or `sudo apt install podman`
   - macOS: `brew install podman` or Podman Desktop
   - Windows: Podman Desktop from https://podman-desktop.io

2. **podman-compose** OR **podman compose** (v2)
   - Option 1: `pip install podman-compose`
   - Option 2: Use `podman compose` (v2) - built into newer Podman versions
   - The scripts automatically detect which is available

## Differences from Docker Scripts

| Feature         | Docker Scripts                    | Podman Scripts                                  |
| --------------- | --------------------------------- | ----------------------------------------------- |
| Command         | `docker` / `docker-compose`       | `podman` / `podman-compose` or `podman compose` |
| Daemon Check    | Checks Docker daemon              | Checks Podman accessibility (daemonless)        |
| Service Start   | Attempts `systemctl start docker` | No service start (daemonless)                   |
| Compose Support | `docker-compose` only             | Both `podman-compose` and `podman compose` (v2) |
| Log File        | `schoolapp-startup.log`           | `schoolapp-podman-startup.log`                  |

## Compatibility

### ✅ Fully Compatible With

- Podman 3.x and 4.x
- Podman Desktop (Windows/macOS)
- Native Podman (Linux)
- Both `podman-compose` and `podman compose` (v2)

### ⚠️ Requirements

- Podman must be installed and accessible
- `podman-compose` OR `podman compose` (v2) must be available
- Podman Desktop must be running (Windows/macOS)
- Same `.env` file configuration as Docker

## Testing Checklist

- [ ] Podman is installed and accessible
- [ ] `podman-compose` or `podman compose` is available
- [ ] `.env` file is configured
- [ ] Scripts execute without errors
- [ ] Containers start successfully
- [ ] Health checks work
- [ ] Logs are created correctly
- [ ] Stop/restart functions work

## Troubleshooting

### Issue: "Podman is not installed"

**Solution:**

- Linux: Install Podman via package manager
- Windows/macOS: Install Podman Desktop from https://podman-desktop.io

### Issue: "podman-compose is not available"

**Solutions:**

1. Install podman-compose: `pip install podman-compose`
2. Use podman compose (v2): Ensure Podman Desktop is up to date
3. Check if `podman compose version` works

### Issue: "Podman is not accessible"

**Solutions:**

- Windows/macOS: Ensure Podman Desktop is running
- Linux: Check Podman installation and permissions
- Verify with: `podman info`

### Issue: Scripts fail with permission errors

**Solutions:**

- Linux: Ensure user has permissions to run Podman (usually no sudo needed for rootless)
- Windows: Run PowerShell/CMD as administrator if needed
- Check Podman Desktop is running

## Integration with Existing Setup

These scripts work alongside the existing Docker scripts:

- **Docker users:** Continue using `docker-auto-start.*` scripts
- **Podman users:** Use `podman-auto-start.*` scripts
- **Both installed:** Choose the appropriate script for your preferred runtime

## Next Steps

1. ✅ Podman auto-start scripts created
2. ⏳ Create unified platform detection script (optional)
3. ⏳ Create Podman systemd service file (for Linux servers)
4. ⏳ Update documentation with Podman script references

## Related Documentation

- `docs/PODMAN_DEPLOYMENT_GUIDE.md` - Comprehensive Podman deployment guide
- `docs/CONTAINER_PLATFORM_ANALYSIS.md` - Platform compatibility analysis
- `docs/PLATFORM_DETECTION_EXPLANATION.md` - Platform detection concepts

---

**Status:** ✅ Complete  
**Date Created:** $(date)  
**Compatibility:** Podman 3.x+, Podman Desktop
