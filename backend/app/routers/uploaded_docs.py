from fastapi import APIRouter, HTTPException
from typing import List, Optional
from app.models.models import UploadedDocuments  # your Pydantic or dataclass model for files
from app.config.firebase import firebase_manager
from app.models.models import Collections
from datetime import datetime
from app.services.knowledgehub.uploaded_docs_service import create_uploaded_doc, get_uploaded_doc, update_uploaded_doc, delete_uploaded_doc
router = APIRouter(prefix="/uploaded_files", tags=["Uploaded Files"])

# Collection name
COLLECTION_NAME = Collections.UPLOADED_DOCS

# ------------------------------
# Create a new uploaded file
# ------------------------------
@router.post("/", response_model=UploadedDocuments)
async def create_uploaded_file(file: UploadedDocuments, label_names: Optional[List[str]] = None):
    created_doc = await create_uploaded_doc(file, label_names)
    if not created_doc:
        raise HTTPException(status_code=400, detail="Failed to create uploaded file.")
    return file

# ------------------------------
# Fetch a single uploaded file
# ------------------------------
@router.get("/{doc_id}", response_model=UploadedDocuments)
async def get_uploaded_file(doc_id: str):
    doc = await get_uploaded_doc(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Uploaded file not found.")
    return UploadedDocuments(**doc)

# ------------------------------
# Fetch multiple uploaded files (filter by user_id, label_id or type)
# ------------------------------
@router.get("/", response_model=List[UploadedDocuments])
async def list_uploaded_files(user_id: Optional[str] = None, label_id: Optional[str] = None, file_type: Optional[str] = None):
    filters = []
    if user_id:
        filters.append(("user_id", "==", user_id))
    if label_id:
        filters.append(("labelIds", "array_contains", label_id))
    if file_type:
        filters.append(("type", "==", file_type))

    if filters:
        docs = await firebase_manager.query_collection(COLLECTION_NAME, filters)
    else:
        docs = await firebase_manager.get_documents(COLLECTION_NAME)

    return [UploadedDocuments(**doc) for doc in docs]

# ------------------------------
# Update an uploaded file
# ------------------------------
@router.put("/{document_id}", response_model=UploadedDocuments)
async def update_uploaded_file(document_id: str, document_update: dict):
    updated = await update_uploaded_doc(document_id, document_update)
    if not updated:
        raise HTTPException(status_code=400, detail="Failed to update uploaded file.")
    return document_update

# ------------------------------
# Delete an uploaded file
# ------------------------------
@router.delete("/")
async def delete_uploaded_file(document_ids: List[str]):
    deleted = await delete_uploaded_doc(document_ids)
    if not deleted:
        raise HTTPException(status_code=400, detail="Failed to delete uploaded file.")
    return {"message": "Uploaded file deleted successfully."}
