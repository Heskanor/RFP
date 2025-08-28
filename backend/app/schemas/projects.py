"""
Project-related Pydantic schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class ProjectStatus(str, Enum):
    """Project status enumeration"""
    active = "active"
    completed = "completed"
    archived = "archived"
    draft = "draft"

class ProjectCreate(BaseModel):
    """Schema for creating a new project"""
    name: str = Field(..., min_length=1, max_length=200, description="Project name")
    description: Optional[str] = Field(None, max_length=1000, description="Project description")
    
class ProjectUpdate(BaseModel):
    """Schema for updating a project"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[ProjectStatus] = None

class ProjectResponse(BaseModel):
    """Schema for project API responses"""
    id: str
    name: str
    description: Optional[str] = None
    status: ProjectStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # TODO: Add related data counts
    # rfp_count: int = 0
    # bid_count: int = 0
    
    class Config:
        from_attributes = True

class ProjectSummary(BaseModel):
    """Lightweight project summary"""
    id: str
    name: str
    status: ProjectStatus
    created_at: datetime

