from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from app.core.firebase_auth import get_current_firebase_user

router = APIRouter()

class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: Optional[str] = None
    picture: Optional[str] = None

@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: dict = Depends(get_current_firebase_user)):
    """
    Get the current authenticated user's information
    """
    return current_user

@router.post("/verify-token")
async def verify_token(current_user: dict = Depends(get_current_firebase_user)):
    """
    Verify a Firebase ID token and return user information
    This endpoint is useful for validating tokens from the frontend
    """
    return {"status": "success", "user": current_user}
