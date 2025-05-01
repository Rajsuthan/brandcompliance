# Redis Deployment on Render

This guide explains how to set up Redis as a separate service on Render for the Brand Compliance AI project.

## Deployment Steps

### 1. Create a New Web Service on Render

1. Log in to your Render dashboard
2. Click "New +" and select "Web Service"
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: `brand-compliance-redis`
   - **Environment**: Docker
   - **Dockerfile Path**: `Dockerfile.redis`
   - **Region**: Choose the same region as your main application
   - **Instance Type**: Free (or paid if you need more memory)
   - **Auto-Deploy**: Enable

### 2. Configure Your Main Application

After your Redis service is deployed, you need to connect your main application to it:

1. Get the internal service URL from Render
   - This will be something like: `brand-compliance-redis:6379`
   - Render services in the same account can communicate via internal networking

2. Set the `REDIS_URL` environment variable in your main application:
   - Go to your main application's environment variables in Render
   - Add: `REDIS_URL=redis://brand-compliance-redis:6379`

## Local Development

For local development, you can run Redis using Docker Compose:

```bash
# Start Redis
docker-compose up -d redis

# Check if Redis is running
docker-compose ps

# Connect to Redis CLI
docker-compose exec redis redis-cli
```

## Memory Management

The Redis configuration in the Dockerfile is set to:

- **Maximum Memory**: 28MB (to stay within the 30MB limit)
- **Eviction Policy**: LRU (Least Recently Used)
- **Persistence**: Enabled with AOF and RDB

This ensures Redis will automatically remove the least recently used items when memory is full, which is ideal for a caching system.

## Monitoring

You can monitor your Redis instance by connecting to the Redis CLI:

```bash
# Connect to Redis CLI (locally)
docker-compose exec redis redis-cli

# Check memory usage
INFO memory

# Check cache statistics
INFO stats
```

On Render, you can view logs from the Redis service in the Render dashboard.
