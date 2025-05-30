# Twelve Labs Video Search Integration: Implementation Specification

## Overview

This specification outlines how to integrate Twelve Labs video search functionality with the existing brand compliance API. The integration will add a new tool to the OpenRouter agent that allows searching within videos for specific content, enhancing the compliance assessment capabilities of the platform.

## Integration Approach

We will implement a video search capability as a tool for the OpenRouter native agent that handles the check-video compliance API. The integration will:

1. Automatically process videos with Twelve Labs in the background during compliance analysis
2. Add a new `search_video` tool to the agent's toolset
3. Require no frontend changes or user intervention

**Advantages:**
- Seamless integration with existing compliance workflow
- No user interface changes required
- LLM can use video search as part of its compliance analysis
- Clear separation of code for maintainability

This approach aligns with the current architecture where the agent leverages various tools during compliance analysis. The video search tool will be one more capability at the agent's disposal.

## Implementation Plan

### 1. Dependencies and Configuration

```python
# Add to requirements.txt
twelvelabs==0.4.0  # Latest version compatible with API v1.3
python-dotenv==1.0.0
```

Environment variables to add in `.env`:
```
TWELVE_LABS_API_KEY=your_api_key_here
```

### 2. Twelve Labs Integration Module

We'll use the previously created Twelve Labs integration module at `/backend/app/core/twelve_labs/` with minimal modifications to ensure it works within the compliance API flow.

### 3. File Structure and Organization

We'll maintain a clean separation of concerns with the following structure:

```
backend/
  └── app/
      ├── core/
      │   ├── twelve_labs/            # Existing Twelve Labs module
      │   │   ├── client.py
      │   │   ├── config.py
      │   │   ├── ...
      │   │
      │   ├── video_agent/
      │   │   ├── twelve_labs_processor.py    # New: Background processing functions
      │   │   └── ...
      │   │
      │   └── openrouter_agent/
      │       ├── video_search_tool.py        # New: Video search tool implementation
      │       └── ...
      │
      └── db/
          └── firestore_twelve_labs.py        # New: Twelve Labs database functions
```

### 4. Background Video Processing Module

Create a new file `app/core/video_agent/twelve_labs_processor.py` to handle the background processing of videos with Twelve Labs:

```python
# app/core/video_agent/twelve_labs_processor.py

import asyncio
import os
from typing import Optional, Dict, Any

from app.core.twelve_labs.client import TwelveLabsClient
from app.db.firestore_twelve_labs import store_twelve_labs_mapping


async def process_video_with_twelve_labs(video_path: str, user_id: str, video_url: str) -> Dict[str, Any]:
    """Process a video with Twelve Labs for search capabilities.
    
    This function handles the entire workflow of processing a video with Twelve Labs:
    1. Creating/getting an index for the user
    2. Uploading the video to Twelve Labs
    3. Waiting for processing to complete
    4. Storing the mapping between the video URL and Twelve Labs IDs
    
    Args:
        video_path: Path to the downloaded video file
        user_id: ID of the user who uploaded the video
        video_url: Original URL of the video
        
    Returns:
        Dictionary with processing results or error information
    """
    try:
        # Initialize the Twelve Labs client
        client = TwelveLabsClient()
        
        # 1. Create or get an index for the user
        index_name = f"user_{user_id}_videos"
        
        # Check if index already exists
        indexes = client.list_indexes()
        index_id = None
        
        for index in indexes:
            if index.name == index_name:
                index_id = index._id
                break
        
        # Create index if it doesn't exist
        if not index_id:
            index_id = client.create_index(index_name)
            
        if not index_id:
            error_msg = f"Failed to create or get index for user {user_id}"
            print(f"[ERROR] {error_msg}")
            return {"success": False, "error": error_msg}
            
        # 2. Upload the video to Twelve Labs
        upload_result = client.upload_video(
            index_id=index_id,
            video_file=video_path,
        )
        
        if not upload_result:
            error_msg = "Failed to upload video to Twelve Labs"
            print(f"[ERROR] {error_msg}")
            return {"success": False, "error": error_msg}
            
        task_id = upload_result["task_id"]
        video_id = upload_result["video_id"]
        
        # 3. Wait for processing to complete
        processing_success = client.wait_for_task_completion(
            task_id=task_id,
            polling_interval=5,
            timeout=3600,  # 1 hour timeout
        )
        
        if not processing_success:
            error_msg = "Video processing failed in Twelve Labs"
            print(f"[ERROR] {error_msg}")
            return {"success": False, "error": error_msg}
            
        # 4. Store the mapping between the original video URL and Twelve Labs video_id
        # This will be used later to retrieve search results
        mapping_id = await store_twelve_labs_mapping(
            user_id=user_id,
            video_url=video_url,
            twelve_labs_index_id=index_id,
            twelve_labs_video_id=video_id,
        )
        
        print(f"[SUCCESS] Video successfully processed with Twelve Labs: index={index_id}, video={video_id}")
        
        return {
            "success": True,
            "index_id": index_id,
            "video_id": video_id,
            "mapping_id": mapping_id
        }
        
    except Exception as e:
        error_msg = f"Error processing video with Twelve Labs: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return {"success": False, "error": error_msg}


async def trigger_background_processing(video_path: str, user_id: str, video_url: str) -> None:
    """Trigger the Twelve Labs processing in the background.
    
    This function creates a background task for processing the video with Twelve Labs,
    ensuring it doesn't block the main compliance analysis flow.
    
    Args:
        video_path: Path to the downloaded video file
        user_id: ID of the user who uploaded the video
        video_url: Original URL of the video
    """
    # Create a background task for Twelve Labs processing
    asyncio.create_task(
        process_video_with_twelve_labs(
            video_path=video_path,
            user_id=user_id,
            video_url=video_url,
        )
    )
    print(f"[INFO] Started background processing of video with Twelve Labs: {video_url}")
```

### 5. Video Search Tool Implementation

Create a new file `app/core/openrouter_agent/video_search_tool.py` to implement the video search tool:

### 6. Database Functions

Create a new file `app/db/firestore_twelve_labs.py` for database functions related to Twelve Labs:

```python
# app/db/firestore_twelve_labs.py

from datetime import datetime
from typing import Dict, Optional, Any, List

from app.db.firestore import get_firestore_client


async def store_twelve_labs_mapping(
    user_id: str, 
    video_url: str, 
    twelve_labs_index_id: str, 
    twelve_labs_video_id: str
) -> str:
    """Store the mapping between a video URL and its Twelve Labs IDs.
    
    Args:
        user_id: ID of the user who uploaded the video
        video_url: Original URL of the video
        twelve_labs_index_id: ID of the Twelve Labs index
        twelve_labs_video_id: ID of the video in Twelve Labs
        
    Returns:
        ID of the created document
    """
    # Get Firestore client
    db = get_firestore_client()
    
    # Create a document with the mapping
    doc_ref = db.collection("twelve_labs_videos").document()
    doc_ref.set({
        "user_id": user_id,
        "video_url": video_url,
        "twelve_labs_index_id": twelve_labs_index_id,
        "twelve_labs_video_id": twelve_labs_video_id,
        "created_at": datetime.now(),
    })
    
    return doc_ref.id


async def get_twelve_labs_mapping(video_url: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get the Twelve Labs mapping for a video URL.
    
    Args:
        video_url: URL of the video to look up
        user_id: ID of the user who uploaded the video
        
    Returns:
        Dictionary with the mapping information if found, None otherwise
    """
    # Get Firestore client
    db = get_firestore_client()
    
    # Query for the mapping
    query = db.collection("twelve_labs_videos").where(
        "video_url", "==", video_url
    ).where("user_id", "==", user_id).limit(1)
    
    docs = query.stream()
    
    for doc in docs:
        return doc.to_dict()
        
    return None


async def get_user_twelve_labs_videos(user_id: str) -> List[Dict[str, Any]]:
    """Get all videos processed with Twelve Labs for a user.
    
    Args:
        user_id: ID of the user
        
    Returns:
        List of dictionaries with video information
    """
    # Get Firestore client
    db = get_firestore_client()
    
    # Query for all user videos
    query = db.collection("twelve_labs_videos").where("user_id", "==", user_id)
    
    results = []
    for doc in query.stream():
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)
        
    return results
```

### 7. Video Search Tool Implementation

Create a new file `app/core/openrouter_agent/video_search_tool.py` for the video search tool:

```python
# app/core/openrouter_agent/video_search_tool.py

from typing import Dict, Any, Optional, List
import asyncio

from app.core.twelve_labs.client import TwelveLabsClient
from app.db.firestore_twelve_labs import get_twelve_labs_mapping


# Tool definition for the OpenRouter agent
VIDEO_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_video",
        "description": "Search within a video for specific content, returning timestamps where the content appears",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query describing what to look for in the video"
                },
                "threshold": {
                    "type": "string",
                    "enum": ["high", "medium", "low", "none"],
                    "description": "The confidence threshold for results"
                }
            },
            "required": ["query"]
        }
    }
}


class VideoSearchTool:
    """Tool for searching within videos using Twelve Labs API.
    
    This tool is used by the OpenRouter agent to search for specific content
    within videos that have been processed by Twelve Labs.
    """
    
    def __init__(self, video_url: str, user_id: str):
        """Initialize the video search tool.
        
        Args:
            video_url: URL of the video to search
            user_id: ID of the user who uploaded the video
        """
        self.video_url = video_url
        self.user_id = user_id
        self.client = TwelveLabsClient()
        
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the video search with the given parameters.
        
        Args:
            params: Dictionary of parameters for the search:
                - query: Search query string
                - threshold: Optional confidence threshold (high, medium, low, none)
                
        Returns:
            Dictionary with search results or error information
        """
        query = params.get("query")
        threshold = params.get("threshold", "medium")
        
        if not query:
            return {"error": "Search query is required"}
            
        if not self.video_url:
            return {"error": "No video URL available for searching"}
            
        try:
            # Get the mapping
            mapping = await get_twelve_labs_mapping(self.video_url, self.user_id)
            
            if not mapping:
                return {
                    "error": "Video not found or not processed for search",
                    "message": "This video is still being processed for search capabilities. Please try again later."
                }
                
            # Search the video
            results = self.client.search_videos(
                index_id=mapping["twelve_labs_index_id"],
                query_text=query,
                threshold=threshold,
            )
            
            if not results:
                return {"message": f"No results found for query: {query}"}
                
            # Format the results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "timestamp": f"{result['start_time_formatted']} - {result['end_time_formatted']}",
                    "confidence": result['confidence'],
                    "score": result['score'],
                })
                
            return {
                "results": formatted_results,
                "message": f"Found {len(formatted_results)} segments matching '{query}'"
            }
            
        except Exception as e:
            return {"error": f"Error searching video: {str(e)}"}
```

### 8. Integration with Process Video Function

Modify the `process_video_frames_and_stream` function in `app/api/compliance.py` to trigger Twelve Labs processing in the background:

```python
# In app/api/compliance.py - process_video_frames_and_stream function

async def process_video_frames_and_stream(
    video_url: str, 
    message: str, 
    analysis_modes: List[str], 
    user_id: str, 
    brand_name: str = None,
):
    # Existing code for video processing...
    
    # After downloading the video and extracting frames successfully
    try:
        # Download the video
        yield "data: status:Downloading video file...\n\n"
        video_path_tuple = await download_video(video_url)
        video_path = video_path_tuple[0]  # Get the path to the downloaded video
        
        # Start Twelve Labs processing in background
        from app.core.video_agent.twelve_labs_processor import trigger_background_processing
        trigger_background_processing(
            video_path=video_path,
            user_id=user_id,
            video_url=video_url,
        )
        
        # Continue with the existing compliance analysis...
```

### 9. Integration with OpenRouter Native Agent

Modify the OpenRouter Native Agent to include the video search tool:

```python
# In app/core/openrouter_agent/native_agent.py

from app.core.openrouter_agent.video_search_tool import VIDEO_SEARCH_TOOL, VideoSearchTool

class OpenRouterAgent:
    # Existing code...
    
    def __init__(
        self,
        api_key: str,
        model: str = "anthropic/claude-3-7-sonnet",
        on_stream: Optional[Callable] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        user_id: Optional[str] = None,
        video_url: Optional[str] = None,  # Add video_url parameter
    ):
        # Existing initialization code...
        self.user_id = user_id
        self.video_url = video_url
        
        # Build tools list
        self.tools = [
            # Existing tools...
        ]
        
        # Add video search tool if video_url is provided
        if self.video_url and self.user_id:
            self.tools.append(VIDEO_SEARCH_TOOL)
            self.video_search_tool = VideoSearchTool(self.video_url, self.user_id)
    
    # Existing methods...
    
    async def handle_tool_call(self, tool_call):
        """Handle a tool call from the LLM."""
        # Existing tool handling code...
        
        # Add handling for video search tool
        if tool_name == "search_video":
            if hasattr(self, "video_search_tool"):
                return await self.video_search_tool.execute(tool_params)
            else:
                return {"error": "Video search tool not available"}
```

### 10. Updating the Agent Initialization in Compliance API

Update the agent initialization in `process_video_frames_and_stream` function to pass the video URL and user ID:

```python
# In app/api/compliance.py - process_video_frames_and_stream function

# When initializing the OpenRouterNativeAgent
agent = OpenRouterNativeAgent(
    api_key=OPENROUTER_API_KEY,
    model="anthropic/claude-3-7-sonnet",
    on_stream=on_stream,
    system_prompt=custom_system_prompt,
    temperature=0.1,
    user_id=user_id,          # Add user_id parameter
    video_url=video_url,      # Add video_url parameter
)
```

## Testing Plan

1. **Unit Testing**:
   - Test the Twelve Labs client module functions
   - Test the background processing functions
   - Test the video search tool implementation
   - Test the database functions

2. **Integration Testing**:
   - Test the automatic background processing of videos
   - Test the search functionality with the OpenRouter agent
   - Test various search queries with different thresholds
   - Test handling of videos not yet processed or failed processing

3. **End-to-End Testing**:
   - Upload a video and verify it's processed by Twelve Labs
   - Use the compliance API with a video and verify the agent can search it
   - Test with various video types and formats
   - Verify the agent can effectively use search results in compliance analysis

## Deployment Considerations

1. **Environment Configuration**:
   - Ensure the Twelve Labs API key is properly configured in the environment
   - Set up appropriate error logging for background processing

2. **Resource Management**:
   - Monitor API usage to stay within Twelve Labs rate limits
   - Implement appropriate timeout handling for long-running operations
   - Consider adding a database cleanup mechanism for old mappings

3. **Performance Optimization**:
   - Implement caching of search results to improve response times
   - Consider adding a queue system for processing multiple videos
   - Monitor and optimize memory usage during video processing

4. **Security**:
   - Ensure proper access control for the video search functionality
   - Validate all inputs to prevent security vulnerabilities
   - Properly handle and secure API keys and credentials
## Future Enhancements

1. **Advanced Brand Compliance Features**:
   - Automatically extract brand elements from videos (logos, colors, typography)
   - Pre-defined brand compliance queries based on brand guidelines
   - Integration with brand guidelines database for automatic compliance checks

2. **Search Enhancements**:
   - Support for image-based search queries to find similar visual elements
   - Visual heatmaps showing areas of brand guideline violations
   - Semantic search for abstract concepts like "brand tone" or "messaging style"

3. **Processing Improvements**:
   - Implement batch processing for multiple videos
   - Add priority queue for processing critical compliance checks first
   - Intelligent video segmentation to focus on key brand moments

4. **Reporting and Analytics**:
   - Generate comprehensive compliance reports with search-powered evidence
   - Track compliance trends over time across campaigns
   - Compare compliance metrics across different brand assets

5. **Integration Capabilities**:
   - Connect with other compliance tools in the workflow
   - Export findings to creative management platforms
   - API endpoints for third-party integrations

6. **Performance Optimizations**:
   - Implement smart caching for frequent searches
   - Reduce processing time through selective frame analysis
   - Memory optimizations for large video libraries
