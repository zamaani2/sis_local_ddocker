#!/bin/bash

# Docker Auto-Start Script for SchoolApp
# This script ensures Docker containers start automatically on system boot

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.yml"
PROJECT_NAME="schoolapp"
LOG_FILE="/var/log/schoolapp-startup.log"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        log_message "ERROR: Docker is not running. Starting Docker service..."
        sudo systemctl start docker
        sleep 5
        
        if ! docker info >/dev/null 2>&1; then
            log_message "ERROR: Failed to start Docker service"
            exit 1
        fi
    fi
    log_message "Docker is running"
}

# Function to check if containers are already running
check_containers() {
    local running_containers=$(docker ps --filter "name=${PROJECT_NAME}" --format "{{.Names}}" | wc -l)
    if [ "$running_containers" -gt 0 ]; then
        log_message "Containers are already running"
        return 0
    fi
    return 1
}

# Function to start containers
start_containers() {
    log_message "Starting SchoolApp containers..."
    
    # Change to the project directory
    cd "$(dirname "$0")/.."
    
    # Start containers in detached mode
    docker-compose up -d
    
    # Wait for services to be healthy
    log_message "Waiting for services to be healthy..."
    docker-compose ps
    
    # Check if all services are running
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose ps | grep -q "Up (healthy)"; then
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
    docker-compose down
    log_message "Containers stopped"
}

# Main execution
main() {
    log_message "=== SchoolApp Docker Auto-Start Script ==="
    
    case "${1:-start}" in
        "start")
            check_docker
            
            if check_containers; then
                log_message "Containers are already running. Nothing to do."
                exit 0
            fi
            
            if start_containers; then
                log_message "SUCCESS: SchoolApp containers started successfully"
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
            check_docker
            cd "$(dirname "$0")/.."
            docker-compose ps
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|status}"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
