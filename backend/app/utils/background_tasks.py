"""
Background Tasks Module

This module provides functionality for running tasks in the background.
"""

import asyncio
import logging
import traceback
from typing import Dict, Any, List, Callable, Coroutine, Optional, Union
import time
import random
import multiprocessing
from datetime import datetime
from app.core.agent.llm import llm
from app.utils.pdf_to_image import pdf_to_image_fitz, pdf_to_image
from app.db.database import create_guideline_page

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

        import os
        from openai import OpenAI

        # Prepare the image as base64
        image_base64 = page_data["base64"]
        if image_base64.startswith("data:image"):
            # Remove data URL prefix if present
            image_base64 = image_base64.split(",", 1)[-1]

        # Prepare the system prompt and user message
        system_prompt = """
You will receive an image of a page from a brand guideline PDF. Provide a brief, keyword-optimized summary (1-2 lines max or comma-separated) that clearly states:

– What the page is about (e.g., design principle, color usage, typography)
– What brand element it refers to (e.g., logo, color, font)
– What must be followed or applied (e.g., use trademark red, consistent typography)
– Include any visual context shown (e.g., product images, examples)

The output should be dense and clear for search/embeddings—no extra explanation or filler.

Example Based on Your Image:
Color usage principle, emphasizes trademark red, shows product cans in various colors (cherry, vanilla, lemon, lime, orange), rule: use red as dominant color to differentiate products and maintain brand consistency
        """

        # Instantiate OpenAI client for Gemini
        client = OpenAI(
            api_key=os.getenv("GOOGLE_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )

        # Compose the Gemini Vision API call
        response = client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "here is the image:"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            },
                        },
                    ],
                },
            ],
            max_tokens=256,
        )

        # Extract the result text
        result_text = response.choices[0].message.content.strip() if response.choices else ""

        # Create final result
        final_result = {
            "page_id": page_id,
            "guideline_id": guideline_id,
            "page_number": page_number,
            "result": result_text,
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


async def process_pdf_batch(
    guideline_id: str,
    pdf_path: str,
    total_pages: int,
    include_base64: bool = True,
    dpi: int = 100,
    max_workers: Optional[int] = None
) -> Dict[str, Any]:
    """
    Process all pages of a PDF in parallel using PyMuPDF.
    This is much faster than processing pages individually.
    
    Args:
        guideline_id: ID of the brand guideline
        pdf_path: Path to the PDF file
        total_pages: Total number of pages in the PDF
        include_base64: Whether to include base64 encoding of the images
        dpi: DPI for the output images
        max_workers: Maximum number of worker processes
        
    Returns:
        Dictionary with processing results
    """
    logger.info(f"Starting batch processing of PDF with {total_pages} pages")
    start_time = time.time()
    
    # Use PyMuPDF for faster processing if available
    # Set max workers based on CPU cores and page count
    if max_workers is None:
        max_workers = min(multiprocessing.cpu_count(), 8)
        
    # For small PDFs, use fewer workers
    if total_pages < max_workers:
        max_workers = max(1, total_pages)
        
    logger.info(f"Using pdf_to_image with {max_workers} workers")
        
    # Process all pages in parallel
    results = pdf_to_image(
        pdf_path=pdf_path,
        include_base64=include_base64,
        dpi=dpi,
        max_workers=max_workers,
        verbose=True
    )
        
    # Store pages in batches to avoid memory issues
    batch_size = 5  # Process 5 pages at a time
    total_processed = 0
        
    for i in range(0, len(results), batch_size):
        batch = results[i:i+batch_size]
            
        for result in batch:
            if result["success"]:
                # Store page in database
                page_data = {
                    "guideline_id": guideline_id,
                    "page_number": result["page"] + 1,  # Convert to 1-based
                    "width": result["width"],
                    "height": result["height"],
                    "base64": result.get("base64", None)
                }
                    
                # Create page in database
                page_id = create_guideline_page(page_data)
                total_processed += 1

                # Call LLM to process the page and generate tags/summary
                from app.db.database import update_guideline_page_with_results
                page_data_with_id = dict(page_data)
                page_data_with_id["id"] = page_id
                llm_result = await process_guideline_page(page_data_with_id)
                update_guideline_page_with_results(page_id, llm_result)
                    
        # Log progress
        progress = (i + len(batch)) / len(results) * 100
        logger.info(f"Processed {i + len(batch)}/{len(results)} pages ({progress:.1f}%)")
            
    elapsed = time.time() - start_time
    pages_per_second = total_processed / elapsed
    logger.info(
        f"Completed batch processing: {total_processed}/{total_pages} pages in {elapsed:.2f}s "
        f"({pages_per_second:.2f} pages/sec)"
    )
        
    # Clean up the temporary PDF file after processing
    try:
        import os
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)
            logger.info(f"Deleted temporary PDF file: {pdf_path}")
    except Exception as cleanup_err:
        logger.error(f"Failed to delete temporary PDF file {pdf_path}: {cleanup_err}")

    return {
        "success": True,
        "total_pages": total_pages,
        "processed_pages": total_processed,
        "elapsed_time": elapsed,
        "pages_per_second": pages_per_second
    }


def create_page_processing_task(
    guideline_id: str,
    total_pages: int,
    pdf_path: str = None,
    include_base64: bool = True,
    dpi: int = 100,
    max_workers: Optional[int] = None
) -> str:
    """
    Create a background task to process a brand guideline PDF.

    Args:
        guideline_id: ID of the brand guideline
        total_pages: Total number of pages in the PDF
        pdf_path: Path to the PDF file (for batch processing)
        include_base64: Whether to include base64 encoding of the images
        dpi: DPI for the output images
        max_workers: Maximum number of worker processes

    Returns:
        Task ID
    """
    # Generate a task ID
    task_id = f"pdf_task_{guideline_id}_{int(time.time())}"

    # If PDF path is provided, use batch processing regardless of PyMuPDF
    if pdf_path:
        logger.info(f"Creating batch processing task for PDF with {total_pages} pages")
        asyncio.create_task(
            run_background_task(
                task_id, 
                process_pdf_batch, 
                guideline_id, 
                pdf_path, 
                total_pages, 
                include_base64, 
                dpi, 
                max_workers
            )
        )
    else:
        logger.error("PDF path not provided. Cannot start background PDF processing task.")
        raise RuntimeError("PDF path is required to process brand guidelines.")

    logger.info(f"Created background task {task_id} for guideline {guideline_id}")
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
