"""Module for creating and managing video embeddings with Twelve Labs.

This module provides functions to create and retrieve video embeddings.
"""

from typing import Dict, List, Optional, Any, Union, BinaryIO

from twelvelabs import TwelveLabs
# Remove specific model imports that may not exist in the current SDK version
# Instead, we'll work directly with the TwelveLabs client

from .config import get_client
from .upload import check_task_status, wait_for_task_completion


def create_video_embeddings(
    model_name: str = "Marengo-retrieval-2.7",
    video_file: Optional[Union[str, BinaryIO]] = None,
    video_url: Optional[str] = None,
    video_embedding_scopes: Optional[List[str]] = None,
    client: Optional[TwelveLabs] = None
) -> Optional[str]:
    """Create embeddings for a video file or URL.
    
    Args:
        model_name: Name of the model to use for generating embeddings
        video_file: Path to local video file or file-like object
        video_url: URL of video to generate embeddings for
        video_embedding_scopes: Scope of embeddings to generate ("clip" and/or "video")
        client: Optional TwelveLabs client instance. If not provided, one will be created
        
    Returns:
        Task ID if successful, None otherwise
        
    Raises:
        ValueError: If neither video_file nor video_url is provided
    """
    if not video_file and not video_url:
        raise ValueError("Either video_file or video_url must be provided")
    
    # Default embedding scopes if none provided
    if video_embedding_scopes is None:
        video_embedding_scopes = ["clip", "video"]
    
    client = client or get_client()
    
    try:
        task_params = {
            "model_name": model_name,
            "video_embedding_scopes": video_embedding_scopes
        }
        
        if video_file:
            task_params["video_file"] = video_file
        elif video_url:
            task_params["video_url"] = video_url
        
        task = client.embeddings.create(**task_params)
        return task._id
    except Exception as e:
        print(f"Error creating video embeddings: {e}")
        return None


def check_embeddings_task_status(
    task_id: str,
    client: Optional[TwelveLabs] = None
) -> Dict[str, Any]:
    """Check the status of a video embedding task.
    
    Args:
        task_id: ID of the embedding task to check
        client: Optional TwelveLabs client instance. If not provided, one will be created
        
    Returns:
        Dictionary containing status information
    """
    client = client or get_client()
    
    try:
        task_status = client.embeddings.status(task_id)
        
        result = {
            "status": task_status.status,
            "progress": task_status.metadata.get("progress", 0) if task_status.metadata else 0
        }
        
        if task_status.status == "failed" and task_status.error:
            result["error"] = task_status.error
            
        return result
    except Exception as e:
        print(f"Error checking embeddings task status: {e}")
        return {"status": "error", "progress": 0, "error": str(e)}


def wait_for_embeddings_completion(
    task_id: str,
    polling_interval: int = 5,
    timeout: int = 3600,
    client: Optional[TwelveLabs] = None
) -> bool:
    """Wait for an embeddings task to complete with timeout.
    
    Args:
        task_id: ID of the task to wait for
        polling_interval: Seconds to wait between status checks
        timeout: Maximum seconds to wait before giving up
        client: Optional TwelveLabs client instance. If not provided, one will be created
        
    Returns:
        True if task completed successfully, False otherwise
    """
    client = client or get_client()
    import time
    start_time = time.time()
    
    while True:
        status_info = check_embeddings_task_status(task_id, client)
        
        if status_info["status"] == "ready":
            return True
        
        if status_info["status"] == "failed":
            print(f"Embeddings task failed: {status_info.get('error', 'Unknown error')}")
            return False
            
        if time.time() - start_time > timeout:
            print(f"Timeout waiting for embeddings task {task_id} to complete")
            return False
            
        print(f"Embeddings task in progress: {status_info['progress']}%")
        time.sleep(polling_interval)


def retrieve_video_embeddings(
    task_id: str,
    client: Optional[TwelveLabs] = None
) -> Optional[List[Dict[str, Any]]]:
    """Retrieve video embeddings once processing is complete.
    
    Args:
        task_id: ID of the embedding task
        client: Optional TwelveLabs client instance. If not provided, one will be created
        
    Returns:
        List of embeddings if successful, None otherwise
    """
    client = client or get_client()
    
    try:
        # Check task status first
        task_status = check_embeddings_task_status(task_id, client)
        
        if task_status["status"] != "ready":
            print(f"Task not ready. Current status: {task_status['status']}")
            return None
            
        # Retrieve the embeddings
        embeddings_task = client.embeddings.retrieve(task_id=task_id)
        
        if not embeddings_task.video_embeddings:
            print("No embeddings available")
            return None
            
        # Format the embeddings data for easier consumption
        formatted_embeddings = []
        for embedding in embeddings_task.video_embeddings:
            formatted_embeddings.append({
                "embedding_id": embedding.id if hasattr(embedding, 'id') else None,
                "video_id": embedding.video_id if hasattr(embedding, 'video_id') else None,
                "scope": embedding.scope if hasattr(embedding, 'scope') else None,
                "start": embedding.start if hasattr(embedding, 'start') else None,
                "end": embedding.end if hasattr(embedding, 'end') else None,
                "values": embedding.values if hasattr(embedding, 'values') else None
            })
            
        return formatted_embeddings
    except Exception as e:
        print(f"Error retrieving video embeddings: {e}")
        return None
