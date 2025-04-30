import json
import hashlib
import time
from typing import Dict, Any, Optional

class ToolResultCache:
    """
    A cache for tool execution results to avoid redundant tool calls with the same inputs.
    
    This cache stores tool results based on the tool name and input parameters,
    with configurable expiration times for different tools.
    """
    
    def __init__(self, default_ttl: int = 3600):
        """
        Initialize the tool result cache.
        
        Args:
            default_ttl: Default time-to-live in seconds for cache entries (default: 1 hour)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        
        # Configure tool-specific TTLs (in seconds)
        self.tool_ttls = {
            # Tools with static results can have longer TTLs
            "get_brand_guidelines": 86400,  # 24 hours
            "get_brand_colors": 86400,     # 24 hours
            "get_brand_fonts": 86400,      # 24 hours
            
            # Analysis tools might need shorter TTLs
            "check_color_contrast": 3600,   # 1 hour
            "check_image_clarity": 3600,    # 1 hour
            "check_element_placement": 3600, # 1 hour
            
            # Dynamic tools should have very short TTLs or be excluded
            "attempt_completion": 300,      # 5 minutes
        }
        
        # Tools to exclude from caching (results always change or have side effects)
        self.exclude_from_cache = [
            # Add tools that should never be cached here
        ]
        
        # Stats for monitoring cache performance
        self.stats = {
            "hits": 0,
            "misses": 0,
            "expirations": 0
        }
    
    def _generate_cache_key(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """
        Generate a unique cache key for a tool call based on tool name and arguments.
        
        Args:
            tool_name: Name of the tool being called
            tool_args: Arguments passed to the tool
            
        Returns:
            A unique hash string to use as cache key
        """
        # Remove image_base64 and images_base64 from the args for the cache key
        # since these are large and might have minor variations that don't affect results
        filtered_args = {k: v for k, v in tool_args.items() 
                        if k not in ["image_base64", "images_base64"]}
        
        # Convert the filtered args to a stable string representation
        args_str = json.dumps(filtered_args, sort_keys=True)
        
        # Create a hash of the tool name and arguments
        key_string = f"{tool_name}:{args_str}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, tool_name: str, tool_args: Dict[str, Any]) -> Optional[Any]:
        """
        Retrieve a cached tool result if available and not expired.
        
        Args:
            tool_name: Name of the tool
            tool_args: Arguments passed to the tool
            
        Returns:
            The cached result or None if not found or expired
        """
        # Skip cache lookup for excluded tools
        if tool_name in self.exclude_from_cache:
            self.stats["misses"] += 1
            return None
        
        # Generate cache key
        cache_key = self._generate_cache_key(tool_name, tool_args)
        
        # Check if key exists in cache
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            current_time = time.time()
            
            # Check if entry has expired
            if current_time - entry["timestamp"] < entry["ttl"]:
                print(f"\033[92m[CACHE HIT] Using cached result for {tool_name}\033[0m")
                self.stats["hits"] += 1
                return entry["result"]
            else:
                # Entry has expired
                print(f"\033[93m[CACHE EXPIRED] Result for {tool_name} has expired\033[0m")
                self.stats["expirations"] += 1
                del self.cache[cache_key]
        
        # Cache miss
        self.stats["misses"] += 1
        return None
    
    def set(self, tool_name: str, tool_args: Dict[str, Any], result: Any) -> None:
        """
        Store a tool result in the cache.
        
        Args:
            tool_name: Name of the tool
            tool_args: Arguments passed to the tool
            result: Result returned by the tool
        """
        # Skip caching for excluded tools
        if tool_name in self.exclude_from_cache:
            return
        
        # Generate cache key
        cache_key = self._generate_cache_key(tool_name, tool_args)
        
        # Get TTL for this tool (or use default)
        ttl = self.tool_ttls.get(tool_name, self.default_ttl)
        
        # Store result with timestamp and TTL
        self.cache[cache_key] = {
            "result": result,
            "timestamp": time.time(),
            "ttl": ttl
        }
        
        print(f"\033[94m[CACHE SET] Cached result for {tool_name} (TTL: {ttl}s)\033[0m")
    
    def clear(self, tool_name: Optional[str] = None) -> None:
        """
        Clear cache entries, either for a specific tool or all entries.
        
        Args:
            tool_name: Optional tool name to clear cache for specific tool only
        """
        if tool_name:
            # Clear entries for specific tool
            keys_to_remove = []
            for key, entry in self.cache.items():
                if entry.get("tool_name") == tool_name:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.cache[key]
                
            print(f"\033[93m[CACHE CLEAR] Cleared cache for {tool_name}\033[0m")
        else:
            # Clear all entries
            self.cache.clear()
            print(f"\033[93m[CACHE CLEAR] Cleared entire cache\033[0m")
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get cache performance statistics.
        
        Returns:
            Dictionary with hit/miss/expiration counts
        """
        return self.stats

# Create a global instance of the cache
tool_cache = ToolResultCache()

async def cached_execute_tool(tool_name: str, tool_args: Dict[str, Any], execute_func):
    """
    Execute a tool with caching support.
    
    Args:
        tool_name: Name of the tool to execute
        tool_args: Arguments for the tool
        execute_func: Async function that executes the actual tool
        
    Returns:
        Tool execution result (either from cache or from actual execution)
    """
    # Try to get result from cache
    cached_result = tool_cache.get(tool_name, tool_args)
    
    if cached_result is not None:
        # Return cached result
        return cached_result
    
    # Execute the tool
    result = await execute_func(tool_name, tool_args)
    
    # Cache the result
    tool_cache.set(tool_name, tool_args, result)
    
    return result
