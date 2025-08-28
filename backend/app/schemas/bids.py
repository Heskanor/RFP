"""
Bid-related Pydantic schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class BidStatus(str, Enum):
    """Bid status enumeration"""
    submitted = "submitted"
    processing = "processing"
    evaluated = "evaluated"
    withdrawn = "withdrawn"

class BidCreate(BaseModel):
    """Schema for creating a new bid"""
    vendor_name: str = Field(..., min_length=1, max_length=200, description="Vendor company name")
    contact_email: Optional[str] = Field(None, description="Vendor contact email")
    contact_phone: Optional[str] = Field(None, description="Vendor contact phone")
    proposal_summary: Optional[str] = Field(None, max_length=2000, description="Brief proposal summary")

class BidUpdate(BaseModel):
    """Schema for updating a bid"""
    vendor_name: Optional[str] = Field(None, min_length=1, max_length=200)
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    proposal_summary: Optional[str] = Field(None, max_length=2000)
    status: Optional[BidStatus] = None

class BidResponse(BaseModel):
    """Schema for bid API responses"""
    id: str
    rfp_id: str
    vendor_name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    proposal_summary: Optional[str] = None
    status: BidStatus
    score: Optional[float] = None
    submitted_at: datetime
    evaluated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class BidScoreCreate(BaseModel):
    """Schema for creating/updating bid scores"""
    criteria_id: str
    score: float = Field(..., ge=0.0, le=100.0, description="Score out of 100")
    explanation: Optional[str] = Field(None, max_length=1000, description="Score explanation")

class BidScoreResponse(BaseModel):
    """Schema for bid score responses"""
    id: str
    bid_id: str
    criteria_id: str
    score: float
    explanation: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class BidAnalysisResponse(BaseModel):
    """Schema for comprehensive bid analysis"""
    bid_id: str
    overall_score: float
    strengths: List[str] = []
    weaknesses: List[str] = []
    recommendations: List[str] = []
    criteria_scores: List[Dict[str, Any]] = []
    generated_at: datetime

class BidSummary(BaseModel):
    """Lightweight bid summary"""
    id: str
    vendor_name: str
    status: BidStatus
    score: Optional[float] = None
    submitted_at: datetime

class BidComparison(BaseModel):
    """Schema for comparing multiple bids"""
    rfp_id: str
    bids: List[BidSummary]
    criteria_comparison: List[Dict[str, Any]] = []
    recommendations: List[str] = []

