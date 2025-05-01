import asyncio
import logging
from typing import Optional, Any, Dict

import redis.asyncio as redis

from .config import get_redis_config

logger = logging.getLogger(__name__)

class RedisConnectionManager:
    """Manages Redis connections and provides a consistent interface for Redis operations."""
    
    _instance: Optional['RedisConnectionManager'] = None
    _connection_pool: Optional[redis.ConnectionPool] = None
    _client: Optional[redis.Redis] = None
    
    def __new__(cls):
        """Singleton pattern to ensure only one connection manager exists."""
        if cls._instance is None:
            cls._instance = super(RedisConnectionManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the Redis connection manager."""
        if getattr(self, '_initialized', False):
            return
            
        # Get Redis configuration
        config = get_redis_config()
        
        # Create connection pool
        self._connection_pool = redis.ConnectionPool(
            **config
        )
        
        # Create Redis client
        self._client = redis.Redis(connection_pool=self._connection_pool)
        self._initialized = True
        logger.info(f"Redis connection manager initialized with config: {config}")
    
    @property
    def client(self) -> redis.Redis:
        """Get the Redis client instance."""
        if not self._client:
            raise RuntimeError("Redis client not initialized")
        return self._client
    
    async def ping(self) -> bool:
        """Check if Redis connection is alive."""
        try:
            return await self._client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {str(e)}")
            return False
    
    async def close(self):
        """Close the Redis connection pool."""
        if self._client:
            await self._client.close()
            logger.info("Redis connection closed")

# Convenience function to get the Redis client
def get_redis_client() -> redis.Redis:
    """Get the Redis client instance."""
    return RedisConnectionManager().client
