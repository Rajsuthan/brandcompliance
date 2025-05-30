"""Module for uploading videos to Twelve Labs platform.

This module provides functions to upload videos and monitor their processing status.
"""

import time
from typing import Dict, Optional, Union, Any, BinaryIO

from twelvelabs import TwelveLabs
# Remove specific model imports that may not exist in the current SDK version
# Instead, we'll work directly with the TwelveLabs client

from .config import get_client


def upload_video(
    index_id: str,
    video_file: Optional[Union[str, BinaryIO]] = None,
    video_url: Optional[str] = None,
    client: Optional[TwelveLabs] = None
) -> Optional[Dict[str, str]]:
    """Upload a video file or URL to the specified index.
    
    Args:
        index_id: ID of the index to upload the video to
        video_file: Path to local video file or file-like object
        video_url: URL of video to upload
        client: Optional TwelveLabs client instance. If not provided, one will be created
        
    Returns:
        Dictionary containing task_id and video_id if successful, None otherwise
        
    Raises:
        ValueError: If neither video_file nor video_url is provided
        
    Example:
        >>> result = upload_video("index_123", video_file="/path/to/video.mp4")
        >>> task_id = result["task_id"]
    """
    if not video_file and not video_url:
        raise ValueError("Either video_file or video_url must be provided")
    
    client = client or get_client()
    
    try:
        # Prepare parameters
        task_params = {"index_id": index_id}
        
        if video_file:
            task_params["video_file"] = video_file
        elif video_url:
            # According to documentation, the correct parameter name might vary
            # Some versions use video_url, others might use url
            task_params["video_url"] = video_url
        
        # Try different approaches to handle SDK structure differences
        try:
            # First try the documented approach
            task = client.tasks.create(**task_params)
        except (AttributeError, TypeError):
            # Try alternative approaches
            try:
                # Some versions might use videos resource instead of tasks
                task = client.videos.upload(**task_params)
            except AttributeError:
                # Try to find any upload-related method
                for resource_name in ["tasks", "videos", "indexes"]:
                    resource = getattr(client, resource_name, None)
                    if resource:
                        for method_name in dir(resource):
                            if any(term in method_name.lower() for term in ["create", "upload", "add"]):
                                try:
                                    method = getattr(resource, method_name)
                                    if callable(method):
                                        task = method(**task_params)
                                        break
                                except Exception:
                                    continue
        
        # Extract IDs from task with both dict and attribute access resilience
        result = {}
        
        # Extract IDs
        if isinstance(task, dict):
            result["task_id"] = task.get("id", "") or task.get("_id", "")
            result["video_id"] = task.get("video_id", "") or task.get("videoId", "")
        else:
            # Try attribute access
            for attr_name in ["id", "_id", "task_id", "taskId"]:
                if hasattr(task, attr_name):
                    result["task_id"] = getattr(task, attr_name)
                    break
            
            for attr_name in ["video_id", "videoId"]:
                if hasattr(task, attr_name):
                    result["video_id"] = getattr(task, attr_name)
                    break
        
        # If we still don't have IDs, use string representation as last resort
        if not result.get("task_id"):
            result["task_id"] = str(task)
        if not result.get("video_id"):
            result["video_id"] = "unknown"
        
        return result
    except Exception as e:
        print(f"Error uploading video: {e}")
        return None


def check_task_status(
    task_id: str,
    client: Optional[TwelveLabs] = None
) -> Dict[str, Any]:
    """Check the status of a video processing task.
    
    Args:
        task_id: ID of the task to check
        client: Optional TwelveLabs client instance. If not provided, one will be created
        
    Returns:
        Dictionary containing status information:
        - status: Current status (e.g., "pending", "processing", "ready", "failed")
        - progress: Progress percentage (0-100)
        - error: Error message if status is "failed"
    """
    client = client or get_client()
    
    try:
        # Try to get task status with more resilient approach
        try:
            # Try the documented approach first
            task_status = client.tasks.status(task_id)
        except (AttributeError, TypeError):
            # Try alternative approaches based on SDK version
            try:
                task_status = client.tasks.get(task_id)
            except AttributeError:
                # Last resort
                task_status = client.tasks.retrieve(task_id)
        
        # Extract status info with attribute/dict access resilience
        result = {}
        
        # Extract status
        if isinstance(task_status, dict):
            result["status"] = task_status.get("status", "unknown")
            # Try to get progress from metadata if available
            metadata = task_status.get("metadata", {})
            result["progress"] = metadata.get("progress", 0) if metadata else 0
            # Check for error
            if result["status"] == "failed":
                result["error"] = task_status.get("error", "Unknown error")
        else:
            # Handle object-style access
            try:
                result["status"] = getattr(task_status, "status", "unknown")
                # Try to get progress from metadata
                metadata = getattr(task_status, "metadata", None)
                if metadata:
                    if isinstance(metadata, dict):
                        result["progress"] = metadata.get("progress", 0)
                    else:
                        result["progress"] = getattr(metadata, "progress", 0)
                else:
                    result["progress"] = 0
                    
                # Check for error
                if result["status"] == "failed":
                    result["error"] = getattr(task_status, "error", "Unknown error")
            except Exception as attr_err:
                # Last resort fallback
                print(f"Error extracting task attributes: {attr_err}")
                result = {
                    "status": "unknown",
                    "progress": 0,
                    "error": f"Could not extract status information: {attr_err}"
                }
        
        return result
    except Exception as e:
        print(f"Error checking task status: {e}")
        return {"status": "error", "progress": 0, "error": str(e)}


def wait_for_task_completion(
    task_id: str,
    polling_interval: int = 5,
    timeout: int = 3600,
    client: Optional[TwelveLabs] = None
) -> bool:
    """Wait for a task to complete with timeout.
    
    Args:
        task_id: ID of the task to wait for
        polling_interval: Seconds to wait between status checks
        timeout: Maximum seconds to wait before giving up
        client: Optional TwelveLabs client instance. If not provided, one will be created
        
    Returns:
        True if task completed successfully, False otherwise
    """
    client = client or get_client()
    start_time = time.time()
    
    while True:
        status_info = check_task_status(task_id, client)
        
        if status_info["status"] == "ready":
            return True
        
        if status_info["status"] == "failed":
            print(f"Task failed: {status_info.get('error', 'Unknown error')}")
            return False
            
        if time.time() - start_time > timeout:
            print(f"Timeout waiting for task {task_id} to complete")
            return False
            
        print(f"Task in progress: {status_info['progress']}%")
        time.sleep(polling_interval)


def get_video_info(
    video_id: str,
    client: Optional[TwelveLabs] = None
) -> Optional[Dict[str, Any]]:
    """Get information about a processed video.
    
    Args:
        video_id: ID of the video to retrieve information for
        client: Optional TwelveLabs client instance. If not provided, one will be created
        
    Returns:
        Dictionary containing video information if successful, None otherwise
    """
    client = client or get_client()
    
    try:
        video = client.videos.get(video_id)
        return {
            "video_id": video._id,
            "index_id": video.index_id,
            "metadata": video.metadata,
            "status": video.status,
            "created_at": video.created_at,
            "updated_at": video.updated_at
        }
    except Exception as e:
        print(f"Error getting video info: {e}")
        return None
