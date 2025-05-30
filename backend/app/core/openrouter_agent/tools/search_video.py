# app/core/openrouter_agent/tools/search_video.py

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List

from app.core.twelve_labs.client import TwelveLabsClient
from app.db.firestore_twelve_labs import get_twelve_labs_mapping

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NOT_PROCESSED_MESSAGE = "Video not found or still being processed. Please wait a few minutes and try again."

async def search_video(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search for specific content within the video being analyzed.
    
    Args:
        args: Dictionary containing:
            query: The search query describing what to look for
            threshold: Optional confidence threshold (high, medium, low, none)
            video_url: The URL of the video to search (added by the agent framework)
            user_id: The ID of the user (added by the agent framework)
            task_detail: A brief description of the task
    
    Returns:
        Dictionary with search results or error information
    """
    start_time = time.time()
    logger.info("🔍 VIDEO SEARCH: Starting search_video function execution")
    logger.info(f"🔍 VIDEO SEARCH: Received parameters: {args.keys()}")
    
    # Extract parameters
    query = args.get("query")
    threshold = args.get("threshold", "medium")
    video_url = args.get("video_url")
    user_id = args.get("user_id")
    task_detail = args.get("task_detail", "Video content search")
    
    logger.info(f"🔍 VIDEO SEARCH: Query: '{query}', Threshold: {threshold}")
    logger.info(f"🔍 VIDEO SEARCH: Video URL: {video_url}")
    logger.info(f"🔍 VIDEO SEARCH: User ID: {user_id}")
    
    # Validate parameters
    if not query:
        logger.error("🔍 VIDEO SEARCH: Missing required parameter 'query'")
        return {"error": "Search query is required."}
    
    if not video_url or not user_id:
        logger.error(f"🔍 VIDEO SEARCH: Missing required parameters - video_url: {'✓' if video_url else '✗'}, user_id: {'✓' if user_id else '✗'}")
        return {"error": "Video URL and User ID are required but were not provided."}
    
    try:
        # Get the mapping for the video
        logger.info(f"🔍 VIDEO SEARCH: Getting Twelve Labs mapping for video URL: {video_url}")
        mapping_start = time.time()
        mapping = await get_twelve_labs_mapping(video_url, user_id)
        logger.info(f"🔍 VIDEO SEARCH: Mapping lookup completed in {time.time() - mapping_start:.2f}s")
        
        if not mapping:
            logger.warning(f"🔍 VIDEO SEARCH: No mapping found for video URL: {video_url}")
            return {
                "task": task_detail,
                "error": NOT_PROCESSED_MESSAGE,
                "results": [],
                "status": "pending"
            }
        
        logger.info(f"🔍 VIDEO SEARCH: Found mapping - Index ID: {mapping['twelve_labs_index_id']}, Video ID: {mapping['twelve_labs_video_id']}")
        
        # Initialize Twelve Labs client
        logger.info("🔍 VIDEO SEARCH: Initializing Twelve Labs client")
        client = TwelveLabsClient()
        
        # Perform the search
        logger.info(f"🔍 VIDEO SEARCH: Executing search with query: '{query}'")
        search_start = time.time()
        results = client.search_videos(
            index_id=mapping["twelve_labs_index_id"],
            query_text=query,
            threshold=threshold
        )
        logger.info(f"🔍 VIDEO SEARCH: Search completed in {time.time() - search_start:.2f}s, found {len(results)} results")
        
        # Format results
        logger.info("🔍 VIDEO SEARCH: Formatting search results")
        formatted_results = []
        for i, result in enumerate(results):
            try:
                # Handle different result formats with resilient field access
                formatted_result = {}
                
                # Get start and end times with fallbacks
                start_time = None
                end_time = None
                start_formatted = "00:00:00"
                end_formatted = "00:00:00"
                
                # Try to get start and end times with various field names
                for start_field in ['start_time', 'start', 'startTime', 'start_seconds']:
                    if start_field in result:
                        start_time = result[start_field]
                        break
                        
                for end_field in ['end_time', 'end', 'endTime', 'end_seconds']:
                    if end_field in result:
                        end_time = result[end_field]
                        break
                
                # Get formatted timestamps if available, or format them ourselves
                if 'start_time_formatted' in result:
                    start_formatted = result['start_time_formatted']
                elif start_time is not None:
                    from app.core.twelve_labs.search import format_timestamp
                    try:
                        start_formatted = format_timestamp(float(start_time))
                    except (ValueError, TypeError):
                        pass
                        
                if 'end_time_formatted' in result:
                    end_formatted = result['end_time_formatted']
                elif end_time is not None:
                    from app.core.twelve_labs.search import format_timestamp
                    try:
                        end_formatted = format_timestamp(float(end_time))
                    except (ValueError, TypeError):
                        pass
                
                # Build the formatted result
                formatted_result = {
                    "timestamp": f"{start_formatted} - {end_formatted}",
                    "confidence": result.get('confidence', 0),
                    "score": float(result.get('score', 0)),
                    "start_seconds": start_time or 0,
                    "end_seconds": end_time or 0
                }
                
                # Add text match information if available
                if 'text_matches' in result:
                    formatted_result['text_matches'] = result['text_matches']
                    
                formatted_results.append(formatted_result)
                if i < 3:  # Log just the first few results for clarity
                    logger.info(f"🔍 VIDEO SEARCH: Result {i+1}: {formatted_result['timestamp']} (confidence: {formatted_result['confidence']})")
            except Exception as format_err:
                logger.error(f"🔍 VIDEO SEARCH: Error formatting result {i}: {str(format_err)}")
        
        if len(results) > 3:
            logger.info(f"🔍 VIDEO SEARCH: ...and {len(results) - 3} more results")
        
        # Build response
        logger.info("🔍 VIDEO SEARCH: Building final response")
        response = {
            "task": task_detail,
            "query": query,
            "results": formatted_results,
            "result_count": len(formatted_results),
            "status": "success"
        }
        
        # Add a helpful message
        if not formatted_results:
            logger.info("🔍 VIDEO SEARCH: No results found")
            response["message"] = f"No results found for '{query}'."
        else:
            logger.info(f"🔍 VIDEO SEARCH: Found {len(formatted_results)} segments matching '{query}'")
            response["message"] = f"Found {len(formatted_results)} segments matching '{query}'."
        
        total_time = time.time() - start_time
        logger.info(f"🔍 VIDEO SEARCH: Search operation completed in {total_time:.2f}s")
        return response
        
    except Exception as e:
        logger.error(f"🔍 VIDEO SEARCH: Error during search operation: {str(e)}", exc_info=True)
        return {
            "task": task_detail,
            "error": f"Error searching video: {str(e)}",
            "results": [],
            "status": "error"
        }
