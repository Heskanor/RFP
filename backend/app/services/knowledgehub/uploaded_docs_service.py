from app.models.models import UploadedDocuments
from app.config.firebase import firebase_manager
from app.models.models import Collections
from typing import List, Optional
from app.services.knowledgehub.curated_qa import get_or_create_labels

COLLECTION_NAME = Collections.UPLOADED_DOCS

async def create_uploaded_doc(uploaded_doc: UploadedDocuments, label_names: Optional[List[str]] = None):
    if label_names:
        uploaded_doc.labelIds = await get_or_create_labels(label_names, uploaded_doc.user_id)
    return await firebase_manager.create_document(COLLECTION_NAME, uploaded_doc.to_dict())

async def get_uploaded_doc(uploaded_doc_id: str):
    return await firebase_manager.get_document(COLLECTION_NAME, uploaded_doc_id)

async def list_uploaded_docs(user_id: Optional[str] = None, label_id: Optional[str] = None, file_type: Optional[str] = None):
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

async def update_uploaded_doc(uploaded_doc_id: str, uploaded_doc: dict):
    return await firebase_manager.update_document(COLLECTION_NAME, uploaded_doc_id, uploaded_doc)

async def delete_uploaded_doc(document_ids: List[str]):
    operations = [{
        "id": document_id,
        "method": "delete"
    } for document_id in document_ids]
    return await firebase_manager.batch_operation(operations)

