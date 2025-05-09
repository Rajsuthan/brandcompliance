import cv2
import re
from datetime import datetime
import json
import json as main_json
from app.core.agent.tools import get_tool_function
import xmltodict
from app.core.agent.prompt import gemini_system_prompt
import numpy as np
from openai import OpenAI  # Gemini via OpenAI wrapper
import asyncio
import base64
import sys
import os
from dotenv import load_dotenv
from pathlib import Path
import hashlib
import time

# Load environment variables
load_dotenv()

# Client Initialization (Gemini only)
client = OpenAI(
    api_key=os.getenv("GOOGLE_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

# Add the parent directory to the Python path
backend_dir = str(
    Path(__file__).resolve().parents[3]
)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

async def validate_video_file(file_path):
    """Validate a video file using OpenCV."""
    try:
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return False, "Could not open video file"
        ret, frame = cap.read()
        if not ret or frame is None:
            cap.release()
            return False, "Could not read video frame"
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if fps <= 0 or frame_count <= 0:
            cap.release()
            return False, "Invalid video properties"
        cap.release()
        return True, None
    except Exception as e:
        return False, str(e)

def calculate_frame_similarity(frame1, frame2, threshold=0.5):
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    size = (200, 200)
    gray1 = cv2.resize(gray1, size)
    gray2 = cv2.resize(gray2, size)
    score = cv2.compareHist(
        cv2.calcHist([gray1], [0], None, [256], [0, 256]),
        cv2.calcHist([gray2], [0], None, [256], [0, 256]),
        cv2.HISTCMP_CORREL,
    )
    is_similar = score > threshold
    return is_similar, score

async def extract_frames(video_path, initial_interval=0.1, similarity_threshold=0.95):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    frame_count = 0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Processing video with {total_frames} total frames")
    video_length = total_frames / fps if fps > 0 else 0
    fixed_interval = initial_interval
    last_timestamp = -1
    prev_frame = None
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
        if frame_count % 100 == 0:
            progress = (frame_count / total_frames) * 100 if total_frames > 0 else 0
            print(f"Processed {frame_count}/{total_frames} frames ({progress:.1f}%)")
        if last_timestamp < 0 or (timestamp - last_timestamp) >= fixed_interval:
            is_unique = True
            if prev_frame is not None:
                is_similar, score = calculate_frame_similarity(prev_frame, frame, threshold=0.5)
                if is_similar:
                    is_unique = False
            if is_unique:
                # Compress the image by reducing JPEG quality to 70% (30% compression)
                encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
                _, buffer = cv2.imencode('.jpg', frame, encode_params)
                base64_data = base64.b64encode(buffer).decode('utf-8')
                frames.append({
                    'timestamp': timestamp,
                    'base64': base64_data,
                    'image_data': base64_data,  # Add image_data key for OpenRouterAgent
                    'frame_number': frame_count
                })
                prev_frame = frame
            last_timestamp = timestamp
    cap.release()
    return frames

def get_frames_by_timestamp(frames, timestamp):
    matching_frames = [
        frame["base64"] for frame in frames if frame["timestamp"] == timestamp
    ]
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
    frames_at_timestamp = get_frames_by_timestamp(frames, timestamp)
    return frames_at_timestamp[0] if frames_at_timestamp else None

async def generate(video_path):
    """
    Analyze a local video file for brand compliance using Gemini LLM.
    Accepts only local video files (no URL/YouTube support).
    """
    is_valid, error = await validate_video_file(video_path)
    if not is_valid:
        raise Exception(f"Invalid video file: {error}")
    frames = await extract_frames(video_path, initial_interval=1, similarity_threshold=0.5)
    frame_captions = {"error": "Audio transcription disabled"}
    model = "gemini-2.0-flash"
    analysis_modes = ["visual", "brand_voice", "tone"]
    all_analysis_results = {}
    token_usage = {}
    # In-memory tool call cache: {cache_key: {"result": ..., "timestamp": ...}}
    TOOL_CALL_CACHE = {}
    TOOL_CACHE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days in seconds

    def tool_cache_key(tool_name, tool_input):
        # Deterministic hash of tool name and sorted input
        key_data = main_json.dumps({"tool": tool_name, "input": tool_input}, sort_keys=True)
        return hashlib.sha256(key_data.encode()).hexdigest()

    async def cached_tool_call(tool_name, tool_func, tool_input):
        key = tool_cache_key(tool_name, tool_input)
        now = time.time()
        if key in TOOL_CALL_CACHE:
            cached = TOOL_CALL_CACHE[key]
            if now - cached["timestamp"] < TOOL_CACHE_MAX_AGE:
                print(f"✅ [TOOL CACHE HIT] {tool_name} {tool_input}")
                return cached["result"]
            else:
                print(f"🕒 [TOOL CACHE EXPIRED] {tool_name} {tool_input}")
        print(f"🚀 [TOOL CACHE MISS] {tool_name} {tool_input}")
        result = await tool_func(tool_input)
        TOOL_CALL_CACHE[key] = {"result": result, "timestamp": now}
        return result

    for analysis_mode in analysis_modes:
        print(f"\n{'='*50}")
        print(f"🔍 Starting {analysis_mode.upper()} analysis")
        print(f"{'='*50}")
        messages = []
        messages.append({"role": "system", "content": gemini_system_prompt})
        user_content = []
        instruction_text = ""
        if analysis_mode == "visual":
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
        frame_count = len(frames)
        for i, frame_data in enumerate(frames):
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
        messages.append({"role": "user", "content": user_content})
        analysis_result = None
        # Token usage for this analysis mode
        token_usage[analysis_mode] = {"prompt": 0, "completion": 0}
        while True:
            final_text = ""
            print(f"\n{'='*50}")
            print(
                f"🚀 Streaming Content for {analysis_mode.upper()} - Started at {datetime.now().strftime('%H:%M:%S')}"
            )
            print(f"{'='*50}")
            max_retries = 3
            retry_count = 0
            streaming_successful = False
            while retry_count < max_retries and not streaming_successful:
                try:
                    response_stream = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        stream=True,
                        max_tokens=8192,
                    )
                    for chunk in response_stream:
                        # Track tokens if available
                        if hasattr(chunk, "usage") and chunk.usage:
                            usage = chunk.usage
                            token_usage[analysis_mode]["prompt"] += usage.get("prompt_tokens", 0)
                            token_usage[analysis_mode]["completion"] += usage.get("completion_tokens", 0)
                        if (
                            chunk.choices
                            and chunk.choices[0].delta
                            and chunk.choices[0].delta.content
                        ):
                            chunk_text = chunk.choices[0].delta.content
                            print(f"📦 Chunk received: {chunk_text}")
                            final_text += chunk_text
                        if chunk.choices and chunk.choices[0].finish_reason:
                            print(
                                f"🏁 Stream finished with reason: {chunk.choices[0].finish_reason}"
                            )
                            break
                    streaming_successful = True
                except Exception as e:
                    retry_count += 1
                    print(f"\nStream Error Type: {type(e).__name__}")
                    print(f"Stream Error Args: {e.args}")
                    if retry_count < max_retries:
                        print(
                            f"\n⚠️ Streaming error (attempt {retry_count}/{max_retries}): {str(e)}"
                        )
                        print(f"🔄 Retrying in 2 seconds...")
                        await asyncio.sleep(2)
                        final_text = ""
                    else:
                        print(
                            f"\n❌ Streaming failed after {max_retries} attempts: {str(e)}"
                        )
                        raise
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

            # --- TOOL CALL HANDLING LOOP (robust, lenient, and clear) ---
            try:
                xml_dict = None
                json_tool_name = None
                content_to_process = None
                is_xml = False

                # 1. Try strict code block extraction
                if (
                    "```xml" in final_text
                    and "```" in final_text.split("```xml")[1]
                ):
                    try:
                        xml_content = (
                            final_text.split("```xml")[1].split("```", 1)[0].strip()
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

                # 2. Try direct regex extraction for <tool>...</tool>
                if not is_xml:
                    print(f"🔎 Attempting to extract XML directly from raw text")
                    xml_pattern = r"<([a-zA-Z0-9_]+)>(.*?)</\1>"
                    xml_matches = re.findall(xml_pattern, final_text, re.DOTALL)
                    if xml_matches:
                        try:
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

                # 3. Try flexible code block regex (lenient)
                if not is_xml:
                    print(
                        f"🔎 Attempting to extract XML from code blocks with flexible regex"
                    )
                    code_block_pattern = r"```(?:xml)?\s*(.*?)```"
                    code_blocks = re.findall(
                        code_block_pattern, final_text, re.DOTALL
                    )
                    for block in code_blocks:
                        try:
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
                    print("❌ No valid XML found in the response (tool call will be skipped)")
                    # Continue the analysis loop, but do not crash
                    break

                # --- TOOL EXECUTION ---
                if is_xml and xml_dict and json_tool_name:
                    print(f"\n🛠️ Tool Information:")
                    print(f"📌 Tool Name: {json_tool_name}")
                    print(
                        f"📊 Processed Data:\n{main_json.dumps(xml_dict, indent=2)}"
                    )
                    tool_input = xml_dict[json_tool_name]

                    # Special handling for frame extraction tools
                    if (
                        json_tool_name
                        in [
                            "get_video_color_scheme",
                            "get_video_fonts",
                            "get_region_color_scheme",
                            "check_color_contrast",
                            "check_video_frame_specs",
                            "check_element_placement",
                            "check_layout_consistency",
                            "check_image_clarity",
                        ]
                        and "timestamp" in tool_input
                    ):
                        timestamp = int(tool_input["timestamp"])
                        frames_base64 = get_frames_by_timestamp(frames, timestamp)
                        if len(frames_base64) == 1:
                            tool_input["image_base64"] = frames_base64[0]
                            print(
                                f"🖼️ Added 1 frame at timestamp {timestamp} to tool input"
                            )
                        else:
                            tool_input["images_base64"] = frames_base64
                            tool_input["image_base64"] = frames_base64[0]
                            print(
                                f"🖼️ Added {len(frames_base64)} frames at timestamp {timestamp} to tool input"
                            )

                    # Get and call the tool function
                    tool_function = get_tool_function(json_tool_name)
                    if tool_function is None:
                        print(f"❌ No tool function found for: {json_tool_name} (skipping)")
                        break
                    tool_result = await cached_tool_call(json_tool_name, tool_function, tool_input)
                    tool_result_json = main_json.loads(tool_result)
                    print(f"\n{'='*50}")
                    print("⚙️ Tool Execution Results")
                    print(f"{'='*50}")
                    print(f"Tool Result: {tool_result}")

                    # Inject tool call and result into conversation
                    messages.append(
                        {"role": "assistant", "content": content_to_process}
                    )

                    # Remove base64/image fields from tool_result_json for text
                    tool_result_json_clean = dict(tool_result_json) if isinstance(tool_result_json, dict) else tool_result_json
                    base64_images = []
                    if isinstance(tool_result_json_clean, dict):
                        if "base64" in tool_result_json_clean and tool_result_json_clean["base64"]:
                            base64_images.append(tool_result_json_clean.pop("base64"))
                        if "images_base64" in tool_result_json_clean and tool_result_json_clean["images_base64"]:
                            base64_images.extend(tool_result_json_clean.pop("images_base64"))
                    # Add the cleaned tool result as text
                    messages.append(
                        {"role": "user", "content": f"Tool Result:\n{main_json.dumps(tool_result_json_clean, indent=2)}"}
                    )
                    # Add each image as an image message
                    for img_b64 in base64_images:
                        if img_b64:
                            messages.append({
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": f"data:image/png;base64,{img_b64}"}
                                    }
                                ]
                            })

                    # If this is the final tool, break (as in attempt_completion)
                    if json_tool_name == "attempt_completion":
                        print(f"\n{'='*50}")
                        print(
                            f"🏁 {analysis_mode.upper()} Analysis Complete: 'attempt_completion' tool detected"
                        )
                        break
            except Exception as e:
                print(f"\n❌ Error during {analysis_mode.upper()} analysis: {str(e)}")
                # Continue to next analysis mode, but don't raise
                break
        all_analysis_results[analysis_mode] = analysis_result
    print("\n===== Token Usage Summary =====")
    for mode, usage in token_usage.items():
        print(f"{mode.title()} - Prompt: {usage['prompt']} tokens, Completion: {usage['completion']} tokens, Total: {usage['prompt'] + usage['completion']} tokens")
    all_analysis_results["token_usage"] = token_usage
    return all_analysis_results

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python gemini_llm.py <local_video_path>")
        sys.exit(1)
    video_path = sys.argv[1]
    asyncio.run(generate(video_path))
