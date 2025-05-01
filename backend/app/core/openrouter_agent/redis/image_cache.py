import json
import time
import hashlib
import logging
from typing import Dict, Any, Optional, List, Tuple, Union
import asyncio
import base64

from .connection import get_redis_client
from .config import get_cache_config, get_monitoring_config

logger = logging.getLogger(__name__)

# Get configuration
cache_config = get_cache_config()
monitoring_config = get_monitoring_config()

# Constants from configuration
DEFAULT_CHUNK_SIZE = cache_config["chunk_size"]  # Default: 1MB chunks
DEFAULT_TTL = cache_config["default_ttl"]  # Default: 24 hours in seconds
MAX_PARALLEL_CHUNKS = cache_config["max_parallel_chunks"]  # Default: 5 chunks in parallel


class ImageCache:
    """Redis-based cache for large base64 encoded images with chunking support.
    
    This class handles caching large base64 encoded images by splitting them into
    manageable chunks and storing them in Redis with appropriate metadata.
    """
    
    def __init__(self, prefix: str = "guideline_image", chunk_size: int = DEFAULT_CHUNK_SIZE, ttl: int = DEFAULT_TTL):
        """Initialize the image cache.
        
        Args:
            prefix: Key prefix for Redis keys
            chunk_size: Size of each chunk in bytes
            ttl: Time-to-live for cache entries in seconds
        """
        self.prefix = prefix
        self.chunk_size = chunk_size
        self.ttl = ttl
        self.redis = get_redis_client()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "stores": 0,
            "errors": 0,
            "chunk_stores": 0,
            "chunk_retrievals": 0
        }
    
    def _generate_key(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Generate a deterministic cache key based on tool name and arguments.
        
        Args:
            tool_name: Name of the tool being cached
            args: Tool arguments (excluding large base64 data)
            
        Returns:
            A string key for Redis
        """
        # Create a copy of args without any large base64 data to avoid huge keys
        filtered_args = {}
        for k, v in args.items():
            # Skip large string values that might be base64 data
            if isinstance(v, str) and len(v) > 1000 and ("," in v[:100] or ";" in v[:100]):
                filtered_args[k] = f"<base64_data_{len(v)}bytes>"
            else:
                filtered_args[k] = v
        
        # Create a deterministic string representation and hash it
        key_data = f"{tool_name}:{json.dumps(filtered_args, sort_keys=True)}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{self.prefix}:{tool_name}:{key_hash}"
    
    async def _store_chunks(self, base_key: str, data: str) -> Dict[str, Any]:
        """Split and store data in chunks.
        
        Args:
            base_key: Base Redis key for the image
            data: Base64 encoded image data
            
        Returns:
            Metadata about the stored chunks
        """
        # Convert string to bytes if needed
        if isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = data
            
        # Split into chunks
        chunks = [data_bytes[i:i+self.chunk_size] for i in range(0, len(data_bytes), self.chunk_size)]
        chunk_count = len(chunks)
        
        # Store metadata
        metadata = {
            "chunk_count": chunk_count,
            "total_size": len(data_bytes),
            "chunk_size": self.chunk_size,
            "created_at": int(time.time()),
            "expires_at": int(time.time()) + self.ttl
        }
        
        # Store metadata
        await self.redis.set(
            f"{base_key}:metadata", 
            json.dumps(metadata).encode('utf-8'),
            ex=self.ttl
        )
        
        # Store chunks in parallel with pipeline
        pipe = self.redis.pipeline()
        for i, chunk in enumerate(chunks):
            pipe.set(f"{base_key}:chunk:{i}", chunk, ex=self.ttl)
            self.stats["chunk_stores"] += 1
        
        await pipe.execute()
        print(f"\033[94m[REDIS CACHE] 💾 Stored {chunk_count} chunks ({len(data_bytes) // 1024}KB) for key {base_key}\033[0m")
        logger.debug(f"Stored {chunk_count} chunks for key {base_key}")
        return metadata
    
    async def _retrieve_chunks(self, base_key: str) -> Optional[bytes]:
        """Retrieve and combine chunks for an image.
        
        Args:
            base_key: Base Redis key for the image
            
        Returns:
            Combined data from all chunks or None if not found
        """
        # Get metadata
        metadata_bytes = await self.redis.get(f"{base_key}:metadata")
        if not metadata_bytes:
            return None
            
        metadata = json.loads(metadata_bytes.decode('utf-8'))
        chunk_count = metadata["chunk_count"]
        
        # Retrieve chunks in batches to avoid too many concurrent operations
        all_chunks = []
        for batch_start in range(0, chunk_count, MAX_PARALLEL_CHUNKS):
            batch_end = min(batch_start + MAX_PARALLEL_CHUNKS, chunk_count)
            batch_keys = [f"{base_key}:chunk:{i}" for i in range(batch_start, batch_end)]
            
            # Get chunks in parallel
            chunk_data = await self.redis.mget(batch_keys)
            self.stats["chunk_retrievals"] += len(batch_keys)
            
            # Check if any chunks are missing
            if None in chunk_data:
                logger.error(f"Missing chunks for {base_key}, cache may be corrupted")
                self.stats["errors"] += 1
                return None
                
            all_chunks.extend(chunk_data)
        
        # Combine chunks
        combined_data = b''.join(all_chunks)
        
        # Verify size
        if len(combined_data) != metadata["total_size"]:
            logger.error(f"Size mismatch for {base_key}: expected {metadata['total_size']}, got {len(combined_data)}")
            self.stats["errors"] += 1
            return None
            
        return combined_data
    
    async def store(self, tool_name: str, args: Dict[str, Any], result: str) -> bool:
        """Store a base64 encoded image in the cache.
        
        Args:
            tool_name: Name of the tool that produced the result
            args: Arguments passed to the tool
            result: Base64 encoded image data
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            key = self._generate_key(tool_name, args)
            await self._store_chunks(key, result)
            self.stats["stores"] += 1
            logger.info(f"Stored image in cache for tool {tool_name} with key {key}")
            return True
        except Exception as e:
            logger.exception(f"Error storing image in cache: {str(e)}")
            self.stats["errors"] += 1
            return False
    
    async def get(self, tool_name: str, args: Dict[str, Any]) -> Optional[str]:
        """Retrieve a base64 encoded image from the cache.
        
        Args:
            tool_name: Name of the tool
            args: Arguments passed to the tool
            
        Returns:
            Base64 encoded image data or None if not found
        """
        try:
            key = self._generate_key(tool_name, args)
            data = await self._retrieve_chunks(key)
            
            if data is not None:
                self.stats["hits"] += 1
                print(f"\033[92m[REDIS CACHE] 👍 CACHE HIT for tool {tool_name} - Using cached base64 image ({len(data) // 1024}KB)\033[0m")
                logger.info(f"Cache hit for tool {tool_name} with key {key}")
                # Convert bytes back to string if it was stored as bytes
                return data.decode('utf-8')
            else:
                self.stats["misses"] += 1
                print(f"\033[93m[REDIS CACHE] 👎 CACHE MISS for tool {tool_name} - Need to fetch base64 image\033[0m")
                logger.info(f"Cache miss for tool {tool_name} with key {key}")
                return None
        except Exception as e:
            logger.exception(f"Error retrieving image from cache: {str(e)}")
            self.stats["errors"] += 1
            return None
    
    async def store_in_background(self, tool_name: str, args: Dict[str, Any], result: str) -> None:
        """Store image in cache without blocking the main process.
        
        This method starts a background task to store the image data without
        waiting for it to complete, allowing the main process to continue.
        
        Args:
            tool_name: Name of the tool that produced the result
            args: Arguments passed to the tool
            result: Base64 encoded image data
        """
        # Create a task but don't wait for it
        asyncio.create_task(self.store(tool_name, args, result))
        logger.debug(f"Started background task to cache result for tool {tool_name}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        hit_rate = 0
        if (self.stats["hits"] + self.stats["misses"]) > 0:
            hit_rate = self.stats["hits"] / (self.stats["hits"] + self.stats["misses"])
            
        return {
            **self.stats,
            "hit_rate": hit_rate,
            "total_requests": self.stats["hits"] + self.stats["misses"]
        }

# Singleton instance
_image_cache_instance = None

def get_image_cache() -> ImageCache:
    """Get the singleton ImageCache instance."""
    global _image_cache_instance
    if _image_cache_instance is None:
        _image_cache_instance = ImageCache()
    return _image_cache_instance
