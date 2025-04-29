# input schema of tools passing to claude

claude_tools = [
    # --- VIDEO TOOLS ---
    {
        "name": "get_video_color_scheme",
        "description": "Get the color scheme of the video frame(s) at the specified timestamp.",
        "input_schema": {
            "type": "object",
            "properties": {
                "timestamp": {
                    "type": "integer",
                    "description": "The timestamp (in seconds) of the video frame to analyze.",
                },
                "images_base64": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of base64-encoded video frames (optional, for multi-frame analysis).",
                },
                "image_base64": {
                    "type": "string",
                    "description": "Base64-encoded image of the video frame (for single frame analysis).",
                },
                "tool_name": {
                    "type": "string",
                    "description": "The exact name of this tool that you are using",
                    "enum": ["get_video_color_scheme"],
                },
                "task_detail": {
                    "type": "string",
                    "description": "A quick title about the task you are doing",
                },
            },
            "required": ["timestamp", "tool_name", "task_detail"],
            "additionalProperties": True,
        },
    },
    {
        "name": "get_video_fonts",
        "description": "Identify fonts used in the video frame(s) at the specified timestamp.",
        "input_schema": {
            "type": "object",
            "properties": {
                "timestamp": {
                    "type": "integer",
                    "description": "The timestamp (in seconds) of the video frame to analyze.",
                },
                "images_base64": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of base64-encoded video frames (optional, for multi-frame analysis).",
                },
                "image_base64": {
                    "type": "string",
                    "description": "Base64-encoded image of the video frame (for single frame analysis).",
                },
                "tool_name": {
                    "type": "string",
                    "description": "The exact name of this tool that you are using",
                    "enum": ["get_video_fonts"],
                },
                "task_detail": {
                    "type": "string",
                    "description": "A quick title about the task you are doing",
                },
            },
            "required": ["timestamp", "tool_name", "task_detail"],
            "additionalProperties": True,
        },
    },
    {
        "name": "check_video_frame_specs",
        "description": "Analyze the video frame specifications at the specified timestamp for compliance with brand guidelines.",
        "input_schema": {
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
                "images_base64": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of base64-encoded video frames (optional, for multi-frame analysis).",
                },
                "image_base64": {
                    "type": "string",
                    "description": "Base64-encoded image of the video frame (for single frame analysis).",
                },
                "tool_name": {
                    "type": "string",
                    "description": "The exact name of this tool that you are using",
                    "enum": ["check_video_frame_specs"],
                },
                "task_detail": {
                    "type": "string",
                    "description": "A quick title about the task you are doing",
                },
            },
            "required": ["timestamp", "tool_name", "task_detail"],
            "additionalProperties": True,
        },
    },
    {
        "name": "extract_verbal_content",
        "description": "Extract all verbal content from video (both spoken and displayed text) using OCR.",
        "input_schema": {
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
                "images_base64": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of base64-encoded video frames (optional, for multi-frame analysis).",
                },
                "image_base64": {
                    "type": "string",
                    "description": "Base64-encoded image of the video frame (for single frame analysis).",
                },
                "tool_name": {
                    "type": "string",
                    "description": "The exact name of this tool that you are using",
                    "enum": ["extract_verbal_content"],
                },
                "task_detail": {
                    "type": "string",
                    "description": "A quick title about the task you are doing",
                },
            },
            "required": ["tool_name", "task_detail"],
            "additionalProperties": True,
        },
    },
    # --- END VIDEO TOOLS ---
    {
        "name": "search_brand_guidelines",
        "description": "Search for and retrieve the brand guidelines for a specific brand.",
        "input_schema": {
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
                "tool_name": {
                    "type": "string",
                    "description": "The exact name of this tool that you are using",
                    "enum": ["search_brand_guidelines"],
                },
                "task_detail": {
                    "type": "string",
                    "description": "A quick title about the task you are doing",
                },
            },
            "required": ["brand_name", "tool_name", "task_detail"],
            "additionalProperties": True,
        },
    },
    {
        "name": "read_guideline_page",
        "description": "Read a specific page from the brand guidelines to understand detailed requirements.",
        "input_schema": {
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
                "tool_name": {
                    "type": "string",
                    "description": "The exact name of this tool that you are using",
                    "enum": ["read_guideline_page"],
                },
                "task_detail": {
                    "type": "string",
                    "description": "A quick title about the task you are doing",
                },
            },
            "required": ["brand_name", "page_number", "tool_name", "task_detail"],
            "additionalProperties": True,
        },
    },
    {
        "name": "get_image_color_scheme",
        "description": """
            Get the color scheme of the original image that the user wants to check compliance for.
            The color palette is a key aspect of brand compliance. By using this tool, you can extract
            the color palette of the image and match it with the brand's guidelines.
        """,
        "input_schema": {
            "type": "object",
            "properties": {
                "tool_name": {
                    "type": "string",
                    "description": "The exact name of this tool that you are using",
                    "enum": ["get_image_color_scheme"],
                },
                "task_detail": {
                    "type": "string",
                    "description": "A quick title about the task you are doing",
                },
            },
            "required": ["tool_name", "task_detail"],
            "additionalProperties": True,
        },
    },
    {
        "name": "get_image_fonts",
        "description": """
            Identify fonts used in the original image that the user wants to check compliance for.
            Typography is a critical aspect of brand compliance. By using this tool, you can identify
            the fonts used in the image and compare them with the brand's typography guidelines.
        """,
        "input_schema": {
            "type": "object",
            "properties": {
                "tool_name": {
                    "type": "string",
                    "description": "The exact name of this tool that you are using",
                    "enum": ["get_image_fonts"],
                },
                "task_detail": {
                    "type": "string",
                    "description": "A quick title about the task you are doing",
                },
            },
            "required": ["tool_name", "task_detail"],
            "additionalProperties": True,
        },
    },
    {
        "name": "get_region_color_scheme",
        "description": """
            Get the color scheme of a specific region within the image.
            This tool allows you to analyze colors in a particular area of the image,
            which is useful for checking compliance of specific elements like logos, text, or UI components.
        """,
        "input_schema": {
            "type": "object",
            "properties": {
                "x1": {
                    "type": "integer",
                    "description": "The x-coordinate of the top-left corner of the region",
                    "minimum": 0,
                },
                "y1": {
                    "type": "integer",
                    "description": "The y-coordinate of the top-left corner of the region",
                    "minimum": 0,
                },
                "x2": {
                    "type": "integer",
                    "description": "The x-coordinate of the bottom-right corner of the region",
                    "minimum": 0,
                },
                "y2": {
                    "type": "integer",
                    "description": "The y-coordinate of the bottom-right corner of the region",
                    "minimum": 0,
                },
                "tool_name": {
                    "type": "string",
                    "description": "The exact name of this tool that you are using",
                    "enum": ["get_region_color_scheme"],
                },
                "task_detail": {
                    "type": "string",
                    "description": "A quick title about the task you are doing",
                },
            },
            "required": ["x1", "y1", "x2", "y2", "tool_name", "task_detail"],
            "additionalProperties": True,
        },
    },
    {
        "name": "check_color_contrast",
        "description": """
            Analyze the image for color contrast accessibility compliance.
            This tool checks color contrast ratios between text and background colors
            to ensure the design meets WCAG accessibility standards, which is often a requirement in brand guidelines.
        """,
        "input_schema": {
            "type": "object",
            "properties": {
                "foreground_region": {
                    "type": "object",
                    "description": "Region containing the foreground (text) color",
                    "properties": {
                        "x1": {"type": "integer", "minimum": 0},
                        "y1": {"type": "integer", "minimum": 0},
                        "x2": {"type": "integer", "minimum": 0},
                        "y2": {"type": "integer", "minimum": 0},
                    },
                    "required": ["x1", "y1", "x2", "y2"],
                },
                "background_region": {
                    "type": "object",
                    "description": "Region containing the background color",
                    "properties": {
                        "x1": {"type": "integer", "minimum": 0},
                        "y1": {"type": "integer", "minimum": 0},
                        "x2": {"type": "integer", "minimum": 0},
                        "y2": {"type": "integer", "minimum": 0},
                    },
                    "required": ["x1", "y1", "x2", "y2"],
                },
                "tool_name": {
                    "type": "string",
                    "description": "The exact name of this tool that you are using",
                    "enum": ["check_color_contrast"],
                },
                "task_detail": {
                    "type": "string",
                    "description": "A quick title about the task you are doing",
                },
            },
            "required": [
                "foreground_region",
                "background_region",
                "tool_name",
                "task_detail",
            ],
            "additionalProperties": True,
        },
    },
    {
        "name": "check_image_specs",
        "description": """
            Analyze the image specifications for compliance with brand guidelines.
            This tool checks image dimensions, resolution, aspect ratio, and file size
            to ensure they meet the requirements specified in brand guidelines.
        """,
        "input_schema": {
            "type": "object",
            "properties": {
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
                "tool_name": {
                    "type": "string",
                    "description": "The exact name of this tool that you are using",
                    "enum": ["check_image_specs"],
                },
                "task_detail": {
                    "type": "string",
                    "description": "A quick title about the task you are doing",
                },
            },
            "required": ["tool_name", "task_detail"],
            "additionalProperties": True,
        },
    },
    {
        "name": "check_element_placement",
        "description": """
            Analyze the placement, spacing, and alignment of elements in the image.
            This tool checks if elements (like logos, text, graphics) are properly positioned
            according to brand guidelines, including edge alignment, safe zones, and spacing requirements.
        """,
        "input_schema": {
            "type": "object",
            "properties": {
                "primary_element_coordinates": {
                    "type": "string",
                    "description": "Coordinates of the primary element (e.g., logo) in format 'x1,y1,x2,y2'",
                },
                "secondary_elements_coordinates": {
                    "type": "string",
                    "description": "Comma-separated list of secondary element coordinates, each in format 'x1,y1,x2,y2'. Multiple elements separated by semicolons (e.g., '10,10,50,50;60,60,100,100')",
                },
                "safe_zone_percentage": {
                    "type": "string",
                    "description": "Safe zone boundaries as percentages in format 'top,right,bottom,left' (default: '10,10,10,10')",
                },
                "min_spacing": {
                    "type": "integer",
                    "description": "Minimum spacing required between elements in pixels (default: 20)",
                    "minimum": 0,
                },
                "output_directory": {
                    "type": "string",
                    "description": "Directory to save visualization images (default: 'compliance_results')",
                },
                "tool_name": {
                    "type": "string",
                    "description": "The exact name of this tool that you are using",
                    "enum": ["check_element_placement"],
                },
                "task_detail": {
                    "type": "string",
                    "description": "A quick title about the task you are doing",
                },
            },
            "required": ["primary_element_coordinates", "tool_name", "task_detail"],
            "additionalProperties": True,
        },
    },
    {
        "name": "check_image_clarity",
        "description": """
            Analyze the clarity and sharpness of a specific region in an image.
            This tool checks if elements like logos, text, or other brand assets are displayed with sufficient clarity.
            It's particularly useful for checking if logos or text are blurred, pixelated, or otherwise unclear.
        """,
        "input_schema": {
            "type": "object",
            "properties": {
                "timestamp": {
                    "type": "integer",
                    "description": "For videos, the timestamp in seconds where to check clarity.",
                },
                "region_coordinates": {
                    "type": "string",
                    "description": "The coordinates of the region to analyze in format 'x1,y1,x2,y2'.",
                },
                "element_type": {
                    "type": "string",
                    "description": "The type of element being analyzed (e.g., 'logo', 'text', 'product').",
                },
                "min_clarity_score": {
                    "type": "integer",
                    "description": "Minimum acceptable clarity score (0-100).",
                },
                "tool_name": {
                    "type": "string",
                    "description": "The exact name of this tool that you are using",
                    "enum": ["check_image_clarity"],
                },
                "task_detail": {
                    "type": "string",
                    "description": "A quick title about the task you are doing",
                },
            },
            "required": ["region_coordinates", "element_type", "tool_name", "task_detail"],
            "additionalProperties": True,
        },
    },
    {
        "name": "check_layout_consistency",
        "description": """
            Analyze the layout consistency of an image against a grid system or template.
            This tool checks if the image follows a consistent grid structure, proper alignment,
            and maintains consistent spacing throughout the layout as specified in brand guidelines.
        """,
        "input_schema": {
            "type": "object",
            "properties": {
                "elements_coordinates": {
                    "type": "string",
                    "description": "Comma-separated list of element coordinates, each in format 'x1,y1,x2,y2'. Multiple elements separated by semicolons (e.g., '10,10,50,50;60,60,100,100')",
                },
                "grid_settings": {
                    "type": "string",
                    "description": "Grid settings in format 'columns,rows,gutter_size,margin_size' (default: '12,0,20,40')",
                },
                "output_directory": {
                    "type": "string",
                    "description": "Directory to save visualization images (default: 'compliance_results')",
                },
                "tool_name": {
                    "type": "string",
                    "description": "The exact name of this tool that you are using",
                    "enum": ["check_layout_consistency"],
                },
                "task_detail": {
                    "type": "string",
                    "description": "A quick title about the task you are doing",
                },
            },
            "required": ["elements_coordinates", "tool_name", "task_detail"],
            "additionalProperties": True,
        },
    },
    {
        "name": "attempt_completion",
        "description": "Present the final brand compliance analysis after examining the image and brand guidelines.",
        "input_schema": {
            "type": "object",
            "properties": {
                "result": {
                    "type": "string",
                    "description": "The detailed compliance analysis result.",
                    "minLength": 1,
                },
                "tool_name": {
                    "type": "string",
                    "description": "The exact name of this tool that you are using",
                    "enum": ["attempt_completion"],
                },
                "task_detail": {
                    "type": "string",
                    "description": "A quick title about the task you are doing",
                },
            },
            "required": ["result", "tool_name", "task_detail"],
            "additionalProperties": True,
        },
    },
]

import json

# --- VIDEO TOOL IMPORTS ---
from app.core.video_agent.video_tools import (
    get_video_color_scheme,
    get_video_fonts,
    check_video_frame_specs,
    extract_verbal_content,
)

def get_tool_function(tool_name: str):
    tool_map = {
        "check_text_grammar": check_text_grammar,
        "search_brand_guidelines": get_brand_guidelines,
        "read_guideline_page": read_guideline_page,
        "attempt_completion": attempt_completion,
        "get_image_color_scheme": get_image_color_scheme,
        "get_image_fonts": get_image_fonts,
        "get_video_color_scheme": get_video_color_scheme,
        "get_video_fonts": get_video_fonts,
        "check_video_frame_specs": check_video_frame_specs,
        "extract_verbal_content": extract_verbal_content,
        "get_region_color_scheme": get_region_color_scheme,
        "check_color_contrast": check_color_contrast,
        "check_image_specs": check_image_specs,
        "check_element_placement": check_element_placement,
        "check_layout_consistency": check_layout_consistency,
        "check_image_clarity": check_image_clarity,
    }
    return tool_map.get(tool_name)


# Tool functions are defined below

async def check_text_grammar(data):
    """
    Stub for check_text_grammar tool.
    """
    return {
        "result": "Grammar check not implemented yet. This is a stub response.",
        "input": data
    }


from io import BytesIO
from PIL import Image
import base64
import json
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def get_image_color_scheme(data):
    """Get the color scheme of the original image that the user wants to check compliance for."""

    image_base64 = data.get("image_base64")

    # Check if the base64 string exists
    if not image_base64:
        return json.dumps({"error": "No image provided."})

    try:
        # Ensure correct padding for base64 string
        padding_needed = len(image_base64) % 4
        if padding_needed != 0:
            image_base64 += "=" * (4 - padding_needed)  # Add padding if necessary

        # Decode the base64 string into binary data
        image_data = base64.b64decode(image_base64)

        # Open the image using PIL
        with Image.open(BytesIO(image_data)) as img:
            # Convert image to RGB if it's not already
            img = img.convert("RGB")

            # Get the color palette of the image
            colors = img.getcolors(
                maxcolors=1000000
            )  # Increase maxcolors to cover all colors

            if not colors:
                return json.dumps({"error": "No colors found in image."})

            # Convert RGB tuples to hex format and remove duplicates
            color_palette = list(
                set([f"#{r:02x}{g:02x}{b:02x}" for count, (r, g, b) in colors])
            )

            # Limit the palette to 10 colors
            color_palette = color_palette[:10]

            return json.dumps({"color_palette": color_palette})

    except Exception as e:
        return json.dumps({"error": f"Failed to process image: {str(e)}"})


async def get_brand_guidelines(data):
    """Search for and retrieve the brand guidelines for a specific brand."""
    brand_name = data.get("brand_name")
    if not brand_name:
        return json.dumps({"error": "No brand name provided."})

    query = data.get("query")

    try:
        # Import necessary modules
        from app.db.database import brand_guidelines_collection, get_guideline_pages
        from bson.objectid import ObjectId
        import re

        # First try an exact match
        exact_match = brand_guidelines_collection.find_one({"brand_name": brand_name})

        if exact_match:
            # Found an exact match
            best_match = exact_match
            best_match["id"] = str(best_match["_id"])
        else:
            # Try a case-insensitive regex match
            regex_pattern = f"^{re.escape(brand_name)}$"
            regex_match = brand_guidelines_collection.find_one(
                {"brand_name": {"$regex": regex_pattern, "$options": "i"}}
            )

            if regex_match:
                # Found a case-insensitive match
                best_match = regex_match
                best_match["id"] = str(best_match["_id"])
            else:
                # Try a fuzzy match by getting all guidelines and calculating similarity
                def calculate_string_similarity(str1, str2):
                    """Calculate similarity between two strings (0-1)"""
                    str1 = str1.lower()
                    str2 = str2.lower()

                    if len(str1) == 0 or len(str2) == 0:
                        return 0.0

                    # Simple Levenshtein distance implementation
                    matrix = [
                        [0 for _ in range(len(str2) + 1)] for _ in range(len(str1) + 1)
                    ]

                    for i in range(len(str1) + 1):
                        matrix[i][0] = i
                    for j in range(len(str2) + 1):
                        matrix[0][j] = j

                    for i in range(1, len(str1) + 1):
                        for j in range(1, len(str2) + 1):
                            if str1[i - 1] == str2[j - 1]:
                                matrix[i][j] = matrix[i - 1][j - 1]
                            else:
                                matrix[i][j] = min(
                                    matrix[i - 1][j] + 1,  # deletion
                                    matrix[i][j - 1] + 1,  # insertion
                                    matrix[i - 1][j - 1] + 1,  # substitution
                                )

                    distance = matrix[len(str1)][len(str2)]
                    max_length = max(len(str1), len(str2))

                    return 1.0 - (distance / max_length)

                # Get all guidelines
                all_guidelines = list(brand_guidelines_collection.find({}))

                # Calculate similarity for each guideline
                best_match = None
                best_similarity = 0

                for guideline in all_guidelines:
                    similarity = calculate_string_similarity(
                        brand_name, guideline.get("brand_name", "")
                    )
                    if similarity >= 0.8 and similarity > best_similarity:
                        best_similarity = similarity
                        best_match = guideline
                        best_match["id"] = str(best_match["_id"])

        # If no match found with at least 80% similarity
        if not best_match:
            return json.dumps(
                {
                    "error": f"Brand guidelines for '{brand_name}' not found.",
                    "available_brands": (
                        [g.get("brand_name") for g in all_guidelines]
                        if "all_guidelines" in locals()
                        else []
                    ),
                }
            )

        # Get all pages for this guideline
        pages = get_guideline_pages(best_match["id"], include_base64=False)

        # If query parameter is provided, filter pages by content
        if query:
            filtered_pages = []
            for page in pages:
                # Check if processing_results contains the query
                if page.get("processing_results") and isinstance(
                    page.get("processing_results"), dict
                ):
                    result_text = page.get("processing_results").get("result", "")
                    if (
                        isinstance(result_text, str)
                        and query.lower() in result_text.lower()
                    ):
                        filtered_pages.append(page)

            # If we found matching pages, use them instead
            if filtered_pages:
                pages = filtered_pages

        # Format the response
        response = {
            "brand_name": best_match.get("brand_name"),
            "filename": best_match.get("filename"),
            "total_pages": best_match.get("total_pages"),
            "description": best_match.get("description"),
            "id": best_match.get("id"),
            "pages": [
                {
                    "id": page.get("id"),
                    "page_number": page.get("page_number"),
                    "width": page.get("width"),
                    "height": page.get("height"),
                    "format": page.get("format"),
                    "processing_results": page.get("processing_results"),
                    "compliance_score": page.get("compliance_score"),
                }
                for page in pages
            ],
            "last_updated": (
                best_match.get("updated_at").isoformat()
                if best_match.get("updated_at")
                else None
            ),
        }

        return json.dumps(response)

    except Exception as e:
        return json.dumps(
            {
                "error": f"Error retrieving brand guidelines: {str(e)}",
                "available_brands": [],
            }
        )


async def read_guideline_page(data):
    """Read a specific page from the brand guidelines."""
    brand_name = data.get("brand_name")
    page_number = data.get("page_number")
    if isinstance(page_number, str):
        page_number = int(page_number)

    if not brand_name:
        return json.dumps({"error": "No brand name provided."})
    if not page_number:
        return json.dumps({"error": "No page number provided."})

    # print("📖 Reading guideline page ->", data)

    try:
        # Import necessary modules
        print("📦 Importing modules")
        from app.db.database import (
            brand_guidelines_collection,
            guideline_pages_collection,
        )

        print("✅ Imported database modules")
        from bson.objectid import ObjectId

        print("✅ Imported ObjectId")
        import re

        print("🔎 Trying to find exact match")
        # First try an exact match
        exact_match = brand_guidelines_collection.find_one({"brand_name": brand_name})

        print("🎯 Found exact match:", exact_match)

        if exact_match:
            # Found an exact match
            best_match = exact_match
            best_match["id"] = str(best_match["_id"])
        else:
            print("❓ No exact match found")
            # Try a case-insensitive regex match
            regex_pattern = f"^{re.escape(brand_name)}$"
            print("🔍 Regex pattern:", regex_pattern)
            regex_match = brand_guidelines_collection.find_one(
                {"brand_name": {"$regex": regex_pattern, "$options": "i"}}
            )

            print("🔍 Regex match:", regex_match)

            if regex_match:
                # Found a case-insensitive match
                best_match = regex_match
                best_match["id"] = str(best_match["_id"])
            else:
                # Try a fuzzy match by getting all guidelines and calculating similarity
                print("❓ No regex match found")

                def calculate_string_similarity(str1, str2):
                    """Calculate similarity between two strings (0-1)"""
                    str1 = str1.lower()
                    str2 = str2.lower()

                    if len(str1) == 0 or len(str2) == 0:
                        return 0.0

                    # Simple Levenshtein distance implementation
                    matrix = [
                        [0 for _ in range(len(str2) + 1)] for _ in range(len(str1) + 1)
                    ]

                    for i in range(len(str1) + 1):
                        matrix[i][0] = i
                    for j in range(len(str2) + 1):
                        matrix[0][j] = j

                    for i in range(1, len(str1) + 1):
                        for j in range(1, len(str2) + 1):
                            if str1[i - 1] == str2[j - 1]:
                                matrix[i][j] = matrix[i - 1][j - 1]
                            else:
                                matrix[i][j] = min(
                                    matrix[i - 1][j] + 1,  # deletion
                                    matrix[i][j - 1] + 1,  # insertion
                                    matrix[i - 1][j - 1] + 1,  # substitution
                                )

                    distance = matrix[len(str1)][len(str2)]
                    max_length = max(len(str1), len(str2))

                    return 1.0 - (distance / max_length)

                # Get all guidelines
                all_guidelines = list(brand_guidelines_collection.find({}))

                # Calculate similarity for each guideline
                best_match = None
                best_similarity = 0

                for guideline in all_guidelines:
                    similarity = calculate_string_similarity(
                        brand_name, guideline.get("brand_name", "")
                    )
                    if similarity >= 0.5 and similarity > best_similarity:
                        best_similarity = similarity
                        best_match = guideline
                        guideline["id"] = str(guideline["_id"])

        # If no match found with at least 80% similarity
        if not best_match:
            print("❌ No match found")
            return json.dumps(
                {
                    "error": f"Brand guidelines for '{brand_name}' not found.",
                    "available_brands": (
                        [g.get("brand_name") for g in all_guidelines]
                        if "all_guidelines" in locals()
                        else []
                    ),
                }
            )

        # Now get the specific page by page number
        page = guideline_pages_collection.find_one(
            {"guideline_id": best_match["id"], "page_number": page_number}
        )

        if not page:
            print("❌ Page not found")
            return json.dumps(
                {
                    "error": f"Page {page_number} not found in {brand_name} guidelines.",
                    "total_pages": best_match.get("total_pages", 0),
                }
            )

        page["id"] = str(page["_id"])

        # Format the response
        response = {
            "brand_name": best_match.get("brand_name"),
            "page_number": page.get("page_number"),
            "width": page.get("width"),
            "height": page.get("height"),
            "format": page.get("format"),
            "base64": page.get("base64"),
            "processing_results": page.get("processing_results"),
            "compliance_score": page.get("compliance_score"),
            "id": page.get("id"),
            "guideline_id": page.get("guideline_id"),
        }

        return json.dumps(response)

    except Exception as e:
        print(f"❌ Error in read_guideline_page: {str(e)}")
        return json.dumps({"error": f"Error retrieving guideline page: {str(e)}"})


async def get_region_color_scheme(data):
    """Get the color scheme of a specific region within the image."""

    image_base64 = data.get("image_base64")
    # Ensure coordinates are integers
    try:
        x1 = int(data.get("x1", 0))
        y1 = int(data.get("y1", 0))
        x2 = int(data.get("x2", 0))
        y2 = int(data.get("y2", 0))
    except Exception as e:
        return json.dumps({"error": f"Invalid coordinate type: {str(e)}"})

    # Check if the base64 string exists
    if not image_base64:
        return json.dumps({"error": "No image provided."})

    # Validate coordinates
    if x1 < 0 or y1 < 0 or x2 <= x1 or y2 <= y1:
        return json.dumps(
            {
                "error": "Invalid region coordinates. Ensure x1 < x2 and y1 < y2, and all values are non-negative."
            }
        )

    try:
        # Ensure correct padding for base64 string
        padding_needed = len(image_base64) % 4
        if padding_needed != 0:
            image_base64 += "=" * (4 - padding_needed)  # Add padding if necessary

        # Decode the base64 string into binary data
        image_data = base64.b64decode(image_base64)

        # Open the image using PIL
        with Image.open(BytesIO(image_data)) as img:
            # Convert image to RGB if it's not already
            img = img.convert("RGB")

            # Get image dimensions
            width, height = img.size

            # Validate coordinates against image dimensions
            if x2 > width or y2 > height:
                return json.dumps(
                    {
                        "error": f"Region coordinates exceed image dimensions. Image size is {width}x{height}.",
                        "image_dimensions": {"width": width, "height": height},
                    }
                )

            # Crop the image to the specified region
            region = img.crop((x1, y1, x2, y2))

            # Get the color palette of the region
            colors = region.getcolors(
                maxcolors=1000000
            )  # Increase maxcolors to cover all colors

            if not colors:
                return json.dumps({"error": "No colors found in the specified region."})

            # Convert RGB tuples to hex format and remove duplicates
            color_palette = list(
                set([f"#{r:02x}{g:02x}{b:02x}" for count, (r, g, b) in colors])
            )

            # Limit the palette to 10 colors
            color_palette = color_palette[:10]

            # Create a visual representation of the region (optional)
            region_preview = region.copy()
            region_preview.thumbnail((200, 200))  # Resize for preview

            # Convert region preview to base64 for visualization
            buffer = BytesIO()
            region_preview.save(buffer, format="PNG")
            region_preview_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            return json.dumps(
                {
                    "region": {
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                        "width": x2 - x1,
                        "height": y2 - y1,
                    },
                    "color_palette": color_palette,
                }
            )

    except Exception as e:
        return json.dumps({"error": f"Failed to process image region: {str(e)}"})


async def get_image_fonts(data):
    """Identify fonts used in the original image using the WhatFontIs API."""

    image_base64 = data.get("image_base64")

    # Check if the base64 string exists
    if not image_base64:
        return json.dumps({"error": "No image provided."})

    try:
        # Ensure correct padding for base64 string
        padding_needed = len(image_base64) % 4
        if padding_needed != 0:
            image_base64 += "=" * (4 - padding_needed)  # Add padding if necessary

        # Get API key from environment variables
        api_key = os.getenv("WHATFONTIS_API_KEY")

        # Prepare the API request
        url = "https://www.whatfontis.com/api2/"
        payload = {
            "API_KEY": api_key,
            "IMAGEBASE64": 1,  # Use base64 encoded image
            "NOTTEXTBOXSDETECTION": 0,  # Attempt to locate a textbox containing text
            "FREEFONTS": 0,  # Include all fonts in results
            "urlimagebase64": image_base64,
            "limit": 5,  # Get up to 5 font matches
        }

        # Make the API request
        response = requests.post(url, data=payload)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response
            font_data = response.json()

            # Return the font information
            return json.dumps(
                {
                    "fonts": font_data,
                    "count": len(font_data) if isinstance(font_data, list) else 0,
                }
            )
        else:
            return json.dumps(
                {
                    "error": f"API request failed with status code {response.status_code}",
                    "message": response.text,
                }
            )

    except Exception as e:
        return json.dumps(
            {"error": f"Failed to process image or identify fonts: {str(e)}"}
        )


async def check_color_contrast(data):
    """Analyze the image for color contrast accessibility compliance."""

    image_base64 = data.get("image_base64")
    foreground_region = data.get("foreground_region", {})
    background_region = data.get("background_region", {})

    # Check if the base64 string exists
    if not image_base64:
        return json.dumps({"error": "No image provided."})

    # Validate regions
    if not foreground_region or not background_region:
        return json.dumps(
            {"error": "Both foreground and background regions must be provided."}
        )

    try:
        # Ensure correct padding for base64 string
        padding_needed = len(image_base64) % 4
        if padding_needed != 0:
            image_base64 += "=" * (4 - padding_needed)  # Add padding if necessary

        # Decode the base64 string into binary data
        image_data = base64.b64decode(image_base64)

        # Open the image using PIL
        with Image.open(BytesIO(image_data)) as img:
            # Convert image to RGB if it's not already
            img = img.convert("RGB")

            # Get image dimensions
            width, height = img.size

            # Extract regions
            fg_x1 = max(0, foreground_region.get("x1", 0))
            fg_y1 = max(0, foreground_region.get("y1", 0))
            fg_x2 = min(width, foreground_region.get("x2", width))
            fg_y2 = min(height, foreground_region.get("y2", height))

            bg_x1 = max(0, background_region.get("x1", 0))
            bg_y1 = max(0, background_region.get("y1", 0))
            bg_x2 = min(width, background_region.get("x2", width))
            bg_y2 = min(height, background_region.get("y2", height))

            # Crop the regions
            foreground_img = img.crop((fg_x1, fg_y1, fg_x2, fg_y2))
            background_img = img.crop((bg_x1, bg_y1, bg_x2, bg_y2))

            # Get the dominant color from each region
            def get_dominant_color(image):
                # Resize image to speed up processing
                image = image.resize((100, 100))
                # Get colors from the image
                colors = image.getcolors(10000)  # Get all colors
                if not colors:
                    return (0, 0, 0)  # Default to black if no colors found
                # Sort by count and get the most common
                sorted_colors = sorted(colors, key=lambda x: x[0], reverse=True)
                return sorted_colors[0][1]  # Return the RGB value

            foreground_color = get_dominant_color(foreground_img)
            background_color = get_dominant_color(background_img)

            # Calculate relative luminance for each color
            def get_luminance(rgb):
                r, g, b = rgb
                # Convert RGB to sRGB
                r_srgb = r / 255
                g_srgb = g / 255
                b_srgb = b / 255

                # Convert sRGB to linear RGB
                r_linear = (
                    r_srgb / 12.92
                    if r_srgb <= 0.04045
                    else ((r_srgb + 0.055) / 1.055) ** 2.4
                )
                g_linear = (
                    g_srgb / 12.92
                    if g_srgb <= 0.04045
                    else ((g_srgb + 0.055) / 1.055) ** 2.4
                )
                b_linear = (
                    b_srgb / 12.92
                    if b_srgb <= 0.04045
                    else ((b_srgb + 0.055) / 1.055) ** 2.4
                )

                # Calculate relative luminance
                return 0.2126 * r_linear + 0.7152 * g_linear + 0.0722 * b_linear

            # Calculate contrast ratio
            l1 = get_luminance(foreground_color)
            l2 = get_luminance(background_color)

            # Ensure l1 is the lighter color
            if l1 <= l2:
                l1, l2 = l2, l1

            contrast_ratio = (l1 + 0.05) / (l2 + 0.05)

            # WCAG 2.0 levels
            wcag_aa_normal = contrast_ratio >= 4.5
            wcag_aa_large = contrast_ratio >= 3.0
            wcag_aaa_normal = contrast_ratio >= 7.0
            wcag_aaa_large = contrast_ratio >= 4.5

            # Create a visual representation
            result_img = img.copy()
            from PIL import ImageDraw

            draw = ImageDraw.Draw(result_img)

            # Draw rectangles around the regions
            draw.rectangle([(fg_x1, fg_y1), (fg_x2, fg_y2)], outline="red", width=2)
            draw.rectangle([(bg_x1, bg_y1), (bg_x2, bg_y2)], outline="blue", width=2)

            # Convert the result image to base64
            buffer = BytesIO()
            result_img.save(buffer, format="PNG")
            result_img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            # Convert RGB to hex for display
            def rgb_to_hex(rgb):
                return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

            foreground_hex = rgb_to_hex(foreground_color)
            background_hex = rgb_to_hex(background_color)

            return json.dumps(
                {
                    "foreground_color": foreground_hex,
                    "background_color": background_hex,
                    "contrast_ratio": round(contrast_ratio, 2),
                    "wcag_compliance": {
                        "AA": {
                            "normal_text": wcag_aa_normal,
                            "large_text": wcag_aa_large,
                        },
                        "AAA": {
                            "normal_text": wcag_aaa_normal,
                            "large_text": wcag_aaa_large,
                        },
                    },
                    # "visualization_base64": result_img_base64,
                }
            )

    except Exception as e:
        return json.dumps({"error": f"Failed to analyze color contrast: {str(e)}"})


async def check_image_specs(data):
    """Analyze the image specifications for compliance with brand guidelines."""

    image_base64 = data.get("image_base64")
    required_width = data.get("required_width", 0)
    required_height = data.get("required_height", 0)
    min_resolution = data.get("min_resolution", 0)
    aspect_ratio = data.get("aspect_ratio", "any")

    # Check if the base64 string exists
    if not image_base64:
        return json.dumps({"error": "No image provided."})

    try:
        # Ensure correct padding for base64 string
        padding_needed = len(image_base64) % 4
        if padding_needed != 0:
            image_base64 += "=" * (4 - padding_needed)  # Add padding if necessary

        # Decode the base64 string into binary data
        image_data = base64.b64decode(image_base64)

        # Get file size in KB
        file_size_kb = len(image_data) / 1024

        # Open the image using PIL
        with Image.open(BytesIO(image_data)) as img:
            # Get image dimensions
            width, height = img.size

            # Check DPI (resolution)
            dpi = img.info.get("dpi", (72, 72))
            resolution = dpi[0]  # Use horizontal DPI

            # Calculate aspect ratio
            def gcd(a, b):
                """Calculate the Greatest Common Divisor of a and b."""
                while b:
                    a, b = b, a % b
                return a

            # Calculate the GCD to simplify the ratio
            divisor = gcd(width, height)
            simplified_ratio = f"{width // divisor}:{height // divisor}"

            # Check if dimensions match requirements
            width_compliant = required_width == 0 or width == required_width
            height_compliant = required_height == 0 or height == required_height
            resolution_compliant = min_resolution == 0 or resolution >= min_resolution

            # Check aspect ratio compliance
            aspect_ratio_compliant = (
                aspect_ratio == "any" or simplified_ratio == aspect_ratio
            )

            # Compile compliance results
            compliance_results = {
                "width": {
                    "actual": width,
                    "required": required_width if required_width > 0 else "any",
                    "compliant": width_compliant,
                },
                "height": {
                    "actual": height,
                    "required": required_height if required_height > 0 else "any",
                    "compliant": height_compliant,
                },
                "resolution": {
                    "actual": resolution,
                    "required": min_resolution if min_resolution > 0 else "any",
                    "compliant": resolution_compliant,
                },
                "aspect_ratio": {
                    "actual": simplified_ratio,
                    "required": aspect_ratio,
                    "compliant": aspect_ratio_compliant,
                },
                "file_size": {"kb": round(file_size_kb, 2)},
            }

            # Overall compliance
            overall_compliant = all(
                [
                    width_compliant,
                    height_compliant,
                    resolution_compliant,
                    aspect_ratio_compliant,
                ]
            )

            return json.dumps(
                {
                    "image_specs": {
                        "width": width,
                        "height": height,
                        "resolution": resolution,
                        "aspect_ratio": simplified_ratio,
                        "file_size_kb": round(file_size_kb, 2),
                    },
                    "compliance_results": compliance_results,
                    "overall_compliant": overall_compliant,
                }
            )

    except Exception as e:
        return json.dumps(
            {"error": f"Failed to analyze image specifications: {str(e)}"}
        )


async def check_element_placement(data):
    """Analyze the placement, spacing, and alignment of elements in the image."""

    image_base64 = data.get("image_base64")
    output_dir = data.get("output_directory", "compliance_results")
    min_spacing = data.get("min_spacing", 20)
    alignment_tolerance = data.get("alignment_tolerance", 5)

    # Parse primary element coordinates
    primary_element_coords = data.get("primary_element_coordinates", "")
    primary_element = {}
    if primary_element_coords:
        try:
            coords = [int(x) for x in primary_element_coords.split(",")]
            if len(coords) == 4:
                primary_element = {
                    "x1": coords[0],
                    "y1": coords[1],
                    "x2": coords[2],
                    "y2": coords[3],
                }
        except (ValueError, IndexError):
            return json.dumps(
                {
                    "error": "Invalid primary element coordinates format. Expected 'x1,y1,x2,y2'"
                }
            )

    # Parse secondary elements coordinates
    secondary_elements = []
    secondary_elements_coords = data.get("secondary_elements_coordinates", "")
    if secondary_elements_coords:
        try:
            elements = secondary_elements_coords.split(";")
            for element in elements:
                if not element.strip():
                    continue
                coords = [int(x) for x in element.split(",")]
                if len(coords) == 4:
                    secondary_elements.append(
                        {
                            "x1": coords[0],
                            "y1": coords[1],
                            "x2": coords[2],
                            "y2": coords[3],
                        }
                    )
        except (ValueError, IndexError):
            return json.dumps(
                {
                    "error": "Invalid secondary elements coordinates format. Expected 'x1,y1,x2,y2;x1,y1,x2,y2;...'"
                }
            )

    # Parse safe zone percentages
    safe_zone = {"top": 10, "right": 10, "bottom": 10, "left": 10}
    safe_zone_percentage = data.get("safe_zone_percentage", "")
    if safe_zone_percentage:
        try:
            percentages = [float(x) for x in safe_zone_percentage.split(",")]
            if len(percentages) == 4:
                safe_zone = {
                    "top": percentages[0],
                    "right": percentages[1],
                    "bottom": percentages[2],
                    "left": percentages[3],
                }
        except (ValueError, IndexError):
            return json.dumps(
                {"error": "Invalid safe zone format. Expected 'top,right,bottom,left'"}
            )

    # Check if the base64 string exists
    if not image_base64:
        return json.dumps({"error": "No image provided."})

    # Validate primary element
    if not primary_element:
        return json.dumps({"error": "Primary element region must be provided."})

    try:
        # Ensure correct padding for base64 string
        padding_needed = len(image_base64) % 4
        if padding_needed != 0:
            image_base64 += "=" * (4 - padding_needed)  # Add padding if necessary

        # Decode the base64 string into binary data
        image_data = base64.b64decode(image_base64)

        # Open the image using PIL
        with Image.open(BytesIO(image_data)) as img:
            # Get image dimensions
            width, height = img.size

            # Calculate safe zone boundaries in pixels
            safe_top = int(height * safe_zone.get("top", 10) / 100)
            safe_right = int(width * (1 - safe_zone.get("right", 10) / 100))
            safe_bottom = int(height * (1 - safe_zone.get("bottom", 10) / 100))
            safe_left = int(width * safe_zone.get("left", 10) / 100)

            # Extract primary element coordinates
            p_x1 = max(0, primary_element.get("x1", 0))
            p_y1 = max(0, primary_element.get("y1", 0))
            p_x2 = min(width, primary_element.get("x2", width))
            p_y2 = min(height, primary_element.get("y2", height))

            # Check if primary element is within safe zone
            primary_in_safe_zone = (
                p_x1 >= safe_left
                and p_y1 >= safe_top
                and p_x2 <= safe_right
                and p_y2 <= safe_bottom
            )

            # Check edge alignment for primary element
            primary_edge_aligned = {
                "left": abs(p_x1 - safe_left) <= alignment_tolerance,
                "top": abs(p_y1 - safe_top) <= alignment_tolerance,
                "right": abs(p_x2 - safe_right) <= alignment_tolerance,
                "bottom": abs(p_y2 - safe_bottom) <= alignment_tolerance,
                "center_x": abs((p_x1 + p_x2) / 2 - width / 2) <= alignment_tolerance,
                "center_y": abs((p_y1 + p_y2) / 2 - height / 2) <= alignment_tolerance,
            }

            # Process secondary elements
            secondary_results = []
            for i, element in enumerate(secondary_elements):
                s_x1 = max(0, element.get("x1", 0))
                s_y1 = max(0, element.get("y1", 0))
                s_x2 = min(width, element.get("x2", width))
                s_y2 = min(height, element.get("y2", height))

                # Check if secondary element is within safe zone
                in_safe_zone = (
                    s_x1 >= safe_left
                    and s_y1 >= safe_top
                    and s_x2 <= safe_right
                    and s_y2 <= safe_bottom
                )

                # Check spacing between primary and secondary element
                # Calculate minimum distance between rectangles
                if s_x2 < p_x1:  # Secondary is to the left of primary
                    min_distance = p_x1 - s_x2
                elif s_x1 > p_x2:  # Secondary is to the right of primary
                    min_distance = s_x1 - p_x2
                elif s_y2 < p_y1:  # Secondary is above primary
                    min_distance = p_y1 - s_y2
                elif s_y1 > p_y2:  # Secondary is below primary
                    min_distance = s_y1 - p_y2
                else:  # Overlapping
                    min_distance = 0

                spacing_compliant = min_distance >= min_spacing

                # Check alignment with primary element
                aligned_with_primary = {
                    "left": abs(s_x1 - p_x1) <= alignment_tolerance,
                    "top": abs(s_y1 - p_y1) <= alignment_tolerance,
                    "right": abs(s_x2 - p_x2) <= alignment_tolerance,
                    "bottom": abs(s_y2 - p_y2) <= alignment_tolerance,
                    "center_x": abs((s_x1 + s_x2) / 2 - (p_x1 + p_x2) / 2)
                    <= alignment_tolerance,
                    "center_y": abs((s_y1 + s_y2) / 2 - (p_y1 + p_y2) / 2)
                    <= alignment_tolerance,
                }

                secondary_results.append(
                    {
                        "element_index": i,
                        "region": {
                            "x1": s_x1,
                            "y1": s_y1,
                            "x2": s_x2,
                            "y2": s_y2,
                            "width": s_x2 - s_x1,
                            "height": s_y2 - s_y1,
                        },
                        "in_safe_zone": in_safe_zone,
                        "spacing_from_primary": min_distance,
                        "spacing_compliant": spacing_compliant,
                        "aligned_with_primary": aligned_with_primary,
                        "any_alignment": any(aligned_with_primary.values()),
                    }
                )

            # Create a visual representation
            result_img = img.copy()
            from PIL import ImageDraw

            draw = ImageDraw.Draw(result_img)

            # Draw safe zone
            draw.rectangle(
                [(safe_left, safe_top), (safe_right, safe_bottom)],
                outline="green",
                width=2,
            )

            # Draw primary element
            draw.rectangle([(p_x1, p_y1), (p_x2, p_y2)], outline="blue", width=2)

            # Draw secondary elements
            for i, element in enumerate(secondary_elements):
                s_x1 = max(0, element.get("x1", 0))
                s_y1 = max(0, element.get("y1", 0))
                s_x2 = min(width, element.get("x2", width))
                s_y2 = min(height, element.get("y2", height))

                # Use red for non-compliant spacing, yellow for compliant
                result = secondary_results[i]
                color = "yellow" if result["spacing_compliant"] else "red"
                draw.rectangle([(s_x1, s_y1), (s_x2, s_y2)], outline=color, width=2)

                # Draw label
                draw.text((s_x1, s_y1 - 10), f"Element {i+1}", fill=color)

            # Save the image locally
            import os
            import time

            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)

            # Generate a unique filename with timestamp
            timestamp = int(time.time())
            brand_name = data.get("brand_name", "unknown")
            image_filename = (
                f"{output_dir}/{brand_name}_element_placement_{timestamp}.png"
            )

            # Save the image
            result_img.save(image_filename)

            # Also convert to base64 for API response if needed
            buffer = BytesIO()
            result_img.save(buffer, format="PNG")
            result_img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            # Compile results
            placement_results = {
                "primary_element": {
                    "region": {
                        "x1": p_x1,
                        "y1": p_y1,
                        "x2": p_x2,
                        "y2": p_y2,
                        "width": p_x2 - p_x1,
                        "height": p_y2 - p_y1,
                    },
                    "in_safe_zone": primary_in_safe_zone,
                    "edge_aligned": primary_edge_aligned,
                    "any_alignment": any(primary_edge_aligned.values()),
                },
                "secondary_elements": secondary_results,
                "safe_zone": {
                    "top": safe_top,
                    "right": safe_right,
                    "bottom": safe_bottom,
                    "left": safe_left,
                },
                "image_dimensions": {"width": width, "height": height},
            }

            # Overall compliance
            all_elements_in_safe_zone = primary_in_safe_zone and all(
                element["in_safe_zone"] for element in secondary_results
            )

            all_spacing_compliant = all(
                element["spacing_compliant"] for element in secondary_results
            )

            any_primary_alignment = any(primary_edge_aligned.values())

            overall_compliant = all_elements_in_safe_zone and all_spacing_compliant

            return json.dumps(
                {
                    "placement_results": placement_results,
                    "compliance_summary": {
                        "all_elements_in_safe_zone": all_elements_in_safe_zone,
                        "all_spacing_compliant": all_spacing_compliant,
                        "primary_element_aligned": any_primary_alignment,
                        "overall_compliant": overall_compliant,
                    },
                    # "visualization_base64": result_img_base64,
                    # "visualization_file_path": image_filename,
                }
            )

    except Exception as e:
        return json.dumps({"error": f"Failed to analyze element placement: {str(e)}"})


async def check_layout_consistency(data):
    """Analyze the layout consistency of an image against a grid system or template."""

    image_base64 = data.get("image_base64")
    output_dir = data.get("output_directory", "compliance_results")
    alignment_tolerance = data.get("alignment_tolerance", 5)

    # Parse grid settings
    grid_columns = 12
    grid_rows = 0  # 0 means flexible rows
    gutter_size = 20
    margin_size = 40

    grid_settings = data.get("grid_settings", "")
    if grid_settings:
        try:
            settings = [int(x) for x in grid_settings.split(",")]
            if len(settings) >= 4:
                grid_columns = settings[0]
                grid_rows = settings[1]
                gutter_size = settings[2]
                margin_size = settings[3]
        except (ValueError, IndexError):
            return json.dumps(
                {
                    "error": "Invalid grid settings format. Expected 'columns,rows,gutter_size,margin_size'"
                }
            )

    # Parse elements coordinates
    elements = []
    elements_coordinates = data.get("elements_coordinates", "")
    if elements_coordinates:
        try:
            element_list = elements_coordinates.split(";")
            for i, element in enumerate(element_list):
                if not element.strip():
                    continue
                coords = [int(x) for x in element.split(",")]
                if len(coords) == 4:
                    elements.append(
                        {
                            "x1": coords[0],
                            "y1": coords[1],
                            "x2": coords[2],
                            "y2": coords[3],
                            "name": f"Element {i+1}",
                        }
                    )
        except (ValueError, IndexError):
            return json.dumps(
                {
                    "error": "Invalid elements coordinates format. Expected 'x1,y1,x2,y2;x1,y1,x2,y2;...'"
                }
            )

    # Check if the base64 string exists
    if not image_base64:
        return json.dumps({"error": "No image provided."})

    # Validate elements
    if not elements:
        return json.dumps({"error": "No elements provided to check against the grid."})

    try:
        # Ensure correct padding for base64 string
        padding_needed = len(image_base64) % 4
        if padding_needed != 0:
            image_base64 += "=" * (4 - padding_needed)  # Add padding if necessary

        # Decode the base64 string into binary data
        image_data = base64.b64decode(image_base64)

        # Open the image using PIL
        with Image.open(BytesIO(image_data)) as img:
            # Get image dimensions
            width, height = img.size

            # Calculate grid cell dimensions
            usable_width = width - (2 * margin_size)
            column_width = (
                usable_width - ((grid_columns - 1) * gutter_size)
            ) / grid_columns

            # Calculate row height if grid_rows is specified
            row_height = 0
            if grid_rows > 0:
                usable_height = height - (2 * margin_size)
                row_height = (
                    usable_height - ((grid_rows - 1) * gutter_size)
                ) / grid_rows

            # Calculate grid lines
            grid_lines_x = [margin_size]
            for i in range(1, grid_columns):
                grid_lines_x.append(
                    margin_size + (i * column_width) + (i * gutter_size)
                )
            grid_lines_x.append(width - margin_size)

            grid_lines_y = [margin_size]
            if grid_rows > 0:
                for i in range(1, grid_rows):
                    grid_lines_y.append(
                        margin_size + (i * row_height) + (i * gutter_size)
                    )
                grid_lines_y.append(height - margin_size)

            # Check each element against the grid
            element_results = []
            for i, element in enumerate(elements):
                e_x1 = max(0, element.get("x1", 0))
                e_y1 = max(0, element.get("y1", 0))
                e_x2 = min(width, element.get("x2", width))
                e_y2 = min(height, element.get("y2", height))
                e_name = element.get("name", f"Element {i+1}")

                # Find closest grid lines
                closest_x1 = min(grid_lines_x, key=lambda x: abs(x - e_x1))
                closest_x2 = min(grid_lines_x, key=lambda x: abs(x - e_x2))
                closest_y1 = (
                    min(grid_lines_y, key=lambda x: abs(x - e_y1))
                    if grid_rows > 0
                    else e_y1
                )
                closest_y2 = (
                    min(grid_lines_y, key=lambda x: abs(x - e_y2))
                    if grid_rows > 0
                    else e_y2
                )

                # Check alignment with grid
                x1_aligned = abs(e_x1 - closest_x1) <= alignment_tolerance
                x2_aligned = abs(e_x2 - closest_x2) <= alignment_tolerance
                y1_aligned = (
                    abs(e_y1 - closest_y1) <= alignment_tolerance
                    if grid_rows > 0
                    else True
                )
                y2_aligned = (
                    abs(e_y2 - closest_y2) <= alignment_tolerance
                    if grid_rows > 0
                    else True
                )

                # Calculate which grid columns/rows this element spans
                col_start = grid_lines_x.index(closest_x1) if x1_aligned else -1
                col_end = grid_lines_x.index(closest_x2) if x2_aligned else -1
                row_start = (
                    grid_lines_y.index(closest_y1)
                    if y1_aligned and grid_rows > 0
                    else -1
                )
                row_end = (
                    grid_lines_y.index(closest_y2)
                    if y2_aligned and grid_rows > 0
                    else -1
                )

                # Determine if element is grid-aligned
                grid_aligned = x1_aligned and x2_aligned and y1_aligned and y2_aligned

                element_results.append(
                    {
                        "name": e_name,
                        "region": {
                            "x1": e_x1,
                            "y1": e_y1,
                            "x2": e_x2,
                            "y2": e_y2,
                            "width": e_x2 - e_x1,
                            "height": e_y2 - e_y1,
                        },
                        "grid_alignment": {
                            "x1_aligned": x1_aligned,
                            "x2_aligned": x2_aligned,
                            "y1_aligned": y1_aligned,
                            "y2_aligned": y2_aligned,
                            "grid_aligned": grid_aligned,
                        },
                        "grid_position": {
                            "column_start": col_start,
                            "column_end": col_end,
                            "row_start": row_start,
                            "row_end": row_end,
                            "column_span": (
                                col_end - col_start
                                if col_start >= 0 and col_end >= 0
                                else 0
                            ),
                            "row_span": (
                                row_end - row_start
                                if row_start >= 0 and row_end >= 0
                                else 0
                            ),
                        },
                    }
                )

            # Create a visual representation with grid overlay
            result_img = img.copy()
            from PIL import ImageDraw

            draw = ImageDraw.Draw(result_img)

            # Draw grid lines
            for x in grid_lines_x:
                draw.line([(x, 0), (x, height)], fill="lightblue", width=1)

            if grid_rows > 0:
                for y in grid_lines_y:
                    draw.line([(0, y), (width, y)], fill="lightblue", width=1)

            # Draw margin boundaries
            draw.rectangle(
                [
                    (margin_size, margin_size),
                    (width - margin_size, height - margin_size),
                ],
                outline="green",
                width=2,
            )

            # Draw elements
            for i, element in enumerate(elements):
                e_x1 = max(0, element.get("x1", 0))
                e_y1 = max(0, element.get("y1", 0))
                e_x2 = min(width, element.get("x2", width))
                e_y2 = min(height, element.get("y2", height))

                # Use blue for grid-aligned elements, red for non-aligned
                result = element_results[i]
                color = "blue" if result["grid_alignment"]["grid_aligned"] else "red"
                draw.rectangle([(e_x1, e_y1), (e_x2, e_y2)], outline=color, width=2)

                # Draw label
                e_name = element.get("name", f"Element {i+1}")
                draw.text((e_x1, e_y1 - 10), e_name, fill=color)

            # Save the image locally
            import os
            import time

            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)

            # Generate a unique filename with timestamp
            timestamp = int(time.time())
            brand_name = data.get("brand_name", "unknown")
            image_filename = (
                f"{output_dir}/{brand_name}_layout_consistency_{timestamp}.png"
            )

            # Save the image
            result_img.save(image_filename)

            # Also convert to base64 for API response if needed
            buffer = BytesIO()
            result_img.save(buffer, format="PNG")
            result_img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            # Calculate overall layout consistency
            all_elements_grid_aligned = all(
                result["grid_alignment"]["grid_aligned"] for result in element_results
            )

            # Count how many elements are aligned
            aligned_count = sum(
                1
                for result in element_results
                if result["grid_alignment"]["grid_aligned"]
            )
            alignment_percentage = (
                (aligned_count / len(element_results)) * 100 if element_results else 0
            )

            return json.dumps(
                {
                    "grid_info": {
                        "columns": grid_columns,
                        "rows": grid_rows,
                        "gutter_size": gutter_size,
                        "margin_size": margin_size,
                        "column_width": round(column_width, 2),
                        "row_height": (
                            round(row_height, 2) if grid_rows > 0 else "flexible"
                        ),
                    },
                    "element_results": element_results,
                    "layout_consistency": {
                        "all_elements_grid_aligned": all_elements_grid_aligned,
                        "aligned_elements_count": aligned_count,
                        "total_elements": len(element_results),
                        "alignment_percentage": round(alignment_percentage, 2),
                    },
                    # "visualization_base64": result_img_base64,
                    # "visualization_file_path": image_filename,
                }
            )

    except Exception as e:
        return json.dumps({"error": f"Failed to analyze layout consistency: {str(e)}"})


async def check_image_clarity(data):
    """
    Analyze the clarity and sharpness of a specific region in an image.
    This tool checks if elements like logos, text, or other brand assets are displayed with sufficient clarity.
    """
    try:
        # Extract parameters
        region_coordinates = data.get("region_coordinates", "")
        element_type = data.get("element_type", "unknown")
        min_clarity_score = int(data.get("min_clarity_score", 80))  # Default to 80 if not provided

        # Get the image data
        image_base64 = data.get("image_base64")
        if not image_base64:
            return json.dumps({
                "error": "No image data provided"
            })

        # Parse region coordinates
        try:
            # Handle different coordinate formats
            if isinstance(region_coordinates, str):
                # Format: "x1,y1,x2,y2"
                coords = region_coordinates.split(",")
                if len(coords) == 4:
                    x1, y1, x2, y2 = map(int, coords)
                else:
                    return json.dumps({
                        "error": f"Invalid region_coordinates format: {region_coordinates}. Expected 'x1,y1,x2,y2'"
                    })
            else:
                # If coordinates are provided in a different format, handle accordingly
                return json.dumps({
                    "error": f"Unsupported region_coordinates format: {type(region_coordinates)}"
                })
        except Exception as coord_error:
            return json.dumps({
                "error": f"Error parsing region coordinates: {str(coord_error)}"
            })

        # Ensure the image is properly padded for base64 decoding
        padding_needed = len(image_base64) % 4
        if padding_needed != 0:
            image_base64 += "=" * (4 - padding_needed)

        # Decode the base64 image
        try:
            image_data = base64.b64decode(image_base64)
            from PIL import Image, ImageFilter
            import numpy as np
            from io import BytesIO

            # Open the image
            img = Image.open(BytesIO(image_data))

            # Crop to the region of interest
            region = img.crop((x1, y1, x2, y2))

            # Save the region for result
            buffer = BytesIO()
            region.save(buffer, format="PNG")
            region_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            # Calculate multiple clarity metrics for more accurate assessment

            # 1. Laplacian variance (higher variance = sharper image)
            np_region = np.array(region.convert("L"))  # Convert to grayscale numpy array
            laplacian = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]])
            conv = np.abs(np.convolve(np_region.flatten(), laplacian.flatten(), mode="same"))
            laplacian_variance = np.var(conv)

            # 2. Edge detection - more edges usually means sharper image
            edge_image = region.filter(ImageFilter.FIND_EDGES)
            edge_data = np.array(edge_image.convert("L"))
            edge_mean = np.mean(edge_data)

            # 3. High-frequency content analysis using FFT
            from scipy import fftpack
            f = np.fft.fft2(np_region)
            fshift = np.fft.fftshift(f)
            magnitude_spectrum = 20*np.log(np.abs(fshift))
            # Calculate high frequency energy (higher frequencies are further from center)
            h, w = magnitude_spectrum.shape
            center_y, center_x = h//2, w//2
            # Create a mask that weights pixels by distance from center
            y, x = np.ogrid[:h, :w]
            dist_from_center = np.sqrt((x - center_x)**2 + (y - center_y)**2)
            # Normalize distances
            max_dist = np.sqrt(center_x**2 + center_y**2)
            normalized_dist = dist_from_center / max_dist
            # Weight the magnitude spectrum by distance
            weighted_spectrum = magnitude_spectrum * normalized_dist
            high_freq_energy = np.sum(weighted_spectrum) / (h * w)

            # Combine metrics with appropriate weights
            # Adjust these weights based on testing with your specific images
            if element_type.lower() == "logo":
                # Logos need very high clarity - be more strict
                max_expected_variance = 400  # Lower threshold for logos
                edge_weight = 0.4
                laplacian_weight = 0.4
                high_freq_weight = 0.2

                # For logos, we need to be more strict about the minimum score
                if min_clarity_score < 85:
                    min_clarity_score = 85  # Override to ensure logos are very clear
            else:
                # Other elements can be slightly less strict
                max_expected_variance = 500
                edge_weight = 0.3
                laplacian_weight = 0.5
                high_freq_weight = 0.2

            # Calculate weighted clarity score (0-100)
            laplacian_score = min(100, int((laplacian_variance / max_expected_variance) * 100))
            edge_score = min(100, int((edge_mean / 50) * 100))  # Normalize to 0-100
            high_freq_score = min(100, int((high_freq_energy / 30) * 100))  # Normalize to 0-100

            clarity_score = int(
                laplacian_score * laplacian_weight +
                edge_score * edge_weight +
                high_freq_score * high_freq_weight
            )

            # Determine if the clarity meets the minimum requirement
            meets_requirement = clarity_score >= min_clarity_score

            # Prepare the result
            result = {
                "element_type": element_type,
                "region": f"({x1},{y1}) to ({x2},{y2})",
                "clarity_score": clarity_score,
                "min_required": min_clarity_score,
                "meets_requirement": meets_requirement,
                "assessment": "Clear" if meets_requirement else "Blurry",
                "detailed_metrics": {
                    "laplacian_score": laplacian_score,
                    "edge_detection_score": edge_score,
                    "high_frequency_score": high_freq_score
                },
                "region_image_base64": region_base64,
                "recommendations": []
            }

            # Add recommendations if clarity is insufficient
            if not meets_requirement:
                result["recommendations"].append("Increase the resolution of the image")
                result["recommendations"].append(f"Ensure the {element_type} is not obscured or blurred")
                if element_type.lower() == "logo":
                    result["recommendations"].append("⚠️ CRITICAL COMPLIANCE ISSUE: Logo blur detected")
                    result["recommendations"].append("Use the vector version of the logo if available")
                    result["recommendations"].append("Logo clarity is a mandatory brand requirement")
                    # Add a more prominent warning in the assessment
                    result["assessment"] = "⚠️ CRITICAL: Blurred Logo Detected"
                elif element_type.lower() == "text":
                    result["recommendations"].append("Increase the font size or use a clearer font")

            return json.dumps(result)

        except Exception as img_error:
            return json.dumps({
                "error": f"Error processing image: {str(img_error)}"
            })

    except Exception as e:
        return json.dumps({
            "error": f"Error in check_image_clarity: {str(e)}"
        })

async def attempt_completion(data):
    """Provide a final recommendation based on synthesized data."""
    result = data.get("result")
    if not result:
        return "Error: No result provided for completion."

    # Simulate a final recommendation
    recommendation = {
        "recommendation": result,
        "summary": "Based on analysis of brand guidelines and image content",
        "timestamp": "2025-03-19",
    }

    return json.dumps(recommendation)
