# Platform Detection - Visual Comparison

## Current Script (Hardcoded to Docker)

```
┌─────────────────────────────────────┐
│  User runs: start-containers.sh    │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  Script checks: docker info         │
└─────────────────────────────────────┘
              │
        ┌─────┴─────┐
        │           │
     YES│           │NO
        │           │
        ▼           ▼
┌──────────┐  ┌──────────────┐
│ Use      │  │ ERROR:       │
│ docker   │  │ Docker not   │
│ commands │  │ running      │
└──────────┘  └──────────────┘
```

**Problem:** If user has Podman, script fails even though Podman is available!

---

## With Platform Detection

```
┌─────────────────────────────────────┐
│  User runs: start-containers.sh    │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  Script checks: docker info         │
└─────────────────────────────────────┘
              │
        ┌─────┴─────┐
        │           │
     YES│           │NO
        │           │
        ▼           ▼
┌──────────┐  ┌─────────────────────┐
│ Use      │  │ Check: podman info  │
│ docker   │  └─────────────────────┘
│ commands │           │
└──────────┘      ┌────┴────┐
                  │         │
               YES│         │NO
                  │         │
                  ▼         ▼
            ┌──────────┐ ┌──────────────┐
            │ Use      │ │ ERROR:       │
            │ podman   │ │ No container  │
            │ commands │ │ runtime      │
            └──────────┘ └──────────────┘
```

**Solution:** Script tries Docker first, then Podman, then shows helpful error.

---

## Side-by-Side Code Comparison

### Without Platform Detection (Current)

```bash
# Hardcoded - only works with Docker
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        echo "ERROR: Docker not running"
        exit 1
    fi
}

start_containers() {
    docker-compose up -d  # ← Hardcoded
}
```

**Result:**

- ✅ Works with Docker Desktop
- ❌ Fails with Podman Desktop
- ❌ User must know to use different commands

---

### With Platform Detection (Proposed)

```bash
# Detects which runtime is available
detect_runtime() {
    if docker info >/dev/null 2>&1; then
        COMPOSE_CMD="docker-compose"
        return 0
    fi

    if podman info >/dev/null 2>&1; then
        COMPOSE_CMD="podman-compose"
        return 0
    fi

    echo "ERROR: Install Docker or Podman"
    return 1
}

start_containers() {
    $COMPOSE_CMD up -d  # ← Uses detected command
}
```

**Result:**

- ✅ Works with Docker Desktop
- ✅ Works with Podman Desktop
- ✅ Automatically detects and uses correct commands

---

## User Experience Comparison

### Scenario: User has Podman Desktop installed

#### Without Platform Detection

```bash
$ ./scripts/docker-auto-start.sh start
ERROR: Docker is not running. Please start Docker Desktop.
# ❌ Script fails, user confused
# User must manually run: podman-compose up -d
```

#### With Platform Detection

```bash
$ ./scripts/start-containers.sh start
Detected: Podman
Using: podman-compose
Starting containers...
✓ SchoolApp is now running at http://localhost:8000
# ✅ Works automatically!
```

---

## Detection Logic Flowchart

```
                    START
                      │
                      ▼
            ┌─────────────────────┐
            │ Is docker command   │
            │ available?          │
            └─────────────────────┘
                      │
            ┌─────────┴─────────┐
            │                   │
          YES                   NO
            │                   │
            ▼                   ▼
    ┌──────────────┐    ┌──────────────┐
    │ Is docker    │    │ Is podman    │
    │ running?     │    │ available?   │
    │ (docker info)│    └──────────────┘
    └──────────────┘            │
            │            ┌───────┴───────┐
            │            │               │
          YES           YES              NO
            │            │               │
            ▼            ▼               ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ Use Docker   │ │ Use Podman   │ │ Show Error   │
    │ Commands     │ │ Commands     │ │ Message      │
    └──────────────┘ └──────────────┘ └──────────────┘
            │            │
            └─────┬──────┘
                  │
                  ▼
         ┌─────────────────┐
         │ Execute Commands │
         │ with Detected   │
         │ Runtime         │
         └─────────────────┘
```

---

## Command Mapping

### Docker Commands → Podman Equivalents

| Docker Command   | Podman Equivalent | Notes                   |
| ---------------- | ----------------- | ----------------------- |
| `docker`         | `podman`          | Direct replacement      |
| `docker-compose` | `podman-compose`  | Requires podman-compose |
| `docker ps`      | `podman ps`       | Same syntax             |
| `docker logs`    | `podman logs`     | Same syntax             |
| `docker exec`    | `podman exec`     | Same syntax             |
| `docker build`   | `podman build`    | Same syntax             |
| `docker volume`  | `podman volume`   | Same syntax             |
| `docker network` | `podman network`  | Same syntax             |

**Key Point:** Commands are nearly identical, just swap `docker` → `podman`

---

## Implementation Example

### Simple Detection Function

```bash
detect_container_runtime() {
    # Priority 1: Try Docker
    if command -v docker >/dev/null 2>&1; then
        if docker info >/dev/null 2>&1; then
            echo "docker"
            return 0
        fi
    fi

    # Priority 2: Try Podman
    if command -v podman >/dev/null 2>&1; then
        if podman info >/dev/null 2>&1; then
            echo "podman"
            return 0
        fi
    fi

    # No runtime found
    echo "none"
    return 1
}

# Usage
RUNTIME=$(detect_container_runtime)
case $RUNTIME in
    docker)
        COMPOSE_CMD="docker-compose"
        ;;
    podman)
        COMPOSE_CMD="podman-compose"
        ;;
    *)
        echo "ERROR: No container runtime found"
        exit 1
        ;;
esac

# Now use $COMPOSE_CMD throughout script
$COMPOSE_CMD up -d
```

---

## Summary

**Platform Detection = Smart Scripts**

Instead of:

- ❌ "Use docker-compose" (hardcoded)
- ❌ Fails if Docker not available

We get:

- ✅ "Detect which runtime is available"
- ✅ "Use appropriate commands automatically"
- ✅ "Works with both Docker and Podman"

**The script becomes intelligent and user-friendly!**




