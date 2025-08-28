# Python standard library imports
import asyncio
import json
import os
import random
import traceback
from time import time
from typing import Any, Dict, List, Tuple, Optional, Union
from uuid import uuid4

# Third party imports
from fastapi import HTTPException
from pydantic import BaseModel

# Local application imports
from app.config.firebase import firebase_manager
from app.config.llm_factory import LLMFactory, LLMModel
from app.models.models import Collections, ProjectStatus, Ticket
from app.models.tickets_models import Context, Tickets
from app.services.explanation import (
    _generate_highlight_snippets,
    generate_highlight_objects,
    get_pdf_text,
)
from app.services.thread_service import _knowledge_hub_context
from app.services.vectorization_service import VectorizationService
from .llm_agents import (
    search_and_answer_from_files,
    generate_answer_for_rfp_tickets,
    generate_context_for_rfp_tickets,
)
from .websocket_manager import ws_manager
from app.services.file.file_processing import enrich_files_with_markdown

knowledge_hub_collection = Collections.KNOWLEDGE_HUB.value
project_collection = Collections.PROJECT.value

thread_collection = Collections.THREAD.value
file_collection = Collections.FILE.value
ticket_collection = Collections.TICKET.value
user_collection = Collections.USER.value


class ChatRequest(BaseModel):
    prompt: str
    timestamp: Optional[int] = None


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

system_prompt = (
    "You are an expert at analysing RFP documents. Your expertise will be solicited to power an RFP submission application.\n"
    "This application is destined to help vendors craft responses to RFPs. To do that, it would aid them in breaking them down into tickets and help provide answers to them."
)

user_prompt_summary = (
    "Extract the summary of the RFP which will be used "
    "by another analyst as initial context to extract requirements, outstanding questions, and issues that must be answered by the vendor submitting a proposal."
)

user_prompt_tickets = (
    "Extract all key requirements, questions to answer, and deliverables from the RFP document **page** provided below. Focus on actionable items only.\n"
    "These questions, requirements, and deliverables will be used in an RFP submission platform. The user will need to provide an answer to each item, so precision is critical.\n"
    "\n"
    "Rules:\n"
    "- Use ONLY the content of the RFP page provided. **DO NOT use or refer to the RFP summary** or any external context.\n"
    "- If the RFP issuer asks for a capability, requirement, or deliverable, extract it as a ticket.\n"
    "- If there's a question, extract it as a ticket that must be answered.\n"
    "- If a requirement is broad, break it down into smaller, actionable items when relevant.\n"
    "- If the RFP page has **no actionable items**, such as a cover page or table of contents, return an empty array `[]`. DO NOT invent or guess any tickets.\n"
    "\n"
    "Also extract, if present:\n"
    "- `timeline`: any deadlines or important dates\n"
    "- `stakeholders`: names or roles of involved people or decision makers\n"
    "- `section`: a section or heading reference from the RFP page (e.g., '2.1.3', or the section heading)\n"
)
user_prompt_merge = (
    "Given these documents that contain tickets (key requirements, questions to answer, and deliverables, potential issues) extracted from an RFP document, ."
    "merge them into a single comprehensive document that the total set of tickets as well as other properties such as timeline, stakeholders, etc."
)


async def openai_struct(model, messages, output_schema):
    response = await LLMFactory.get_llm_with_structured_output(model, output_schema).ainvoke(messages)
    return response


async def extract_details(files: list, model: LLMModel = LLMModel.GPT_4O_MINI) -> Context:
    """
    Extract the summary of the RFP which will be used as initial context to extract requirements, outstanding questions, and issues that must be answered by the vendor submitting a proposal.
    """
    # Create initial summary
    prompt = user_prompt_summary + f"\n\n RFP documents:\n"
    markdown_pages = ""
    for file in files:
        for page_number in range(max(len(file.get("markdown", {})), 3)):

            markdown_pages += (
                file.get("markdown").get(f"page_{str(page_number+1)}", "") + "\n"
            )

        prompt += f"\n\n File {file.get('name')}: {markdown_pages}"
    # print(prompt)
    messages_summary = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": prompt,
        },
    ]

    summary = await openai_struct(model, messages_summary, Context)
    summary = summary.model_dump()

    summary["timeline"] = summary.get("timeline", [])
    summary["stakeholders"] = summary.get("stakeholders", [])
    return summary


async def extract_rfp_tickets(files: list, summary: Context, model: LLMModel = LLMModel.GPT_4O_MINI) -> Tickets:
    """
    Extract key requirements and questions from RFP markdown using OpenAI structured outputs
    """

    # Create tasks for parallel processing
    async def process_page(
        pages: Union[List[int], str], content: str, summary: dict, file_id: str
    ) -> Tickets:
        messages_tickets = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": user_prompt_tickets
                + f"\n\n RFP summary: {json.dumps(summary)}"
                # + f"\n\n RFP document page key: {pages}"
                + f"\n\n RFP document chunk: {content}",
            },
        ]
        tickets = await openai_struct(model, messages_tickets, Tickets)
        tickets = tickets.model_dump()

        # print("-"*100)
        # print("File content", content[:500])
        # print("Pages", pages)
        # Manually embed page and file information in each ticket
        for ticket in tickets.get("tickets", []):

            # print("Ticket", ticket.get("title"))
            ticket["reference"]["page"] = pages
            ticket["reference"]["file_id"] = file_id

        # print("-"*100)
        return tickets
    
     # Split dosument by Section
    vectorization_service = VectorizationService()
    # chunks = []
    tasks = []
    for file in files:
        chunks = vectorization_service.hybrid_chunk_markdown_with_pages(file["markdown"])
        tasks.extend([process_page(chunk.page_numbers, chunk.content, summary, file.get("id")) for chunk in chunks])

    tickets = await asyncio.gather(*tasks)

    # Flatten tickets list and combine with summary in one clean operation

    # Initialize sets with existing unique elements in summary
    unique_timelines = {
        tuple(sorted(timeline.items())) for timeline in summary.get("timeline") or []
    }
    unique_stakeholders = {
        tuple(sorted(stakeholder.items()))
        for stakeholder in summary.get("stakeholders") or []
    }

    for ticket in tickets:
        if ticket.get("timeline"):
            for timeline in ticket["timeline"]:
               
                timeline_tuple = tuple(sorted(timeline.items()))  # Make it hashable
                if timeline_tuple not in unique_timelines:
                    unique_timelines.add(timeline_tuple)
                    summary["timeline"].append(timeline)

        if ticket.get("stakeholders"):
            for stakeholder in ticket["stakeholders"]:
  
                stakeholder_tuple = tuple(
                    sorted(stakeholder.items())
                )  # Make it hashable
                if stakeholder_tuple not in unique_stakeholders:
                    unique_stakeholders.add(stakeholder_tuple)
                    summary["stakeholders"].append(stakeholder)
    return {
        **summary,
        "tickets": [
            ticket for page_tickets in tickets for ticket in page_tickets["tickets"]
        ],
    }


def consolidate_files_md(files_array):
    cons_files = ""
    try:
        for file in files_array:
            if isinstance(file.get("markdown"), dict):
                content = file.get("markdown")
            else:
                content = {"page_1": file.get("markdown")}
        return content
    except Exception as e:
        return {"error": str(e)}


# Function to create multiple tickets
async def create_tickets(
    dossier_id: str, tickets_data: List[Dict[str, Any]]
) -> List[str]:
    """Create multiple tickets in a dossier asynchronously.

    Args:
        dossier_id: ID of the dossier to which the tickets belong
        tickets_data: List of dictionaries containing ticket details

    Returns:
        List of IDs of the created tickets
    """
    return await firebase_manager.create_tickets(dossier_id, tickets_data)


# Function to get tickets by IDs
async def get_tickets(ticket_ids: List[str]) -> List[Dict[str, Any]]:
    """Retrieve multiple tickets by their IDs asynchronously.

    Args:
        ticket_ids: List of ticket IDs to retrieve

    Returns:
        List of ticket documents
    """
    return await firebase_manager.get_documents(ticket_collection, ticket_ids)


# Function to update a ticket
async def update_ticket(ticket_id: str, updates: Dict[str, Any]) -> str:
    """Update a ticket asynchronously.

    Args:
        ticket_id: ID of the ticket to update
        updates: Dictionary with fields to update

    Returns:
        ID of the updated ticket
    """
    return await firebase_manager.update_document(ticket_collection, ticket_id, updates)


# Function to delete multiple tickets
async def delete_tickets(
    project_id: str = None, ticket_ids: List[str] = []
) -> List[str]:
    """Delete multiple tickets asynchronously.

    Args:
        ticket_ids: List of ticket IDs to delete

    Returns:
        List of IDs of the deleted tickets
    """
    # threads_to_delete = []
    if ticket_ids:
        operations = []
        for ticket_id in ticket_ids:
            operations.append(
                {
                    "type": "delete",
                    "collection": ticket_collection,
                    "document_id": ticket_id,
                }
            )
        threads = await firebase_manager.query_collection(thread_collection, filters=[("ticket_id", "in", ticket_ids)])
        for thread in threads:
            operations.append(
                {
                    "type": "delete",
                    "collection": thread_collection,
                    "document_id": thread.get("id"),
                }
            )
        await firebase_manager.batch_operation(operations)
        return ticket_ids
    else:
        project_tickets = await firebase_manager.query_collection(
            ticket_collection, filters=[("project_id", "==", project_id)]
        )
        ticket_ids = [ticket.get("id") for ticket in project_tickets]
        threads =  await firebase_manager.query_collection(thread_collection, filters=[("ticket_id", "in", ticket_ids)]) if ticket_ids else []
        operations = []
        for ticket_id in ticket_ids:
            operations.append(
                {
                    "type": "delete",
                    "collection": ticket_collection,
                    "document_id": ticket_id,
                }
            )
        for thread in threads:
            operations.append(
                {
                    "type": "delete",
                    "collection": thread_collection,
                    "document_id": thread.get("id"),
                }   
            )   
        await firebase_manager.batch_operation(operations)
        return ticket_ids


async def write_dossier_rfp_details(
    project_id, summary, timeline, stakeholders, tickets
):
    random_assignee = ["John Doe", "Jane Doe", "John Smith", "Jane Smith"]
    random_reviewer = ["John Doe", "Jane Doe", "John Smith", "Jane Smith"]
    # delete existing tickets
    await delete_tickets(project_id)

    operations = []
    ticket_ids = []
    for ticket in tickets:
        id = str(uuid4())
        ticket_ids.append(id)
        operations.append(
            {
                "type": "create",
                "collection": ticket_collection,
                "data": Ticket(
                    id=id,
                    project_id=project_id,
                    title=ticket.get("title"),
                    description=ticket.get("description"),
                    status="new",
                    type=ticket.get("type"),
                    weight=ticket.get("weight"),
                    reference=ticket.get("reference"),
                    assignee=random.choice(random_assignee),
                    reviewer=random.choice(random_reviewer),
                ).to_dict(),
                "document_id": id,
            }
        )
    await firebase_manager.batch_operation(operations)
    project_data = {
        "details": {
            "summary": summary,
            "timeline": timeline,
            "stakeholders": stakeholders,
        },
        "status": ProjectStatus.COMPLETED.value,
    }
    await firebase_manager.update_document(project_collection, project_id, project_data)
    return project_data


async def generate_project_rfp(project_id: str, rfp_file_id: list[str], model: LLMModel = LLMModel.GPT_4O_MINI):
    """Generate the RFP for a project

    Args:
        project_id: ID of the project
    """
    print(f"Generating RFP for project {project_id}, {rfp_file_id}")
    try:
        if rfp_file_id:
            print(f"Fetching document with rfp_file_id: {rfp_file_id}")
            files = await enrich_files_with_markdown(rfp_file_id)

        else:
            print(f"Querying collection for project {project_id}")
            files = await firebase_manager.query_collection(
                file_collection,
                [("project_id", "==", project_id), 
                 ("is_knowledge_hub", "==", False), 
                 ("is_supporting_file", "==", False),
                 ("is_proposal_draft", "==", False)]
            )
            files = await enrich_files_with_markdown([file.get("id") for file in files])

        if not files:
            print("No files found for RFP generation.")
            return {"error": "No files found"}

        await firebase_manager.update_document(
            project_collection, project_id, {"status": ProjectStatus.IN_PROGRESS.value}
        )

        print(f"Processing RFP files {len(files)}")
        details = await extract_details(files, model)
        await firebase_manager.update_document(
            project_collection, project_id,  {
            "details": {
                "summary": details.get("summary"),
                "timeline": details.get("timeline"),
                "stakeholders": details.get("stakeholders"),
            }
        }
        )
        tickets = await extract_rfp_tickets(files, details, model)

        await write_dossier_rfp_details(
            project_id,
            tickets.get("summary", ""),
            tickets.get("timeline",[]),
            tickets.get("stakeholders",[]),
            tickets.get("tickets",[]),
        )
        return {
            "success": True,
            "details": {
                "summary": details.get("summary"),
                "timeline": details.get("timeline"),
                "stakeholders": details.get("stakeholders"),
            }
            # "tickets": tickets.get("tickets",[]),
        }
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}


async def update_project_status(project_id: str, status: str):
    """Update the status of a project

    Args:
        dossier_id: ID of the dossier to update
        status: New status to set
    """
    await firebase_manager.update_document(
        project_collection, project_id, {"status": status}
    )
    return {"success": True}


async def create_ticket(ticket: Ticket):
    """Create a new ticket."""
    try:    
        id =  ticket.id if ticket.id else str(uuid4())
        return await firebase_manager.create_document(ticket_collection, ticket.to_dict(), id)
    except Exception as e:
        return {"error": str(e)}

async def get_tickets_data(project_id: str):
    """Get tickets associated with a specific dossier

    Args:
        project_id: ID of the project
        dossier_id: ID of the dossier to fetch tickets from

    Returns:
        Dict containing ticket metadata or error message
    """
    try:
        # Get dossier data using existing function
        project_data = await firebase_manager.get_document(
            project_collection, project_id
        )
        if not project_data:
            return {"error": "Project not found"}

        project_title = project_data.get("title")
        rfp_details = project_data.get("details", {})

        tickets = await firebase_manager.query_collection(
            ticket_collection, filters=[("project_id", "==", project_id)]
        )

        if not (rfp_details or tickets):
            return {"error": "Project does not contain RFP content"}

        response = {
            "title": project_title,
            "summary": rfp_details.get("summary"),
            "timeline": rfp_details.get("timeline", []),
            "stakeholders": rfp_details.get("stakeholders", []),
            "tickets": tickets,
        }

        return response

    except Exception as e:
        return {"error": str(e)}



# --- Helper functions ---

def build_organization_metadata(user: dict) -> str:
    return f"""Organization Name: {user.get("company_name")}
Organization URL: {user.get("company_url")}
Organization Description: {user.get("company_description")}
"""

def build_ticket_details(ticket: dict, organization_metadata: str, context: str, custom_instructions: Optional[str]) -> str:
    return (
        f"Title: {ticket.get('title')}\n"
        f"Description: {ticket.get('description')}\n"
        f"Type: {ticket.get('type')}\n"
        f"Reference Section: {ticket.get('reference', {}).get('section')}\n\n"
        "Organization preparing the response to the RFP:\n"
        f"{organization_metadata}\n"
        f"{f'Additional Context: {context}' if context else ''}"
        f"{f'Custom Instructions: {custom_instructions}' if custom_instructions else ''}"
    )

def build_query_from_ticket(ticket: dict) -> str:
    return f"{ticket.get('title', '')} {ticket.get('description', '')}"

# --- Main Function ---

async def generate_ticket_answer(
    ticket_id: str,
    user_id: str,
    context: str = "",
    filesContext: Optional[List[dict]] = None,
    custom_instructions: Optional[str] = None,
    model: LLMModel = LLMModel.GPT_4O_MINI,
) -> Union[Tuple[str, List], Dict[str, str]]:
    timing_logs = {}
    total_start = time()

    try:
        # Step 1: Fetch ticket and user
        t0 = time()
        # Fetch ticket and user in parallel
        ticket, user = await asyncio.gather(
            firebase_manager.get_document(ticket_collection, ticket_id),
            firebase_manager.get_document(user_collection, user_id)
        )
        
        if not ticket:
            return {"error": "Ticket not found"}
        project_id = ticket.get("project_id")
        organization_metadata = build_organization_metadata(user)
        timing_logs["firebase_fetch"] = time() - t0

        # Step 2: Fallback filesContext
        if not filesContext:
            t2 = time()
            print("No filesContext provided, fetching files from project and user")
            project_files = await firebase_manager.query_collection(
                file_collection, [("project_id", "==", project_id)]
            )
            user_files = await firebase_manager.query_collection(
                file_collection,
                [("user_id", "==", user_id), ("is_knowledge_hub", "==", True)]
            )
            filesContext = [
                {"contentId": f.get("id")} for f in project_files + user_files
            ]
            timing_logs["fetch_files_context"] = time() - t2

        print(f"Using files: {filesContext}")

        # Step 3: Generate context from files
        t3 = time()
        query = build_query_from_ticket(ticket)
        filters = {
            "file_id": [item.get("contentId") for item in filesContext if item.get("contentId")]
        }

        files_context, files_pages = (
            await generate_context_for_rfp_tickets(query, filters=filters, top_k=3)
            if filters["file_id"] else ("", {})
        )

        kh_items_content = await _knowledge_hub_context(filesContext)
        # print("kh_items_content", kh_items_content[:200])
        full_context = f"{files_context}\n\n{kh_items_content}"
        timing_logs["generate_context"] = time() - t3

        # Step 4: Generate answer
        t4 = time()
        ticket_details = build_ticket_details(ticket, organization_metadata, context, custom_instructions)
        answer, references = await generate_answer_for_rfp_tickets(
            ticket_details=ticket_details,
            kh_context=full_context,
            files_pages=files_pages,
            model=model,
        )
        timing_logs["generate_answer"] = time() - t4

        # Step 5: Save answer to ticket
        t5 = time()
        await firebase_manager.update_document(
            ticket_collection,
            ticket_id,
            {"answer": {"markdown": answer, "references": references}},
        )
        timing_logs["firebase_save"] = time() - t5

        timing_logs["total"] = time() - total_start
        print("\nTicket Answer Generation Timing:")
        for step, duration in timing_logs.items():
            print(f"{step:<25}: {duration:.2f} seconds")
        print("-" * 100)

        return answer, references

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}


# --- Batched Version ---

async def _generate_tickets_answer(
    ticket: dict,
    user: dict,
    context: str,
    filesContext: List[dict],
    kh_items_content: str,
    custom_instructions: Optional[str],
    model: LLMModel,
) -> str:
    try:
        organization_metadata = build_organization_metadata(user)
        ticket_details = build_ticket_details(ticket, organization_metadata, context, custom_instructions)
        query = build_query_from_ticket(ticket)

        filters = {
            "file_id": [item.get("contentId") for item in filesContext if item.get("contentId")]
        }

        files_context, files_pages = (
            await generate_context_for_rfp_tickets(query, filters=filters, top_k=3)
            if filters["file_id"] else ("", {})
        )

        full_context = f"{files_context}\n{kh_items_content}"

        answer, references = await generate_answer_for_rfp_tickets(
            ticket_details=ticket_details,
            kh_context=full_context,
            files_pages=files_pages,
            model=model,
        )

        await firebase_manager.update_document(
            ticket_collection,
            ticket.get("id"),
            {"answer": {"markdown": answer, "references": references}},
        )

        return ticket.get("id")

    except Exception as e:
        traceback.print_exc()
        raise Exception(f"Error generating ticket answer: {str(e)}")


# --- Batch Entry Point ---

async def generate_tickets_answer(
    user_id: str,
    project_id: str,
    context: str = "",
    filesContext: Optional[List[dict]] = None,
    custom_instructions: Optional[str] = None,
    model: LLMModel = LLMModel.GPT_4O_MINI,
) -> List[Union[str, Exception]]:
    try:
        user = await firebase_manager.get_document(user_collection, user_id)

        if not filesContext:
            items = await firebase_manager.query_collection(
                knowledge_hub_collection, filters=[("user_id", "==", user_id)]
            )
            filesContext = [
                {"itemId": item.get("id"), "contentId": item.get("content", {}).get("id")}
                if item.get("content", {}).get("id")
                else {"itemId": item.get("id")}
                for item in items
            ]

        print("filesContext", filesContext)
        kh_items_content = await _knowledge_hub_context(filesContext)

        tickets = await firebase_manager.query_collection(
            ticket_collection, filters=[("project_id", "==", project_id)]
        )
        n = len(tickets)

        results = []
        for i in range(0, len(tickets), 10):
            batch = tickets[i:i + 10]
            batch_result = await asyncio.gather(*[
                _generate_tickets_answer(ticket, user, context, filesContext, kh_items_content, custom_instructions, model)
                for ticket in batch
            ], return_exceptions=True)
            results.extend(batch_result)
            
            # Send progress update
            progress = (min(i+10, n)/ n)*100
            await ws_manager.send(project_id, "tickets_answers_generation_progress", progress)

            for result in batch_result:
                if isinstance(result, Exception):
                    # Optionally log the error with traceback for debugging
                    print(f"[ERROR] Ticket generation failed: {str(result)}")
                    traceback.print_exception(type(result), result, result.__traceback__)

        await ws_manager.send(project_id, "tickets_answers_generation_progress", 100, completed=True)


        return results

    except Exception as e:
        traceback.print_exc()
        return [{"error": str(e)}]
    
async def save_ticket_answer(ticket_id: str, answer: str):
    """Save the answer for a specific ticket.

    Args:
        ticket_id: ID of the ticket to save the answer for
        answer: HTML string from TipTap editor's getHTML()
    """
    try:

        print(f"Saving answer for ticket {ticket_id}")

        await firebase_manager.update_document(
            ticket_collection, ticket_id, {"answer": answer}
        )
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


async def generate_text_highlight(ticket_id: str, paragraph_id: str, model: LLMModel = LLMModel.GPT_4O_MINI):
    """Generate a text highlight for a specific ticket.

    Args:
        ticket_id: ID of the ticket to generate the highlight for
        paragraph_id: ID of the paragraph to highlight

    Returns:
        Dictionary containing the highlight or error message
    """
    try:
        ticket = await firebase_manager.get_document(ticket_collection, ticket_id)
        if not ticket:
            return {"error": "Ticket not found"}

        markdown = ticket.get("answer", {}).get("markdown", "")
        references = ticket.get("answer", {}).get("references", {})

        paragraph = references.get(paragraph_id, {})
        # highlights = paragraph.get("highlights", [])
        sources = paragraph.get("sources", [])

        if not paragraph:
            return {"error": "No paragraph found for ticket"}
        if not sources:
            return {"error": "No sources found for ticket to highlight"}
        files = {}
        files_content = ""
        answer = ""
        for source in sources:
            file_id = source.get("file_id")
            file = await firebase_manager.get_document(file_collection, file_id)
            if not file:
                return {"error": "File not found"}

            file_content = get_pdf_text(file.get("url"), source.get("pages"))
            files_content += f"""File ID: {file_id}\nContent:\n```{file_content}```\n\n"""

            files[file.get("id")] = (file.get("url"), source.get("pages"))
            answer += f"{source.get('text')}\n"

        # print("files_content", files_content, "\n")
        # print("answer", answer, "\n")
 

        highlight_data, highlights_usage = await _generate_highlight_snippets(
            files_content, answer, model
        )

        print("highlight_data", highlight_data)
        complete_highlights = []

        if highlight_data:
            for h in highlight_data:
                highlight_objects = []
                if h and h.snippets:
                    url, pages = files.get(h.file_id)
                    pages_num = [int(page.split("_")[-1]) for page in pages] if pages else None
                    highlight_objects = await generate_highlight_objects(
                        url, h.snippets, pages_num
                    )

                # print("Highlight objects", highlight_objects)
                complete_highlights.append(
                    {
                        "id": file["id"],
                        "name": file["name"],
                        "url": file["url"],
                        "highlights": highlight_objects,
                    }
                )
        paragraph["highlights"] = complete_highlights
        references[paragraph_id] = paragraph

        updated_ticket = {"answer": {"markdown": markdown, "references": references}}
        await update_ticket(ticket_id, updated_ticket)
        return complete_highlights

    except Exception as e:
        traceback.print_exc()
        print(f"Error generating text highlight: {str(e)}")
        return {"error": str(e)}
