from fastapi import APIRouter, HTTPException, Path, Query, Body, File, UploadFile
from fastapi.responses import JSONResponse
from typing import Dict, Optional, List
import traceback

from app.services.user_service import (
    get_user,
    create_user,
    update_user,
)

router = APIRouter()

@router.get("/users/{user_id}")
async def get_user_route(user_id: str = Path(..., description="Unique identifier of the user")):
    """Retrieve user details by ID."""
    try:
        user = await get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users")
async def create_user_route(user: Dict = Body(..., description="User details to create")):
    """Create a new user."""
    try:
        user = await create_user(user)
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/users/{user_id}")
async def update_user_route(
    user_id: str = Path(..., description="Unique identifier of the user"), 
    data: Dict = Body(..., description="User details to update")):
    """Update user details."""
    try:
        user = await update_user(user_id, data)
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

