"""Main client module for Twelve Labs video search functionality.

This module provides a unified interface to all Twelve Labs functionality.
"""

from typing import Dict, List, Optional, Any, Union, BinaryIO

from twelvelabs import TwelveLabs

from .config import get_client
from .indexes import create_index, list_indexes, get_index, delete_index
from .upload import upload_video, check_task_status, wait_for_task_completion, get_video_info
from .embeddings import (
    create_video_embeddings, check_embeddings_task_status,
    wait_for_embeddings_completion, retrieve_video_embeddings
)
from .search import search_videos, search_videos_with_image, format_timestamp


class TwelveLabsClient:
    """Client class for interacting with Twelve Labs video search functionality.
    
    This class provides a unified interface to all Twelve Labs functionality,
    including index management, video uploads, embeddings creation, and search.
    It directly exposes the namespaced interfaces of the Twelve Labs SDK.
    
    Attributes:
        client: Initialized TwelveLabs SDK client
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the TwelveLabsClient.
        
        Args:
            api_key: Optional API key. If not provided, will be read from environment variables.
        """
        self.client = get_client(api_key)
        
        # Directly expose the namespaced interfaces from the SDK
        # This provides access to client.indexes.create(), client.tasks.create(), etc.
        self.indexes = self.client.indexes if hasattr(self.client, 'indexes') else None
        self.tasks = self.client.tasks if hasattr(self.client, 'tasks') else None
        self.search = self.client.search if hasattr(self.client, 'search') else None
        
    # Maintain backward compatibility with previous implementation
    def create_index(self, index_name: str, models: Optional[List[Dict[str, Any]]] = None,
                   addons: Optional[List[str]] = None) -> Union[str, None]:
        """Create a new index for video processing."""
        if self.indexes and hasattr(self.indexes, 'create'):
            try:
                index = self.indexes.create(name=index_name, models=models, addons=addons)
                if hasattr(index, 'id'):
                    return index.id
                elif hasattr(index, '_id'):
                    return index._id
                elif isinstance(index, dict) and 'id' in index:
                    return index['id']
                return str(index)
            except Exception as e:
                print(f"Error creating index: {e}")
                return None
        else:
            return create_index(index_name, models, addons, self.client)
    
    def list_indexes(self) -> List[Any]:
        """List all available indexes."""
        if self.indexes and hasattr(self.indexes, 'list'):
            try:
                return list(self.indexes.list())
            except Exception as e:
                print(f"Error listing indexes: {e}")
                return []
        else:
            return list_indexes(self.client)
    
    def get_index(self, index_id: str) -> Optional[Any]:
        """Get details for a specific index."""
        if self.indexes and hasattr(self.indexes, 'retrieve'):
            try:
                return self.indexes.retrieve(index_id)
            except Exception as e:
                print(f"Error retrieving index: {e}")
                return None
        else:
            return get_index(index_id, self.client)
    
    def delete_index(self, index_id: str) -> bool:
        """Delete a specific index."""
        if self.indexes and hasattr(self.indexes, 'delete'):
            try:
                self.indexes.delete(index_id)
                return True
            except Exception as e:
                print(f"Error deleting index: {e}")
                return False
        else:
            return delete_index(index_id, self.client)
    
    # Video upload and processing
    def upload_video(self, index_id: str, video_file: Optional[Union[str, BinaryIO]] = None,
                   video_url: Optional[str] = None) -> Optional[Dict[str, str]]:
        """Upload a video file or URL to the specified index."""
        if self.tasks and hasattr(self.tasks, 'create'):
            try:
                if video_file:
                    task = self.tasks.create(index_id=index_id, video_file=video_file)
                elif video_url:
                    task = self.tasks.create(index_id=index_id, video_url=video_url)
                else:
                    raise ValueError("Either video_file or video_url must be provided")
                
                return {
                    "task_id": task._id if hasattr(task, '_id') else None,
                    "video_id": task.video_id if hasattr(task, 'video_id') else None
                }
            except Exception as e:
                print(f"Error uploading video: {e}")
                return None
        else:
            return upload_video(index_id, video_file, video_url, self.client)
    
    # Task status methods
    def check_task_status(self, task_id: str) -> Dict[str, Any]:
        """Check the status of a video processing task."""
        if self.tasks and hasattr(self.tasks, 'status'):
            try:
                status = self.tasks.status(task_id)
                return {
                    "status": status.status if hasattr(status, 'status') else "unknown",
                    "progress": status.metadata.get("progress", 0) if hasattr(status, 'metadata') else 0
                }
            except Exception as e:
                print(f"Error checking task status: {e}")
                return {"status": "error", "progress": 0}
        else:
            return check_task_status(task_id, self.client)
    
    def wait_for_task_completion(self, task_id: str, polling_interval: int = 5,
                              timeout: int = 3600) -> bool:
        """Wait for a task to complete with timeout."""
        if self.tasks and hasattr(self.tasks, 'status'):
            import time
            start_time = time.time()
            
            while True:
                try:
                    status_info = self.check_task_status(task_id)
                    
                    if status_info["status"] == "ready":
                        return True
                    
                    if status_info["status"] == "failed":
                        return False
                        
                    if time.time() - start_time > timeout:
                        print(f"Timeout waiting for task {task_id} to complete")
                        return False
                        
                    print(f"Task in progress: {status_info['progress']}%")
                    time.sleep(polling_interval)
                except Exception as e:
                    print(f"Error waiting for task completion: {e}")
                    return False
        else:
            return wait_for_task_completion(task_id, polling_interval, timeout, self.client)
    
    def get_video_info(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a processed video."""
        if self.indexes and hasattr(self.indexes, 'videos') and hasattr(self.indexes.videos, 'get'):
            try:
                video_info = self.indexes.videos.get(video_id)
                return video_info if isinstance(video_info, dict) else video_info.__dict__
            except Exception as e:
                print(f"Error getting video info: {e}")
                return None
        else:
            return get_video_info(video_id, self.client)
    
    # Video embeddings
    def create_video_embeddings(self, model_name: str = "Marengo-retrieval-2.7",
                              video_file: Optional[Union[str, BinaryIO]] = None,
                              video_url: Optional[str] = None,
                              video_embedding_scopes: Optional[List[str]] = None) -> Optional[str]:
        """Create embeddings for a video file or URL."""
        if hasattr(self.client, 'embeddings') and hasattr(self.client.embeddings, 'create'):
            try:
                if video_file:
                    task = self.client.embeddings.create(
                        model_name=model_name,
                        video_file=video_file,
                        video_embedding_scopes=video_embedding_scopes
                    )
                elif video_url:
                    task = self.client.embeddings.create(
                        model_name=model_name,
                        video_url=video_url,
                        video_embedding_scopes=video_embedding_scopes
                    )
                else:
                    raise ValueError("Either video_file or video_url must be provided")
                    
                return task._id if hasattr(task, '_id') else str(task)
            except Exception as e:
                print(f"Error creating embeddings: {e}")
                return None
        else:
            return create_video_embeddings(
                model_name, video_file, video_url, video_embedding_scopes, self.client
            )
    
    def check_embeddings_task_status(self, task_id: str) -> Dict[str, Any]:
        """Check the status of a video embedding task."""
        if hasattr(self.client, 'embeddings') and hasattr(self.client.embeddings, 'status'):
            try:
                status = self.client.embeddings.status(task_id)
                return {
                    "status": status.status if hasattr(status, 'status') else "unknown",
                    "progress": status.metadata.get("progress", 0) if hasattr(status, 'metadata') else 0
                }
            except Exception as e:
                print(f"Error checking embeddings task status: {e}")
                return {"status": "error", "progress": 0}
        else:
            return check_embeddings_task_status(task_id, self.client)
    
    def wait_for_embeddings_completion(self, task_id: str, polling_interval: int = 5,
                                     timeout: int = 3600) -> bool:
        """Wait for an embeddings task to complete with timeout."""
        if hasattr(self.client, 'embeddings'):
            import time
            start_time = time.time()
            
            while True:
                try:
                    status_info = self.check_embeddings_task_status(task_id)
                    
                    if status_info["status"] == "ready":
                        return True
                    
                    if status_info["status"] == "failed":
                        return False
                        
                    if time.time() - start_time > timeout:
                        print(f"Timeout waiting for embeddings task {task_id} to complete")
                        return False
                        
                    print(f"Embeddings task in progress: {status_info['progress']}%")
                    time.sleep(polling_interval)
                except Exception as e:
                    print(f"Error waiting for embeddings task completion: {e}")
                    return False
        else:
            return wait_for_embeddings_completion(
                task_id, polling_interval, timeout, self.client
            )
    
    def retrieve_video_embeddings(self, task_id: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve video embeddings once processing is complete."""
        if hasattr(self.client, 'embeddings') and hasattr(self.client.embeddings, 'retrieve'):
            try:
                embeddings = self.client.embeddings.retrieve(task_id)
                # Format the result based on the response structure
                if hasattr(embeddings, 'data'):
                    return embeddings.data
                elif isinstance(embeddings, list):
                    return embeddings
                else:
                    return [embeddings]
            except Exception as e:
                print(f"Error retrieving embeddings: {e}")
                return None
        else:
            return retrieve_video_embeddings(task_id, self.client)
    
    # Video search
    def search_videos(self, index_id: str, query_text: str, options: List[str] = None,
                    group_by: Optional[str] = None, threshold: Optional[str] = None,
                    operator: Optional[str] = None, page_limit: Optional[int] = 10,
                    sort_option: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for video clips matching the query text."""
        if self.search and hasattr(self.search, 'query'):
            try:
                search_results = self.search.query(
                    index_id=index_id,
                    query_text=query_text,
                    options=options,
                    group_by=group_by,
                    threshold=threshold,
                    operator=operator,
                    page_limit=page_limit,
                    sort_option=sort_option
                )
                
                results = []
                
                # Process results based on the response structure
                if hasattr(search_results, 'data'):
                    results.extend(search_results.data)
                    
                    # Get additional pages if available and if pagination is supported
                    if hasattr(search_results, 'next') and callable(search_results.next):
                        try:
                            while True:
                                next_page = search_results.next()
                                if hasattr(next_page, 'data'):
                                    results.extend(next_page.data)
                                else:
                                    break
                        except (StopIteration, Exception) as e:
                            if not isinstance(e, StopIteration):
                                print(f"Error getting next page: {e}")
                elif isinstance(search_results, list):
                    results = search_results
                
                return results
            except Exception as e:
                print(f"Error searching videos: {e}")
                return []
        else:
            return search_videos(
                index_id, query_text, options, group_by, threshold,
                operator, page_limit, sort_option, self.client
            )
    
    def search_videos_with_image(self, index_id: str, image_file: Optional[str] = None,
                               image_url: Optional[str] = None, options: List[str] = None,
                               group_by: Optional[str] = None, threshold: Optional[str] = None,
                               page_limit: Optional[int] = 10,
                               sort_option: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for video clips using an image query."""
        if self.search and hasattr(self.search, 'query_by_image'):
            try:
                # Prepare parameters
                params = {
                    'index_id': index_id,
                    'options': options,
                    'group_by': group_by,
                    'threshold': threshold,
                    'page_limit': page_limit,
                    'sort_option': sort_option
                }
                
                if image_file:
                    params['image_file'] = image_file
                elif image_url:
                    params['image_url'] = image_url
                else:
                    raise ValueError("Either image_file or image_url must be provided")
                
                # Execute search
                search_results = self.search.query_by_image(**params)
                
                results = []
                
                # Process results based on the response structure
                if hasattr(search_results, 'data'):
                    results.extend(search_results.data)
                    
                    # Get additional pages if available
                    if hasattr(search_results, 'next') and callable(search_results.next):
                        try:
                            while True:
                                next_page = search_results.next()
                                if hasattr(next_page, 'data'):
                                    results.extend(next_page.data)
                                else:
                                    break
                        except (StopIteration, Exception) as e:
                            if not isinstance(e, StopIteration):
                                print(f"Error getting next page: {e}")
                elif isinstance(search_results, list):
                    results = search_results
                
                return results
            except Exception as e:
                print(f"Error searching videos with image: {e}")
                return []
        else:
            return search_videos_with_image(
                index_id, image_file, image_url, options, group_by,
                threshold, page_limit, sort_option, self.client
            )
    
    # Additional helper methods
    def check_processing_started(self, video_id: str, index_id: str) -> bool:
        """Check if processing has started for a video."""
        try:
            video_info = self.get_video_info(video_id)
            return video_info is not None
        except Exception as e:
            print(f"Error checking if processing started: {e}")
            return False
    
    def check_processing_complete(self, video_id: str, index_id: str) -> bool:
        """Check if processing is complete for a video."""
        try:
            video_info = self.get_video_info(video_id)
            
            if not video_info:
                return False
                
            # Check status based on response structure
            if isinstance(video_info, dict):
                status = video_info.get('status', '').lower()
                return status == 'ready' or status == 'completed' or status == 'done'
            elif hasattr(video_info, 'status'):
                status = video_info.status.lower() if isinstance(video_info.status, str) else ''
                return status == 'ready' or status == 'completed' or status == 'done'
            
            return False
        except Exception as e:
            print(f"Error checking if processing complete: {e}")
            return False
