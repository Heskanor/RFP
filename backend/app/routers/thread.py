from fastapi import APIRouter, HTTPException, Path, Query, Body
from typing import Dict, Optional, List, Any

from app.config.llm_factory import LLMModel
from app.services.thread_service import (
    get_thread_by_ticket_id,
    delete_thread,
    generate_tickets_insights,
    generate_highlights,
    create_project_thread,
    get_project_thread,
    update_project_thread,
    delete_project_thread,
    get_threads_by_project_id,
    stream_project_chat,
)

from app.models.routers_models import (
    ChatRequest,
    ChatMessage,
    MessageRequest,

)


from fastapi.responses import StreamingResponse
import traceback

import logging

router = APIRouter()


@router.post(
    "/projects/{project_id}/tickets/{ticket_id}/thread/generate-answer-stream",
    response_class=StreamingResponse,
)
async def generate_ticket_answer_stream(
    project_id: str = Path(..., description="The id of the project"),
    ticket_id: str = Path(..., description="The id of the ticket"),
    chat_request: ChatRequest = Body(
        ..., description="Chat request containing the user's prompt"
    ),
    filesContext: Optional[List] = Body(None, description="List of file context"),
    is_regenerated: Optional[bool] = Body(
        False, description="Is the answer being regenerated"
    ),
    llm_model: Optional[LLMModel] = Body(
        LLMModel.GPT_4O_MINI, description="LLM model to use"
    ),
):
    """Generate an answer for a specific ticket."""
    try:
       
        return StreamingResponse(
            generate_tickets_insights(
                project_id, ticket_id, chat_request, filesContext, is_regenerated, llm_model
            ),
            media_type="text/x-ndjson",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating ticket answer: {str(e)}"
        )


@router.get("/tickets/{ticket_id}/thread/chat")
async def get_thread_route(
    ticket_id: str = Path(..., description="The id of the ticket"),
):
    """Get the thread for a specific dossier."""
    
    result = await get_thread_by_ticket_id(ticket_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
   

@router.delete("/tickets/{ticket_id}/thread/chat")
async def delete_thread_route(
    ticket_id: str = Path(..., description="The id of the ticket"),
):
    """Delete the thread for a specific dossier."""
    try:
        result = await delete_thread(ticket_id=ticket_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting thread: {str(e)}")


@router.post(
    "/threads/{thread_id}/generate-highlights",
    response_model=ChatMessage,
)
async def generate_highlights_route(
    thread_id: str = Path(
        ..., description="ID of the thread to generate highlights for"
    ),
    message_id: str = Body(
        ..., description="ID of the message to generate highlights for"
    ),
    llm_model: Optional[LLMModel] = Body(
        LLMModel.GPT_4O_MINI, description="LLM model to use"
    ),
):
    """Generate highlights for a specific dossier."""
    response = await generate_highlights(thread_id, message_id, llm_model)
    if "error" in response:
        raise HTTPException(status_code=404, detail=response["error"])
    return response


# -- Project Threads --


@router.post("/projects/{project_id}/threads", response_model=dict)
async def create_thread_route(
    user_id: str = Body(..., description="Unique identifier of the project user"),
    project_id: str = Path(..., description="Unique identifier of the project"),
    is_web_search: Optional[bool] = Body(
        False, description="Whether to use web search"
    ),
    file_ids: Optional[List[str]] = Body(
        [], description="List of file IDs to include in the thread"
    ),
    initial_message: Optional[MessageRequest] = Body(
        None, description="Initial message to include in the thread"
    ),
):
    """Create a new thread."""
    thread_data = await create_project_thread(
        user_id, project_id, is_web_search, file_ids, initial_message
    )
    if thread_data.get("error"):
        raise HTTPException(status_code=400, detail=thread_data["error"])
    return thread_data


@router.get("/threads/{thread_id}", response_model=dict)
async def get_thread_route(
    thread_id: str = Path(..., description="Unique identifier of the thread")
):
    """Retrieve a thread by ID."""
    thread_data = await get_project_thread(thread_id)
    if thread_data.get("error"):
        raise HTTPException(status_code=404, detail=thread_data["error"])
    return thread_data


@router.put("/threads/{thread_id}", response_model=dict)
async def update_thread_route(thread_id: str, updates: dict = Body(...)):
    """Update a thread."""
    thread_data = await update_project_thread(thread_id, updates)
    if thread_data.get("error"):
        raise HTTPException(status_code=400, detail=thread_data["error"])
    return thread_data


@router.delete("/threads/{thread_id}", response_model=dict)
async def delete_thread_route(thread_id: str):
    """Delete a thread by ID."""
    thread_data = await delete_project_thread(thread_id)
    if thread_data.get("error"):
        raise HTTPException(status_code=404, detail=thread_data["error"])
    return thread_data


@router.post("/projects/{project_id}/threads/{thread_id}/stream", response_class=StreamingResponse)
async def stream_thread_route(
    thread_id: str = Path(..., description="Unique identifier of the thread"),
    project_id: str = Path(..., description="Unique identifier of the project"),
    chat_request: ChatRequest = Body(..., description="User prompt"),
    is_web_search: bool = Body(False, description="Whether to use web search"),
    file_ids: List[dict] = Body(
        [], description="List of file IDs to include in the thread"
    ),
    all_kh_files: bool = Body(False, description="Whether to include all knowledge hub files"),
    llm_model: Optional[LLMModel] = Body(
        LLMModel.GPT_4O_MINI, description="LLM model to use"
    ),
    is_regenerated: bool = Body(False, description="Whether to regenerate the thread"),
):
    """Stream messages from a thread."""
    try:
        print("llm_model:", llm_model)
        return StreamingResponse(
            stream_project_chat(
                thread_id, project_id, chat_request, llm_model, is_web_search, file_ids, all_kh_files, is_regenerated
            ),
            media_type="text/x-ndjson",
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/threads", response_model=List)
async def get_threads_by_project_id_route(
    project_id: str = Path(..., description="Unique identifier of the project"),
    limit: int = Query(None, description="Limit the number of threads returned"),
):
    """Retrieve all threads by project ID."""
    try:
        thread_data = await get_threads_by_project_id(project_id, limit)
        return thread_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
