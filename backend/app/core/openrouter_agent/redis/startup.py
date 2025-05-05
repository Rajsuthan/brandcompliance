import asyncio
import logging
from typing import Dict, Any, Optional

from .health import initialize_redis
from .config import get_redis_config, get_cache_config

logger = logging.getLogger(__name__)

async def initialize_redis_cache() -> bool:
    """
    Initialize the Redis cache system during application startup.
    
    Returns:
        True if initialization was successful, False otherwise
    """
    print("\033[95m[REDIS CACHE] 🔍 Initializing Redis cache system...\033[0m")
    logger.info("Initializing Redis cache system...")
    
    # Initialize Redis connection and check health
    success, error = await initialize_redis()
    
    if not success:
        logger.warning(f"Redis initialization failed: {error}")
        logger.warning("Continuing without Redis caching. Tool results will not be cached.")
        return False
    
    # Log configuration
    redis_config = get_redis_config()
    cache_config = get_cache_config()
    
    print(f"\033[92m[REDIS CACHE] 🔓 Successfully connected to Redis at {redis_config['host']}:{redis_config['port']}\033[0m")
    print(f"\033[92m[REDIS CACHE] ⏱️  Cache TTL: {cache_config['default_ttl'] // 3600} hours\033[0m")
    print(f"\033[92m[REDIS CACHE] 📷 Caching enabled for tools: {cache_config['image_returning_tools']}\033[0m")
    
    logger.info(f"Redis cache initialized successfully at {redis_config['host']}:{redis_config['port']}")
    logger.info(f"Cache TTL: {cache_config['default_ttl']} seconds")
    logger.info(f"Image returning tools: {cache_config['image_returning_tools']}")
    
    return True

# Function to be called during application startup
def setup_redis_cache():
    """
    Setup Redis cache during application startup.
    This function is synchronous and can be called from FastAPI startup event.
    If the event loop is already running, this function will log an error and return False.
    """
    loop = asyncio.get_event_loop()
    if loop.is_running():
        logger.error("Cannot call setup_redis_cache: event loop is already running. "
                     "Use 'await initialize_redis_cache()' in async contexts.")
        return False
    try:
        success = loop.run_until_complete(initialize_redis_cache())
        return success
    except Exception as e:
        logger.exception(f"Error setting up Redis cache: {str(e)}")
        return False


async def cleanup_redis_cache():
    """
    Clean up Redis connections during application shutdown.
    """
    from .connection import RedisConnectionManager
    
    try:
        # Get the connection manager instance and close it
        connection_manager = RedisConnectionManager()
        await connection_manager.close()
        logger.info("Redis connections closed successfully")
        return True
    except Exception as e:
        logger.exception(f"Error closing Redis connections: {str(e)}")
        return False


def shutdown_redis_cache():
    """
    Shutdown Redis cache during application shutdown.
    This function is synchronous and can be called from FastAPI shutdown event.
    If the event loop is already running, this function will log an error and return False.
    """
    loop = asyncio.get_event_loop()
    if loop.is_running():
        logger.error("Cannot call shutdown_redis_cache: event loop is already running. "
                     "Use 'await cleanup_redis_cache()' in async contexts.")
        return False
    try:
        success = loop.run_until_complete(cleanup_redis_cache())
        return success
    except Exception as e:
        logger.exception(f"Error shutting down Redis cache: {str(e)}")
        return False
