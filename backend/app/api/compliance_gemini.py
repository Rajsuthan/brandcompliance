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
from app.core.agent.gemini_agent import GeminiAgent, encode_image_to_base64
from app.core.agent.prompt import gemini_system_prompt
from app.core.video_agent.video_agent_class import VideoAgent
# Import both MongoDB and Firestore functions for backward compatibility
from app.db.database import create_feedback as create_feedback_mongo, get_user_feedback as get_user_feedback_mongo
from app.db.firestore import create_feedback, get_user_feedback

router = APIRouter()

@router.post("/compliance/check-image")
async def check_image_compliance(
    file: UploadFile = File(...),
    text: Optional[str] = Form("Analyze this image for brand compliance."),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload an image and check it for brand compliance using Gemini.
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
    Process an image using the Gemini agent and stream the results.
    """
    message_id = str(uuid4())
    queue = asyncio.Queue()

    async def on_stream(data: Dict[str, Any]):
        await queue.put(data)

    # Get user feedback to include in the system prompt
    try:
        # Try to get feedback from Firestore
        user_feedback_list = get_user_feedback(user_id)
        print(f"[INFO] Retrieved {len(user_feedback_list)} user feedback items from Firestore")
    except Exception as e:
        print(f"[WARNING] Failed to get user feedback from Firestore: {str(e)}")
        # Fallback to MongoDB
        try:
            user_feedback_list = get_user_feedback_mongo(user_id)
            print(f"[INFO] Retrieved {len(user_feedback_list)} user feedback items from MongoDB")
        except Exception as e2:
            print(f"[ERROR] Failed to get user feedback from MongoDB: {str(e2)}")
            user_feedback_list = []

    # Prepare custom system prompt with user feedback if available
    custom_system_prompt = gemini_system_prompt
    if user_feedback_list and len(user_feedback_list) > 0:
        print(f"\n🧠 [USER MEMORIES] Found {len(user_feedback_list)} feedback items for user {user_id}")

        feedback_section = "\n\n<User Memories and Feedback> !IMPORTANT! \nThis is feedback given by the user in previous compliance checks. You need to make sure to acknowledge your knowledge of these feedback in your initial detailed plan and say that you will follow them \n"
        for i, feedback in enumerate(user_feedback_list):
            feedback_content = feedback["content"]
            feedback_date = feedback["created_at"]
            feedback_section += f"- Memory {i+1} ({feedback_date}): {feedback_content}\n"
            print(f"🧠 [MEMORY {i+1}] {feedback_content}")

        custom_system_prompt = gemini_system_prompt + feedback_section
        print(f"🧠 [SYSTEM PROMPT] Added user memories to system prompt")
    else:
        print(f"🧠 [USER MEMORIES] No feedback found for user {user_id}")

    # Create a Gemini agent instance
    agent = GeminiAgent(
        model="gemini-2.0-flash",
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
    video_url: Optional[str] = None,
    message: Optional[str] = Form(None),
    analysis_modes: Optional[List[str]] = Form(["visual", "brand_voice", "tone"]),
    brand_name: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    """
    Check video compliance using the video agent.
    """
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
            brand_name=brand_name,
        ),
        media_type="text/event-stream",
    )

async def process_video_and_stream(
    video_url: str,
    message: str,
    analysis_modes: List[str],
    user_id: str,
    brand_name: str = None,
):
    """
    Process a video using the video compliance agent and stream the results.
    """
    queue = asyncio.Queue()

    async def on_stream(data: Dict[str, Any]):
        await queue.put(data)

    # Create a video agent instance
    agent = VideoAgent(
        model="gemini-2.0-flash-lite",
        on_stream=on_stream,
        user_id=user_id,
    )

    # Process the video in a separate task
    processing_task = asyncio.create_task(
        agent.generate(
            video_url=video_url,
            message=message,
            analysis_modes=analysis_modes,
        )
    )

    # Stream the results
    try:
        while True:
            try:
                # Get data from the queue with a timeout
                data = await asyncio.wait_for(queue.get(), timeout=1.0)

                # Format as a server-sent event
                event_data = f"data: {data['type']}:{data['content']}\n\n"
                yield event_data

                # Mark the item as processed
                queue.task_done()
            except asyncio.TimeoutError:
                # Check if the processing task is done
                if processing_task.done():
                    # Get the final result
                    result = processing_task.result()

                    # Send a completion event with the final result
                    yield f"data: complete:{json.dumps(result)}\n\n"
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

class FeedbackRequest(BaseModel):
    content: str

@router.post("/compliance/feedback")
async def submit_feedback(
    feedback: FeedbackRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Submit user feedback for the compliance system.
    """
    try:
        # Create feedback in Firestore
        feedback_data = {
            "user_id": current_user["id"],
            "content": feedback.content,
        }
        feedback_id = create_feedback(feedback_data)
        print(f"[INFO] Created feedback in Firestore with ID: {feedback_id}")

        # Also store in MongoDB for backward compatibility
        try:
            mongo_feedback_id = create_feedback_mongo(
                user_id=current_user["id"],
                content=feedback.content,
            )
            print(f"[INFO] Created feedback in MongoDB with ID: {mongo_feedback_id}")
        except Exception as mongo_error:
            print(f"[WARNING] Failed to create feedback in MongoDB: {str(mongo_error)}")

        return {"id": feedback_id, "status": "success"}
    except Exception as e:
        print(f"[ERROR] Failed to create feedback in Firestore: {str(e)}")

        # Fallback to MongoDB
        try:
            mongo_feedback_id = create_feedback_mongo(
                user_id=current_user["id"],
                content=feedback.content,
            )
            print(f"[INFO] Created feedback in MongoDB with ID: {mongo_feedback_id}")
            return {"id": str(mongo_feedback_id), "status": "success"}
        except Exception as mongo_error:
            print(f"[ERROR] Failed to create feedback in MongoDB: {str(mongo_error)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error submitting feedback: {str(e)}",
            )

@router.get("/compliance/feedback")
async def get_feedback(
    current_user: dict = Depends(get_current_user),
):
    """
    Get all feedback submitted by the current user.
    """
    try:
        # Get feedback from Firestore
        feedback_list = get_user_feedback(current_user["id"])
        print(f"[INFO] Retrieved {len(feedback_list)} feedback items from Firestore")
        return {"feedback": feedback_list, "status": "success"}
    except Exception as e:
        print(f"[WARNING] Failed to get feedback from Firestore: {str(e)}")

        # Fallback to MongoDB
        try:
            feedback_list = get_user_feedback_mongo(current_user["id"])
            print(f"[INFO] Retrieved {len(feedback_list)} feedback items from MongoDB")
            return {"feedback": feedback_list, "status": "success"}
        except Exception as mongo_error:
            print(f"[ERROR] Failed to get feedback from MongoDB: {str(mongo_error)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting feedback: {str(e)}",
            )
