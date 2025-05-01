import logging
import asyncio
from typing import Dict, Any, Tuple, Optional

from .connection import get_redis_client, RedisConnectionManager

logger = logging.getLogger(__name__)

async def check_redis_health() -> Tuple[bool, Optional[str]]:
    """
    Check if Redis is available and responding.
    
    Returns:
        Tuple of (is_healthy, error_message)
    """
    try:
        # Get Redis client
        redis = get_redis_client()
        
        # Try to ping Redis
        result = await redis.ping()
        
        if result:
            logger.info("Redis health check: OK")
            return True, None
        else:
            error_msg = "Redis ping returned False"
            logger.error(f"Redis health check failed: {error_msg}")
            return False, error_msg
            
    except Exception as e:
        error_msg = f"Redis health check failed: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

async def initialize_redis() -> Tuple[bool, Optional[str]]:
    """
    Initialize Redis connection and perform health check.
    
    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Initialize connection manager (singleton)
        RedisConnectionManager()
        
        # Perform health check
        is_healthy, error = await check_redis_health()
        
        if is_healthy:
            # Set a test key to verify write access
            redis = get_redis_client()
            await redis.set("redis_health_check", "ok", ex=60)
            
            # Read back the test key
            test_value = await redis.get("redis_health_check")
            if test_value == b"ok":
                logger.info("Redis initialization successful")
                return True, None
            else:
                error_msg = f"Redis write/read test failed: expected 'ok', got '{test_value}'"
                logger.error(error_msg)
                return False, error_msg
        else:
            return False, error
            
    except Exception as e:
        error_msg = f"Redis initialization failed: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
