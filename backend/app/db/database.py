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
    # Set db to None and re-raise the exception to halt startup if DB connection fails
    client = None
    db = None
    raise e

# Collections
users_collection = db.users
brand_guidelines_collection = db.brand_guidelines
guideline_pages_collection = db.guideline_pages
feedback_collection = db.feedback
compliance_analysis_collection = db.compliance_analysis


# Helper functions for database operations

def convert_mongo_doc_to_json(doc):
    """
    Convert MongoDB document to JSON-serializable format

    Args:
        doc: MongoDB document

    Returns:
        dict: JSON-serializable dictionary
    """
    if doc is None:
        return None

    from bson.objectid import ObjectId
    import json

    # Convert ObjectId to string
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["id"] = str(doc["_id"])

    # Handle nested documents
    for key, value in list(doc.items()):
        if isinstance(value, ObjectId):
            doc[key] = str(value)
        elif isinstance(value, dict):
            doc[key] = convert_mongo_doc_to_json(value)
        elif isinstance(value, list):
            doc[key] = [
                convert_mongo_doc_to_json(item) if isinstance(item, dict) else
                str(item) if isinstance(item, ObjectId) else item
                for item in value
            ]

    return doc
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
        # Convert MongoDB document to JSON-serializable format
        return convert_mongo_doc_to_json(guideline_data)
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
        # Convert MongoDB document to JSON-serializable format
        json_page = convert_mongo_doc_to_json(page)
        pages.append(json_page)

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
        # Convert MongoDB document to JSON-serializable format
        return convert_mongo_doc_to_json(page_data)
    return None


def get_brand_guidelines_by_user(user_id):
    """Get all brand guidelines for a user"""
    cursor = brand_guidelines_collection.find({"user_id": user_id})

    guidelines = []
    for guideline in cursor:
        # Convert MongoDB document to JSON-serializable format
        json_guideline = convert_mongo_doc_to_json(guideline)
        guidelines.append(json_guideline)

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

    # Convert any ObjectId in results to string
    results = convert_mongo_doc_to_json(results)

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


def create_feedback(feedback_data):
    """Create a new user feedback record in the database"""
    feedback_data["created_at"] = datetime.utcnow()
    result = feedback_collection.insert_one(feedback_data)
    return str(result.inserted_id)


def get_user_feedback(user_id):
    """Get all feedback for a specific user"""
    from bson.objectid import ObjectId

    cursor = feedback_collection.find({"user_id": user_id}).sort("created_at", -1)

    feedback_list = []
    for feedback in cursor:
        # Convert MongoDB document to JSON-serializable format
        json_feedback = convert_mongo_doc_to_json(feedback)
        feedback_list.append(json_feedback)

    return feedback_list


def create_compliance_analysis(analysis_data):
    """Create a new compliance analysis record in the database"""
    analysis_data["created_at"] = datetime.utcnow()
    result = compliance_analysis_collection.insert_one(analysis_data)
    return str(result.inserted_id)


def get_compliance_analysis(analysis_id):
    """Get a compliance analysis by ID"""
    from bson.objectid import ObjectId

    analysis = compliance_analysis_collection.find_one({"_id": ObjectId(analysis_id)})
    if analysis:
        # Convert MongoDB document to JSON-serializable format
        return convert_mongo_doc_to_json(analysis)
    return None


def get_user_compliance_analyses(user_id):
    """Get all compliance analyses for a user"""
    cursor = compliance_analysis_collection.find({"user_id": user_id}).sort("created_at", -1)

    analyses = []
    for analysis in cursor:
        # Convert MongoDB document to JSON-serializable format
        json_analysis = convert_mongo_doc_to_json(analysis)
        analyses.append(json_analysis)

    return analyses
