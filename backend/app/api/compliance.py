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
    status,
)
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any, List
from uuid import uuid4
import asyncio

from app.core.auth import get_current_user
from app.core.agent.index import Agent, encode_image_to_base64
from app.core.agent.prompt import system_prompt, gemini_system_prompt
from app.core.video_agent.video_agent_class import VideoAgent

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

    # Create an agent instance
    agent = Agent(
        model="claude-3-7-sonnet-20250219",
        on_stream=on_stream,
        user_id=user_id,
        message_id=message_id,
        system_prompt=system_prompt,
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
async def check_video_compliance(
    data: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Check a video for brand compliance using its URL.

    This endpoint:
    1. Accepts a video URL and optional message
    2. Processes the video using the video compliance agent
    3. Streams the results back to the client
    """
    # Extract data from request
    video_url = data.get("video_url")
    message = data.get("message", "Analyze this video for brand compliance.")
    analysis_modes = data.get("analysis_modes", ["visual", "brand_voice", "tone"])

    if not video_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video URL is required",
        )

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

    # Create a video agent instance
    agent = VideoAgent(
        model="gemini-2.0-flash",
        on_stream=on_stream,
        user_id=user_id,
        message_id=message_id,
    )

    # Process the video in a separate task
    processing_task = asyncio.create_task(
        agent.generate(video_url, message, analysis_modes)
    )

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
                    results = processing_task.result()

                    # Format the results as JSON
                    final_response = json.dumps(
                        {"results": results["results"], "filepath": results["filepath"]}
                    )

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
