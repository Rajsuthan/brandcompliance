# Tool schemas for OpenRouter native tool calling

import json
from typing import Dict, List, Any


def get_tool_schemas() -> List[Dict[str, Any]]:
    """
    Get the list of tool schemas in OpenRouter native format.
    
    Returns:
        List of tool schemas in OpenRouter native format.
    """
    return [
        # --- VIDEO TOOLS ---
        {
            "type": "function",
            "function": {
                "name": "get_video_color_scheme",
                "description": "Get the color scheme of the video frame(s) at the specified timestamp.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timestamp": {
                            "type": "integer",
                            "description": "The timestamp (in seconds) of the video frame to analyze.",
                        },
                        "task_detail": {
                            "type": "string",
                            "description": "A quick title about the task you are doing",
                        },
                    },
                    "required": ["timestamp", "task_detail"],
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_video_fonts",
                "description": "Identify fonts used in the video frame(s) at the specified timestamp.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timestamp": {
                            "type": "integer",
                            "description": "The timestamp (in seconds) of the video frame to analyze.",
                        },
                        "task_detail": {
                            "type": "string",
                            "description": "A quick title about the task you are doing",
                        },
                    },
                    "required": ["timestamp", "task_detail"],
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "check_video_frame_specs",
                "description": "Analyze the video frame specifications at the specified timestamp for compliance with brand guidelines.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timestamp": {
                            "type": "integer",
                            "description": "The timestamp (in seconds) of the video frame to analyze.",
                        },
                        "required_width": {
                            "type": "integer",
                            "description": "Required width in pixels (0 for no requirement)",
                            "minimum": 0,
                        },
                        "required_height": {
                            "type": "integer",
                            "description": "Required height in pixels (0 for no requirement)",
                            "minimum": 0,
                        },
                        "min_resolution": {
                            "type": "integer",
                            "description": "Minimum resolution in DPI (0 for no requirement)",
                            "minimum": 0,
                        },
                        "aspect_ratio": {
                            "type": "string",
                            "description": "Required aspect ratio (e.g., '16:9', '4:3', '1:1', or 'any')",
                        },
                        "task_detail": {
                            "type": "string",
                            "description": "A quick title about the task you are doing",
                        },
                    },
                    "required": ["timestamp", "task_detail"],
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "extract_verbal_content",
                "description": "Extract all verbal content from video (both spoken and displayed text) using OCR.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timestamps": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "List of timestamps (in seconds) to analyze for text.",
                        },
                        "all_frames": {
                            "type": "object",
                            "description": "Dictionary of all frames by timestamp (optional).",
                        },
                        "task_detail": {
                            "type": "string",
                            "description": "A quick title about the task you are doing",
                        },
                    },
                    "required": ["task_detail"],
                }
            }
        },
        # --- GUIDELINES TOOLS ---
        {
            "type": "function",
            "function": {
                "name": "search_brand_guidelines",
                "description": "Search for and retrieve the brand guidelines for a specific brand.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "brand_name": {
                            "type": "string",
                            "description": "The name of the brand to search for guidelines (e.g., 'Nike', 'Coca-Cola').",
                            "minLength": 1,
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query to find specific guidelines (e.g., 'logo usage', 'color palette')",
                            "minLength": 1,
                        },
                        "task_detail": {
                            "type": "string",
                            "description": "A quick title about the task you are doing",
                        },
                    },
                    "required": ["brand_name", "task_detail"],
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_guideline_page",
                "description": "Read a specific page from the brand guidelines to understand detailed requirements.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "brand_name": {
                            "type": "string",
                            "description": "The name of the brand whose guidelines you're reading.",
                            "minLength": 1,
                        },
                        "page_number": {
                            "type": "integer",
                            "description": "The page number of the brand guidelines to read.",
                            "minimum": 1,
                        },
                        "task_detail": {
                            "type": "string",
                            "description": "A quick title about the task you are doing",
                        },
                    },
                    "required": ["brand_name", "page_number", "task_detail"],
                }
            }
        },
        # --- IMAGE ANALYSIS TOOLS ---
        {
            "type": "function",
            "function": {
                "name": "get_region_color_scheme",
                "description": "Get the color scheme of a specific region within the video frame at the specified timestamp.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timestamp": {
                            "type": "integer",
                            "description": "The timestamp (in seconds) of the video frame to analyze.",
                        },
                        "x1": {
                            "type": "integer",
                            "description": "The x-coordinate of the top-left corner of the region.",
                        },
                        "y1": {
                            "type": "integer",
                            "description": "The y-coordinate of the top-left corner of the region.",
                        },
                        "x2": {
                            "type": "integer",
                            "description": "The x-coordinate of the bottom-right corner of the region.",
                        },
                        "y2": {
                            "type": "integer",
                            "description": "The y-coordinate of the bottom-right corner of the region.",
                        },
                        "task_detail": {
                            "type": "string",
                            "description": "A quick title about the task you are doing",
                        },
                    },
                    "required": ["timestamp", "x1", "y1", "x2", "y2", "task_detail"],
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "check_color_contrast",
                "description": "Analyze the video frame at the specified timestamp for color contrast accessibility compliance.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timestamp": {
                            "type": "integer",
                            "description": "The timestamp (in seconds) of the video frame to analyze.",
                        },
                        "foreground_region": {
                            "type": "object",
                            "properties": {
                                "x1": {"type": "integer"},
                                "y1": {"type": "integer"},
                                "x2": {"type": "integer"},
                                "y2": {"type": "integer"},
                            },
                            "description": "Region containing the foreground (text) color.",
                        },
                        "background_region": {
                            "type": "object",
                            "properties": {
                                "x1": {"type": "integer"},
                                "y1": {"type": "integer"},
                                "x2": {"type": "integer"},
                                "y2": {"type": "integer"},
                            },
                            "description": "Region containing the background color.",
                        },
                        "task_detail": {
                            "type": "string",
                            "description": "A quick title about the task you are doing",
                        },
                    },
                    "required": ["timestamp", "foreground_region", "background_region", "task_detail"],
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "check_element_placement",
                "description": "Analyze the placement, spacing, and alignment of elements in the video frame at the specified timestamp.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timestamp": {
                            "type": "integer",
                            "description": "The timestamp (in seconds) of the video frame to analyze.",
                        },
                        "primary_element_coordinates": {
                            "type": "string",
                            "description": "Coordinates of the primary element (e.g., logo) in format 'x1,y1,x2,y2'.",
                        },
                        "secondary_elements_coordinates": {
                            "type": "string",
                            "description": "Comma-separated list of secondary element coordinates.",
                        },
                        "safe_zone_percentage": {
                            "type": "string",
                            "description": "Safe zone boundaries as percentages in format 'top,right,bottom,left'.",
                        },
                        "min_spacing": {
                            "type": "integer",
                            "description": "Minimum spacing required between elements in pixels.",
                        },
                        "task_detail": {
                            "type": "string",
                            "description": "A quick title about the task you are doing",
                        },
                    },
                    "required": ["timestamp", "primary_element_coordinates", "task_detail"],
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "check_image_clarity",
                "description": "Analyze the clarity and quality of brand elements in the video frame at the specified timestamp to detect blurring, pixelation, or other forms of degradation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timestamp": {
                            "type": "integer",
                            "description": "The timestamp (in seconds) of the video frame to analyze.",
                        },
                        "region_coordinates": {
                            "type": "string",
                            "description": "Coordinates of the region to analyze in format 'x1,y1,x2,y2'.",
                        },
                        "element_type": {
                            "type": "string",
                            "description": "Type of brand element being analyzed (e.g., 'logo', 'text', 'icon').",
                        },
                        "min_clarity_score": {
                            "type": "integer",
                            "description": "Minimum acceptable clarity score (0-100, default: 80).",
                            "minimum": 0,
                            "maximum": 100,
                        },
                        "task_detail": {
                            "type": "string",
                            "description": "A quick title about the task you are doing",
                        },
                    },
                    "required": ["timestamp", "region_coordinates", "element_type", "task_detail"],
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "check_layout_consistency",
                "description": "Analyze the layout consistency of a video frame against a grid system or template.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timestamp": {
                            "type": "integer",
                            "description": "The timestamp (in seconds) of the video frame to analyze.",
                        },
                        "grid_type": {
                            "type": "string",
                            "description": "Type of grid system to check against (e.g., 'rule_of_thirds', 'golden_ratio', 'custom').",
                        },
                        "grid_columns": {
                            "type": "integer",
                            "description": "Number of columns in the grid (for custom grids).",
                        },
                        "grid_rows": {
                            "type": "integer",
                            "description": "Number of rows in the grid (for custom grids).",
                        },
                        "key_points": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of key points to check against the grid (format: 'element:x,y').",
                        },
                        "template_sections": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of template section definitions (format: 'section_name:x1,y1,x2,y2').",
                        },
                        "task_detail": {
                            "type": "string",
                            "description": "A quick title about the task you are doing",
                        },
                    },
                    "required": ["timestamp", "task_detail"],
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "check_text_grammar",
                "description": "Analyze text for grammar, spelling, and brand voice compliance.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The text to analyze for grammar and spelling.",
                        },
                        "brand_voice_guidelines": {
                            "type": "string",
                            "description": "Brand voice guidelines to check compliance against.",
                        },
                        "language": {
                            "type": "string",
                            "description": "Language of the text (default: 'en-US').",
                        },
                        "task_detail": {
                            "type": "string",
                            "description": "A quick title about the task you are doing",
                        },
                    },
                    "required": ["text", "task_detail"],
                }
            }
        },
        # --- COMPLETION TOOL ---
        {
            "type": "function",
            "function": {
                "name": "attempt_completion",
                "description": "Summarize key compliance findings for final processing. Do NOT include a detailed analysis here - just provide key points which will be transformed into a full report.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "compliance_summary": {
                            "type": "string",
                            "description": "Short bullet points of key compliance findings (color scheme, logo, typography, etc.) - keep this concise!",
                        },
                        "compliance_status": {
                            "type": "string",
                            "description": "Overall compliance status: 'compliant', 'partially_compliant', or 'non_compliant'",
                            "enum": ["compliant", "partially_compliant", "non_compliant"]
                        },
                        "task_detail": {
                            "type": "string",
                            "description": "A quick title about the task you are doing",
                        },
                    },
                    "required": ["compliance_summary", "compliance_status", "task_detail"],
                }
            }
        }
    ]


def print_tool_schema_json():
    """
    Print the tool schemas as formatted JSON for easy inspection or export.
    """
    schemas = get_tool_schemas()
    print(json.dumps(schemas, indent=2))


if __name__ == "__main__":
    print_tool_schema_json()
