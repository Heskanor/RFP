from fastapi import APIRouter, HTTPException, Body
from typing import List, Optional, Literal, Any, Dict
from pydantic import BaseModel
import json, traceback
from app.services.search_service import query_index, format_search_results_with_file_metadata
# from app.models.models import SearchResponse

# Request model for search
class SearchRequest(BaseModel):
    query: str
    search_type: Literal["lexical", "semantic", "hybrid"] = "lexical"
    filters: Optional[Dict[str, Any]] = {}
    order_by: Optional[dict] = None
    limit: Optional[int] = 10
    offset: Optional[int] = 0

# Response models for search results
class SearchResult(BaseModel):
    id: str
    metadata: Dict[str, Any]
    score: float
    values: List[float] = []
    
    class Config:
        extra = "allow"  # Allow extra fields

router = APIRouter(prefix="/users/{user_id}/search", tags=["Search"])

# ------------------------------
# Search endpoint for different index types
# ------------------------------
@router.post("/{index_name}", response_model=List[SearchResult])
async def search_index(
    user_id: str,
    index_name: str, 
    request: SearchRequest = Body(...)
):
    
    if not index_name:
        raise HTTPException(status_code=400, detail="Index name is required")
    
    if not request.query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    # Validate index name
    valid_indexes = ["documents", "images", "tables", "curated_qas"]
    if index_name not in valid_indexes:
        raise HTTPException(status_code=400, detail=f"Invalid index name. Must be one of: {valid_indexes}")
    
    # Use the filters directly from the request
    filters_dict = request.filters or {}
    
    try:
        # Use unified search function for all index types
        search_results = await query_index(
            user_id,
            index_name, 
            request.query, 
            filters_dict, 
            request.limit, 
            request.offset
        )
        
        # Format results with appropriate content type
        content_type = index_name[:-1] if index_name.endswith('s') else index_name
        formatted_results = await format_search_results_with_file_metadata(search_results, content_type, request.order_by)
        # with open('dump.json', 'r') as f:
        #     formatted_results = json.load(f)
        
        # formatted_results = formatted_results.get(index_name, [])
        return formatted_results
        
    except Exception as e:
        traceback.print_exc()
        print(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search operation failed: {str(e)}")
    

# @router.post("/{user_id}", response_model=List)
# async def search_index(
#                        user_id: str,
#                        query: str,
#                        search_type: Literal["lexical", "semantic", "hybrid"] = "semantic",
#                        search_mode: Literal["all", "document", "image", "table", "curated_document", "web_page"] = "all",
#                     #    filters: Optional[List[str]] = [], 
#                        order_by: Optional[dict] = None, 
#                        limit: Optional[int] = 5, 
#                        offset: Optional[int] = 0):

    
#     if not query:
#         raise HTTPException(status_code=400, detail="Query is required")
    
#     search_results = await query_index(
#         user_id=user_id, 
#         query=query, 
#         search_type=search_type, 
#         search_mode=search_mode, 
#         limit=limit, 
#         offset=offset
#     )
#     return search_results