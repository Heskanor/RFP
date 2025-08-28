import firebase_admin
from firebase_admin import credentials, firestore_async, storage
from google.cloud.firestore_v1 import AsyncClient
from google.cloud.firestore_v1.async_collection import AsyncCollectionReference
from google.cloud.firestore_v1.base_query import FieldFilter
from fastapi import UploadFile

from typing import List, Dict, Any, Optional, Union
from app.models.models import BaseModel

import asyncio
import os

from uuid import uuid4
from datetime import datetime
import dotenv
import json

dotenv.load_dotenv()

firebase_service_account_key = (
    os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_DEV")
    if os.getenv("ENVIRONMENT") == "local"
    else os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
)
storage_bucket = (
    os.getenv("STORAGE_BUCKET_DEV")
    if os.getenv("ENVIRONMENT") == "local"
    else os.getenv("STORAGE_BUCKET")
)




class AsyncFirebaseDataManager:
    def __init__(
        self,
        service_account_path: str = firebase_service_account_key,
        storage_bucket: str = storage_bucket,
        firestore_db: str = os.getenv("FIRESTORE_DB")
    ):
        """Initialize Firebase Admin SDK and Firestore client asynchronously."""
       # You must deserialize the JSON string if it's stored as an env variable
        if isinstance(service_account_path, str):
            service_account_path = json.loads(service_account_path)

        app_name = firestore_db if firestore_db else None
        # Initialize the app only if it hasn't been initialized yet
        app = None
        try:
            app = firebase_admin.get_app(app_name)
        except ValueError:
            if not firebase_admin._apps:
                cred = credentials.Certificate(service_account_path)
                app = firebase_admin.initialize_app(
                    cred, 
                    {"storageBucket": storage_bucket}
                )
          
                
        self.db: AsyncClient = firestore_async.client(app= app, database_id=firestore_db)
        self.bucket = storage.bucket(app= app)
        self._collection_cache = {}

    async def _get_collection(self, collection_name: str) -> AsyncCollectionReference:
        """Get a collection reference with caching."""
        if collection_name not in self._collection_cache:
            self._collection_cache[collection_name] = self.db.collection(
                collection_name
            )
        return self._collection_cache[collection_name]

    async def _firebase_to_dict(self, data: Any) -> Optional[Dict]:
        """Convert Firebase data to a dictionary format."""
        if data is None:
            return None
        if isinstance(data, dict):
            return data
        try:
            return dict(data)
        except (ValueError, TypeError):
            return (
                {str(i): item for i, item in enumerate(data)}
                if isinstance(data, (list, tuple))
                else None
            )

    async def create_document(
        self,
        collection: str,
        data: Union[BaseModel, Dict[str, Any]],
        document_id: Optional[str] = None,
    ) -> str:
        """Generic method to create a document in any collection."""
        doc_id = document_id or str(uuid4())

        if isinstance(data, BaseModel):
            doc_data = data.to_dict()
        else:
            doc_data = data

        if "id" not in doc_data:
            doc_data["id"] = doc_id

        if "created_at" not in doc_data:
            current_time = int(datetime.now().timestamp())
            doc_data.update({"created_at": current_time, "updated_at": current_time})

        collection_ref = await self._get_collection(collection)
        await collection_ref.document(doc_id).set(doc_data)
        return doc_id

    async def get_document(self, collection: str, document_id: str) -> Optional[Dict]:
        """Generic method to get a document from any collection."""
        collection_ref = await self._get_collection(collection)
        doc = await collection_ref.document(document_id).get()
        return await self._firebase_to_dict(doc.to_dict()) if doc.exists else None
    
    @staticmethod
    def chunk_list(lst, chunk_size):
        for i in range(0, len(lst), chunk_size):
            yield lst[i:i + chunk_size]

    async def get_documents(
        self,
        collection: str,
        list_ids: List[str] = None,
        order_by: str = None,
        ascending: bool = True,
    ) -> List[Dict]:
        """Generic method to get multiple documents from any collection, supporting batching and optional ordering."""

        collection_ref = await self._get_collection(collection)
        results = []

        if list_ids:
            for id_chunk in self.chunk_list(list_ids, 30):
                query = collection_ref.where(filter=FieldFilter("id", "in", id_chunk))
                docs = query.stream()
                async for doc in docs:
                    doc_data = doc.to_dict()
                    results.append(doc_data)
        else:
            query = collection_ref
            if order_by:
                direction = "ASCENDING" if ascending else "DESCENDING"
                query = query.order_by(order_by, direction=direction)
            docs = query.stream()
            async for doc in docs:
                doc_data = doc.to_dict()
                results.append(doc_data)

        if order_by and list_ids:
            results.sort(key=lambda x: x.get(order_by), reverse=not ascending)

        return results

    async def update_document(
        self, collection: str, document_id: str, updates: Dict[str, Any]
    ) -> str:
        """Generic method to update a document in any collection."""
        updates["updated_at"] = int(datetime.now().timestamp())
        collection_ref = await self._get_collection(collection)
        await collection_ref.document(document_id).update(updates)
        return document_id

    async def delete_document(self, collection: str, document_id: str) -> str:
        """Generic method to delete a document from any collection."""
        collection_ref = await self._get_collection(collection)
        await collection_ref.document(document_id).delete()
        return document_id

    async def query_collection(
        self,
        collection: str,
        filters: List[tuple] = None,
        order_by: str = None,
        ascending: bool = True,
        limit: int = None,
    ) -> List[Dict]:
        """
        Generic method to query any collection with filters.
        Supports batching for 'in' operator when the value list exceeds 30 items.
        """
        collection_ref = await self._get_collection(collection)
        base_filters = []
        batched_filters = []

        if filters:
            for f in filters:
                if f[1] == "in" and isinstance(f[2], list) and len(f[2]) > 30:
                    # Split the long 'in' filter into batches of 30
                    batched_values = [f[2][i:i+30] for i in range(0, len(f[2]), 30)]
                    batched_filters.append((f[0], f[1], batched_values))
                else:
                    base_filters.append(f)

        # If no batching is needed, run a single query
        if not batched_filters:
            return await self._run_query(collection_ref, base_filters, order_by, ascending, limit)

        # If batching is needed, run multiple queries and merge results
        all_results = []
        for field, op, value_batches in batched_filters:
            for value_batch in value_batches:
                current_filters = base_filters + [(field, op, value_batch)]
                results = await self._run_query(collection_ref, current_filters, order_by, ascending, limit)
                all_results.extend(results)

        # Optionally remove duplicates based on a unique key like 'id'
        unique_results = {item['id']: item for item in all_results}.values()
        return list(unique_results)


    async def _run_query(
        self,
        collection_ref,
        filters: List[tuple],
        order_by: str,
        ascending: bool,
        limit: int,
    ) -> List[Dict]:
        query = collection_ref

        for field, operator, value in filters:
            query = query.where(filter=FieldFilter(field, operator, value))

        if order_by:
            direction = "ASCENDING" if ascending else "DESCENDING"
            query = query.order_by(order_by, direction=direction)

        if limit:
            query = query.limit(limit)

        docs = query.stream()
        results = []
        
        try:
            docs = query.stream()
            results = []
            async for doc in docs:
                doc_data = await self._firebase_to_dict(doc.to_dict())
                results.append(doc_data)
            return results
        except Exception as e:
            print(f"Firestore query failed: {filters}, {order_by}, {limit}, error={e}")
            raise
            

        # return results
    
    async def batch_operation(self, operations: List[Dict[str, Any]]) -> None:
        """
        Perform batch operations on multiple documents.

        :param operations: List of operations, each containing:
            - type: 'create', 'update', or 'delete'
            - collection: collection name
            - document_id: document ID
            - data: document data (for create/update)
        """
        batch = self.db.batch()

        for op in operations:
            collection_ref = await self._get_collection(op["collection"])
            doc_ref = collection_ref.document(op["document_id"])

            if op["type"] == "create":
                batch.set(doc_ref, op["data"])
            elif op["type"] == "update":
                batch.update(doc_ref, op["data"])
            elif op["type"] == "delete":
                batch.delete(doc_ref)

        await batch.commit()

    async def upload_file(
        self,
        file: UploadFile,
        path_segments: List[str],
        file_id: str = None,
        retry_count: int = 3,
        delay: float = 1.0,
        file_source: str = None,  #  path to file on disk, if available
        file_type: str = "pdf",
        content_type: str = None,
    ) -> str:
        """
        Generic file upload method.

        :param file: FastAPI UploadFile object (used if file_source is None)
        :param path_segments: List of path segments (e.g., [user_id, project_id, dossier_id])
        :param file_source: Optional local file path to upload directly from disk
        """
        file_id = file_id or str(uuid4())
        destination_path = "/".join([*path_segments, f"{file_id}.{file_type}"])
        print(f"Uploading file to {destination_path} storage")

        blob = self.bucket.blob(destination_path)
        blob.content_type = content_type if content_type else file.content_type if file and file.content_type else "application/pdf"

        for attempt in range(retry_count):
            try:
                if file_source:
                    await asyncio.to_thread(blob.upload_from_filename, file_source)
                else:
                    await asyncio.to_thread(blob.upload_from_file, file.file, rewind=True)

                await asyncio.to_thread(blob.make_public)
                return blob.public_url

            except Exception as e:
                if attempt == retry_count - 1:
                    raise
                await asyncio.sleep(delay)
                delay *= 2

    async def delete_file(self, path_segments: List[str]) -> None:
        """Generic file deletion method."""
        destination_path = "/".join(path_segments)
        destination_path += ".pdf"

        blob = self.bucket.blob(destination_path)

        if blob.exists():
            blob.delete()
        else:
            print(f"File {destination_path} does not exist")


firebase_manager = AsyncFirebaseDataManager()
