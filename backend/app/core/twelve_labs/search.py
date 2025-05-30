"""Module for searching video content using Twelve Labs API.

This module provides functions to search for specific content within videos.
"""

from typing import Dict, List, Optional, Any, Union

from twelvelabs import TwelveLabs

from .config import get_client


def search_videos(
    index_id: str,
    query_text: str,
    options: List[str] = None,
    group_by: Optional[str] = None,
    threshold: Optional[str] = None,
    operator: Optional[str] = None,
    page_limit: Optional[int] = 10,
    sort_option: Optional[str] = None,
    client: Optional[TwelveLabs] = None
) -> List[Dict[str, Any]]:
    """Search for video clips matching the query text.
    
    Args:
        index_id: ID of the index to search in
        query_text: Text query to search for
        options: Search options (e.g., ["visual", "audio"])
        group_by: How to group results ("video" or "clip")
        threshold: Confidence threshold ("high", "medium", "low", "none")
        operator: Logical operator for multi-term queries ("or", "and")
        page_limit: Number of results per page
        sort_option: How to sort results ("score", "clip_count")
        client: Optional TwelveLabs client instance. If not provided, one will be created
        
    Returns:
        List of formatted search results
    """
    # Default search options if none provided
    if options is None:
        options = ["visual", "audio"]
    
    client = client or get_client()
    
    try:
        # Prepare search parameters
        search_params = {
            "index_id": index_id,
            "query_text": query_text,
            "options": options,
            "page_limit": page_limit
        }
        
        # Add optional parameters if provided
        if group_by:
            search_params["group_by"] = group_by
        if threshold:
            search_params["threshold"] = threshold
        if operator:
            search_params["operator"] = operator
        if sort_option:
            search_params["sort_option"] = sort_option
        
        # Try different approaches to handle SDK structure differences
        try:
            # First try the documented approach
            search_results = client.search.query(**search_params)
        except (AttributeError, TypeError):
            # Try alternative approaches
            try:
                # Some versions might use different method names or structures
                if hasattr(client, 'search'):
                    # Try to find any search-related method
                    for method_name in dir(client.search):
                        if any(term in method_name.lower() for term in ['query', 'search', 'find']):
                            try:
                                method = getattr(client.search, method_name)
                                if callable(method):
                                    search_results = method(**search_params)
                                    break
                            except Exception:
                                continue
                else:
                    # Try to find search functionality in other resources
                    for resource_name in ["videos", "indexes"]:
                        resource = getattr(client, resource_name, None)
                        if resource:
                            for method_name in dir(resource):
                                if any(term in method_name.lower() for term in ['search', 'query', 'find']):
                                    try:
                                        method = getattr(resource, method_name)
                                        if callable(method):
                                            search_results = method(**search_params)
                                            break
                                    except Exception:
                                        continue
            except Exception as e:
                print(f"Error finding search method: {e}")
                return []
                
        # Handle different response structures        
        results = []
        
        # Process results with resilient approach
        try:
            # First try the documented approach - assume search_results has data attribute
            if hasattr(search_results, 'data'):
                results.extend(format_search_results(search_results.data))
                
                # Try to handle pagination if available
                try:
                    while True:
                        try:
                            next_page = next(search_results)
                            results.extend(format_search_results(next_page))
                        except (StopIteration, TypeError):
                            break
                except Exception as e:
                    print(f"Error handling pagination: {e}")
            else:
                # If no data attribute, try other approaches
                if isinstance(search_results, dict):
                    # It might be a direct result dictionary
                    results.extend(format_search_results(search_results))
                elif isinstance(search_results, list):
                    # It might be a direct list of results
                    results.extend(format_search_results({"data": search_results}))
                else:
                    # Try to get any useful attribute
                    for attr in dir(search_results):
                        if attr.lower() in ['results', 'clips', 'videos', 'matches']:
                            attr_value = getattr(search_results, attr)
                            if attr_value:
                                if isinstance(attr_value, list):
                                    results.extend(format_search_results({"data": attr_value}))
                                    break
                                elif isinstance(attr_value, dict):
                                    results.extend(format_search_results(attr_value))
                                    break
        except Exception as e:
            print(f"Error processing search results: {e}")
            
        return results
    except Exception as e:
        print(f"Error searching videos: {e}")
        return []


def search_videos_with_image(
    index_id: str,
    image_file: Optional[str] = None,
    image_url: Optional[str] = None,
    options: List[str] = None,
    group_by: Optional[str] = None,
    threshold: Optional[str] = None,
    page_limit: Optional[int] = 10,
    sort_option: Optional[str] = None,
    client: Optional[TwelveLabs] = None
) -> List[Dict[str, Any]]:
    """Search for video clips using an image query.
    
    Args:
        index_id: ID of the index to search in
        image_file: Path to local image file
        image_url: URL of image to use as query
        options: Search options (e.g., ["visual", "audio"])
        group_by: How to group results ("video" or "clip")
        threshold: Confidence threshold ("high", "medium", "low", "none")
        page_limit: Number of results per page
        sort_option: How to sort results ("score", "clip_count")
        client: Optional TwelveLabs client instance. If not provided, one will be created
        
    Returns:
        List of formatted search results
        
    Raises:
        ValueError: If neither image_file nor image_url is provided
    """
    if not image_file and not image_url:
        raise ValueError("Either image_file or image_url must be provided")
    
    # Default search options if none provided
    if options is None:
        options = ["visual"]
    
    client = client or get_client()
    
    try:
        # Prepare search parameters
        search_params = {
            "index_id": index_id,
            "query_media_type": "image",
            "options": options,
            "page_limit": page_limit
        }
        
        # Add image source
        if image_file:
            search_params["query_media_file"] = image_file
        elif image_url:
            search_params["query_media_url"] = image_url
        
        # Add optional parameters if provided
        if group_by:
            search_params["group_by"] = group_by
        if threshold:
            search_params["threshold"] = threshold
        if sort_option:
            search_params["sort_option"] = sort_option
        
        # Execute search query
        search_results = client.search.query(**search_params)
        
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
        print(f"Error searching videos with image: {e}")
        return []


def format_search_results(result_page) -> List[Dict[str, Any]]:
    """Format the search results for easy consumption.
    
    Args:
        result_page: Page of search results from Twelve Labs API
        
    Returns:
        List of formatted result dictionaries
    """
    formatted_results = []
    
    # Handle different response structures
    if not result_page:
        return []
    
    # Check if result_page is a dictionary with data key
    if isinstance(result_page, dict):
        if "data" in result_page:
            clips = result_page.get("data", [])
        elif "results" in result_page:
            clips = result_page.get("results", [])
        elif "clips" in result_page:
            clips = result_page.get("clips", [])
        else:
            # Just use any available items
            clips = []
            for key, value in result_page.items():
                if isinstance(value, list):
                    clips = value
                    break
            if not clips and len(result_page) > 0:
                # Might be a single result
                clips = [result_page]
    elif isinstance(result_page, list):
        # If it's already a list, use it directly
        clips = result_page
    else:
        # Try to extract a list from the object
        clips = []
        for attr in dir(result_page):
            if attr not in ["__class__", "__dict__", "__module__", "__doc__"]:
                try:
                    value = getattr(result_page, attr)
                    if isinstance(value, list):
                        clips = value
                        break
                except (AttributeError, TypeError):
                    pass
    
    # Process each clip
    for clip in clips:
        # Create a base result dictionary
        result = {}
        
        # Extract data with both attribute and dictionary access
        # for common result fields
        for field in ["video_id", "score", "confidence", "start_time", "start", "end_time", "end"]:
            # Try dictionary access first
            if isinstance(clip, dict) and field in clip:
                result[field] = clip[field]
            # Try attribute access next
            elif hasattr(clip, field):
                result[field] = getattr(clip, field)
                
        # Handle common field name variations
        if "video_id" not in result and "videoId" in result:
            result["video_id"] = result["videoId"]
        if "start_time" not in result and "start" in result:
            result["start_time"] = result["start"]
        if "end_time" not in result and "end" in result:
            result["end_time"] = result["end"]
            
        # Ensure we have at least video_id and start_time
        if "video_id" not in result or "start_time" not in result:
            # Skip incomplete results
            continue
            
        # Add formatted timestamps
        try:
            start_time = result.get("start_time", 0)
            end_time = result.get("end_time", 0)
            result["start_time_formatted"] = format_timestamp(float(start_time))
            result["end_time_formatted"] = format_timestamp(float(end_time))
        except (ValueError, TypeError) as e:
            # Handle cases where timestamps might not be valid
            print(f"Error formatting timestamps: {e}")
            result["start_time_formatted"] = "00:00:00"
            result["end_time_formatted"] = "00:00:00"
        
        # Add thumbnail with resilient approach
        if isinstance(clip, dict):
            # Try dictionary access
            if "thumbnail" in clip and clip["thumbnail"]:
                result["thumbnail"] = clip["thumbnail"]
        else:
            # Try attribute access
            if hasattr(clip, 'thumbnail') and getattr(clip, 'thumbnail'):
                result["thumbnail"] = getattr(clip, 'thumbnail')
            
        # Add text matches with resilient approach
        text_matches = None
        
        # Try multiple field name variations
        for field_name in ['text_matches', 'textMatches', 'text_match', 'textMatch', 'matches']:
            # Try dictionary access
            if isinstance(clip, dict) and field_name in clip and clip[field_name]:
                text_matches = clip[field_name]
                break
            # Try attribute access
            elif hasattr(clip, field_name) and getattr(clip, field_name):
                text_matches = getattr(clip, field_name)
                break
                
        if text_matches:
            result["text_matches"] = text_matches
            
        formatted_results.append(result)
    
    return formatted_results


def format_timestamp(seconds: float) -> str:
    """Format seconds into HH:MM:SS format.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted time string in HH:MM:SS format
    """
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
