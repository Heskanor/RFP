from fastapi import APIRouter, HTTPException
from typing import List, Optional
from app.models.models import Label
from app.models.models import Collections

from app.services.knowledgehub.labels_service import create_label, get_label, list_labels, update_label, delete_label

router = APIRouter(prefix="/labels", tags=["Labels"])

COLLECTION_NAME = Collections.LABELS

# ------------------------------
# Create a new label
# ------------------------------
@router.post("", response_model=Label)
async def create_label_route(label: Label):
    # Check if label already exists
 
    created_doc = await create_label(label)
    if not created_doc:
        raise HTTPException(status_code=400, detail="Failed to create label.")
    
    return label

# ------------------------------
# Fetch a single label
# ------------------------------
@router.get("/{label_id}", response_model=Label)
async def get_label_route(label_id: str):
    doc = await get_label(label_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Label not found.")
    return Label(**doc)

# ------------------------------
# List labels (filter by user_id or parentLabelId)
# ------------------------------
@router.get("", response_model=List[Label])
async def list_labels_route(user_id: Optional[str] = None, parentLabelId: Optional[str] = None):
    docs = await list_labels(user_id, parentLabelId)
    if "error" in docs:
        raise HTTPException(status_code=404, detail=docs["message"])
    return docs.get("data", [])

# ------------------------------
# Update a label
# ------------------------------
@router.put("/{label_id}", response_model=Label)
async def update_label_route(label_id: str, label_update: dict):
    updated = await update_label(label_id, label_update)
    if not updated:
        raise HTTPException(status_code=400, detail="Failed to update label.")
    return label_update

# ------------------------------
# Delete a label
# ------------------------------
@router.delete("")
async def delete_label_route(label_ids: List[str]):
    print(f"Deleting labels: {label_ids}")
    deleted = await delete_label(label_ids)
    if "error" in deleted:
        raise HTTPException(status_code=400, detail=deleted["error"])
    return {"message": "Label deleted successfully."}
