from fastapi import APIRouter, HTTPException, Path, Query, Body, File, UploadFile
from fastapi.responses import JSONResponse
from typing import Dict, Optional, List
import traceback

from app.services.bid_service import (
    get_bids,
    get_bid,
    create_bid,
    update_bid,
    delete_bid,
    upload_bid_document,
    get_bid_documents,
)

router = APIRouter(prefix="/bids", tags=["bids"])

@router.get("")
async def get_bids_route(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    vendor_id: Optional[str] = Query(None, description="Filter by vendor ID"),
    status: Optional[str] = Query(None, description="Filter by bid status"),
    limit: int = Query(50, description="Number of bids to return"),
    offset: int = Query(0, description="Offset for pagination")
):
    """Get bids with optional filtering."""
    try:
        bids = await get_bids(
            project_id=project_id,
            vendor_id=vendor_id, 
            status=status,
            limit=limit,
            offset=offset
        )
        return JSONResponse(status_code=200, content=bids)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{bid_id}")
async def get_bid_route(
    bid_id: str = Path(..., description="Unique identifier of the bid")
):
    """Get bid details by ID."""
    try:
        bid = await get_bid(bid_id)
        if not bid:
            raise HTTPException(status_code=404, detail="Bid not found")
        return JSONResponse(status_code=200, content=bid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
async def create_bid_route(
    bid_data: Dict = Body(..., description="Bid information including project_id, vendor_id, summary, etc.")
):
    """Create a new bid submission."""
    try:
        bid = await create_bid(bid_data)
        return JSONResponse(status_code=201, content=bid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{bid_id}")
async def update_bid_route(
    bid_id: str = Path(..., description="Unique identifier of the bid"),
    bid_data: Dict = Body(..., description="Updated bid information")
):
    """Update bid information."""
    try:
        bid = await update_bid(bid_id, bid_data)
        if not bid:
            raise HTTPException(status_code=404, detail="Bid not found")
        return JSONResponse(status_code=200, content=bid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{bid_id}")
async def delete_bid_route(
    bid_id: str = Path(..., description="Unique identifier of the bid")
):
    """Delete a bid."""
    try:
        result = await delete_bid(bid_id)
        if not result:
            raise HTTPException(status_code=404, detail="Bid not found")
        return JSONResponse(status_code=200, content={"message": "Bid deleted successfully"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Bid Document Management
@router.post("/{bid_id}/documents")
async def upload_bid_document_route(
    bid_id: str = Path(..., description="Unique identifier of the bid"),
    file: UploadFile = File(..., description="Bid document to upload"),
    document_type: Optional[str] = Query("proposal", description="Type of document (proposal, technical, financial, etc.)")
):
    """Upload a document for a bid."""
    try:
        document = await upload_bid_document(bid_id, file, document_type)
        return JSONResponse(status_code=201, content=document)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{bid_id}/documents")
async def get_bid_documents_route(
    bid_id: str = Path(..., description="Unique identifier of the bid")
):
    """Get all documents for a bid."""
    try:
        documents = await get_bid_documents(bid_id)
        return JSONResponse(status_code=200, content=documents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
