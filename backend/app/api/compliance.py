import os
import base64
import mimetypes
import tempfile
import shutil
import json
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    Body,
    Request,
    status,
)
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any, List
from uuid import uuid4
import asyncio
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.agent.index import Agent, encode_image_to_base64
from app.core.agent.prompt import system_prompt, gemini_system_prompt
from app.core.video_agent.video_agent_class import VideoAgent
from app.db.database import create_feedback, get_user_feedback

import re
import xmltodict

router = APIRouter()


@router.post("/compliance/check-image")
async def check_image_compliance(
    file: UploadFile = File(...),
    text: Optional[str] = Form("Analyze this image for brand compliance."),
    current_user: dict = Depends(get_current_user),
):
    import inspect
    import time
    start_time = time.time()
    print(f"\033[94m[LOG] check_image_compliance: Start at {start_time:.3f} (line {inspect.currentframe().f_lineno})\033[0m")
    print(f"\033[96m[LOG] check_image_compliance: Received file: {file.filename}, content_type: {file.content_type} (line {inspect.currentframe().f_lineno})\033[0m")
    print(f"\033[96m[LOG] check_image_compliance: User: {current_user.get('username', 'unknown')} (line {inspect.currentframe().f_lineno})\033[0m")
    """
    Upload an image and check it for brand compliance.

    This endpoint:
    1. Accepts an image file upload
    2. Processes the image using the compliance agent
    3. Streams the results back to the client
    """
    # Validate file type
    content_type = file.content_type or ""
    print(f"\033[93m[LOG] check_image_compliance: Validating file type: {content_type} (line {inspect.currentframe().f_lineno})\033[0m")
    if not content_type.startswith("image/"):
        print(f"\033[91m[LOG] check_image_compliance: Invalid file type (line {inspect.currentframe().f_lineno})\033[0m")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files are allowed",
        )

    # Create a temporary file to store the uploaded image
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=f".{content_type.split('/')[-1]}"
    ) as temp_file:
        print(f"\033[92m[LOG] check_image_compliance: Creating temp file at {temp_file.name} (line {inspect.currentframe().f_lineno})\033[0m")
        # Write the uploaded file content to the temporary file
        shutil.copyfileobj(file.file, temp_file)
        temp_file_path = temp_file.name

    try:
        print(f"\033[92m[LOG] check_image_compliance: Encoding image to base64 (line {inspect.currentframe().f_lineno})\033[0m")
        # Get the base64 encoding of the image
        image_base64, media_type = encode_image_to_base64(temp_file_path)
        print(f"\033[92m[LOG] check_image_compliance: Encoded image, media_type: {media_type} (line {inspect.currentframe().f_lineno})\033[0m")

        # Create a streaming response
        print(f"\033[94m[LOG] check_image_compliance: Creating StreamingResponse (line {inspect.currentframe().f_lineno})\033[0m")
        stream_start = time.time()
        print(f"\033[94m[LOG] check_image_compliance: Streaming will start at {stream_start:.3f}\033[0m")
        response = StreamingResponse(
            process_image_and_stream(
                image_base64=image_base64,
                media_type=media_type,
                text=text,
                user_id=current_user["id"],
            ),
            media_type="text/event-stream",
        )
        stream_end = time.time()
        print(f"\033[94m[LOG] check_image_compliance: StreamingResponse created at {stream_end:.3f}, elapsed: {stream_end - stream_start:.3f}s\033[0m")
        return response
    except Exception as e:
        print(f"\033[91m[LOG] check_image_compliance: Exception occurred: {e} (line {inspect.currentframe().f_lineno})\033[0m")
        # Handle any errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing image: {str(e)}",
        )
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            print(f"\033[91m[LOG] check_image_compliance: Deleting temp file {temp_file_path} (line {inspect.currentframe().f_lineno})\033[0m")
            os.unlink(temp_file_path)


import inspect
async def process_image_and_stream(
    image_base64: str, media_type: str, text: str, user_id: str
):
    print(f"[LOG] process_image_and_stream: Start (line {inspect.currentframe().f_lineno})")
    print(f"[LOG] process_image_and_stream: Using model: anthropic/claude-3-7-sonnet-20250219 (line {inspect.currentframe().f_lineno})")
    print(f"[LOG] process_image_and_stream: user_id: {user_id} (line {inspect.currentframe().f_lineno})")
    print(f"[LOG] process_image_and_stream: media_type: {media_type} (line {inspect.currentframe().f_lineno})")
    print(f"[LOG] process_image_and_stream: text: {text} (line {inspect.currentframe().f_lineno})")
    """
    Process an image using the compliance agent and stream the results.

    Args:
        image_base64: Base64-encoded image data
        media_type: Media type of the image
        text: Text prompt to send with the image
        user_id: ID of the current user

    Yields:
        Server-sent events with the streaming results
    """
    # Create a message ID for this request
    message_id = str(uuid4())

    # Create a queue for the streaming data
    queue = asyncio.Queue()

    # Define the streaming callback
    async def on_stream(data: Dict[str, Any]):
        await queue.put(data)

    # Get user feedback to include in the system prompt
    user_feedback_list = get_user_feedback(user_id)
    print(f"[LOG] process_image_and_stream: Retrieved {len(user_feedback_list) if user_feedback_list else 0} user feedback items (line {inspect.currentframe().f_lineno})")

    # Prepare custom system prompt with user feedback if available
    custom_system_prompt = gemini_system_prompt
    if user_feedback_list and len(user_feedback_list) > 0:
        print(f"[LOG] process_image_and_stream: Adding user feedback to system prompt (line {inspect.currentframe().f_lineno})")
        feedback_section = "\n\n<User Memories and Feedback> !IMPORTANT! \n This is feedback given by the user in previous compliance checks. You need to make sure to acknolwedge your knowledge of these feedback in your initial detailed plan and say that you will follow them \n"
        for i, feedback in enumerate(user_feedback_list):
            feedback_content = feedback["content"]
            feedback_date = feedback["created_at"]
            feedback_section += (
                f"- Memory {i+1} ({feedback_date}): {feedback_content}\n"
            )
            print(f"[LOG] process_image_and_stream: Feedback {i+1}: {feedback_content} (line {inspect.currentframe().f_lineno})")

        # Add feedback section to system prompt
        custom_system_prompt = gemini_system_prompt + feedback_section
        print(f"[LOG] process_image_and_stream: System prompt updated with user feedback (line {inspect.currentframe().f_lineno})")
    else:
        print(f"[LOG] process_image_and_stream: No user feedback found (line {inspect.currentframe().f_lineno})")

    # Create an OpenRouterAgent instance using our native implementation with Claude 3.7 Sonnet
    # Claude is better suited for image compliance analysis with its ability to detect visual details
    print(f"[LOG] process_image_and_stream: Instantiating OpenRouterNativeAgent with Claude 3.7 (line {inspect.currentframe().f_lineno})")
    from app.core.openrouter_agent.native_agent import OpenRouterAgent as OpenRouterNativeAgent
    
    # Get the OpenRouter API key from environment variables
    import os
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    if not OPENROUTER_API_KEY:
        print(f"\033[91m[ERROR] OPENROUTER_API_KEY not found in environment variables\033[0m")
        raise ValueError("OPENROUTER_API_KEY environment variable is required")
    
    print(f"\033[94m[INFO] Using OpenRouter API key: {OPENROUTER_API_KEY[:5]}...\033[0m")
    
    # Note: The OpenRouterNativeAgent uses OPENROUTER_TIMEOUT internally, so we don't pass timeout here
    agent = OpenRouterNativeAgent(
        api_key=OPENROUTER_API_KEY,  # Required parameter
        model="anthropic/claude-3.7-sonnet",  # Using Claude 3.7 Sonnet for improved compliance analysis
        on_stream=on_stream,
        system_prompt=custom_system_prompt,
        temperature=0.1  # Lower temperature for more consistent outputs
    )

    # Start the agent process in a background task
    print(f"[LOG] process_image_and_stream: Creating processing_task for OpenRouterAgent (line {inspect.currentframe().f_lineno})")
    try:
        # Ensure image_base64 doesn't include the prefix if it's already there
        if image_base64.startswith("data:image/"):
            # Extract only the base64 portion if it includes the data URL prefix
            image_base64 = image_base64.split(",")[1]
        
        print(f"[DEBUG] Image base64 length: {len(image_base64)} characters")
        
        processing_task = asyncio.create_task(
            agent.process(
                user_prompt=text,
                image_base64=image_base64,
                # No need to pass media_type - native agent handles image format internally
            )
        )
    except Exception as e:
        print(f"[ERROR] process_image_and_stream: Exception when creating processing_task: {e} (line {inspect.currentframe().f_lineno})")
        import traceback
        traceback.print_exc()
        raise

    # Stream the results
    try:
        tool_buffer = ""
        tool_buffering = False

        import time
        last_yield_time = time.time()
        while True:
            try:
                # Get data from the queue with a timeout
                data = await asyncio.wait_for(queue.get(), timeout=1.0)
                print(f"[LOG] process_image_and_stream: Received data from queue: {data} (line {inspect.currentframe().f_lineno})")

                # Process data from the native agent implementation
                event_type = data.get("type")
                print(f"[LOG] process_image_and_stream: Received event_type: {event_type} (line {inspect.currentframe().f_lineno})")
                
                # Handle text events - these come directly from the model
                if event_type == "text":
                    # If we were buffering a tool, yield it now
                    if tool_buffering and tool_buffer:
                        try:
                            parsed = json.loads(tool_buffer)
                            event_data = f"data: tool:{json.dumps(parsed)}\n\n"
                            print(f"[LOG] process_image_and_stream: Yielding parsed tool event_data: {event_data.strip()} (line {inspect.currentframe().f_lineno})")
                            yield event_data
                        except Exception as e:
                            print(f"[LOG] process_image_and_stream: Tool buffer not valid JSON at flush: {e} (line {inspect.currentframe().f_lineno})")
                        tool_buffer = ""
                        tool_buffering = False

                    content = data["content"]
                    print(f"[LOG] process_image_and_stream: Handling text content: {content} (line {inspect.currentframe().f_lineno})")
                    
                    # With native agent, we don't need to parse XML anymore
                    # Simply pass through the text content
                    event_data = f"data: text:{content}\n\n"
                    print(f"[LOG] process_image_and_stream: Yielding text event_data: {event_data.strip()} (line {inspect.currentframe().f_lineno})")
                    yield event_data
                    last_yield_time = time.time()
                elif event_type == "tool":
                    # With the native implementation, tool events are properly formatted JSON
                    print(f"[LOG] process_image_and_stream: Processing tool event (line {inspect.currentframe().f_lineno})")
                    
                    # Extract the tool details
                    tool_content = data.get("content", "{}")
                    print(f"[LOG] process_image_and_stream: Tool content type: {type(tool_content)} (line {inspect.currentframe().f_lineno})")
                    
                    # If it's a string, try to parse it as JSON
                    if isinstance(tool_content, str):
                        try:
                            tool_content = json.loads(tool_content)
                            print(f"[LOG] process_image_and_stream: Parsed tool_content as JSON (line {inspect.currentframe().f_lineno})")
                        except Exception as e:
                            print(f"[LOG] process_image_and_stream: Failed to parse tool_content as JSON: {e} (line {inspect.currentframe().f_lineno})")
                            # Use as is if it's not valid JSON
                    
                    # Check if this is an attempt_completion tool - special handling for completion status
                    tool_name = tool_content.get("tool_name") if isinstance(tool_content, dict) else None
                    print(f"[LOG] process_image_and_stream: Tool name: {tool_name} (line {inspect.currentframe().f_lineno})")
                    
                    # Forward the tool event to the client
                    event_data = f"data: tool:{json.dumps(tool_content) if isinstance(tool_content, dict) else tool_content}\n\n"
                    print(f"[LOG] process_image_and_stream: Yielding tool event_data: {event_data.strip()} (line {inspect.currentframe().f_lineno})")
                    yield event_data
                    last_yield_time = time.time()
                elif event_type == "complete":
                    # If we were buffering a tool, yield it now
                    if tool_buffering and tool_buffer:
                        try:
                            parsed = json.loads(tool_buffer)
                            event_data = f"data: tool:{json.dumps(parsed)}\n\n"
                            print(f"[LOG] process_image_and_stream: Yielding parsed tool event_data: {event_data.strip()} (line {inspect.currentframe().f_lineno})")
                            yield event_data
                        except Exception as e:
                            print(f"[LOG] process_image_and_stream: Tool buffer not valid JSON at flush: {e} (line {inspect.currentframe().f_lineno})")
                        tool_buffer = ""
                        tool_buffering = False

                    # For the native agent, the complete event contains the final detailed compliance report
                    # with compliance_status, detailed_report, and summary
                    final_answer = data.get("content", "")
                    print(f"[LOG] process_image_and_stream: Processing complete event with content type: {type(final_answer)} (line {inspect.currentframe().f_lineno})")
                    
                    # If it's a string, try to parse it as JSON (in case it's serialized)
                    if isinstance(final_answer, str):
                        try:
                            # Check if it looks like JSON
                            if final_answer.strip().startswith('{'):
                                parsed_answer = json.loads(final_answer)
                                final_answer = parsed_answer
                                print(f"[LOG] process_image_and_stream: Parsed complete content as JSON (line {inspect.currentframe().f_lineno})")
                        except Exception as e:
                            print(f"[LOG] process_image_and_stream: Content is not JSON: {e} (line {inspect.currentframe().f_lineno})")
                            # Use as is if parsing fails
                    
                    # Format the completion event based on content type
                    if isinstance(final_answer, dict):
                        # Our native agent returns a structured response
                        event_data = f"data: complete:{json.dumps(final_answer)}\n\n"
                    else:
                        # Just a string - pass as is
                        event_data = f"data: complete:{final_answer}\n\n"
                    
                    print(f"[LOG] process_image_and_stream: Yielding complete event_data: {event_data.strip()[:200]}... (line {inspect.currentframe().f_lineno})")
                    yield event_data
                    break
                elif event_type in ("status", "error"):
                    # If we were buffering a tool, yield it now
                    if tool_buffering and tool_buffer:
                        try:
                            parsed = json.loads(tool_buffer)
                            event_data = f"data: tool:{json.dumps(parsed)}\n\n"
                            print(f"[LOG] process_image_and_stream: Yielding parsed tool event_data: {event_data.strip()} (line {inspect.currentframe().f_lineno})")
                            yield event_data
                        except Exception as e:
                            print(f"[LOG] process_image_and_stream: Tool buffer not valid JSON at flush: {e} (line {inspect.currentframe().f_lineno})")
                        tool_buffer = ""
                        tool_buffering = False

                    event_data = f"data: {event_type}:{data.get('content','')}\n\n"
                    print(f"[LOG] process_image_and_stream: Yielding {event_type} event_data: {event_data.strip()} (line {inspect.currentframe().f_lineno})")
                    yield event_data
                    last_yield_time = time.time()
                else:
                    # If we were buffering a tool, yield it now
                    if tool_buffering and tool_buffer:
                        try:
                            parsed = json.loads(tool_buffer)
                            event_data = f"data: tool:{json.dumps(parsed)}\n\n"
                            print(f"[LOG] process_image_and_stream: Yielding parsed tool event_data: {event_data.strip()} (line {inspect.currentframe().f_lineno})")
                            yield event_data
                        except Exception as e:
                            print(f"[LOG] process_image_and_stream: Tool buffer not valid JSON at flush: {e} (line {inspect.currentframe().f_lineno})")
                        tool_buffer = ""
                        tool_buffering = False

                    event_data = f"data: {event_type}:{data.get('content','')}\n\n"
                    print(f"[LOG] process_image_and_stream: Yielding other event_data: {event_data.strip()} (line {inspect.currentframe().f_lineno})")
                    yield event_data
                    last_yield_time = time.time()

                queue.task_done()
                print(f"[LOG] process_image_and_stream: Marked queue item as done (line {inspect.currentframe().f_lineno})")
            except asyncio.TimeoutError:
                print(f"[LOG] process_image_and_stream: Timeout waiting for queue item (line {inspect.currentframe().f_lineno})")
                # If more than 5 seconds have passed since last yield, send a user-friendly keep-alive tool event
                if time.time() - last_yield_time > 15:
                    keep_alive_event = {
                        "tool_name": "keep_alive",
                        "tool_input": {},
                        "task_detail": "Still working on your image compliance analysis. This may take a few moments..."
                    }
                    event_data = f"data: tool:{json.dumps(keep_alive_event)}\n\n"
                    print(f"[LOG] process_image_and_stream: Yielding keep-alive tool event: {event_data.strip()} (line {inspect.currentframe().f_lineno})")
                    yield event_data
                    last_yield_time = time.time()
                if processing_task.done():
                    print(f"[LOG] process_image_and_stream: processing_task is done (line {inspect.currentframe().f_lineno})")
                    # Do not send any "complete" event here; only yield "complete" when received from the agent
                    break
    except asyncio.CancelledError:
        print(f"[LOG] process_image_and_stream: asyncio.CancelledError (line {inspect.currentframe().f_lineno})")
        if not processing_task.done():
            processing_task.cancel()
        raise
    except Exception as e:
        print(f"[ERROR] process_image_and_stream: Exception in streaming loop: {e} (line {inspect.currentframe().f_lineno})")
        import traceback
        traceback.print_exc()
        raise
    finally:
        if not processing_task.done():
            processing_task.cancel()
        print(f"[LOG] process_image_and_stream: processing_task cancelled in finally (line {inspect.currentframe().f_lineno})")


@router.post("/compliance/check-video")
@router.get("/compliance/check-video")
async def check_video_compliance(
    request: Request,
    data: Dict[str, Any] = Body(None),
    current_user: dict = Depends(get_current_user),
    video_url: str = None,
    message: str = None,
    analysis_modes: str = None,
    brand_name: str = None,
):
    """
    Check a video for brand compliance using its URL.

    This endpoint:
    1. Accepts a video URL and optional message
    2. Processes the video using the video compliance agent
    3. Streams the results back to the client
    """
    # Handle both GET and POST methods
    if request.method == "GET":
        if not video_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Video URL is required for GET request",
            )
        # Set defaults for GET request
        message = message or "Analyze this video for brand compliance."
        analysis_modes = (
            analysis_modes.split(",")
            if analysis_modes
            else ["visual", "brand_voice", "tone"]
        )
        # Keep brand_name as is from query parameters
    else:
        # POST method - extract from body
        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request body is required for POST request",
            )
        video_url = data.get("video_url")
        message = data.get("message", "Analyze this video for brand compliance.")
        analysis_modes = data.get("analysis_modes", ["visual", "brand_voice", "tone"])
        brand_name = data.get("brand_name", brand_name)  # Extract brand_name from request body

    # Validate input
    if not video_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video URL is required",
        )

    # Validate video URL format
    if not (video_url.startswith("http://") or video_url.startswith("https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid video URL format. URL must start with http:// or https://",
        )

    # Validate analysis modes
    valid_modes = ["visual", "brand_voice", "tone"]
    invalid_modes = [mode for mode in analysis_modes if mode not in valid_modes]
    if invalid_modes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid analysis modes: {', '.join(invalid_modes)}. Valid modes are: {', '.join(valid_modes)}",
        )

    try:
        # Create a streaming response
        return StreamingResponse(
            process_video_frames_and_stream(
                video_url=video_url,
                message=message,
                analysis_modes=analysis_modes,
                user_id=current_user["id"],
                brand_name=brand_name,
            ),
            media_type="text/event-stream",
        )
    except Exception as e:
        # Log the error for debugging
        print(f"Error in check_video_compliance: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process video: {str(e)}",
        )


async def process_video_frames_and_stream(
    video_url: str, message: str, analysis_modes: List[str], user_id: str, brand_name: str = None
):
    """
    Process a video using the native agent implementation with frames extraction.
    This function is similar to process_image_and_stream but handles video frames.

    Args:
        video_url: URL of the video to analyze
        message: Text prompt to send with the video
        analysis_modes: List of analysis modes to run (currently only used in prompt)
        user_id: ID of the current user
        brand_name: Optional name of the brand being analyzed

    Yields:
        Server-sent events with the streaming results
    """
    import inspect
    import json
    import time
    
    print(f"[LOG] process_video_frames_and_stream: Start (line {inspect.currentframe().f_lineno})")
    print(f"[LOG] process_video_frames_and_stream: Using model: anthropic/claude-3-7-sonnet (line {inspect.currentframe().f_lineno})")
    print(f"[LOG] process_video_frames_and_stream: user_id: {user_id} (line {inspect.currentframe().f_lineno})")
    print(f"[LOG] process_video_frames_and_stream: video_url: {video_url} (line {inspect.currentframe().f_lineno})")
    print(f"[LOG] process_video_frames_and_stream: message: {message} (line {inspect.currentframe().f_lineno})")

    # Create a message ID for this request
    message_id = str(uuid4())

    # Create a queue for the streaming data
    queue = asyncio.Queue()

    # Define the streaming callback
    async def on_stream(data: Dict[str, Any]):
        # in color
        print(f"\033[92m[LOG] process_video_and_stream: Received streaming data: {data}\033[0m (line {inspect.currentframe().f_lineno})")
        await queue.put(data)

    # Get user feedback to include in the system prompt
    user_feedback_list = get_user_feedback(user_id)

    # Prepare custom system prompt with user feedback if available
    custom_system_prompt = gemini_system_prompt
    
    # Add brand name information to system prompt if provided
    if brand_name:
        print(f"\n🏷️ [BRAND INFO] Analyzing compliance for brand: {brand_name}")
        brand_section = f"\n\n<Brand Information> !IMPORTANT!\nYou are analyzing content for the {brand_name} brand. Focus your analysis specifically on {brand_name}'s brand guidelines, visual identity, verbal identity, and overall compliance standards. When checking logos, colors, typography, and messaging, pay special attention to {brand_name}'s specific requirements and standards.\n"
        custom_system_prompt += brand_section
    
    if user_feedback_list and len(user_feedback_list) > 0:
        print(
            f"\n🧠 [USER MEMORIES] Found {len(user_feedback_list)} feedback items for user {user_id}"
        )

        feedback_section = "\n\n<User Memories and Feedback> !IMPORTANT! \n This is feedback given by the user in previous compliance checks. You need to make sure to acknowledge your knowledge of these feedback in your initial detailed plan and say that you will follow them \n"
        for i, feedback in enumerate(user_feedback_list):
            feedback_content = feedback["content"]
            feedback_date = feedback["created_at"]
            feedback_section += (
                f"- Memory {i+1} ({feedback_date}): {feedback_content}\n"
            )
            print(f"🧠 [MEMORY {i+1}] {feedback_content}")

        # Add feedback section to system prompt
        custom_system_prompt = gemini_system_prompt + feedback_section
        print(f"🧠 [SYSTEM PROMPT] Added user memories to system prompt")
    else:
        print(f"🧠 [USER MEMORIES] No feedback found for user {user_id}")

    # Download video and extract frames
    print(f"[LOG] process_video_frames_and_stream: Downloading video from {video_url} (line {inspect.currentframe().f_lineno})")
    
    # Import video processing functions
    from app.core.video_agent.gemini_llm import extract_frames
    from app.core.video_agent.video_agent_class import download_video
    
    # Download the video
    try:
        # First yield a status event to inform the client that download is in progress
        yield "data: status:Downloading video file...\n\n"
        
        # Download the video to a temporary file
        video_path_tuple = await download_video(video_url)
        video_path = video_path_tuple[0]  # Get the path to the downloaded video
        
        # Yield status update
        yield "data: status:Extracting video frames for analysis...\n\n"
        
        # Extract frames from the video (with a reasonable interval to avoid too many frames)
        frames = await extract_frames(video_path, initial_interval=1.0)  # Extract a frame every 3 seconds
        
        print(f"[LOG] process_video_frames_and_stream: Extracted {len(frames)} frames from video (line {inspect.currentframe().f_lineno})")
        
        # Convert frames to base64 format for the OpenRouterNativeAgent
        frame_base64_list = []
        for frame in frames:
            if 'base64' in frame:  # Fix: use 'base64' key which is what extract_frames produces
                # The image data is already in base64 format from the extract_frames function
                frame_base64_list.append(frame['base64'])
                
        print(f"[LOG] process_video_frames_and_stream: Prepared {len(frame_base64_list)} frame images for analysis (line {inspect.currentframe().f_lineno})")
        
        # Choose a reasonable subset of frames if there are too many (e.g., max 10 frames)
        max_frames = 10
        if len(frame_base64_list) > max_frames:
            # Take frames at even intervals to cover the whole video
            step = len(frame_base64_list) // max_frames
            frame_base64_list = frame_base64_list[::step][:max_frames]
            print(f"[LOG] process_video_frames_and_stream: Reduced to {len(frame_base64_list)} representative frames (line {inspect.currentframe().f_lineno})")
        
    except Exception as e:
        error_msg = f"Error downloading or processing video: {str(e)}"
        print(f"\033[91m[ERROR] {error_msg}\033[0m")
        yield f"data: error:{error_msg}\n\n"
        return
    
    # Get the OpenRouter API key from environment variables
    import os
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    if not OPENROUTER_API_KEY:
        print(f"\033[91m[ERROR] OPENROUTER_API_KEY not found in environment variables\033[0m")
        yield "data: error:OpenRouter API key not configured\n\n"
        return
    
    # Create an OpenRouterNativeAgent instance using our native implementation with Claude 3.7 Sonnet
    print(f"[LOG] process_video_frames_and_stream: Instantiating OpenRouterNativeAgent with Claude 3.7 (line {inspect.currentframe().f_lineno})")
    from app.core.openrouter_agent.native_agent import OpenRouterAgent as OpenRouterNativeAgent
    
    agent = OpenRouterNativeAgent(
        api_key=OPENROUTER_API_KEY,
        model="anthropic/claude-3-7-sonnet",  # Using Claude 3.7 Sonnet for improved compliance analysis
        on_stream=on_stream,
        system_prompt=custom_system_prompt,
        temperature=0.1  # Lower temperature for more consistent outputs
    )

    # Start the agent process in a background task with the extracted frames
    try:
        # Prepare a prompt that explains we're analyzing video frames
        enhanced_prompt = f"{message}\n\nThis is a video analysis task. I'm providing {len(frame_base64_list)} key frames extracted from the video. Please analyze these frames for brand compliance, paying attention to logo usage, colors, typography, placement, and overall visual identity compliance.".strip()
        
        # Yield status update to client
        yield "data: status:Analyzing video frames for brand compliance...\n\n"
        
        # Start the analysis with the frame images
        if frame_base64_list:
            print(f"[LOG] process_video_frames_and_stream: Starting analysis with {len(frame_base64_list)} frames (line {inspect.currentframe().f_lineno})")
            
            # We'll use the frames property of the native agent to pass multiple frames
            # Convert frames to the expected format for the agent
            formatted_frames = []
            for i, frame_base64 in enumerate(frame_base64_list):
                # Ensure image_base64 doesn't include the prefix if it's already there
                if frame_base64.startswith("data:image/"):
                    # Extract only the base64 portion if it includes the data URL prefix
                    frame_base64 = frame_base64.split(",")[1]
                
                # Debug info
                if i == 0 or i == len(frame_base64_list)-1:
                    print(f"\033[94m[DEBUG] Frame {i} base64 length: {len(frame_base64)} characters\033[0m")
                    
                formatted_frames.append({
                    "timestamp": frames[i].get('timestamp', i * 3.0),  # Use actual timestamp if available
                    "frame_number": frames[i].get('frame_number', i),  # Use actual frame number if available
                    "image_data": frame_base64  # Key must match what native_agent.py expects
                })
            
            processing_task = asyncio.create_task(
                agent.process(
                    user_prompt=enhanced_prompt,
                    frames=formatted_frames  # Pass the frames as a list to the agent
                )
            )
        else:
            # Fallback if no frames were extracted
            print(f"\033[93m[WARNING] No frames extracted from video, trying to use video_url directly\033[0m")
            processing_task = asyncio.create_task(
                agent.process(
                    user_prompt=message,
                    video_url=video_url,
                )
            )

        # Send initial status
        yield "data: status:Analyzing brand compliance across video frames...\n\n"

        # Stream the results - using same approach as image compliance API
        try:
            import time
            last_yield_time = time.time()
            while True:
                try:
                    # Get data from the queue with a timeout
                    data = await asyncio.wait_for(queue.get(), timeout=1.0)
                    print(f"[LOG] process_video_frames_and_stream: Received data from queue: {data} (line {inspect.currentframe().f_lineno})")
                    
                    event_type = data.get("type")
                    print(f"[LOG] process_video_frames_and_stream: Received event_type: {event_type} (line {inspect.currentframe().f_lineno})")
                    
                    if event_type == "complete":
                        # This is the final completion event, we need to parse it and yield a complete event
                        complete_content = data.get("content", "{}")
                        print(f"[LOG] process_video_frames_and_stream: Received complete event: {complete_content[:100]}... (line {inspect.currentframe().f_lineno})")
                        
                        # Try to extract the tool call data and send it as a tool event first
                        try:
                            complete_json = json.loads(complete_content)
                            if isinstance(complete_json, dict) and "tool_name" in complete_json:
                                # This is a tool event in the complete event
                                tool_event = {
                                    "tool_name": complete_json.get("tool_name"),
                                    "tool_input": {},
                                    "task_detail": complete_json.get("task_detail") or "Final compliance analysis",
                                    "result": complete_json.get("tool_result") or ""
                                }
                                event_data_tool = f"data: tool:{json.dumps(tool_event)}\n\n"
                                yield event_data_tool
                        except Exception as e:
                            print(f"\033[91m[ERROR] Error parsing complete event as tool: {str(e)}\033[0m")
                            # Continue with regular complete event
                        
                        try:
                            # Create a simplified response with just the recommendation
                            simplified_response = {}
                            
                            # Check for errors in the tool_result first
                            tool_result_error = False
                            tool_result = None
                            
                            if isinstance(complete_json, dict):
                                tool_result = complete_json.get("tool_result", {})
                                
                                # Check if we have an error in the tool_result
                                if isinstance(tool_result, str) and "Error" in tool_result:
                                    tool_result_error = True
                                    print(f"\033[93m[WARNING] Tool result contains error: {tool_result}\033[0m")
                                
                                # Also check for empty dict or None result
                                if not tool_result or (isinstance(tool_result, dict) and not tool_result):
                                    tool_result_error = True
                                    print(f"\033[93m[WARNING] Tool result is empty or None\033[0m")
                                    
                            # Handle normal case - extract from tool_result
                            if not tool_result_error and isinstance(tool_result, dict):
                                detailed_report = tool_result.get("detailed_report", "")
                                simplified_response["recommendation"] = detailed_report
                            # Handle error case - try to extract from tool_input
                            elif isinstance(complete_json, dict) and "tool_input" in complete_json:
                                print(f"\033[94m[INFO] Using tool_input as fallback for recommendation\033[0m")
                                tool_input = complete_json.get("tool_input", {})
                                
                                if isinstance(tool_input, dict):
                                    compliance_status = tool_input.get("compliance_status", "unknown")
                                    compliance_summary = tool_input.get("compliance_summary", "")
                                    task_detail = tool_input.get("task_detail", "Brand Compliance Analysis")
                                    
                                    # Create a formatted recommendation from the original input
                                    recommendation_template = "# {0}\n\n## Compliance Status: {1}\n\n## Summary\n{2}\n\n*Note: This report was generated from the initial analysis data.*"
                                    recommendation = recommendation_template.format(task_detail, compliance_status, compliance_summary)
                                    simplified_response["recommendation"] = recommendation
                                    print(f"\033[94m[INFO] Created recommendation of {len(recommendation)} characters from tool_input\033[0m")
                                else:
                                    simplified_response["recommendation"] = str(tool_result)
                            else:
                                simplified_response["recommendation"] = str(complete_json)
                            
                            # Replace the complete content with our simplified object
                            complete_content = json.dumps(simplified_response)
                            
                            print(f"\033[94m[INFO] Simplified complete response to just include recommendation\033[0m")
                        except Exception as e:
                            print(f"\033[91m[ERROR] Failed to simplify complete event: {str(e)}\033[0m")
                            # Create a basic response if JSON parsing fails
                            complete_content = json.dumps({"recommendation": "Error processing compliance report"})
                            
                        event_data = f"data: complete:{complete_content}\n\n"
                        yield event_data
                        queue.task_done()
                        break
                    elif event_type == "text":
                        # Just pass through text events
                        event_data = f"data: text:{data.get('content', '')}\n\n"
                        yield event_data
                    elif event_type == "tool":
                        # This is a regular tool event
                        event_data = f"data: tool:{data.get('content', '')}\n\n"
                        yield event_data
                    elif event_type == "error":
                        # An error occurred in the agent
                        error_content = data.get("content", "Unknown error")
                        print(f"\033[91m[ERROR] Error in agent: {error_content}\033[0m")
                        event_data = f"data: error:{error_content}\n\n"
                        yield event_data
                    else:
                        # Unknown event type, just pass it through
                        event_data = f"data: {event_type}:{data.get('content', '')}\n\n"
                        yield event_data
                        
                    # Each iteration of the loop must call task_done() once
                    queue.task_done()
                except asyncio.TimeoutError:
                    # If more than 5 seconds have passed since last yield, send a user-friendly keep-alive tool event
                    if time.time() - last_yield_time > 15:
                        keep_alive_event = {
                            "tool_name": "keep_alive",
                            "tool_input": {},
                            "task_detail": "Still working on your video compliance analysis. This may take a few moments..."
                        }
                        event_data = f"data: tool:{json.dumps(keep_alive_event)}\n\n"
                        yield event_data
                        last_yield_time = time.time()
                    # Check if the processing task is done
                    if processing_task.done():
                        break

        except asyncio.CancelledError:
            # Handle client disconnection
            yield "data: status:Processing cancelled by client\n\n"
            if not processing_task.done():
                processing_task.cancel()
            raise

        except Exception as e:
            # Handle any other streaming errors
            error_response = json.dumps(
                {
                    "status": "error",
                    "error": str(e),
                    "detail": "Error during video processing stream",
                }
            )
            yield f"data: error:{error_response}\n\n"

    except Exception as e:
        # Handle any errors in task creation or initial setup
        error_response = json.dumps(
            {
                "status": "error",
                "error": str(e),
                "detail": "Failed to initialize video processing",
            }
        )
        yield f"data: error:{error_response}\n\n"

    finally:
        # Ensure the processing task is cancelled if not done
        if "processing_task" in locals() and not processing_task.done():
            processing_task.cancel()
            yield "data: status:Cleanup completed\n\n"


class FeedbackRequest(BaseModel):
    content: str


@router.post("/compliance/feedback")
async def submit_feedback(
    feedback: FeedbackRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Submit user feedback for the compliance system.

    This feedback will be stored in the database and used to improve the system.
    It will be included in the system prompt for future compliance checks.

    Args:
        feedback: The feedback content
        current_user: The authenticated user

    Returns:
        The ID of the created feedback record
    """
    try:
        # Create feedback data
        feedback_data = {
            "user_id": current_user["id"],
            "content": feedback.content,
        }

        # Store feedback in database
        feedback_id = create_feedback(feedback_data)

        return {"id": feedback_id, "status": "success"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store feedback: {str(e)}",
        )


@router.get("/compliance/feedback")
async def get_feedback(
    current_user: dict = Depends(get_current_user),
):
    """
    Get all feedback submitted by the current user.

    Args:
        current_user: The authenticated user

    Returns:
        List of feedback records
    """
    try:
        # Get feedback from database
        feedback_list = get_user_feedback(current_user["id"])

        return {"feedback": feedback_list, "status": "success"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve feedback: {str(e)}",
        )
