# Docker Setup Guide

This guide explains how to run MediaCrawler in Docker containers.

## Prerequisites

- Docker Desktop or Docker Engine installed
- `docker-compose` available in PATH
- No local Python or Node.js installation needed

## Quick Start

```bash
# Clone/navigate to project
cd media-crawler

# Build and start services
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

## Access URLs

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8080
- **API Documentation**: http://localhost:8080/docs
- **API Health Check**: http://localhost:8080/api/health

## Services

### Backend (Python/FastAPI)
- **Image**: python:3.11-slim
- **Port**: 8080
- **Entry**: `uv run uvicorn api.main:app`
- **Health Check**: Every 10s

### Frontend (React/Node.js)
- **Image**: node:20-alpine (multi-stage build)
- **Port**: 3000
- **Server**: `serve -s dist`
- **Health Check**: Every 10s
- **Depends on**: Backend service

## Common Commands

```bash
# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop containers
docker-compose stop

# Stop and remove containers
docker-compose down

# Rebuild images (clean)
docker-compose build --no-cache

# Execute shell in container
docker-compose exec backend bash
docker-compose exec frontend sh

# Restart services
docker-compose restart

# Clean up everything (images, volumes, networks)
docker-compose down -v --rmi all
```

## Development

### Live Reload
Backend volume mount is configured for live code reload:
```yaml
volumes:
  - ./:/app
```

Modify code in `api/` or `webui/src/` and changes will take effect.

### Environment Variables
Edit `docker-compose.yml` to customize:
- `PYTHONUNBUFFERED=1` - Python output buffering
- `REACT_APP_API_URL=http://backend:8080` - Frontend API endpoint

## Production Deployment

### Optimize for Production
1. Remove volume mounts from `docker-compose.yml`
2. Set `PYTHONUNBUFFERED=0` for better performance
3. Add resource limits:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
  frontend:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
```

### Using Nginx Reverse Proxy
Uncomment the nginx service in `docker-compose.yml` and create `nginx.conf`:

```nginx
upstream backend {
    server backend:8080;
}

upstream frontend {
    server frontend:3000;
}

server {
    listen 80;
    server_name _;

    location /api/ {
        proxy_pass http://backend;
    }

    location / {
        proxy_pass http://frontend;
    }
}
```

## Troubleshooting

### Port Already in Use
```bash
# Find process using port
lsof -i :8080
lsof -i :3000

# Kill process or use different ports in docker-compose.yml
```

### Container Won't Start
```bash
# Check logs
docker-compose logs backend

# Rebuild without cache
docker-compose build --no-cache
```

### Frontend Can't Connect to Backend
Ensure both services are healthy:
```bash
docker-compose ps
# STATUS should show "Up (healthy)" for both
```

### Clear Docker Cache
```bash
docker system prune -a
docker volume prune
```

## Image Sizes

- Backend: ~1.2GB (Python + dependencies)
- Frontend: ~200MB (Node.js + built React app)

## Health Checks

Both services include automatic health checks:

- **Backend**: HTTP GET `/api/health`
- **Frontend**: HTTP GET `http://localhost:3000`

If a service fails health check, it's automatically restarted.

## Support

For issues related to Docker setup, please:
1. Check logs: `docker-compose logs`
2. Verify Docker and docker-compose versions
3. Ensure sufficient disk space for images and volumes
