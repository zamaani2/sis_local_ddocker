#!/bin/bash

# Podman Auto-Start Script for SchoolApp
# This script ensures Podman containers start automatically on system boot

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.yml"
PROJECT_NAME="schoolapp"
LOG_FILE="/var/log/schoolapp-podman-startup.log"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to check if Podman is available and running
check_podman() {
    # Check if podman command exists
    if ! command -v podman >/dev/null 2>&1; then
        log_message "ERROR: Podman is not installed. Please install Podman first."
        log_message "Installation: sudo dnf install podman (RHEL/Fedora) or sudo apt install podman (Debian/Ubuntu)"
        exit 1
    fi
    
    # Check if podman-compose is available
    if ! command -v podman-compose >/dev/null 2>&1; then
        log_message "WARNING: podman-compose is not installed. Attempting to use podman compose (v2)..."
        # Try podman compose (v2 syntax)
        if podman compose version >/dev/null 2>&1; then
            log_message "Found podman compose (v2). Using podman compose commands."
            export USE_PODMAN_COMPOSE_V2=true
        else
            log_message "ERROR: podman-compose is not available."
            log_message "Installation: pip install podman-compose or sudo dnf install podman-compose"
            exit 1
        fi
    else
        export USE_PODMAN_COMPOSE_V2=false
    fi
    
    # Check if Podman is running (daemonless, but we check if it can execute)
    if ! podman info >/dev/null 2>&1; then
        log_message "ERROR: Podman is not accessible. Please check your Podman installation."
        log_message "Note: Podman is daemonless, but it needs to be properly configured."
        exit 1
    fi
    
    log_message "Podman is available and ready"
}

# Function to get the compose command
get_compose_cmd() {
    if [ "$USE_PODMAN_COMPOSE_V2" = "true" ]; then
        echo "podman compose"
    else
        echo "podman-compose"
    fi
}

# Function to check if containers are already running
check_containers() {
    local compose_cmd=$(get_compose_cmd)
    local running_containers=$(podman ps --filter "name=${PROJECT_NAME}" --format "{{.Names}}" | wc -l)
    if [ "$running_containers" -gt 0 ]; then
        log_message "Containers are already running"
        return 0
    fi
    return 1
}

# Function to start containers
start_containers() {
    log_message "Starting SchoolApp containers with Podman..."
    
    # Change to the project directory
    cd "$(dirname "$0")/.."
    
    local compose_cmd=$(get_compose_cmd)
    
    # Start containers in detached mode
    $compose_cmd up -d
    
    # Wait for services to be healthy
    log_message "Waiting for services to be healthy..."
    $compose_cmd ps
    
    # Check if all services are running
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        # Check for healthy containers (podman-compose may show different status)
        if $compose_cmd ps | grep -qE "(Up|healthy|running)"; then
            log_message "All services are healthy and running"
            return 0
        fi
        
        attempt=$((attempt + 1))
        log_message "Attempt $attempt/$max_attempts - Waiting for services to be healthy..."
        sleep 10
    done
    
    log_message "WARNING: Some services may not be fully healthy after $max_attempts attempts"
    return 1
}

# Function to stop containers gracefully
stop_containers() {
    log_message "Stopping SchoolApp containers..."
    cd "$(dirname "$0")/.."
    local compose_cmd=$(get_compose_cmd)
    $compose_cmd down
    log_message "Containers stopped"
}

# Main execution
main() {
    log_message "=== SchoolApp Podman Auto-Start Script ==="
    
    case "${1:-start}" in
        "start")
            check_podman
            
            if check_containers; then
                log_message "Containers are already running. Nothing to do."
                exit 0
            fi
            
            if start_containers; then
                log_message "SUCCESS: SchoolApp containers started successfully with Podman"
                echo -e "${GREEN}✓ SchoolApp is now running at http://localhost:8000${NC}"
            else
                log_message "ERROR: Failed to start containers"
                echo -e "${RED}✗ Failed to start SchoolApp containers${NC}"
                exit 1
            fi
            ;;
        "stop")
            stop_containers
            ;;
        "restart")
            stop_containers
            sleep 5
            main start
            ;;
        "status")
            check_podman
            cd "$(dirname "$0")/.."
            local compose_cmd=$(get_compose_cmd)
            $compose_cmd ps
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|status}"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"


