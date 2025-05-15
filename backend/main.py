from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
import os
import logging
import json
from fastapi.encoders import jsonable_encoder
from app.utils.json_encoder import MongoJSONEncoder, mongo_json_serializer

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Firebase first to avoid multiple initializations
from app.core.firebase_init import firebase_app

# Import API modules
from app.api import auth, items, brand_guidelines, compliance, video_upload, firebase_auth, user_profile

# Import Redis startup module
try:
    from app.core.openrouter_agent.redis.startup import (
        initialize_redis_cache,
        cleanup_redis_cache,
    )
    redis_available = True
except ImportError:
    logger.warning("Redis module not available. Continuing without Redis caching.")
    redis_available = False

# Initialize FastAPI app
app = FastAPI(
    title="Compliance API", description="API for compliance management", version="0.1.0"
)

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Compliance API...")

    # Initialize Redis cache if available
    if redis_available:
        try:
            logger.info("Initializing Redis cache...")
            success = await initialize_redis_cache()
            if success:
                logger.info("Redis cache initialized successfully")
            else:
                logger.warning("Failed to initialize Redis cache. Continuing without caching.")
        except Exception as e:
            logger.exception(f"Error initializing Redis cache: {str(e)}")

    logger.info("Compliance API startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Compliance API...")

    # Clean up Redis connections if available
    if redis_available:
        try:
            logger.info("Closing Redis connections...")
            success = await cleanup_redis_cache()
            if success:
                logger.info("Redis connections closed successfully")
            else:
                logger.warning("Failed to close Redis connections cleanly")
        except Exception as e:
            logger.exception(f"Error closing Redis connections: {str(e)}")

    logger.info("Compliance API shutdown complete")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Override default JSON encoder
fastapi_jsonable_encoder_original = jsonable_encoder

def custom_jsonable_encoder(*args, **kwargs):
    """Custom jsonable_encoder that handles MongoDB ObjectId"""
    try:
        return fastapi_jsonable_encoder_original(*args, **kwargs)
    except ValueError as e:
        # If standard encoder fails, try with our custom serializer
        if args and isinstance(args[0], (dict, list)):
            return json.loads(json.dumps(args[0], default=mongo_json_serializer))
        raise e

# Replace FastAPI's jsonable_encoder with our custom version
jsonable_encoder = custom_jsonable_encoder


# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to the Compliance API"}

@app.get("/healthz/")
async def health_check():
    return {"status": "ok"}


# Include routers
app.include_router(auth.router, tags=["authentication"])
app.include_router(firebase_auth.router, prefix="/api/firebase-auth", tags=["firebase-authentication"])
app.include_router(user_profile.router, prefix="/api/user", tags=["user-profile"])
app.include_router(items.router, prefix="/api", tags=["items"])
app.include_router(brand_guidelines.router, prefix="/api", tags=["brand-guidelines"])
app.include_router(compliance.router, prefix="/api", tags=["compliance"])
app.include_router(
    video_upload.router, prefix="/api", tags=["Video Upload"]
)  # Added video upload router

# Run the application
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
