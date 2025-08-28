from fastapi import APIRouter, HTTPException, Path, Query, Body
from fastapi.responses import JSONResponse
from typing import Dict, Optional, List
import traceback

from app.services.evaluation_service import (
    get_evaluation_criteria,
    create_evaluation_criteria,
    update_evaluation_criteria,
    delete_evaluation_criteria,
    get_vendor_scores,
    submit_vendor_scores,
    calculate_weighted_scores,
)

router = APIRouter(prefix="/evaluation", tags=["evaluation"])

# Evaluation Criteria Management
@router.get("/projects/{project_id}/criteria")
async def get_criteria_route(
    project_id: str = Path(..., description="Unique identifier of the project")
):
    """Get evaluation criteria for a project."""
    try:
        criteria = await get_evaluation_criteria(project_id)
        return JSONResponse(status_code=200, content=criteria)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/projects/{project_id}/criteria")
async def create_criteria_route(
    project_id: str = Path(..., description="Unique identifier of the project"),
    criteria_data: Dict = Body(..., description="Evaluation criteria data")
):
    """Create evaluation criteria for a project."""
    try:
        criteria = await create_evaluation_criteria(project_id, criteria_data)
        return JSONResponse(status_code=201, content=criteria)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/criteria/{criteria_id}")
async def update_criteria_route(
    criteria_id: str = Path(..., description="Unique identifier of the criteria"),
    criteria_data: Dict = Body(..., description="Updated criteria data")
):
    """Update evaluation criteria."""
    try:
        criteria = await update_evaluation_criteria(criteria_id, criteria_data)
        if not criteria:
            raise HTTPException(status_code=404, detail="Criteria not found")
        return JSONResponse(status_code=200, content=criteria)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/criteria/{criteria_id}")
async def delete_criteria_route(
    criteria_id: str = Path(..., description="Unique identifier of the criteria")
):
    """Delete evaluation criteria."""
    try:
        result = await delete_evaluation_criteria(criteria_id)
        if not result:
            raise HTTPException(status_code=404, detail="Criteria not found")
        return JSONResponse(status_code=200, content={"message": "Criteria deleted successfully"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Vendor Scoring
@router.get("/vendors/{vendor_id}/scores")
async def get_vendor_scores_route(
    vendor_id: str = Path(..., description="Unique identifier of the vendor"),
    project_id: str = Query(..., description="Project ID for the scores")
):
    """Get scores for a vendor in a specific project."""
    try:
        scores = await get_vendor_scores(vendor_id, project_id)
        return JSONResponse(status_code=200, content=scores)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/vendors/{vendor_id}/scores")
async def submit_scores_route(
    vendor_id: str = Path(..., description="Unique identifier of the vendor"),
    scores_data: Dict = Body(..., description="Scores data including project_id, criteria scores, and justifications")
):
    """Submit or update scores for a vendor."""
    try:
        scores = await submit_vendor_scores(vendor_id, scores_data)
        return JSONResponse(status_code=200, content=scores)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects/{project_id}/scores")
async def get_project_scores_route(
    project_id: str = Path(..., description="Unique identifier of the project"),
    calculate_weighted: bool = Query(True, description="Whether to calculate weighted scores")
):
    """Get all vendor scores for a project with optional weighted calculation."""
    try:
        if calculate_weighted:
            scores = await calculate_weighted_scores(project_id)
        else:
            # Get raw scores for all vendors in project
            scores = await get_vendor_scores(None, project_id)
        return JSONResponse(status_code=200, content=scores)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
