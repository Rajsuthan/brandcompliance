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
    print(f"[LOG] check_image_compliance: Start (line {inspect.currentframe().f_lineno})")
    print(f"[LOG] check_image_compliance: Received file: {file.filename}, content_type: {file.content_type} (line {inspect.currentframe().f_lineno})")
    print(f"[LOG] check_image_compliance: User: {current_user.get('username', 'unknown')} (line {inspect.currentframe().f_lineno})")
    """
    Upload an image and check it for brand compliance.

    This endpoint:
    1. Accepts an image file upload
    2. Processes the image using the compliance agent
    3. Streams the results back to the client
    """
    # Validate file type
    import inspect
    content_type = file.content_type or ""
    print(f"[LOG] check_image_compliance: Validating file type: {content_type} (line {inspect.currentframe().f_lineno})")
    if not content_type.startswith("image/"):
        print(f"[LOG] check_image_compliance: Invalid file type (line {inspect.currentframe().f_lineno})")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files are allowed",
        )

    # Create a temporary file to store the uploaded image
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=f".{content_type.split('/')[-1]}"
    ) as temp_file:
        print(f"[LOG] check_image_compliance: Creating temp file at {temp_file.name} (line {inspect.currentframe().f_lineno})")
        # Write the uploaded file content to the temporary file
        shutil.copyfileobj(file.file, temp_file)
        temp_file_path = temp_file.name

    try:
        print(f"[LOG] check_image_compliance: Encoding image to base64 (line {inspect.currentframe().f_lineno})")
        # Get the base64 encoding of the image
        image_base64, media_type = encode_image_to_base64(temp_file_path)
        print(f"[LOG] check_image_compliance: Encoded image, media_type: {media_type} (line {inspect.currentframe().f_lineno})")

        # Create a streaming response
        print(f"[LOG] check_image_compliance: Creating StreamingResponse (line {inspect.currentframe().f_lineno})")
        return StreamingResponse(
            process_image_and_stream(
                image_base64=image_base64,
                media_type=media_type,
                text=text,
                user_id=current_user["id"],
            ),
            media_type="text/event-stream",
        )
    except Exception as e:
        print(f"[LOG] check_image_compliance: Exception occurred: {e} (line {inspect.currentframe().f_lineno})")
        # Handle any errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing image: {str(e)}",
        )
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            print(f"[LOG] check_image_compliance: Deleting temp file {temp_file_path} (line {inspect.currentframe().f_lineno})")
            os.unlink(temp_file_path)


import inspect
async def process_image_and_stream(
    image_base64: str, media_type: str, text: str, user_id: str
):
    print(f"[LOG] process_image_and_stream: Start (line {inspect.currentframe().f_lineno})")
    print(f"[LOG] process_image_and_stream: Using model: claude-3-5-sonnet-20241022 (line {inspect.currentframe().f_lineno})")
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

    # Create an OpenRouterAgent instance
    print(f"[LOG] process_image_and_stream: Instantiating OpenRouterAgent (line {inspect.currentframe().f_lineno})")
    from app.core.openrouter_agent.agent import OpenRouterAgent

    agent = OpenRouterAgent(
        model="google/gemini-2.5-pro-preview-03-25",
        on_stream=on_stream,
        system_prompt=custom_system_prompt,
    )

    # Start the agent process in a background task
    print(f"[LOG] process_image_and_stream: Creating processing_task for OpenRouterAgent (line {inspect.currentframe().f_lineno})")
    try:
        processing_task = asyncio.create_task(
            agent.process(
                user_prompt=text,
                image_base64=image_base64,
                media_type=media_type,
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

                event_type = data.get("type")
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
                    if not (content.strip().startswith("<") and ">" in content):
                        # Final check for any attempt_completion XML in the text before yielding
                        ac_match_final = re.search(r"<attempt_completion>(.*?)</attempt_completion>", content, re.DOTALL)
                        if ac_match_final:
                            xml_block = "<attempt_completion>" + ac_match_final.group(1) + "</attempt_completion>"
                            try:
                                xml_dict = xmltodict.parse(xml_block)
                                ac = xml_dict.get("attempt_completion", {})
                                tool_event = {
                                    "tool_name": "attempt_completion",
                                    "tool_input": {},
                                    "task_detail": ac.get("task_detail") or "Final compliance result",
                                    "result": ac.get("result") or ""
                                }
                                event_data = f"data: tool:{json.dumps(tool_event)}\n\n"
                                yield event_data
                                event_data_complete = f"data: complete:{json.dumps(tool_event)}\n\n"
                                yield event_data_complete
                                break
                            except Exception:
                                event_data = f"data: text:{content}\n\n"
                                print(f"[LOG] process_image_and_stream: Yielding event_data: {event_data.strip()} (line {inspect.currentframe().f_lineno})")
                                yield event_data
                                last_yield_time = time.time()
                        else:
                            event_data = f"data: text:{content}\n\n"
                            print(f"[LOG] process_image_and_stream: Yielding event_data: {event_data.strip()} (line {inspect.currentframe().f_lineno})")
                            yield event_data
                            last_yield_time = time.time()
                elif event_type == "tool":
                    # If the content is already valid JSON, yield immediately
                    try:
                        json.loads(data["content"])
                        event_data = f"data: tool:{data['content']}\n\n"
                        print(f"[LOG] process_image_and_stream: Yielding tool event_data: {event_data.strip()} (line {inspect.currentframe().f_lineno})")
                        yield event_data
                        last_yield_time = time.time()
                    except Exception:
                        # If not valid JSON, buffer as before (for XML or partial)
                        tool_buffer += data["content"]
                        tool_buffering = True
                        print(f"[LOG] process_image_and_stream: Buffering tool content: {tool_buffer} (line {inspect.currentframe().f_lineno})")
                    # Do not try to parse or yield yet; wait for next non-tool event
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

                    # Only yield the final answer as the complete event, then break
                    final_answer = data.get("content", "")
                    event_data = f"data: complete:{final_answer}\n\n"
                    print(f"[LOG] process_image_and_stream: Yielding complete event_data: {event_data.strip()} (line {inspect.currentframe().f_lineno})")
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
            process_video_and_stream(
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


async def process_video_and_stream(
    video_url: str, message: str, analysis_modes: List[str], user_id: str, brand_name: str = None
):
    """
    Process a video using the video compliance agent and stream the results.

    Args:
        video_url: URL of the video to analyze
        message: Text prompt to send with the video
        analysis_modes: List of analysis modes to run
        user_id: ID of the current user
        brand_name: Optional name of the brand being analyzed

    Yields:
        Server-sent events with the streaming results
    """
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

    # Create an OpenRouterAgent instance for video compliance
    from app.core.openrouter_agent.agent import OpenRouterAgent

    agent = OpenRouterAgent(
        model="google/gemini-2.5-pro-preview-03-25",
        on_stream=on_stream,
        system_prompt=custom_system_prompt,
    )

    # Start the agent process in a background task
    try:
        processing_task = asyncio.create_task(
            agent.process(
                user_prompt=message,
                video_url=video_url,
                media_type="video/mp4",  # or infer from URL if needed
            )
        )

        # Send initial status
        yield "data: status:Starting video download and processing...\n\n"

        # Stream the results
        try:
            import time
            last_yield_time = time.time()
            while True:
                try:
                    # Get data from the queue with a timeout
                    data = await asyncio.wait_for(queue.get(), timeout=1.0)

                    event_type = data.get("type")
                    if event_type == "text":
                        content = data["content"]
                        import re
                        import xmltodict
                        ac_match = re.search(r"<attempt_completion>(.*?)</attempt_completion>", content, re.DOTALL)
                        if ac_match:
                            xml_block = "<attempt_completion>" + ac_match.group(1) + "</attempt_completion>"
                            try:
                                xml_dict = xmltodict.parse(xml_block)
                                ac = xml_dict.get("attempt_completion", {})
                                tool_event = {
                                    "tool_name": "attempt_completion",
                                    "tool_input": {},
                                    "task_detail": ac.get("task_detail") or "Final compliance result",
                                    "result": ac.get("result") or ""
                                }
                                event_data = f"data: tool:{json.dumps(tool_event)}\n\n"
                                yield event_data
                                event_data_complete = f"data: complete:{json.dumps(tool_event)}\n\n"
                                yield event_data_complete
                                queue.task_done()
                                break
                            except Exception:
                                event_data = f"data: text:{content}\n\n"
                                yield event_data
                                last_yield_time = time.time()
                        elif not (content.strip().startswith("<") and ">" in content):
                            # Final check for any attempt_completion XML in the text before yielding
                            ac_match_final = re.search(r"<attempt_completion>(.*?)</attempt_completion>", content, re.DOTALL)
                            if ac_match_final:
                                xml_block = "<attempt_completion>" + ac_match_final.group(1) + "</attempt_completion>"
                                try:
                                    xml_dict = xmltodict.parse(xml_block)
                                    ac = xml_dict.get("attempt_completion", {})
                                    tool_event = {
                                        "tool_name": "attempt_completion",
                                        "tool_input": {},
                                        "task_detail": ac.get("task_detail") or "Final compliance result",
                                        "result": ac.get("result") or ""
                                    }
                                    event_data = f"data: tool:{json.dumps(tool_event)}\n\n"
                                    yield event_data
                                    event_data_complete = f"data: complete:{json.dumps(tool_event)}\n\n"
                                    yield event_data_complete
                                    queue.task_done()
                                    break
                                except Exception:
                                    event_data = f"data: {event_type}:{content}\n\n"
                                    yield event_data
                                    last_yield_time = time.time()
                            else:
                                event_data = f"data: {event_type}:{content}\n\n"
                                yield event_data
                                last_yield_time = time.time()
                    elif event_type == "complete":
                        complete_content = data.get('content', '')
                        import re
                        import xmltodict
                        ac_match = re.search(r"<attempt_completion>(.*?)</attempt_completion>", complete_content, re.DOTALL)
                        if ac_match:
                            xml_block = "<attempt_completion>" + ac_match.group(1) + "</attempt_completion>"
                            try:
                                xml_dict = xmltodict.parse(xml_block)
                                ac = xml_dict.get("attempt_completion", {})
                                tool_event = {
                                    "tool_name": "attempt_completion",
                                    "tool_input": {},
                                    "task_detail": ac.get("task_detail") or "Final compliance result",
                                    "result": ac.get("result") or ""
                                }
                                event_data_tool = f"data: tool:{json.dumps(tool_event)}\n\n"
                                yield event_data_tool
                            except Exception:
                                pass
                        event_data = f"data: complete:{complete_content}\n\n"
                        yield event_data
                        queue.task_done()
                        break
                    else:
                        event_data = f"data: {event_type}:{data.get('content', '')}\n\n"
                        yield event_data
                        last_yield_time = time.time()

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
