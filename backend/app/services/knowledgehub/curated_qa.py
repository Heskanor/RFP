from app.models.models import CuratedQA  # your dataclass models
from app.config.firebase import firebase_manager
from uuid import uuid4
from datetime import datetime
from typing import List, Optional
from app.models.models import Collections

label_collection = Collections.LABELS

# Collection name
COLLECTION_NAME = Collections.CURATED_QA

async def get_or_create_labels(label_names: List[str], user_id: str) -> List[str]:
    """
    Given a list of label names, returns a list of labelIds.
    Creates the label if it does not exist.
    """
    label_ids = []
    for name in label_names:
        # Query by name
        existing = await firebase_manager.query_collection("labels", [("name", "==", name), ("user_id", "==", user_id)])
        
        if existing:
            label_ids.append(existing[0]["id"])
        else:
            # Create the new label
            label_id = str(uuid4())
            label_data = {
                "id": label_id,
                "name": name,
                "user_id": user_id,
                "created_at": int(datetime.now().timestamp()),
                "updated_at": int(datetime.now().timestamp()),
            }
            await firebase_manager.create_document(label_collection, label_data)
            label_ids.append(label_id)
    
    return label_ids


async def create_curated_qa(curated_qa: CuratedQA, label_names: Optional[List[str]] = None):
    """Create a new curated QA"""
    if label_names:
        curated_qa.labelIds = await get_or_create_labels(label_names, curated_qa.user_id)

    created_doc = await firebase_manager.create_document(COLLECTION_NAME, curated_qa.to_dict())
    return created_doc

async def get_curated_qa(curated_qa_id: str):
    """Get a curated QA by ID"""
    return await firebase_manager.get_document(COLLECTION_NAME, curated_qa_id)

async def update_curated_qa(curated_qa_id: str, curated_qa: dict):
    """Update a curated QA"""
    
    return await firebase_manager.update_document(COLLECTION_NAME, curated_qa_id, curated_qa)


async def list_curated_qas(user_id: str = None, label_id: str = None, label_name: str = None):
    """List curated QAs"""
    filters = []
    if user_id:
        filters.append(("user_id", "==", user_id))
    if label_id:
        filters.append(("labelIds", "array_contains", label_id))
    # if label_name:
    #     filters.append(("labelIds", "array_contains", label_name))
    docs = await firebase_manager.query_collection(COLLECTION_NAME, filters=filters)
    return [CuratedQA(**doc) for doc in docs]

async def delete_curated_qa(curated_qa_ids: List[str]):
    """Delete a curated QA"""
    operations = [{
        "id": curated_qa_id,
        "method": "delete"
    } for curated_qa_id in curated_qa_ids]

    return await firebase_manager.batch_operation(operations)
