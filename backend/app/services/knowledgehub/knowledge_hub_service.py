from app.models.models import KnowledgeItem, UploadedFileContent, typeMapper
from app.config.firebase import firebase_manager
from app.models.models import Collections
from typing import List, Optional, Tuple
from app.services.file.file_service import delete_files
from app.services.vectorization_service import VectorizationService
from app.services.explanation import (
    _generate_highlight_snippets,
    generate_highlight_objects,
    get_pdf_text,
)
from collections import defaultdict
from app.services.file.curated_qa_extraction import CuratedQAExtractor
# from algoliasearch.search.client import SearchClient
import asyncio
import traceback

COLLECTION_NAME = Collections.KNOWLEDGE_HUB
FILE_COLLECTION = Collections.FILE


async def create_knowledge_items(items: List[KnowledgeItem]):
    try:    
        curated_qa_extractor = CuratedQAExtractor(user_id=items[0].user_id if items else None)
        operations = []
        curated_qas_to_vectorize = []
        for item in items:
            operations.append({
                "type": "create",
                "collection": COLLECTION_NAME,
                "document_id": item.id,
                "data": item.to_dict()
            })
            if item.type == "curated_qa":
                curated_qas_to_vectorize.append(item.to_dict())
        
        await firebase_manager.batch_operation(operations)
        if curated_qas_to_vectorize:
            await curated_qa_extractor._vectorize_curated_qas(curated_qas_to_vectorize)
        return {
            "success": True,
            "message": "Knowledge items created successfully",
        }
    except Exception as e:
        traceback.print_exc()
        return {
            "error": str(e),
            "message": "Failed to create knowledge items " + str(e)
        }
    


async def get_knowledge_items(
         user_id: str = None, 
         type: str = None, 
         subtype: str = None, 
         label_id: str = None, 
         more_filters: List[Tuple[str, str, str]] = [],
         expand_labels: bool = False):
    filters = []
    if user_id:
        filters.append(["user_id", "==", user_id])

    if type:
        filters.append(["type", "==", type])
    if subtype:
        filters.append(["subtype", "==", subtype])
    if label_id:
        filters.append(["labelIds", "array_contains", label_id])
    if more_filters:
        filters.extend(more_filters)

    try :       
        items = await firebase_manager.query_collection(COLLECTION_NAME, filters, order_by="updated_at", ascending=False)
     
        # items_content = await get_kh_files(items)
        return {
            "success": True,
            "message": "Knowledge items retrieved successfully",
            "data": items
        }
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to retrieve knowledge items: " + str(e)
        }

async def get_knowledge_items_by_text_filter(user_id: str, text: str):
    try:    
        vectorization_service = VectorizationService()
        docs = await vectorization_service.query_context(query=text, filters={"user_id": [user_id]}, aggregation=False)
        # result = await _search_markdown(query=text, user_id=user_id)
        results = [
            {
                "id": doc.metadata["file_id"],
                "pages": doc.metadata["page_numbers"],
                "content": doc.metadata["text"]
            } for doc in docs
        ]
        
        # Group results by "id"
        grouped_results = defaultdict(list) 

        for result in results:
            grouped_results[result["id"]].append(result["content"])

        # Concatenate contents for each grouped result
        concatenated_results = []

        for file_id, contents in grouped_results.items():
            # concatenated_content = " ".join(contents)  # Concatenate the content from different pages
            concatenated_results.append({
                "id": file_id,
                "pages": [f"page_{i}" for i in range(1, len(contents) + 1)],  # Keep track of pages (example)
                # "content": concatenated_content
            })
     
        files = await firebase_manager.get_documents(FILE_COLLECTION, [result.get("id") for result in concatenated_results])
        files_with_pages = []
        for result in concatenated_results:
            file = next((file for file in files if file.get("id") == result.get("id")), None)
            if file:
                file['pages'] = result.get("pages")
                file['content'] = result.get("content")
                pages = [int(page.split("_")[-1]) for page in file['pages']]
                highlight_objects = []
                for page in pages:
                    highlight_objects.extend(await generate_highlight_objects(
                            file["url"], [text], page, num_words=1
                        ))
                file['highlights'] = highlight_objects

                del file["markdown"]
                files_with_pages.append(file)

        return {
            "success": True,
            "message": "Knowledge items retrieved successfully",
            "data": files_with_pages
        }
    except Exception as e:
        traceback.print_exc()
        return {
            "error": str(e),
            "message": "Failed to retrieve knowledge items: " + str(e)
        }

async def get_knowledge_item(item_id: str):
    try:
        item = await firebase_manager.get_document(COLLECTION_NAME, item_id)
        return {
            "success": True,
            "message": "Knowledge item retrieved successfully",
            "data": item    
        }
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to retrieve knowledge item"
        }

async def get_knowledge_hub_stats(user_id: str):
    try:

        items = await get_knowledge_items(user_id=user_id)
        types_stats = [
            {
                "type": type,
                "count": 0
            }
            for type in typeMapper.keys()
        ]
        for item in items.get("data", []):
            type = item.get("subtype") if item.get("subtype") else item.get("type")
            for stat in types_stats:
                if stat.get("type") == type:
                    stat["count"] += 1
                    break

        return {
            "success": True,
            "message": "Knowledge hub stats retrieved successfully",
            "data": types_stats
        }
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to retrieve knowledge hub stats" + str(e)
        }

async def update_knowledge_item(item_id: str, item: dict):
    try:
        await firebase_manager.update_document(COLLECTION_NAME, item_id, item)
        return {
            "success": True,
            "message": "Knowledge item updated successfully",
        }
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to update knowledge item"
        }

async def delete_knowledge_items(item_ids: Optional[List[str]] = [], content_ids: Optional[List[str]] = None):
    try:
        vectorization_service = VectorizationService()

        # Itentify KH items with file id and delete them
        if content_ids:            
            items = await get_knowledge_items(more_filters=[["content.id", "in", content_ids]])
            print(f"KH Items Linked to files: {len(items.get('data', []))}")
            item_ids += [item.get("id") for item in items.get("data", [])]
        
        operations = [
            {
                "type": "delete",
                "collection": COLLECTION_NAME,
                "document_id": item_id
            }
            for item_id in item_ids
        ]
        tasks = [firebase_manager.batch_operation(operations)]
        if content_ids:
            tasks.append(delete_files(file_ids=content_ids))

        # Delete vectorized kh items without files 
        if item_ids:
            tasks.append(vectorization_service.delete_data(filters={"kh_item_id": item_ids}))
            
        await asyncio.gather(*tasks)
       
        return {
            "success": True,
            "message": "Knowledge items deleted successfully",
        }
        
    except Exception as e:
        traceback.print_exc()
        return {
            "error": str(e),
            "message": "Failed to delete knowledge items" + str(e)
        }