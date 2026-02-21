# Docker Hub Push Guide

This guide explains how to build and push your SchoolApp Docker image to Docker Hub.

## Repository Information

- **Docker Hub Username**: `zamaan2`
- **Repository Name**: `schooolsystem`
- **Full Image Name**: `zamaan2/schooolsystem:tag`

## Prerequisites

1. **Docker Desktop** installed and running
2. **Docker Hub account** (username: `zamaan2`)
3. **Logged into Docker Hub** from your terminal

### Login to Docker Hub

Before pushing, make sure you're logged in:

```bash
docker login
```

Enter your Docker Hub username and password when prompted.

## Quick Start

### Option 1: Using PowerShell Script (Windows - Recommended)

```powershell
# Build and push with default tag "latest"
.\scripts\docker-build-and-push.ps1

# Build and push with custom tag
.\scripts\docker-build-and-push.ps1 -Tag v1.0.0

# Build only (don't push)
.\scripts\docker-build-and-push.ps1 -NoPush

# Push only (skip build)
.\scripts\docker-build-and-push.ps1 -NoBuild
```

### Option 2: Using Bash Script (Linux/macOS/Git Bash)

```bash
# Make script executable (first time only)
chmod +x scripts/docker-build-and-push.sh

# Build and push with default tag "latest"
./scripts/docker-build-and-push.sh

# Build and push with custom tag
./scripts/docker-build-and-push.sh v1.0.0

# Build only (don't push)
./scripts/docker-build-and-push.sh --no-push

# Push only (skip build)
./scripts/docker-build-and-push.sh --no-build
```

### Option 3: Manual Commands

If you prefer to run commands manually:

```bash
# 1. Build the image
docker build -t zamaan2/schooolsystem:latest .

# Or with a specific tag
docker build -t zamaan2/schooolsystem:v1.0.0 .

# 2. Login to Docker Hub (if not already logged in)
docker login

# 3. Push the image
docker push zamaan2/schooolsystem:latest

# Or push with specific tag
docker push zamaan2/schooolsystem:v1.0.0
```

## Tag Naming Best Practices

Use semantic versioning for tags:

- `latest` - Always points to the most recent stable version
- `v1.0.0` - Specific version numbers
- `v1.0.0-beta` - Pre-release versions
- `dev` - Development builds

Example:

```powershell
# Build and push version 1.0.0
.\scripts\docker-build-and-push.ps1 -Tag v1.0.0

# Build and push as latest
.\scripts\docker-build-and-push.ps1 -Tag latest
```

## Verifying the Push

After pushing, you can verify on Docker Hub:

1. Go to https://hub.docker.com/r/zamaan2/schooolsystem
2. You should see your pushed tags listed

You can also verify locally:

```bash
# Pull the image to verify
docker pull zamaan2/schooolsystem:latest

# Check image details
docker images zamaan2/schooolsystem
```

## Using the Pushed Image

Once pushed, you or others can pull and use the image:

```bash
# Pull the image
docker pull zamaan2/schooolsystem:latest

# Run the container
docker run -d \
  -p 8000:8000 \
  --env-file .env \
  --name schoolapp \
  zamaan2/schooolsystem:latest
```

Or in `docker-compose.yml`, you can reference the image:

```yaml
services:
  django:
    image: zamaan2/schooolsystem:latest
    # ... rest of configuration
```

## Troubleshooting

### Build Fails

- **Issue**: Build fails during `collectstatic`

  - **Solution**: This is normal if some settings require a database. The static files will be collected at runtime.

- **Issue**: Build is slow
  - **Solution**: This is normal for the first build. Subsequent builds will be faster due to Docker layer caching.

### Push Fails

- **Issue**: Authentication failed

  - **Solution**: Run `docker login` again and verify your credentials

- **Issue**: Permission denied

  - **Solution**: Make sure you own the repository `zamaan2/schooolsystem` on Docker Hub

- **Issue**: Repository doesn't exist
  - **Solution**: Create the repository on Docker Hub first:
    1. Go to https://hub.docker.com/repositories
    2. Click "Create Repository"
    3. Name it `schooolsystem`
    4. Set visibility (public or private)

### Docker Not Running

- **Issue**: "Cannot connect to Docker daemon"
  - **Solution**: Start Docker Desktop (Windows/Mac) or Docker service (Linux)

## Image Size Optimization

The current Dockerfile is optimized for size, but you can further optimize by:

1. Using multi-stage builds
2. Removing unnecessary files in `.dockerignore`
3. Combining RUN commands to reduce layers

Current `.dockerignore` already excludes:

- Virtual environments
- Media files
- Logs
- Database files
- Cache files

## Next Steps

After successfully pushing:

1. **Set up automated builds** on Docker Hub (optional):

   - Connect your GitHub repository
   - Configure auto-build on git push

2. **Document usage** in your README:

   - Add pull instructions
   - Include environment variable requirements
   - Provide example docker-compose configurations

3. **Create tags** for different environments:
   - `production` - Production-ready builds
   - `staging` - Staging environment
   - `development` - Development builds
