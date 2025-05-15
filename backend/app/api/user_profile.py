from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any

from app.core.firebase_auth import get_current_firebase_user
# Import both MongoDB and Firestore functions for backward compatibility
from app.db.database import (
    get_user_compliance_analyses as get_user_compliance_analyses_mongo,
    get_brand_guidelines_by_user as get_brand_guidelines_by_user_mongo,
    get_compliance_analysis as get_compliance_analysis_mongo
)
from app.db.firestore import (
    get_user_compliance_analyses,
    get_brand_guidelines_by_user,
    get_compliance_analysis
)
from app.models.user import User

router = APIRouter()

@router.get("/profile", response_model=User)
async def get_user_profile(current_user: dict = Depends(get_current_firebase_user)):
    """Get the current user's profile"""
    return current_user

@router.get("/compliance-history")
async def get_compliance_history(current_user: dict = Depends(get_current_firebase_user)):
    """Get the user's compliance analysis history"""
    try:
        # Get compliance analyses from Firestore
        analyses = get_user_compliance_analyses(current_user["id"])
        print(f"[INFO] Retrieved {len(analyses)} compliance analyses from Firestore")
        return analyses
    except Exception as e:
        print(f"[WARNING] Failed to get compliance analyses from Firestore: {str(e)}")

        # Fallback to MongoDB
        try:
            analyses = get_user_compliance_analyses_mongo(current_user["id"])
            print(f"[INFO] Retrieved {len(analyses)} compliance analyses from MongoDB")
            return analyses
        except Exception as mongo_error:
            print(f"[ERROR] Failed to get compliance analyses from MongoDB: {str(mongo_error)}")
            return []

@router.get("/compliance-analysis/{analysis_id}")
async def get_analysis_by_id(
    analysis_id: str,
    current_user: dict = Depends(get_current_firebase_user)
):
    """Get a specific compliance analysis by ID"""
    analysis = None

    try:
        # Get compliance analysis from Firestore
        analysis = get_compliance_analysis(analysis_id)
        if analysis:
            print(f"[INFO] Retrieved compliance analysis from Firestore with ID: {analysis_id}")
    except Exception as e:
        print(f"[WARNING] Failed to get compliance analysis from Firestore: {str(e)}")

    # If not found in Firestore, try MongoDB
    if not analysis:
        try:
            analysis = get_compliance_analysis_mongo(analysis_id)
            if analysis:
                print(f"[INFO] Retrieved compliance analysis from MongoDB with ID: {analysis_id}")
        except Exception as mongo_error:
            print(f"[WARNING] Failed to get compliance analysis from MongoDB: {str(mongo_error)}")

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compliance analysis not found"
        )

    # Check if the analysis belongs to the current user
    if analysis.get("user_id") != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this analysis"
        )

    return analysis

@router.get("/brand-guidelines")
async def get_user_brand_guidelines(current_user: dict = Depends(get_current_firebase_user)):
    """Get all brand guidelines for the current user"""
    try:
        # Get brand guidelines from Firestore
        guidelines = get_brand_guidelines_by_user(current_user["id"])
        print(f"[INFO] Retrieved {len(guidelines)} brand guidelines from Firestore")
        return guidelines
    except Exception as e:
        print(f"[WARNING] Failed to get brand guidelines from Firestore: {str(e)}")

        # Fallback to MongoDB
        try:
            guidelines = get_brand_guidelines_by_user_mongo(current_user["id"])
            print(f"[INFO] Retrieved {len(guidelines)} brand guidelines from MongoDB")
            return guidelines
        except Exception as mongo_error:
            print(f"[ERROR] Failed to get brand guidelines from MongoDB: {str(mongo_error)}")
            return []
