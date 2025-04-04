import asyncio
import os
import json
import shutil
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable

# Import the functions from the existing llm.py file
from app.core.video_agent.llm import (
    download_direct_video,
    download_video,
    calculate_frame_similarity,
    extract_frames,
    get_frames_by_timestamp,
    get_frame_by_timestamp,
)

from app.core.agent.prompt import gemini_system_prompt
from google import genai
from google.genai import types
import xmltodict
from app.core.video_agent.video_tools import get_tool_function
import re


class VideoAgent:
    """
    A class-based interface for the video agent that can be easily used
    similar to the normal agent in index.py.
    """

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        system_prompt: Optional[str] = None,
        on_stream: Optional[Callable] = None,
        on_stop: Optional[Callable] = None,
        user_id: Optional[str] = None,
        message_id: Optional[str] = None,
    ):
        """
        Initialize the VideoAgent.

        Args:
            model: The model to use for generation
            system_prompt: Custom system prompt (defaults to gemini_system_prompt)
            on_stream: Callback function for streaming events
            on_stop: Callback function when generation stops
            user_id: User ID for tracking
            message_id: Message ID for tracking
        """
        self.model = model
        self.system_prompt = system_prompt or gemini_system_prompt
        self.on_stream = self.container_on_stream if on_stream else None
        self._original_on_stream = on_stream
        self.on_stop = on_stop
        self.user_id = user_id
        self.message_id = message_id
        self.tool_response = ""
        self.text_response = ""

        # Initialize the Google AI client
        self.client = genai.Client(
            vertexai=True,
            project=os.getenv("GOOGLE_CLOUD_PROJECT", "nifty-digit-452608-t4"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )

        # Initialize results storage
        self.all_analysis_results = {}
        self.frames = []
        self.video_path = None
        self.frame_captions = {"error": "Audio transcription disabled"}

    async def container_on_stream(self, data: Dict[str, Any]):
        """Handle streaming data"""
        print(
            f"\n🔄 === Streaming Event ===\nType: {data['type']}\nContent: {data['content']}\n================"
        )
        if data["type"] in ("text", "thinking"):
            self.text_response += data["content"]
        elif data["type"] == "tool":
            self.tool_response += data["content"]
        if self._original_on_stream:
            await self._original_on_stream(data)
        return data

    async def generate(
        self,
        video_url: str,
        message: Optional[str] = None,
        analysis_modes: Optional[List[str]] = None,
    ):
        """
        Generate analysis for a video URL with an optional message.

        Args:
            video_url: URL of the video to analyze
            message: Optional message to include with the analysis
            analysis_modes: List of analysis modes to run (defaults to visual, brand_voice, tone)

        Returns:
            Dict containing analysis results and filepath
        """
        # Define default analysis modes if not provided
        if analysis_modes is None:
            analysis_modes = [
                "visual",  # Start with visual analysis
                "brand_voice",  # Then analyze brand voice
                "tone",  # Then analyze tone
            ]

        # Download the video and extract frames
        video_path_tuple = await download_video(video_url)
        # Handle the tuple returned by download_video
        if isinstance(video_path_tuple, tuple):
            self.video_path = video_path_tuple[0]  # Extract just the path
            temp_dir = video_path_tuple[1]  # Store the temp dir for cleanup
        else:
            # For backward compatibility if download_video is updated to return just a path
            self.video_path = video_path_tuple
            temp_dir = None

        self.frames = extract_frames(
            self.video_path, interval=1, similarity_threshold=0.8
        )

        # Clean up the downloaded video file
        try:
            os.remove(self.video_path)
            print(f"🧹 Cleaned up temporary video file {self.video_path}")
            # Also clean up temp directory if it exists
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                print(f"🧹 Cleaned up temporary directory {temp_dir}")
        except Exception as e:
            print(f"⚠️ Could not remove temporary file or directory: {str(e)}")

        # Run each analysis mode in sequence
        for analysis_mode in analysis_modes:
            await self.process_analysis_mode(analysis_mode, message)

        # Create a directory to store analysis results
        results_dir = os.path.join(os.getcwd(), "video_analysis_results")
        os.makedirs(results_dir, exist_ok=True)

        # Create a timestamp for the filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Extract video ID or name from URL
        video_id = (
            video_url.split("=")[-1] if "=" in video_url else video_url.split("/")[-1]
        )

        # Create a metadata object with information about the analysis
        metadata = {
            "video_url": video_url,
            "video_id": video_id,
            "analysis_timestamp": timestamp,
            "analysis_modes": analysis_modes,
            "frames_analyzed": len(self.frames),
            "video_duration_seconds": len(
                set(frame["timestamp"] for frame in self.frames)
            ),
            "transcription_available": "error" not in self.frame_captions,
            "custom_message": message if message else None,
        }

        # Combine metadata with analysis results
        full_results = {"metadata": metadata, "results": self.all_analysis_results}

        # Save results to a JSON file
        results_filename = f"{video_id}_{timestamp}_analysis.json"
        results_filepath = os.path.join(results_dir, results_filename)

        with open(results_filepath, "w") as f:
            json.dump(full_results, f, indent=2)

        print(f"\n📊 Analysis results saved to: {results_filepath}")

        # Return the results and filepath
        return {"results": self.all_analysis_results, "filepath": results_filepath}

    async def process_analysis_mode(
        self, analysis_mode: str, message: Optional[str] = None
    ):
        """Process a single analysis mode."""
        print(f"\n{'='*50}")
        print(f"🔍 Starting {analysis_mode.upper()} analysis")
        print(f"{'='*50}")

        # Create parts list with all frames as images
        parts = []

        # Add system prompt and instruction
        parts.append(types.Part.from_text(text=self.system_prompt))

        # Set instruction based on current analysis mode and user message
        if message:
            instruction = message
        elif analysis_mode == "visual":
            instruction = (
                "Check the compliance of this video for logo usage, color and brand compliance. "
                f"I'm providing {len(self.frames)} frames from a {len(set(frame['timestamp'] for frame in self.frames))} second video"
            )
        elif analysis_mode == "brand_voice":
            instruction = (
                "Analyze the BRAND VOICE of this video. Focus specifically on the overall personality and style. "
                "Check if the tone is consistent with brand guidelines and if the personality expressed aligns with brand values. "
                f"I'm providing {len(self.frames)} frames from a {len(set(frame['timestamp'] for frame in self.frames))} second video"
            )
        elif analysis_mode == "tone":
            instruction = (
                "Analyze the TONE OF VOICE in this video. Focus specifically on mood variations based on context. "
                "Check if the emotional tone shifts appropriately for different scenes and if these shifts align with brand guidelines. "
                f"I'm providing {len(self.frames)} frames from a {len(set(frame['timestamp'] for frame in self.frames))} second video"
            )
        else:
            instruction = (
                f"Analyze this video based on the following criteria: {analysis_mode}. "
                f"I'm providing {len(self.frames)} frames from a {len(set(frame['timestamp'] for frame in self.frames))} second video"
            )

        # Add transcription information if available
        if "error" not in self.frame_captions:
            instruction += f" along with audio transcription for each timestamp."
        else:
            instruction += "."

        parts.append(types.Part.from_text(text=instruction))

        # Add transcription data if available
        if "error" not in self.frame_captions:
            transcription_text = "Video Transcription by Timestamp:\n"
            for timestamp, caption_data in self.frame_captions.get(
                "frame_captions", {}
            ).items():
                if caption_data.get("text"):
                    transcription_text += f"[{timestamp}s]: {caption_data['text']}\n"

            if transcription_text != "Video Transcription by Timestamp:\n":
                parts.append(types.Part.from_text(text=transcription_text))
                print("📝 Added transcription data to API request")

        # Add all frames to the parts list
        frame_count = len(self.frames)

        # Add each frame to the parts list
        for i, frame in enumerate(self.frames):
            # Decode base64 to bytes
            import base64

            image_bytes = base64.b64decode(frame["base64"])
            # Add image part
            parts.append(
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            )
            print(
                f"🖼️ Added frame {i+1}/{frame_count} at timestamp {frame['timestamp']} to API request"
            )

        # Create the content with all parts
        contents = [
            types.Content(
                role="user",
                parts=parts,
            ),
        ]
        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            top_p=0.95,
            max_output_tokens=8192,
            response_modalities=["TEXT"],
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_HARASSMENT", threshold="OFF"
                ),
            ],
            system_instruction=self.system_prompt,
        )

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
                    for chunk in self.client.models.generate_content_stream(
                        model=self.model,
                        contents=contents,
                        config=generate_content_config,
                    ):
                        print(f"📦 Chunk received: {chunk.text}")
                        final_text += chunk.text

                        # Send streaming event if callback is set
                        if self.on_stream:
                            await self.on_stream(
                                {"type": "text", "content": chunk.text}
                            )

                    # If we get here without exception, streaming was successful
                    streaming_successful = True

                except Exception as e:
                    retry_count += 1
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
            print(f"🔢 Raw Bytes (first 200): {repr(final_text.encode('utf-8')[:200])}")

            # Process the complete text after streaming
            try:
                # Reset variables for each iteration to prevent using stale data
                xml_dict = None
                json_tool_name = None
                content_to_process = None
                is_xml = False

                # Method 1: Check if XML is wrapped in code blocks
                if "```xml" in final_text and "```" in final_text.split("```xml")[1]:
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
                            f"🧩 Parsed XML Content:\n{json.dumps(xml_dict, indent=2)}"
                        )

                        json_tool_name = list(xml_dict.keys())[0]
                    except Exception as xml_error:
                        print(f"⚠️ Error parsing XML from code blocks: {str(xml_error)}")
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
                            reconstructed_xml = f"<{root_tag}>{content}</{root_tag}>"

                            xml_dict = xmltodict.parse(reconstructed_xml)
                            is_xml = True
                            content_to_process = reconstructed_xml
                            json_tool_name = root_tag

                            print(f"\n{'='*50}")
                            print("🔍 XML Processing Results (With Direct Regex)")
                            print(f"{'='*50}")
                            print(f"📋 Extracted XML Content:\n{reconstructed_xml}")
                            print(
                                f"🧩 Parsed XML Content:\n{json.dumps(xml_dict, indent=2)}"
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
                    code_blocks = re.findall(code_block_pattern, final_text, re.DOTALL)

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
                                    f"🧩 Parsed XML Content:\n{json.dumps(xml_dict, indent=2)}"
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
                    print(f"📊 Processed Data:\n{json.dumps(xml_dict, indent=2)}")

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
                        frames_base64 = get_frames_by_timestamp(self.frames, timestamp)

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

                    # Send tool event if callback is set
                    if self.on_stream:
                        await self.on_stream(
                            {
                                "type": "tool",
                                "content": json.dumps(
                                    {"tool_name": json_tool_name, **tool_input}
                                ),
                            }
                        )

                    # Execute tool function
                    tool_function = get_tool_function(json_tool_name)
                    tool_result = await tool_function(tool_input)
                    tool_result_json = json.loads(tool_result)

                    print(f"\n{'='*50}")
                    print("⚙️ Tool Execution Results")
                    print(f"{'='*50}")

                    # Update contents
                    contents.append(
                        types.Content(
                            role="assistant",
                            parts=[types.Part.from_text(text=content_to_process)],
                        )
                    )

                    if tool_result_json.get("base64"):
                        contents.append(
                            types.Content(
                                role="user",
                                parts=[
                                    types.Part.from_bytes(
                                        data=base64.b64decode(
                                            tool_result_json["base64"]
                                        ),
                                        mime_type="image/*",
                                    ),
                                    types.Part.from_text(
                                        text=json.dumps(
                                            {
                                                k: v
                                                for k, v in tool_result_json.items()
                                                if k != "base64"
                                            }
                                        )
                                    ),
                                ],
                            )
                        )
                    else:
                        contents.append(
                            types.Content(
                                role="user",
                                parts=[types.Part.from_text(text=tool_result)],
                            )
                        )

                    if json_tool_name == "attempt_completion":
                        print(f"\n{'='*50}")
                        print(
                            f"🏁 {analysis_mode.upper()} Analysis Complete: 'attempt_completion' tool detected"
                        )
                        print(f"{'='*50}")

                        # Store the final result for this analysis mode
                        if "result" in tool_input:
                            self.all_analysis_results[analysis_mode] = tool_input[
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


# Example usage
async def test():
    # Create an instance of the VideoAgent
    agent = VideoAgent()

    # Analyze a video with a custom message
    video_url = "https://www.youtube.com/watch?v=9cPxh2DikIA"
    message = "Check this video for brand compliance and analyze the tone of voice."

    # Generate the analysis
    results = await agent.generate(video_url, message)

    print(f"\n=== Final Results ===\n{json.dumps(results, indent=2)}")


if __name__ == "__main__":
    asyncio.run(test())
