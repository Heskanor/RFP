from fastapi import APIRouter, HTTPException, Body, Query
from typing import List, Optional
from app.services.knowledgehub.web_page_service import process_web_pages, process_single_web_page
from app.config.llm_factory import LLMModel
from pydantic import BaseModel
from app.services.knowledgehub.scarping_service import validate_url

router = APIRouter(prefix="/web-pages", tags=["Web Pages"])

class URL(BaseModel):
    url: str
    title: str

class WebPageProcessRequest(BaseModel):
    urls: List[URL]
    user_id: str
    label_ids: Optional[List[str]] = []
    llm_model: Optional[LLMModel] = LLMModel.GEMINI_2_FLASH
    urls_batch_size: Optional[int] = 3
    max_concurrent_urls: Optional[int] = 2

class SingleWebPageRequest(BaseModel):
    url: str
    user_id: str
    label_ids: Optional[List[str]] = []
    llm_model: Optional[LLMModel] = LLMModel.GEMINI_2_FLASH

class WebPageValidationRequest(BaseModel):
    url: str

@router.post("/process")
async def process_web_pages_route(request: WebPageProcessRequest):
    """
    Process multiple web pages for knowledge hub.
    
    Args:
        request: WebPageProcessRequest containing URLs and processing parameters
        
    Returns:
        Dictionary mapping URLs to created document IDs
    """
    try:
        # Validate URLs
        invalid_urls = [url for url in request.urls if not validate_url(url)]
        if invalid_urls:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid URLs provided: {invalid_urls}"
            )
        
        if not request.urls:
            raise HTTPException(
                status_code=400, 
                detail="No URLs provided"
            )
        
        print(f"Processing {len(request.urls)} web pages for user {request.user_id}")
        
        result = await process_web_pages(
            urls=request.urls,
            llm_model=request.llm_model,
            user_id=request.user_id,
            urls_batch_size=request.urls_batch_size,
            label_ids=request.label_ids,
            max_concurrent_urls=request.max_concurrent_urls
        )
        
        return {
            "success": True,
            "data": result,
            "processed_count": len([doc_id for doc_id in result.values() if doc_id]),
            "failed_count": len([doc_id for doc_id in result.values() if not doc_id])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing web pages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")