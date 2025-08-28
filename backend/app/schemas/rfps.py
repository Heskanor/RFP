"""
RFP-related Pydantic schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class RFPStatus(str, Enum):
    """RFP status enumeration"""
    draft = "draft"
    active = "active"
    closed = "closed"
    processing = "processing"

class CriteriaCategory(str, Enum):
    """Evaluation criteria categories"""
    technical = "technical"
    financial = "financial"
    delivery = "delivery"
    qualifications = "qualifications"
    other = "other"

class RFPCreate(BaseModel):
    """Schema for creating a new RFP"""
    title: str = Field(..., min_length=1, max_length=300, description="RFP title")
    description: Optional[str] = Field(None, max_length=2000, description="RFP description")
    requirements: Optional[str] = Field(None, description="Detailed requirements")

class RFPUpdate(BaseModel):
    """Schema for updating an RFP"""
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = Field(None, max_length=2000)
    requirements: Optional[str] = None
    status: Optional[RFPStatus] = None

class RFPResponse(BaseModel):
    """Schema for RFP API responses"""
    id: str
    project_id: str
    title: str
    description: Optional[str] = None
    requirements: Optional[str] = None
    status: RFPStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # TODO: Add computed fields
    # criteria_count: int = 0
    # bid_count: int = 0
    
    class Config:
        from_attributes = True

class RFPCriteriaCreate(BaseModel):
    """Schema for creating evaluation criteria"""
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=1000)
    weight: float = Field(..., ge=0.0, le=1.0, description="Criteria weight (0-1)")
    category: CriteriaCategory = CriteriaCategory.other

class RFPCriteriaUpdate(BaseModel):
    """Schema for updating evaluation criteria"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=1000)
    weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    category: Optional[CriteriaCategory] = None

class RFPCriteriaResponse(BaseModel):
    """Schema for criteria API responses"""
    id: str
    rfp_id: str
    title: str
    description: str
    weight: float
    category: CriteriaCategory
    created_at: datetime
    
    class Config:
        from_attributes = True

class RFPSummary(BaseModel):
    """Lightweight RFP summary"""
    id: str
    title: str
    status: RFPStatus
    created_at: datetime
    criteria_count: int = 0
    bid_count: int = 0

