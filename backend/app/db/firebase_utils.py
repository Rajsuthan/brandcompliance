"""Firebase utilities module.

This module provides utility functions for interacting with Firebase services.
"""

from firebase_admin import firestore
from typing import Optional

# Import the centralized Firebase initialization
from app.core.firebase_init import firebase_app


def get_firestore_client() -> firestore.Client:
    """
    Get the Firestore client using the existing Firebase app.
    
    Returns:
        firestore.Client: Initialized Firestore client
    """
    return firestore.client(app=firebase_app)


def get_collection(collection_name: str) -> firestore.CollectionReference:
    """
    Get a reference to a Firestore collection.
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        firestore.CollectionReference: Reference to the collection
    """
    db = get_firestore_client()
    return db.collection(collection_name)


def get_document_ref(collection_name: str, doc_id: str) -> firestore.DocumentReference:
    """
    Get a reference to a Firestore document.
    
    Args:
        collection_name: Name of the collection
        doc_id: ID of the document
        
    Returns:
        firestore.DocumentReference: Reference to the document
    """
    collection = get_collection(collection_name)
    return collection.document(doc_id)
