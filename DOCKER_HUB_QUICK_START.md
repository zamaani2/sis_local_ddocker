# Quick Start: Push to Docker Hub

## Your Repository

- **Docker Hub Username**: `zamaan2`
- **Repository Name**: `schooolsystem`
- **Full Image**: `zamaan2/schooolsystem:tag`

## Step-by-Step Instructions

### 1. Login to Docker Hub (First Time Only)

Open PowerShell or Command Prompt and run:

```bash
docker login
```

Enter your Docker Hub username (`zamaan2`) and password when prompted.

### 2. Build and Push (Choose One Method)

#### Method 1: Using Batch File (Easiest - Windows)

```cmd
# Build and push with "latest" tag
scripts\docker-build-and-push.bat

# Build and push with custom tag (e.g., v1.0.0)
scripts\docker-build-and-push.bat v1.0.0
```

#### Method 2: Using PowerShell Script

```powershell
# Build and push with "latest" tag
.\scripts\docker-build-and-push.ps1

# Build and push with custom tag
.\scripts\docker-build-and-push.ps1 -Tag v1.0.0
```

#### Method 3: Manual Commands

```bash
# Build the image
docker build -t zamaan2/schooolsystem:latest .

# Push to Docker Hub
docker push zamaan2/schooolsystem:latest
```

### 3. Verify on Docker Hub

1. Go to: https://hub.docker.com/r/zamaan2/schooolsystem
2. You should see your pushed image

## Important Notes

1. **First time?** Create the repository on Docker Hub:

   - Go to https://hub.docker.com/repositories
   - Click "Create Repository"
   - Name: `schooolsystem`
   - Visibility: Public or Private

2. **Tag Examples**:

   - `latest` - Most recent version
   - `v1.0.0` - Version 1.0.0
   - `dev` - Development build

3. **Build Time**: First build takes 5-10 minutes. Subsequent builds are faster.

## Using Your Pushed Image

Once pushed, you can pull and run it anywhere:

```bash
# Pull the image
docker pull zamaan2/schooolsystem:latest

# Run the container
docker run -d -p 8000:8000 --env-file .env zamaan2/schooolsystem:latest
```

## Need Help?

See the detailed guide: [docs/DOCKER_HUB_PUSH_GUIDE.md](docs/DOCKER_HUB_PUSH_GUIDE.md)


