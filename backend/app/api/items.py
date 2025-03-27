from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.core.auth import get_current_user
from app.models.user import User

router = APIRouter()

# Sample data
items = [
    {"id": 1, "name": "Item 1", "description": "This is item 1"},
    {"id": 2, "name": "Item 2", "description": "This is item 2"},
]


@router.get("/items", tags=["items"])
async def get_items(current_user: dict = Depends(get_current_user)):
    """
    Get all items. This endpoint requires authentication.
    """
    return items


@router.get("/items/{item_id}", tags=["items"])
async def get_item(item_id: int, current_user: dict = Depends(get_current_user)):
    """
    Get a specific item by ID. This endpoint requires authentication.
    """
    if item_id < 1 or item_id > len(items):
        raise HTTPException(status_code=404, detail="Item not found")
    return items[item_id - 1]
