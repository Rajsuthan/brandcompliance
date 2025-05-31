# app/core/video_agent/twelve_labs_processor.py

import asyncio
import logging
import os
import time
from typing import Dict, Any, Optional, Tuple, List, Union, BinaryIO, Callable, Literal
from datetime import datetime

from twelvelabs import types, models

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
        
        index_id: Optional[str] = None
        try:
            logger.info(f"🔄 TWELVE LABS PROCESSOR: Attempting to retrieve index directly by name: '{DEFAULT_INDEX_NAME}'")
            # Use the 'name' parameter for a direct lookup
            # client.indexes.list() returns a RootModelList[models.Index]
            matching_indexes_list = client.indexes.list(name=DEFAULT_INDEX_NAME)
            
            found_index_model: Optional[models.Index] = None
            if matching_indexes_list and len(matching_indexes_list.data) > 0:
                # If the list is not empty, the first item should be our index
                found_index_model = matching_indexes_list.data[0]
                if found_index_model.name == DEFAULT_INDEX_NAME:
                    index_id = found_index_model.id
                    logger.info(f"🔄 TWELVE LABS PROCESSOR: Found existing index '{DEFAULT_INDEX_NAME}' with ID: {index_id} via direct name lookup.")
                else:
                    # This case should ideally not happen if the name filter works as expected
                    logger.warning(f"🔄 TWELVE LABS PROCESSOR: Index found by name filter does not match '{DEFAULT_INDEX_NAME}'. Name found: {found_index_model.name}. Proceeding to create.")
                    found_index_model = None # Reset to ensure creation
            else:
                logger.info(f"🔄 TWELVE LABS PROCESSOR: No index found with name '{DEFAULT_INDEX_NAME}' via direct lookup.")
            
            if not found_index_model:
                logger.info(f"🔄 TWELVE LABS PROCESSOR: Index '{DEFAULT_INDEX_NAME}' not found, creating it.")
                # Define engine configurations using types.IndexModel
                index_models_config = [
                    types.IndexModel(
                        name="marengo2.6",  # Confirm this is the desired engine, or use a newer one if available
                        options=[
                            types.VIDEO_INDEXING_OPTIONS_VISUAL,
                            types.VIDEO_INDEXING_OPTIONS_CONVERSATION,
                            types.VIDEO_INDEXING_OPTIONS_TEXT_IN_VIDEO,
                            types.VIDEO_INDEXING_OPTIONS_LOGO
                        ]
                    )
                ]
                # Optional: specify addons
                addons_config = ["thumbnail"]

                created_index_model = client.indexes.create(
                    name=DEFAULT_INDEX_NAME,
                    models=index_models_config,
                    addons=addons_config
                )
                index_id = created_index_model.id
                logger.info(f"🔄 TWELVE LABS PROCESSOR: Created new index '{DEFAULT_INDEX_NAME}' with ID: {index_id}")

        except Exception as e:
            logger.error(f"🔄 TWELVE LABS PROCESSOR: Error listing or creating indexes: {e}", exc_info=True)
        
        if not index_id:
            logger.error("🔄 TWELVE LABS PROCESSOR: Failed to get or create Twelve Labs index")
            return False, "Failed to initialize search index"
        
        logger.info(f"🔄 TWELVE LABS PROCESSOR: Using index with ID: {index_id}")
        
        # Create a video indexing task
        logger.info(f"🔄 TWELVE LABS PROCESSOR: Creating video indexing task for video '{video_path}' in index '{index_id}'.")
        task: Optional[models.Task] = None
        try:
            task = client.tasks.create(index_id=index_id, file=video_path)
            logger.info(f"🔄 TWELVE LABS PROCESSOR: Task created with ID: {task.id}, current status: {task.status}")

            # Store initial mapping with task ID and processing status
            # Assuming store_twelve_labs_mapping can handle twelve_labs_video_id=None initially
            # and that we might add twelve_labs_task_id to our DB model/function.
            # For now, we'll pass video_id as None.
            await store_twelve_labs_mapping(
                video_url=video_url,
                user_id=user_id,
                twelve_labs_index_id=index_id,
                twelve_labs_video_id=None, # Video ID is not known until task is 'ready'
                status="processing", # Initial status
                # twelve_labs_task_id=task.id # Ideal: store task.id for out-of-band checks
            )
            logger.info(f"🔄 TWELVE LABS PROCESSOR: Initial mapping stored for task {task.id}.")

        except Exception as e:
            logger.error(f"🔄 TWELVE LABS PROCESSOR: Failed to create video indexing task: {e}", exc_info=True)
            await update_twelve_labs_status(
                video_url=video_url, user_id=user_id, status="failed", error_message=f"Failed to create indexing task: {e}"
            )
            return False, f"Failed to create indexing task: {e}"

        # Define callback for wait_for_done
        def log_task_progress(updated_task: models.Task):
            progress = updated_task.process.get('percentage', 0) if updated_task.process else 'N/A'
            logger.info(f"🔄 TWELVE LABS PROCESSOR: Task {updated_task.id} status: {updated_task.status}, progress: {progress}%")

        # Wait for the task to complete
        logger.info(f"🔄 TWELVE LABS PROCESSOR: Waiting for task {task.id} to complete (max_wait_time: {max_wait_time}s, check_interval: {check_interval}s)...")
        completed_task: Optional[models.Task] = None
        try:
            # Wrap wait_for_done with asyncio.wait_for to enforce our max_wait_time
            # task.wait_for_done is blocking, so it needs to be run in an executor for asyncio.wait_for
            # However, the SDK might handle async operations internally if used in an async context.
            # For simplicity here, assuming direct call and relying on SDK's potential internal timeout
            # or handling exceptions if it blocks too long without its own timeout matching max_wait_time.
            # A more robust solution for strict timeout with blocking calls in asyncio is run_in_executor.
            # The guide mentions this complexity. For now, direct call:
            completed_task = await asyncio.wait_for(
                asyncio.to_thread(
                    task.wait_for_done,
                    sleep_interval=float(check_interval),
                    callback=log_task_progress
                ),
                timeout=float(max_wait_time)
            )
            # The asyncio.wait_for wrapper will raise asyncio.TimeoutError if max_wait_time is exceeded.

            if completed_task.status == "ready":
                final_video_id = completed_task.video_id
                logger.info(f"✅ TWELVE LABS PROCESSOR: Task {completed_task.id} completed. Video ID: {final_video_id}")
                await update_twelve_labs_status(
                    video_url=video_url,
                    user_id=user_id,
                    status="ready",
                    twelve_labs_video_id=final_video_id # Update with the actual video_id
                )
                total_duration = time.time() - start_time
                logger.info(f"✅ TWELVE LABS PROCESSOR: Successfully processed video {video_url} in {total_duration:.2f}s")
                return True, None
            else:
                error_msg = f"Video processing task {completed_task.id} failed. Status: {completed_task.status} Medata: {completed_task.metadata}."
                if completed_task.error_message:
                    error_msg += f" Details: {completed_task.error_message}"
                logger.error(f"❌ TWELVE LABS PROCESSOR: {error_msg}")
                await update_twelve_labs_status(
                    video_url=video_url, user_id=user_id, status="failed", error_message=error_msg
                )
                return False, error_msg
        
        except asyncio.TimeoutError:
            logger.warning(f"⌛ TWELVE LABS PROCESSOR: Video processing task {task.id} timed out after {max_wait_time}s (our configured timeout). Attempting to retrieve final status.")
            # If our own timeout wrapper (not implemented here fully for blocking call) triggers, or if we want to handle it:
            try:
                current_task_status = client.tasks.retrieve(id=task.id)
                error_msg = f"Processing timed out. Last known status for task {task.id}: {current_task_status.status}"
                await update_twelve_labs_status(video_url=video_url, user_id=user_id, status="failed", error_message=error_msg)
                return False, error_msg
            except Exception as retrieve_e:
                logger.error(f"❌ TWELVE LABS PROCESSOR: Failed to retrieve status for timed-out task {task.id}: {retrieve_e}", exc_info=True)
                await update_twelve_labs_status(video_url=video_url, user_id=user_id, status="failed", error_message="Processing timed out, final status unknown.")
                return False, "Processing timed out, final status unknown."

        except Exception as e:
            logger.error(f"❌ TWELVE LABS PROCESSOR: Error waiting for task {task.id} to complete: {e}", exc_info=True)
            # Attempt to get last known status
            last_status = "unknown"
            if task:
                try:
                    current_task_state = client.tasks.retrieve(id=task.id)
                    last_status = current_task_state.status
                except Exception as retrieve_e:
                    logger.error(f"Failed to retrieve status for task {task.id} after error: {retrieve_e}")
            error_message_for_db = f"Error during video processing: {e}. Last known status: {last_status}"
            await update_twelve_labs_status(
                video_url=video_url, user_id=user_id, status="failed", error_message=error_message_for_db
            )
            return False, error_message_for_db
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
