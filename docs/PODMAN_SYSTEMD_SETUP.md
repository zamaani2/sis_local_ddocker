# Podman Systemd Service Setup Guide

## Overview

This guide explains how to set up the Podman systemd service for automatic container startup on Linux servers.

## Service File

The service file is located at: `scripts/schoolapp-podman.service`

## Installation Steps

### 1. Copy Service File

```bash
sudo cp scripts/schoolapp-podman.service /etc/systemd/system/
```

### 2. Edit Service File

Edit the service file to set your project path:

```bash
sudo nano /etc/systemd/system/schoolapp-podman.service
```

Update these lines:

```ini
WorkingDirectory=/path/to/your/SchoolApp
ExecStart=/path/to/your/SchoolApp/scripts/podman-auto-start.sh start
ExecStop=/path/to/your/SchoolApp/scripts/podman-auto-start.sh stop
ExecReload=/path/to/your/SchoolApp/scripts/podman-auto-start.sh restart
```

**For rootless Podman (recommended):**

```ini
User=your-username
Group=your-username
Environment=XDG_RUNTIME_DIR=/run/user/$(id -u your-username)
```

**For rootful Podman:**

```ini
User=root
Group=root
```

### 3. Reload Systemd

```bash
sudo systemctl daemon-reload
```

### 4. Enable Service

```bash
sudo systemctl enable schoolapp-podman.service
```

### 5. Start Service

```bash
sudo systemctl start schoolapp-podman.service
```

### 6. Check Status

```bash
sudo systemctl status schoolapp-podman.service
```

## Service Management

### Start Service

```bash
sudo systemctl start schoolapp-podman.service
```

### Stop Service

```bash
sudo systemctl stop schoolapp-podman.service
```

### Restart Service

```bash
sudo systemctl restart schoolapp-podman.service
```

### View Logs

```bash
# Service logs
sudo journalctl -u schoolapp-podman.service -f

# Application logs
tail -f /var/log/schoolapp-podman-startup.log
```

### Disable Auto-Start

```bash
sudo systemctl disable schoolapp-podman.service
```

## Rootless vs Rootful Podman

### Rootless Podman (Recommended)

**Advantages:**

- More secure (no root privileges needed)
- User-level container management
- Better isolation

**Configuration:**

```ini
User=your-username
Group=your-username
Environment=XDG_RUNTIME_DIR=/run/user/$(id -u your-username)
```

**Requirements:**

- User must have Podman configured
- Containers run as your user
- No sudo needed for Podman commands

### Rootful Podman

**Configuration:**

```ini
User=root
Group=root
```

**Requirements:**

- Requires sudo for Podman commands
- Containers run as root
- Less secure but simpler setup

## Troubleshooting

### Service Fails to Start

1. **Check service status:**

   ```bash
   sudo systemctl status schoolapp-podman.service
   ```

2. **Check logs:**

   ```bash
   sudo journalctl -u schoolapp-podman.service -n 50
   ```

3. **Verify paths:**

   - Ensure WorkingDirectory path is correct
   - Ensure script paths are correct
   - Ensure scripts are executable: `chmod +x scripts/podman-auto-start.sh`

4. **Check Podman:**
   ```bash
   podman info
   ```

### Permission Issues (Rootless)

1. **Check user permissions:**

   ```bash
   id
   ```

2. **Verify Podman storage:**

   ```bash
   podman info | grep rootless
   ```

3. **Check XDG_RUNTIME_DIR:**
   ```bash
   echo $XDG_RUNTIME_DIR
   ```

### Network Issues

1. **Check network is online:**

   ```bash
   systemctl is-active network-online.target
   ```

2. **Verify Podman network:**
   ```bash
   podman network ls
   ```

## Differences from Docker Service

| Feature    | Docker Service                | Podman Service                     |
| ---------- | ----------------------------- | ---------------------------------- |
| Dependency | Requires `docker.service`     | No service dependency (daemonless) |
| User       | Usually root                  | Can be rootless (recommended)      |
| Startup    | Waits for Docker daemon       | Waits for network only             |
| Security   | Requires root or docker group | Can run as regular user            |

## Best Practices

1. **Use Rootless Podman** when possible for better security
2. **Test the service** before enabling auto-start
3. **Monitor logs** regularly
4. **Keep Podman updated** for security patches
5. **Use proper paths** - use absolute paths in service file

## Example: Complete Setup for Rootless Podman

```bash
# 1. Set your project path
PROJECT_PATH="/home/username/SchoolApp"
USERNAME="username"

# 2. Copy and edit service file
sudo cp scripts/schoolapp-podman.service /etc/systemd/system/
sudo sed -i "s|/path/to/your/SchoolApp|$PROJECT_PATH|g" /etc/systemd/system/schoolapp-podman.service
sudo sed -i "s|%i|$USERNAME|g" /etc/systemd/system/schoolapp-podman.service

# 3. Get user ID for XDG_RUNTIME_DIR
USER_ID=$(id -u $USERNAME)
sudo sed -i "s|/run/user/%i|/run/user/$USER_ID|g" /etc/systemd/system/schoolapp-podman.service

# 4. Enable and start
sudo systemctl daemon-reload
sudo systemctl enable schoolapp-podman.service
sudo systemctl start schoolapp-podman.service

# 5. Verify
sudo systemctl status schoolapp-podman.service
```

## Verification Checklist

- [ ] Service file copied to `/etc/systemd/system/`
- [ ] Paths updated in service file
- [ ] User/group configured correctly
- [ ] Systemd daemon reloaded
- [ ] Service enabled
- [ ] Service started successfully
- [ ] Containers are running: `podman ps`
- [ ] Application accessible: `curl http://localhost:8000`

## Related Documentation

- `docs/PODMAN_DEPLOYMENT_GUIDE.md` - General Podman deployment
- `docs/PODMAN_SCRIPTS_CREATED.md` - Podman scripts documentation
- `scripts/podman-auto-start.sh` - The startup script used by the service

---

**Status:** ✅ Ready for use  
**Compatibility:** Linux with systemd, Podman 3.x+
