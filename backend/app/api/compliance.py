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

router = APIRouter()


@router.post("/compliance/check-image")
async def check_image_compliance(
    file: UploadFile = File(...),
    text: Optional[str] = Form("Analyze this image for brand compliance."),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload an image and check it for brand compliance.

    This endpoint:
    1. Accepts an image file upload
    2. Processes the image using the compliance agent
    3. Streams the results back to the client
    """
    # Validate file type
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files are allowed",
        )

    # Create a temporary file to store the uploaded image
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=f".{content_type.split('/')[-1]}"
    ) as temp_file:
        # Write the uploaded file content to the temporary file
        shutil.copyfileobj(file.file, temp_file)
        temp_file_path = temp_file.name

    try:
        # Get the base64 encoding of the image
        image_base64, media_type = encode_image_to_base64(temp_file_path)

        # Create a streaming response
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
        # Handle any errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing image: {str(e)}",
        )
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


async def process_image_and_stream(
    image_base64: str, media_type: str, text: str, user_id: str
):
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

    # Prepare custom system prompt with user feedback if available
    custom_system_prompt = system_prompt
    if user_feedback_list and len(user_feedback_list) > 0:
        print(
            f"\n🧠 [USER MEMORIES] Found {len(user_feedback_list)} feedback items for user {user_id}"
        )

        feedback_section = "\n\n<User Memories and Feedback> !IMPORTANT! \n This is feedback given by the user in previous compliance checks. You need to make sure to acknolwedge your knowledge of these feedback in your initial detailed plan and say that you will follow them \n"
        for i, feedback in enumerate(user_feedback_list):
            feedback_content = feedback["content"]
            feedback_date = feedback["created_at"]
            feedback_section += (
                f"- Memory {i+1} ({feedback_date}): {feedback_content}\n"
            )
            print(f"🧠 [MEMORY {i+1}] {feedback_content}")

        # Add feedback section to system prompt
        custom_system_prompt = system_prompt + feedback_section
        print(f"🧠 [SYSTEM PROMPT] Added user memories to system prompt")
    else:
        print(f"🧠 [USER MEMORIES] No feedback found for user {user_id}")

    # Create an agent instance
    agent = Agent(
        model="claude-3-7-sonnet-20250219",
        on_stream=on_stream,
        user_id=user_id,
        message_id=message_id,
        system_prompt=custom_system_prompt,
    )

    # Create a dictionary with image data and text
    image_message = {
        "image_base64": image_base64,
        "media_type": media_type,
        "text": text,
    }

    # Process the message with image in a separate task
    processing_task = asyncio.create_task(agent.process_message(image_message))

    # Stream the results
    try:
        while True:
            try:
                # Get data from the queue with a timeout
                data = await asyncio.wait_for(queue.get(), timeout=1.0)

                # Filter out XML content from the data
                if data["type"] == "text":
                    # Check if the content contains XML tags
                    content = data["content"]
                    if not (content.strip().startswith("<") and ">" in content):
                        # Format as a server-sent event
                        event_data = f"data: {data['type']}:{content}\n\n"
                        yield event_data
                else:
                    # Format as a server-sent event
                    event_data = f"data: {data['type']}:{data['content']}\n\n"
                    yield event_data

                # Mark the item as processed
                queue.task_done()
            except asyncio.TimeoutError:
                # Check if the processing task is done
                if processing_task.done():
                    # Get the final result
                    final_response, messages = processing_task.result()

                    # Send a completion event
                    yield f"data: complete:{final_response}\n\n"
                    break
    except asyncio.CancelledError:
        # Handle client disconnection
        if not processing_task.done():
            processing_task.cancel()
        raise
    finally:
        # Ensure the processing task is cancelled if not done
        if not processing_task.done():
            processing_task.cancel()


@router.post("/compliance/check-video")
@router.get("/compliance/check-video")
async def check_video_compliance(
    request: Request,
    data: Dict[str, Any] = Body(None),
    current_user: dict = Depends(get_current_user),
    video_url: str = None,
    message: str = None,
    analysis_modes: str = None,
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
    video_url: str, message: str, analysis_modes: List[str], user_id: str
):
    """
    Process a video using the video compliance agent and stream the results.

    Args:
        video_url: URL of the video to analyze
        message: Text prompt to send with the video
        analysis_modes: List of analysis modes to run
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

    # Prepare custom system prompt with user feedback if available
    custom_system_prompt = gemini_system_prompt
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

    # Create a video agent instance
    agent = VideoAgent(
        model="gemini-2.0-flash",
        on_stream=on_stream,
        user_id=user_id,
        message_id=message_id,
        system_prompt=custom_system_prompt,
    )

    # Process the video in a separate task
    try:
        processing_task = asyncio.create_task(
            agent.generate(video_url, message, analysis_modes)
        )

        # Send initial status
        yield "data: status:Starting video download and processing...\n\n"

        # Stream the results
        try:
            while True:
                try:
                    # Get data from the queue with a timeout
                    data = await asyncio.wait_for(queue.get(), timeout=1.0)

                    # Filter out XML content from the data
                    if data["type"] == "text":
                        # Check if the content contains XML tags
                        content = data["content"]
                        if not (content.strip().startswith("<") and ">" in content):
                            # Format as a server-sent event
                            event_data = f"data: {data['type']}:{content}\n\n"
                            yield event_data
                    else:
                        # Format as a server-sent event
                        event_data = f"data: {data['type']}:{data['content']}\n\n"
                        yield event_data

                    # Mark the item as processed
                    queue.task_done()
                except asyncio.TimeoutError:
                    # Check if the processing task is done
                    if processing_task.done():
                        try:
                            # Get the final result
                            results = processing_task.result()

                            # Format the results as JSON
                            final_response = json.dumps(
                                {
                                    "results": results["results"],
                                    "filepath": results["filepath"],
                                    "status": "success",
                                }
                            )

                            # Send a completion event
                            yield f"data: complete:{final_response}\n\n"
                            break
                        except Exception as e:
                            # Handle any errors in processing task
                            error_response = json.dumps(
                                {
                                    "status": "error",
                                    "error": str(e),
                                    "detail": "Failed to process video results",
                                }
                            )
                            yield f"data: error:{error_response}\n\n"
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
