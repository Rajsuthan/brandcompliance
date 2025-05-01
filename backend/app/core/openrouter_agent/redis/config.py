import os
import json
import logging
from typing import Dict, Any

from .url_parser import parse_redis_url

logger = logging.getLogger(__name__)

# Get Redis configuration from environment
def get_redis_config_from_env() -> Dict[str, Any]:
    """
    Get Redis configuration from individual environment variables.
    """
    return {
        # Redis connection details
        "host": os.environ.get("REDIS_HOST", "localhost"),
        "port": int(os.environ.get("REDIS_PORT", 6379)),
        "username": os.environ.get("REDIS_USERNAME") or None,
        "password": os.environ.get("REDIS_PASSWORD") or None,
        "db": int(os.environ.get("REDIS_DB", 0)),
        "decode_responses": False,  # Keep as binary for base64 data
        "socket_timeout": int(os.environ.get("REDIS_SOCKET_TIMEOUT", 10)),
        "socket_connect_timeout": int(os.environ.get("REDIS_CONNECT_TIMEOUT", 10)),
        "retry_on_timeout": True,
        "max_connections": int(os.environ.get("REDIS_MAX_CONNECTIONS", 10)),
    }

# Redis configuration
# First check if REDIS_URL is set (Render format)
REDIS_URL = os.environ.get("REDIS_URL")
if REDIS_URL:
    logger.info(f"Using Redis URL from environment: {REDIS_URL[:10]}...")
    REDIS_CONFIG = parse_redis_url(REDIS_URL)
else:
    # Fall back to individual environment variables
    logger.info("Using Redis configuration from individual environment variables")
    REDIS_CONFIG = get_redis_config_from_env()

# Cache configuration
CACHE_CONFIG = {
    # Default TTL for cached items (24 hours by default)
    "default_ttl": int(os.environ.get("REDIS_CACHE_TTL", 60 * 60 * 24)),
    
    # Chunk size for large base64 strings (1MB by default)
    "chunk_size": int(os.environ.get("REDIS_CACHE_CHUNK_SIZE", 1024 * 1024)),
    
    # Maximum number of chunks to fetch in parallel
    "max_parallel_chunks": int(os.environ.get("REDIS_CACHE_MAX_PARALLEL_CHUNKS", 5)),
    
    # Tools that return base64 images we want to cache
    "image_returning_tools": [
        "read_guideline_page",
        # Add other tools that return base64 images here
    ],
    
    # Tools that should never be cached
    "never_cache_tools": [
        "attempt_completion",
        # Add other dynamic tools here
    ],
}

# Monitoring configuration
MONITORING_CONFIG = {
    # Enable detailed logging of cache operations
    "log_cache_operations": os.environ.get("REDIS_LOG_OPERATIONS", "True").lower() == "true",
    
    # Log level for cache operations
    "log_level": os.environ.get("REDIS_LOG_LEVEL", "INFO"),
    
    # Enable cache statistics collection
    "collect_stats": os.environ.get("REDIS_COLLECT_STATS", "True").lower() == "true",
}

def get_redis_config() -> Dict[str, Any]:
    """Get the Redis configuration."""
    return REDIS_CONFIG

def get_cache_config() -> Dict[str, Any]:
    """Get the cache configuration."""
    return CACHE_CONFIG

def get_monitoring_config() -> Dict[str, Any]:
    """Get the monitoring configuration."""
    return MONITORING_CONFIG
