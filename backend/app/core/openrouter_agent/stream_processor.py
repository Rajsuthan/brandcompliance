import time
import json
import asyncio
from typing import List, Dict, Any, Optional, Callable, Awaitable, Tuple
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

# Import the tool execution and media handling functions directly
from app.core.openrouter_agent.tool_executor import execute_tool
from app.core.openrouter_agent.media_handler import inject_image_data

async def process_completion_chunks(
    completion_stream,
    message_handler,
    on_update_time: Callable[[float], None],
) -> Tuple[str, List[Dict[str, Any]], bool]:
    """Process streaming chunks from OpenRouter API response.

    Args:
        completion_stream: AsyncIterator of completion chunks from OpenAI SDK
        message_handler: MessageHandler instance for handling messages
        on_update_time: Callback to update last response time

    Returns:
        Tuple of (content string, tool calls list, is_tool_call flag)
    """
    # Initialize accumulators
    current_content = ""
    current_tool_calls = []
    is_tool_call = False

    # Process each chunk
    async for chunk in completion_stream:
        # Update last response time
        on_update_time(time.time())

        # We'll implement usage tracking later when OpenRouter's API supports it properly

        # Track chunk counts for debugging purposes
        if 'chunk_count' not in globals():
            globals()['chunk_count'] = 0
        globals()['chunk_count'] += 1

        # Print every 50th chunk just as a heartbeat
        if globals()['chunk_count'] % 50 == 0:
            print(f"\033[96m[INFO] Processed {globals()['chunk_count']} chunks\033[0m")

        # Extract content delta if present
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            content_delta = chunk.choices[0].delta.content
            current_content += content_delta

            # Stream content delta to the client
            await message_handler.stream_content(content_delta)

        # Process tool call delta if present
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.tool_calls:
            is_tool_call = True
            for tool_call_delta in chunk.choices[0].delta.tool_calls:
                # Find or create the corresponding tool call in our accumulator
                tool_call = None
                if tool_call_delta.index is not None:
                    # Find existing tool call with same index
                    for tc in current_tool_calls:
                        if tc.get("index") == tool_call_delta.index:
                            tool_call = tc
                            break

                    # Create new tool call if not found
                    if not tool_call:
                        tool_call = {
                            "index": tool_call_delta.index,
                            "id": tool_call_delta.id or "",
                            "type": "function",
                            "function": {
                                "name": "",
                                "arguments": ""
                            }
                        }
                        current_tool_calls.append(tool_call)

                # Update tool call with delta information
                if tool_call_delta.function:
                    if tool_call_delta.function.name:
                        tool_call["function"]["name"] = tool_call_delta.function.name
                    if tool_call_delta.function.arguments:
                        tool_call["function"]["arguments"] += tool_call_delta.function.arguments

    return current_content, current_tool_calls, is_tool_call


def extract_tool_call_from_response(
    response_content: str,
    response_tool_calls: Optional[List[Dict[str, Any]]] = None
) -> Optional[Dict[str, Any]]:
    """Extract tool call information from a response.

    Args:
        response_content: Text content from the response
        response_tool_calls: Tool calls from the response, if available

    Returns:
        Extracted tool call or None if no tool call found
    """
    if response_tool_calls:
        # If tool_calls is available directly, use the first one
        if response_tool_calls and len(response_tool_calls) > 0:
            first_tool_call = response_tool_calls[0]

            if (
                "function" in first_tool_call and
                "name" in first_tool_call["function"] and
                "arguments" in first_tool_call["function"]
            ):
                try:
                    # Parse the arguments as JSON
                    args_str = first_tool_call["function"]["arguments"]
                    return {
                        "name": first_tool_call["function"]["name"],
                        "arguments": json.loads(args_str) if args_str else {}
                    }
                except json.JSONDecodeError:
                    print(f"\033[91m[ERROR] Failed to parse tool arguments: {first_tool_call['function']['arguments']}\033[0m")
                    return {
                        "name": first_tool_call["function"]["name"],
                        "arguments": {}
                    }

    # If no tool call was found or args couldn't be parsed
    return None


async def stream_tool_execution(
    tool_name: str,
    tool_args: Dict[str, Any],
    message_handler,
    tool_trace: List[Dict[str, Any]],
    image_base64: str = None,
    frames: List[Dict[str, Any]] = None,
) -> Any:
    """Execute a tool and stream its result.

    Args:
        tool_name: Name of the tool to execute
        tool_args: Arguments for the tool
        message_handler: Message handler instance
        tool_trace: List to track tool execution history
        image_base64: Optional base64-encoded image
        frames: Optional list of video frames with timestamps

    Returns:
        Result of tool execution
    """
    # Clean the arguments for streaming and messaging (without image data)
    # This prevents sending huge base64 strings back in messages and conserves tokens
    clean_args = {k: v for k, v in tool_args.items() if k not in ["image_base64", "images_base64"]}

    # Log the image data presence for debugging
    if "image_base64" in tool_args and tool_args["image_base64"]:
        print(f"[LOG] Tool {tool_name} has image_base64 data: {len(tool_args['image_base64'][:100])}... ({len(tool_args['image_base64'])} chars total)")
    if "images_base64" in tool_args and tool_args["images_base64"]:
        print(f"[LOG] Tool {tool_name} has images_base64 data with {len(tool_args['images_base64'])} items")

    # Add debugging for frames
    if frames:
        print(f"\033[93m[DEBUG] stream_tool_execution received {len(frames)} frames for {tool_name}\033[0m")
        if len(frames) > 0:
            print(f"\033[93m[DEBUG] First frame keys: {list(frames[0].keys())}\033[0m")
    else:
        print(f"\033[93m[DEBUG] stream_tool_execution received NO frames for {tool_name}\033[0m")

    # For video tools, directly add frames to tool_args before calling inject_image_data
    video_tools = ["get_video_color_scheme", "check_video_frame_specs", "get_video_fonts", "extract_verbal_content"]
    if tool_name in video_tools and frames and len(frames) > 0:
        print(f"\033[92m[INFO] Directly adding frames to {tool_name} arguments\033[0m")

        # Find the frame with the closest timestamp if timestamp is provided
        if "timestamp" in tool_args and tool_args["timestamp"]:
            target_ts = tool_args["timestamp"]
            print(f"\033[93m[DEBUG] Looking for timestamp: {target_ts}\033[0m")

            # Find the closest frame
            closest_frame = min(frames, key=lambda f: abs(f.get("timestamp", 0) - float(target_ts)))
            print(f"\033[93m[DEBUG] Found closest frame at timestamp: {closest_frame.get('timestamp')}\033[0m")

            # Get the base64 data from either key
            frame_base64 = closest_frame.get("image_data") or closest_frame.get("base64")
            if frame_base64:
                print(f"\033[92m[INFO] Adding closest frame as image_base64 (length: {len(frame_base64)})\033[0m")
                tool_args["image_base64"] = frame_base64

                # Always add at least the closest frame to images_base64
                tool_args["images_base64"] = [frame_base64]
                print(f"\033[92m[INFO] Added closest frame to images_base64 array\033[0m")

                # Get all frames within 1 second of the target timestamp
                nearby_frames = [
                    f for f in frames
                    if abs(f.get("timestamp", 0) - float(target_ts)) <= 1
                ]

                # Extract base64 data from each frame
                images_base64 = []
                for frame in nearby_frames:
                    frame_data = frame.get("image_data") or frame.get("base64")
                    if frame_data:
                        images_base64.append(frame_data)

                if images_base64:
                    print(f"\033[92m[INFO] Adding {len(images_base64)} nearby frames as images_base64\033[0m")
                    tool_args["images_base64"] = images_base64
        else:
            # If no timestamp, add all frames
            images_base64 = []
            for frame in frames:
                frame_data = frame.get("image_data") or frame.get("base64")
                if frame_data:
                    images_base64.append(frame_data)

            if images_base64:
                print(f"\033[92m[INFO] Adding all {len(images_base64)} frames as images_base64\033[0m")
                tool_args["images_base64"] = images_base64
                if len(images_base64) > 0:
                    tool_args["image_base64"] = images_base64[0]  # Add first frame as image_base64

        # Debug log to verify frames are being added
        if "images_base64" in tool_args:
            print(f"\033[92m[DEBUG] Final tool_args has images_base64 with {len(tool_args['images_base64'])} items\033[0m")
        else:
            print(f"\033[91m[ERROR] Final tool_args is missing images_base64\033[0m")

    # Inject media data if needed (as a backup)
    tool_args_with_media = inject_image_data(tool_name, tool_args, image_base64, frames)

    # Log the final tool arguments
    if "image_base64" in tool_args_with_media:
        print(f"\033[92m[INFO] Final tool_args has image_base64 with length: {len(tool_args_with_media['image_base64'])}\033[0m")
    if "images_base64" in tool_args_with_media:
        print(f"\033[92m[INFO] Final tool_args has images_base64 with {len(tool_args_with_media['images_base64'])} items\033[0m")

    # Stream that we're executing the tool
    execution_message = f"Executing tool: {tool_name}..."
    await message_handler.stream_content(execution_message)

    # Execute the tool
    start_time = time.time()
    tool_result = await execute_tool(tool_name, tool_args_with_media)
    execution_time = time.time() - start_time

    # Stream the tool result
    await message_handler.stream_tool_result(tool_name, clean_args, tool_result)

    # Add to tool trace
    tool_trace.append({
        "tool": tool_name,
        "input": clean_args,
        "output": tool_result,
        "execution_time": execution_time
    })

    return tool_result
