import logging
import asyncio
from typing import Dict, Any, Optional, List

from .image_cache import get_image_cache
from .config import get_cache_config, get_monitoring_config

# Get configuration
cache_config = get_cache_config()
monitoring_config = get_monitoring_config()

# Configure logging
logger = logging.getLogger(__name__)
if monitoring_config["log_cache_operations"]:
    logger.setLevel(monitoring_config["log_level"])

# List of tools that return base64 images we want to cache
IMAGE_RETURNING_TOOLS = cache_config["image_returning_tools"]

# List of tools that should never be cached
NEVER_CACHE_TOOLS = cache_config["never_cache_tools"]

async def cache_tool_result(tool_name: str, tool_args: Dict[str, Any], result: Any) -> None:
    """
    Cache a tool result if it contains base64 images.
    
    Args:
        tool_name: Name of the tool that was executed
        tool_args: Arguments passed to the tool
        result: Result returned by the tool
    """
    # Skip tools that should never be cached
    if tool_name in NEVER_CACHE_TOOLS:
        return
    
    # Only cache tools that return base64 images
    if tool_name not in IMAGE_RETURNING_TOOLS:
        return
    
    try:
        # Parse the result if it's a JSON string
        if isinstance(result, str):
            import json
            try:
                result_dict = json.loads(result)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse result as JSON for tool {tool_name}")
                return
        else:
            result_dict = result
        
        # Check if the result contains a base64 field
        if isinstance(result_dict, dict) and "base64" in result_dict and result_dict["base64"]:
            # Get the base64 image data
            base64_data = result_dict["base64"]
            
            # Store the base64 image in Redis cache in the background
            print(f"\033[94m[REDIS CACHE] 💾 Caching base64 image for tool {tool_name} in the background\033[0m")
            logger.info(f"Caching base64 image for tool {tool_name} in the background")
            image_cache = get_image_cache()
            await image_cache.store_in_background(tool_name, tool_args, base64_data)
            
    except Exception as e:
        logger.exception(f"Error caching tool result: {str(e)}")

async def get_cached_image(tool_name: str, tool_args: Dict[str, Any]) -> Optional[str]:
    """
    Get a cached base64 image for a tool if available.
    
    Args:
        tool_name: Name of the tool
        tool_args: Arguments passed to the tool
        
    Returns:
        Cached base64 image or None if not found
    """
    # Skip tools that should never be cached
    if tool_name in NEVER_CACHE_TOOLS:
        return None
    
    # Only check cache for tools that return base64 images
    if tool_name not in IMAGE_RETURNING_TOOLS:
        return None
    
    try:
        # Get the cached base64 image
        image_cache = get_image_cache()
        cached_base64 = await image_cache.get(tool_name, tool_args)
        
        if cached_base64:
            logger.info(f"Found cached base64 image for tool {tool_name}")
            return cached_base64
        else:
            logger.info(f"No cached base64 image found for tool {tool_name}")
            return None
            
    except Exception as e:
        logger.exception(f"Error getting cached image: {str(e)}")
        return None

async def process_tool_result_with_cache(tool_name: str, tool_args: Dict[str, Any], result: Any) -> Any:
    """
    Process a tool result, potentially replacing base64 fields with cached values.
    
    Args:
        tool_name: Name of the tool
        tool_args: Arguments passed to the tool
        result: Original result from the tool
        
    Returns:
        Processed result, potentially with cached base64 values
    """
    # Cache the result for future use
    asyncio.create_task(cache_tool_result(tool_name, tool_args, result))
    
    # Return the original result (caching happens in the background)
    return result
