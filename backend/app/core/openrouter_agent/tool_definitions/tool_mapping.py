# Tool mappings for OpenRouter native tool calling

from typing import Dict, Any, Callable, Awaitable, Optional
import asyncio

# Import tool implementations
from app.core.agent.tools import (
    get_video_color_scheme as _get_video_color_scheme,
    get_video_fonts as _get_video_fonts,
    check_video_frame_specs as _check_video_frame_specs,
    extract_verbal_content as _extract_verbal_content,
    get_brand_guidelines as _search_brand_guidelines,
    read_guideline_page as _read_guideline_page,
    get_region_color_scheme as _get_region_color_scheme,
    check_color_contrast as _check_color_contrast,
    check_element_placement as _check_element_placement,
    check_layout_consistency as _check_layout_consistency,
    check_image_clarity as _check_image_clarity,
    check_text_grammar as _check_text_grammar,
    attempt_completion as _attempt_completion,
)
# Import the video search tool
from app.core.openrouter_agent.tools.search_video import search_video as _search_video


async def execute_tool(tool_name: str, tool_args: Dict[str, Any]) -> Any:
    """
    Execute a tool by name with the provided arguments.

    Args:
        tool_name: The name of the tool to execute.
        tool_args: Arguments to pass to the tool.

    Returns:
        The tool execution result.

    Raises:
        ValueError: If the tool does not exist.
    """
    # Add more debugging information
    print(f"\033[93m[DEBUG] execute_tool called for {tool_name}\033[0m")
    print(f"\033[93m[DEBUG] tool_args keys: {list(tool_args.keys())}\033[0m")

    # For video tools, check if images_base64 is present
    video_tools = {"get_video_color_scheme", "get_video_fonts", "check_video_frame_specs", "extract_verbal_content"}
    if tool_name in video_tools:
        if "images_base64" in tool_args:
            print(f"\033[92m[INFO] Tool {tool_name} has images_base64 with {len(tool_args['images_base64'])} items\033[0m")
        else:
            print(f"\033[91m[ERROR] Tool {tool_name} is missing images_base64\033[0m")

    tool_func = TOOL_MAPPING.get(tool_name)
    if not tool_func:
        raise ValueError(f"Tool '{tool_name}' not found in the tool mapping.")

    # Check if the tool function is async
    if asyncio.iscoroutinefunction(tool_func):
        result = await tool_func(tool_args)
    else:
        result = tool_func(tool_args)

    return result


# Map tool names to their implementation functions
TOOL_MAPPING: Dict[str, Callable[[Dict[str, Any]], Any]] = {
    # Video tools
    "get_video_color_scheme": _get_video_color_scheme,
    "get_video_fonts": _get_video_fonts,
    "check_video_frame_specs": _check_video_frame_specs,
    "extract_verbal_content": _extract_verbal_content,
    "search_video": _search_video,  # New Twelve Labs video search tool

    # Guidelines tools
    "search_brand_guidelines": _search_brand_guidelines,
    "read_guideline_page": _read_guideline_page,

    # Image analysis tools
    "get_region_color_scheme": _get_region_color_scheme,
    "check_color_contrast": _check_color_contrast,
    "check_element_placement": _check_element_placement,
    "check_layout_consistency": _check_layout_consistency,
    "check_image_clarity": _check_image_clarity,
    "check_text_grammar": _check_text_grammar,

    # Completion tool
    "attempt_completion": _attempt_completion,
}


def get_tool_function(tool_name: str) -> Optional[Callable[[Dict[str, Any]], Any]]:
    """
    Get the tool function by name.

    Args:
        tool_name: The name of the tool to get.

    Returns:
        The tool function, or None if not found.
    """
    return TOOL_MAPPING.get(tool_name)
