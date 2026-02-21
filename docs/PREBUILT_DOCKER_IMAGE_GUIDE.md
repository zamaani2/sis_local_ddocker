# Prebuilt Docker Image Guide

This guide shows how to run the project with prebuilt images from Docker Hub (instead of building locally).

## Why use prebuilt images?

- Avoid local build failures when Docker cannot reach base images (for example `python:3.11-slim`).
- Start faster with already-built application images.
- Keep deployment consistent across machines.

## Images used

- Django: `cise1/sis-django:latest`
- Postgres: `postgres:15`
- Nginx: `nginx:alpine`

## Compose support already added

`docker-compose.yml` now supports:

- `DJANGO_IMAGE` (default: `cise1/sis-django:latest`)
- `DJANGO_PULL_POLICY` (default: `missing`)

So you can choose prebuilt mode at runtime without editing compose files.

## Run with prebuilt Django image (PowerShell)

```powershell
cd "C:\Users\Administrator\Videos\Django\SIS_local_Docker"
$env:DJANGO_IMAGE="cise1/sis-django:latest"
$env:DJANGO_PULL_POLICY="always"
docker compose pull django
docker compose up -d --no-build
```

`--no-build` is important: it prevents local Dockerfile build and uses pulled images only.

## Return to local build mode

```powershell
cd "C:\Users\Administrator\Videos\Django\SIS_local_Docker"
Remove-Item Env:DJANGO_IMAGE -ErrorAction SilentlyContinue
Remove-Item Env:DJANGO_PULL_POLICY -ErrorAction SilentlyContinue
docker compose up -d --build
```

## CI/CD image updates

Your GitHub Actions workflow builds and pushes updated images on each push to GitHub.  
To enable Docker Hub push in Actions, set repository secrets:

- `DOCKER_USERNAME`
- `DOCKER_PASSWORD` (Docker Hub PAT)

Then each push updates `latest` tags for your service images.

## Troubleshooting

### Error: cannot resolve `registry-1.docker.io`

If you see DNS/proxy errors during local build, use prebuilt mode:

1. `docker compose pull django`
2. `docker compose up -d --no-build`

If pulls also fail, check:

- Internet connectivity
- DNS settings
- HTTPS proxy settings in Docker Desktop
- Firewall/antivirus network filtering


