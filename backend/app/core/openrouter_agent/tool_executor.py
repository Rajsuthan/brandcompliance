import json
import datetime
import logging
from typing import Dict, Any, List, Optional

from app.core.openrouter_agent.tool_definitions import execute_tool
from app.core.openrouter_agent.tool_cache import tool_cache
from app.core.openrouter_agent.redis import get_cached_image, cache_tool_result

logger = logging.getLogger(__name__)

async def execute_and_process_tool(
    tool_name: str,
    tool_args: Dict[str, Any],
    image_base64: str = None,
    frames: List[Dict[str, Any]] = None,
    tool_call_id: Optional[str] = None,
    on_stream = None,
    video_url: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    # Sanitize the tool_call_id to prevent token explosion
    # If it's too long, truncate or hash it
    MAX_TOOL_CALL_ID_LENGTH = 64  # Reasonable length for an ID
    if tool_call_id and len(str(tool_call_id)) > MAX_TOOL_CALL_ID_LENGTH:
        import hashlib
        # Hash the ID and use a prefix to identify it's been hashed
        hashed_id = hashlib.md5(str(tool_call_id).encode()).hexdigest()
        tool_call_id = f"hashed_{hashed_id}"
        print(f"\033[93m[WARNING] tool_call_id was too long, replaced with hash: {tool_call_id}\033[0m")
    """Execute a tool and prepare results for the agent response.

    Args:
        tool_name: The name of the tool to execute
        tool_args: Arguments to pass to the tool
        tool_call_id: Optional ID of the tool call (for OpenAI compatibility)
        on_stream: Optional streaming callback function

    Returns:
        A dictionary with the tool execution results and metadata
    """
    try:
        # Log input sizes
        tool_args_str = str(tool_args)
        print(f"\033[92m[TOOL EXEC] Executing {tool_name}...\033[0m")
        print(f"\033[92m[TOOL INPUT SIZE] {tool_name}: {len(tool_args_str)} chars\033[0m")
        
        # For video search tool, ensure video_url and user_id are passed
        if tool_name == "search_video" and video_url and user_id:
            # Add video_url and user_id to the tool arguments
            tool_args["video_url"] = video_url
            tool_args["user_id"] = user_id
            print(f"\033[92m[TOOL EXEC] Adding video_url and user_id to search_video tool\033[0m")

        # Log all keys in tool_args
        if isinstance(tool_args, dict):
            print(f"\033[93m[DEBUG] {tool_name} received keys: {list(tool_args.keys())}\033[0m")

            # Log values for non-image keys
            for key, value in tool_args.items():
                if key not in ["image_base64", "images_base64"]:
                    print(f"\033[93m[DEBUG] {key}: {value}\033[0m")

            # For image input, show the length but not the content
            if "image_base64" in tool_args and tool_args["image_base64"]:
                img_len = len(tool_args["image_base64"])
                print(f"\033[92m[IMAGE SIZE] image_base64 in {tool_name}: {img_len} chars\033[0m")
                print(f"\033[93m[DEBUG] image_base64 (first 20 chars): {tool_args['image_base64'][:20]}...\033[0m")
            else:
                print(f"\033[93m[DEBUG] No image_base64 found in {tool_name}\033[0m")

            # For images_base64 array, show the length and count
            if "images_base64" in tool_args and tool_args["images_base64"]:
                if isinstance(tool_args["images_base64"], list):
                    img_count = len(tool_args["images_base64"])
                    total_len = sum(len(img) for img in tool_args["images_base64"] if isinstance(img, str))
                    print(f"\033[92m[IMAGE SIZE] images_base64 in {tool_name}: {img_count} images, total {total_len} chars\033[0m")

                    # Log the first few characters of the first image
                    if img_count > 0 and isinstance(tool_args["images_base64"][0], str):
                        first_img = tool_args["images_base64"][0]
                        print(f"\033[93m[DEBUG] First image in images_base64 (first 20 chars): {first_img[:20]}...\033[0m")
                else:
                    print(f"\033[91m[ERROR] images_base64 in {tool_name} is not a list: {type(tool_args['images_base64'])}\033[0m")
            else:
                print(f"\033[93m[DEBUG] No images_base64 found in {tool_name}\033[0m")

            # CRITICAL: Check if this is a video tool and ensure frames are added
            video_tools = {
                "get_video_color_scheme",
                "get_video_fonts",
                "check_video_frame_specs",
                "extract_verbal_content",
                "get_region_color_scheme",
                "check_color_contrast",
                "check_element_placement",
                "check_image_clarity",
                "check_text_grammar",
            }

            if tool_name in video_tools:
                has_images_base64 = "images_base64" in tool_args and tool_args["images_base64"]
                has_image_base64 = "image_base64" in tool_args and tool_args["image_base64"]

                print(f"\033[93m[DEBUG] Video tool check - has_images_base64: {has_images_base64}, has_image_base64: {has_image_base64}\033[0m")

                # If neither is present but we have frames, add them
                if not (has_images_base64 or has_image_base64) and frames and len(frames) > 0:
                    print(f"\033[91m[ERROR] {tool_name} is missing both images_base64 and image_base64. Adding frames now.\033[0m")

                    # For extract_verbal_content, add frames for timestamps
                    if tool_name == "extract_verbal_content":
                        # Get timestamps or use defaults
                        timestamps = tool_args.get("timestamps", [5, 10, 15])

                        # Add timestamps to tool_args if not present
                        if "timestamps" not in tool_args:
                            tool_args["timestamps"] = timestamps
                            print(f"\033[92m[INFO] Added default timestamps to extract_verbal_content: {timestamps}\033[0m")

                        # For each timestamp, find the closest frame
                        images_base64 = []
                        for ts in timestamps:
                            closest_frame = min(frames, key=lambda f: abs(f.get("timestamp", 0) - float(ts)))
                            frame_base64 = closest_frame.get("image_data") or closest_frame.get("base64")
                            if frame_base64:
                                images_base64.append(frame_base64)

                        if images_base64:
                            print(f"\033[92m[INFO] TOOL EXECUTOR - Adding {len(images_base64)} frames to images_base64 for extract_verbal_content\033[0m")
                            tool_args["images_base64"] = images_base64
                            tool_args["image_base64"] = images_base64[0]  # Add first frame as image_base64

                    # For other video tools with timestamp
                    elif "timestamp" in tool_args:
                        target_ts = tool_args["timestamp"]
                        print(f"\033[93m[DEBUG] TOOL EXECUTOR - Looking for timestamp: {target_ts}\033[0m")

                        # Find the closest frame
                        closest_frame = min(frames, key=lambda f: abs(f.get("timestamp", 0) - float(target_ts)))
                        frame_base64 = closest_frame.get("image_data") or closest_frame.get("base64")

                        if frame_base64:
                            print(f"\033[92m[INFO] TOOL EXECUTOR - Adding closest frame to image_base64 and images_base64\033[0m")
                            tool_args["image_base64"] = frame_base64
                            tool_args["images_base64"] = [frame_base64]

                    # For other video tools without timestamp
                    else:
                        # Add all frames
                        images_base64 = []
                        for frame in frames:
                            frame_data = frame.get("image_data") or frame.get("base64")
                            if frame_data:
                                images_base64.append(frame_data)

                        if images_base64:
                            print(f"\033[92m[INFO] TOOL EXECUTOR - Adding all {len(images_base64)} frames\033[0m")
                            tool_args["images_base64"] = images_base64
                            tool_args["image_base64"] = images_base64[0]

        # Check if we have a cached result for this tool call
        cached_result = tool_cache.get(tool_name, tool_args)
        if cached_result is not None:
            tool_result = cached_result
            print(f"\033[92m[CACHE HIT] Using cached result for {tool_name}\033[0m")
        else:
            # Check if we have a cached base64 image for this tool call
            cached_base64 = await get_cached_image(tool_name, tool_args)

            if cached_base64 is not None:
                print(f"\033[92m[REDIS CACHE] 👍 IMAGE CACHE HIT for {tool_name} - Using cached base64 image ({len(cached_base64) // 1024}KB)\033[0m")

                # Execute the tool to get the basic result structure
                tool_result = await execute_tool(tool_name, tool_args)

                # If the result is a string (JSON), parse it
                if isinstance(tool_result, str):
                    try:
                        result_dict = json.loads(tool_result)
                        # Replace the base64 field with our cached version
                        if isinstance(result_dict, dict) and "base64" in result_dict:
                            result_dict["base64"] = cached_base64
                            tool_result = json.dumps(result_dict)
                            print(f"\033[92m[REDIS CACHE] 🔄 Replaced base64 in result with cached version ({len(cached_base64) // 1024}KB)\033[0m")
                    except json.JSONDecodeError:
                        # If we can't parse the result, just use it as is
                        pass
            else:
                # Execute the tool and cache the result
                tool_result = await execute_tool(tool_name, tool_args)

                # Cache the base64 image if present in the result
                await cache_tool_result(tool_name, tool_args, tool_result)

            # Cache the full tool result
            tool_cache.set(tool_name, tool_args, tool_result)

        # Log output sizes
        tool_result_str = str(tool_result)
        print(f"\033[95m[TOOL OUTPUT SIZE] {tool_name}: {len(tool_result_str)} chars\033[0m")

        trunc_tool_result = tool_result_str[:300] + ("...[[TRUNCATED]]" if len(tool_result_str) > 300 else "")
        print(f"\033[95m[TOOL RESULT] {tool_name}: {trunc_tool_result}\033[0m")
    except Exception as e:
        print(f"\033[91m[ERROR] Exception in {tool_name}: {e}\033[0m")
        tool_result = {"error": str(e)}
        trunc_tool_result = str(tool_result)

    # Create the result record for the tool trace
    trace_record = {
        "timestamp": datetime.datetime.now().isoformat(),
        "tool_name": tool_name,
        "tool_input": tool_args,
        "truncated_result": trunc_tool_result,
        "full_result": tool_result if tool_name == "attempt_completion" else None,
        "cached": cached_result is not None  # Track if result was from cache
    }

    # Stream tool result to the client if needed
    if on_stream:
        # Remove image_base64 and images_base64 from tool_input before sending
        filtered_tool_args = dict(tool_args) if isinstance(tool_args, dict) else tool_args
        if isinstance(filtered_tool_args, dict):
            filtered_tool_args.pop("image_base64", None)
            filtered_tool_args.pop("images_base64", None)

        await on_stream({
            "type": "tool",
            "tool_name": tool_name,
            "content": json.dumps({
                "tool_name": tool_name,
                "tool_input": filtered_tool_args,
                "tool_result": tool_result
            })
        })

    # Prepare a SIMPLIFIED message format for OpenAI compatibility
    # Only include a summarized version of the tool result to prevent token explosion
    # Maximum length for tool result in the message format
    MAX_TOOL_RESULT_LENGTH = 5000  # Reasonable limit to prevent explosion

    # If the tool result is too long, truncate it drastically
    tool_result_str = str(tool_result)
    if len(tool_result_str) > MAX_TOOL_RESULT_LENGTH:
        print(f"\033[91m[WARNING] Tool result too large ({len(tool_result_str)} chars), truncating to {MAX_TOOL_RESULT_LENGTH}\033[0m")
        # For JSON results, try to preserve structure by truncating internal content
        if tool_result_str.startswith('{') and tool_result_str.endswith('}'):
            try:
                # Parse the JSON and truncate large string values - use the already imported json
                # (don't reimport within the function)
                result_obj = json.loads(tool_result_str)
                # Helper function to truncate nested object values
                def truncate_values(obj, max_len=1000):
                    if isinstance(obj, dict):
                        return {k: truncate_values(v, max_len) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [truncate_values(item, max_len) for item in obj[:5]] + (["...truncated..."] if len(obj) > 5 else [])
                    elif isinstance(obj, str) and len(obj) > max_len:
                        return obj[:max_len] + "...truncated..."
                    else:
                        return obj

                # Truncate the object
                truncated_obj = truncate_values(result_obj)
                truncated_result = json.dumps(truncated_obj)
                # Final safety check
                if len(truncated_result) > MAX_TOOL_RESULT_LENGTH:
                    truncated_result = truncated_result[:MAX_TOOL_RESULT_LENGTH] + "...truncated..."
            except:
                # Fallback to simple truncation if JSON parsing fails
                truncated_result = tool_result_str[:MAX_TOOL_RESULT_LENGTH] + "...truncated..."
        else:
            # Simple truncation for non-JSON results
            truncated_result = tool_result_str[:MAX_TOOL_RESULT_LENGTH] + "...truncated..."
    else:
        truncated_result = tool_result_str

    # Create the simplified message format
    message_format = {
        "tool_call_id": tool_call_id,
        "name": tool_name,
        "content": truncated_result
    }

    # Log the size of all components for debugging
    tool_call_id_len = len(str(tool_call_id)) if tool_call_id else 0
    print(f"\033[93m[DEBUG] tool_call_id length: {tool_call_id_len} chars\033[0m")
    print(f"\033[93m[DEBUG] Original tool result length: {len(tool_result_str)} chars\033[0m")
    print(f"\033[93m[DEBUG] Truncated result length: {len(truncated_result)} chars\033[0m")
    print(f"\033[93m[DEBUG] Final message format length: {len(str(message_format))} chars\033[0m")

    # Return the tool result in the proper OpenAI/OpenRouter compatible format
    return message_format

# Function to get cache statistics for monitoring
def get_cache_stats():
    """Get current cache statistics.

    Returns:
        Dictionary with cache hit/miss statistics
    """
    return tool_cache.get_stats()

# Function to clear the cache
def clear_cache(tool_name=None):
    """Clear the tool result cache.

    Args:
        tool_name: Optional tool name to clear cache for specific tool only
    """
    tool_cache.clear(tool_name)
