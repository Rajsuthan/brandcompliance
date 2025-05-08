from io import BytesIO
import sys
import os
import tempfile
import asyncio
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Add the parent directory to the Python path
backend_dir = str(
    Path(__file__).resolve().parents[3]
)  # Go up 3 levels to reach the backend directory
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from PIL import Image
import base64
import json
import requests

# Load environment variables
load_dotenv()

# (Removed circular import of get_tool_function from app.core.agent.tools)

# If you need to map tool names to functions, do it in app.core.agent.tools only.


async def get_video_color_scheme(data):
    """
    Get the color scheme of the video frame(s) at the specified timestamp.
    Handles both single frame and multiple frames.
    """
    # Log all keys in the data dictionary
    print(f"\033[93m[DEBUG] get_video_color_scheme received keys: {list(data.keys())}\033[0m")

    # Log the values (truncated) for each key
    for key, value in data.items():
        if key in ["images_base64", "image_base64"]:
            if isinstance(value, list):
                print(f"\033[93m[DEBUG] {key}: List with {len(value)} items\033[0m")
                if value and len(value) > 0:
                    first_item = value[0]
                    print(f"\033[93m[DEBUG] {key}[0] (first 50 chars): {str(first_item)[:50]}...\033[0m")
            else:
                print(f"\033[93m[DEBUG] {key} (first 50 chars): {str(value)[:50]}...\033[0m")
        else:
            print(f"\033[93m[DEBUG] {key}: {value}\033[0m")

    timestamp = data.get("timestamp", 0)

    # Check if we have multiple frames or a single frame
    images_base64 = data.get("images_base64", [])
    if not images_base64:
        # Fall back to single image for backward compatibility
        single_image = data.get("image_base64")
        if single_image:
            print(f"\033[93m[DEBUG] Using single image_base64 (length: {len(single_image)})\033[0m")
            images_base64 = [single_image]

    # Check if we have any frames to process
    if not images_base64:
        print(f"\033[91m[ERROR] No images provided for the video frame(s). Data keys: {list(data.keys())}\033[0m")
        return json.dumps({"error": "No images provided for the video frame(s)."})

    try:
        # Process all frames and collect their color palettes
        all_colors = set()
        frame_palettes = []

        for i, image_base64 in enumerate(images_base64):
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
                    print(f"No colors found in frame {i} at timestamp {timestamp}")
                    continue

                # Convert RGB tuples to hex format
                frame_colors = [
                    f"#{r:02x}{g:02x}{b:02x}" for count, (r, g, b) in colors
                ]

                # Add to the overall set of colors
                all_colors.update(frame_colors)

                # Store this frame's palette
                frame_palettes.append(
                    {
                        "frame_index": i,
                        "color_palette": frame_colors[
                            :10
                        ],  # Limit to 10 colors per frame
                    }
                )

        if not all_colors:
            return json.dumps({"error": "No colors found in any video frames."})

        # Convert the set to a list and limit to 10 colors for the overall palette
        color_palette = list(all_colors)[:10]

        # Create the response with both overall palette and individual frame palettes
        response_data = {
            "timestamp": timestamp,
            "color_palette": color_palette,  # Overall palette across all frames
            "frame_count": len(images_base64),
            "frame_palettes": frame_palettes if len(images_base64) > 1 else None,
        }

        response = json.dumps(response_data)
        print(f"Returning: {response}")
        return response

    except Exception as e:
        response = json.dumps({"error": f"Failed to process video frame(s): {str(e)}"})
        print(f"Returning: {response}")
        return response


async def get_video_fonts(data):
    """
    Identify fonts used in the video frame(s) at the specified timestamp.
    Handles both single frame and multiple frames.
    """
    timestamp = data.get("timestamp", 0)

    # Check if we have multiple frames or a single frame
    images_base64 = data.get("images_base64", [])
    if not images_base64:
        # Fall back to single image for backward compatibility
        single_image = data.get("image_base64")
        if single_image:
            images_base64 = [single_image]

    # Check if we have any frames to process
    if not images_base64:
        return json.dumps({"error": "No images provided for the video frame(s)."})

    try:
        # Get API key from environment variables
        api_key = os.getenv("WHATFONTIS_API_KEY")
        url = "https://www.whatfontis.com/api2/"

        # Process all frames and collect their font data
        all_fonts = []
        frame_fonts = []

        for i, image_base64 in enumerate(images_base64):
            # Ensure correct padding for base64 string
            padding_needed = len(image_base64) % 4
            if padding_needed != 0:
                image_base64 += "=" * (4 - padding_needed)  # Add padding if necessary

            # Prepare the API request
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

                # Add to the overall list of fonts
                if isinstance(font_data, list):
                    all_fonts.extend(font_data)

                    # Store this frame's fonts
                    frame_fonts.append(
                        {"frame_index": i, "fonts": font_data, "count": len(font_data)}
                    )
                else:
                    print(f"No valid font data for frame {i} at timestamp {timestamp}")
            else:
                print(
                    f"API request failed for frame {i}: {response.status_code} - {response.text}"
                )
                frame_fonts.append(
                    {
                        "frame_index": i,
                        "error": f"API request failed with status code {response.status_code}",
                        "message": response.text,
                    }
                )

        # Create the response with both overall fonts and individual frame fonts
        response_data = {
            "timestamp": timestamp,
            "fonts": all_fonts,  # All fonts across all frames
            "count": len(all_fonts),
            "frame_count": len(images_base64),
            "frame_fonts": frame_fonts if len(images_base64) > 1 else None,
        }

        response = json.dumps(response_data)
        print(f"Returning: {response}")
        return response

    except Exception as e:
        response = json.dumps(
            {
                "timestamp": timestamp,
                "error": f"Failed to process video frame(s) or identify fonts: {str(e)}",
            }
        )
        print(f"Returning: {response}")
        return response


async def check_video_frame_specs(data):
    """
    Analyze the video frame specifications at the specified timestamp for compliance with brand guidelines.
    Handles both single frame and multiple frames.
    """
    timestamp = data.get("timestamp", 0)
    required_width = data.get("required_width", 0)
    required_height = data.get("required_height", 0)
    min_resolution = data.get("min_resolution", 0)
    aspect_ratio = data.get("aspect_ratio", "any")

    # Check if we have multiple frames or a single frame
    images_base64 = data.get("images_base64", [])
    if not images_base64:
        # Fall back to single image for backward compatibility
        single_image = data.get("image_base64")
        if single_image:
            images_base64 = [single_image]

    # Check if we have any frames to process
    if not images_base64:
        return json.dumps({"error": "No images provided for the video frame(s)."})

    try:
        # Process all frames and collect their specifications
        frame_specs = []
        all_compliant = True

        # Helper function to calculate GCD for aspect ratio
        def gcd(a, b):
            """Calculate the Greatest Common Divisor of a and b."""
            while b:
                a, b = b, a % b
            return a

        for i, image_base64 in enumerate(images_base64):
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

                # Calculate the GCD to simplify the ratio
                divisor = gcd(width, height)
                simplified_ratio = f"{width // divisor}:{height // divisor}"

                # Check if dimensions match requirements
                width_compliant = required_width == 0 or width == required_width
                height_compliant = required_height == 0 or height == required_height
                resolution_compliant = (
                    min_resolution == 0 or resolution >= min_resolution
                )

                # Check aspect ratio compliance
                aspect_ratio_compliant = (
                    aspect_ratio == "any" or simplified_ratio == aspect_ratio
                )

                # Compile compliance results for this frame
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

                # Overall compliance for this frame
                frame_compliant = all(
                    [
                        width_compliant,
                        height_compliant,
                        resolution_compliant,
                        aspect_ratio_compliant,
                    ]
                )

                # Update overall compliance
                all_compliant = all_compliant and frame_compliant

                # Add this frame's specs to the list
                frame_specs.append(
                    {
                        "frame_index": i,
                        "specs": {
                            "width": width,
                            "height": height,
                            "resolution": resolution,
                            "aspect_ratio": simplified_ratio,
                            "file_size_kb": round(file_size_kb, 2),
                        },
                        "compliance_results": compliance_results,
                        "compliant": frame_compliant,
                    }
                )

        # Create the response with both overall compliance and individual frame specs
        response_data = {
            "timestamp": timestamp,
            "frame_count": len(images_base64),
            "overall_compliant": all_compliant,
            "frame_specs": (
                frame_specs if len(images_base64) > 1 else frame_specs[0]["specs"]
            ),
            "compliance_results": (
                frame_specs[0]["compliance_results"]
                if len(images_base64) == 1
                else None
            ),
        }

        response = json.dumps(response_data)
        print(f"Returning: {response}")
        return response

    except Exception as e:
        response = json.dumps(
            {
                "timestamp": timestamp,
                "error": f"Failed to analyze video frame specifications: {str(e)}",
            }
        )
        print(f"Returning: {response}")
        return response


async def extract_verbal_content(data):
    """
    Extract all verbal content from video (both spoken and displayed text).
    This tool uses OCR to extract text visible in frames.
    """
    # Log all keys in the data dictionary
    print(f"\033[93m[DEBUG] extract_verbal_content received keys: {list(data.keys())}\033[0m")

    # Log the values (truncated) for each key
    for key, value in data.items():
        if key in ["images_base64", "image_base64"]:
            if isinstance(value, list):
                print(f"\033[93m[DEBUG] {key}: List with {len(value)} items\033[0m")
                if value and len(value) > 0:
                    first_item = value[0]
                    print(f"\033[93m[DEBUG] {key}[0] (first 50 chars): {str(first_item)[:50]}...\033[0m")
            else:
                print(f"\033[93m[DEBUG] {key} (first 50 chars): {str(value)[:50]}...\033[0m")
        else:
            print(f"\033[93m[DEBUG] {key}: {value}\033[0m")

    timestamps = data.get("timestamps", [])

    # If no specific timestamps provided, use all available timestamps
    if not timestamps:
        # Try to get all frames
        all_frames = data.get("all_frames", {})
        if all_frames:
            timestamps = list(all_frames.keys())

    # If still no timestamps, check if we have a single timestamp
    if not timestamps:
        timestamp = data.get("timestamp", 0)
        timestamps = [timestamp]

    print(f"\033[93m[DEBUG] Processing timestamps: {timestamps}\033[0m")

    try:
        # Import necessary libraries for OCR
        import cv2
        import numpy as np
        import pytesseract

        # Check if pytesseract is installed and configured
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            return json.dumps(
                {
                    "error": f"Tesseract OCR not properly installed or configured: {str(e)}",
                    "text_content": "Unable to extract text due to missing OCR dependencies.",
                }
            )

        # Process frames for all timestamps
        all_text = []
        timestamp_texts = {}

        for timestamp in timestamps:
            # Get the frames for this timestamp
            images_base64 = data.get(f"images_base64_{timestamp}", [])

            # If no specific key for this timestamp, try to get from the main data
            if not images_base64 and timestamp == timestamps[0]:
                images_base64 = data.get("images_base64", [])

            # If still no frames, try the single image
            if not images_base64:
                single_image = data.get(f"image_base64_{timestamp}")
                if not single_image and timestamp == timestamps[0]:
                    single_image = data.get("image_base64")

                if single_image:
                    images_base64 = [single_image]

            # If we have frames for this timestamp, process them
            if images_base64:
                frame_texts = []

                for i, image_base64 in enumerate(images_base64):
                    # Ensure correct padding for base64 string
                    padding_needed = len(image_base64) % 4
                    if padding_needed != 0:
                        image_base64 += "=" * (
                            4 - padding_needed
                        )  # Add padding if necessary

                    # Decode the base64 string into binary data
                    image_data = base64.b64decode(image_base64)

                    # Convert to OpenCV format
                    nparr = np.frombuffer(image_data, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                    # Preprocess image for better OCR results
                    # Convert to grayscale
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

                    # Apply thresholding to isolate text
                    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)

                    # Apply some noise reduction
                    kernel = np.ones((1, 1), np.uint8)
                    thresh = cv2.dilate(thresh, kernel, iterations=1)
                    thresh = cv2.erode(thresh, kernel, iterations=1)

                    # Extract text using pytesseract
                    text = pytesseract.image_to_string(thresh)

                    # Clean up the text
                    text = text.strip()

                    if text:
                        frame_texts.append(
                            {
                                "frame_index": i,
                                "text": text,
                                "word_count": len(text.split()),
                                "character_count": len(text),
                            }
                        )
                        all_text.append(text)

                # Store texts for this timestamp
                timestamp_texts[str(timestamp)] = {
                    "frame_count": len(images_base64),
                    "text_found_in_frames": len(frame_texts),
                    "frame_texts": frame_texts,
                    "combined_text": " ".join([item["text"] for item in frame_texts]),
                }

        # Combine all text and analyze
        combined_text = " ".join(all_text)

        # Basic text analysis
        word_count = len(combined_text.split())
        character_count = len(combined_text)

        # Create the response
        response_data = {
            "timestamps_analyzed": timestamps,
            "total_frames_analyzed": sum(
                data["frame_count"] for data in timestamp_texts.values()
            ),
            "total_text_found_in_frames": sum(
                data["text_found_in_frames"] for data in timestamp_texts.values()
            ),
            "timestamp_texts": timestamp_texts,
            "combined_text": combined_text,
            "word_count": word_count,
            "character_count": character_count,
            "has_text": word_count > 0,
        }

        response = json.dumps(response_data)
        print(f"Returning verbal content analysis for {len(timestamps)} timestamps")
        return response

    except Exception as e:
        response = json.dumps(
            {
                "error": f"Failed to extract verbal content: {str(e)}",
                "timestamps": timestamps,
            }
        )
        print(f"Error in verbal content extraction: {str(e)}")
        return response
