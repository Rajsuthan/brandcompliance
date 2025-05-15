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

# In-memory progress tracking for guideline processing
processing_progress = {}

# from app.core.auth import get_current_user
from app.core.firebase_auth import get_current_user_compatibility as get_current_user
from app.models.pdf import (
    BrandGuideline,
    BrandGuidelineCreate,
    BrandGuidelinePage,
    BrandGuidelinePageWithBase64,
    BrandGuidelineUploadResponse,
)
from app.db.database import (
    create_brand_guideline as create_brand_guideline_mongo,
    create_guideline_page as create_guideline_page_mongo,
    get_brand_guideline as get_brand_guideline_mongo,
    get_guideline_pages as get_guideline_pages_mongo,
    get_guideline_page as get_guideline_page_mongo,
    get_brand_guidelines_by_user as get_brand_guidelines_by_user_mongo,
)

# Import Firestore functions
from app.db.firestore import (
    create_brand_guideline,
    create_guideline_page,
    get_brand_guideline,
    get_guideline_pages,
    get_guideline_page,
    get_brand_guidelines_by_user,
)

import logging
logger = logging.getLogger(__name__)

router = APIRouter()


from fastapi.responses import StreamingResponse
import json

@router.post("/brand-guidelines/upload")
async def upload_brand_guideline(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    brand_name: str = Form(...),
    description: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload a brand guideline PDF and stream progress as each page is processed.
    """
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed",
        )

    # Create a temporary file to store the uploaded PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        shutil.copyfileobj(file.file, temp_file)
        temp_file_path = temp_file.name

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
    # Create brand guideline record in Firestore
    try:
        guideline_id = create_brand_guideline(guideline_data)
        print(f"[INFO] Created brand guideline in Firestore with ID: {guideline_id}")
    except Exception as e:
        print(f"[WARNING] Failed to create brand guideline in Firestore: {str(e)}")
        # Fallback to MongoDB
        try:
            guideline_id = create_brand_guideline_mongo(guideline_data)
            print(f"[INFO] Created brand guideline in MongoDB with ID: {guideline_id}")
        except Exception as e2:
            print(f"[ERROR] Failed to create brand guideline in MongoDB: {str(e2)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create brand guideline",
            )

    from app.utils.pdf_to_image import pdf_to_image_fitz
    from app.utils.background_tasks import process_guideline_page

    async def event_stream():
        # Extract pages as images
        results = pdf_to_image_fitz(
            pdf_path=temp_file_path,
            include_base64=True,
            dpi=100,
            max_workers=None,
            verbose=True
        )
        processed = 0
        for result in results:
            if result["success"]:
                # Store page in database 
                page_data = {
                    "guideline_id": str(guideline_id),
                    "page_number": result["page"] + 1,
                    "width": result["width"],
                    "height": result["height"],
                    "base64": result.get("base64", None)
                }
                # Create page record in Firestore
                try:
                    page_id = create_guideline_page(page_data)
                    print(f"[INFO] Created guideline page in Firestore with ID: {page_id}")
                except Exception as e:
                    print(f"[WARNING] Failed to create guideline page in Firestore: {str(e)}")
                    # Fallback to MongoDB
                    try:
                        page_id = create_guideline_page_mongo(page_data)
                        print(f"[INFO] Created guideline page in MongoDB with ID: {page_id}")
                    except Exception as e2:
                        print(f"[ERROR] Failed to create guideline page in MongoDB: {str(e2)}")
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to create guideline page",
                        )
                # LLM processing
                page_data_with_id = dict(page_data)
                page_data_with_id["id"] = page_id
                llm_result = await process_guideline_page(page_data_with_id)
                # Update page with results in Firestore
                try:
                    from app.db.firestore import update_guideline_page_with_results
                    update_guideline_page_with_results(page_id, llm_result)
                except Exception as e:
                    print(f"[WARNING] Failed to update guideline page in Firestore: {str(e)}")
                    # Fallback to MongoDB
                    try:
                        from app.db.database import update_guideline_page_with_results as update_guideline_page_with_results_mongo
                        update_guideline_page_with_results_mongo(page_id, llm_result)
                    except Exception as e2:
                        print(f"[WARNING] Failed to update guideline page in MongoDB: {str(e2)}")
                processed += 1
                percent = int((processed / total_pages) * 100)
                # Stream progress as JSON line
                yield f"data: {json.dumps({'progress': percent, 'processed_pages': processed, 'total_pages': total_pages, 'guideline_id': str(guideline_id)})}\n\n"
        # Final result
        guideline = get_brand_guideline(guideline_id)
        # Convert datetime fields to ISO strings for JSON serialization
        def iso(val):
            if isinstance(val, datetime):
                return val.isoformat()
            return val

        guideline_response = {
            "id": guideline["id"],
            "filename": guideline["filename"],
            "user_id": guideline["user_id"],
            "brand_name": guideline["brand_name"],
            "total_pages": guideline["total_pages"],
            "description": guideline.get("description"),
            "created_at": iso(guideline["created_at"]),
            "updated_at": iso(guideline["updated_at"]),
        }
        yield f"data: {json.dumps({'progress': 100, 'status': 'done', 'guideline': guideline_response})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

# Progress endpoint for frontend polling
@router.get("/brand-guidelines/{guideline_id}/progress")
async def get_guideline_processing_progress(guideline_id: str):
    progress = processing_progress.get(str(guideline_id))
    if not progress:
        return {"status": "not_found", "progress": 0}
    return progress


@router.get("/brand-guidelines", response_model=List[BrandGuideline])
async def get_user_brand_guidelines(current_user: dict = Depends(get_current_user)):
    """Get all brand guidelines for the current user"""
    # Get all brand guidelines for the user from Firestore
    try:
        guidelines = get_brand_guidelines_by_user(current_user["id"])
        print(f"[INFO] Retrieved {len(guidelines)} brand guidelines from Firestore")
    except Exception as e:
        print(f"[WARNING] Failed to get brand guidelines from Firestore: {str(e)}")
        # Fallback to MongoDB
        try:
            guidelines = get_brand_guidelines_by_user_mongo(current_user["id"])
            print(f"[INFO] Retrieved {len(guidelines)} brand guidelines from MongoDB")
        except Exception as e2:
            print(f"[ERROR] Failed to get brand guidelines from MongoDB: {str(e2)}")
            guidelines = []
    return guidelines


@router.get("/brand-guidelines/{guideline_id}", response_model=BrandGuideline)
async def get_brand_guideline_by_id(
    guideline_id: str, current_user: dict = Depends(get_current_user)
):
    """Get a specific brand guideline by ID"""
    # Get brand guideline from Firestore
    try:
        guideline = get_brand_guideline(guideline_id)
        if guideline:
            print(f"[INFO] Retrieved brand guideline from Firestore with ID: {guideline_id}")
    except Exception as e:
        print(f"[WARNING] Failed to get brand guideline from Firestore: {str(e)}")
        guideline = None

    # If not found in Firestore, try MongoDB
    if not guideline:
        try:
            guideline = get_brand_guideline_mongo(guideline_id)
            if guideline:
                print(f"[INFO] Retrieved brand guideline from MongoDB with ID: {guideline_id}")
        except Exception as e:
            print(f"[ERROR] Failed to get brand guideline from MongoDB: {str(e)}")

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
    try:
        # Try to get pages from Firestore
        pages = get_guideline_pages(guideline_id, include_base64=False)
        print(f"[INFO] Retrieved {len(pages)} guideline pages from Firestore")
    except Exception as e:
        print(f"[WARNING] Failed to get guideline pages from Firestore: {str(e)}")
        # Fallback to MongoDB
        try:
            pages = get_guideline_pages_mongo(guideline_id, include_base64=False)
            print(f"[INFO] Retrieved {len(pages)} guideline pages from MongoDB")
        except Exception as e2:
            print(f"[ERROR] Failed to get guideline pages from MongoDB: {str(e2)}")
            pages = []
    return pages


@router.get(
    "/brand-guidelines/pages/{page_id}", response_model=BrandGuidelinePageWithBase64
)
async def get_guideline_page_by_id(
    page_id: str, current_user: dict = Depends(get_current_user)
):
    """Get a specific brand guideline page by ID, including base64 data"""
    # Get the page with base64 data from Firestore
    try:
        page = get_guideline_page(page_id, include_base64=True)
        if page:
            print(f"[INFO] Retrieved guideline page from Firestore with ID: {page_id}")
    except Exception as e:
        print(f"[WARNING] Failed to get guideline page from Firestore: {str(e)}")
        page = None

    # If not found in Firestore, try MongoDB
    if not page:
        try:
            page = get_guideline_page_mongo(page_id, include_base64=True)
            if page:
                print(f"[INFO] Retrieved guideline page from MongoDB with ID: {page_id}")
        except Exception as e:
            print(f"[ERROR] Failed to get guideline page from MongoDB: {str(e)}")

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
