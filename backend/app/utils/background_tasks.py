"""
Background Tasks Module

This module provides functionality for running tasks in the background.
"""

import asyncio
import logging
import traceback
from typing import Dict, Any, List, Callable, Coroutine
import time
import random
from datetime import datetime
from app.core.agent.llm import llm

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store for background tasks
# task_id -> {"status": str, "result": Any, "created_at": datetime, "completed_at": datetime}
tasks_store = {}


async def process_guideline_page(page_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single brand guideline page.
    This is a placeholder function that simulates processing a page.

    Args:
        page_data: Dictionary containing page data

    Returns:
        Dictionary with processing results
    """
    try:
        # Extract page information
        page_id = page_data.get("id")
        guideline_id = page_data.get("guideline_id")
        page_number = page_data.get("page_number")

        async def on_stream(data):
            print(
                "streaming ->",
            )

        async def on_stop(data):
            print("stopping -> ")

        response, reason = await llm(
            model="gemini-2.0-flash-lite",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "here is the image:"},
                        {
                            "type": "image_url",
                            "image_url": {"url": page_data["base64"]},
                        },
                    ],
                }
            ],
            on_stream=on_stream,
            on_stop=on_stop,
            available_tools=None,
            system_prompt="""
You will receive an image of a page from a brand guideline PDF. Provide a brief, keyword-optimized summary (1-2 lines max or comma-separated) that clearly states:

– What the page is about (e.g., design principle, color usage, typography)
– What brand element it refers to (e.g., logo, color, font)
– What must be followed or applied (e.g., use trademark red, consistent typography)
– Include any visual context shown (e.g., product images, examples)

The output should be dense and clear for search/embeddings—no extra explanation or filler.

Example Based on Your Image:
Color usage principle, emphasizes trademark red, shows product cans in various colors (cherry, vanilla, lemon, lime, orange), rule: use red as dominant color to differentiate products and maintain brand consistency
            """,
        )

        # Create final result
        final_result = {
            "page_id": page_id,
            "guideline_id": guideline_id,
            "page_number": page_number,
            "result": response,
        }

        return final_result

    except Exception as e:
        import json
        import os
        from datetime import datetime

        error_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "page_id": page_data.get("id"),
            "guideline_id": page_data.get("guideline_id"),
            "error": str(e),
            "traceback": traceback.format_exc(),
        }

        # Ensure errors directory exists
        os.makedirs("errors", exist_ok=True)

        # Write error to JSON file
        error_filename = f"errors/page_processing_error_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(error_filename, "w") as f:
            json.dump(error_data, f, indent=2)

        logger.error(f"Error processing page {page_data.get('id')}: {str(e)}")
        logger.error(f"Error details saved to {error_filename}")

        return {
            "page_id": page_data.get("id"),
            "guideline_id": page_data.get("guideline_id"),
            "page_number": page_data.get("page_number"),
            "result": f"Error processing page: {str(e)}",
            "error": True,
            "error_file": error_filename,
        }


async def run_background_task(task_id: str, func: Callable, *args, **kwargs) -> None:
    """
    Run a function as a background task and store its result.
    Also updates the page in the database with the processing results.

    Args:
        task_id: Unique identifier for the task
        func: Function to run
        *args, **kwargs: Arguments to pass to the function
    """
    try:
        # Initialize task in store
        tasks_store[task_id] = {
            "status": "running",
            "result": None,
            "created_at": datetime.utcnow(),
            "completed_at": None,
        }

        # Run the function
        result = await func(*args, **kwargs)

        # Update task store with result
        tasks_store[task_id] = {
            "status": "completed",
            "result": result,
            "created_at": tasks_store[task_id]["created_at"],
            "completed_at": datetime.utcnow(),
        }

        # Update the page in the database with the processing results
        if isinstance(result, dict) and "page_id" in result:
            from app.db.database import update_guideline_page_with_results

            page_id = result["page_id"]
            updated_page = update_guideline_page_with_results(page_id, result)
            logger.info(f"Updated page {page_id} with processing results")

        logger.info(f"Task {task_id} completed successfully")

    except Exception as e:
        # Update task store with error
        tasks_store[task_id] = {
            "status": "failed",
            "result": str(e),
            "created_at": tasks_store[task_id]["created_at"],
            "completed_at": datetime.utcnow(),
        }

        logger.error(f"Task {task_id} failed: {str(e)}")


def create_page_processing_task(page_data: Dict[str, Any]) -> str:
    """
    Create a background task to process a brand guideline page.

    Args:
        page_data: Dictionary containing page data

    Returns:
        Task ID
    """
    # Generate a task ID
    task_id = f"page_task_{page_data.get('id')}_{int(time.time())}"

    # Create and start the background task
    asyncio.create_task(run_background_task(task_id, process_guideline_page, page_data))

    logger.info(
        f"Created background task {task_id} for page {page_data.get('page_number')}"
    )

    return task_id


def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get the status of a background task.

    Args:
        task_id: Task ID

    Returns:
        Dictionary with task status information
    """
    if task_id not in tasks_store:
        return {"status": "not_found"}

    return tasks_store[task_id]
