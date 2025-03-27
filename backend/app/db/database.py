from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime

# Load environment variables
load_dotenv()

# MongoDB Connection
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("MONGODB_DB_NAME")

# Print connection details for debugging
print(f"Connecting to MongoDB with URI: {MONGODB_URI}")
print(f"Database name: {DB_NAME}")

# Create MongoDB client with timeout
try:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    # Force a connection to verify it works
    client.admin.command("ping")
    print("✅ Successfully connected to MongoDB!")
    db = client[DB_NAME]
    print(f"✅ Successfully accessed database: {DB_NAME}")
except Exception as e:
    print(f"❌ Error connecting to MongoDB: {e}")
    # Create a mock client and database for fallback
    client = None
    db = None

# Collections
users_collection = db.users
brand_guidelines_collection = db.brand_guidelines
guideline_pages_collection = db.guideline_pages


# Helper functions for database operations
def create_brand_guideline(guideline_data):
    """Create a new brand guideline record in the database"""
    guideline_data["created_at"] = datetime.utcnow()
    guideline_data["updated_at"] = datetime.utcnow()
    result = brand_guidelines_collection.insert_one(guideline_data)
    return str(result.inserted_id)


def create_guideline_page(page_data):
    """Create a new brand guideline page record in the database"""
    page_data["created_at"] = datetime.utcnow()
    result = guideline_pages_collection.insert_one(page_data)
    return str(result.inserted_id)


def get_brand_guideline(guideline_id):
    """Get a brand guideline record by ID"""
    from bson.objectid import ObjectId

    guideline_data = brand_guidelines_collection.find_one(
        {"_id": ObjectId(guideline_id)}
    )
    if guideline_data:
        guideline_data["id"] = str(guideline_data["_id"])
        return guideline_data
    return None


def get_guideline_pages(guideline_id, include_base64=False):
    """Get all pages for a brand guideline"""
    from bson.objectid import ObjectId

    # Define projection to include or exclude base64 data
    projection = None if include_base64 else {"base64": 0}

    # Find all pages for the guideline
    cursor = guideline_pages_collection.find(
        {"guideline_id": guideline_id}, projection
    ).sort("page_number", 1)

    # Convert cursor to list and add id field
    pages = []
    for page in cursor:
        page["id"] = str(page["_id"])
        pages.append(page)

    return pages


def get_guideline_page(page_id, include_base64=False):
    """Get a brand guideline page record by ID"""
    from bson.objectid import ObjectId

    # Define projection to include or exclude base64 data
    projection = None if include_base64 else {"base64": 0}

    page_data = guideline_pages_collection.find_one(
        {"_id": ObjectId(page_id)}, projection
    )

    if page_data:
        page_data["id"] = str(page_data["_id"])
        return page_data
    return None


def get_brand_guidelines_by_user(user_id):
    """Get all brand guidelines for a user"""
    cursor = brand_guidelines_collection.find({"user_id": user_id})

    guidelines = []
    for guideline in cursor:
        guideline["id"] = str(guideline["_id"])
        guidelines.append(guideline)

    return guidelines


def update_guideline_page_with_results(page_id, results):
    """
    Update a guideline page with processing results.

    Args:
        page_id: ID of the page to update
        results: Dictionary containing processing results

    Returns:
        Updated page data or None if page not found
    """
    from bson.objectid import ObjectId

    # Create update data with processing results
    update_data = {
        "$set": {
            "processing_results": results,
            "processed_at": datetime.utcnow(),
            "compliance_score": results.get("compliance_score", 0),
        }
    }

    # Update the page in the database
    result = guideline_pages_collection.update_one(
        {"_id": ObjectId(page_id)}, update_data
    )

    if result.modified_count == 0:
        return None

    # Get and return the updated page
    return get_guideline_page(page_id)
