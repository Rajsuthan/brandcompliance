import os
import shutil
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    status,
    BackgroundTasks,
)
from typing import List, Optional, Dict, Any
import tempfile
from datetime import datetime
from bson.objectid import ObjectId

from app.utils.pdf_to_image import pdf_to_image, get_pdf_page_count
from app.utils.background_tasks import create_page_processing_task, get_task_status

from app.core.auth import get_current_user
from app.models.pdf import (
    BrandGuideline,
    BrandGuidelineCreate,
    BrandGuidelinePage,
    BrandGuidelinePageWithBase64,
    BrandGuidelineUploadResponse,
)
from app.db.database import (
    create_brand_guideline,
    create_guideline_page,
    get_brand_guideline,
    get_guideline_pages,
    get_guideline_page,
    get_brand_guidelines_by_user,
)

router = APIRouter()


@router.post("/brand-guidelines/upload", response_model=BrandGuidelineUploadResponse)
async def upload_brand_guideline(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    brand_name: str = Form(...),
    description: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload a brand guideline PDF and convert its pages to images.

    This endpoint:
    1. Accepts a PDF file upload
    2. Saves the file temporarily
    3. Processes each page using the pdf_to_image function
    4. Stores metadata in the brand_guidelines collection
    5. Stores each page's data in the guideline_pages collection
    """
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed",
        )

    # Create a temporary file to store the uploaded PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        # Write the uploaded file content to the temporary file
        shutil.copyfileobj(file.file, temp_file)
        temp_file_path = temp_file.name

    try:
        # Get the total number of pages in the PDF
        total_pages = get_pdf_page_count(temp_file_path)

        if total_pages == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not process the PDF file. It may be corrupted or empty.",
            )

        # Create a brand guideline record in the database
        guideline_data = {
            "filename": file.filename,
            "user_id": current_user["id"],
            "brand_name": brand_name,
            "total_pages": total_pages,
            "description": description,
        }

        guideline_id = create_brand_guideline(guideline_data)

        # Process the PDF pages
        results = pdf_to_image(
            pdf_path=temp_file_path,
            include_base64=True,  # We need the base64 data for storage
            verbose=False,  # Don't print status messages
        )

        # Store each page in the database
        pages_processed = 0

        # If results is a single dict (for single page PDFs), convert to list
        if isinstance(results, dict):
            results = [results]

        for result in results:
            print(f"Processing result: {result}")
            if result["success"]:
                print(f"Result is successful for page {result['page']}")
                # Create page data
                page_data = {
                    "guideline_id": guideline_id,
                    "page_number": result["page"],
                    "width": result["width"],
                    "height": result["height"],
                    "format": result["format"],
                    "base64": result["base64"],
                }
                print(f"Created page data")

                # Store page in database
                page_id = create_guideline_page(page_data)
                print(f"Stored page in database with ID")

                # Process the page directly instead of creating a background task
                from app.utils.background_tasks import process_guideline_page
                from app.db.database import update_guideline_page_with_results
                import asyncio

                print("Imported required modules")

                # Create page data with ID for processing
                page_with_id = {
                    "id": page_id,
                    "guideline_id": guideline_id,
                    "page_number": result["page"],
                    "width": result["width"],
                    "height": result["height"],
                    "format": result["format"],
                    "base64": f"data:image/{result['format']};base64,{result['base64']}",  # Format as data URL
                }
                print(f"Created page data with ID")

                # Process the page directly (run the async function in the event loop)
                print("Starting page processing...")
                processing_result = await process_guideline_page(page_with_id)
                print(f"Page processing complete.")

                # Update the page in the database with the processing results
                updated_page = update_guideline_page_with_results(
                    page_id, processing_result
                )
                print(f"Updated page in database")

                print(f"Processed page directly")

                pages_processed += 1
                print(f"Pages processed so far")

        # Get the created guideline with ID
        guideline = get_brand_guideline(guideline_id)

        # Convert to response model
        guideline_response = {
            "id": guideline["id"],
            "filename": guideline["filename"],
            "user_id": guideline["user_id"],
            "brand_name": guideline["brand_name"],
            "total_pages": guideline["total_pages"],
            "description": guideline.get("description"),
            "created_at": guideline["created_at"],
            "updated_at": guideline["updated_at"],
        }

        return {
            "guideline": guideline_response,
            "pages_processed": pages_processed,
            "message": f"Successfully processed {pages_processed} pages of {guideline['filename']}",
        }

    except Exception as e:
        # Handle any errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing PDF: {str(e)}",
        )
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@router.get("/brand-guidelines", response_model=List[BrandGuideline])
async def get_user_brand_guidelines(current_user: dict = Depends(get_current_user)):
    """Get all brand guidelines for the current user"""
    guidelines = get_brand_guidelines_by_user(current_user["id"])
    return guidelines


@router.get("/brand-guidelines/{guideline_id}", response_model=BrandGuideline)
async def get_brand_guideline_by_id(
    guideline_id: str, current_user: dict = Depends(get_current_user)
):
    """Get a specific brand guideline by ID"""
    guideline = get_brand_guideline(guideline_id)

    if not guideline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand guideline not found",
        )

    # Check if the guideline belongs to the current user
    if guideline["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this brand guideline",
        )

    return guideline


@router.get(
    "/brand-guidelines/{guideline_id}/pages", response_model=List[BrandGuidelinePage]
)
async def get_guideline_pages_by_guideline_id(
    guideline_id: str, current_user: dict = Depends(get_current_user)
):
    """Get all pages for a specific brand guideline"""
    # First check if the guideline exists and belongs to the user
    guideline = get_brand_guideline(guideline_id)

    if not guideline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand guideline not found",
        )

    if guideline["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this brand guideline",
        )

    # Get the pages without base64 data to reduce response size
    pages = get_guideline_pages(guideline_id, include_base64=False)
    return pages


@router.get(
    "/brand-guidelines/pages/{page_id}", response_model=BrandGuidelinePageWithBase64
)
async def get_guideline_page_by_id(
    page_id: str, current_user: dict = Depends(get_current_user)
):
    """Get a specific brand guideline page by ID, including base64 data"""
    # Get the page with base64 data
    page = get_guideline_page(page_id, include_base64=True)

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand guideline page not found",
        )

    # Get the guideline to check ownership
    guideline = get_brand_guideline(page["guideline_id"])

    if guideline["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this page",
        )

    return page


@router.get("/tasks")
async def get_all_tasks(current_user: dict = Depends(get_current_user)):
    """
    Get all background tasks.

    This endpoint allows clients to list all background tasks.
    """
    from app.utils.background_tasks import tasks_store

    # Filter tasks that the user has permission to access
    user_tasks = {}

    for task_id, task_data in tasks_store.items():
        # Check if the task has a result with guideline_id
        if task_data["status"] == "completed" and "result" in task_data:
            result = task_data["result"]
            if isinstance(result, dict) and "guideline_id" in result:
                guideline_id = result["guideline_id"]
                guideline = get_brand_guideline(guideline_id)

                # Only include tasks for guidelines owned by the user
                if guideline and guideline["user_id"] == current_user["id"]:
                    user_tasks[task_id] = task_data
        else:
            # For tasks that are not completed or don't have guideline_id,
            # include them if they have a page_id that starts with "page_task_"
            if task_id.startswith("page_task_"):
                user_tasks[task_id] = task_data

    return user_tasks


@router.get("/tasks/{task_id}")
async def get_task_status_by_id(
    task_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Get the status of a background task.

    This endpoint allows clients to check the progress of page processing tasks.
    """
    # Get the task status
    task_status = get_task_status(task_id)

    if task_status["status"] == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # If the task has a result with guideline_id, check ownership
    if task_status["status"] == "completed" and "result" in task_status:
        result = task_status["result"]
        if isinstance(result, dict) and "guideline_id" in result:
            guideline_id = result["guideline_id"]
            guideline = get_brand_guideline(guideline_id)

            if guideline and guideline["user_id"] != current_user["id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to access this task",
                )

    return task_status
