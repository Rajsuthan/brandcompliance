from typing import Dict, Any, List, Optional

def inject_image_data(
    tool_name: str,
    tool_args: Dict[str, Any],
    image_base64: Optional[str] = None,
    frames: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Inject image or video frame data into tool arguments before execution.

    Args:
        tool_name: The name of the tool to execute
        tool_args: Arguments to pass to the tool
        image_base64: Optional base64-encoded image
        frames: Optional list of video frames with timestamps

    Returns:
        Updated tool arguments dictionary with injected image data
    """
    # Return early if no image data to inject or tool_args isn't a dict
    if not isinstance(tool_args, dict) or (not image_base64 and not frames):
        return tool_args

    # These tools expect images_base64 (array format)
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

    # Handle timestamp-based image injection for video tools
    if tool_name in video_tools and frames:
        print(f"\033[93m[DEBUG] Processing video tool: {tool_name} with {len(frames)} frames\033[0m")
        print(f"\033[93m[DEBUG] Tool args keys: {list(tool_args.keys())}\033[0m")

        # Log the first frame's keys to understand its structure
        if frames and len(frames) > 0:
            print(f"\033[93m[DEBUG] First frame keys: {list(frames[0].keys())}\033[0m")
            for key in frames[0].keys():
                value = frames[0][key]
                if key in ["base64", "image_data"]:
                    print(f"\033[93m[DEBUG] First frame {key} length: {len(str(value))}\033[0m")
                else:
                    print(f"\033[93m[DEBUG] First frame {key}: {value}\033[0m")

        # If images_base64 is already in tool_args, don't override it
        if "images_base64" in tool_args and tool_args["images_base64"]:
            print(f"\033[92m[INFO] Tool args already has images_base64 with {len(tool_args['images_base64'])} items, not overriding\033[0m")
            return tool_args

        ts = tool_args.get("timestamp")
        if ts is not None:
            print(f"\033[93m[DEBUG] Looking for timestamp: {ts}\033[0m")
            try:
                ts_int = int(ts)
                # Find the closest frame
                frame = None
                min_diff = float("inf")
                for f in frames:
                    frame_ts = int(f.get("timestamp", -1))
                    diff = abs(frame_ts - ts_int)
                    if diff < min_diff:
                        min_diff = diff
                        frame = f

                print(f"\033[93m[DEBUG] Found closest frame at timestamp: {frame.get('timestamp') if frame else 'None'}\033[0m")

                # Get the base64 data from either key
                frame_base64 = None
                if frame:
                    print(f"\033[93m[DEBUG] Frame keys: {list(frame.keys())}\033[0m")
                    has_image_data = "image_data" in frame
                    has_base64 = "base64" in frame
                    print(f"\033[93m[DEBUG] Frame has image_data: {has_image_data}, has base64: {has_base64}\033[0m")

                    frame_base64 = frame.get("image_data") or frame.get("base64")
                    if frame_base64:
                        print(f"\033[93m[DEBUG] Got frame_base64 with length: {len(frame_base64)}\033[0m")
                    else:
                        print(f"\033[91m[ERROR] Could not get base64 data from frame\033[0m")

                if frame_base64:
                    # Video tools expect images_base64 as an array
                    tool_args["images_base64"] = [frame_base64]
                    print(f"\033[92m[LOG] Added frame at timestamp {ts} as images_base64 array\033[0m")

                    # Also add as image_base64 for backward compatibility
                    tool_args["image_base64"] = frame_base64
                    print(f"\033[92m[LOG] Also added as image_base64 for backward compatibility\033[0m")

                    # Get all frames within 1 second of the target timestamp
                    nearby_frames = [
                        f for f in frames
                        if abs(f.get("timestamp", 0) - float(ts)) <= 1
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
            except Exception as e:
                print(f"\033[91m[ERROR] Could not extract frame for timestamp {ts}: {e}\033[0m")
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
    # For video tools, add as images_base64 array if no timestamp
    elif tool_name in video_tools:
        tool_args["images_base64"] = [image_base64] if image_base64 else []
        print(f"\033[92m[LOG] Added image as images_base64 array for video tool {tool_name}\033[0m")
    # For other tools, add as image_base64
    else:
        tool_args["image_base64"] = image_base64
        print(f"\033[92m[LOG] Added image as image_base64 for tool {tool_name}\033[0m")

    return tool_args
