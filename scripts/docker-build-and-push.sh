#!/usr/bin/env bash
# Docker Build and Push Script for Docker Hub
# Repository: zamaan2/schooolsystem

set -e  # Exit on error

# Default values
TAG="${1:-latest}"
NO_BUILD=false
NO_PUSH=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --tag|-t)
            TAG="$2"
            shift 2
            ;;
        --no-build)
            NO_BUILD=true
            shift
            ;;
        --no-push)
            NO_PUSH=true
            shift
            ;;
        *)
            if [[ -z "$TAG" ]] || [[ "$TAG" == "latest" ]]; then
                TAG="$1"
            fi
            shift
            ;;
    esac
done

DOCKER_USERNAME="zamaan2"
REPOSITORY="schooolsystem"
IMAGE_NAME="${DOCKER_USERNAME}/${REPOSITORY}:${TAG}"

echo "==========================================="
echo "Docker Build and Push Script"
echo "==========================================="
echo "Repository: $IMAGE_NAME"
echo ""

# Check if Docker is running
echo "Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo "✗ Docker is not running. Please start Docker."
    exit 1
fi
echo "✓ Docker is running"

# Build the image
if [ "$NO_BUILD" = false ]; then
    echo ""
    echo "Building Docker image..."
    echo "This may take several minutes..."
    
    docker build -t "$IMAGE_NAME" .
    
    if [ $? -ne 0 ]; then
        echo "✗ Build failed!"
        exit 1
    fi
    
    echo "✓ Build completed successfully!"
    
    # Also tag as latest if a different tag was specified
    if [ "$TAG" != "latest" ]; then
        LATEST_TAG="${DOCKER_USERNAME}/${REPOSITORY}:latest"
        echo "Tagging as latest: $LATEST_TAG"
        docker tag "$IMAGE_NAME" "$LATEST_TAG"
    fi
else
    echo "Skipping build (--no-build specified)"
fi

# Push to Docker Hub
if [ "$NO_PUSH" = false ]; then
    echo ""
    echo "Pushing to Docker Hub..."
    echo "Make sure you're logged in: docker login"
    echo ""
    
    echo "Pushing $IMAGE_NAME ..."
    docker push "$IMAGE_NAME"
    
    if [ $? -ne 0 ]; then
        echo "✗ Push failed!"
        exit 1
    fi
    
    echo "✓ Push completed successfully!"
    
    # Push latest tag if it was created
    if [ "$TAG" != "latest" ]; then
        LATEST_TAG="${DOCKER_USERNAME}/${REPOSITORY}:latest"
        echo "Pushing $LATEST_TAG ..."
        docker push "$LATEST_TAG"
    fi
else
    echo "Skipping push (--no-push specified)"
fi

echo ""
echo "==========================================="
echo "✓ Done!"
echo "Image: $IMAGE_NAME"
echo ""
echo "To pull this image:"
echo "  docker pull $IMAGE_NAME"
echo ""
echo "To run this image:"
echo "  docker run -p 8000:8000 --env-file .env $IMAGE_NAME"
echo "==========================================="



