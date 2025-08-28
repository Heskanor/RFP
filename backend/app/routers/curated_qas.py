from fastapi import APIRouter, HTTPException
from typing import List, Optional
from app.models.models import CuratedQA  # your dataclass models
from app.services.knowledgehub.curated_qa import create_curated_qa, get_curated_qa, update_curated_qa, delete_curated_qa, list_curated_qas

router = APIRouter(prefix="/curated_qas", tags=["Curated QAs"])

# ------------------------------
# Create a new Curated QA
# ------------------------------
@router.post("/", response_model=CuratedQA)
async def create_curated_qa_route(qa: CuratedQA, label_names: Optional[List[str]] = None):
    created_doc = await create_curated_qa(qa, label_names)
    if not created_doc:
        raise HTTPException(status_code=400, detail="Failed to create Curated QA.")
    return qa

# ------------------------------
# Fetch a single Curated QA
# ------------------------------
@router.get("/{qa_id}", response_model=CuratedQA)
async def get_curated_qa_route(qa_id: str):
    doc = await get_curated_qa(qa_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Curated QA not found.")
    return CuratedQA(**doc)

# ------------------------------
# Fetch multiple Curated QAs (filter by user_id or labelId optional)
# ------------------------------
@router.get("/", response_model=List[CuratedQA])
async def list_curated_qas_route(user_id: Optional[str] = None, label_id: Optional[str] = None, label_name: Optional[str] = None):
    docs = await list_curated_qas(user_id, label_id, label_name)
    if not docs:
        raise HTTPException(status_code=404, detail="No Curated QAs found.")
    return docs

# ------------------------------
# Update a Curated QA
# ------------------------------
@router.patch("/{qa_id}", response_model=CuratedQA)
async def update_curated_qa_route(qa_id: str, qa_update: dict):
    updated = await update_curated_qa(qa_id, qa_update)
    if not updated:
        raise HTTPException(status_code=400, detail="Failed to update Curated QA.")
    return qa_update

# ------------------------------
# Delete a Curated QA
# ------------------------------
@router.delete("/")
async def delete_curated_qa_route(qa_ids: List[str]):
    deleted = await delete_curated_qa(qa_ids)
    if not deleted:
        raise HTTPException(status_code=400, detail="Failed to delete Curated QA.")
    return {"message": "Curated QA deleted successfully."}

