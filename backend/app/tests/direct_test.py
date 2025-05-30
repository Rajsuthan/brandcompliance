#!/usr/bin/env python3
"""
Direct Test for Twelve Labs Video Search Implementation

This script directly tests the search_video function and database functionality
without relying on the full application infrastructure.
"""

import os
import sys
import asyncio
import json
from pathlib import Path

# Set up logging to see what's happening
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
backend_dir = Path(__file__).parent.parent.parent
logger.info(f"Adding {backend_dir} to sys.path")
sys.path.insert(0, str(backend_dir))

async def test_search():
    """Test the search_video function directly"""
    try:
        # First, check if the video exists
        video_path = backend_dir / "app" / "assets" / "BurgerKing_NonCompliant_LogoInversion (1).mp4"
        logger.info(f"Checking if test video exists at: {video_path}")
        if not os.path.exists(video_path):
            logger.error(f"Test video not found at: {video_path}")
            return
        
        logger.info(f"Test video found: {video_path}")
        
        # Create a test video URL (this would normally come from the uploaded video)
        test_url = f"file://{video_path.absolute()}"
        test_user_id = "direct-test-user"
        
        # 1. Import the necessary modules
        logger.info("Importing required modules...")
        try:
            from app.db.firestore_twelve_labs import store_twelve_labs_mapping, get_twelve_labs_mapping
            from app.core.video_agent.twelve_labs_processor import process_video_for_twelve_labs
            from app.core.openrouter_agent.tools.search_video import search_video
            logger.info("Successfully imported all modules")
        except ImportError as e:
            logger.error(f"Import error: {e}")
            return
        
        # 2. Process the video
        logger.info(f"Processing video: {test_url}")
        try:
            success, error = await process_video_for_twelve_labs(
                video_path=str(video_path),
                user_id=test_user_id,
                video_url=test_url
            )
            
            if not success:
                logger.error(f"Video processing failed: {error}")
                return
                
            logger.info(f"Video processed successfully: {success}")
        except Exception as e:
            logger.error(f"Error during video processing: {e}", exc_info=True)
            return
        
        # 3. Test search query
        logger.info("Testing search functionality...")
        try:
            search_args = {
                "query": "burger king logo",
                "threshold": "low",
                "task_detail": "Direct test of video search",
                "video_url": test_url,
                "user_id": test_user_id
            }
            
            result = await search_video(search_args)
            logger.info(f"Search result: {json.dumps(result, indent=2)}")
        except Exception as e:
            logger.error(f"Error during search: {e}", exc_info=True)
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

if __name__ == "__main__":
    logger.info("Starting direct test...")
    asyncio.run(test_search())
    logger.info("Test completed")
