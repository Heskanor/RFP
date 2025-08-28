from fastapi import APIRouter, HTTPException, Path, Query, Body, File, UploadFile
from typing import Dict, Optional, List, Any, Literal
from app.services.file.file_service import (
    create_project_files,
    parse_files,
    get_file,
    get_files_collection,
    delete_files,
    get_file_status,
    update_files,
    vectorize_files_batch,
    get_file_visuals,
    get_file_content,


)
from app.services.knowledgehub.knowledge_hub_service import delete_knowledge_items, get_knowledge_items
from app.models.models import Collections
from fastapi.responses import JSONResponse
from app.services.file.curated_qa_extraction import extract_curated_qa
from app.config.llm_factory import LLMModel

collection_mapper = {
    "project": Collections.PROJECT,
    "dossier": Collections.DOSSIER,
    "file": Collections.FILE,
    "ticket": Collections.TICKET,
    "thread": Collections.THREAD,
    "knowledge_hub": Collections.KNOWLEDGE_HUB,
}
router = APIRouter(prefix="/files", tags=["files"])


@router.get("/{file_id}")
async def get_file_router(
    file_id: str = Path(..., description="Unique identifier of the file")
):
    """
    Get a file
    """
    file = await get_file(file_id)
    if "error" in file:
        raise HTTPException(status_code=404, detail=file.get("error"))
    return JSONResponse(status_code=200, content=file)


@router.get("")
async def get_files_router(
    collection: str = Query(..., description="Collection name"),
    id: str = Query(..., description="Id of the document"),
):
    """
    Get a file
    """
    files = await get_files_collection(collection, id)
    if "error" in files:
        raise HTTPException(status_code=404, detail=files.get("error"))
    return JSONResponse(status_code=200, content=files)


@router.post("/upload")
async def upload_file(
    user_id: str = Query(..., description="User id"),
    # files: List[UploadFile] = File(..., description="Files to upload"),
    collection: str = Query(..., description="Collection name"),
    id: str = Query(..., description="Id of the document"),
    is_supporting_file: Optional[bool] = Query(False, description="Is supporting file"),
    files: List[Dict[str, Any]] = Body(..., description="Files to upload"),

):
    """
    Upload a file to a collection
    """
    print(f"Uploading file to collection: {collection}, id: {id}")
    if collection == "project":
        project_id = id
        dossier_id = None
        is_knowledge_hub = False
        is_supporting_file = is_supporting_file
    else:
        project_id = None
        dossier_id = id
        is_knowledge_hub = True if collection == "knowledge_hub" else False
        is_supporting_file = is_supporting_file

    print(
        f"user_id: {user_id}, project_id: {project_id}, dossier_id: {dossier_id}, is_knowledge_hub: {is_knowledge_hub}, is_supporting_file: {is_supporting_file}"
    )
   

    results = await create_project_files(
        user_id=user_id,
        project_id=project_id,
        files=files,
        dossier_id=dossier_id,
        is_knowledge_hub=is_knowledge_hub,
        is_supporting_file=is_supporting_file,
    )

 
    
    if "error" in results:
        raise HTTPException(status_code=500, detail=results.get("error"))
    # return results.get("successful_files", [])
    return results

@router.post("/process")
async def process_files_route(
    file_ids: List[str] = Body(..., description="List of file ids to process"),
    provider: Literal["docling", "mistral"] = Body(..., description="Provider to use for parsing"),
    channel_id: Optional[str] = Body(None, description="Channel id for progress updates"),
    analyze_image: Optional[bool] = Body(True, description="Whether to analyze images in the documents"),
    reprocess_files: Optional[bool] = Body(False, description="Whether to reprocess the files"),
):
    """
    Process files using the specified OCR provider
    """
    if not file_ids:
        raise HTTPException(status_code=400, detail="File ids are required")
    

    results = await parse_files(file_ids, provider, channel_id, reprocess_files)
    if "error" in results:
        raise HTTPException(status_code=500, detail=results.get("error"))
    return results

@router.post("/curated_qa")
async def extract_curated_qa_route(
    file_ids: List[str] = Body(..., description="List of file ids to extract curated qa"),
    label_ids: Optional[List[str]] = Body(None, description="List of label ids to add to the curated qa"),
    provider: Literal["docling", "mistral"] = Body("mistral", description="Provider to use for parsing"),
    user_id: Optional[str] = Body(None, description="User id for progress updates"),
    # channel_id: Optional[str] = Body(None, description="Channel id for progress updates"),
    llm_model: Optional[LLMModel] = Body(LLMModel.GEMINI_2_FLASH, description="LLM model to use for parsing"),
    re_extract: Optional[bool] = Body(False, description="Whether to re-extract the curated qa"),
    files_batch_size: Optional[int] = Body(3, description="Number of files to process in each batch"),
    max_concurrent_files: Optional[int] = Body(2, description="Maximum number of files to process concurrently"),
):
    """
    Extract curated qa from files with progress tracking
    """
    if not file_ids:
        raise HTTPException(status_code=400, detail="File ids are required")
    if not user_id:
        raise HTTPException(status_code=400, detail="User id is required")
    
    try:
        print(f"Extracting curated qa from files: {file_ids}")
        if re_extract:
            data = await get_knowledge_items(user_id=user_id, type="curated_qa")
            if "error" in data:
                raise HTTPException(status_code=500, detail=data.get("error"))
            items = [item.get("id") for item in data.get("data", []) if item.get("content", {}).get("file_id") in file_ids]
            await delete_knowledge_items(items)
            print(f"Deleted {len(items)} curated qa items")

        results = await extract_curated_qa(
            file_ids=file_ids, 
            user_id=user_id, 
            # channel_id=channel_id,
            llm_model=llm_model, 
            label_ids=label_ids or [],
            files_batch_size=files_batch_size,
            max_concurrent_files=max_concurrent_files
        )
        return results
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting curated Q&As: {str(e)}")


@router.post("/vectorize")
async def vectorize_files_route(
    file_ids: List[str] = Body(..., description="List of file ids to vectorize"),
):
    """
    Vectorize files
    """ 
    if not file_ids:
        raise HTTPException(status_code=400, detail="File ids are required")
    results = await vectorize_files_batch(file_ids)
    if "error" in results:
        raise HTTPException(status_code=500, detail=results.get("error"))
    return results

@router.post("/status")
async def file_status(
    file_ids: List[str] = Body(default=[], description="Unique identifier of the file")
):
    """
    Get the status of a file
    """

    try:

        status = await get_file_status(file_ids)

        if "error" in status:
            raise HTTPException(status_code=404, detail=status.get("error"))

        return JSONResponse(status_code=200, content=status)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during file status retrieval: {str(e)}",
        )


@router.patch("")
async def update_file_router(
    filesData: List[Dict[str, Any]] = Body(..., description="List of files to update with their data"),
):
    """
    Update a file
    """
    results = await update_files(filesData)
    if "error" in results:
        raise HTTPException(status_code=500, detail=results.get("error"))
    return JSONResponse(status_code=200, content=results)


@router.delete("")
async def del_files(
    files_ids: List[str] = Body(..., description="Ids of the files to delete"),
):
    """
    Delete files from Firebase DB
    """

    results = await delete_files(file_ids=files_ids)
    if "error" in results:
        raise HTTPException(status_code=500, detail=results.get("error"))

    return JSONResponse(
        status_code=200, content={"message": "Files deleted", "files": results}
    )

@router.get("/{file_id}/visuals")
async def get_file_visuals_route(
    file_id: str = Path(..., description="Unique identifier of the file")
):
    """
    Get the visuals of a file
    """
    results = await get_file_visuals(file_id)
    if "error" in results:
        raise HTTPException(status_code=500, detail=results.get("error"))
    return JSONResponse(status_code=200, content=results.get("pages"))

@router.get("/{file_id}/content")
async def get_file_visual_url_route(
    file_id: str = Path(..., description="Unique identifier of the file"),
    name: str = Query(..., description="Name of the image or table document"),
    type: Literal["image", "table"] = Query(..., description="Type of the document")
):
    """
    Get the URL for a specific visual (image or table) from a file
    """
    result = await get_file_content(file_id, name, type)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result.get("error"))
    return JSONResponse(status_code=200, content=result)



@router.post("/ticket/parse")
async def load_files_to_ticket(
    files: List[UploadFile] = File(..., description="List of files to upload"),
):
    """
    Load files to a ticket
    """

    print(f"Loading files to ticket")
    results = await parse_files(files=files)
    if "error" in results:
        raise HTTPException(status_code=500, detail=results.get("error"))
    return JSONResponse(status_code=200, content=results)
