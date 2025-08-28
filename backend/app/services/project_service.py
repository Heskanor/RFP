from app.config.firebase import firebase_manager
from time import time
from app.models.models import Collections, Dossier, Project
from typing import Dict, Any, List
import asyncio
import httpx
from .file.file_service import create_project_files
from fastapi import UploadFile
from uuid import uuid4

import traceback
from app.services.file.file_service import delete_files
from app.services.ticket_service import delete_tickets
from app.services.thread_service import delete_thread


project_collection = Collections.PROJECT.value
dossier_collection = Collections.DOSSIER.value
file_collection = Collections.FILE.value
ticket_collection = Collections.TICKET.value
thread_collection = Collections.THREAD.value


async def get_projects(user_id: str):
    """Get list of all projects under the default workspace"""
    projects_data = await firebase_manager.query_collection(
        project_collection, filters=[("user_id", "==", user_id)], order_by="created_at"
    )

    return [
        {
            "id": data.get("id"),
            "title": data.get("title", ""),
            "status": data.get("status", ""),
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
        }
        for data in projects_data[::-1]
    ]


async def get_dossier_hub(user_id: str, include_content: bool = False):
    dossiers_hub = await firebase_manager.query_collection(
        dossier_collection, filters=[("user_id", "==", user_id)]
    )

    async def get_files(dossier_id: str):
        files = await firebase_manager.query_collection(
            file_collection, filters=[("dossier_id", "==", dossier_id)]
        )
        if not include_content:
            return [
                {k: v for k, v in file.items() if k != "markdown"} for file in files
            ]
        return files

    dossiers_files = [
        {
            "id": dossier.get("id"),
            "title": dossier.get("title"),
            "files": await get_files(dossier.get("id")),
            "is_open": dossier.get("is_open"),
        }
        for dossier in dossiers_hub
    ]
    return dossiers_files


async def create_project(
    user_id: str,
    project_id: str,
    title: str,
    project_files: List,
    supporting_files: List,
):
    
    # Create project document in the database
    await firebase_manager.create_document(
        project_collection,
        Project(id=project_id, title=title, user_id=user_id),
        project_id,
    )
    # Add files to project
    output = {"project_files": [], "supporting_files": []}
    if project_files:
        await create_project_files(user_id, project_id, project_files)
        output["project_files"] = [file.get("id") for file in project_files] 


    if supporting_files:
        await create_project_files(
            user_id, project_id, supporting_files, is_supporting_file=True
        )
        output["supporting_files"] = [file.get("id") for file in supporting_files]


    return output


async def get_project(project_id: str, include_content: bool = False):
    project_data = await firebase_manager.get_document(project_collection, project_id)

    if not project_data:
        return {"error": "Project not found"}
    user_id = project_data.get("user_id")
    # dossiers_hub = await get_dossier_hub(user_id)

    project_files = await firebase_manager.query_collection(
        file_collection,
        filters=[("project_id", "==", project_id), ("is_knowledge_hub", "==", False)],
    )

    if not include_content:
        for file in project_files:
            if "markdown" in file:
                del file["markdown"]
        # for dossier in dossiers_hub:
        #     for file in dossier["files"]:
        #         if "markdown" in file:
        #             del file["markdown"]
    files = [file for file in project_files if not file.get("is_supporting_file") and not file.get("is_proposal_draft")]

    
    supporting_files = [
        file for file in project_files if file.get("is_supporting_file")
    ]
    exported_files = [
        file for file in project_files if file.get("is_proposal_draft")
    ]
    return {
        "id": project_data.get("id"),
        "title": project_data.get("title"),
        "description": project_data.get("description"),
        "status": project_data.get("status"),
        "details": project_data.get("details", {}),
        "files": files,
        "supporting_files": supporting_files,
        # "dossiers_hub": dossiers_hub,
        "exported_files": exported_files,
        "linked_project": [],
    }


async def update_project(project_id: str, title: str):
    try:
        await firebase_manager.update_document(
            project_collection, project_id, {"title": title}
        )
        return {"success": True}
    except Exception as e:
        print(e)
        return {"error": str(e)}


async def delete_project(project_id: str):
    try:
        await delete_files(project_id=project_id)
        print(f"Deleted files for project {project_id}")
        await delete_tickets(project_id=project_id)
        print(f"Deleted tickets for project {project_id}")
        await delete_thread(project_id=project_id)
        print(f"Deleted thread for project {project_id}")
        await firebase_manager.delete_document(project_collection, project_id)
        print(f"Deleted project {project_id}")
        return {"success": True}
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}


async def get_project_status(project_id: str):
    try:
        project_data = await firebase_manager.get_document(
            project_collection, project_id
        )
        return {
            "status": project_data.get("status"),
        }
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}
