from app.config.firebase import firebase_manager
from typing import Dict
from app.models.models import User
from fastapi import HTTPException


async def get_user(user_id: str):
    """Retrieve user details by ID."""
    try:
        user = await firebase_manager.get_document("Users", user_id)
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
async def create_user(user: User):
    """Create a new user."""
    try:
        user = await firebase_manager.create_document("Users", user.to_dict())
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
async def update_user(user_id: str, data: Dict):
    """Update user details."""
    try:
        user = await firebase_manager.update_document("Users", user_id, data)
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
