"""
Firebase Firestore database module.
This module provides functions for interacting with Firebase Firestore.
"""

from firebase_admin import firestore
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

# Import the centralized Firebase initialization
from app.core.firebase_init import firebase_app

# Initialize Firestore client
try:
    # Get Firestore client using the existing Firebase app
    db = firestore.client(app=firebase_app)

    # Collection references
    users_collection = db.collection('users')
    brand_guidelines_collection = db.collection('brand_guidelines')
    guideline_pages_collection = db.collection('guideline_pages')
    feedback_collection = db.collection('feedback')
    compliance_analysis_collection = db.collection('compliance_analysis')
    usage_tracking_collection = db.collection('usage_tracking')

    # Create required indexes programmatically
    def create_index_if_needed(collection_name, fields, ascending=None):
        """Create a composite index for a collection if it doesn't exist"""
        try:
            from firebase_admin import firestore_admin
            from google.cloud.firestore_admin_v1.types import Index, Field

            # Get the Firestore Admin client
            client = firestore_admin.FirestoreAdminClient()

            # Get the project ID from the app
            project_id = firebase_app.project_id

            # Create the parent path
            parent = f"projects/{project_id}/databases/(default)/collectionGroups/{collection_name}"

            # Define the index fields
            index_fields = []
            for i, field in enumerate(fields):
                # Default to ascending for all fields if not specified
                is_ascending = ascending[i] if ascending and i < len(ascending) else True
                direction = Field.Direction.ASCENDING if is_ascending else Field.Direction.DESCENDING
                index_fields.append(Field(field_path=field, order=direction))

            # Create the index
            index = Index(
                query_scope=Index.QueryScope.COLLECTION,
                fields=index_fields
            )

            # Create the index in Firestore
            operation = client.create_index(parent=parent, index=index)
            print(f"✅ Creating index for {collection_name} on fields {fields}. Operation: {operation.name}")

            return True
        except Exception as e:
            print(f"⚠️ Could not create index for {collection_name}: {str(e)}")
            # This is not a critical error, so we'll continue
            return False

    # Create required indexes for our queries
    # For compliance_analysis collection - user_id + created_at (descending)
    create_index_if_needed('compliance_analysis', ['user_id', 'created_at'], [True, False])

    # For feedback collection - user_id + created_at (descending)
    create_index_if_needed('feedback', ['user_id', 'created_at'], [True, False])

    # For guideline_pages collection - guideline_id + page_number
    create_index_if_needed('guideline_pages', ['guideline_id', 'page_number'])

    # For usage_tracking collection - user_id + timestamp (descending)
    create_index_if_needed('usage_tracking', ['user_id', 'timestamp'], [True, False])

    print("✅ Firestore collections initialized successfully")
except Exception as e:
    print(f"❌ Error initializing Firestore collections: {str(e)}")
    # Set collections to None to prevent usage if initialization fails
    users_collection = None
    brand_guidelines_collection = None
    guideline_pages_collection = None
    feedback_collection = None
    compliance_analysis_collection = None
    usage_tracking_collection = None

# Helper functions for Firestore operations
def convert_to_dict(obj: Any) -> Dict:
    """
    Convert Firestore document to dictionary with proper ID field

    Args:
        obj: Firestore document or dictionary

    Returns:
        dict: Dictionary with id field
    """
    if isinstance(obj, dict):
        # If already a dict, ensure it has an id field
        if 'id' not in obj and obj.get('_id'):
            obj['id'] = obj.pop('_id')
        return obj

    # If it's a Firestore DocumentSnapshot
    data = obj.to_dict()
    if data is None:
        return None
    data['id'] = obj.id
    return data

def timestamp_to_datetime(timestamp):
    """Convert Firestore timestamp to datetime"""
    if isinstance(timestamp, datetime):
        return timestamp
    if hasattr(timestamp, 'seconds'):
        return datetime.fromtimestamp(timestamp.seconds + timestamp.nanoseconds / 1e9)
    return timestamp

# Basic CRUD operations
def create_document(collection, data: Dict) -> str:
    """
    Create a new document in the specified collection

    Args:
        collection: Firestore collection reference
        data: Dictionary containing document data

    Returns:
        str: ID of the created document
    """
    # Add timestamps
    data['created_at'] = firestore.SERVER_TIMESTAMP

    # Create document with auto-generated ID
    doc_ref = collection.document()
    doc_ref.set(data)
    return doc_ref.id

def get_document(collection, doc_id: str) -> Optional[Dict]:
    """
    Get a document by ID

    Args:
        collection: Firestore collection reference
        doc_id: Document ID

    Returns:
        dict: Document data or None if not found
    """
    doc_ref = collection.document(doc_id)
    doc = doc_ref.get()
    if doc.exists:
        return convert_to_dict(doc)
    return None

def update_document(collection, doc_id: str, data: Dict) -> str:
    """
    Update a document by ID

    Args:
        collection: Firestore collection reference
        doc_id: Document ID
        data: Dictionary containing fields to update

    Returns:
        str: Document ID
    """
    # Add updated_at timestamp
    data['updated_at'] = firestore.SERVER_TIMESTAMP

    # Update document
    doc_ref = collection.document(doc_id)
    doc_ref.update(data)
    return doc_id

def delete_document(collection, doc_id: str) -> str:
    """
    Delete a document by ID

    Args:
        collection: Firestore collection reference
        doc_id: Document ID

    Returns:
        str: Document ID
    """
    doc_ref = collection.document(doc_id)
    doc_ref.delete()
    return doc_id

def query_collection(collection, field: str, operator: str, value: Any) -> List[Dict]:
    """
    Query a collection by field

    Args:
        collection: Firestore collection reference
        field: Field to query
        operator: Comparison operator ('==', '>', '<', '>=', '<=', 'array_contains')
        value: Value to compare against

    Returns:
        list: List of matching documents
    """
    query = collection.where(field, operator, value)
    results = []
    for doc in query.stream():
        results.append(convert_to_dict(doc))
    return results

# Compliance Analysis Operations
def create_compliance_analysis(analysis_data: Dict) -> str:
    """
    Create a new compliance analysis record

    Args:
        analysis_data: Dictionary containing analysis data

    Returns:
        str: ID of the created analysis
    """
    return create_document(compliance_analysis_collection, analysis_data)

def get_compliance_analysis(analysis_id: str) -> Optional[Dict]:
    """
    Get a compliance analysis by ID

    Args:
        analysis_id: Analysis ID

    Returns:
        dict: Analysis data or None if not found
    """
    return get_document(compliance_analysis_collection, analysis_id)

def get_user_compliance_analyses(user_id: str) -> List[Dict]:
    """
    Get all compliance analyses for a user

    Args:
        user_id: User ID

    Returns:
        list: List of compliance analyses
    """
    try:
        # Try with the compound query (requires index)
        query = compliance_analysis_collection.where('user_id', '==', user_id).order_by('created_at', direction=firestore.Query.DESCENDING)
        results = []
        for doc in query.stream():
            results.append(convert_to_dict(doc))
        return results
    except Exception as e:
        # If index error, try without ordering
        if "The query requires an index" in str(e):
            print(f"⚠️ Firestore index not yet available for compliance_analysis query. This is normal if the index was just created.")
            print(f"⚠️ Index is being created for: collection='compliance_analysis', fields=['user_id', 'created_at']")
            print(f"⚠️ Falling back to unordered query and sorting in memory.")

            # Fallback to simple query without ordering
            query = compliance_analysis_collection.where('user_id', '==', user_id)
            results = []
            for doc in query.stream():
                results.append(convert_to_dict(doc))

            # Sort results in memory (not as efficient but works without index)
            results.sort(key=lambda x: x.get('created_at', 0), reverse=True)
            return results
        else:
            # Re-raise if it's not an index error
            raise

# Feedback Operations
def create_feedback(feedback_data: Dict) -> str:
    """
    Create a new user feedback record

    Args:
        feedback_data: Dictionary containing feedback data

    Returns:
        str: ID of the created feedback
    """
    return create_document(feedback_collection, feedback_data)

def get_user_feedback(user_id: str) -> List[Dict]:
    """
    Get all feedback for a specific user

    Args:
        user_id: User ID

    Returns:
        list: List of feedback records
    """
    try:
        # Try with the compound query (requires index)
        query = feedback_collection.where('user_id', '==', user_id).order_by('created_at', direction=firestore.Query.DESCENDING)
        results = []
        for doc in query.stream():
            results.append(convert_to_dict(doc))
        return results
    except Exception as e:
        # If index error, try without ordering
        if "The query requires an index" in str(e):
            print(f"WARNING: Firestore index not found for feedback query. Please create the index.")
            print(f"Index needed for: collection='feedback', fields=['user_id', 'created_at']")
            print(f"Falling back to unordered query.")

            # Fallback to simple query without ordering
            query = feedback_collection.where('user_id', '==', user_id)
            results = []
            for doc in query.stream():
                results.append(convert_to_dict(doc))

            # Sort results in memory (not as efficient but works without index)
            results.sort(key=lambda x: x.get('created_at', 0), reverse=True)
            return results
        else:
            # Re-raise if it's not an index error
            raise

# Usage Tracking Operations
def log_compliance_check(user_id: str, asset_type: str, asset_id: Optional[str] = None, analysis_id: Optional[str] = None) -> str:
    """
    Log a compliance check for usage tracking

    Args:
        user_id: User ID
        asset_type: Type of asset ('image' or 'video')
        asset_id: ID of the asset (optional)
        analysis_id: ID of the compliance analysis (optional)

    Returns:
        str: ID of the created tracking record
    """
    tracking_data = {
        'user_id': user_id,
        'asset_type': asset_type,
        'asset_id': asset_id,
        'analysis_id': analysis_id,  # Store the analysis ID for backtracking
        'timestamp': firestore.SERVER_TIMESTAMP
    }
    return create_document(usage_tracking_collection, tracking_data)

def get_user_usage(user_id: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict]:
    """
    Get usage statistics for a user

    Args:
        user_id: User ID
        start_date: Start date for filtering (optional)
        end_date: End date for filtering (optional)

    Returns:
        list: List of usage records
    """
    query = usage_tracking_collection.where('user_id', '==', user_id)

    if start_date:
        query = query.where('timestamp', '>=', start_date)
    if end_date:
        query = query.where('timestamp', '<=', end_date)

    query = query.order_by('timestamp', direction=firestore.Query.DESCENDING)

    results = []
    for doc in query.stream():
        results.append(convert_to_dict(doc))
    return results

# Brand Guidelines Operations
def create_brand_guideline(guideline_data: Dict) -> str:
    """
    Create a new brand guideline record

    Args:
        guideline_data: Dictionary containing guideline data

    Returns:
        str: ID of the created guideline
    """
    # Add updated_at timestamp
    guideline_data['updated_at'] = firestore.SERVER_TIMESTAMP

    return create_document(brand_guidelines_collection, guideline_data)

def get_brand_guideline(guideline_id: str) -> Optional[Dict]:
    """
    Get a brand guideline record by ID

    Args:
        guideline_id: Guideline ID

    Returns:
        dict: Guideline data or None if not found
    """
    return get_document(brand_guidelines_collection, guideline_id)

def get_brand_guidelines_by_user(user_id: str) -> List[Dict]:
    """
    Get all brand guidelines for a user

    Args:
        user_id: User ID

    Returns:
        list: List of brand guidelines
    """
    query = brand_guidelines_collection.where('user_id', '==', user_id)
    results = []
    for doc in query.stream():
        results.append(convert_to_dict(doc))
    return results

# Guideline Pages Operations
def create_guideline_page(page_data: Dict) -> str:
    """
    Create a new brand guideline page record

    Args:
        page_data: Dictionary containing page data

    Returns:
        str: ID of the created page
    """
    return create_document(guideline_pages_collection, page_data)

def get_guideline_page(page_id: str, include_base64: bool = False) -> Optional[Dict]:
    """
    Get a brand guideline page record by ID

    Args:
        page_id: Page ID
        include_base64: Whether to include base64 data in the result

    Returns:
        dict: Page data or None if not found
    """
    page = get_document(guideline_pages_collection, page_id)

    # Remove base64 data if not requested
    if page and not include_base64 and 'base64' in page:
        del page['base64']

    return page

def get_guideline_pages(guideline_id: str, include_base64: bool = False) -> List[Dict]:
    """
    Get all pages for a brand guideline

    Args:
        guideline_id: Guideline ID
        include_base64: Whether to include base64 data in the results

    Returns:
        list: List of guideline pages
    """
    query = guideline_pages_collection.where('guideline_id', '==', guideline_id).order_by('page_number')

    results = []
    for doc in query.stream():
        page = convert_to_dict(doc)

        # Remove base64 data if not requested
        if not include_base64 and 'base64' in page:
            del page['base64']

        results.append(page)

    return results

def update_guideline_page_with_results(page_id: str, results: Dict) -> Optional[Dict]:
    """
    Update a guideline page with processing results

    Args:
        page_id: ID of the page to update
        results: Dictionary containing processing results

    Returns:
        dict: Updated page data or None if page not found
    """
    # Create update data with processing results
    update_data = {
        'processing_results': results,
        'processed_at': firestore.SERVER_TIMESTAMP,
        'compliance_score': results.get('compliance_score', 0)
    }

    # Update the page in the database
    try:
        update_document(guideline_pages_collection, page_id, update_data)

        # Get and return the updated page
        return get_guideline_page(page_id)
    except Exception as e:
        print(f"Error updating guideline page: {str(e)}")
        return None
