import aiohttp
import yt_dlp
from io import BytesIO
import requests
import cv2
import tempfile
import re
from datetime import datetime
import json
import json as main_json
from app.core.video_agent.video_tools import (
    get_tool_function,
)
import xmltodict
from app.core.agent.prompt import gemini_system_prompt
import numpy as np

# from google.genai import types # Removed google.genai specific types
# from google import genai # Removed google.genai client
from openai import OpenAI  # Added OpenAI client
import asyncio
import base64
import sys
import os
import shutil  # Added for directory cleanup
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Client Initialization (using OpenAI wrapper for Gemini)
client = OpenAI(
    api_key=os.getenv("GOOGLE_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

# Add the parent directory to the Python path
backend_dir = str(
    Path(__file__).resolve().parents[3]
)  # Go up 3 levels to reach the backend directory
if backend_dir not in sys.path:
    sys.path.append(backend_dir)


async def validate_video_file(file_path):
    """Validate a video file using OpenCV."""
    try:
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return False, "Could not open video file"

        # Try to read the first frame
        ret, frame = cap.read()
        if not ret or frame is None:
            cap.release()
            return False, "Could not read video frame"

        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Basic validation
        if fps <= 0 or frame_count <= 0:
            cap.release()
            return False, "Invalid video properties"

        cap.release()
        return True, None
    except Exception as e:
        return False, str(e)


async def download_youtube_video(url, temp_dir):
    """Download a video from YouTube using yt-dlp. Returns video_path."""
    try:
        ydl_opts = {
            # More flexible format selection
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": os.path.join(temp_dir, "%(title)s.%(ext)s"),
            "quiet": True,
            # Enhanced download options (REMOVED cookie handling - not viable on Render)
            "no_warnings": True,
            "no_color": True,
            "retries": 10,  # Retry on network errors
            "fragment_retries": 10,
            "ignoreerrors": True,  # Skip unavailable videos but check info below
            "socket_timeout": 30,  # Increase timeout
            "extractor_retries": 3,  # Retry extractor on failure
            "file_access_retries": 3,  # Retry file access
            # Additional options to bypass restrictions
            "nocheckcertificate": True,
            "extract_flat": "in_playlist",  # Helps avoid some age restrictions
            "youtube_include_dash_manifest": False,
            # User agent to avoid bot detection
            # Generic user agent
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Check if download was skipped due to errors (e.g., requires login)
            if (
                info is None
                or "_type" in info
                and info["_type"] == "playlist"
                and not info.get("entries")
            ):
                # Check if 'entries' is missing or empty for playlists, indicating failure
                raise Exception(
                    "yt-dlp failed to extract video info or download. Video might require login or be unavailable."
                )
            video_path = ydl.prepare_filename(info)

            # Verify the downloaded file exists and is not empty
            if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                # Verify file integrity using OpenCV
                is_valid, validation_error = await validate_video_file(video_path)
                if is_valid:
                    print(f"✅ YouTube video downloaded and verified: {video_path}")
                    return video_path  # Return only the path, temp_dir cleanup handled by caller
                else:
                    print(
                        f"❌ Downloaded file is not a valid video: {validation_error}"
                    )
                    # Clean up invalid file
                    try:
                        os.unlink(video_path)
                    except:
                        pass
                    raise Exception(
                        f"Invalid video file format after download: {validation_error}"
                    )
            else:
                # This might happen if ignoreerrors=True skipped the download
                print("❌ Video file is missing or empty after yt-dlp process.")
                raise Exception(
                    "Video download failed or was skipped by yt-dlp (possibly requires login)."
                )

    except Exception as e:
        # Catch specific yt-dlp errors if needed, otherwise re-raise
        print(f"❌ Error downloading YouTube video with yt-dlp: {str(e)}")
        raise e  # Re-raise the exception to be caught by download_video


async def download_direct_video(url):
    """Download a video directly using aiohttp. Returns video_path."""
    print(f"🎬 Attempting direct download from {url}")

    temp_file = None
    try:
        # Create a temporary file
        temp_fd, temp_path = tempfile.mkstemp(suffix=".mp4")
        os.close(temp_fd)
        temp_file = temp_path

        # Download the video with custom headers
        headers = {
            # Generic user agent
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(
                url, allow_redirects=True, timeout=60
            ) as response:  # Added timeout and redirects
                if response.status != 200:
                    raise Exception(f"Failed to download video: HTTP {response.status}")

                # Check content type for non-YouTube URLs
                content_type = response.headers.get("content-type", "")
                if not any(
                    t in content_type.lower()
                    for t in [
                        "video/",
                        "application/octet-stream",
                        "application/x-mpegurl",
                        "application/vnd.apple.mpegurl",
                    ]
                ):
                    raise Exception(
                        f"Invalid content type for direct download: {content_type}"
                    )

                # Get total size for progress tracking
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0

                with open(temp_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size and total_size > 0:
                                progress = (downloaded / total_size) * 100
                                print(
                                    f"📥 Download progress: {progress:.1f}%", end="\r"
                                )  # Use carriage return for progress
                            else:
                                print(
                                    f"📥 Downloaded {downloaded / (1024*1024):.2f} MB",
                                    end="\r",
                                )  # Show MB if no total size

                print("\n📥 Download complete.")  # Newline after progress

        # Validate the downloaded file
        print("🔍 Validating video file...")
        is_valid, error = await validate_video_file(temp_path)
        if not is_valid:
            raise Exception(f"Invalid video file after download: {error}")

        print(f"✅ Video successfully downloaded and validated: {temp_path}")
        return temp_path  # Return only the path, temp file cleanup handled by caller

    except Exception as e:
        # Clean up temp file if it exists and error occurred
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except:
                pass
        print(f"❌ Error in direct download: {str(e)}")
        raise Exception(f"Video download failed: {str(e)}")


async def download_video(url):
    """
    Download a video from a URL.
    Returns a tuple: (video_path, temp_dir_to_clean)
    temp_dir_to_clean will be None for direct downloads.

    Note: This function always returns a tuple (path, temp_dir) for consistency.
    """
    print(f"🎬 Downloading video from {url}")

    if "youtube.com" in url or "youtu.be" in url:
        # Create a temporary directory to store the video
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp()
            video_path = await download_youtube_video(url, temp_dir)
            return video_path, temp_dir  # Return path and the dir to clean later
        except Exception as e:
            # Clean up temp dir immediately if YouTube download fails
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
            print(f"❌ YouTube download failed: {str(e)}")
            raise Exception(f"Failed to download YouTube video: {str(e)}")
        # REMOVED finally block here - cleanup is now caller's responsibility
    else:
        # For non-YouTube URLs, use the direct download method
        temp_file_path = None
        try:
            temp_file_path = await download_direct_video(url)
            # For direct downloads, the temp file itself needs cleanup, not a dir
            return temp_file_path, None  # Return path and None for temp_dir
        except Exception as e:
            # Cleanup already handled within download_direct_video on error
            print(f"❌ Direct download failed for non-YouTube URL: {str(e)}")
            raise Exception(f"Failed to download video: {str(e)}")


def calculate_frame_similarity(frame1, frame2, threshold=0.8):
    """Calculate similarity between two frames using structural similarity index."""
    # Convert frames to grayscale for comparison
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

    # Resize images to a standard size for faster comparison
    size = (200, 200)
    gray1 = cv2.resize(gray1, size)
    gray2 = cv2.resize(gray2, size)

    # Calculate structural similarity index
    score = cv2.compareHist(
        cv2.calcHist([gray1], [0], None, [256], [0, 256]),
        cv2.calcHist([gray2], [0], None, [256], [0, 256]),
        cv2.HISTCMP_CORREL,
    )

    # Return the actual score and whether frames are similar
    is_similar = score > threshold
    return is_similar, score


async def extract_frames(video_path, initial_interval=0.1, similarity_threshold=0.95):
    """Maximum frame extraction for comprehensive compliance analysis"""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    frame_count = 0
    
    # Calculate total frames for progress reporting
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Processing video with {total_frames} total frames")
    
    # Determine optimal sampling rate based on video length
    # For compliance analysis, we want to capture frames frequently
    video_length = total_frames / fps if fps > 0 else 0
    
    # Use a fixed small interval for maximum frame capture
    # This ensures we don't miss any important brand elements
    fixed_interval = initial_interval  # Default to 0.1 seconds between frames
    
    last_timestamp = -1
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_count += 1
        timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
        
        # Progress reporting
        if frame_count % 100 == 0:
            progress = (frame_count / total_frames) * 100 if total_frames > 0 else 0
            print(f"Processed {frame_count}/{total_frames} frames ({progress:.1f}%)")
        
        # Capture frame if it's at least fixed_interval seconds from the last captured frame
        # This ensures we capture frames at regular intervals without missing anything
        if last_timestamp < 0 or (timestamp - last_timestamp) >= fixed_interval:
            # Encode and store frame
            _, buffer = cv2.imencode('.jpg', frame)
            frames.append({
                'timestamp': timestamp,
                'base64': base64.b64encode(buffer).decode('utf-8'),
                'frame_number': frame_count
            })
            last_timestamp = timestamp

    cap.release()
    return frames


def get_frames_by_timestamp(frames, timestamp):
    """
    Get all frames at the specified timestamp.

    Args:
        frames: List of frame dictionaries
        timestamp: The timestamp to find frames for

    Returns:
        A list of base64-encoded frames for the timestamp
    """
    # Find all frames that match the timestamp
    matching_frames = [
        frame["base64"] for frame in frames if frame["timestamp"] == timestamp
    ]

    # If no exact matches found, find the closest timestamp
    if not matching_frames:
        closest_timestamp = min(
            set(frame["timestamp"] for frame in frames),
            key=lambda x: abs(x - timestamp),
        )
        matching_frames = [
            frame["base64"]
            for frame in frames
            if frame["timestamp"] == closest_timestamp
        ]
        print(
            f"⚠️ Exact timestamp {timestamp} not found, using closest frames at timestamp {closest_timestamp}"
        )

    print(f"📊 Found {len(matching_frames)} frames for timestamp {timestamp}")
    return matching_frames


def get_frame_by_timestamp(frames, timestamp):
    """
    Get a single frame at the specified timestamp (for backward compatibility).

    This function returns just the first frame found at the timestamp.
    """
    frames_at_timestamp = get_frames_by_timestamp(frames, timestamp)
    return frames_at_timestamp[0] if frames_at_timestamp else None


async def generate():
    # Removed Vertex AI specific client initialization and credentials
    # Client is now initialized globally above

    video_url = "https://www.youtube.com/watch?v=9cPxh2DikIA"

    video_path = None
    temp_dir_to_clean = None  # For YouTube downloads
    temp_file_to_clean = None  # For direct downloads
    frames = []  # Initialize frames list

    try:
        # Download the video and extract frames
        video_path_tuple = await download_video(
            video_url
        )  # Returns (path, temp_dir or None)
        video_path = video_path_tuple[0]
        temp_dir_to_clean = video_path_tuple[1]
        if temp_dir_to_clean is None:  # It was a direct download
            temp_file_to_clean = video_path  # Mark the file itself for cleanup

        frames = await extract_frames(
            video_path, initial_interval=1, similarity_threshold=0.8
        )  # Pass only the path

        # Initialize empty frame_captions
        frame_captions = {"error": "Audio transcription disabled"}

        # --- Start Analysis ---
        # Instead of passing the video URL, we'll pass all the extracted frames
        model = "gemini-2.0-flash"

        # Define the sequence of analysis modes to run
        analysis_modes = [
            "visual",  # Start with visual analysis
            "brand_voice",  # Then analyze brand voice
            "tone",  # Then analyze tone
        ]

        # Store results from each analysis
        all_analysis_results = {}

        # Run each analysis mode in sequence
        for analysis_mode in analysis_modes:
            print(f"\n{'='*50}")
            print(f"🔍 Starting {analysis_mode.upper()} analysis")
            print(f"{'='*50}")

            # Create messages list in OpenAI format
            messages = []

            # Add system prompt (if not already added or handled differently)
            # Assuming gemini_system_prompt is the main system instruction
            messages.append({"role": "system", "content": gemini_system_prompt})

            # Prepare user message content (will include text and images)
            user_content = []

            # Set instruction based on current analysis mode
            instruction_text = ""
            if analysis_mode == "visual":
                # instruction = ( # Removed leftover line causing syntax error
                instruction_text = (
                    "Check the compliance of this video for logo usage, color and brand compliance. "
                    f"I'm providing {len(frames)} frames from a {len(set(frame['timestamp'] for frame in frames))} second video"
                )
                if "error" not in frame_captions:
                    instruction_text += (
                        f" along with audio transcription for each timestamp."
                    )
                else:
                    instruction_text += "."
            elif analysis_mode == "brand_voice":
                instruction_text = (
                    "Analyze the BRAND VOICE of this video. Focus specifically on the overall personality and style. "
                    "Check if the tone is consistent with brand guidelines and if the personality expressed aligns with brand values. "
                    f"I'm providing {len(frames)} frames from a {len(set(frame['timestamp'] for frame in frames))} second video"
                )
                if "error" not in frame_captions:
                    instruction_text += (
                        f" along with audio transcription for each timestamp."
                    )
                else:
                    instruction_text += "."
            elif analysis_mode == "tone":
                instruction_text = (
                    "Analyze the TONE OF VOICE in this video. Focus specifically on mood variations based on context. "
                    "Check if the emotional tone shifts appropriately for different scenes and if these shifts align with brand guidelines. "
                    f"I'm providing {len(frames)} frames from a {len(set(frame['timestamp'] for frame in frames))} second video"
                )
                if "error" not in frame_captions:
                    instruction_text += (
                        f" along with audio transcription for each timestamp."
                    )
                else:
                    instruction_text += "."

            user_content.append({"type": "text", "text": instruction_text})

            # Add transcription data if available and valid
            if "error" not in frame_captions and frame_captions.get("frame_captions"):
                transcription_text = "Video Transcription by Timestamp:\n"
                transcription_items = []
                for timestamp, caption_data in frame_captions.get(
                    "frame_captions", {}
                ).items():
                    if caption_data.get("text"):
                        transcription_items.append(
                            f"[{timestamp}s]: {caption_data['text']}"
                        )

                if transcription_items:
                    transcription_text += "\n".join(transcription_items)
                    user_content.append({"type": "text", "text": transcription_text})
                    print("📝 Added transcription data to API request")

            # Add all frames as image parts
            frame_count = len(frames)
            for i, frame_data in enumerate(frames):
                # Add image part using base64 data URI scheme
                user_content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{frame_data['base64']}"
                        },
                    }
                )
                print(
                    f"🖼️ Added frame {i+1}/{frame_count} at timestamp {frame_data['timestamp']} to API request"
                )

            # Add the user message to the messages list
            messages.append({"role": "user", "content": user_content})

            # Removed generate_content_config - parameters are passed directly to create()

            # Store the final result for this analysis mode
            analysis_result = None

            # Process loop for this analysis mode
            while True:
                final_text = ""

                print(f"\n{'='*50}")
                print(
                    f"🚀 Streaming Content for {analysis_mode.upper()} - Started at {datetime.now().strftime('%H:%M:%S')}"
                )
                print(f"{'='*50}")

                # Stream content and build text with retry logic
                max_retries = 3
                retry_count = 0
                streaming_successful = False

                while retry_count < max_retries and not streaming_successful:
                    try:
                        # Use client.chat.completions.create for streaming
                        response_stream = client.chat.completions.create(
                            model=model,
                            messages=messages,  # Pass the constructed messages list
                            stream=True,
                            # Pass other parameters directly if needed (e.g., temperature, max_tokens)
                            # temperature=1, # Example
                            max_tokens=8192,  # Example
                            # stop=["</tool_code>"] # Example stop sequence if needed
                        )

                        for chunk in response_stream:
                            if (
                                chunk.choices
                                and chunk.choices[0].delta
                                and chunk.choices[0].delta.content
                            ):
                                chunk_text = chunk.choices[0].delta.content
                                print(f"📦 Chunk received: {chunk_text}")
                                final_text += chunk_text
                            # Check for finish reason (OpenAI format)
                            if chunk.choices and chunk.choices[0].finish_reason:
                                print(
                                    f"🏁 Stream finished with reason: {chunk.choices[0].finish_reason}"
                                )
                                break  # Exit inner loop on finish

                        streaming_successful = (
                            True  # Assume success if loop completes or finishes cleanly
                        )

                    except Exception as e:
                        retry_count += 1
                        print(f"\nStream Error Type: {type(e).__name__}")  # Debugging
                        print(f"Stream Error Args: {e.args}")  # Debugging
                        if retry_count < max_retries:
                            print(
                                f"\n⚠️ Streaming error (attempt {retry_count}/{max_retries}): {str(e)}"
                            )
                            print(f"🔄 Retrying in 2 seconds...")
                            await asyncio.sleep(2)  # Wait before retrying
                            final_text = ""  # Reset final_text for the retry
                        else:
                            print(
                                f"\n❌ Streaming failed after {max_retries} attempts: {str(e)}"
                            )
                            raise  # Re-raise the exception after max retries

                # Sanitize the final text
                final_text = final_text.strip()

                print(f"\n{'-'*50}")
                print(
                    f"✅ Streaming Complete for {analysis_mode.upper()} - Processing Final Text"
                )
                print(f"{'-'*50}")
                print(f"📄 Raw Response (length: {len(final_text)}):\n{final_text}")
                print(
                    f"🔢 Raw Bytes (first 200): {repr(final_text.encode('utf-8')[:200])}"
                )

                # Process the complete text after streaming
                try:
                    # Reset variables for each iteration to prevent using stale data
                    xml_dict = None
                    json_tool_name = None
                    content_to_process = None
                    is_xml = False

                    # Method 1: Check if XML is wrapped in code blocks
                    if (
                        "```xml" in final_text
                        and "```" in final_text.split("```xml")[1]
                    ):
                        try:
                            xml_content = (
                                final_text.split("```xml")[1].split("```")[0].strip()
                            )
                            content_to_process = xml_content
                            xml_dict = xmltodict.parse(xml_content)
                            is_xml = True

                            print(f"\n{'='*50}")
                            print("🔍 XML Processing Results (With Code Block Markers)")
                            print(f"{'='*50}")
                            print(f"📋 Extracted XML Content:\n{xml_content}")
                            print(
                                f"🧩 Parsed XML Content:\n{main_json.dumps(xml_dict, indent=2)}"
                            )

                            json_tool_name = list(xml_dict.keys())[0]
                        except Exception as xml_error:
                            print(
                                f"⚠️ Error parsing XML from code blocks: {str(xml_error)}"
                            )
                            is_xml = False

                    # Method 2: If Method 1 failed, try to find XML tags with regex in the raw text
                    if not is_xml:
                        print(f"🔎 Attempting to extract XML directly from raw text")

                        # Look for XML-like patterns in the text
                        # First, try to find a complete XML structure with a root tag
                        xml_pattern = r"<([a-zA-Z0-9_]+)>(.*?)</\1>"
                        xml_matches = re.findall(xml_pattern, final_text, re.DOTALL)

                        if xml_matches:
                            try:
                                # Reconstruct XML from the first match
                                root_tag, content = xml_matches[0]
                                reconstructed_xml = (
                                    f"<{root_tag}>{content}</{root_tag}>"
                                )

                                xml_dict = xmltodict.parse(reconstructed_xml)
                                is_xml = True
                                content_to_process = reconstructed_xml
                                json_tool_name = root_tag

                                print(f"\n{'='*50}")
                                print("🔍 XML Processing Results (With Direct Regex)")
                                print(f"{'='*50}")
                                print(f"📋 Extracted XML Content:\n{reconstructed_xml}")
                                print(
                                    f"🧩 Parsed XML Content:\n{main_json.dumps(xml_dict, indent=2)}"
                                )
                            except Exception as regex_xml_error:
                                print(
                                    f"⚠️ Error parsing XML with direct regex: {str(regex_xml_error)}"
                                )
                                is_xml = False

                    # Method 3: Try to find XML in code blocks with a more flexible approach
                    if not is_xml:
                        print(
                            f"🔎 Attempting to extract XML from code blocks with flexible regex"
                        )
                        # Look for content between any code block markers that might contain XML
                        code_block_pattern = r"```(?:xml)?\s*(.*?)```"
                        code_blocks = re.findall(
                            code_block_pattern, final_text, re.DOTALL
                        )

                        for block in code_blocks:
                            try:
                                # Try to parse each block as XML
                                block = block.strip()
                                if block and block[0] == "<" and block[-1] == ">":
                                    xml_dict = xmltodict.parse(block)
                                    is_xml = True
                                    content_to_process = block
                                    json_tool_name = list(xml_dict.keys())[0]

                                    print(f"\n{'='*50}")
                                    print(
                                        "🔍 XML Processing Results (From Code Block with Regex)"
                                    )
                                    print(f"{'='*50}")
                                    print(f"📋 Extracted XML Content:\n{block}")
                                    print(
                                        f"🧩 Parsed XML Content:\n{main_json.dumps(xml_dict, indent=2)}"
                                    )
                                    break
                            except Exception as block_error:
                                print(
                                    f"⚠️ Error parsing potential XML block: {str(block_error)}"
                                )
                                continue

                    if not is_xml:
                        print("❌ No valid XML found in the response")
                        continue

                    # Only proceed with tool execution if we have valid XML data
                    if is_xml and xml_dict and json_tool_name:
                        print(f"\n🛠️ Tool Information:")
                        print(f"📌 Tool Name: {json_tool_name}")
                        print(
                            f"📊 Processed Data:\n{main_json.dumps(xml_dict, indent=2)}"
                        )

                        # Add image_base64 to tool input if it's a video analysis tool and has a timestamp
                        tool_input = xml_dict[json_tool_name]

                        # Check if this is a video tool that requires a timestamp
                        if (
                            json_tool_name
                            in [
                                "get_video_color_scheme",
                                "get_video_fonts",
                                "get_region_color_scheme",
                                "check_color_contrast",
                                "check_video_frame_specs",
                                "check_element_placement",
                            ]
                            and "timestamp" in tool_input
                        ):
                            # Get the timestamp and corresponding frames
                            timestamp = int(tool_input["timestamp"])
                            frames_base64 = get_frames_by_timestamp(frames, timestamp)

                            # Add the base64 images to the tool input
                            if len(frames_base64) == 1:
                                # For backward compatibility with tools that expect a single image
                                tool_input["image_base64"] = frames_base64[0]
                                print(
                                    f"🖼️ Added 1 frame at timestamp {timestamp} to tool input"
                                )
                            else:
                                # For tools that can handle multiple images
                                tool_input["images_base64"] = frames_base64
                                tool_input["image_base64"] = frames_base64[
                                    0
                                ]  # For backward compatibility
                                print(
                                    f"🖼️ Added {len(frames_base64)} frames at timestamp {timestamp} to tool input"
                                )

                        # Execute tool function
                        tool_function = get_tool_function(json_tool_name)
                        tool_result = await tool_function(tool_input)
                        tool_result_json = main_json.loads(
                            tool_result
                        )  # Corrected indentation

                        print(f"\n{'='*50}")
                        print("⚙️ Tool Execution Results")
                        print(f"{'='*50}")
                        print(f"Tool Result: {tool_result}")  # Log tool result

                        # Update messages list (OpenAI format)
                        # 1. Add the assistant's response (which contained the tool call)
                        messages.append(
                            {"role": "assistant", "content": content_to_process}
                        )  # Assuming content_to_process holds the raw XML tool call

                        # 2. Add the tool result message
                        # Note: OpenAI expects tool calls/results differently, often via function calling mechanism.
                        # This simulates adding a user message with the tool output for the next turn.
                        # A more robust implementation might use OpenAI's tool/function calling features if the wrapper supports it.
                        # For now, adding as a user message containing the result string.
                        messages.append(
                            {"role": "user", "content": f"Tool Result:\n{tool_result}"}
                        )

                        # If the tool result included an image, we might need a way to represent that.
                        # OpenAI's standard message format doesn't directly support tool results with images.
                        # We'll skip adding the image back into the conversation history for now.
                        # if tool_result_json.get("base64"):
                        #    print("⚠️ Image in tool result - cannot add back to OpenAI message history directly.")

                        if json_tool_name == "attempt_completion":
                            print(f"\n{'='*50}")
                            print(
                                f"🏁 {analysis_mode.upper()} Analysis Complete: 'attempt_completion' tool detected"
                            )
                            print(f"{'='*50}")

                            # Store the final result for this analysis mode
                            if "result" in tool_input:
                                all_analysis_results[analysis_mode] = tool_input[
                                    "result"
                                ]

                            # Break out of the while loop for this analysis mode
                            break

                except Exception as e:
                    print(f"\n{'-'*50}")
                    print(f"❌ Error Processing Content: {str(e)}")
                    print(f"📄 Raw Final Text:\n{final_text}")
                    print(f"🔢 Raw Bytes (full): {repr(final_text.encode('utf-8'))}")
                    print(f"{'-'*50}")
                    continue

            # End of while loop for this analysis mode

        # End of for loop for all analysis modes

        print(f"\n{'='*50}")
        print("🎉 All analyses completed!")
        print(f"{'='*50}")

        # Create a directory to store analysis results
        results_dir = os.path.join(os.getcwd(), "video_analysis_results")
        os.makedirs(results_dir, exist_ok=True)

        # Create a timestamp for the filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Extract video ID or name from URL
        video_id = (
            video_url.split("=")[-1] if "=" in video_url else video_url.split("/")[-1]
        )

        #

        # Create a metadata object with information about the analysis
        metadata = {
            "video_url": video_url,
            "video_id": video_id,
            "analysis_timestamp": timestamp,
            "analysis_modes": analysis_modes,
            "frames_analyzed": len(frames),
            "video_duration_seconds": len(set(frame["timestamp"] for frame in frames)),
            "transcription_available": "error" not in frame_captions,
        }

        # Combine metadata with analysis results
        full_results = {"metadata": metadata, "results": all_analysis_results}

        # Save results to a JSON file
        results_filename = f"{video_id}_{timestamp}_analysis.json"
        results_filepath = os.path.join(results_dir, results_filename)

        with open(results_filepath, "w") as f:
            json.dump(full_results, f, indent=2)

        print(f"\n📊 Analysis results saved to: {results_filepath}")

        # Return the results and filepath
        return {"results": all_analysis_results, "filepath": results_filepath}

    finally:
        # --- Final Cleanup with Debugging ---
        print(f"--- Starting Cleanup ---")
        print(f"Debug: video_path = {repr(video_path)} (type: {type(video_path)})")
        print(
            f"Debug: temp_dir_to_clean = {repr(temp_dir_to_clean)} (type: {type(temp_dir_to_clean)})"
        )
        print(
            f"Debug: temp_file_to_clean = {repr(temp_file_to_clean)} (type: {type(temp_file_to_clean)})"
        )

        # Clean up the temporary directory for YouTube downloads
        if temp_dir_to_clean:
            print(
                f"Cleanup Check: temp_dir_to_clean = {repr(temp_dir_to_clean)} (type: {type(temp_dir_to_clean)})"
            )
            if isinstance(temp_dir_to_clean, str) and os.path.exists(temp_dir_to_clean):
                try:
                    shutil.rmtree(temp_dir_to_clean)
                    print(f"🧹 Cleaned up temporary directory {temp_dir_to_clean}")
                except Exception as cleanup_e:
                    print(
                        f"⚠️ Could not remove temporary directory {temp_dir_to_clean}: {str(cleanup_e)}"
                    )
            elif not isinstance(temp_dir_to_clean, str):
                print(f"⚠️ Cleanup Error: temp_dir_to_clean is not a string!")

        # Clean up the temporary file for direct downloads
        elif temp_file_to_clean:
            print(
                f"Cleanup Check: temp_file_to_clean = {repr(temp_file_to_clean)} (type: {type(temp_file_to_clean)})"
            )
            if isinstance(temp_file_to_clean, str) and os.path.exists(
                temp_file_to_clean
            ):
                try:
                    os.unlink(temp_file_to_clean)
                    print(f"🧹 Cleaned up temporary file {temp_file_to_clean}")
                except Exception as cleanup_e:
                    print(
                        f"⚠️ Could not remove temporary file {temp_file_to_clean}: {str(cleanup_e)}"
                    )
            elif not isinstance(temp_file_to_clean, str):
                print(f"⚠️ Cleanup Error: temp_file_to_clean is not a string!")

        # If video_path exists but wasn't marked for specific cleanup (edge case, should not happen often with new logic)
        elif video_path:
            print(
                f"Cleanup Check (Edge Case): video_path = {repr(video_path)} (type: {type(video_path)})"
            )
            if isinstance(video_path, str) and os.path.exists(video_path):
                try:
                    os.unlink(video_path)
                    print(f"🧹 Cleaned up remaining video file {video_path}")
                except Exception as cleanup_e:
                    print(
                        f"⚠️ Could not remove remaining video file {video_path}: {str(cleanup_e)}"
                    )
            elif not isinstance(video_path, str):
                print(f"⚠️ Cleanup Error: video_path is not a string!")
        print(f"--- Finished Cleanup ---")


if __name__ == "__main__":
    asyncio.run(generate())
