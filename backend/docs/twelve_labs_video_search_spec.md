# Twelve Labs Video Search Implementation Specification

## Implementation Status

- ✅ Setting up the environment and initializing the SDK
- ✅ Creating and managing indexes
- ✅ Uploading videos and monitoring processing status
- ✅ Creating video embeddings
- ✅ Implementing video search functionality
- ✅ Creating a unified client interface
- ✅ Example usage script

## Overview

This document outlines the implementation plan for integrating Twelve Labs video understanding API into our brand compliance AI project. The integration will enable users to upload videos, generate embeddings, and perform semantic searches to find specific moments or content within those videos.

## Key Functionality

1. Upload videos to Twelve Labs platform
2. Process videos to generate embeddings and enable search
3. Perform semantic search using text queries
4. Retrieve and display search results with timestamps

## Implementation Architecture

### Prerequisites

- Python 3.7+
- Twelve Labs API key
- Required Python packages:
  - `twelvelabs`: Official Twelve Labs Python SDK
  - `requests`: For HTTP requests
  - `python-dotenv`: For environment variable management

### Core Components

1. **Video Upload and Processing Service**
   - Handles video file uploads
   - Creates indexes in Twelve Labs platform
   - Submits videos for processing
   - Monitors task status

2. **Video Search Service**
   - Processes search queries
   - Communicates with Twelve Labs API
   - Formats and returns search results

3. **Result Presentation Layer**
   - Displays search results with timestamps
   - Provides video playback functionality starting at relevant timestamps

## Implementation Steps

### 1. Setting Up the Environment

```python
# Installation
pip install twelvelabs requests python-dotenv
```

```python
# Configuration
# .env file structure
TWELVE_LABS_API_KEY=your_api_key_here
```

### 2. Initializing the SDK

```python
from twelvelabs import TwelveLabs
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize the SDK client
client = TwelveLabs(api_key=os.getenv("TWELVE_LABS_API_KEY"))
```

### 3. Creating an Index

```python
def create_video_index(index_name):
    """Create a new index for video processing"""
    try:
        index = client.indexes.create(
            index_name=index_name,
            models=[
                {
                    "model_name": "marengo2.7",
                    "model_options": ["visual", "audio"]
                }
            ],
            addons=["thumbnail"]
        )
        return index._id
    except Exception as e:
        print(f"Error creating index: {e}")
        return None
```

### 4. Uploading Videos

```python
def upload_video(index_id, video_path=None, video_url=None):
    """Upload a video file or URL to the specified index"""
    try:
        if video_path:
            # Upload from local file
            task = client.tasks.create(
                index_id=index_id,
                video_file=video_path
            )
        elif video_url:
            # Upload from URL
            task = client.tasks.create(
                index_id=index_id,
                video_url=video_url
            )
        else:
            raise ValueError("Either video_path or video_url must be provided")
            
        # Return task ID and video ID for status tracking
        return {
            "task_id": task._id,
            "video_id": task.video_id
        }
    except Exception as e:
        print(f"Error uploading video: {e}")
        return None
```

### 5. Monitoring Task Status

```python
def check_task_status(task_id):
    """Check the status of a video processing task"""
    try:
        task_status = client.tasks.status(task_id)
        return {
            "status": task_status.status,
            "progress": task_status.metadata.get("progress", 0) if task_status.metadata else 0
        }
    except Exception as e:
        print(f"Error checking task status: {e}")
        return {"status": "error", "progress": 0}

def wait_for_task_completion(task_id, polling_interval=5, timeout=3600):
    """Wait for a task to complete with timeout"""
    import time
    start_time = time.time()
    
    while True:
        status_info = check_task_status(task_id)
        
        if status_info["status"] == "ready":
            return True
        
        if status_info["status"] == "failed":
            return False
            
        if time.time() - start_time > timeout:
            print(f"Timeout waiting for task {task_id} to complete")
            return False
            
        print(f"Task in progress: {status_info['progress']}%")
        time.sleep(polling_interval)
```

### 6. Searching Videos

```python
def search_videos(index_id, query_text, options=["visual", "audio"], page_limit=10):
    """Search for video clips matching the query text"""
    try:
        search_results = client.search.query(
            index_id=index_id,
            query_text=query_text,
            options=options,
            page_limit=page_limit
        )
        
        results = []
        
        # Process first page of results
        results.extend(format_search_results(search_results.data))
        
        # Get additional pages if available
        try:
            while True:
                next_page = next(search_results)
                results.extend(format_search_results(next_page))
        except StopIteration:
            pass
            
        return results
    except Exception as e:
        print(f"Error searching videos: {e}")
        return []

def format_search_results(result_page):
    """Format the search results for easy consumption"""
    formatted_results = []
    
    for clip in result_page:
        formatted_results.append({
            "video_id": clip.video_id,
            "score": clip.score,
            "confidence": clip.confidence,
            "start_time": clip.start,
            "end_time": clip.end,
            "start_time_formatted": format_timestamp(clip.start),
            "end_time_formatted": format_timestamp(clip.end),
            "thumbnail": clip.thumbnail if hasattr(clip, 'thumbnail') else None
        })
    
    return formatted_results

def format_timestamp(seconds):
    """Format seconds into HH:MM:SS"""
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
```

### 7. Creating Video Embeddings (Alternative Approach)

```python
def create_video_embeddings(video_path=None, video_url=None):
    """Create embeddings for a video file or URL"""
    try:
        if video_path:
            # Create embeddings from local file
            task = client.embeddings.create(
                model_name="Marengo-retrieval-2.7",
                video_file=video_path,
                video_embedding_scopes=["clip", "video"]
            )
        elif video_url:
            # Create embeddings from URL
            task = client.embeddings.create(
                model_name="Marengo-retrieval-2.7",
                video_url=video_url,
                video_embedding_scopes=["clip", "video"]
            )
        else:
            raise ValueError("Either video_path or video_url must be provided")
            
        # Return task ID for status tracking
        return task._id
    except Exception as e:
        print(f"Error creating video embeddings: {e}")
        return None

def retrieve_video_embeddings(task_id):
    """Retrieve video embeddings once processing is complete"""
    try:
        # Check task status first
        task_status = client.embeddings.status(task_id)
        
        if task_status.status != "ready":
            print(f"Task not ready. Current status: {task_status.status}")
            return None
            
        # Retrieve the embeddings
        embeddings_task = client.embeddings.retrieve(task_id=task_id)
        
        if not embeddings_task.video_embeddings:
            print("No embeddings available")
            return None
            
        return embeddings_task.video_embeddings
    except Exception as e:
        print(f"Error retrieving video embeddings: {e}")
        return None
```

## Complete Usage Example

```python
# Example workflow for video upload and search
import os
from twelvelabs import TwelveLabs
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the SDK client
client = TwelveLabs(api_key=os.getenv("TWELVE_LABS_API_KEY"))

# Create a new index
index_name = "brand_compliance_videos"
index_id = create_video_index(index_name)
print(f"Created index: {index_id}")

# Upload a video
video_path = "/path/to/video.mp4"
upload_result = upload_video(index_id, video_path=video_path)
print(f"Uploaded video: {upload_result}")

# Wait for processing to complete
task_id = upload_result["task_id"]
if wait_for_task_completion(task_id):
    print("Video processing completed successfully")
    
    # Search for content in the video
    search_query = "person wearing red shirt"
    results = search_videos(index_id, search_query)
    
    # Display results
    print(f"Found {len(results)} matches for '{search_query}':")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['start_time_formatted']} - {result['end_time_formatted']} (Confidence: {result['confidence']})")
else:
    print("Video processing failed")
```

## Error Handling and Best Practices

1. **API Rate Limits**:
   - Implement exponential backoff for retries on rate limit errors
   - Use appropriate polling intervals when checking task status

2. **File Size and Format Limitations**:
   - Validate video files before uploading (supported formats, resolution, etc.)
   - Consider implementing client-side compression for large files

3. **Error Handling**:
   - Implement comprehensive error handling for all API interactions
   - Log detailed error information for debugging

4. **Security**:
   - Store API keys securely using environment variables
   - Implement user authentication and authorization for access control

## Future Enhancements

1. **Advanced Search Features**:
   - Implement search filtering and sorting options
   - Add support for image-based search queries

2. **Caching**:
   - Implement caching for search results to improve performance
   - Store video metadata locally to reduce API calls

3. **Batch Processing**:
   - Add support for batch video uploads and processing
   - Implement background tasks for long-running operations

4. **User Interface**:
   - Develop a user-friendly interface for video search and browsing
   - Implement video playback with highlighted segments based on search results

## Conclusion

This implementation plan provides a comprehensive approach to integrating Twelve Labs video understanding technology into our application. By following this specification, we can build a robust video search functionality that enables users to easily find specific moments and content within their videos, enhancing the brand compliance analysis capabilities of our platform.
