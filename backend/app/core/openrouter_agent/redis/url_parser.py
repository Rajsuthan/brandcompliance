import urllib.parse
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def parse_redis_url(url: str) -> Dict[str, Any]:
    """
    Parse a Redis URL into connection parameters.
    
    Supports formats like:
    - redis://username:password@host:port/db
    - rediss://username:password@host:port/db (SSL)
    
    Args:
        url: Redis URL string
        
    Returns:
        Dictionary with Redis connection parameters
    """
    try:
        # Parse the URL
        parsed = urllib.parse.urlparse(url)
        
        # Check if it's a Redis URL
        if parsed.scheme not in ['redis', 'rediss']:
            logger.warning(f"Invalid Redis URL scheme: {parsed.scheme}")
            return {}
        
        # Extract host and port
        host = parsed.hostname or 'localhost'
        port = parsed.port or 6379
        
        # Extract username and password
        username = None
        password = None
        if parsed.username:
            username = urllib.parse.unquote(parsed.username)
        if parsed.password:
            password = urllib.parse.unquote(parsed.password)
        
        # Extract database number
        db = 0
        if parsed.path and len(parsed.path) > 1:
            try:
                db = int(parsed.path[1:])
            except ValueError:
                logger.warning(f"Invalid database number in Redis URL: {parsed.path}")
        
        # Build the connection config
        config = {
            "host": host,
            "port": port,
            "db": db,
            "decode_responses": False,  # Keep as binary for base64 data
            "socket_timeout": 10,
            "socket_connect_timeout": 10,
            "retry_on_timeout": True,
            "max_connections": 10,
        }
        
        # Add username and password if provided
        if username:
            config["username"] = username
        if password:
            config["password"] = password
            
        # Add SSL if using rediss://
        if parsed.scheme == 'rediss':
            config["ssl"] = True
            config["ssl_cert_reqs"] = None  # Don't verify SSL cert
            
        return config
        
    except Exception as e:
        logger.exception(f"Error parsing Redis URL: {str(e)}")
        return {}
