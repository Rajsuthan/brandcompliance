import os
import json
import base64
import aiohttp
import asyncio
import re
import xmltodict
import inspect
import time
import traceback
import datetime
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Awaitable

# Import tool schemas and functions from the existing tools.py
from app.core.agent.tools import claude_tools, get_tool_function

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Constants for timeout settings
OPENROUTER_TIMEOUT = 120  # 2 minutes timeout for OpenRouter API calls
STREAMING_TIMEOUT = 180  # 3 minutes timeout for the entire streaming operation

class OpenRouterAgent:
    def __init__(
        self,
        model: str = "anthropic/claude-3-7-sonnet-20250219",
        available_tools: Optional[List[Dict]] = None,
        on_stream: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        system_prompt: Optional[str] = None,
        timeout: int = OPENROUTER_TIMEOUT,
        save_messages: bool = True,
    ):
        self.model = model
        self.available_tools = available_tools or claude_tools
        self.messages: List[Dict[str, Any]] = []
        self.on_stream = on_stream
        self.system_prompt = system_prompt  # No override, let LLM use default tool call protocol
        self.timeout = timeout
        self.save_messages = save_messages
        self.conversation_id = str(uuid.uuid4())
        
        # Create logs directory if it doesn't exist
        self.logs_dir = Path("logs/conversations")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.messages_file = self.logs_dir / f"{self.conversation_id}.json"
        
        print(f"\033[94m[LOG] OpenRouterAgent.__init__: Initialized with model {model} and timeout {timeout}s\033[0m")
        if self.save_messages:
            print(f"\033[94m[LOG] OpenRouterAgent.__init__: Messages will be saved to {self.messages_file}\033[0m")

    async def save_messages_to_file(self):
        """Save current messages to a JSON file in real-time."""
        if not self.save_messages:
            return
            
        try:
            timestamp = datetime.datetime.now().isoformat()
            data = {
                "conversation_id": self.conversation_id,
                "model": self.model,
                "timestamp": timestamp,
                "messages": self.messages
            }
            
            with open(self.messages_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
            print(f"\033[92m[LOG] Saved messages to {self.messages_file}\033[0m")
        except Exception as e:
            print(f"\033[91m[ERROR] Failed to save messages to file: {e}\033[0m")
    
    async def add_message(self, role: str, content: Any):
        message = {"role": role, "content": content, "timestamp": datetime.datetime.now().isoformat()}
        self.messages.append(message)
        # Save messages in real-time
        await self.save_messages_to_file()

    async def stream_llm_response(self, session, payload):
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        async with session.post(OPENROUTER_API_URL, headers=headers, json=payload) as resp:
            async for line in resp.content:
                if line.startswith(b"data: "):
                    data = line[6:].decode("utf-8").strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        yield chunk
                    except Exception:
                        continue

    def extract_xml_tool_call(self, text: str):
        """
        Extract tool call information from XML blocks in the text.
        
        Supports multiple formats including:
        - Standard XML format: <tool_name>...</tool_name>
        - Python formatted blocks: <|python_start|>tool_name>...</tool_name><|python_end|>
        """
        # Check for Python-style tool call format
        python_pattern = r"<\|python_start\|>([a-zA-Z0-9_]+)>(.*?)</\1><\|python"
        python_match = re.search(python_pattern, text, re.DOTALL)
        if python_match:
            tool_name = python_match.group(1)
            content = python_match.group(2)
            # Extract content between tool tags to create proper XML
            proper_xml = f"<{tool_name}>{content}</{tool_name}>"
            try:
                # Parse the reconstructed XML
                xml_dict = xmltodict.parse(proper_xml)
                return tool_name, xml_dict[tool_name]
            except Exception as e:
                print(f"\033[91m[ERROR] Failed to parse Python-style tool call: {e}\033[0m")
                return None, None
        
        # Standard XML pattern
        xml_pattern = r"<([a-zA-Z0-9_]+)>([\s\S]*?)</\1>"
        match = re.search(xml_pattern, text)
        if match:
            tag = match.group(1)
            xml_content = match.group(0)
            
            # Skip processing if tag is a common inner tag (not a valid tool)
            inner_tags = ["timestamp", "tool_name", "task_detail", "image_base64", "tool_input"]
            if tag in inner_tags:
                print(f"\033[93m[WARNING] Found inner tag '{tag}' as outer tag. Looking for proper tool tag.\033[0m")
                # Try to find the actual tool tag
                proper_tool_pattern = r"<(get_[a-zA-Z0-9_]+|check_[a-zA-Z0-9_]+|analyze_[a-zA-Z0-9_]+|attempt_completion)>([\s\S]*?)</\1>"
                proper_match = re.search(proper_tool_pattern, text)
                if proper_match:
                    tag = proper_match.group(1)
                    xml_content = proper_match.group(0)
                    print(f"\033[92m[RECOVERY] Found proper tool tag: {tag}\033[0m")
                else:
                    print(f"\033[91m[ERROR] Could not find proper tool tag in the content\033[0m")
                    return None, None
            
            try:
                xml_dict = xmltodict.parse(xml_content)
                # If the outer tag is "xml", extract the first child as the real tool
                if tag == "xml" and isinstance(xml_dict["xml"], dict):
                    # Get the first key and value inside <xml>
                    inner_items = list(xml_dict["xml"].items())
                    if inner_items:
                        inner_tag, inner_value = inner_items[0]
                        return inner_tag, inner_value
                    else:
                        return None, None
                return tag, xml_dict[tag]
            except Exception as e:
                print(f"\033[91m[ERROR] XML parsing error for tag '{tag}': {e}\033[0m")
                return None, None
        return None, None

    async def process(
        self,
        user_prompt: str,
        image_base64: str = None,
        media_type: str = "image/png",
        video_path: str = None,
        video_url: str = None,
        frame_interval: float = 1.0,
        similarity_threshold: float = 0.8,
    ):
        """
        Process an image or video for compliance analysis.

        Args:
            user_prompt: The prompt for the LLM.
            image_base64: Base64-encoded image (for image analysis).
            media_type: MIME type of the input.
            video_path: Path to a local video file (for video analysis).
            video_url: URL to download a video (for video analysis).
            frame_interval: Interval (seconds) for frame extraction.
            similarity_threshold: Similarity threshold for frame deduplication.
        """
        import time
        process_start_time = time.time()
        print(f"[LOG] OpenRouterAgent.process: Started at {process_start_time:.3f}")
        user_content = []
        frames = []
        temp_dir = None

        # Video support
        if media_type.startswith("video/") or video_path or video_url:
            clarification = (
                "You are analyzing a video. "
                "You may use video-related tools as needed. "
                "If you need to analyze specific frames, timestamps, or regions, call the appropriate video tool."
            )
            # Download video if URL is provided
            if video_url:
                from app.core.video_agent.video_agent_class import download_video as _download_video
                video_path_tuple = await _download_video(video_url)
                if isinstance(video_path_tuple, tuple):
                    video_path = video_path_tuple[0]
                    temp_dir = video_path_tuple[1]
                else:
                    video_path = video_path_tuple
            # Extract frames
            from app.core.video_agent.gemini_llm import extract_frames
            frames = await extract_frames(
                video_path, initial_interval=frame_interval, similarity_threshold=similarity_threshold
            )
            # Build user_content: instruction + all frames as image_url
            instruction = (
                f"{user_prompt}\n"
                f"I'm providing {len(frames)} frames from this video for analysis."
            )
            user_content.append({"type": "text", "text": instruction})
            for i, frame_data in enumerate(frames):
                user_content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{frame_data['base64']}"
                        },
                    }
                )
        else:
            clarification = (
                "You are analyzing an image, not a video. "
                "Only use image-related tools. Do not call video tools."
            )
            user_content = [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media_type};base64,{image_base64}"
                    }
                },
                {
                    "type": "text",
                    "text": user_prompt
                }
            ]
        if self.system_prompt:
            await self.add_message("system", self.system_prompt)
        await self.add_message("user", clarification)
        await self.add_message("user", user_content)

        # Prepare OpenAI-compatible tool definitions
        def convert_tool(tool):
            return {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"]
                }
            }
        tools = [convert_tool(t) for t in self.available_tools]

        import datetime

        session = aiohttp.ClientSession()
        tool_trace = []
        try:
            while True:
                payload = {
                    "model": self.model,
                    "messages": self.messages,
                    "tools": tools,
                    "stream": True,  # Enable streaming for assistant text
                }
                # Stream the assistant's response
                full_content = ""
                tool_calls = None
                try:
                    print(f"\033[94m[LOG] OpenRouterAgent.stream_llm_response: Starting API call to {OPENROUTER_API_URL} at {time.time():.3f}\033[0m")
                    async with session.post(
                        OPENROUTER_API_URL, 
                        headers={
                            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                            "Content-Type": "application/json",
                        }, 
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as resp:
                        # Buffer all text content for this LLM response
                        full_content = ""
                        stream_start_time = time.time()
                        print(f"\033[94m[LOG] OpenRouterAgent.process: Streaming started at {stream_start_time:.3f}\033[0m")
                        first_chunk_time = None
                        chunk_count = 0
                        async for line in resp.content:
                            if line.startswith(b"data: "):
                                data = line[6:].decode("utf-8").strip()
                                if data == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data)
                                except Exception:
                                    continue
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                if "content" in delta:
                                    chunk_content = delta["content"]
                                    if chunk_content is not None:
                                        if first_chunk_time is None:
                                            first_chunk_time = time.time()
                                            print(f"\033[92m[LOG] First stream chunk received at {first_chunk_time:.3f} ({first_chunk_time - stream_start_time:.3f}s after stream start)\033[0m")
                                        full_content += chunk_content
                                        chunk_count += 1
                                        print(f"\033[96m[STREAM CHUNK {chunk_count}] {chunk_content}\033[0m")
                        stream_end_time = time.time()
                        print(f"\033[91m[LOG] OpenRouterAgent.process: Streaming ended at {stream_end_time:.3f}\033[0m")
                        print(f"\033[93m[LOG] OpenRouterAgent.process: Total streaming time: {stream_end_time - stream_start_time:.3f} seconds\033[0m")
                        if first_chunk_time:
                            print(f"\033[93m[LOG] Time to first stream chunk: {first_chunk_time - stream_start_time:.3f} seconds\033[0m")
                            print(f"\033[93m[LOG] Time from first chunk to end: {stream_end_time - first_chunk_time:.3f} seconds\033[0m")
                        print(f"\033[95m[LOG] OpenRouterAgent.process: Full content received: {full_content[:200]}{'...[[TRUNCATED]]' if len(full_content) > 200 else ''}\033[0m")
                except asyncio.TimeoutError:
                    print(f"\033[91m[ERROR] OpenRouterAgent.process: Timeout after {self.timeout}s waiting for OpenRouter API response\033[0m")
                    if self.on_stream:
                        await self.on_stream({"type": "text", "content": "Timeout error while processing. The request took too long to complete."})
                        await self.on_stream({"type": "complete", "content": "Processing timed out."})
                    raise
                except Exception as e:
                    print(f"\033[91m[ERROR] OpenRouterAgent.process: Exception during API call: {str(e)}\033[0m")
                    traceback.print_exc()
                    if self.on_stream:
                        await self.on_stream({"type": "text", "content": f"Error while processing: {str(e)}"})
                        await self.on_stream({"type": "complete", "content": "Processing failed with an error."})
                    raise
                
                # After streaming is done, extract XML tool call(s) and stream both text and tool
                if self.on_stream and full_content:
                    # Find all XML tool call blocks
                    xml_blocks = list(re.finditer(r"<xml>[\s\S]*?</xml>", full_content))
                    tool_events = []
                    attempt_completion_event = None
                    for xml_match in xml_blocks:
                        xml_content = xml_match.group(0)
                        tool_tag, tool_input = self.extract_xml_tool_call(xml_content)
                        if tool_tag and tool_input:
                            tool_event_json = json.dumps({
                                "tool_name": tool_tag,
                                "tool_input": tool_input
                            })
                            if tool_tag == "attempt_completion":
                                attempt_completion_event = tool_event_json
                            else:
                                tool_events.append(tool_event_json)
                        # Remove all XML blocks from text
                        cleaned_text = re.sub(r"<xml>[\s\S]*?</xml>", "", full_content).strip()
                        if cleaned_text:
                            await self.on_stream({"type": "text", "content": cleaned_text})
                        # Stream all tool events except attempt_completion
                        for tool_event_json in tool_events:
                            await self.on_stream({"type": "tool", "content": tool_event_json})
                        # Stream attempt_completion as both tool and complete event, if present
                        if attempt_completion_event:
                            await self.on_stream({"type": "tool", "content": attempt_completion_event})
                            await self.on_stream({"type": "complete", "content": attempt_completion_event})
                            break
                # XML tool call protocol: parse XML from assistant's text
                await self.add_message("assistant", {"content": full_content})
                # Only process the first XML tool call in the response
                tool_tag, tool_input = self.extract_xml_tool_call(full_content)
                if tool_tag and tool_input:
                    print(f"\033[96m[TOOL CALL] {tool_tag} with input: {str(tool_input)[:200]}...\033[0m")
                    tool_func = get_tool_function(tool_tag)
                    if not tool_func:
                        error_msg = f"Unknown tool: {tool_tag}. Please use one of the available tools."
                        print(f"\033[91m[ERROR] {error_msg}\033[0m")
                        
                        # Instead of raising an exception, send a helpful error message back to the model
                        error_feedback = (
                            f"ERROR: {error_msg}\n\n"
                            f"The format you used was incorrect. You tried to use '{tool_tag}' which is not a valid tool.\n"
                            f"Available tools include: get_video_fonts, check_video_frame_specs, extract_verbal_content, attempt_completion, etc.\n"
                            f"Please try again with the correct format:\n"
                            f"<tool_name>\n"
                            f"  <timestamp>10</timestamp>\n"
                            f"  <task_detail>Your task description</task_detail>\n"
                            f"</tool_name>\n"
                        )
                        
                        # Send error message as a user message to allow the model to correct itself
                        await self.add_message("user", error_feedback)
                        continue
                    # Add image_base64 for video tools based on timestamp, respecting input schema
                    video_tools = {
                        "get_video_color_scheme",
                        "get_video_fonts",
                        "check_video_frame_specs",
                        "extract_verbal_content",
                        "get_region_color_scheme",
                        "check_color_contrast",
                        "check_element_placement",
                        "check_image_clarity",
                        "check_layout_consistency",
                        "check_text_grammar",
                    }
                    if isinstance(tool_input, dict) and tool_tag in video_tools and frames:
                        # Only inject if neither images_base64 nor image_base64 is present
                        if "images_base64" not in tool_input and "image_base64" not in tool_input:
                            ts = tool_input.get("timestamp")
                            if ts is not None:
                                try:
                                    ts_int = int(ts)
                                    # Find the closest frame if exact match is not found
                                    frame = None
                                    min_diff = float("inf")
                                    for f in frames:
                                        frame_ts = int(f.get("timestamp", -1))
                                        diff = abs(frame_ts - ts_int)
                                        if diff < min_diff:
                                            min_diff = diff
                                            frame = f
                                    if frame and "base64" in frame:
                                        tool_input["image_base64"] = frame["base64"]
                                except Exception as e:
                                    print(f"\033[91m[ERROR] Could not extract frame for timestamp {ts}: {e}\033[0m")
                    elif isinstance(tool_input, dict) and "image_base64" not in tool_input:
                        tool_input["image_base64"] = image_base64
                    try:
                        print(f"\033[92m[TOOL EXEC] Executing {tool_tag}...\033[0m")
                        tool_result = await tool_func(tool_input)
                        trunc_tool_result = tool_result[:300] + ("...[[TRUNCATED]]" if len(tool_result) > 300 else "")
                        print(f"\033[95m[TOOL RESULT] {tool_tag}: {trunc_tool_result}\033[0m")
                    except Exception as e:
                        print(f"\033[91m[ERROR] Exception in {tool_tag}: {e}\033[0m")
                        tool_result = json.dumps({"error": str(e)})
                    # Log tool call and result
                    tool_trace.append({
                        "timestamp": datetime.datetime.now().isoformat(),
                        "tool_name": tool_tag,
                        "tool_input": tool_input,
                        "truncated_result": trunc_tool_result,
                        "full_result": tool_result if tool_tag == "attempt_completion" else None
                    })
                    # Stream tool result as a "tool" event (JSON-stringified)
                    if self.on_stream:
                        # Remove image_base64 and images_base64 from tool_input before yielding to frontend
                        filtered_tool_input = dict(tool_input) if isinstance(tool_input, dict) else tool_input
                        if isinstance(filtered_tool_input, dict):
                            filtered_tool_input.pop("image_base64", None)
                            filtered_tool_input.pop("images_base64", None)
                        await self.on_stream({
                            "type": "tool",
                            "tool_name": tool_tag,
                            "content": json.dumps({
                                "tool_name": tool_tag,
                                "tool_input": filtered_tool_input,
                                "tool_result": tool_result
                            })
                        })
                    # Send tool result as a new user message (not as a tool message)
                    tool_result_message = (
                        f"TOOL RESULT for <{tool_tag}>:\n"
                        f"{tool_result}\n\n"
                        f"You have received the result for <{tool_tag}>. "
                        f"Use this information to decide the next step. "
                        f"If more analysis is needed, call another tool using an XML block. "
                        f"If you are ready, provide your final answer."
                    )
                    await self.add_message("user", tool_result_message)
                    # If attempt_completion, send "complete" event and end the loop
                    if tool_tag == "attempt_completion":
                        if self.on_stream:
                            # Only send the final answer (tool_result) as the complete event
                            await self.on_stream({"type": "complete", "content": tool_result})
                        break
                    # Continue the loop for the next LLM response (enforce one tool call per response, but allow iterative tool use)
                    continue
                else:
                    # No XML tool call, but don't end the process
                    # Continue the loop by sending another model message
                    # Only attempt_completion should end the process
                    if self.on_stream:
                        await self.on_stream({"type": "text", "content": "Continuing the analysis..."})      
                    continue
        finally:
            await session.close()
            # Final save of all messages
            await self.save_messages_to_file()
        return self.messages

# Example usage
# async def main():
#     with open("test_image.png", "rb") as f:
#         image_base64 = base64.b64encode(f.read()).decode("utf-8")
#     agent = OpenRouterAgent()
#     async def print_stream(data):
#         print(f"{data['type']}: {data['content']}")
#     await agent.process("Check this image for brand compliance.", image_base64)

# if __name__ == "__main__":
#     asyncio.run(main())
