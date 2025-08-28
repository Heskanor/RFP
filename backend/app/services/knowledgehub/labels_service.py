from app.config.firebase import firebase_manager
from app.models.models import Collections, Label
import uuid
from datetime import datetime
from typing import List, Optional
from app.services.file.file_service import delete_files
COLLECTION_NAME = Collections.LABELS
KH_COLLECTION = Collections.KNOWLEDGE_HUB

async def get_or_create_labels(label_names: List[str], user_id: str) -> List[str]:
    """
    Given a list of label names, returns a list of label IDs.
    Creates missing labels.
    """
    label_ids = []
    for name in label_names:
        existing = await firebase_manager.query_collection(COLLECTION_NAME, [("name", "==", name), ("user_id", "==", user_id)])
        if existing:
            label_ids.append(existing[0]["id"])
        else:
            label_id = str(uuid.uuid4())
            label_data = {
                "id": label_id,
                "name": name,
                "user_id": user_id,
                "created_at": int(datetime.now().timestamp()),
                "updated_at": int(datetime.now().timestamp()),
            }
            await firebase_manager.create_document("labels", label_data)
            label_ids.append(label_id)
    return label_ids

async def find_label_by_name(name: str, user_id: str) -> Optional[dict]:
    """
    Find a label by its name for a specific user.
    """
    labels = await firebase_manager.query_collection("labels", [("name", "==", name), ("user_id", "==", user_id)])
    return labels[0] if labels else None

async def create_label(label: Label):
    """
    Create a new label.
    """
    # existing = await find_label_by_name(label.name, label.user_id)
    # if existing:
    #     return {"error": "Label with this name already exists."}
    
    if not label.id:
        label.id = str(uuid.uuid4())

    created_doc = await firebase_manager.create_document(COLLECTION_NAME, label.to_dict(), label.id)
    return created_doc

async def get_label(label_id: str):
    """
    Get a label by its ID.
    """
    return await firebase_manager.get_document(COLLECTION_NAME, label_id)


async def list_labels(user_id: Optional[str] = None, parentLabelId: Optional[str] = None):
    try:
        filters = []
        if user_id:
            filters.append(("user_id", "==", user_id))
        if parentLabelId:
            filters.append(("parentLabelId", "==", parentLabelId))
        
        if filters:
            docs = await firebase_manager.query_collection(COLLECTION_NAME, filters)
        else:
            docs = await firebase_manager.get_documents(COLLECTION_NAME)

        return {
            "success": True,
            "message": "Labels fetched successfully",
            "data": [Label(**doc) for doc in docs]
        }
    except Exception as e:
        print(f"Error listing labels: {e}")
        return {
            "success": False,
            "message": "Error listing labels" + str(e),

        }

async def update_label(label_id: str, label_update: dict):
    """
    Update a label.
    """
    return await firebase_manager.update_document(COLLECTION_NAME, label_id, label_update)

async def delete_label(labels_ids: List[str]):
    """
    Delete a label.
    """
    try:
        operations = [{ 
            "collection": COLLECTION_NAME,
            "document_id": label_id,
            "type": "delete"
        } for label_id in labels_ids]
        await firebase_manager.batch_operation(operations)

        # Delete the label from the knowledge hub Items
        for label_id in labels_ids:
            kh_items = await firebase_manager.query_collection(KH_COLLECTION, [("labelIds", "array_contains", label_id)])
            print(f"Kh items: {len(kh_items)} linked to label {label_id}")
            operations = []
            for item in kh_items:
                
                operations.append({
                    "collection": KH_COLLECTION,
                    "document_id": item.get("id"),
                    "type": "update",
                    "data": {
                        "labelIds": [label_id for label_id in item.get("labelIds") if label_id not in labels_ids]
                    }
                })
              
                    
            await firebase_manager.batch_operation(operations)
                

        return {
            "success": True,
            "message": "Labels deleted successfully"
        }
    except Exception as e:
        print(f"Error deleting labels: {e}")
        return {
            "success": False,
            "error": str(e)
        }