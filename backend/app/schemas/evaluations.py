"""
Evaluation and analysis-related Pydantic schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class EvaluationResponse(BaseModel):
    """Schema for comprehensive RFP evaluation"""
    rfp_id: str
    total_bids: int
    evaluation_summary: str
    top_recommendations: List[Dict[str, Any]] = []
    generated_at: datetime

class ComparisonResponse(BaseModel):
    """Schema for bid comparison matrix"""
    rfp_id: str
    comparison_matrix: List[Dict[str, Any]] = []
    overall_ranking: List[Dict[str, Any]] = []

class ChatRequest(BaseModel):
    """Schema for chat requests"""
    message: str = Field(..., min_length=1, max_length=1000, description="User message")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")

class ChatResponse(BaseModel):
    """Schema for AI chat responses"""
    message: str
    context: Optional[Dict[str, Any]] = None

class ReportRequest(BaseModel):
    """Schema for generating evaluation reports"""
    format: str = Field(default="pdf", description="Report format (pdf, excel, json)")
    include_sections: Optional[List[str]] = Field(None, description="Sections to include")
    
class ReportResponse(BaseModel):
    """Schema for report generation response"""
    report_id: str
    status: str
    download_url: Optional[str] = None
    generated_at: datetime

class ScoreBreakdown(BaseModel):
    """Schema for detailed score breakdown"""
    criteria_id: str
    criteria_title: str
    weight: float
    score: float
    weighted_score: float
    explanation: Optional[str] = None

class VendorAnalysis(BaseModel):
    """Schema for individual vendor analysis"""
    bid_id: str
    vendor_name: str
    overall_score: float
    score_breakdown: List[ScoreBreakdown] = []
    strengths: List[str] = []
    weaknesses: List[str] = []
    risk_level: str = "medium"  # low, medium, high
    recommendation: Optional[str] = None

