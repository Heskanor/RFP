from app.config.firebase import firebase_manager
from app.services.file.file_service import create_project_files

from app.models.models import Collections, Dossier
from app.services.file.file_service import delete_files
from typing import Dict, Any, List, Union, Optional
import re
from time import time
import traceback


project_collection = Collections.PROJECT.value
dossier_collection = Collections.DOSSIER.value
file_collection = Collections.FILE.value
ticket_collection = Collections.TICKET.value
thread_collection = Collections.THREAD.value

async def get_user_dossiers(user_id: str, type: Optional[str] = None, subtype: Optional[str] = None, include_files: bool = True, include_content: bool = False):
    filters = [("user_id", "==", user_id)]  
    if type:
        filters.append(("type", "==", type))
    if subtype:
        filters.append(("subtype", "==", subtype))

 
    dossiers_hub = await firebase_manager.query_collection(
        dossier_collection, filters=filters
    )
    if type == "curated_qa":
        qa_files = [{
            "id": qa.get("id"),
            "dossier_id": dossier.get("id"),
            "question": qa.get("question"),
            "answer": qa.get("answer"),
            "type": dossier.get("type"),
            "labels": dossier.get("labels", []),
            "created_at": dossier.get("created_at"),
            "updated_at": dossier.get("updated_at"),
            "is_open": dossier.get("is_open"),
        } for dossier in dossiers_hub for qa in dossier.get("metadata", {}).get("qa_files", [])]
        return qa_files

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
            "type": dossier.get("type"),
            "labels": dossier.get("labels"),
            "metadata": dossier.get("metadata", {}),
            "files": await get_files(dossier.get("id")) if include_files else [],
            "is_open": dossier.get("is_open"),
        }
        for dossier in dossiers_hub
    ]
    return dossiers_files
    
async def get_dossier(dossier_id: str, include_content: bool = False):
    """Get metadata for a specific dossier including files and magic column values

    Args:
        project_id: ID of the project
        dossier_id: ID of the dossier to fetch
        include_content: Whether to include file content in response

    Returns:
        Dict containing dossier metadata or error message
    """
    try:
        # Get project data using existing function
        dossier = await firebase_manager.get_document(dossier_collection, dossier_id)
        files = await firebase_manager.query_collection(
            file_collection, filters=[("dossier_id", "==", dossier_id)]
        )

        if not dossier:
            return {"error": "Dossier not found"}

        if not include_content:
            dossier["files"] = [
                {k: v for k, v in file.items() if k != "markdown"} for file in files
            ]
        else:
            for file in files:
                if isinstance(file.get("markdown"), dict):
                    markdown = ""
                    for i in range(len(file["markdown"])):
                        markdown += file["markdown"].get(f"page_{i+1}")
                    file["markdown"] = markdown
            dossier["files"] = files

        return {
            "dossier_id": dossier_id,
            "title": dossier.get("title", ""),
            "files": dossier.get("files", []),
        }

    except Exception as e:
        return {"error": str(e)}


async def create_dossier(user_id, dossier_id, files, type, labels, subtype):
    """Create a new dossier"""
    try:
        print("creating dossier", user_id, dossier_id, type, labels, subtype)
        if type == "curated_qa":
            dossier = Dossier(id=dossier_id, user_id=user_id, type=type, labels=labels, subtype=subtype, metadata={"qa_files": files})
            await firebase_manager.create_document(dossier_collection, dossier, dossier_id)
        elif type == "uploaded_documents":
            dossier = Dossier(id=dossier_id, user_id=user_id, type=type, labels=labels, subtype=subtype)
            await firebase_manager.create_document(dossier_collection, dossier, dossier_id)
            await create_project_files(user_id=user_id, project_id=None, dossier_id=dossier_id, files=files, is_knowledge_hub=True)
        # elif type == "web_search":
        #     await create_project_files(user_id=user_id, project_id=None, dossier_id=dossier_id, files=files, is_knowledge_hub=True)
        # elif type == "custom_connectors":
        #     await create_project_files(user_id=user_id, project_id=None, dossier_id=dossier_id, files=files, is_knowledge_hub=True)
        return {"success": True}
    
    except Exception as e:
        return {"error": str(e)}


async def delete_dossier(dossier_ids: List[str]):
    """Delete a dossier"""
    try:
        dossiers_files = await firebase_manager.query_collection(
            file_collection, filters=[("dossier_id", "in", dossier_ids)]
        )
        await delete_files(file_ids=[file["id"] for file in dossiers_files])
        operations = []
        for dossier_id in dossier_ids:
            print("deleting dossier", dossier_id)
            operations.append(
                {
                    "type": "delete",
                    "collection": dossier_collection,
                    "document_id": dossier_id,
                }
            )
        await firebase_manager.batch_operation(operations)
        return {"success": True}
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}

async def delete_files_from_dossier(dossier_id: str, file_ids: List[str]):
    """Delete files from a dossier"""
    try:
        files = await firebase_manager.query_collection(
            file_collection, filters=[("dossier_id", "==", dossier_id)]
        )
        dossier_file_ids = [file["id"] for file in files if file["id"] in file_ids]

        if dossier_file_ids == file_ids:
            await delete_dossier(dossier_ids=[dossier_id])
        else:
            await delete_files(file_ids=dossier_file_ids)
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}



async def update_dossier(dossier_id: str, data: dict):
    """Update a dossier"""
    try:
        await firebase_manager.update_document(dossier_collection, dossier_id, data)
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}
