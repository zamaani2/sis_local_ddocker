# Platform Detection in Scripts - Explanation

## What is Platform Detection?

**Platform detection** is the ability of a script to automatically identify which container runtime (Docker or Podman) is available on the system and use the appropriate commands accordingly.

## Current State (Without Platform Detection)

### Problem: Scripts are Hardcoded

Currently, all scripts are **hardcoded** to use Docker commands:

**Example from `scripts/docker-auto-start.sh`:**

```bash
# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        log_message "ERROR: Docker is not running..."
        exit 1
    fi
    log_message "Docker is running"
}

# Function to start containers
start_containers() {
    docker-compose up -d  # ← Hardcoded to Docker
    docker-compose ps      # ← Hardcoded to Docker
}
```

**What happens with Podman Desktop:**

- ❌ Script fails because it only checks for `docker`
- ❌ Uses `docker-compose` which doesn't exist with Podman
- ❌ User must manually use `podman-compose` commands

## What Platform Detection Would Do

### With Platform Detection

A script would:

1. **Detect** which container runtime is available (Docker or Podman)
2. **Set variables** for the appropriate commands
3. **Use those variables** throughout the script
4. **Work automatically** with either platform

### Example Flow

```
Script Starts
    ↓
Check: Is Docker available?
    ↓
    YES → Use docker/docker-compose commands
    NO  → Check: Is Podman available?
              ↓
          YES → Use podman/podman-compose commands
          NO  → Error: No container runtime found
```

## Implementation Examples

### Example 1: Bash Script with Platform Detection

```bash
#!/bin/bash

# Platform Detection Function
detect_container_runtime() {
    # Check for Docker
    if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
        CONTAINER_CMD="docker"
        COMPOSE_CMD="docker-compose"
        RUNTIME="docker"
        echo "Detected: Docker"
        return 0
    fi

    # Check for Podman
    if command -v podman >/dev/null 2>&1 && podman info >/dev/null 2>&1; then
        CONTAINER_CMD="podman"
        COMPOSE_CMD="podman-compose"
        RUNTIME="podman"
        echo "Detected: Podman"
        return 0
    fi

    # No runtime found
    echo "ERROR: Neither Docker nor Podman is available"
    return 1
}

# Use detected runtime
if ! detect_container_runtime; then
    exit 1
fi

# Now use the detected commands
echo "Using: $RUNTIME"
$COMPOSE_CMD up -d
$COMPOSE_CMD ps
```

### Example 2: PowerShell Script with Platform Detection

```powershell
# Platform Detection Function
function Get-ContainerRuntime {
    # Check for Docker
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        try {
            docker info | Out-Null
            return @{
                Runtime = "docker"
                ContainerCmd = "docker"
                ComposeCmd = "docker-compose"
            }
        } catch {
            # Docker installed but not running
        }
    }

    # Check for Podman
    if (Get-Command podman -ErrorAction SilentlyContinue) {
        try {
            podman info | Out-Null
            return @{
                Runtime = "podman"
                ContainerCmd = "podman"
                ComposeCmd = "podman-compose"
            }
        } catch {
            # Podman installed but not running
        }
    }

    # No runtime found
    Write-Error "Neither Docker nor Podman is available"
    return $null
}

# Use detected runtime
$Runtime = Get-ContainerRuntime
if ($null -eq $Runtime) {
    exit 1
}

Write-Host "Using: $($Runtime.Runtime)"
& $Runtime.ComposeCmd up -d
& $Runtime.ComposeCmd ps
```

### Example 3: Unified Wrapper Script

A single script that works with both:

```bash
#!/bin/bash
# scripts/start-containers.sh - Platform-agnostic script

# Detect platform
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
    RUNTIME="Docker"
elif command -v podman >/dev/null 2>&1 && podman info >/dev/null 2>&1; then
    COMPOSE_CMD="podman-compose"
    RUNTIME="Podman"
else
    echo "ERROR: No container runtime found. Please install Docker Desktop or Podman Desktop."
    exit 1
fi

echo "Detected: $RUNTIME"
echo "Using: $COMPOSE_CMD"

# Use the detected command
$COMPOSE_CMD up -d
$COMPOSE_CMD ps
```

## Benefits of Platform Detection

### 1. **User-Friendly**

- Users don't need to know which platform they have
- Script automatically works with either

### 2. **Single Script**

- One script works for both Docker and Podman
- No need for separate scripts

### 3. **Flexibility**

- Easy to add support for other runtimes (e.g., containerd)
- Future-proof

### 4. **Better Error Messages**

- Can tell user exactly what's missing
- Can suggest installation steps

## Comparison: Before vs After

### Before (Current - Hardcoded)

```bash
# User with Podman Desktop runs:
./scripts/docker-auto-start.sh start

# Result:
ERROR: Docker is not running. Please start Docker Desktop.
# ❌ Fails even though Podman is available
```

### After (With Platform Detection)

```bash
# User with Podman Desktop runs:
./scripts/start-containers.sh start

# Result:
Detected: Podman
Using: podman-compose
Starting containers...
# ✅ Works automatically
```

## Real-World Example

### Scenario 1: User has Docker Desktop

```bash
$ ./scripts/start-containers.sh
Detected: Docker
Using: docker-compose
✓ Starting containers with Docker...
```

### Scenario 2: User has Podman Desktop

```bash
$ ./scripts/start-containers.sh
Detected: Podman
Using: podman-compose
✓ Starting containers with Podman...
```

### Scenario 3: User has both installed

```bash
$ ./scripts/start-containers.sh
Detected: Docker (preferred)
Using: docker-compose
✓ Starting containers with Docker...
```

### Scenario 4: User has neither

```bash
$ ./scripts/start-containers.sh
ERROR: No container runtime found.
Please install one of the following:
  - Docker Desktop: https://www.docker.com/products/docker-desktop
  - Podman Desktop: https://podman-desktop.io
```

## Implementation Priority

### High Priority Functions to Detect

1. **Container Runtime Detection**

   - Check if `docker` or `podman` command exists
   - Verify it's actually running

2. **Compose Command Detection**

   - Check for `docker-compose` or `podman-compose`
   - Handle both v1 and v2 compose formats

3. **Health Check Commands**
   - Use `docker ps` or `podman ps`
   - Use `docker logs` or `podman logs`

### Medium Priority

4. **Volume Management**

   - `docker volume` vs `podman volume`
   - Different storage locations

5. **Network Management**
   - `docker network` vs `podman network`
   - Network naming differences

## Code Pattern for Platform Detection

### Standard Pattern

```bash
# 1. Detect runtime
detect_runtime() {
    if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
        export CONTAINER_CMD="docker"
        export COMPOSE_CMD="docker-compose"
        return 0
    fi

    if command -v podman >/dev/null 2>&1 && podman info >/dev/null 2>&1; then
        export CONTAINER_CMD="podman"
        export COMPOSE_CMD="podman-compose"
        return 0
    fi

    return 1
}

# 2. Use detected commands
if detect_runtime; then
    $COMPOSE_CMD up -d
    $CONTAINER_CMD ps
else
    echo "No container runtime found"
    exit 1
fi
```

## Summary

**Platform detection** means scripts automatically:

- ✅ Detect which container runtime is available
- ✅ Use the correct commands (docker vs podman)
- ✅ Work with either Docker Desktop or Podman Desktop
- ✅ Provide helpful error messages if neither is found

**Without platform detection:**

- ❌ Scripts only work with Docker
- ❌ Podman users must use manual commands
- ❌ Separate scripts needed for each platform

**With platform detection:**

- ✅ One script works for both platforms
- ✅ Automatic detection and command selection
- ✅ Better user experience
