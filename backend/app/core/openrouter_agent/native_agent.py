import os
import json
import asyncio
import time
import traceback
import uuid
from typing import List, Dict, Any, Optional, Callable, Awaitable
import re

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

# Constants for timeout settings
OPENROUTER_TIMEOUT = 120  # 2 minutes timeout for OpenRouter API calls

class OpenRouterAgent:
    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-opus-20240229",
        on_stream: Optional[Callable] = None,
        temperature: float = 0.2,
        max_tokens: int = 4000,
        stream: bool = True,
        system_prompt: Optional[str] = None,
        save_messages: bool = True,
    ):
        """Initialize a new OpenRouter agent with native tool calling capabilities.
        
        Args:
            api_key: OpenRouter API key
            model: Model identifier to use
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

        # Track iteration count to enforce completion after max_iterations
        iteration_count = 0

        # Track last response time to detect timeouts
        last_response_time = time.time()
        
        # Add the user prompt as a message, including image if provided
        if image_base64:
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
                print(f"\033[94m[LOG] OpenRouterAgent.process: Starting iteration {iteration_count}\033[0m")
                
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
                        max_msgs = None  # No pruning needed
                    
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
                    
                    completion = await self.client.chat.completions.create(
                        model=self.model,
                        messages=formatted_messages,
                        tools=self.tools,  # Pass the tool schemas
                        temperature=self.temperature,
                        max_tokens=current_max_tokens,
                        stream=self.stream,
                        timeout=self.timeout
                    )
                    # Update the last response time since we got a response
                    last_response_time = time.time()
                    
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
                            print(f"\033[91m[ERROR] Error processing completion chunks: {e}\033[0m")
                            # Stream the error to client
                            if self.message_handler.on_stream:
                                await self.message_handler.on_stream({
                                    "type": "error",
                                    "content": f"Error processing response: {str(e)}"
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
                                
                                # Execute the tool and stream its result
                                try:
                                    print(f"\033[92m[TOOL EXEC] Executing {tool_name}...\033[0m")
                                    
                                    # First, stream that we're executing the tool (better UX)
                                    if self.message_handler.on_stream:
                                        await self.message_handler.on_stream({
                                            "type": "text",
                                            "content": f"Executing tool: {tool_name}..."
                                        })
                                    
                                    # Execute the tool - returns the proper OpenRouter compatible message format
                                    result_format = await execute_and_process_tool(
                                        tool_name, 
                                        tool_args,
                                        image_base64,
                                        frames,
                                        tool_call_id=tool_id,  # Pass the tool_call_id from the API response
                                        on_stream=self.message_handler.on_stream
                                    )
                                    
                                    # Extract the actual tool result from the message format
                                    tool_result = result_format["content"] if isinstance(result_format, dict) and "content" in result_format else str(result_format)
                                    
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
                                
                                # Try multiple approaches to extract useful data
                                attempt_completion_summary = {}
                                
                                # Approach 1: If it's already a dictionary, use it directly
                                if isinstance(tool_result, dict):
                                    attempt_completion_summary = tool_result
                                
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
                                                attempt_completion_summary = json.loads(cleaned_result)
                                            except:
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
                                    print(f"\033[94m[INFO] Generating detailed compliance report...\033[0m")
                                    
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
                                    
                                    # Look for the image in previous messages
                                    for msg in previous_messages:
                                        if msg.get("role") == "user" and msg.get("content"):
                                            content = msg.get("content")
                                            if isinstance(content, list):
                                                for item in content:
                                                    if isinstance(item, dict) and item.get("type") == "image_url":
                                                        image_content = item
                                                        original_image_message = msg
                                                        break
                                                if image_content:
                                                    break
                                    
                                    print(f"\033[94m[INFO] Image content found for final report: {image_content is not None}\033[0m")
                                    
                                    # Construct the user prompt with the summary and instructions
                                    final_user_prompt_text = f"""Generate a FINAL DETAILED brand compliance analysis report for the image shown.

Here is a summary of key compliance findings from the analysis:
{json.dumps(attempt_completion_summary, indent=2)}

Your final report MUST include:

1. Executive Summary - Overall compliance verdict with critical issues
2. Methodology - How you analyzed the asset against brand guidelines
3. Detailed Element Analysis - For logo, typography, color palette, and other visual elements
4. Brand Guideline Compliance - Section-by-section compliance with evidence
5. Recommendations - Specific actions to achieve full compliance
6. Conclusion - Final compliance rating with justification

IMPORTANT: Check image quality carefully for blurring, pixelation, or distortion issues.
Pay special attention to spacing, alignment, and clarity of all brand elements.
The report MUST be extremely detailed, professionally formatted, and actionable."""
                                    
                                    # Create a message list that includes system prompt and previous message context
                                    messages_for_completion = [
                                        {"role": "system", "content": final_report_prompt}
                                    ]
                                    
                                    # Important: Add ALL previous messages including system messages and ALL tool results
                                    # This ensures the model has access to the complete conversation history
                                    for msg in previous_messages:
                                        messages_for_completion.append(msg)
                                    
                                    # Construct the final user prompt with the image
                                    # If we found an image in the previous messages, include it in the final prompt
                                    if image_content:
                                        # Create a multimodal content array with both text and image
                                        final_user_prompt = [
                                            {"type": "text", "text": final_user_prompt_text},
                                            image_content  # The image content we extracted earlier
                                        ]
                                    else:
                                        # If no image found, just use the text prompt
                                        print(f"\033[93m[WARNING] No image found for final report generation\033[0m")
                                        final_user_prompt = final_user_prompt_text
                                    
                                    # Add the final user prompt with image at the end
                                    messages_for_completion.append({
                                        "role": "user", 
                                        "content": final_user_prompt
                                    })
                                    
                                    print(f"\033[94m[INFO] Generating final report with {len(messages_for_completion)} messages in context\033[0m")
                                    
                                    # Generate the final detailed report with full context
                                    final_report_response = await self.client.chat.completions.create(
                                        model=self.model,
                                        messages=messages_for_completion,
                                        temperature=self.temperature,
                                        max_tokens=4000,  # Allow longer response for detailed report
                                        stream=False  # No streaming for final report
                                    )
                                    
                                    # Extract the final detailed report
                                    detailed_report = final_report_response.choices[0].message.content
                                    
                                    # Combine summary status with detailed report
                                    # Ensure attempt_completion_summary is not None before accessing its properties
                                    if attempt_completion_summary is None:
                                        attempt_completion_summary = {}  # Use empty dict as fallback
                                        print(f"\033[93m[WARNING] attempt_completion_summary is None, using empty dict fallback\033[0m")
                                    
                                    final_result = {
                                        "compliance_status": attempt_completion_summary.get("compliance_status", "unknown"),
                                        "detailed_report": detailed_report,
                                        "summary": attempt_completion_summary.get("compliance_summary", "")
                                    }
                                    
                                    # Stream the results (both tool and complete events)
                                    if self.message_handler.on_stream:
                                        # First ensure we signal this is a tool event
                                        await self.message_handler.on_stream({
                                            "type": "tool",
                                            "content": json.dumps({
                                                "tool_name": "attempt_completion",
                                                "task_detail": attempt_completion_summary.get("task_detail", "Final compliance analysis"),
                                                "tool_result": final_result
                                            })
                                        })
                                        
                                        # Then signal completion with the same data
                                        await self.message_handler.on_stream({
                                            "type": "complete",
                                            "content": json.dumps({
                                                "tool_name": "attempt_completion",
                                                "task_detail": attempt_completion_summary.get("task_detail", "Final compliance analysis"),
                                                "tool_result": final_result
                                            })
                                        })
                                    
                                    # Return the final result
                                    return {
                                        "success": True,
                                        "response": final_result,
                                        "tool_trace": tool_trace,
                                        "iteration_count": iteration_count
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
                                    
                                    # Return error response
                                    return {
                                        "success": False,
                                        "error": error_msg,
                                        "tool_trace": tool_trace,
                                        "iteration_count": iteration_count
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
                                    return {
                                        "success": True,
                                        "response": tool_result,
                                        "tool_trace": tool_trace,
                                        "model": self.model
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
            
            await self.message_handler.stream_content("An unexpected error occurred. Please try again.")
            
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
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
