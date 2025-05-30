# app/core/video_agent/twelve_labs_processor.py

import asyncio
import logging
import os
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from app.core.twelve_labs.client import TwelveLabsClient
from app.db.firestore_twelve_labs import (
    store_twelve_labs_mapping,
    update_twelve_labs_status
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# The default index name for brand compliance videos
DEFAULT_INDEX_NAME = "brand_compliance_videos"

async def process_video_for_twelve_labs(
    video_path: str,
    user_id: str,
    video_url: str,
    max_wait_time: int = 300,  # Maximum time to wait for initial indexing (seconds)
    check_interval: int = 15,  # Time between status checks (seconds)
) -> Tuple[bool, Optional[str]]:
    """
    Process a video for Twelve Labs indexing and searching.
    This function now runs synchronously in the main flow and sends status updates.
    
    Args:
        video_path: Local path to the downloaded video
        user_id: ID of the user who uploaded the video
        video_url: Original URL of the video
        max_wait_time: Maximum time to wait for initial indexing (seconds)
        check_interval: Time between status checks (seconds)
        
    Returns:
        Tuple of (success, error_message)
    """
    logger.info(f"🔄 TWELVE LABS PROCESSOR: Starting processing for video {video_url}")
    logger.info(f"🔄 TWELVE LABS PROCESSOR: Video path: {video_path}")
    logger.info(f"🔄 TWELVE LABS PROCESSOR: User ID: {user_id}")
    
    start_time = time.time()
    
    try:
        # Initialize client
        logger.info(f"🔄 TWELVE LABS PROCESSOR: Initializing Twelve Labs client")
        client = TwelveLabsClient()
        
        # Check if index exists, create if it doesn't
        logger.info(f"🔄 TWELVE LABS PROCESSOR: Getting or creating index '{DEFAULT_INDEX_NAME}'")
        
        # Get a list of existing indexes and check if ours exists
        try:
            # Use methods from our TwelveLabsClient implementation
            try:
                indexes = client.list_indexes()
                logger.info(f"🔄 TWELVE LABS PROCESSOR: Found {len(indexes)} existing indexes")
            except Exception as e:
                logger.error(f"🔄 TWELVE LABS PROCESSOR: Failed to list indexes: {str(e)}")
                indexes = []
            
            # Try to find our index by name
            index_id = None
            for index in indexes:
                # Check various ways the name might be stored based on SDK version
                index_name = None
                if isinstance(index, dict):
                    index_name = index.get('name', index.get('display_name', None))
                    if index_name and DEFAULT_INDEX_NAME in index_name:
                        index_id = index.get('id', index.get('_id', None))
                        break
                else:
                    # Try attribute access
                    if hasattr(index, 'name') and getattr(index, 'name') and DEFAULT_INDEX_NAME in getattr(index, 'name'):
                        index_id = getattr(index, 'id', getattr(index, '_id', None))
                        break
                    elif hasattr(index, 'display_name') and getattr(index, 'display_name') and DEFAULT_INDEX_NAME in getattr(index, 'display_name'):
                        index_id = getattr(index, 'id', getattr(index, '_id', None))
                        break
            
            # If index doesn't exist, create it
            if not index_id:
                logger.info(f"🔄 TWELVE LABS PROCESSOR: Index '{DEFAULT_INDEX_NAME}' not found, creating it")
                try:
                    # Use our TwelveLabsClient implementation
                    new_index = client.create_index(
                        index_name=DEFAULT_INDEX_NAME,
                        models=[{
                            "model_name": "marengo2.7",
                            "model_options": ["visual", "audio"]
                        }],
                        addons=["thumbnail"]
                    )
                    
                    # Extract index ID
                    if isinstance(new_index, dict):
                        index_id = new_index.get('id', new_index.get('_id'))
                    elif hasattr(new_index, 'id'):
                        index_id = new_index.id
                        
                    logger.info(f"🔄 TWELVE LABS PROCESSOR: Created new index with ID: {index_id}")
                except Exception as e:
                    logger.error(f"🔄 TWELVE LABS PROCESSOR: Error creating index: {str(e)}")
                    # We won't attempt a fallback since we're using our implementation

                # Index ID is already extracted in the try/except blocks above
        except Exception as e:
            logger.error(f"🔄 TWELVE LABS PROCESSOR: Error listing/creating indexes: {str(e)}")
        
        if not index_id:
            logger.error("🔄 TWELVE LABS PROCESSOR: Failed to get or create Twelve Labs index")
            return False, "Failed to initialize search index"
        
        logger.info(f"🔄 TWELVE LABS PROCESSOR: Using index with ID: {index_id}")
        
        # Upload video to Twelve Labs
        logger.info(f"🔄 TWELVE LABS PROCESSOR: Uploading video to Twelve Labs")
        upload_start = time.time()
        video_id = client.upload_video(
            video_path=video_path,
            index_id=index_id,
        )
        upload_duration = time.time() - upload_start
        logger.info(f"🔄 TWELVE LABS PROCESSOR: Video upload completed in {upload_duration:.2f}s")
        
        if not video_id:
            logger.error("🔄 TWELVE LABS PROCESSOR: Failed to upload video to Twelve Labs")
            return False, "Failed to upload video for search indexing"
        
        logger.info(f"🔄 TWELVE LABS PROCESSOR: Video uploaded with ID: {video_id}")
            
        # Store mapping in database
        logger.info(f"🔄 TWELVE LABS PROCESSOR: Storing mapping in database")
        store_start = time.time()
        success = await store_twelve_labs_mapping(
            video_url=video_url,
            user_id=user_id,
            twelve_labs_index_id=index_id,
            twelve_labs_video_id=video_id,
            status="processing"
        )
        store_duration = time.time() - store_start
        logger.info(f"🔄 TWELVE LABS PROCESSOR: Mapping storage completed in {store_duration:.2f}s (success: {success})")
        
        if not success:
            logger.error("🔄 TWELVE LABS PROCESSOR: Failed to store Twelve Labs mapping")
            return False, "Failed to store search mapping data"
            
        # Wait for processing to start
        logger.info(f"🔄 TWELVE LABS PROCESSOR: Checking if processing has started")
        processing_start = time.time()
        processing_started = client.check_processing_started(video_id, index_id)
        processing_check_duration = time.time() - processing_start
        logger.info(f"🔄 TWELVE LABS PROCESSOR: Processing check completed in {processing_check_duration:.2f}s (started: {processing_started})")
        
        if not processing_started:
            logger.error("🔄 TWELVE LABS PROCESSOR: Video processing failed to start")
            await update_twelve_labs_status(
                video_url=video_url,
                user_id=user_id,
                status="failed",
                error_message="Video processing failed to start"
            )
            return False, "Video processing failed to start"
        
        # Now we'll wait for processing to complete (up to max_wait_time)
        logger.info(f"🔄 TWELVE LABS PROCESSOR: Waiting for video processing to complete (max {max_wait_time} seconds)")
        
        # Start the wait loop
        wait_start_time = time.time()
        max_checks = max_wait_time // check_interval
        is_complete = False
        
        for i in range(max_checks):
            # Check if we've exceeded the max wait time
            elapsed_time = time.time() - wait_start_time
            if elapsed_time >= max_wait_time:
                logger.warning(f"🔄 TWELVE LABS PROCESSOR: Reached maximum wait time of {max_wait_time}s")
                break
            
            # Wait before checking status
            logger.info(f"🔄 TWELVE LABS PROCESSOR: Waiting {check_interval}s before check {i+1}/{max_checks}")
            await asyncio.sleep(check_interval)
            
            # Check processing status
            logger.info(f"🔄 TWELVE LABS PROCESSOR: Checking processing status (check {i+1}/{max_checks})")
            try:
                is_complete = client.check_processing_complete(
                    video_id=video_id,
                    index_id=index_id
                )
                
                if is_complete:
                    logger.info(f"🔄 TWELVE LABS PROCESSOR: Processing completed after {i+1} checks ({elapsed_time:.2f}s)")
                    # Update status in database
                    await update_twelve_labs_status(
                        video_url=video_url,
                        user_id=user_id,
                        status="completed"
                    )
                    break
                else:
                    logger.info(f"🔄 TWELVE LABS PROCESSOR: Processing still in progress (check {i+1}/{max_checks})")
                    # Update status with progress
                    await update_twelve_labs_status(
                        video_url=video_url,
                        user_id=user_id,
                        status="processing",
                        metadata={"progress": (i+1)/max_checks}
                    )
            except Exception as e:
                logger.warning(f"🔄 TWELVE LABS PROCESSOR: Error checking status: {str(e)}")
                # Continue checking despite error
                continue
        
        total_duration = time.time() - start_time
        
        if is_complete:
            logger.info(f"🔄 TWELVE LABS PROCESSOR: Video {video_url} successfully processed in {total_duration:.2f}s")
            return True, None
        else:
            # Processing started but didn't complete within our wait time
            # This is still a success as it will complete in the background
            logger.info(f"🔄 TWELVE LABS PROCESSOR: Video {video_url} processing started but not yet complete after {total_duration:.2f}s")
            return True, "Processing started but not yet complete - it will continue in the background"
        
    except Exception as e:
        logger.error(f"🔄 TWELVE LABS PROCESSOR: Error in process_video_for_twelve_labs: {str(e)}", exc_info=True)
        try:
            await update_twelve_labs_status(
                video_url=video_url,
                user_id=user_id,
                status="failed",
                error_message=str(e)
            )
        except Exception as update_err:
            logger.error(f"🔄 TWELVE LABS PROCESSOR: Error updating status: {str(update_err)}")
            
        return False, str(e)

async def check_processing_status(
    video_url: str,
    user_id: str,
) -> bool:
    """
    Check the processing status of a video and update the database.
    
    Args:
        video_url: Original URL of the video
        user_id: ID of the user who uploaded the video
        
    Returns:
        True if processing is complete, False otherwise
    """
    from app.db.firestore_twelve_labs import get_twelve_labs_mapping
    
    logger.info(f"🔄 TWELVE LABS PROCESSOR: Checking processing status for video {video_url}")
    start_time = time.time()
    
    try:
        # Get mapping
        logger.info(f"🔄 TWELVE LABS PROCESSOR: Getting mapping for video {video_url}")
        mapping = await get_twelve_labs_mapping(video_url, user_id)
        
        if not mapping:
            logger.warning(f"🔄 TWELVE LABS PROCESSOR: No mapping found for video {video_url}")
            return False
        
        logger.info(f"🔄 TWELVE LABS PROCESSOR: Found mapping with video ID {mapping['twelve_labs_video_id']}")
            
        # Initialize client
        client = TwelveLabsClient()
        
        # Check status
        logger.info(f"🔄 TWELVE LABS PROCESSOR: Checking processing status with Twelve Labs API")
        status_check_start = time.time()
        status_complete = client.check_processing_complete(
            video_id=mapping["twelve_labs_video_id"],
            index_id=mapping["twelve_labs_index_id"]
        )
        status_check_duration = time.time() - status_check_start
        logger.info(f"🔄 TWELVE LABS PROCESSOR: Status check completed in {status_check_duration:.2f}s (complete: {status_complete})")
        
        if status_complete:
            # Update status in database
            logger.info(f"🔄 TWELVE LABS PROCESSOR: Processing is complete, updating status in database")
            update_start = time.time()
            await update_twelve_labs_status(
                video_url=video_url,
                user_id=user_id,
                status="completed"
            )
            update_duration = time.time() - update_start
            logger.info(f"🔄 TWELVE LABS PROCESSOR: Status update completed in {update_duration:.2f}s")
            logger.info(f"🔄 TWELVE LABS PROCESSOR: Video {video_url} processing completed")
            return True
        
        total_duration = time.time() - start_time
        logger.info(f"🔄 TWELVE LABS PROCESSOR: Processing not complete yet for video {video_url} (check took {total_duration:.2f}s)")
        return False
        
    except Exception as e:
        logger.error(f"🔄 TWELVE LABS PROCESSOR: Error checking processing status: {str(e)}", exc_info=True)
        return False

def trigger_background_processing(
    video_path: str,
    user_id: str,
    video_url: str,
) -> None:
    """
    Trigger the background processing of a video for Twelve Labs.
    This function is called during the compliance check workflow.
    
    Args:
        video_path: Local path to the downloaded video
        user_id: ID of the user who uploaded the video
        video_url: Original URL of the video
    """
    logger.info(f"🚀 TWELVE LABS PROCESSOR: Triggering background processing for video {video_url}")
    logger.info(f"🚀 TWELVE LABS PROCESSOR: User ID: {user_id}")
    logger.info(f"🚀 TWELVE LABS PROCESSOR: Video path: {video_path}")
    
    # Create a background task for processing
    async def background_task():
        try:
            logger.info(f"🚀 TWELVE LABS PROCESSOR: Starting background task for video {video_url}")
            # Process the video
            start_time = time.time()
            success, error = await process_video_for_twelve_labs(
                video_path=video_path,
                user_id=user_id,
                video_url=video_url
            )
            
            initial_processing_time = time.time() - start_time
            logger.info(f"🚀 TWELVE LABS PROCESSOR: Initial processing completed in {initial_processing_time:.2f}s (success: {success})")
            
            if not success:
                logger.error(f"🚀 TWELVE LABS PROCESSOR: Background processing failed: {error}")
                return
                
            # Start a periodic check for processing status
            MAX_CHECKS = 30  # Maximum number of checks to perform
            CHECK_INTERVAL = 30  # Seconds between checks
            
            logger.info(f"🚀 TWELVE LABS PROCESSOR: Starting periodic status checks (max {MAX_CHECKS} checks, every {CHECK_INTERVAL}s)")
            
            for i in range(MAX_CHECKS):
                # Wait before checking
                logger.info(f"🚀 TWELVE LABS PROCESSOR: Waiting {CHECK_INTERVAL}s before check {i+1}/{MAX_CHECKS}")
                await asyncio.sleep(CHECK_INTERVAL)
                
                # Check status
                logger.info(f"🚀 TWELVE LABS PROCESSOR: Performing check {i+1}/{MAX_CHECKS}")
                check_start = time.time()
                complete = await check_processing_status(
                    video_url=video_url,
                    user_id=user_id
                )
                check_duration = time.time() - check_start
                logger.info(f"🚀 TWELVE LABS PROCESSOR: Check {i+1} completed in {check_duration:.2f}s (complete: {complete})")
                
                if complete:
                    logger.info(f"🚀 TWELVE LABS PROCESSOR: Video {video_url} processing completed after {i+1} checks")
                    break
            
            total_duration = time.time() - start_time
            logger.info(f"🚀 TWELVE LABS PROCESSOR: Completed background processing monitoring for {video_url} in {total_duration:.2f}s")
            
        except Exception as e:
            logger.error(f"🚀 TWELVE LABS PROCESSOR: Error in background processing task: {str(e)}", exc_info=True)
    
    # Start the background task without awaiting it
    asyncio.create_task(background_task())
    logger.info(f"🚀 TWELVE LABS PROCESSOR: Background task created for video {video_url}")
