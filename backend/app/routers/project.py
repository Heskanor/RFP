from fastapi import APIRouter, HTTPException, Path, Query, Body, File, UploadFile
from fastapi.responses import JSONResponse
from typing import Dict, Optional, List, Literal
import traceback
from app.config.llm_factory import LLMModel
from app.services.project_service import (
    get_projects,
    get_project,
    create_project,
    delete_project,
    update_project,
    get_project_status,
)
from app.services.file.file_service import parse_files
from app.services.ticket_service import generate_project_rfp
from app.models.routers_models import (
    ProjectResponse,
    ProjectDataResponse,

    ExportParams,
)
from app.services.doc_creation import doc_creation_service
from app.services.websocket_manager import ws_manager
from app.models.models import FileStatus, ProjectStatus
import logging

router = APIRouter()


@router.post("/users/{user_id}/projects/{project_id}", response_model=Dict)
async def create_project_route(
    project_id: Optional[str] = Path(
        ..., description="Unique identifier of the project"
    ),
    user_id: Optional[str] = Path(
        ..., description="Unique identifier of the project user"
    ),
    title: Optional[str] = Body(None, description="title of the project"),
    project_files: Optional[List] = Body(
        None, description="files of the project"
    ),
    supporting_files: Optional[List] = Body(
        None, description="files of the supporting documents"
    ),
    provider: Literal["docling", "mistral"] = Body(default="docling", description="Provider to use for parsing"),
    llm_model: LLMModel = Body(default=LLMModel.GPT_4O, description="LLM model to use for parsing"),
):
    """Retrieve data for a specific project."""
    print(f"Creating project: {project_id}, {user_id}, {title} with llm model: {llm_model}")
    print("project_files", project_files)
    print("supporting_files", supporting_files)
    
    await ws_manager.send(channel_id=user_id, event="rfp_creation_progress", data={"project_id": project_id, "status": ProjectStatus.IN_PROGRESS.value})
    project_data = await create_project(
        user_id=user_id,
        project_id=project_id,
        title=title,
        project_files=project_files,
        supporting_files=supporting_files,
    )
    data = {
        project_id: await get_project(project_id)
    }
    await ws_manager.send(channel_id=user_id, event="rfp_creation_progress", data=data)

    if "error" in project_data:
        raise HTTPException(status_code=404, detail=project_data["error"])
    # process files and generate rfp
    print(f"Processing files: {project_data}")
    file_ids = project_data.get("project_files") + project_data.get("supporting_files")

    async def _process_files_and_generate_rfp_task():
        try:
            await parse_files(file_ids, provider)
            data[project_id] = await get_project(project_id)
            await ws_manager.send(channel_id=user_id, event="rfp_creation_progress", data=data)

            await generate_project_rfp(project_id, project_data.get("project_files"), llm_model)
            data[project_id] = await get_project(project_id)      

            await ws_manager.send(channel_id=user_id, event="rfp_creation_progress", data=data, completed=True)
            return {"success": True}
        except Exception as e:
            traceback.print_exc()
            print(f"Error processing files and generating rfp: {e}")
            return {"error": str(e)}

    await _process_files_and_generate_rfp_task()

    return project_data


@router.get("/users/{user_id}/projects", response_model=ProjectResponse)
async def get_projects_route(
    user_id: Optional[str] = None,
    include_content: Optional[bool] = Query(
        False, description="Whether to include document content in response"
    ),
):
    """Retrieve all available projects."""
    projects = await get_projects(user_id)
    # dossiers_hub = await get_dossier_hub(user_id, include_content)

    return {"projects": projects}


@router.get("/projects/{project_id}/status", response_model=Dict)
async def get_project_status_route(project_id: Optional[str] = None):
    """Retrieve the status of a specific project."""
    status = await get_project_status(project_id)
    if status.get("error"):
        raise HTTPException(status_code=404, detail=status["error"])
    return status


@router.get("/projects/{project_id}", response_model=ProjectDataResponse)
async def get_project_route(
    project_id: str = Path(..., description="Unique identifier of the project"),
    include_content: Optional[bool] = Query(
        False, description="Whether to include document content in response"
    ),
):
    """Retrieve data for a specific project."""
    logging.info("Getting project data")
    project_data = await get_project(project_id, include_content)
    if project_data.get("error"):
        raise HTTPException(status_code=404, detail=project_data["error"])
    return project_data


@router.patch("/projects/{project_id}", response_model=Dict)
async def update_project_route(
    project_id: str = Path(..., description="Unique identifier of the project"),
    title: Optional[str] = Body(None, description="title of the project"),
):
    """Update a specific project."""
    project = await update_project(project_id, title)
    if project.get("error"):
        raise HTTPException(status_code=404, detail=project["error"])
    return project

@router.post("/projects/{project_id}/export", response_model=Dict)
async def export_project_route(
    project_id: str = Path(..., description="Unique identifier of the project"),
    export_params: ExportParams = Body(..., description="Export parameters")
):
    """Export a specific project."""
    print(f"Exporting project {project_id} with params: {export_params}")
    file_id = await doc_creation_service.create_doc(project_id, export_params)     
    return {"message": "Project exported successfully", "file_id": file_id}



@router.delete("/projects/{project_id}", response_model=Dict)
async def del_project(
    project_id: str = Path(..., description="Unique identifier of the project"),
):
    """Retrieve data for a specific project."""
    print("Deleting project data")

    project = await delete_project(project_id)
    if project.get("error"):
        raise HTTPException(status_code=404, detail=project["error"])
    return project

