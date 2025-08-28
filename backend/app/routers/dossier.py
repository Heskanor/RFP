from fastapi import APIRouter, HTTPException, Path, Query, Body, File, UploadFile

from fastapi.responses import JSONResponse
from typing import Dict, Optional, List, Union, Any
from app.services.dossier_service import (
    get_user_dossiers,
    get_dossier,
    create_dossier,
    delete_dossier,
    update_dossier,
    delete_files_from_dossier,
)

from app.models.routers_models import DossierMetadataResponse
import traceback

router = APIRouter()

@router.get("/users/{user_id}/dossiers")
async def get_dossiers_route(
    user_id: str = Path(..., description="ID of the user to fetch dossiers for"),
    type: Optional[str] = Query(
        None, description="Type of dossiers to fetch"
    ),
    subtype: Optional[str] = Query(
        None, description="Subtype of dossiers to fetch"
    ),
    include_files: Optional[bool] = Query(
        True, description="Whether to include files in the response"
    ),
):
    """Retrieve all dossiers for a user"""
    result = await get_user_dossiers(user_id, type, subtype, include_files)
    return result

@router.get(
    "/dossiers/{dossier_id}",
    response_model=DossierMetadataResponse,
)
async def get_dossier_metadata_route(
    dossier_id: str = Path(..., description="ID of the dossier to fetch"),
    include_content: Optional[bool] = Query(
        False, description="Whether to include file content in response"
    ),
):
    """Retrieve metadata for a specific dossier including files and magic column values"""
    result = await get_dossier(dossier_id, include_content)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.post("/users/{user_id}/dossiers/{dossier_id}")
async def create_dossier_route(
    user_id: str = Path(..., description="ID of the user to create the dossier for"),
    dossier_id: str = Path(..., description="ID of the dossier to create"),
    files: Optional[List[UploadFile]] = File(
        None, description="Files to upload"
    ),
    type: Optional[str] = Body(
        None, description="Type of dossier to create"
    ),
    labels: Optional[List[str]] = Body(
        None, description="Labels to add to the dossier"
    ),
    subtype: Optional[str] = Body(
        None, description="Subtype of dossier to create"
    )
):
    """Create a new dossier"""
    result = await create_dossier(user_id, dossier_id, files, type, labels, subtype)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
    # print("creating dossier", user_id, dossier_id, files, type, labels, subtype)
    # return {"success": True}

@router.post("/users/{user_id}/dossiers/{dossier_id}/from-json")
async def create_dossier_from_json_route(
    user_id: str = Path(..., description="ID of the user to create the dossier for"),
    dossier_id: str = Path(..., description="ID of the dossier to create"),
    files: Optional[List[Dict[str, Any]]] = Body(
        [], description="Files to upload"
    ),
    type: Optional[str] = Body(
        None, description="Type of dossier to create"
    ),
    labels: Optional[List[str]] = Body(
        None, description="Labels to add to the dossier"
    ),
    subtype: Optional[str] = Body(
        None, description="Subtype of dossier to create"
    )
):
    """Create a new dossier"""
    result = await create_dossier(user_id, dossier_id, files, type, labels, subtype)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
@router.delete("/dossiers")
async def delete_dossier_route(
    dossiers_ids: List[str] = Body(..., description="List of dossier IDs to delete")
):
    """Delete a dossier"""
    print("deleting dossiers", dossiers_ids)
    result = await delete_dossier(dossiers_ids)
    return result

@router.delete("/dossiers/{dossier_id}/files")
async def delete_file_route(
    dossier_id: str = Path(..., description="ID of the dossier to delete the file from"),
    file_ids: List[str] = Body(..., description="List of file IDs to delete")
):
    """Delete a file"""
    result = await delete_files_from_dossier(dossier_id, file_ids)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.patch("/dossiers/{dossier_id}")
async def update_dossier_router(
    dossier_id: str = Path(..., description="Id of the dossier to update"),
    data: dict = Body(..., description="Data to update"),
):
    """
    Update a dossier
    """
    results = await update_dossier(dossier_id, data)
    if "error" in results:
        raise HTTPException(status_code=500, detail=results.get("error"))
    return JSONResponse(status_code=200, content=results)


@router.get("/dossiers/{dossier_id}/files/status")
async def file_status(
    dossier_id: str = Path(..., description="Unique identifier of the dossier")
):
    """
    Get the status of a file
    """
    try:
        status = await get_file_status(dossier_id)
        return JSONResponse(status_code=200, content=status)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during file status retrieval: {str(e)}",
        )
