import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_redis_connection():
    try:
        # Import Redis modules
        from app.core.openrouter_agent.redis import get_redis_client, initialize_redis
        from app.core.openrouter_agent.redis.config import get_redis_config
        
        # Get Redis configuration
        config = get_redis_config()
        logger.info(f"Testing Redis connection with config: {config}")
        
        # Initialize Redis
        success, error = await initialize_redis()
        
        if success:
            logger.info("✅ Redis connection successful!")
            
            # Get Redis client
            redis = get_redis_client()
            
            # Test setting a value
            await redis.set("test_key", "test_value", ex=60)
            logger.info("✅ Successfully set test key")
            
            # Test getting a value
            value = await redis.get("test_key")
            logger.info(f"✅ Successfully retrieved test key: {value}")
            
            # Test chunked base64 storage (simulated)
            from app.core.openrouter_agent.redis import get_image_cache
            
            # Create a simulated base64 string (10KB of data)
            fake_base64 = "A" * 10240
            
            # Store it in the cache
            image_cache = get_image_cache()
            await image_cache.store("test_tool", {"test_arg": "value"}, fake_base64)
            logger.info("✅ Successfully stored simulated base64 data")
            
            # Retrieve it from the cache
            cached_base64 = await image_cache.get("test_tool", {"test_arg": "value"})
            
            if cached_base64 and len(cached_base64) == 10240:
                logger.info("✅ Successfully retrieved simulated base64 data")
            else:
                logger.error(f"❌ Retrieved base64 data has incorrect length: {len(cached_base64) if cached_base64 else 'None'}")
            
            # Get cache stats
            stats = await image_cache.get_stats()
            logger.info(f"Cache stats: {stats}")
            
            return True
        else:
            logger.error(f"❌ Redis connection failed: {error}")
            return False
            
    except Exception as e:
        logger.exception(f"❌ Error testing Redis connection: {str(e)}")
        return False

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_redis_connection())
