# app/db/firestore_twelve_labs.py

import asyncio
import firebase_admin
import logging
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
from google.cloud.firestore_v1 import DocumentSnapshot

# Import Firebase utilities (assuming these exist in the project)
from app.db.firebase_utils import get_firestore_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Collection name for Twelve Labs video mappings
TWELVE_LABS_COLLECTION = "twelve_labs_videos"

def generate_document_id(user_id: str, video_url: str) -> str:
    """
    Generate a consistent document ID from user_id and video_url.
    Uses MD5 hash to avoid issues with URL length and special characters.
    
    Args:
        user_id: ID of the user
        video_url: URL of the video
        
    Returns:
        Document ID string
    """
    # Hash the URL to avoid issues with length and special characters
    url_hash = hashlib.md5(video_url.encode()).hexdigest()
    return f"{user_id}_{url_hash}"

async def store_twelve_labs_mapping(
    video_url: str,
    user_id: str,
    twelve_labs_index_id: str,
    twelve_labs_video_id: str,
    status: str = "processing"
) -> bool:
    """
    Store mapping between original video URL and Twelve Labs IDs.
    
    Args:
        video_url: Original URL of the video
        user_id: ID of the user who uploaded the video
        twelve_labs_index_id: Twelve Labs index ID
        twelve_labs_video_id: Twelve Labs video ID
        status: Processing status (processing, completed, failed)
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"📝 TWELVE LABS DB: Storing mapping for video {video_url}")
    logger.info(f"📝 TWELVE LABS DB: User ID: {user_id}")
    logger.info(f"📝 TWELVE LABS DB: Index ID: {twelve_labs_index_id}")
    logger.info(f"📝 TWELVE LABS DB: Video ID: {twelve_labs_video_id}")
    logger.info(f"📝 TWELVE LABS DB: Status: {status}")
    
    try:
        # Get Firestore client
        db = get_firestore_client()
        logger.info(f"📝 TWELVE LABS DB: Got Firestore client")
        
        # Create document ID from user_id and video_url
        doc_id = f"{user_id}_{video_url}"
        logger.info(f"📝 TWELVE LABS DB: Document ID: {doc_id}")
        
        # Create mapping document
        doc_ref = db.collection(TWELVE_LABS_COLLECTION).document(doc_id)
        
        # Set mapping data
        mapping_data = {
            "video_url": video_url,
            "user_id": user_id,
            "twelve_labs_index_id": twelve_labs_index_id,
            "twelve_labs_video_id": twelve_labs_video_id,
            "status": status,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Store in Firestore
        doc_ref.set(mapping_data)
        logger.info(f"📝 TWELVE LABS DB: Successfully stored mapping in Firestore")
        
        return True
        
    except Exception as e:
        logger.error(f"📝 TWELVE LABS DB: Failed to store Twelve Labs mapping: {str(e)}", exc_info=True)
        return False

async def update_twelve_labs_status(
    video_url: str,
    user_id: str,
    status: str,
    error_message: str = None
) -> bool:
    """
    Update the status of a Twelve Labs video processing task.
    
    Args:
        video_url: Original URL of the video
        user_id: ID of the user who uploaded the video
        status: New status (processing, completed, failed)
        error_message: Optional error message if status is failed
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"📝 TWELVE LABS DB: Updating status for video {video_url}")
    logger.info(f"📝 TWELVE LABS DB: User ID: {user_id}")
    logger.info(f"📝 TWELVE LABS DB: New status: {status}")
    if error_message:
        logger.info(f"📝 TWELVE LABS DB: Error message: {error_message}")
    
    try:
        # Get Firestore client
        db = get_firestore_client()
        
        # Create document ID from user_id and video_url
        doc_id = f"{user_id}_{video_url}"
        logger.info(f"📝 TWELVE LABS DB: Document ID: {doc_id}")
        
        # Reference to the mapping document
        doc_ref = db.collection(TWELVE_LABS_COLLECTION).document(doc_id)
        
        # Update data
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Add error message if provided
        if error_message and status == "failed":
            update_data["error_message"] = error_message
            
        # Update in Firestore
        doc_ref.update(update_data)
        logger.info(f"📝 TWELVE LABS DB: Successfully updated status to {status}")
        
        return True
        
    except Exception as e:
        logger.error(f"📝 TWELVE LABS DB: Failed to update Twelve Labs status: {str(e)}", exc_info=True)
        return False

async def get_twelve_labs_mapping(
    video_url: str,
    user_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get the Twelve Labs mapping for a video.
    
    Args:
        video_url: Original URL of the video
        user_id: ID of the user who uploaded the video
        
    Returns:
        Mapping dictionary or None if not found
    """
    logger.info(f"📝 TWELVE LABS DB: Getting mapping for video {video_url}")
    logger.info(f"📝 TWELVE LABS DB: User ID: {user_id}")
    
    try:
        # Get Firestore client
        db = get_firestore_client()
        
        # Create document ID from user_id and video_url
        doc_id = f"{user_id}_{video_url}"
        logger.info(f"📝 TWELVE LABS DB: Document ID: {doc_id}")
        
        # Reference to the mapping document
        doc_ref = db.collection(TWELVE_LABS_COLLECTION).document(doc_id)
        
        # Get document
        doc = doc_ref.get()
        
        # Check if document exists
        if not doc.exists:
            logger.warning(f"📝 TWELVE LABS DB: No mapping found for document ID {doc_id}")
            return None
            
        # Get data
        mapping_data = doc.to_dict()
        logger.info(f"📝 TWELVE LABS DB: Found mapping with status: {mapping_data.get('status')}")
        
        # Check if processing is complete
        if mapping_data.get("status") != "completed":
            logger.info(f"📝 TWELVE LABS DB: Processing not completed for video {video_url}")
            return None
            
        return mapping_data
        
    except Exception as e:
        logger.error(f"📝 TWELVE LABS DB: Failed to get Twelve Labs mapping: {str(e)}", exc_info=True)
        return None

async def get_twelve_labs_mapping_with_status(
    video_url: str,
    user_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get the Twelve Labs mapping for a video, including processing status.
    Unlike get_twelve_labs_mapping, this returns the mapping regardless of status.
    
    Args:
        video_url: Original URL of the video
        user_id: ID of the user who uploaded the video
        
    Returns:
        Mapping dictionary or None if not found
    """
    logger.info(f"📝 TWELVE LABS DB: Getting mapping with status for video {video_url}")
    logger.info(f"📝 TWELVE LABS DB: User ID: {user_id}")
    
    try:
        # Get Firestore client
        db = get_firestore_client()
        
        # Create document ID from user_id and video_url
        doc_id = f"{user_id}_{video_url}"
        logger.info(f"📝 TWELVE LABS DB: Document ID: {doc_id}")
        
        # Reference to the mapping document
        doc_ref = db.collection(TWELVE_LABS_COLLECTION).document(doc_id)
        
        # Get document
        doc = doc_ref.get()
        
        # Check if document exists
        if not doc.exists:
            logger.warning(f"📝 TWELVE LABS DB: No mapping found for document ID {doc_id}")
            return None
            
        # Get data
        mapping_data = doc.to_dict()
        logger.info(f"📝 TWELVE LABS DB: Found mapping with status: {mapping_data.get('status')}")
        
        return mapping_data
        
    except Exception as e:
        logger.error(f"📝 TWELVE LABS DB: Failed to get Twelve Labs mapping: {str(e)}", exc_info=True)
        return None

async def list_twelve_labs_videos(user_id: str) -> List[Dict[str, Any]]:
    """
    List all Twelve Labs videos for a user.
    
    Args:
        user_id: ID of the user
        
    Returns:
        List of video mappings
    """
    logger.info(f"📝 TWELVE LABS DB: Listing videos for user {user_id}")
    
    try:
        # Get Firestore client
        db = get_firestore_client()
        
        # Query videos for the user
        query = db.collection(TWELVE_LABS_COLLECTION).where("user_id", "==", user_id)
        
        # Execute query
        results = query.stream()
        
        # Process results
        videos = []
        for doc in results:
            video_data = doc.to_dict()
            videos.append(video_data)
            
        logger.info(f"📝 TWELVE LABS DB: Found {len(videos)} videos for user {user_id}")
        return videos
        
    except Exception as e:
        logger.error(f"📝 TWELVE LABS DB: Failed to list Twelve Labs videos: {str(e)}", exc_info=True)
        return []
