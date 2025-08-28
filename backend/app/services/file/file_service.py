from app.config.firebase import firebase_manager
from fastapi import UploadFile
from typing import List, Dict, Literal, Optional, Union


import httpx
import os


import asyncio
from uuid import uuid4

import traceback
from app.models.models import Collections, File, FileStatus
from app.services.vectorization_service import VectorizationService
from app.services.file.mistral_ocr import ocr_mistral_batch

from app.services.websocket_manager import ws_manager

from .file_processing import process_files, _EMPTY_COLUMN_PREFIX

from typing import Dict, Any
import asyncio
# from .ocr_providers.factory import OCRProviderFactory
from app.models.files_models import BoundingBox, ImageContent, TableContent
import shutil
import tempfile

project_collection = Collections.PROJECT.value
dossier_collection = Collections.DOSSIER.value
file_collection = Collections.FILE.value
file_data_collection = Collections.FILE_DATA.value
ticket_collection = Collections.TICKET.value
thread_collection = Collections.THREAD.value


MAX_CONCURRENT_TASKS = 3  # Limit concurrency
PAGES_PER_DOCUMENT = 2


# async def _create_file(
def _create_file(
    # file: UploadFile,
    file: dict,
    project_id: str,
    user_id: str,
    dossier_id: str = None,
    is_knowledge_hub: bool = False,
    is_supporting_file: bool = False,
):
    # file_id = str(uuid4())
    try:
        # path_segments = (
        #     [user_id, project_id] if not is_knowledge_hub else [user_id]
        # )
        # print(f"Path segments: {path_segments}")
        # file_url = await firebase_manager.upload_file(
        #     file=file, path_segments=path_segments, file_id=file_id
        # )
        file_data = File(
            id=file.get("id"),
            project_id=project_id,
            user_id=user_id,
            dossier_id=dossier_id,

            name=file.get("name"),
            url=file.get("url"),
            is_knowledge_hub=is_knowledge_hub,
            is_supporting_file=is_supporting_file,
            is_used= is_supporting_file == True,
            size=file.get("size")
        )
        # await firebase_manager.create_document(
        #     collection=file_collection,
        #     data=file_data,
        #     document_id=file.get("id"),
        # )
        # return file.get("id")
        return {
            "type": "create",
            "collection": file_collection,
            "document_id": file.get("id"),
            "data": file_data.to_dict()
        }
    except Exception as e:
        print(e)
        return {}



async def create_project_files(
    user_id: str,
    project_id: str,
    # files: List[UploadFile],
    files: List[Dict[str, Any]],
    dossier_id: str = None,
    is_knowledge_hub: bool = False,
    is_supporting_file: bool = False,
):
    try :
        create_tasks = [
                _create_file(
                    file, project_id, user_id, dossier_id, is_knowledge_hub, is_supporting_file
                )
                for file in files
            ]
        await firebase_manager.batch_operation(create_tasks)
        # results = await asyncio.gather(*create_tasks)
        # # Handle results and collect successful uploads
        # successful_files = []

        # for id in results:
        #     if isinstance(id, Exception):
        #         print(f"Project file upload failed: {str(id)}")
        #         continue
        #     successful_files.append(id)

        # return successful_files
        return {"success": True}
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}


async def vectorize_files_batch(files_ids: List[str]):
    vectorization_service = VectorizationService()
    async def _vectorize_file(file: dict):
        
        try:
            print(f"Start vectorizing file name:  {file.get('name')}")
            markdown = file.get("markdown")
            metadata = {
                "file_id": file.get("id", ""),
                "dossier_id": file.get("dossier_id", ""),
                "project_id": file.get("project_id", ""),
                "user_id": file.get("user_id", ""),
            }

            if markdown:
                chunks = vectorization_service.hybrid_chunk_markdown_with_headers(markdown, max_tokens=500)
                await vectorization_service.embed_and_upload(
                    chunks=chunks, metadata=metadata, batch_size=50
                )
        except Exception as e:
            traceback.print_exc()
            print(f"Error vectorizing file {file.get('name')}: {e}")

    files = await firebase_manager.get_documents(file_collection, files_ids)

    print(f"Vectorizing files: {files_ids}")
    
    # Process files in batches of 10
    for batch in [files[i:i+10] for i in range(0, len(files), 10)]:
        await asyncio.gather(*(_vectorize_file(file) for file in batch))
    
    return {"success": True}

async def process_files_docling(file_ids: List[str]):
    """Process files using Docling provider."""
    doc_processing_url = os.getenv("DOC_PROSSING_API_URL")

    async with httpx.AsyncClient(timeout=300) as client:
        try:
            # Fire-and-forget request
            await client.post(f"{doc_processing_url}/magic-rfp/process", json=file_ids)
        except Exception as e:
            print(f"Error processing files with Docling: {e}")
            raise

async def mistral_process_files(file_ids: List[str], channel_id: str = None, data: dict = {}):
    files = await firebase_manager.get_documents(file_collection, list_ids=file_ids)
    operations = []
    for file in files:
        operations.append(
            {
                "type": "update",
                "collection": file_collection,
                "document_id": file.get("id"),      
                "data": {
                    "status": FileStatus.PROCESSING.value,
                    "progress": 0
                }
            }
        )
    await firebase_manager.batch_operation(operations)


    results = await ocr_mistral_batch(files, channel_id, data) 
    operations = []
    for file in results:
        operations.append(
            {
                "type": "update",
                "collection": file_collection,
                "document_id": file.get("id"),      
                "data": file
            }
        )
    await firebase_manager.batch_operation(operations)

    # Vectorize files
    await vectorize_files_batch(file_ids)
    return results

async def parse_files(file_ids: List[str], provider: Literal["docling", "mistral"] = "docling", channel_id: str = None, reprocess_files: bool = False):
    try:
        data = {file_id: {"status": FileStatus.PROCESSING.value, "progress": 0} for file_id in file_ids}
        # print(f"data: {data}", "channel_id:", channel_id)
        if channel_id:
            await ws_manager.send(channel_id=channel_id, event="files_processing_progress", data=data)
        if reprocess_files:
            delete_results = await delete_files_metadata(file_ids)
            print(f"Delete Files Metadata to reprocess files: {file_ids}")
            if "error" in delete_results:
                return {"error": delete_results.get("error")}

        if provider == "docling":
            await process_files_docling(file_ids)
        elif provider == "mistral":
            # await mistral_process_files(file_ids, channel_id, data)
           
            await process_files(
                file_ids,
                channel_id=channel_id,
                data=data
            )
        else:
            raise ValueError(f"Invalid provider: {provider}")
        
        if channel_id:
            await ws_manager.send(channel_id=channel_id, event="files_processing_progress", data=data, completed=True)
        # for i in range(10):
        #     await asyncio.sleep(2)
        #     print(f"progress: {i / 10 * 100}")
        #     data[file_ids[0]]["progress"] = i / 10 * 100
        #     data[file_ids[0]]["status"] = FileStatus.PROCESSING.value
        #     print(f"data: {data}")
        #     if channel_id:
        #         await ws_manager.send(channel_id=channel_id, event="files_processing_progress", data=data)
        # await ws_manager.send(channel_id=channel_id, event="files_processing_progress", data=data, completed=True)
        return {"success": True}
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}
    

async def get_file(file_id: str):
    """
    Get a file
    """
    file = await firebase_manager.get_document(file_collection, file_id)
    if not file:
        return {"error": "File not found"}
    return file


async def get_files_collection(collection: str, id: str):
    """
    Get a file
    """
    collection_id_name = None
    is_knowledge_hub = False
    if collection == "project":
        collection_id_name = "project_id"
    elif collection == "dossier" or collection == "knowledge_hub":
        is_knowledge_hub = True
        collection_id_name = "dossier_id"

    files = await firebase_manager.query_collection(
        file_collection,
        filters=[
            (collection_id_name, "==", id),
            ("is_knowledge_hub", "==", is_knowledge_hub),
        ],
    )
    if not files:
        return {"error": "Files not found"}
    return files


async def get_file_status(files_id: List[str]):
    """
    Get the status of a file
    """

    files = await firebase_manager.get_documents(file_collection, files_id)
    if not files:
        return {"error": "Files not found"}
    return {
        file.get("id"): {
            "status": file.get("status"),
            "progress": file.get("progress"),
        }
        for file in files
    }


async def delete_files(
    file_ids: Optional[List[str]] = None,
    project_id: Optional[str] = None,
    dossier_id: Optional[str] = None,
):
    try:
        vectorization_service = VectorizationService()
        file_ids = file_ids or []

        # Determine filter based on priority
        filters = []
        if project_id:
            filters = [("project_id", "==", project_id)]
        elif dossier_id:
            filters = [("dossier_id", "==", dossier_id)]
        elif file_ids:
            filters = [("id", "in", file_ids)]
        else:
            return {"error": "Must provide project_id, dossier_id, or file_ids."}
        if not filters:
            return {"error": "No filters provided."}
        # Query relevant files
        files = await firebase_manager.query_collection(file_collection, filters=filters)
        if not files:
            return {"success": True, "message": "No files found to delete."}

        # Track IDs for raw data and vector DB
        all_file_ids = [f["id"] for f in files]

        # Prepare deletion operations
        doc_deletions = [{
            "type": "delete",
            "collection": file_collection,
            "document_id": file["id"],
        } for file in files]

        file_data = await firebase_manager.query_collection(
            file_data_collection,
            filters=[("file_id", "in", all_file_ids)]
        )
        data_deletions = [{
            "type": "delete",
            "collection": file_data_collection,
            "document_id": data["id"],
        } for data in file_data]

        # Delete raw storage files
        storage_deletions = []
        for file in files:
            user_id = file.get("user_id")
            project_id = file.get("project_id")
            file_id = file.get("id")
            if file.get("is_knowledge_hub"):
                path = [user_id, file_id]
            else:
                path = [user_id, project_id, file_id]
            storage_deletions.append(firebase_manager.delete_file(path))

        # Execute deletions
        await asyncio.gather(
            firebase_manager.batch_operation(doc_deletions),
            firebase_manager.batch_operation(data_deletions),
            *storage_deletions,
            vectorization_service.delete_data(filters={"file_id": all_file_ids})
        )

        return {"success": True, "deleted_file_ids": all_file_ids}
    
    except Exception as e:
        print("Delete files error:", e)
        return {"error": str(e)}
    
async def delete_files_metadata(file_ids: List[str]):
    try:
        vectorization_service = VectorizationService()

        data_deletions = [{
            "type": "delete",
            "collection": file_data_collection,
            "document_id": id,
        } for id in file_ids]
        
        await asyncio.gather(
            firebase_manager.batch_operation(data_deletions),
            vectorization_service.delete_data(filters={"file_id": file_ids})
        )

        return {"success": True}
    except Exception as e:
        print("Delete files metadata error:", e)
        return {"error": str(e)}

async def update_files(filesData: List[Dict[str, Any]]):
    """
    Update a file
    """
    try:
        operation = []
        for file in filesData:
            operation.append(
                {
                    "type": "update",
                    "collection": file_collection,
                    "document_id": file.get("id"),
                    "data": file.get("data"),
                }   
            )
        await firebase_manager.batch_operation(operation)
        return {"success": True}
    except Exception as e:
        print(e)
        return {"error": str(e)}

def convert_bounding_box_to_highlight(item: Union[ImageContent, TableContent]) -> Dict:
    box = item.get("bounding_boxes", {})
    width = box.get("width") #box.bottom_right_x - box.top_left_x
    height = box.get("height") #box.bottom_right_y - box.top_left_y
    if item.get("type") == "image":
        data = item.get("structured_output",{}).get("chart_data",[])
    else:

        data = item.get("csv_data",[])
        # for row in data:
        #     for key, value in row.items():
        #         if value == _EMPTY_COLUMN_PREFIX:
        #             row[key] = ""
    content = {}
    if item.get("type") == "image":
        content = {
            "image": item.get("image_url")
        }
    else:
        content = {
            "text": item.get("markdown")
        }
    return {
        "id": item.get("id"),
        "structuredData": {
            "type": item.get("type"),
            # "imageUrl": image.image_url,
            "summary": item.get("markdown",""),
            "data": data
        },
        # "content": content,
         "position": {
            "boundingRect": {
                "x1": box.get("top_left_x") ,
                "y1": box.get("top_left_y"),
                "x2": box.get("bottom_right_x"),
                "y2": box.get("bottom_right_y"),
                "width": width,
                "height": height
            },
            "rects": [
                {
                    "x1": box.get("top_left_x") ,
                    "y1": box.get("top_left_y"),
                    "x2": box.get("bottom_right_x"),
                    "y2": box.get("bottom_right_y"),
                    "width": width,
                    "height": height
                }
            ],
            "pageNumber": item.get("page_number")
        }
    }
async def get_file_visuals(file_id: str) -> Dict[str, Any]:
    try:
        # Fetch images
        images = await firebase_manager.query_collection(
            file_data_collection, 
            [("file_id", "==", file_id), ("type", "==", "image")],
            order_by="page_number"
        )

        # Fetch tables
        tables = await firebase_manager.query_collection(
            file_data_collection, 
            [("file_id", "==", file_id), ("type", "==", "table")],
            order_by="page_number"
        )

        result_by_page: Dict[int, Dict[str, Any]] = {}

        for img in images:
            page = img["page_number"]
            result_by_page.setdefault(page, {"highlights": [], "has_table": False})
            if img.get("bounding_boxes"):
                highlight = convert_bounding_box_to_highlight(img)
                result_by_page[page]["highlights"].append(highlight)

        for table in tables:
            page = table["page_number"]
            result_by_page.setdefault(page, {"highlights": [], "has_table": True})
            highlight = convert_bounding_box_to_highlight(table)
            result_by_page[page]["highlights"].append(highlight)

        # Convert dict to list sorted by page number
        response = [
            {"page": page, **data}
            for page, data in sorted(result_by_page.items())
        ]
        return {"pages": response}

    except Exception as e:
       traceback.print_exc()
       return {"error": str(e)}

async def get_file_content(file_id: str, name: str, type: Literal["image", "table"]):
    try:        
        file_data, file_metadata = await asyncio.gather(
            firebase_manager.query_collection(
            file_data_collection, 
            [("file_id", "==", file_id), ("name", "==", name)]
        ), firebase_manager.get_document(file_collection, file_id)
        )

        data = None
        highlights = None
        if type == "image":
            data = file_data[0].get("image_url")
            if file_data[0].get("bounding_boxes"):
                highlights = [convert_bounding_box_to_highlight(file_data[0])]
        elif type == "table":
            data = file_data[0].get("csv_data")
            if file_data[0].get("bounding_boxes"):
                highlights = [convert_bounding_box_to_highlight(file_data[0])]

        return {"data": data, 
        "highlights": highlights,
        "file_id": file_id, 
        "name": name, 
        "type": type, 
        "page_number": file_data[0].get("page_number"),
        "file_id": file_id,
        "file_name": file_metadata.get("name"),
        "file_url": file_metadata.get("url"),
        }
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}