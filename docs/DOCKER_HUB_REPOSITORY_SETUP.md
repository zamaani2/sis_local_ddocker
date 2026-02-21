# Docker Hub Repository Setup Guide

This guide walks you through creating and configuring your Docker Hub repository for the SchoolApp project.

## Repository Information

- **Docker Hub Username**: `zamaan2`
- **Repository Name**: `schooolsystem`
- **Full Image Path**: `zamaan2/schooolsystem:tag`

## Step 1: Create Docker Hub Account (If Needed)

1. Go to https://hub.docker.com/
2. Click **"Sign Up"** (top right)
3. Choose a username: `zamaan2` (or use existing account)
4. Complete the registration process
5. Verify your email address

## Step 2: Create the Repository

### Method 1: Via Web Interface

1. **Login to Docker Hub**

   - Go to https://hub.docker.com/
   - Click **"Sign In"** (top right)
   - Enter your credentials

2. **Navigate to Repositories**

   - Click on your username (top right)
   - Select **"Repositories"** from the dropdown
   - Or go directly to: https://hub.docker.com/repositories

3. **Create New Repository**

   - Click the **"Create Repository"** button (top right)
   - Fill in the details:
     - **Repository Name**: `schooolsystem`
     - **Visibility**:
       - **Public** - Anyone can see and pull your image
       - **Private** - Only you (and collaborators) can access
     - **Short Description** (optional): "Django School Management System"
     - **Full Description** (optional): Add detailed information about your project
   - Click **"Create"**

4. **Verify Repository Created**
   - You should see your new repository at: https://hub.docker.com/r/zamaan2/schooolsystem
   - The page will show instructions for pushing your first image

### Method 2: Via Docker CLI (After First Push)

The repository can also be created automatically on the first push if you have the right permissions.

## Step 3: Login via Command Line

Before you can push images, you need to authenticate:

### Windows (PowerShell or Command Prompt)

```bash
docker login
```

You'll be prompted to enter:

- **Username**: `zamaan2`
- **Password**: Your Docker Hub password (or access token)

### Using Access Token (More Secure)

1. **Create Access Token**:

   - Go to https://hub.docker.com/settings/security
   - Click **"New Access Token"**
   - Name: `SchoolApp Push Token`
   - Permissions: **Read & Write**
   - Click **"Generate"**
   - **Copy the token** (you won't see it again!)

2. **Login with Token**:
   ```bash
   docker login
   # Username: zamaan2
   # Password: <paste your access token>
   ```

### Verify Login

```bash
docker info | findstr "Username"
```

Or check your Docker config file:

- Windows: `%USERPROFILE%\.docker\config.json`

## Step 4: Repository Settings (Optional)

After creating the repository, you can configure:

### Repository Settings

1. **Description**: Update the description with project details
2. **Collaborators**: Add team members who can push/pull
3. **Webhooks**: Set up automated actions
4. **Build Settings**: Connect GitHub for automated builds

### Recommended Settings

- **Visibility**: Choose based on your needs
  - **Public**: Good for open-source projects
  - **Private**: Better for proprietary applications
- **Readme**: Add a README.md to your repository page
- **Tags**: Use semantic versioning (v1.0.0, latest, etc.)

## Step 5: Verify Repository is Ready

Before pushing, verify:

1. ✅ Repository exists at: https://hub.docker.com/r/zamaan2/schooolsystem
2. ✅ You're logged in: Run `docker login`
3. ✅ Docker Desktop is running
4. ✅ You have push permissions (you're the owner)

## Quick Checklist

Before your first push:

```
☐ Docker Hub account created/accessed
☐ Repository "schooolsystem" created
☐ Logged in via CLI: docker login
☐ Docker Desktop is running
☐ Ready to build and push
```

## Troubleshooting

### "Repository does not exist"

**Solution**: Create the repository first using Step 2 above.

### "Access denied" or "Permission denied"

**Solutions**:

- Verify you're logged in: `docker login`
- Check repository name matches exactly: `schooolsystem`
- Ensure you own the repository or have push permissions
- Try logging out and back in: `docker logout` then `docker login`

### "Authentication failed"

**Solutions**:

- Verify your username and password
- Try using an access token instead of password
- Check if 2FA is enabled (you may need an access token)

### "Cannot connect to Docker daemon"

**Solution**: Start Docker Desktop (Windows/Mac) or Docker service (Linux)

## Next Steps

Once your repository is set up:

1. ✅ **Test the build**: Build locally first
2. ✅ **Push the image**: Use the provided scripts
3. ✅ **Verify on Docker Hub**: Check your repository page

See:

- [DOCKER_HUB_QUICK_START.md](../DOCKER_HUB_QUICK_START.md) - Quick start guide
- [DOCKER_HUB_PUSH_GUIDE.md](DOCKER_HUB_PUSH_GUIDE.md) - Detailed push instructions

## Repository URL

Once created, your repository will be available at:

- **Web Interface**: https://hub.docker.com/r/zamaan2/schooolsystem
- **Pull Command**: `docker pull zamaan2/schooolsystem:tag`
