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

# from google import genai # Removed google.genai client
# from google.genai import types # Removed google.genai types
from openai import OpenAI  # Added OpenAI client
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
        self.tool_response = (
            ""  # Consider if this is still needed with OpenAI structure
        )
        self.text_response = (
            ""  # Consider if this is still needed with OpenAI structure
        )

        # Initialize the OpenAI client (using wrapper for Gemini)
        self.client = OpenAI(
            api_key=os.getenv("GOOGLE_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
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

        # Create messages list in OpenAI format
        messages = []

        # Add system prompt
        messages.append({"role": "system", "content": self.system_prompt})

        # Prepare user message content (will include text and images)
        user_content = []

        # Set instruction based on current analysis mode and user message
        instruction_text = ""
        if message:
            instruction_text = message
        elif analysis_mode == "visual":
            instruction_text = (
                "Check the compliance of this video for logo usage, color and brand compliance. "
                f"I'm providing {len(self.frames)} frames from a {len(set(frame['timestamp'] for frame in self.frames))} second video"
            )
        elif analysis_mode == "brand_voice":
            instruction_text = (
                "Analyze the BRAND VOICE of this video. Focus specifically on the overall personality and style. "
                "Check if the tone is consistent with brand guidelines and if the personality expressed aligns with brand values. "
                f"I'm providing {len(self.frames)} frames from a {len(set(frame['timestamp'] for frame in self.frames))} second video"
            )
        elif analysis_mode == "tone":
            instruction_text = (
                "Analyze the TONE OF VOICE in this video. Focus specifically on mood variations based on context. "
                "Check if the emotional tone shifts appropriately for different scenes and if these shifts align with brand guidelines. "
                f"I'm providing {len(self.frames)} frames from a {len(set(frame['timestamp'] for frame in self.frames))} second video"
            )
        else:
            instruction_text = (
                f"Analyze this video based on the following criteria: {analysis_mode}. "
                f"I'm providing {len(self.frames)} frames from a {len(set(frame['timestamp'] for frame in self.frames))} second video"
            )

        # Add transcription information if available
        if "error" not in self.frame_captions:
            instruction_text += f" along with audio transcription for each timestamp."
        else:
            instruction_text += "."

        user_content.append({"type": "text", "text": instruction_text})
        # Add transcription data if available and valid
        if "error" not in self.frame_captions and self.frame_captions.get(
            "frame_captions"
        ):
            transcription_text = "Video Transcription by Timestamp:\n"
            transcription_items = []
            for timestamp, caption_data in self.frame_captions.get(
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
        frame_count = len(self.frames)
        for i, frame_data in enumerate(self.frames):
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

        # Removed generate_content_config

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
                    response_stream = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,  # Pass the constructed messages list
                        stream=True,
                        max_tokens=8192,  # Example max_tokens
                        # Add other parameters like temperature if needed
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
                            # Send streaming event if callback is set
                            if self.on_stream:
                                await self.on_stream(
                                    {"type": "text", "content": chunk_text}
                                )
                        # Check for finish reason
                        if chunk.choices and chunk.choices[0].finish_reason:
                            print(
                                f"🏁 Stream finished with reason: {chunk.choices[0].finish_reason}"
                            )
                            break  # Exit inner loop

                    streaming_successful = (
                        True  # Assume success if loop completes/finishes
                    )

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
            try: # Top level try for XML processing and tool execution
                # Reset variables for each iteration
                xml_dict = None
                json_tool_name = None
                content_to_process = None
                is_xml = False

                # Method 1: Use regex to find XML specifically within ```xml ... ``` blocks
                xml_code_block_match = re.search(r"```xml\s*(.*?)\s*```", final_text, re.DOTALL | re.IGNORECASE)
                if xml_code_block_match:
                    try:
                        xml_content = xml_code_block_match.group(1).strip()
                        if xml_content.startswith("<") and xml_content.endswith(">"):
                            content_to_process = xml_content
                            xml_dict = xmltodict.parse(xml_content)
                            is_xml = True
                            print(f"\n{'='*50}\n🔍 XML Processing Results (From ```xml Code Block Regex)\n{'='*50}")
                            print(f"📋 Extracted XML Content:\n{xml_content}")
                            print(f"🧩 Parsed XML Content:\n{json.dumps(xml_dict, indent=2)}")
                            json_tool_name = list(xml_dict.keys())[0]
                        else:
                            print("⚠️ Content within ```xml block doesn't look like XML.")
                            is_xml = False
                    except Exception as xml_error:
                        print(f"⚠️ Error parsing XML from ```xml code block: {str(xml_error)}")
                        is_xml = False

                # Method 2: If Method 1 failed, try direct XML tag search
                if not is_xml:
                    print(f"🔎 Attempting to extract XML directly from raw text (Method 2)")
                    xml_pattern = r"<([a-zA-Z0-9_]+)>(.*?)</\1>"
                    xml_matches = re.findall(xml_pattern, final_text, re.DOTALL)
                    if xml_matches:
                        try:
                            root_tag, content = xml_matches[0]
                            reconstructed_xml = f"<{root_tag}>{content}</{root_tag}>"
                            xml_dict = xmltodict.parse(reconstructed_xml)
                            is_xml = True
                            content_to_process = reconstructed_xml
                            json_tool_name = root_tag
                            print(f"\n{'='*50}\n🔍 XML Processing Results (With Direct Regex)\n{'='*50}")
                            print(f"📋 Extracted XML Content:\n{reconstructed_xml}")
                            print(f"🧩 Parsed XML Content:\n{json.dumps(xml_dict, indent=2)}")
                        except Exception as regex_xml_error:
                            print(f"⚠️ Error parsing XML with direct regex (Method 2): {str(regex_xml_error)}")
                            is_xml = False

                # Method 3: If Methods 1 & 2 failed, try any code block
                if not is_xml:
                    print(f"🔎 Attempting to extract XML from *any* code block (Method 3)")
                    code_block_pattern = r"```(?:xml)?\s*(.*?)```"
                    code_blocks = re.findall(code_block_pattern, final_text, re.DOTALL)
                    for block in code_blocks:
                        try:
                            block = block.strip()
                            if block and block.startswith("<") and block.endswith(">"):
                                xml_dict = xmltodict.parse(block)
                                is_xml = True
                                content_to_process = block
                                json_tool_name = list(xml_dict.keys())[0]
                                print(f"\n{'='*50}\n🔍 XML Processing Results (From Any Code Block Regex - Method 3)\n{'='*50}")
                                print(f"📋 Extracted XML Content:\n{block}")
                                print(f"🧩 Parsed XML Content:\n{json.dumps(xml_dict, indent=2)}")
                                break # Found valid XML
                        except Exception as block_error:
                            continue # Ignore errors for non-XML blocks

                # --- Check if XML was found and proceed ---
                if not is_xml:
                    print("❌ No valid XML found in the response")
                    continue # Skip to the next iteration of the outer while loop

                # --- Tool Execution Logic (Only runs if is_xml is True) ---
                print(f"\n🛠️ Tool Information:")
                print(f"📌 Tool Name: {json_tool_name}")
                print(f"📊 Processed Data:\n{json.dumps(xml_dict, indent=2)}")

                # Add image_base64 to tool input if needed
                tool_input = xml_dict[json_tool_name]

                if (
                    json_tool_name in [
                        "get_video_color_scheme", "get_video_fonts",
                        "get_region_color_scheme", "check_color_contrast",
                        "check_video_frame_specs", "check_element_placement",
                    ] and "timestamp" in tool_input
                ):
                    timestamp = int(tool_input["timestamp"])
                    frames_base64 = get_frames_by_timestamp(self.frames, timestamp)
                    if len(frames_base64) == 1:
                        tool_input["image_base64"] = frames_base64[0]
                        print(f"🖼️ Added 1 frame at timestamp {timestamp} to tool input")
                    else:
                        tool_input["images_base64"] = frames_base64
                        tool_input["image_base64"] = frames_base64[0] # Backward compatibility
                        print(f"🖼️ Added {len(frames_base64)} frames at timestamp {timestamp} to tool input")

                # Send tool event if callback is set
                if self.on_stream:
                    await self.on_stream({
                        "type": "tool",
                        "content": json.dumps({"tool_name": json_tool_name, **tool_input}),
                    })

                # Execute tool function
                tool_function = get_tool_function(json_tool_name)
                tool_result = await tool_function(tool_input)
                tool_result_json = json.loads(tool_result)

                print(f"\n{'='*50}")
                print("⚙️ Tool Execution Results")
                print(f"{'='*50}")
                print(f"Tool Result: {tool_result}")

                # Update messages list for the next turn
                messages.append({"role": "assistant", "content": content_to_process})
                messages.append({"role": "user", "content": f"Tool Result:\n{tool_result}"})

                # Check for completion tool
                if json_tool_name == "attempt_completion": # Corrected indentation
                    print(f"\n{'='*50}") # Corrected indentation
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

                    print(f"🏁 {analysis_mode.upper()} Analysis Complete: 'attempt_completion' tool detected") # Corrected indentation
                    print(f"{'='*50}") # Corrected indentation
                    if "result" in tool_input: # Corrected indentation
                        self.all_analysis_results[analysis_mode] = tool_input["result"] # Corrected indentation
                    break # Corrected indentation - Exit the while True loop for this analysis mode

            except Exception as e: # Catch errors during XML parsing or tool execution
                print(f"\n{'-'*50}\n❌ Error Processing Content or Executing Tool: {str(e)}\n{'-'*50}")
                print(f"📄 Raw Final Text (at time of error):\n{final_text}")
                # Continue to the next iteration of the while True loop to retry the API call
                continue

            # If loop finishes without break (e.g., tool executed but wasn't 'attempt_completion'),
            # it will implicitly continue to the next API call in the while True loop.

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
