from fastapi import APIRouter, HTTPException, Path, Query, Body
from fastapi import WebSocket
from typing import Dict, Optional, List, Any
from app.services.ticket_service import (
    get_tickets_data,
    create_ticket,
    generate_ticket_answer,
    save_ticket_answer,
    delete_tickets,
    update_ticket,
    generate_project_rfp,
    generate_text_highlight,
    generate_tickets_answer
)
from app.services.explanation import (
    generate_highlight_objects,
    _generate_highlight_snippets,
    get_pdf_text,
)
from app.config.llm_factory import LLMModel

# from app.services.dossier_chat import _generate_highlight_snippets

from app.config.firebase import firebase_manager
from app.models.models import Collections, Ticket
import traceback

file_collection = Collections.FILE.value
dossier_collection = Collections.DOSSIER.value
project_collection = Collections.PROJECT.value
router = APIRouter()



@router.get("/tickets/{ticket_id}")
async def get_ticket_route(
    ticket_id: str = Path(..., description="Unique identifier of the ticket"),
):
    """Retrieve a specific ticket by ID."""
    try:
        ticket = await firebase_manager.get_document(
            Collections.TICKET.value, ticket_id
        )
        return ticket
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving ticket: {str(e)}"
        )
    
@router.post("/tickets")
async def create_ticket_route(
    ticket: Ticket = Body(..., description="Ticket to create"),
):
    """Create a new ticket."""
    result = await create_ticket(ticket)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result

@router.patch("/tickets/{ticket_id}")
async def update_ticket_route(
    ticket_id: str = Path(..., description="Unique identifier of the ticket"),
    ticket: Dict[str, Any] = Body(..., description="Ticket to update"),
):
    """Update a ticket."""
    result = await update_ticket(ticket_id, ticket)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result

@router.delete("/tickets")
async def delete_ticket_route(  
    tickets_ids: List[str] = Body(..., description="List of ticket IDs to delete"),
):
    """Delete a ticket."""
    result = await delete_tickets( ticket_ids=tickets_ids)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result

@router.post("/projects/{project_id}/rfp-tickets")
async def extract_rfp_tickets_route(
    project_id: str = Path(..., description="Unique identifier of the project"),
    rfp_file_id: Optional[list[str]] = Body(None, description="File ID to process"),
    llm_model: Optional[LLMModel] = Body(
        LLMModel.GPT_4O_MINI, description="LLM model to use"
    ),
):
    """Extract tickets (requirements and questions) from RFP markdown document."""
    result = await generate_project_rfp(project_id, rfp_file_id, llm_model)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result


@router.get("/projects/{project_id}/rfp-tickets", response_model=Dict[str, Any])
async def get_rfp_tickets_route(
    project_id: str = Path(..., description="Unique identifier of the project"),
):
    """Retrieve RFP tickets data for a specific dossier."""
    try:
        # Fetch the dossier data to get associated tickets
        tickets_data = await get_tickets_data(project_id)
        return tickets_data
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving RFP tickets: {str(e)}"
        )


@router.post("/tickets/{ticket_id}/generate-answer")
async def generate_ticket_answer_route(
    ticket_id: str = Path(..., description="Unique identifier of the ticket"),
    user_id: Optional[str] = Query(
        None, description="Unique identifier of the user"
    ),
    custom_instructions: Optional[str] = Body(
        None, description="Custom instructions for the answer"
    ),
    filesContext: Optional[List] = Body([], description="List of file context"),
    context: Optional[str] = Query(
        None, description="Additional context for the answer"
    ),
    llm_model: Optional[LLMModel] = Body(
        LLMModel.GPT_4O_MINI, description="LLM model to use"
    )
):
    """Generate an answer for a specific ticket."""

    try:

        answer, references = await generate_ticket_answer(
            ticket_id, user_id, context, filesContext, custom_instructions, llm_model
        )

        # answer  = """To implement a user feedback mechanism for capturing user feedback on incorrect extractions, it is essential to design an intuitive interface that allows users to easily highlight and correct specific parts of the extracted data. This mechanism should include features such as a simple selection tool that enables users to click on the incorrect extraction and provide their input on what the correct information should be. Additionally, a comment box can be included for users to elaborate on their feedback, ensuring that the context of the correction is clear. p_1

        # Furthermore, the feedback collected should be systematically stored and analyzed to identify common issues and trends in the extraction process. This data can be invaluable for refining the extraction algorithms and improving overall accuracy. Regular updates based on user feedback will not only enhance the system's performance but also foster user trust and engagement, as they see their input leading to tangible improvements. p_2
        #         """
        # references =  {'p_1':{'sources': [{'file_id': '674546bc-ae91-4244-ba7b-38c1a9faad53', 'url': 'https://storage.googleapis.com/magic-rfp-app-dev.firebasestorage.app/8a024ab0-85d4-4168-b521-31786215451d/d4561aaa-bbd2-41bb-af47-e4c3ac9db353/674546bc-ae91-4244-ba7b-38c1a9faad53.pdf', 'pages': ['page_1'], 'text': 'To implement a user feedback mechanism for capturing user feedback on incorrect extractions, it is essential to design an intuitive interface that allows users to easily highlight and correct specific parts of the extracted data.'}],
        #                 'highlights': []},
        #                 'p_2': {'sources': [{'file_id': '674546bc-ae91-4244-ba7b-38c1a9faad53', 'url': 'https://storage.googleapis.com/magic-rfp-app-dev.firebasestorage.app/8a024ab0-85d4-4168-b521-31786215451d/d4561aaa-bbd2-41bb-af47-e4c3ac9db353/674546bc-ae91-4244-ba7b-38c1a9faad53.pdf', 'pages': ['page_1'], 'text': 'Furthermore, the system should log all feedback submissions for analysis, allowing for continuous improvement of the extraction algorithms.'}], 'highlights': []}}

        return {"markdown": answer, "references": references}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating ticket answer: {str(e)}"
        )

@router.post("/projects/{project_id}/generate-answers")
async def generate_project_ticket_answers_route(
    project_id: str = Path(..., description="Project identifier"),
    user_id: Optional[str] = Query(None, description="User ID"),
    context: Optional[str] = Query("", description="Global context"),
    custom_instructions: Optional[str] = Body(None),
    filesContext: Optional[List] = Body([]),
    llm_model: Optional[LLMModel] = Body(LLMModel.GPT_4O_MINI),
):
    """Generate answers for all tickets in a project."""
    try:
        # from app.services.websocket_manager import ws_manager
        # import asyncio
        # print(f"Generating answers for project {project_id} with user {user_id}")
        # for i in range(10):
        #     await ws_manager.send(project_id, "tickets_answers_generation_progress", (i/10)*100)
        #     await asyncio.sleep(5)

        # await ws_manager.send(project_id, "tickets_answers_generation_progress", 100, completed=True)
        results = await generate_tickets_answer(
            user_id, project_id, context, filesContext, custom_instructions, llm_model
        )
        return {"answers": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tickets/{ticket_id}/highlight-text/{paragraph_id}")
async def generate_text_highlight_route(
    ticket_id: str = Path(..., description="Unique identifier of the ticket"),
    paragraph_id: str = Path(..., description="Paragraph to highlight"),
    llm_model: Optional[LLMModel] = Body(
        LLMModel.GPT_4O_MINI, description="LLM model to use"
    ),
):
    """Generate text highlight for a specific ticket."""

    print("Generating text highlight for ticket", ticket_id, paragraph_id)
    results = await generate_text_highlight(ticket_id, paragraph_id, llm_model)
    if "error" in results:
        raise HTTPException(status_code=500, detail=results.get("error"))
    return results


@router.post("/tickets/{ticket_id}/save-answer")
async def save_ticket_answer_route(
    ticket_id: str = Path(..., description="Unique identifier of the ticket"),
    answer: Dict[str, Any] = Body(..., description="Answer to the ticket"),
):
    """Save the answer for a specific ticket."""
    try:

        result = await save_ticket_answer(ticket_id, answer)

        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error saving ticket answer: {str(e)}"
        )


@router.post("/tickets/{ticket_id}/generate-highlights")
async def generate_tickets_highlights(
    ticket_id: str = Path(..., description="Ticket ID"),
    llm_model: Optional[LLMModel] = Body(
        LLMModel.GPT_4O_MINI, description="LLM model to use"
    )
):
    """Generate highlights for a specific ticket."""
    try:

        ticket = await firebase_manager.get_document(
            Collections.TICKET.value, ticket_id
        )
       
        page = ticket["reference"].get("page")
        file_id = ticket["reference"].get("file_id")
        file = await firebase_manager.get_document(file_collection, file_id)
        if page:
            # Handle both single page string and list of pages
            pages = [page] if isinstance(page, str) else page
            # Get first page number for highlighting
            pages_num = [int(page.split("_")[-1]) for page in pages]
            file_content = get_pdf_text(file["url"], pages)
        else:
            pages_num = None
            file_content = get_pdf_text(file["url"])

        files_content = f"""File ID: {file_id}\nContent:\n```{file_content}```"""
        answer = (
            f"title: {ticket.get('title')}\n"
            + f"description: {ticket.get('description')}\n"
        )

        # print("file_content", file_content)
        # print("answer", answer)
        highlight_data, highlights_usage = await _generate_highlight_snippets(
            files_content, answer, llm_model
        )

        print("highlight_data", highlight_data)

        complete_file_highlights = []
        file_highlight_data = next(
            (h for h in highlight_data if h.file_id == file["id"]), None
        )

        highlight_objects = []
        if file_highlight_data and file_highlight_data.snippets:
            highlight_objects = await generate_highlight_objects(
                file["url"], file_highlight_data.snippets, pages_num
            )
        
        complete_file_highlights.append(
            {
                "id": file["id"],
                "name": file["name"],
                "url": file["url"],
                "highlights": highlight_objects,
            }
        )
        updated_ticket = {
            "reference": {
                **ticket.get("reference"),
                "highlights": complete_file_highlights,
            }
        }
        await update_ticket(ticket_id, updated_ticket)

        return updated_ticket.get("reference").get("highlights")

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Error generating ticket highlights: {str(e)}"
        )


@router.delete("/projects/{project_id}/rfp-tickets")
async def delete_rfp_tickets_route(
    project_id: str = Path(..., description="Unique identifier of the project"),
    ticket_ids: Optional[List[str]] = Body(
        [], description="List of ticket IDs to delete"
    ),
):
    """Delete all RFP tickets for a specific project."""
    try:
        await delete_tickets(project_id, ticket_ids)
        return {"success": True}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting RFP tickets: {str(e)}"
        )
