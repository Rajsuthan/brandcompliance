import os
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from dotenv import load_dotenv
import logging
import uuid
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

router = APIRouter()

# Cloudflare R2 Credentials from environment variables
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")  # R2 uses S3 compatible API
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")  # R2 uses S3 compatible API
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_PUBLIC_URL_BASE = os.getenv(
    "R2_PUBLIC_URL_BASE"
)  # Optional: Base URL for public access if bucket is public

# Check if all required environment variables are set
required_env_vars = [
    CLOUDFLARE_ACCOUNT_ID,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    R2_BUCKET_NAME,
]
s3_client: Optional[boto3.client] = None  # Define s3_client with type hint

if not all(required_env_vars):
    logger.warning(
        "Missing one or more Cloudflare R2 environment variables (CLOUDFLARE_ACCOUNT_ID, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, R2_BUCKET_NAME). Video upload endpoint will be disabled."
    )
else:
    # Construct the R2 endpoint URL
    r2_endpoint_url = f"https://{CLOUDFLARE_ACCOUNT_ID}.r2.cloudflarestorage.com"
    logger.info(f"Configuring Boto3 client for R2 endpoint: {r2_endpoint_url}")

    # Initialize Boto3 S3 client for R2
    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=r2_endpoint_url,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name="auto",  # R2 specific setting
        )
        # Optional: Test connection by trying to head the bucket
        # This requires GetBucketLocation or HeadBucket permission on the bucket
        try:
            s3_client.head_bucket(Bucket=R2_BUCKET_NAME)
            logger.info(f"Successfully connected to R2 bucket: {R2_BUCKET_NAME}")
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                logger.error(
                    f"R2 Bucket '{R2_BUCKET_NAME}' not found. Please check the name."
                )
                s3_client = None  # Disable client if bucket not found
            elif e.response["Error"]["Code"] == "403":
                logger.error(
                    f"Permission denied accessing R2 bucket '{R2_BUCKET_NAME}'. Check credentials and permissions."
                )
                s3_client = None  # Disable client on permission error
            else:
                logger.error(f"Error checking R2 bucket status: {e}")
                # Decide if you want to disable the client on other errors too
                # s3_client = None
        logger.info("Boto3 client initialized successfully for Cloudflare R2.")
    except NoCredentialsError:
        logger.error(
            "AWS credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY) not found in environment variables."
        )
        s3_client = None
    except ClientError as e:
        logger.error(f"Failed to initialize Boto3 client due to client error: {e}")
        s3_client = None
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during Boto3 client initialization: {e}"
        )
        s3_client = None


@router.post(
    "/upload-video/", status_code=status.HTTP_201_CREATED, tags=["Video Upload"]
)
async def upload_video_to_r2(file: UploadFile = File(...)):
    """
    Receives a video file and uploads it to Cloudflare R2.

    Returns the URL of the uploaded file if successful.
    """
    if not s3_client:
        logger.error(
            "Attempted to upload video, but R2 client is not available/configured."
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="R2 storage service is not configured or available. Check server logs and environment variables.",
        )

    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided.",
        )

    # Basic content type check (can be expanded)
    if not file.content_type or not file.content_type.startswith("video/"):
        logger.warning(
            f"Upload rejected: Invalid content type '{file.content_type}'. Expected video/*."
        )
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {file.content_type}. Please upload a video file.",
        )

    # Generate a unique filename to avoid collisions
    file_extension = (
        os.path.splitext(file.filename)[1] if file.filename else ".mp4"
    )  # Default extension if none
    unique_filename = f"videos/{uuid.uuid4()}{file_extension}"

    logger.info(
        f"Attempting to upload '{file.filename}' as '{unique_filename}' to R2 bucket '{R2_BUCKET_NAME}'."
    )

    try:
        # Upload the file stream directly to R2
        s3_client.upload_fileobj(
            file.file,  # The file-like object from UploadFile
            R2_BUCKET_NAME,
            unique_filename,
            ExtraArgs={
                "ContentType": file.content_type  # Set content type for proper serving
            },
        )
        logger.info(
            f"Successfully uploaded '{unique_filename}' to R2 bucket '{R2_BUCKET_NAME}'."
        )

        # Construct the public URL if the base URL is provided and the bucket is public
        file_url = None
        if R2_PUBLIC_URL_BASE:
            # Ensure no double slashes
            base_url = R2_PUBLIC_URL_BASE.rstrip("/")
            file_url = f"{base_url}/{unique_filename}"
            logger.info(f"Generated public URL: {file_url}")
        else:
            logger.info(
                "R2_PUBLIC_URL_BASE not set, returning filename instead of full URL."
            )
            # You might return the object key (unique_filename) or a signed URL if the bucket isn't public

        # For the compliance API, we need to return a single URL string, not a tuple
        # The URL will be used directly in the video compliance API
        return {"filename": unique_filename, "url": file_url}

    except ClientError as e:
        logger.error(f"Failed to upload {unique_filename} to R2: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not upload file to R2 storage: {e}",
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred during file upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during upload: {e}",
        )
    finally:
        # Ensure the file pointer is closed
        await file.close()
        logger.debug(f"Closed file stream for '{file.filename}'.")
