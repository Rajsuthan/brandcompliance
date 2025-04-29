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
        ts = tool_args.get("timestamp")
        if ts is not None:
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
                if frame and "base64" in frame:
                    # Video tools expect images_base64 as an array
                    tool_args["images_base64"] = [frame["base64"]]
                    print(f"\033[92m[LOG] Added frame at timestamp {ts} as images_base64 array\033[0m")
            except Exception as e:
                print(f"\033[91m[ERROR] Could not extract frame for timestamp {ts}: {e}\033[0m")
    # For video tools, add as images_base64 array if no timestamp
    elif tool_name in video_tools:
        tool_args["images_base64"] = [image_base64] if image_base64 else []
        print(f"\033[92m[LOG] Added image as images_base64 array for video tool {tool_name}\033[0m")
    # For other tools, add as image_base64
    else:
        tool_args["image_base64"] = image_base64
        print(f"\033[92m[LOG] Added image as image_base64 for tool {tool_name}\033[0m")
    
    return tool_args
