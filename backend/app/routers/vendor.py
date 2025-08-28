from fastapi import APIRouter, HTTPException, Path, Query, Body
from fastapi.responses import JSONResponse
from typing import Dict, Optional, List
import traceback

from app.services.vendor_service import (
    get_vendors,
    get_vendor,
    create_vendor,
    update_vendor,
    delete_vendor,
)

router = APIRouter(prefix="/vendors", tags=["vendors"])

@router.get("")
async def get_vendors_route(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    limit: int = Query(50, description="Number of vendors to return"),
    offset: int = Query(0, description="Offset for pagination")
):
    """Get all vendors, optionally filtered by project."""
    try:
        vendors = await get_vendors(project_id=project_id, limit=limit, offset=offset)
        return JSONResponse(status_code=200, content=vendors)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{vendor_id}")
async def get_vendor_route(
    vendor_id: str = Path(..., description="Unique identifier of the vendor")
):
    """Get vendor details by ID."""
    try:
        vendor = await get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        return JSONResponse(status_code=200, content=vendor)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
async def create_vendor_route(
    vendor_data: Dict = Body(..., description="Vendor information")
):
    """Create a new vendor."""
    try:
        vendor = await create_vendor(vendor_data)
        return JSONResponse(status_code=201, content=vendor)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{vendor_id}")
async def update_vendor_route(
    vendor_id: str = Path(..., description="Unique identifier of the vendor"),
    vendor_data: Dict = Body(..., description="Updated vendor information")
):
    """Update vendor information."""
    try:
        vendor = await update_vendor(vendor_id, vendor_data)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        return JSONResponse(status_code=200, content=vendor)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{vendor_id}")
async def delete_vendor_route(
    vendor_id: str = Path(..., description="Unique identifier of the vendor")
):
    """Delete a vendor."""
    try:
        result = await delete_vendor(vendor_id)
        if not result:
            raise HTTPException(status_code=404, detail="Vendor not found")
        return JSONResponse(status_code=200, content={"message": "Vendor deleted successfully"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
