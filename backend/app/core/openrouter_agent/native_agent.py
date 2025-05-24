import os
import json
import asyncio
import time
import traceback
import uuid
import datetime
from typing import List, Dict, Any, Optional, Callable, Awaitable
import re
from pathlib import Path

# Import OpenAI SDK for native tool calling
from openai import AsyncOpenAI

# Import tool schemas and prompt management
from app.core.openrouter_agent.tool_definitions import get_tool_schemas
from app.core.openrouter_agent.prompt_manager import (
    get_system_prompt,
    get_iteration_milestone_prompt,
    get_force_completion_prompt
)

# Import modular components
from app.core.openrouter_agent.message_handler import MessageHandler
from app.core.openrouter_agent.stream_processor import process_completion_chunks
from app.core.openrouter_agent.tool_executor import execute_and_process_tool
from app.core.openrouter_agent.media_handler import inject_image_data

from app.core.agent.prompt import system_prompt

# Constants for timeout settings
OPENROUTER_TIMEOUT = 120  # 2 minutes timeout for OpenRouter API calls

# Fallback models to try when the primary model fails
FALLBACK_MODELS = [
    "openai/gpt-4o",
    "openai/o3-mini",
    # "google/gemini-2.5-pro-preview-03-25",
    "cohere/command-r-08-2024",
    "openai/gpt-4o"
]

class OpenRouterAgent:
    def __init__(
        self,
        api_key: str = os.getenv("OPENROUTER_API_KEY"),
        model: str = "anthropic/claude-3.7-sonnet",
        on_stream: Optional[Callable] = None,
        temperature: float = 0.2,
        max_tokens: int = 4000,
        stream: bool = True,
        system_prompt: Optional[str] = None,
        save_messages: bool = True,
    ):
        """Initialize a new OpenRouter agent with native tool calling capabilities.

        Args:
            api_key: OpenRouter API key (default: hardcoded API key)
            model: Model identifier to use (default: anthropic/claude-3.7-sonnet)
            on_stream: Optional callback for streaming responses
            temperature: Temperature parameter for generation
            max_tokens: Maximum tokens to generate
            stream: Whether to stream responses
            system_prompt: Optional custom system prompt
            save_messages: Whether to save conversation to disk
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.stream = stream
        self.timeout = OPENROUTER_TIMEOUT
        self.conversation_id = str(uuid.uuid4())

        # Initialize message handler
        self.message_handler = MessageHandler(
            conversation_id=self.conversation_id,
            on_stream=on_stream,
            save_messages=save_messages
        )

        # Note: tool_executor and media_handler are imported as functions, not classes

        # Add system prompt
        self.system_prompt = system_prompt or get_system_prompt(model)
        asyncio.create_task(self.message_handler.add_message("system", self.system_prompt))

        # Track whether an image is part of the conversation
        self.has_image = False

        # Initialize the OpenAI client with OpenRouter API settings
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://brandguideline.ai",
                "X-Title": "Brand Compliance AI"
            }
        )

        # Get tool schemas
        self.tools = get_tool_schemas()

        print(f"\033[94m[LOG] OpenRouterAgent.__init__: Initialized with model {model} and timeout {self.timeout}s\033[0m")

    async def process(
        self,
        user_prompt: str,
        image_base64: str = None,
        frames: List[Dict[str, Any]] = None,
        max_iterations: int = 25,
        response_timeout: int = 120,
        retry_count: int = 2,
        video_name: str = None,
        max_tokens: int = None,
    ) -> Dict[str, Any]:
        # Initialize timing metrics
        timing_metrics = {
            "start_time": time.time(),
            "end_time": None,
            "total_duration": None,
            "iterations": [],
            "llm_calls": [],
            "tool_executions": [],
            "final_report_generation": {
                "start_time": None,
                "end_time": None,
                "duration": None,
                "retries": []
            }
        }
        """Process user prompt using OpenRouter's native tool calling.

        This method handles the agentic loop, tool execution, and streaming responses.
        It's been refactored to leverage modular components for better maintainability.

        Args:
            user_prompt: The user's prompt/question
            image_base64: Optional base64-encoded image to include
            frames: Optional list of video frames with timestamps
            max_iterations: Maximum number of iterations before suggesting completion
            response_timeout: Timeout in seconds to wait for a response
            retry_count: Number of retries if API call fails
            video_name: Optional name of video being analyzed

        Returns:
            Dict with success status, response content, and tool trace
        """
        # Store tool calls and results for the final response
        tool_trace = []
        attempt_completion_result = None

        print(f"\033[94m[TIMING] Process started at {datetime.datetime.fromtimestamp(timing_metrics['start_time']).strftime('%H:%M:%S.%f')[:-3]}\033[0m")

        # Track iteration count to enforce completion after max_iterations
        iteration_count = 0

        # Track last response time to detect timeouts
        last_response_time = time.time()

        # Add the user prompt as a message, including image(s) if provided
        if frames:
            # We have video frames to process - create a multimodal message with all frames
            print(f"\033[94m[INFO] Processing video with {len(frames)} frames\033[0m")

            # Start with the text component
            message_content = [{"type": "text", "text": user_prompt}]

            # Add each frame as an image - support up to 25 frames
            max_frames = 25  # Updated maximum frames limit

            # Only sample frames if we have more than the maximum limit
            if len(frames) > max_frames:
                print(f"\033[93m[WARNING] Video has {len(frames)} frames, sampling down to {max_frames}\033[0m")
                sampling_step = len(frames) // max_frames
                if sampling_step < 1:
                    sampling_step = 1
            else:
                sampling_step = 1  # Use all frames if under the limit

            for i, frame in enumerate(frames):
                # Apply sampling if needed
                if len(frames) > max_frames and i % sampling_step != 0 and i > 0 and i < len(frames) - 1:
                    # Skip frames based on sampling, but always keep first and last frame
                    continue

                # Extract the image data (the key should be 'image_data' from compliance.py)
                image_data = frame.get("image_data")
                if not image_data:
                    print(f"\033[91m[ERROR] Frame {i} missing image_data, skipping\033[0m")
                    # Debug what keys are actually available
                    print(f"\033[93m[DEBUG] Frame {i} has keys: {list(frame.keys())}\033[0m")
                    continue

                # Add debugging info
                frame_number = frame.get("frame_number", i)
                timestamp = frame.get("timestamp", i * 0.5)
                print(f"\033[94m[DEBUG] Processing frame number {frame_number} at timestamp {timestamp:.2f}s\033[0m")

                # Check image size and potentially reduce detail level for large images
                image_size_kb = len(image_data) / 1024  # Convert to KB
                detail_level = "high" if image_size_kb < 500 else "low"  # More aggressive size management for multiple frames

                # Add the image to the message
                message_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_data}",
                        "detail": detail_level
                    }
                })

                print(f"\033[94m[INFO] Added frame {i} ({image_size_kb:.1f}KB) with {detail_level} detail\033[0m")

            await self.message_handler.add_message("user", message_content)
            self.has_image = True

        elif image_base64:
            # Single image processing - standard behavior
            # Check image size and potentially reduce detail level for large images
            image_size_kb = len(image_base64) / 1024  # Convert to KB
            detail_level = "high" if image_size_kb < 1000 else "low"  # Use low detail for images > 1MB

            # Log image details
            print(f"\033[94m[INFO] Processing image: {image_size_kb:.1f}KB with {detail_level} detail\033[0m")

            # Format the message with image data in OpenAI-compatible format
            message_content = [
                {"type": "text", "text": user_prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}",
                        "detail": detail_level
                    }
                }
            ]
            await self.message_handler.add_message("user", message_content)

            # Store image info for tools that need it, but don't keep the full image in history
            self.has_image = True
        else:
            # Regular text-only message
            await self.message_handler.add_message("user", user_prompt)
            self.has_image = False

        # Main loop to process the conversation and handle tool calls
        try:
            while True:
                # Increment iteration counter
                iteration_count += 1
                iteration_start_time = time.time()
                print(f"\033[94m[LOG] OpenRouterAgent.process: Starting iteration {iteration_count}\033[0m")
                print(f"\033[94m[TIMING] Iteration {iteration_count} started at {datetime.datetime.fromtimestamp(iteration_start_time).strftime('%H:%M:%S.%f')[:-3]}\033[0m")

                # Check if we've timed out waiting for a response
                if time.time() - last_response_time > response_timeout:
                    print(f"\033[93m[WARNING] OpenRouterAgent.process: Response timeout after {response_timeout}s\033[0m")
                    # Stream timeout message to the client
                    await self.message_handler.stream_content("The model is taking too long to respond. Please try again.")

                    return {
                        "success": False,
                        "error": f"Response timeout after {response_timeout}s",
                        "tool_trace": tool_trace,
                        "model": self.model
                    }

                try:
                    # Record start time for LLM call preparation
                    llm_prep_start = time.time()
                    print(f"\033[94m[TIMING] LLM call preparation started at {datetime.datetime.fromtimestamp(llm_prep_start).strftime('%H:%M:%S.%f')[:-3]}\033[0m")

                    # Check estimated token count
                    token_estimate = self.message_handler.get_message_token_estimate()
                    print(f"\033[94m[INFO] Estimated token count: {token_estimate}\033[0m")

                    # Use message history management to prevent token overflow
                    # Keep system messages and most recent messages if token count is high
                    # For OpenRouter, we need more aggressive pruning to avoid token limit errors
                    # The Claude 3.7 context window is 200K tokens
                    if token_estimate > 150000:  # Very high - risk of overflow
                        max_msgs = 5  # Very aggressive pruning
                        print(f"\033[91m[WARNING] Token count very high ({token_estimate}), pruning aggressively\033[0m")
                    elif token_estimate > 50000:  # High but manageable
                        max_msgs = 10  # Standard pruning
                        print(f"\033[93m[WARNING] Token count high ({token_estimate}), pruning messages\033[0m")
                    else:
                        max_msgs = 15  # No pruning needed

                    print(f"\033[94m[INFO] max_msgs: {max_msgs}\033[0m")


                    # Create the chat completion with the OpenAI SDK
                    # Override default max_tokens if specified in the process call
                    current_max_tokens = max_tokens if max_tokens is not None else self.max_tokens

                    # More aggressive message history management to prevent token overflow
                    # For large token counts (from images), limit to system prompt + latest messages
                    token_limit = 50000  # Lower threshold for context limiting
                    if token_estimate > token_limit:
                        # More aggressive token management - system prompt + last few messages
                        msg_limit = 3  # Set a very tight limit on message history
                        print(f"\033[93m[WARNING] Very high token count ({token_estimate}), using tight history limit of {msg_limit}\033[0m")
                        max_msgs = msg_limit

                    # Get formatted messages and log their sizes
                    formatted_messages = self.message_handler.get_formatted_messages(max_messages=max_msgs)

                    # Save the messages being passed to the LLM to a JSON file
                    loop_messages_dir = Path("logs/llm_messages")
                    loop_messages_dir.mkdir(parents=True, exist_ok=True)

                    # Create a timestamped filename to track each loop
                    timestamp = int(time.time())
                    loop_messages_file = loop_messages_dir / f"{self.conversation_id}_{iteration_count}_{timestamp}.json"

                    # Save messages to file
                    try:
                        with open(loop_messages_file, 'w') as f:
                            # Use a safe JSON serializer that can handle various types
                            json.dump({
                                "conversation_id": self.conversation_id,
                                "iteration": iteration_count,
                                "timestamp": timestamp,
                                "model": self.model,
                                "messages": formatted_messages
                            }, f, default=str, indent=2)
                        print(f"\033[94m[LOG] Saved LLM messages for iteration {iteration_count} to {loop_messages_file}\033[0m")
                    except Exception as e:
                        print(f"\033[91m[ERROR] Failed to save LLM messages to file: {str(e)}\033[0m")

                    # Add detailed size logging
                    total_chars = sum(len(str(msg)) for msg in formatted_messages)
                    print(f"\033[96m[MESSAGE DETAILS] Sending {len(formatted_messages)} messages with {total_chars} total chars\033[0m")

                    # Log size of the system prompt specifically
                    if len(formatted_messages) > 0 and formatted_messages[0]["role"] == "system":
                        system_prompt_size = len(str(formatted_messages[0]["content"]))
                        print(f"\033[96m[SYSTEM PROMPT SIZE] {system_prompt_size} chars\033[0m")
                        # Use repr to avoid issues with newlines and quotes in the preview
                        preview = repr(formatted_messages[0]["content"][:200])
                        print(f"\033[96m[SYSTEM PROMPT PREVIEW] {preview}...\033[0m")

                    # Show sizes of the most recent messages
                    for i, msg in enumerate(formatted_messages[-3:], 1):
                        msg_type = msg.get("role", "unknown")
                        msg_content = msg.get("content", "")
                        msg_size = len(str(msg))
                        print(f"\033[96m[MESSAGE {i} of {len(formatted_messages)}] Type: {msg_type}, Size: {msg_size} chars\033[0m")

                    # Record LLM call start time
                    llm_call_start = time.time()
                    llm_prep_duration = llm_call_start - llm_prep_start
                    print(f"\033[94m[TIMING] LLM call preparation completed in {llm_prep_duration:.2f}s\033[0m")
                    print(f"\033[94m[TIMING] LLM call started at {datetime.datetime.fromtimestamp(llm_call_start).strftime('%H:%M:%S.%f')[:-3]}\033[0m")

                    # Try to make the API call with potential model fallback
                    api_error = None
                    model_fallback_attempted = False
                    current_model = self.model

                    # Try the current model first
                    try:
                        completion = await self.client.chat.completions.create(
                            model=current_model,
                            messages=formatted_messages,
                            tools=self.tools,  # Pass the tool schemas
                            temperature=self.temperature,
                            max_tokens=current_max_tokens,
                            stream=self.stream,
                            timeout=self.timeout
                        )
                    except Exception as model_error:
                        print('--------❗❗❗❗❗❗❗❗❗❗❗')
                        print(model_error)
                        print('--------❗❗❗❗❗❗❗❗❗❗❗')
                        api_error = model_error
                        error_msg = str(model_error)
                        print(f"\033[91m[ERROR] Error with model {current_model}: {error_msg}\033[0m")

                        # Check if this is a provider error that requires model fallback
                        if "Provider returned error" in error_msg:
                            model_fallback_attempted = True

                            # Stream the error to client
                            if self.message_handler.on_stream:
                                await self.message_handler.on_stream({
                                    "type": "text",
                                    "content": f"The model {current_model} returned an error. Trying with a different model..."
                                })

                            # Try each fallback model in sequence
                            for fallback_model in FALLBACK_MODELS:
                                # Skip the current model if it's in the fallback list
                                if fallback_model == current_model:
                                    continue

                                print(f"\033[93m[MODEL FALLBACK] Trying fallback model: {fallback_model}\033[0m")

                                # Notify the user about the model change
                                if self.message_handler.on_stream:
                                    await self.message_handler.on_stream({
                                        "type": "text",
                                        "content": f"Trying model: {fallback_model}"
                                    })

                                try:
                                    # Try with the fallback model
                                    completion = await self.client.chat.completions.create(
                                        model=fallback_model,
                                        messages=formatted_messages,
                                        tools=self.tools,
                                        temperature=self.temperature,
                                        max_tokens=current_max_tokens,
                                        stream=self.stream,
                                        timeout=self.timeout
                                    )

                                    # If we get here, the fallback model worked
                                    print(f"\033[92m[MODEL FALLBACK] Successfully switched to {fallback_model}\033[0m")

                                    # Update the model for future iterations
                                    self.model = fallback_model
                                    current_model = fallback_model

                                    # Clear the error since we succeeded with a fallback model
                                    api_error = None
                                    break
                                except Exception as fallback_error:
                                    # Log the fallback error and continue to the next model
                                    print(f"\033[91m[ERROR] Fallback model {fallback_model} also failed: {str(fallback_error)}\033[0m")

                            # If we still have an error after trying all fallback models, raise it
                            if api_error:
                                print(f"\033[91m[ERROR] All fallback models failed\033[0m")
                                if self.message_handler.on_stream:
                                    await self.message_handler.on_stream({
                                        "type": "error",
                                        "content": "All available models failed. Please try again later."
                                    })
                                raise api_error

                    # Record LLM call end time
                    llm_call_end = time.time()
                    llm_call_duration = llm_call_end - llm_call_start
                    print(f"\033[94m[TIMING] LLM call completed in {llm_call_duration:.2f}s with model {current_model}\033[0m")

                    # Add to timing metrics
                    timing_metrics["llm_calls"].append({
                        "purpose": "main_iteration",
                        "iteration": iteration_count,
                        "model": current_model,
                        "start_time": llm_call_start,
                        "end_time": llm_call_end,
                        "duration": llm_call_duration,
                        "preparation_time": llm_prep_duration,
                        "fallback_attempted": model_fallback_attempted
                    })
                    # Update the last response time since we got a response
                    last_response_time = time.time()

                    # Record iteration end time and add to metrics
                    iteration_end_time = time.time()
                    iteration_duration = iteration_end_time - iteration_start_time
                    print(f"\033[94m[TIMING] Iteration {iteration_count} completed in {iteration_duration:.2f}s\033[0m")

                    # Add iteration timing to metrics
                    timing_metrics["iterations"].append({
                        "iteration": iteration_count,
                        "start_time": iteration_start_time,
                        "end_time": iteration_end_time,
                        "duration": iteration_duration,
                        "tool_calls": [t["tool_name"] for t in timing_metrics["tool_executions"] if t.get("iteration") == iteration_count]
                    })

                    # Stream handling
                    if self.stream:
                        # Process chunks to build response content and extract tool calls
                        # This will also stream text content in real-time during processing
                        try:
                            current_content, current_tool_calls, is_tool_call = await process_completion_chunks(
                                completion, self.message_handler, lambda t: globals().update({'last_response_time': t})
                            )

                            # Handle the response based on content and tool calls
                            if current_content and not current_tool_calls:
                                # Simple text response, no tools
                                await self.message_handler.add_message("assistant", current_content)
                            # Handle tool calls per OpenRouter documentation
                            elif current_tool_calls:
                                # Create the assistant message with tool_calls format
                                assistant_message = {
                                    "role": "assistant"
                                }

                                # Add content if there is any
                                if current_content:
                                    assistant_message["content"] = current_content
                        except Exception as e:
                            error_msg = str(e)
                            print(f"\033[91m[ERROR] Error processing completion chunks: {error_msg}\033[0m")

                            # Check if this is a provider error that requires model fallback
                            if "Provider returned error" in error_msg:
                                # Stream the error to client
                                if self.message_handler.on_stream:
                                    await self.message_handler.on_stream({
                                        "type": "text",
                                        "content": f"The model {self.model} returned an error. Trying with a different model..."
                                    })

                                # Find the next model to try
                                current_model_index = -1
                                try:
                                    # If current model is in the fallback list, get its index
                                    current_model_index = FALLBACK_MODELS.index(self.model)
                                except ValueError:
                                    # Current model is not in the fallback list, start with the first fallback model
                                    pass

                                # Get the next model to try
                                if current_model_index < len(FALLBACK_MODELS) - 1:
                                    # There are more models to try
                                    next_model = FALLBACK_MODELS[current_model_index + 1]
                                    print(f"\033[93m[MODEL FALLBACK] Switching from {self.model} to {next_model}\033[0m")

                                    # Update the model and try again
                                    self.model = next_model

                                    # Notify the user about the model change
                                    if self.message_handler.on_stream:
                                        await self.message_handler.on_stream({
                                            "type": "text",
                                            "content": f"Switching to model: {next_model}"
                                        })

                                    # Continue with the next iteration to retry with the new model
                                    continue
                                else:
                                    # We've tried all models, give up
                                    print(f"\033[91m[ERROR] All fallback models failed\033[0m")
                                    if self.message_handler.on_stream:
                                        await self.message_handler.on_stream({
                                            "type": "error",
                                            "content": "All available models failed. Please try again later."
                                        })
                            else:
                                # Not a provider error, just a regular error
                                # Stream the error to client
                                if self.message_handler.on_stream:
                                    await self.message_handler.on_stream({
                                        "type": "error",
                                        "content": f"Error processing response: {error_msg}"
                                    })

                            # Continue with the next iteration if there was an error processing chunks
                            continue

                        # Format the tool calls following the OpenAI structure (only if we had tool calls)
                        if current_tool_calls:
                            tool_calls = []
                            for tool_call in current_tool_calls:
                                # Generate an ID if one isn't provided
                                tool_id = tool_call.get("id", f"call_{str(uuid.uuid4())}")

                                tool_calls.append({
                                    "id": tool_id,
                                    "type": "function",
                                    "function": {
                                        "name": tool_call["function"]["name"],
                                        "arguments": tool_call["function"]["arguments"]
                                    }
                                })

                            # Add tool_calls array to the message
                            assistant_message["tool_calls"] = tool_calls

                            # Add the complete assistant message to conversation history through message_handler
                            await self.message_handler.add_message("assistant", assistant_message)

                            # Now process each tool call
                            for i, tool_call in enumerate(current_tool_calls):
                                # Extract tool information
                                tool_id = tool_call.get("id", assistant_message["tool_calls"][i]["id"])
                                tool_name = tool_call["function"]["name"]
                                tool_args_str = tool_call["function"]["arguments"]

                                # Parse arguments
                                try:
                                    tool_args = json.loads(tool_args_str)
                                except json.JSONDecodeError:
                                    print(f"\033[91m[ERROR] Failed to parse tool arguments: {tool_args_str}\033[0m")
                                    tool_args = {}

                                # Debug log the tool arguments
                                print(f"\033[93m[DEBUG] Initial tool_args for {tool_name}: {list(tool_args.keys())}\033[0m")

                                # Log detailed information about frames
                                if frames:
                                    print(f"\033[93m[DEBUG] Available frames: {len(frames)}\033[0m")
                                    for i, frame in enumerate(frames[:3]):  # Log first 3 frames
                                        print(f"\033[93m[DEBUG] Frame {i} keys: {list(frame.keys())}\033[0m")
                                        print(f"\033[93m[DEBUG] Frame {i} timestamp: {frame.get('timestamp')}\033[0m")
                                        has_image_data = "image_data" in frame and frame["image_data"]
                                        has_base64 = "base64" in frame and frame["base64"]
                                        print(f"\033[93m[DEBUG] Frame {i} has image_data: {has_image_data}, has base64: {has_base64}\033[0m")
                                        if has_image_data:
                                            print(f"\033[93m[DEBUG] Frame {i} image_data length: {len(frame['image_data'])}\033[0m")
                                            print(f"\033[93m[DEBUG] Frame {i} image_data (first 20 chars): {frame['image_data'][:20]}...\033[0m")
                                        if has_base64:
                                            print(f"\033[93m[DEBUG] Frame {i} base64 length: {len(frame['base64'])}\033[0m")
                                            print(f"\033[93m[DEBUG] Frame {i} base64 (first 20 chars): {frame['base64'][:20]}...\033[0m")
                                else:
                                    print(f"\033[91m[ERROR] No frames available for {tool_name}\033[0m")

                                # For video tools, ensure frames are added to tool_args
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

                                # Debug log to check if this is a video tool
                                if tool_name in video_tools:
                                    print(f"\033[92m[INFO] {tool_name} is a video tool\033[0m")
                                else:
                                    print(f"\033[93m[DEBUG] {tool_name} is not a video tool\033[0m")

                                if tool_name in video_tools and frames and len(frames) > 0:
                                    print(f"\033[93m[DEBUG] Adding frames to {tool_name} arguments\033[0m")

                                    # Special handling for extract_verbal_content
                                    if tool_name == "extract_verbal_content":
                                        # For extract_verbal_content, we need to add all frames
                                        images_base64 = []
                                        timestamps = tool_args.get("timestamps", [])

                                        # If no timestamps provided, use a default list
                                        if not timestamps:
                                            # Use timestamps from frames at 5-second intervals
                                            frame_timestamps = sorted(list(set([int(f.get("timestamp", 0)) for f in frames])))
                                            timestamps = [ts for ts in frame_timestamps if ts % 5 == 0]

                                            # If no timestamps at 5-second intervals, use first, middle, and last
                                            if not timestamps and frame_timestamps:
                                                timestamps = [
                                                    frame_timestamps[0],
                                                    frame_timestamps[len(frame_timestamps) // 2],
                                                    frame_timestamps[-1]
                                                ]

                                            # If still no timestamps, use [5, 10, 15]
                                            if not timestamps:
                                                timestamps = [5, 10, 15]

                                            # Add timestamps to tool_args
                                            tool_args["timestamps"] = timestamps
                                            print(f"\033[92m[INFO] Added timestamps to extract_verbal_content: {timestamps}\033[0m")

                                        # For each timestamp, find the closest frame
                                        for ts in timestamps:
                                            closest_frame = min(frames, key=lambda f: abs(f.get("timestamp", 0) - float(ts)))
                                            frame_base64 = closest_frame.get("image_data") or closest_frame.get("base64")
                                            if frame_base64:
                                                images_base64.append(frame_base64)

                                        if images_base64:
                                            print(f"\033[92m[INFO] Adding {len(images_base64)} frames to images_base64 for extract_verbal_content\033[0m")
                                            tool_args["images_base64"] = images_base64
                                            if len(images_base64) > 0:
                                                tool_args["image_base64"] = images_base64[0]  # Add first frame as image_base64

                                    # For other video tools
                                    elif "timestamp" in tool_args:
                                        target_ts = tool_args["timestamp"]
                                        print(f"\033[93m[DEBUG] Looking for timestamp: {target_ts}\033[0m")

                                        # Find the closest frame
                                        closest_frame = min(frames, key=lambda f: abs(f.get("timestamp", 0) - float(target_ts)))
                                        print(f"\033[93m[DEBUG] Found closest frame at timestamp: {closest_frame.get('timestamp')}\033[0m")

                                        # Get the base64 data from either key
                                        frame_base64 = closest_frame.get("image_data") or closest_frame.get("base64")
                                        if frame_base64:
                                            print(f"\033[92m[INFO] Adding closest frame as image_base64 (length: {len(frame_base64)})\033[0m")
                                            tool_args["image_base64"] = frame_base64

                                            # Always add at least the closest frame to images_base64
                                            tool_args["images_base64"] = [frame_base64]
                                            print(f"\033[92m[INFO] Added closest frame to images_base64 array\033[0m")

                                            # Get all frames within 1 second of the target timestamp
                                            nearby_frames = [
                                                f for f in frames
                                                if abs(f.get("timestamp", 0) - float(target_ts)) <= 1
                                            ]

                                            # Extract base64 data from each frame
                                            images_base64 = []
                                            for frame in nearby_frames:
                                                frame_data = frame.get("image_data") or frame.get("base64")
                                                if frame_data:
                                                    images_base64.append(frame_data)

                                            if images_base64:
                                                print(f"\033[92m[INFO] Adding {len(images_base64)} nearby frames as images_base64\033[0m")
                                                tool_args["images_base64"] = images_base64
                                    else:
                                        # If no timestamp, add all frames
                                        images_base64 = []
                                        for frame in frames:
                                            frame_data = frame.get("image_data") or frame.get("base64")
                                            if frame_data:
                                                images_base64.append(frame_data)

                                        if images_base64:
                                            print(f"\033[92m[INFO] Adding all {len(images_base64)} frames as images_base64\033[0m")
                                            tool_args["images_base64"] = images_base64
                                            if len(images_base64) > 0:
                                                tool_args["image_base64"] = images_base64[0]  # Add first frame as image_base64

                                    # Debug log to verify frames are being added
                                    if "images_base64" in tool_args:
                                        print(f"\033[92m[DEBUG] Final tool_args has images_base64 with {len(tool_args['images_base64'])} items\033[0m")
                                    else:
                                        print(f"\033[91m[ERROR] Final tool_args is missing images_base64\033[0m")

                                # Execute the tool and stream its result
                                try:
                                    print(f"\033[92m[TOOL EXEC] Executing {tool_name}...\033[0m")

                                    # First, stream that we're executing the tool (better UX)
                                    if self.message_handler.on_stream:
                                        # await self.message_handler.on_stream({
                                        #     "type": "text",
                                        #     "content": f"Executing tool: {tool_name}..."
                                        # })
                                        print('tool name', tool_name)

                                    # CRITICAL: Final check to ensure frames are added for video tools
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

                                    if tool_name in video_tools:
                                        print(f"\033[93m[DEBUG] FINAL CHECK for {tool_name} - tool_args keys: {list(tool_args.keys())}\033[0m")

                                        # Check if images_base64 or image_base64 is present
                                        has_images_base64 = "images_base64" in tool_args and tool_args["images_base64"]
                                        has_image_base64 = "image_base64" in tool_args and tool_args["image_base64"]

                                        print(f"\033[93m[DEBUG] FINAL CHECK - has_images_base64: {has_images_base64}, has_image_base64: {has_image_base64}\033[0m")

                                        # If neither is present but we have frames, add them
                                        if not (has_images_base64 or has_image_base64) and frames and len(frames) > 0:
                                            print(f"\033[91m[ERROR] {tool_name} is missing both images_base64 and image_base64. Adding frames now.\033[0m")

                                            # For extract_verbal_content, add frames for timestamps
                                            if tool_name == "extract_verbal_content":
                                                # Get timestamps or use defaults
                                                timestamps = tool_args.get("timestamps", [5, 10, 15])

                                                # Add timestamps to tool_args if not present
                                                if "timestamps" not in tool_args:
                                                    tool_args["timestamps"] = timestamps
                                                    print(f"\033[92m[INFO] Added default timestamps to extract_verbal_content: {timestamps}\033[0m")

                                                # For each timestamp, find the closest frame
                                                images_base64 = []
                                                for ts in timestamps:
                                                    closest_frame = min(frames, key=lambda f: abs(f.get("timestamp", 0) - float(ts)))
                                                    frame_base64 = closest_frame.get("image_data") or closest_frame.get("base64")
                                                    if frame_base64:
                                                        images_base64.append(frame_base64)

                                                if images_base64:
                                                    print(f"\033[92m[INFO] FINAL CHECK - Adding {len(images_base64)} frames to images_base64 for extract_verbal_content\033[0m")
                                                    tool_args["images_base64"] = images_base64
                                                    tool_args["image_base64"] = images_base64[0]  # Add first frame as image_base64

                                            # For other video tools with timestamp
                                            elif "timestamp" in tool_args:
                                                target_ts = tool_args["timestamp"]
                                                print(f"\033[93m[DEBUG] FINAL CHECK - Looking for timestamp: {target_ts}\033[0m")

                                                # Find the closest frame
                                                closest_frame = min(frames, key=lambda f: abs(f.get("timestamp", 0) - float(target_ts)))
                                                frame_base64 = closest_frame.get("image_data") or closest_frame.get("base64")

                                                if frame_base64:
                                                    print(f"\033[92m[INFO] FINAL CHECK - Adding closest frame to image_base64 and images_base64\033[0m")
                                                    tool_args["image_base64"] = frame_base64
                                                    tool_args["images_base64"] = [frame_base64]

                                            # For other video tools without timestamp
                                            else:
                                                # Add all frames
                                                images_base64 = []
                                                for frame in frames:
                                                    frame_data = frame.get("image_data") or frame.get("base64")
                                                    if frame_data:
                                                        images_base64.append(frame_data)

                                                if images_base64:
                                                    print(f"\033[92m[INFO] FINAL CHECK - Adding all {len(images_base64)} frames\033[0m")
                                                    tool_args["images_base64"] = images_base64
                                                    tool_args["image_base64"] = images_base64[0]

                                        # Final verification
                                        if "images_base64" in tool_args:
                                            print(f"\033[92m[DEBUG] FINAL VERIFICATION - tool_args has images_base64 with {len(tool_args['images_base64'])} items\033[0m")
                                        else:
                                            print(f"\033[91m[ERROR] FINAL VERIFICATION - tool_args is still missing images_base64\033[0m")

                                    # Record tool execution start time
                                    tool_start = time.time()
                                    print(f"\033[94m[TIMING] Tool execution for {tool_name} started at {datetime.datetime.fromtimestamp(tool_start).strftime('%H:%M:%S.%f')[:-3]}\033[0m")

                                    # Execute the tool - returns the proper OpenRouter compatible message format
                                    result_format = await execute_and_process_tool(
                                        tool_name,
                                        tool_args,
                                        image_base64,
                                        frames,
                                        tool_call_id=tool_id,  # Pass the tool_call_id from the API response
                                        on_stream=self.message_handler.on_stream
                                    )

                                    # Record tool execution end time
                                    tool_end = time.time()
                                    tool_duration = tool_end - tool_start
                                    print(f"\033[94m[TIMING] Tool execution for {tool_name} completed in {tool_duration:.2f}s\033[0m")

                                    # Add to timing metrics
                                    timing_metrics["tool_executions"].append({
                                        "tool_name": tool_name,
                                        "iteration": iteration_count,
                                        "start_time": tool_start,
                                        "end_time": tool_end,
                                        "duration": tool_duration
                                    })

                                    # Extract the actual tool result from the message format
                                    if isinstance(result_format, dict) and "content" in result_format:
                                        tool_result = result_format["content"]
                                    else:
                                        tool_result = str(result_format)

                                    # Ensure tool_result is properly formatted for further processing
                                    # If it's a string that looks like JSON, try to parse it
                                    if isinstance(tool_result, str):
                                        try:
                                            if tool_result.strip().startswith('{') and tool_result.strip().endswith('}'):
                                                parsed_result = json.loads(tool_result)
                                                tool_result = parsed_result
                                        except json.JSONDecodeError:
                                            # If parsing fails, keep it as a string
                                            pass

                                    # Add to tool trace for logging/debugging (minimal format)
                                    tool_trace.append({
                                        "tool": tool_name,
                                        "input": {k: v for k, v in tool_args.items() if k not in ["image_base64", "images_base64"]},
                                        "output": tool_result
                                    })

                                    # Stream the tool result in the format compliance API expects
                                    # Only include the minimal necessary information to reduce token usage
                                    if self.message_handler.on_stream:
                                        # Create a simplified result representation - remove any unnecessarily large fields
                                        simplified_result = tool_result
                                        if isinstance(simplified_result, str):
                                            # Try to parse as JSON to simplify if possible
                                            try:
                                                simplified_result = json.loads(simplified_result)
                                            except:
                                                pass

                                        # Remove trace and other metadata if present
                                        if isinstance(simplified_result, dict):
                                            if "trace_record" in simplified_result:
                                                del simplified_result["trace_record"]

                                        await self.message_handler.on_stream({
                                            "type": "tool",
                                            "content": json.dumps({
                                                "tool_name": tool_name,
                                                "tool_input": {k: v for k, v in tool_args.items() if k not in ["image_base64", "images_base64"]},
                                                "tool_result": simplified_result
                                            })
                                        })
                                except Exception as e:
                                    print(f"\033[91m[ERROR] Exception in {tool_name}: {e}\033[0m")
                                    tool_result = {"error": str(e)}

                                    # Stream error to client
                                    if self.message_handler.on_stream:
                                        await self.message_handler.on_stream({
                                            "type": "error",
                                            "content": f"Error executing tool {tool_name}: {str(e)}"
                                        })

                                # Add tool result as a message following OpenAI/OpenRouter format
                                tool_response = {
                                    "role": "tool",
                                    "tool_call_id": tool_id,
                                    "name": tool_name,
                                    "content": json.dumps(tool_result)  # Must be JSON string per OpenRouter docs
                                }

                                # Add the tool response to conversation history
                                await self.message_handler.add_message("tool", tool_response)

                            # If attempt_completion, proceed to the second step of our two-step approach
                            if tool_name == "attempt_completion":
                                print(f"\033[94m[INFO] Received attempt_completion summary, proceeding to detailed report generation\033[0m")

                                # Handle attempt_completion results (even incomplete ones)
                                print(f"\033[94m[DEBUG] Raw attempt_completion result: {tool_result}\033[0m")

                                # Safety check: if tool_result is None, handle it gracefully
                                if tool_result is None:
                                    print(f"\033[91m[ERROR] attempt_completion tool_result is None\033[0m")
                                    tool_result = "No result available"

                                # Try multiple approaches to extract useful data
                                attempt_completion_summary = {}

                                # Approach 1: If it's already a dictionary, use it directly
                                if isinstance(tool_result, dict):
                                    attempt_completion_summary = tool_result
                                    print(f"\033[94m[INFO] attempt_completion_summary is a dictionary with keys: {list(attempt_completion_summary.keys())}\033[0m")

                                    # Check if tool_result has a nested structure with 'tool_result' key
                                    if 'tool_result' in attempt_completion_summary and isinstance(attempt_completion_summary['tool_result'], dict):
                                        print(f"\033[94m[INFO] Found nested tool_result in attempt_completion_summary\033[0m")
                                        # Use the nested tool_result instead
                                        attempt_completion_summary = attempt_completion_summary['tool_result']
                                        print(f"\033[94m[INFO] Using nested tool_result with keys: {list(attempt_completion_summary.keys())}\033[0m")

                                # Approach 2: Try to parse as JSON if it's a string
                                elif isinstance(tool_result, str):
                                    try:
                                        # Clean attempt_completion_result if it looks like malformed JSON
                                        cleaned_result = tool_result
                                        # Handle common errors in JSON formatting
                                        if cleaned_result.startswith("Error:"):
                                            # If it's an error message, create a summary with that message
                                            attempt_completion_summary = {
                                                "compliance_status": "unknown",
                                                "compliance_summary": f"Analysis incomplete: {cleaned_result}"
                                            }
                                        else:
                                            # Try to parse as JSON
                                            try:
                                                parsed_result = json.loads(cleaned_result)
                                                print(f"\033[94m[INFO] Successfully parsed string as JSON\033[0m")

                                                # Check if the parsed result is a dictionary
                                                if isinstance(parsed_result, dict):
                                                    attempt_completion_summary = parsed_result

                                                    # Check if there's a nested tool_result
                                                    if 'tool_result' in attempt_completion_summary and isinstance(attempt_completion_summary['tool_result'], dict):
                                                        print(f"\033[94m[INFO] Found nested tool_result in parsed JSON\033[0m")
                                                        attempt_completion_summary = attempt_completion_summary['tool_result']
                                                else:
                                                    print(f"\033[93m[WARNING] Parsed JSON is not a dictionary: {type(parsed_result)}\033[0m")
                                                    attempt_completion_summary = {
                                                        "compliance_status": "unknown",
                                                        "compliance_summary": f"Unexpected format: {str(parsed_result)[:300]}..."
                                                    }
                                            except json.JSONDecodeError as json_err:
                                                print(f"\033[93m[WARNING] Failed to parse as JSON: {str(json_err)}\033[0m")
                                                # If JSON parsing fails, check if we got partial data
                                                if "compliance_status" in cleaned_result:
                                                    # Extract what we can using string operations
                                                    status_match = re.search(r"\"compliance_status\":\s*\"([^\"]+)\"", cleaned_result)
                                                    if status_match:
                                                        attempt_completion_summary["compliance_status"] = status_match.group(1)

                                                # If still empty, create a basic summary
                                                if not attempt_completion_summary:
                                                    attempt_completion_summary = {
                                                        "compliance_status": "unknown",
                                                        "compliance_summary": f"Partial analysis: {cleaned_result[:300]}..."
                                                    }
                                    except Exception as e:
                                        print(f"\033[91m[WARNING] Failed to process attempt_completion result: {str(e)}\033[0m")
                                        attempt_completion_summary = {
                                            "compliance_status": "unknown",
                                            "compliance_summary": f"Error processing completion: {str(tool_result)[:300]}..."
                                        }

                                # Ensure we have the minimum required fields
                                if "compliance_status" not in attempt_completion_summary:
                                    # Look for common status indicators in the raw result
                                    raw_str = str(tool_result).lower()
                                    if "non-compliant" in raw_str or "non_compliant" in raw_str:
                                        attempt_completion_summary["compliance_status"] = "non_compliant"
                                    elif "compliant" in raw_str:
                                        attempt_completion_summary["compliance_status"] = "compliant"
                                    else:
                                        attempt_completion_summary["compliance_status"] = "unknown"

                                if "compliance_summary" not in attempt_completion_summary:
                                    attempt_completion_summary["compliance_summary"] = str(tool_result)[:500]

                                # Include the raw tool_result as context
                                attempt_completion_summary["raw_tool_result"] = str(tool_result)[:1000]

                                # STEP 2: Generate detailed compliance report using Claude 3.7 Sonnet without tools
                                # This avoids the issues with large tool results and provides better formatting
                                try:
                                    # Record start time for final report generation
                                    final_report_start = time.time()
                                    timing_metrics["final_report_generation"]["start_time"] = final_report_start
                                    print(f"\033[94m[INFO] Generating detailed compliance report...\033[0m")
                                    print(f"\033[94m[TIMING] Final report generation started at {datetime.datetime.fromtimestamp(final_report_start).strftime('%H:%M:%S.%f')[:-3]}\033[0m")

                                    # Import prompt from prompt_manager to ensure we're using the exact same prompt
                                    from app.core.openrouter_agent.prompt_manager import get_system_prompt

                                    # Get the exact Claude prompt from prompt_manager
                                    final_report_prompt = get_system_prompt(self.model)

                                    # Get all the previous conversation messages to include as context
                                    # This ensures the model has access to all previous findings and analysis
                                    previous_messages = self.message_handler.get_formatted_messages()

                                    # Extract the image content from the original message for the final report
                                    # This is critical to ensure the model can analyze the image directly
                                    image_content = None
                                    original_image_message = None


                                    print(f"\033[94m[INFO] Image content found for final report: {image_content is not None}\033[0m")

                                    # Construct the user prompt with the summary and instructions
                                    # Convert attempt_completion_summary to a string representation, regardless of its type
                                    attempt_completion_str = str(attempt_completion_summary)
                                    if isinstance(attempt_completion_summary, dict):
                                        try:
                                            attempt_completion_str = json.dumps(attempt_completion_summary, indent=2)
                                        except Exception as json_err:
                                            # If JSON serialization fails, fall back to string representation
                                            print(f"\033[93m[WARNING] Failed to serialize attempt_completion_summary to JSON: {str(json_err)}\033[0m")
                                            attempt_completion_str = str(attempt_completion_summary)

                                    print(f"\033[94m[INFO] Using attempt_completion_str for final report: {attempt_completion_str[:200]}...\033[0m")

                                    final_user_prompt_text = f"""Generate a FINAL DETAILED brand compliance analysis report for the image shown.

Here is a summary of key compliance findings from the analysis:
{attempt_completion_str}

{system_prompt}"""

                                    # Create a message list that includes system prompt and previous message context
                                    messages_for_completion = [
                                        {"role": "system", "content": final_report_prompt}
                                    ]

                                    # Important: Add ALL previous messages including system messages and ALL tool results
                                    # This ensures the model has access to the complete conversation history
                                    for msg in previous_messages:
                                        # check if a msg content is a list
                                        # if its a list, then see if there is a object with the type of 'image_url'
                                        # if then, remove that object
                                        if isinstance(msg["content"], list):
                                            for c in msg["content"]:
                                                if c.get("type") == "image_url":
                                                    msg["content"].remove(c)
                                        messages_for_completion.append(msg)
                                        # # Skip messages that don't have required fields
                                        # if not isinstance(msg, dict) or "role" not in msg:
                                        #     print(f"\033[93m[WARNING] Skipping message without role: {msg}\033[0m")
                                        #     continue

                                        # # Skip system messages
                                        # if msg["role"] == "system":
                                        #     continue

                                        # # Handle case where content is missing
                                        # if "content" not in msg:
                                        #     print(f"\033[93m[WARNING] Message has no content field: {msg}\033[0m")
                                        #     # Add with empty content to maintain conversation flow
                                        #     messages_for_completion.append({"role": msg["role"], "content": ""})
                                        #     continue

                                        # # Handle different content formats safely
                                        # if isinstance(msg["content"], list):
                                        #     # Content is a list of objects (e.g., containing text and images)
                                        #     new_content = []
                                        #     for c in msg["content"]:
                                        #         # Only add non-image content
                                        #         if isinstance(c, dict) and c.get("type") != "image_url":
                                        #             new_content.append(c)
                                        #         elif not isinstance(c, dict):
                                        #             # If it's not a dict, convert to string and check for image_url
                                        #             c_str = str(c).lower()
                                        #             if "image_url" not in c_str:
                                        #                 # Only add if it doesn't contain image_url
                                        #                 new_content.append(c)
                                        #     # Only add if we have content
                                        #     if new_content:
                                        #         messages_for_completion.append({"role": msg["role"], "content": new_content})
                                        # else:
                                        #     # Content is a simple string or other value
                                        #     # Check if it contains image_url before adding
                                        #     content_str = str(msg["content"]).lower()
                                        #     if "image_url" not in content_str:
                                        #         # Only add if it doesn't contain image_url
                                        #         messages_for_completion.append({"role": msg["role"], "content": msg["content"]})

                                    # Insert images for final answer generation (after removing all previous images)
                                    # IMAGE COMPLIANCE: Add image_base64 as image_url message
                                    # infer the type of image (jpeg or png) from the image64 being sent
                                    # image_type = "jpeg" if "jpeg" in image_base64.lower() else "png"

                                    # if image_base64:
                                    #     image_size_kb = len(image_base64) / 1024
                                    #     detail_level = "high" if image_size_kb < 1000 else "low"
                                    #     messages_for_completion.append({
                                    #         "role": "user",
                                    #         "content": [
                                    #             {
                                    #                 "type": "image_url",
                                    #                 "image_url": {
                                    #                     "url": f"data:image/{image_type};base64,{image_base64}",
                                    #                     "detail": detail_level
                                    #                 }
                                    #             }
                                    #         ]
                                    #     })
                                    # # VIDEO COMPLIANCE: Add all frames' image_data as image_url messages
                                    # elif frames:
                                    #     for i, frame in enumerate(frames):
                                    #         image_data = frame.get("image_data")
                                    #         if not image_data:
                                    #             print(f"[WARNING] Frame {i} missing image_data, skipping for final answer images.")
                                    #             continue
                                    #         image_size_kb = len(image_data) / 1024
                                    #         detail_level = "high" if image_size_kb < 500 else "low"
                                    #         messages_for_completion.append({
                                    #             "role": "user",
                                    #             "content": [
                                    #                 {
                                    #                     "type": "image_url",
                                    #                     "image_url": {
                                    #                         "url": f"data:image/{image_type};base64,{image_data}",
                                    #                         "detail": detail_level
                                    #                     }
                                    #                 }
                                    #             ]
                                    #         })

                                    print(f"\033[94m[INFO] Using text-only prompt for final report generation to avoid image format errors\033[0m")
                                    final_user_prompt = final_user_prompt_text

                                    # Add the final user prompt (text only, no images) at the end
                                    messages_for_completion.append({
                                        "role": "user",
                                        "content": final_user_prompt
                                    })

                                    print(f"\033[94m[INFO] Generating final report with {len(messages_for_completion)} messages in context\033[0m")

                                    # Generate the final detailed report with full context with retry logic
                                    max_retries = 3
                                    retry_count = 0
                                    detailed_report = None
                                    last_error = None

                                    # First, stream a message to the client that we're generating the final report
                                    if self.message_handler.on_stream:
                                        await self.message_handler.on_stream({
                                            "type": "text",
                                            "content": "Generating final compliance analysis report..."
                                        })

                                    while retry_count < max_retries and detailed_report is None:
                                        try:
                                            # Record retry start time
                                            retry_start = time.time()
                                            print(f"\033[94m[TIMING] Final report retry {retry_count} started at {datetime.datetime.fromtimestamp(retry_start).strftime('%H:%M:%S.%f')[:-3]}\033[0m")

                                            # If we hit image format errors, try to fix common issues
                                            if retry_count > 0:
                                                print(f"\033[93m[WARNING] Retry {retry_count}: Removing all images from messages to avoid format errors\033[0m")

                                            # We already removed images from the final prompt, so no additional action needed here

                                            # Save the final messages in a file for debugging purposes
                                            final_messages_dir = Path("logs/final_report_messages")
                                            final_messages_dir.mkdir(parents=True, exist_ok=True)

                                            # Create a timestamped filename
                                            timestamp = int(time.time())
                                            final_messages_file = final_messages_dir / f"{self.conversation_id}_{timestamp}.json"

                                            # Save messages to file
                                            try:
                                                with open(final_messages_file, 'w') as f:
                                                    # Use a safe JSON serializer that can handle various types
                                                    json.dump({
                                                        "conversation_id": self.conversation_id,
                                                        "timestamp": timestamp,
                                                        "model": self.model,
                                                        "messages": messages_for_completion
                                                    }, f, default=str, indent=2)
                                                print(f"\033[94m[LOG] Saved final report messages to {final_messages_file}\033[0m")
                                            except Exception as e:
                                                print(f"\033[91m[ERROR] Failed to save final report messages to file: {str(e)}\033[0m")

                                            # Record start time for LLM call
                                            llm_call_start = time.time()
                                            print(f"\033[94m[TIMING] Final report LLM call started at {datetime.datetime.fromtimestamp(llm_call_start).strftime('%H:%M:%S.%f')[:-3]}\033[0m")

                                            # Try to make the API call with potential model fallback
                                            api_error = None
                                            model_fallback_attempted = False
                                            current_model = self.model
                                            final_report_response = None

                                            # Try the current model first
                                            try:
                                                final_report_response = await self.client.chat.completions.create(
                                                    model='google/gemini-2.0-flash-001',
                                                    messages=messages_for_completion,
                                                    temperature=self.temperature,
                                                    max_tokens=4000,  # Allow longer response for detailed report
                                                    stream=False  # No streaming for final report
                                                )
                                            except Exception as model_error:
                                                # Set the api_error for fallback logic
                                                api_error = model_error
                                                # Extract the detailed error information
                                                error_msg = str(model_error)
                                                print(f"\033[91m[ERROR] Error with model {current_model} for final report: {error_msg}\033[0m")

                                                # Try to extract structured error data if available
                                                provider_name = "Unknown"
                                                raw_provider_error = ""

                                                try:
                                                    # Check if this is a structured OpenRouter error response
                                                    if hasattr(model_error, 'response') and hasattr(model_error.response, 'json'):
                                                        error_data = model_error.response.json()
                                                        if isinstance(error_data, dict) and 'error' in error_data:
                                                            error_obj = error_data['error']

                                                            # Extract metadata if available
                                                            if 'metadata' in error_obj and error_obj['metadata']:
                                                                metadata = error_obj['metadata']
                                                                provider_name = metadata.get('provider_name', 'Unknown')
                                                                raw_provider_error = metadata.get('raw', '')

                                                                # Log the detailed provider error
                                                                print(f"\033[91m[PROVIDER ERROR] Provider: {provider_name}, Raw error: {raw_provider_error}\033[0m")
                                                except Exception as parse_error:
                                                    print(f"\033[91m[ERROR] Failed to parse error response: {str(parse_error)}\033[0m")

                                                # Stream the detailed error message to the client
                                                if self.message_handler.on_stream:
                                                    error_content = f"OpenRouter Error with {current_model}:\n"
                                                    error_content += f"Provider: {provider_name}\n"
                                                    if raw_provider_error:
                                                        error_content += f"Provider Error: {raw_provider_error}\n"
                                                    error_content += f"Full Error: {error_msg}"

                                                    await self.message_handler.on_stream({
                                                        "type": "error",
                                                        "content": error_content
                                                    })

                                                # Check if this is a provider error that requires retry or fallback
                                                if "Provider returned error" in error_msg:
                                                    # First try the same model (Claude 3.7 Sonnet) with increasing wait times
                                                    claude_model = "anthropic/claude-3.7-sonnet"
                                                    retry_successful = False

                                                    # Try Claude with increasing wait times (2s, 5s, 10s)
                                                    for wait_time in [2, 5, 10]:
                                                        # Stream the retry info to client
                                                        if self.message_handler.on_stream:
                                                            await self.message_handler.on_stream({
                                                                "type": "text",
                                                                "content": f"Retrying with {claude_model} after waiting {wait_time} seconds..."
                                                            })


                                                        # Wait before retrying
                                                        print(f"\033[93m[RETRY] Waiting {wait_time}s before retrying with {claude_model}\033[0m")
                                                        await asyncio.sleep(wait_time)

                                                        try:
                                                            # Try with Claude 3.7 Sonnet
                                                            final_report_response = await self.client.chat.completions.create(
                                                                model=claude_model,
                                                                messages=messages_for_completion,
                                                                temperature=self.temperature,
                                                                max_tokens=4000,  # Allow longer response for detailed report
                                                                stream=False  # No streaming for final report
                                                            )
                                                            # If we get here, the retry worked
                                                            print(f"\033[94m[INFO] Successfully generated report with {claude_model} after waiting {wait_time}s\033[0m")
                                                            retry_successful = True
                                                            current_model = claude_model  # Update current model for logging
                                                            break  # Exit the retry loop
                                                        except Exception as retry_error:
                                                            # Extract the exact error message
                                                            retry_error_msg = str(retry_error)
                                                            # Log the retry error and continue to the next wait time
                                                            print(f"\033[91m[ERROR] Retry with {claude_model} after {wait_time}s wait also failed: {retry_error_msg}\033[0m")

                                                            # Try to extract structured error data if available
                                                            provider_name = "Unknown"
                                                            raw_provider_error = ""

                                                            try:
                                                                # Check if this is a structured OpenRouter error response
                                                                if hasattr(retry_error, 'response') and hasattr(retry_error.response, 'json'):
                                                                    error_data = retry_error.response.json()
                                                                    if isinstance(error_data, dict) and 'error' in error_data:
                                                                        error_obj = error_data['error']

                                                                        # Extract metadata if available
                                                                        if 'metadata' in error_obj and error_obj['metadata']:
                                                                            metadata = error_obj['metadata']
                                                                            provider_name = metadata.get('provider_name', 'Unknown')
                                                                            raw_provider_error = metadata.get('raw', '')

                                                                            # Log the detailed provider error
                                                                            print(f"\033[91m[PROVIDER ERROR] Provider: {provider_name}, Raw error: {raw_provider_error}\033[0m")
                                                            except Exception as parse_error:
                                                                print(f"\033[91m[ERROR] Failed to parse retry error response: {str(parse_error)}\033[0m")

                                                            # Stream the detailed error message to the client
                                                            if self.message_handler.on_stream:
                                                                error_content = f"Retry Error with {claude_model} after {wait_time}s wait:\n"
                                                                error_content += f"Provider: {provider_name}\n"
                                                                if raw_provider_error:
                                                                    error_content += f"Provider Error: {raw_provider_error}\n"
                                                                error_content += f"Full Error: {retry_error_msg}"

                                                                await self.message_handler.on_stream({
                                                                    "type": "error",
                                                                    "content": error_content
                                                                })

                                                    # If Claude retries failed, try fallback models
                                                    if not retry_successful:
                                                        # Try each fallback model in sequence
                                                        for fallback_model in FALLBACK_MODELS:
                                                            # Skip the current model if it's in the fallback list
                                                            if fallback_model == current_model:
                                                                continue

                                                            print(f"\033[93m[MODEL FALLBACK] Trying fallback model for final report: {fallback_model}\033[0m")

                                                            # Notify the user about the model change
                                                            if self.message_handler.on_stream:
                                                                await self.message_handler.on_stream({
                                                                    "type": "text",
                                                                    "content": f"Trying model for final report: {fallback_model}"
                                                                })

                                                            try:
                                                                # Try with the fallback model
                                                                final_report_response = await self.client.chat.completions.create(
                                                                    model=fallback_model,
                                                                    messages=messages_for_completion,
                                                                    temperature=self.temperature,
                                                                    max_tokens=4000,  # Allow longer response for detailed report
                                                                    stream=False  # No streaming for final report
                                                                )
                                                                # If we get here, the fallback worked
                                                                print(f"\033[94m[INFO] Successfully generated report with fallback model {fallback_model}\033[0m")
                                                                current_model = fallback_model  # Update current model for logging
                                                                # Break out of the fallback loop
                                                                break
                                                            except Exception as fallback_error:
                                                                # Extract the exact error message
                                                                fallback_error_msg = str(fallback_error)
                                                                # Log the fallback error and continue to the next model
                                                                print(f"\033[91m[ERROR] Fallback model {fallback_model} also failed for final report: {fallback_error_msg}\033[0m")

                                                                # Try to extract structured error data if available
                                                                provider_name = "Unknown"
                                                                raw_provider_error = ""

                                                                try:
                                                                    # Check if this is a structured OpenRouter error response
                                                                    if hasattr(fallback_error, 'response') and hasattr(fallback_error.response, 'json'):
                                                                        error_data = fallback_error.response.json()
                                                                        if isinstance(error_data, dict) and 'error' in error_data:
                                                                            error_obj = error_data['error']

                                                                            # Extract metadata if available
                                                                            if 'metadata' in error_obj and error_obj['metadata']:
                                                                                metadata = error_obj['metadata']
                                                                                provider_name = metadata.get('provider_name', 'Unknown')
                                                                                raw_provider_error = metadata.get('raw', '')

                                                                                # Log the detailed provider error
                                                                                print(f"\033[91m[PROVIDER ERROR] Provider: {provider_name}, Raw error: {raw_provider_error}\033[0m")
                                                                except Exception as parse_error:
                                                                    print(f"\033[91m[ERROR] Failed to parse fallback error response: {str(parse_error)}\033[0m")

                                                                # Stream the detailed error message to the client
                                                                if self.message_handler.on_stream:
                                                                    error_content = f"Fallback Error with {fallback_model}:\n"
                                                                    error_content += f"Provider: {provider_name}\n"
                                                                    if raw_provider_error:
                                                                        error_content += f"Provider Error: {raw_provider_error}\n"
                                                                    error_content += f"Full Error: {fallback_error_msg}"

                                                                    await self.message_handler.on_stream({
                                                                        "type": "error",
                                                                        "content": error_content
                                                                    })

                                                        # If we still have an error after trying all fallback models, notify the user
                                                        if api_error:
                                                            print(f"\033[91m[ERROR] All models failed for final report\033[0m")
                                                            if self.message_handler.on_stream:
                                                                await self.message_handler.on_stream({
                                                                    "type": "error",
                                                                    "content": "All available models failed for final report. Using partial results."
                                                                })
                                                else:
                                                    # For non-provider errors, just log and continue
                                                    print(f"\033[91m[ERROR] Error generating final report with model {current_model}: {error_msg}\033[0m")

                                                    # Stream the error to client
                                                    if self.message_handler.on_stream:
                                                        await self.message_handler.on_stream({
                                                            "type": "text",
                                                            "content": f"Error generating detailed report with {current_model}. Using partial results."
                                                        })

                                                # For final report, we'll continue with partial results rather than raising the error

                                            # Record end time for LLM call
                                            llm_call_end = time.time()
                                            llm_call_duration = llm_call_end - llm_call_start
                                            print(f"\033[94m[TIMING] Final report LLM call completed in {llm_call_duration:.2f}s with model {current_model}\033[0m")

                                            # Add to timing metrics
                                            timing_metrics["llm_calls"].append({
                                                "purpose": "final_report",
                                                "retry": retry_count,
                                                "start_time": llm_call_start,
                                                "end_time": llm_call_end,
                                                "duration": llm_call_duration
                                            })

                                            # Extract the final detailed report with robust error handling
                                            detailed_report = "[No detailed report could be generated]"

                                            try:
                                                if final_report_response and hasattr(final_report_response, 'choices') and final_report_response.choices:
                                                    if len(final_report_response.choices) > 0 and hasattr(final_report_response.choices[0], 'message'):
                                                        message = final_report_response.choices[0].message
                                                        if hasattr(message, 'content') and message.content:
                                                            detailed_report = message.content
                                                            print(f"\033[94m[INFO] Successfully generated detailed report of {len(detailed_report)} characters\033[0m")
                                                        else:
                                                            print(f"\033[93m[WARNING] Message has no content attribute or empty content\033[0m")
                                                    else:
                                                        print(f"\033[93m[WARNING] No valid choices in response or message missing\033[0m")
                                                else:
                                                    print(f"\033[93m[WARNING] Invalid response format: {final_report_response}\033[0m")
                                            except Exception as extract_error:
                                                print(f"\033[91m[ERROR] Error extracting content from response: {str(extract_error)}\033[0m")
                                                print(f"\033[91m[ERROR] Response structure: {final_report_response}\033[0m")

                                            # Check if we have a valid detailed report
                                            if detailed_report is None or detailed_report.strip() == "":
                                                print(f"\033[91m[ERROR] Final report response has incomplete structure: {final_report_response}\033[0m")
                                                last_error = f"Incomplete API response: {final_report_response}"
                                                retry_count += 1
                                            else:
                                                # We have a valid report, stream it if streaming is enabled
                                                if self.message_handler.on_stream:
                                                    await self.message_handler.on_stream({
                                                        "type": "text",
                                                        "content": f"Final compliance report: {detailed_report[:200]}..."
                                                    })
                                        except Exception as report_error:
                                            print(f"\033[91m[ERROR] Failed to generate detailed report (attempt {retry_count+1}/{max_retries}): {str(report_error)}\033[0m")
                                            last_error = report_error
                                            retry_count += 1
                                            # Record retry end time and add to metrics
                                            retry_end = time.time()
                                            retry_duration = retry_end - retry_start
                                            print(f"\033[94m[TIMING] Final report retry {retry_count} failed after {retry_duration:.2f}s\033[0m")

                                            # Add retry timing to metrics
                                            timing_metrics["final_report_generation"]["retries"].append({
                                                "retry": retry_count,
                                                "start_time": retry_start,
                                                "end_time": retry_end,
                                                "duration": retry_duration,
                                                "error": str(report_error)
                                            })

                                            await asyncio.sleep(1)  # Brief pause between retries

                                    # Record end time for final report generation
                                    final_report_end = time.time()
                                    final_report_duration = final_report_end - final_report_start
                                    timing_metrics["final_report_generation"]["end_time"] = final_report_end
                                    timing_metrics["final_report_generation"]["duration"] = final_report_duration
                                    print(f"\033[94m[TIMING] Final report generation completed in {final_report_duration:.2f}s\033[0m")

                                    # If all retries failed, use a fallback
                                    if detailed_report is None or detailed_report.strip() == "":
                                        print(f"\033[91m[ERROR] All {max_retries} attempts to generate report failed or returned empty result\033[0m")

                                        # Try to salvage information from the attempt_completion tool if we have it
                                        # Extract compliance status and summary using a simplified approach
                                        compliance_status_input = "unknown"
                                        compliance_summary_input = "No detailed information available"

                                        # Only try to extract if attempt_completion_summary is a dictionary
                                        if isinstance(attempt_completion_summary, dict):
                                            # Extract directly using dictionary access with fallbacks
                                            if "compliance_status" in attempt_completion_summary:
                                                compliance_status_input = str(attempt_completion_summary["compliance_status"])
                                            if "compliance_summary" in attempt_completion_summary:
                                                compliance_summary_input = str(attempt_completion_summary["compliance_summary"])

                                            # Check if there's a tool_input field with useful information
                                            if "tool_input" in attempt_completion_summary and isinstance(attempt_completion_summary["tool_input"], dict):
                                                tool_input = attempt_completion_summary["tool_input"]
                                                print(f"\033[93m[WARNING] Using compliance data from tool_input as fallback\033[0m")

                                                # Extract from tool_input if available
                                                if "compliance_status" in tool_input:
                                                    compliance_status_input = str(tool_input["compliance_status"])
                                                if "compliance_summary" in tool_input:
                                                    compliance_summary_input = str(tool_input["compliance_summary"])

                                                # Construct a reasonable detailed report from the available information
                                                report_template = "# Brand Compliance Analysis\n\n## Compliance Status: {0}\n\n## Summary\n{1}\n\n*Note: This report was generated using available information from the initial analysis. A full detailed report could not be generated due to technical limitations.*"
                                                detailed_report = report_template.format(compliance_status_input, compliance_summary_input)
                                                print(f"\033[94m[INFO] Generated fallback report of {len(detailed_report)} characters using available data\033[0m")
                                            else:
                                                detailed_report = f"[Error: After {max_retries} attempts, could not generate detailed compliance report. Last error: {str(last_error)}]"
                                        else:
                                            detailed_report = f"[Error: After {max_retries} attempts, could not generate detailed compliance report. Last error: {str(last_error)}]"
                                    # Combine summary status with detailed report
                                    # Create a simplified final result with string values to avoid type issues
                                    # Extract compliance status
                                    compliance_status = "unknown"
                                    if isinstance(attempt_completion_summary, dict) and "compliance_status" in attempt_completion_summary:
                                        compliance_status = str(attempt_completion_summary["compliance_status"])
                                    elif isinstance(attempt_completion_summary, str):
                                        # Try to extract from string if it contains compliance_status
                                        if "non-compliant" in attempt_completion_summary.lower() or "non_compliant" in attempt_completion_summary.lower():
                                            compliance_status = "non_compliant"
                                        elif "compliant" in attempt_completion_summary.lower():
                                            compliance_status = "compliant"

                                    # Extract summary
                                    summary = ""
                                    if isinstance(attempt_completion_summary, dict) and "compliance_summary" in attempt_completion_summary:
                                        summary = str(attempt_completion_summary["compliance_summary"])
                                    elif isinstance(attempt_completion_summary, str):
                                        # Use the first 500 chars as summary if it's a string
                                        summary = attempt_completion_summary[:500]

                                    # Ensure detailed_report is a string
                                    if not isinstance(detailed_report, str):
                                        print(f"\033[93m[WARNING] detailed_report is not a string: {type(detailed_report)}\033[0m")
                                        detailed_report = str(detailed_report)

                                    # If detailed_report is empty or None, just use a simple message
                                    if not detailed_report or detailed_report == "[No detailed report could be generated]":
                                        print(f"\033[94m[INFO] No detailed report was generated, using simple message\033[0m")
                                        detailed_report = "No detailed compliance report could be generated."

                                    # Create the final result with simple string values
                                    final_result = {
                                        "compliance_status": compliance_status,
                                        "detailed_report": detailed_report,
                                        "summary": summary
                                    }

                                    # Stream the results (both tool and complete events)
                                    if self.message_handler.on_stream:
                                        # Use a simple string for task_detail to avoid any potential issues
                                        task_detail = "Final compliance analysis"
                                        # Only try to extract task_detail if we're sure attempt_completion_summary is a dict
                                        if isinstance(attempt_completion_summary, dict) and "task_detail" in attempt_completion_summary:
                                            try:
                                                task_detail = str(attempt_completion_summary["task_detail"])
                                            except Exception as e:
                                                print(f"\033[93m[WARNING] Error extracting task_detail: {str(e)}\033[0m")

                                        # First ensure we signal this is a tool event
                                        await self.message_handler.on_stream({
                                            "type": "tool",
                                            "content": json.dumps({
                                                "tool_name": "attempt_completion",
                                                "task_detail": task_detail,
                                                "tool_result": final_result
                                            })
                                        })

                                        # Then signal completion with the same data
                                        await self.message_handler.on_stream({
                                            "type": "complete",
                                            "content": json.dumps({
                                                "tool_name": "attempt_completion",
                                                "task_detail": task_detail,
                                                "tool_result": final_result
                                            })
                                        })

                                    # Return the final result
                                    return {
                                        "success": True,
                                        "response": final_result,
                                        "tool_trace": tool_trace,
                                        "iteration_count": iteration_count,
                                        "timing_metrics": {
                                            "total_duration": timing_metrics["total_duration"],
                                            "iterations_count": len(timing_metrics["iterations"]),
                                            "llm_calls_count": len(timing_metrics["llm_calls"]),
                                            "tool_executions_count": len(timing_metrics["tool_executions"]),
                                            "avg_iteration_time": sum(iter_data["duration"] for iter_data in timing_metrics["iterations"]) / len(timing_metrics["iterations"]) if timing_metrics["iterations"] else 0,
                                            "avg_llm_call_time": sum(call_data["duration"] for call_data in timing_metrics["llm_calls"]) / len(timing_metrics["llm_calls"]) if timing_metrics["llm_calls"] else 0,
                                            "avg_tool_execution_time": sum(tool_data["duration"] for tool_data in timing_metrics["tool_executions"]) / len(timing_metrics["tool_executions"]) if timing_metrics["tool_executions"] else 0,
                                            "final_report_generation_time": timing_metrics["final_report_generation"]["duration"]
                                        }
                                    }

                                except Exception as e:
                                    error_msg = f"Error generating detailed report: {str(e)}"
                                    print(f"\033[91m[ERROR] {error_msg}\033[0m")

                                    # Stream error as complete event
                                    if self.message_handler.on_stream:
                                        await self.message_handler.on_stream({
                                            "type": "error",
                                            "content": error_msg
                                        })

                                    # Record end time and calculate total duration
                                    timing_metrics["end_time"] = time.time()
                                    timing_metrics["total_duration"] = timing_metrics["end_time"] - timing_metrics["start_time"]

                                    # Print timing summary for error case
                                    print(f"\033[91m[TIMING SUMMARY] Process failed after {timing_metrics['total_duration']:.2f}s\033[0m")

                                    # Return error response with timing metrics
                                    return {
                                        "success": False,
                                        "error": error_msg,
                                        "tool_trace": tool_trace,
                                        "iteration_count": iteration_count,
                                        "timing_metrics": {
                                            "total_duration": timing_metrics["total_duration"],
                                            "iterations_count": len(timing_metrics["iterations"]),
                                            "llm_calls_count": len(timing_metrics["llm_calls"]),
                                            "tool_executions_count": len(timing_metrics["tool_executions"])
                                        }
                                    }

                    # Handle non-streaming case
                    else:
                        response = completion.choices[0].message

                        # Add the response to our messages
                        if response.content:
                            await self.message_handler.add_message("assistant", response.content)
                            await self.message_handler.stream_content(response.content)

                        # Process any tool calls in the response
                        if response.tool_calls:
                            for tool_call in response.tool_calls:
                                # Extract tool information
                                tool_name = tool_call.function.name

                                # Parse arguments
                                try:
                                    tool_args = json.loads(tool_call.function.arguments)
                                except json.JSONDecodeError:
                                    print(f"\033[91m[ERROR] Failed to parse tool arguments: {tool_call.function.arguments}\033[0m")
                                    tool_args = {}

                                # Inject image data before execution
                                if isinstance(tool_args, dict):
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

                                    # Add image data like in the streaming case
                                    if tool_name in video_tools:
                                        tool_args["images_base64"] = [image_base64] if image_base64 else []
                                    else:
                                        tool_args["image_base64"] = image_base64

                                # If executing a video tool and tool_args has a timestamp, attach the corresponding frame's base64
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
                                if tool_name in video_tools and "timestamp" in tool_args and frames:
                                    # Log the number of frames available
                                    print(f"\033[93m[DEBUG] Processing {len(frames)} frames for {tool_name}\033[0m")

                                    # Find the frame with the closest timestamp
                                    target_ts = tool_args["timestamp"]
                                    closest_frame = min(frames, key=lambda f: abs(f.get("timestamp", 0) - target_ts))

                                    # Log the closest frame data
                                    print(f"\033[93m[DEBUG] Closest frame keys: {list(closest_frame.keys())}\033[0m")

                                    # Try to get the base64 data from either key (image_data or base64)
                                    frame_base64 = closest_frame.get("image_data") or closest_frame.get("base64")

                                    if frame_base64:
                                        print(f"\033[92m[INFO] Found base64 data for frame at timestamp {target_ts} (length: {len(frame_base64)})\033[0m")
                                        # Set both image_base64 and image_data for backward compatibility
                                        tool_args["image_base64"] = frame_base64
                                        tool_args["image_data"] = frame_base64

                                        # Always add the closest frame to images_base64 for all video tools
                                        # This ensures that even if we don't find nearby frames, we at least have one frame
                                        tool_args["images_base64"] = [frame_base64]
                                        tool_args["images_data"] = [frame_base64]
                                        print(f"\033[92m[INFO] Added closest frame to images_base64 for {tool_name}\033[0m")

                                        # For tools that support multiple frames, also add all nearby frames
                                        if tool_name in ["get_video_color_scheme", "check_video_frame_specs", "get_video_fonts", "extract_verbal_content"]:
                                            # Get all frames within 1 second of the target timestamp
                                            nearby_frames = [
                                                f for f in frames
                                                if abs(f.get("timestamp", 0) - target_ts) <= 1
                                            ]

                                            print(f"\033[93m[DEBUG] Found {len(nearby_frames)} nearby frames within 1 second of timestamp {target_ts}\033[0m")

                                            # Extract base64 data from each frame
                                            images_base64 = []
                                            for frame in nearby_frames:
                                                # Try both keys for backward compatibility
                                                frame_data = frame.get("image_data") or frame.get("base64")
                                                if frame_data:
                                                    images_base64.append(frame_data)
                                                else:
                                                    print(f"\033[91m[ERROR] Frame missing image data. Frame keys: {list(frame.keys())}\033[0m")

                                            if images_base64:
                                                print(f"\033[92m[INFO] Adding {len(images_base64)} frames to images_base64 for {tool_name}\033[0m")
                                                # Set both images_base64 and images_data for backward compatibility
                                                tool_args["images_base64"] = images_base64
                                                tool_args["images_data"] = images_base64
                                            else:
                                                print(f"\033[91m[ERROR] No valid image data found in any nearby frames for {tool_name}\033[0m")
                                    else:
                                        print(f"\033[91m[ERROR] No image data found in closest frame for {tool_name}. Frame keys: {list(closest_frame.keys())}\033[0m")

                                # Execute the tool and stream its result
                                try:
                                    print(f"\033[92m[TOOL EXEC] Executing {tool_name}...\033[0m")
                                    tool_result = await stream_tool_execution(
                                        tool_name,
                                        tool_args,
                                        self.message_handler,
                                        tool_trace,
                                        image_base64,
                                        frames
                                    )
                                except Exception as e:
                                    print(f"\033[91m[ERROR] Exception in {tool_name}: {e}\033[0m")
                                    tool_result = {"error": str(e)}

                                # Add tool result as a message
                                await self.message_handler.add_message(
                                    "tool",
                                    {
                                        "tool_call_id": tool_call.id,
                                        "name": tool_name,
                                        "content": str(tool_result)
                                    }
                                )

                                # If attempt_completion, return result
                                if tool_name == "attempt_completion":
                                    attempt_completion_result = tool_result
                                    await self.message_handler.stream_complete(tool_result)
                                    # Record end time and calculate total duration
                                    timing_metrics["end_time"] = time.time()
                                    timing_metrics["total_duration"] = timing_metrics["end_time"] - timing_metrics["start_time"]

                                    # Print timing summary
                                    print(f"\033[92m[TIMING SUMMARY] Total process duration: {timing_metrics['total_duration']:.2f}s\033[0m")
                                    print(f"\033[92m[TIMING SUMMARY] Number of iterations: {len(timing_metrics['iterations'])}\033[0m")
                                    print(f"\033[92m[TIMING SUMMARY] Number of LLM calls: {len(timing_metrics['llm_calls'])}\033[0m")
                                    print(f"\033[92m[TIMING SUMMARY] Number of tool executions: {len(timing_metrics['tool_executions'])}\033[0m")

                                    # Calculate average times
                                    avg_iteration = sum(iter_data["duration"] for iter_data in timing_metrics["iterations"]) / len(timing_metrics["iterations"]) if timing_metrics["iterations"] else 0
                                    avg_llm_call = sum(call_data["duration"] for call_data in timing_metrics["llm_calls"]) / len(timing_metrics["llm_calls"]) if timing_metrics["llm_calls"] else 0
                                    avg_tool_exec = sum(tool_data["duration"] for tool_data in timing_metrics["tool_executions"]) / len(timing_metrics["tool_executions"]) if timing_metrics["tool_executions"] else 0

                                    print(f"\033[92m[TIMING SUMMARY] Average iteration time: {avg_iteration:.2f}s\033[0m")
                                    print(f"\033[92m[TIMING SUMMARY] Average LLM call time: {avg_llm_call:.2f}s\033[0m")
                                    print(f"\033[92m[TIMING SUMMARY] Average tool execution time: {avg_tool_exec:.2f}s\033[0m")

                                    return {
                                        "success": True,
                                        "response": tool_result,
                                        "tool_trace": tool_trace,
                                        "model": self.model,
                                        "timing_metrics": {
                                            "total_duration": timing_metrics["total_duration"],
                                            "iterations_count": len(timing_metrics["iterations"]),
                                            "llm_calls_count": len(timing_metrics["llm_calls"]),
                                            "tool_executions_count": len(timing_metrics["tool_executions"]),
                                            "avg_iteration_time": avg_iteration,
                                            "avg_llm_call_time": avg_llm_call,
                                            "avg_tool_execution_time": avg_tool_exec
                                        }
                                    }
                except Exception as e:
                    error_msg = str(e)

                    # More detailed error logging with specific error types
                    if "429" in error_msg or "rate limit" in error_msg.lower():
                        print(f"\033[91m[ERROR] Rate limit exceeded on OpenRouter API: {error_msg}\033[0m")
                    elif "401" in error_msg or "auth" in error_msg.lower():
                        print(f"\033[91m[ERROR] Authentication error with OpenRouter API: {error_msg}\033[0m")
                    elif "400" in error_msg:
                        print(f"\033[91m[ERROR] Bad request to OpenRouter API (possible token limit): {error_msg}\033[0m")
                        # If this is a token limit issue, reduce history more aggressively for next iteration
                        if token_estimate > 10000:
                            # Force a more aggressive limit on messages for the next iteration
                            print(f"\033[93m[WARNING] High token count detected ({token_estimate}), will reduce context\033[0m")
                            max_msgs = 5  # More aggressive limit on recent messages
                    else:
                        print(f"\033[91m[ERROR] Error calling OpenRouter API: {error_msg}\033[0m")

                    # Check if we've reached max retries
                    if retry_count <= 0:
                        await self.message_handler.stream_content("Failed to get a response from the model. Please try again.")
                        return {
                            "success": False,
                            "error": f"Failed to get a response after multiple retries: {str(e)}",
                            "tool_trace": tool_trace,
                            "model": self.model
                        }


                # Check if we've reached max retries
                if retry_count <= 0:
                    await self.message_handler.stream_content("Failed to get a response from the model. Please try again.")
                    return {
                        "success": False,
                        "error": f"Failed to get a response after multiple retries: {str(e)}",
                        "tool_trace": tool_trace,
                        "model": self.model
                    }

                    # Retry with backoff
                    retry_count -= 1
                    wait_time = 2 * (3 - retry_count)  # 2, 4, 6 seconds
                    print(f"\033[93m[WARNING] OpenRouterAgent.process: Retrying in {wait_time}s (retries left: {retry_count})\033[0m")
                    await asyncio.sleep(wait_time)
                    continue

                # Process iteration milestones and provide appropriate feedback
                if iteration_count >= max_iterations:
                    # We've hit max iterations, suggest completion
                    print(f"\033[93m[INFO] OpenRouterAgent.process: Reached {iteration_count} iterations without attempt_completion, suggesting completion\033[0m")
                    suggestion_message = get_force_completion_prompt(self.model)
                    await self.message_handler.add_message("user", suggestion_message)
                    await self.message_handler.stream_content("Checking if analysis is ready for completion...")
                elif iteration_count % 10 == 0:
                    # Hit a multiple of 10 iterations, provide a reminder
                    print(f"\033[93m[INFO] OpenRouterAgent.process: Reached {iteration_count} iterations, providing reminder\033[0m")
                    reminder_message = get_iteration_milestone_prompt(self.model, iteration_count)
                    await self.message_handler.add_message("user", reminder_message)
                    await self.message_handler.stream_content(f"Iteration {iteration_count} reminder sent...")
                else:
                    # Just continue with normal iteration
                    await self.message_handler.stream_content("Continuing the analysis...")

                # Continue the loop for the next LLM response
                continue
        except Exception as e:
            # Handle any unexpected errors in the main loop
            print(f"\033[91m[ERROR] Unexpected error in OpenRouterAgent.process: {e}\033[0m")
            traceback.print_exc()

            # Notify the user about the error
            await self.message_handler.stream_content("An unexpected error occurred, but we'll generate a report with available information.")

            # Extract any useful information from the error
            error_message = str(e)

            # Return a simple error result
            return {
                "success": False,
                "error": f"Unexpected error: {error_message}",
                "tool_trace": tool_trace,
                "model": self.model
            }

        # If we reach here, we exited the loop without a completion
        return {
            "success": False,
            "error": "No completion was produced",
            "tool_trace": tool_trace,
            "model": self.model
        }
