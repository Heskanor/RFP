from app.config.firebase import firebase_manager

from app.models.models import (Thread, Collections)
from app.models.routers_models import MessageRequest

from app.config.llm_factory import  LLMModel, LLMFactory, force_tool_choice
from fastapi import HTTPException

from typing import List, Literal, Optional, Dict, Any
import json
from pydantic import BaseModel

from uuid import uuid4
from time import time

from datetime import datetime
import traceback
import asyncio

from .llm_agents import (
    search_and_answer_from_files,
    generate_answer_from_conversation,
    generate_context,
    generate_answer,
    generate_answer_for_rfp_tickets,
    TOOL_SYSTEM_PROMPT,
    AnswerSchema
)
from app.services.explanation import (
    _generate_highlight_snippets,
    generate_highlight_objects,
    get_pdf_text,
)
from app.services.prompts import TOOLS_CHOICE_PROMPT, TOOLS_CHOICE_PROMPT

dossier_collection = Collections.DOSSIER.value
project_collection = Collections.PROJECT.value
thread_collection = Collections.THREAD.value
file_collection = Collections.FILE.value
ticket_collection = Collections.TICKET.value
knowledge_hub_collection = Collections.KNOWLEDGE_HUB.value
user_collection = Collections.USER.value


CHAT_SYSTEM_PROMPT = """
You are a helpful assistant supporting users on RFP and knowledge-based projects. Your task is to provide answers grounded in the project documents, curated knowledge hub items, and prior chat history.
1. Base all answers **strictly** on the retrieved document context, structured data, or prior conversation.
2. Provide accurate, concise responses
3. If charts or non-text elements were extracted and summarized, feel free to include their insights if relevant.
4. If you cannot find relevant information in any document, state that clearly (provide knowledge hub with relevant items or select relevant items)
5. If multiple documents support an answer, synthesize across them.
Always ensure answers are focused, fact-based.
"""

class ChatRequest(BaseModel):
    id: str
    prompt: str
    timestamp: Optional[int] = None


class Milestone(BaseModel):
    date: str
    milestone: str


class Contact(BaseModel):
    """
    Schema for stakeholder contact information
    """

    name: str
    title: str
    email: str


async def _get_or_create_thread( ticket_id, project_id, user_id, title):
    thread = await firebase_manager.query_collection(
            thread_collection,
            filters=[("ticket_id", "==", ticket_id)],
        )
    
    if not thread:
        thread_id = str(uuid4())
        thread = Thread(
                id=thread_id,
                ticket_id=ticket_id,
                project_id=project_id,
                user_id=user_id,
                title=title,
                thread=[],
            )
        await firebase_manager.create_document(
            thread_collection,
            thread,
            document_id=thread_id,
        )
        return thread.to_dict()
    return thread[0]


async def _process_tool_response(
    response, filesContext, project_details, tickets_details, chat_history, FILES_PAGES, llm_model, org_context
):
    tool_call = response.tool_calls
    images_references = []
    tables_references = []
    if not tool_call:
        return

    tool_call = tool_call[0]
    function_name = tool_call.get("name", "")
    print("FUNCTION NAME", function_name)

    if function_name == "generate_answer_from_conversation":
        yield {"content": tool_call.get("args", "").get("answer", ""), 
            "images_references": images_references, 
            "tables_references": tables_references,
            # "files_pages": FILES_PAGES
            }
        print("ANSWER", tool_call.get("args", ""))

    elif function_name == "search_and_answer_from_files":
        query = tool_call.get("args", "")
        print("QUERY", query)

        files_context, files_pages = await generate_context(
            query["query"],
            filters={
                "file_id": [item.get("contentId") for item in filesContext if item.get("contentId")],
            },
            top_k=5
        )
        kh_items_content = await _knowledge_hub_context(filesContext)

        print("files_context", files_context[:500])
        print("kh_items_content", kh_items_content[:500])
        kh_context = f"{files_context} \n\n{kh_items_content}"
        # rfp_context += f"\n# Knowledge Hub Context:\n\n{files_context} \n\n{kh_items_content}"
        FILES_PAGES.append(files_pages)

        async for answer in generate_answer(
            user_prompt=query["query"],
            kh_context=kh_context,
            project_details=project_details,
            tickets_details=tickets_details,
            chat_history=chat_history,
            llm_model=llm_model,
            org_context=org_context
        ):
            chunk = answer.model_dump()
            images_references = chunk.get("image_references", []) if chunk.get("image_references") else []
            tables_references = chunk.get("table_references", []) if chunk.get("table_references") else []

            images_references = [image for image in images_references if image.get("image_id") in kh_context]
            tables_references = [table for table in tables_references if table.get("table_id") in kh_context]

            yield {"content": chunk.get("markdown", ""), 
                "images_references": images_references, 
                "tables_references": tables_references,
                }


async def _update_chat_history(
    thread_id, chat_history, chat_request, generated_answer, files_pages, is_regenerated, images_references, tables_references
):
    try:
        # if is_regenerated:
        #     chat_history = [msg for msg in chat_history if msg["id"] != chat_request.id]

        timestamp_now = int(datetime.now().timestamp())
        chat_history.extend(
            [
                {
                    "id": chat_request.id,
                    "role": "user",
                    "content": chat_request.prompt,
                    "timestamp": chat_request.timestamp,
                },
                {
                    "id": chat_request.id,
                    "role": "assistant",
                    "content": generated_answer,
                    "timestamp": timestamp_now,
                    "files_pages": files_pages,
                    "images_references": images_references,
                    "tables_references": tables_references,
                },
            ]
        )
        
        await firebase_manager.update_document(
            thread_collection, thread_id, {"thread": chat_history}
        )
    except Exception as e:
        traceback.print_exc()
        print(e)


def generate_ticket_context(
    summary: str,
    timeline: List[Milestone],
    stakeholders: List[Contact],
    ticket_data: dict
) -> str:
    """Generate context string from RFP details"""

    # Transform tickets_data into a more structured format
    structured_tickets = {
        "title": ticket_data.get("title"),
        "description": ticket_data.get("description"),
        "status": ticket_data.get("status"),
        "assignee": ticket_data.get("assignee"),
        "reviewer": ticket_data.get("reviewer"),
        "type": ticket_data.get("type"),
        "answer": ticket_data.get("answer", {}).get("markdown", ""),
    }
    project_details = f"""
**Project Summary**: {summary}

**Project Timeline**:
```json
{json.dumps(timeline, indent=2)}
```

**Project Stakeholders**:
```json
{json.dumps(stakeholders, indent=2)}
```
"""
    tickets_details = f"""
**Focused Requirements(Tickets) for Proposal Generation**:
- title: {structured_tickets.get('title')}
- description: {structured_tickets.get('description')}
- type: {structured_tickets.get('type')}
- answer: {structured_tickets.get('answer')}
"""
    return project_details, tickets_details


async def generate_tickets_insights(
    project_id: str,
    ticket_id: str,
    chat_request: ChatRequest,
    filesContext: Optional[List] = [],
    is_regenerated: Optional[bool] = False,
    llm_model: Optional[LLMModel] = LLMModel.GPT_4O_MINI,
):      
    """
    Generate an answer for a specific ticket using context from RFP metadata and documents.
    """
    CHAT_SYSTEM_PROMPT = (
        "You are an expert at analysing RFP documents. "
        "Your expertise will be solicited to power an RFP submission application."
    )

    timing_logs = {}
    total_start = time()
    images_references = []
    tables_references = []
    print("FILES CONTEXT", filesContext)

    try:
        # --- Step 1: Fetch ticket and project data ---
        fetch_start = time()
        ticket_data, project_data = await asyncio.gather(
            firebase_manager.get_document(ticket_collection, ticket_id),
            firebase_manager.get_document(project_collection, project_id)
        )
        user_data = await firebase_manager.get_document(user_collection, project_data.get("user_id", ""))
        org_context  = f"""Organization Name: {user_data.get("company_name")}
Organization URL: {user_data.get("company_url")}
Organization Description: {user_data.get("company_description")}
"""
        timing_logs["firebase_fetch"] = time() - fetch_start

        user_id = project_data.get("user_id", "")
        title = project_data.get("title", "")
        rfp_details = project_data.get("details", {})

        # --- Step 2: Fetch thread data ---
        thread_start = time()
        
        thread = await _get_or_create_thread(ticket_id, project_id, user_id, title)
        chat_history, thread_id = thread.get("thread", []), thread.get("id", "")

        if is_regenerated:
            chat_history_regenerated = []
            for msg in chat_history:
                if msg["id"] == chat_request.id:
                    break
                chat_history_regenerated.append(msg)
            chat_history = chat_history_regenerated
        

    
        timing_logs["thread_fetch"] = time() - thread_start

        # --- Step 3: Construct RFP context ---
      
        project_details, tickets_details = generate_ticket_context(
            rfp_details.get("summary", ""),
            rfp_details.get("timeline", []),
            rfp_details.get("stakeholders", []),
            ticket_data,
        )


        # --- Step 4: Prepare and call LLM with tools ---
        llm_start = time()
        formatted_history = [{"role": msg["role"], "content": msg["content"]} for msg in chat_history]
        TOOL_SYSTEM_PROMPT = TOOLS_CHOICE_PROMPT.compile(project_context = project_details + "\n\n" + tickets_details, org_context = org_context)
        tools_messages = [
            {"role": "system", "content": TOOL_SYSTEM_PROMPT},
            *formatted_history,
            {"role": "user", "content": f"\n{chat_request.prompt}"},
        ]



        response = await LLMFactory.get_llm(llm_model).bind_tools([search_and_answer_from_files, generate_answer_from_conversation]).ainvoke(
            input=tools_messages,
            tool_choice=force_tool_choice(llm_model))
        timing_logs["tool_call"] = time() - llm_start

        # --- Step 5: Process tool response and stream output ---
        answer_start = time()
        GENERATED_ANSWER = ""
        FILES_PAGES = []
        async for answer in _process_tool_response(
            response=response,
            filesContext=filesContext,
            project_details=project_details,
            tickets_details=tickets_details,
            chat_history=formatted_history,
            FILES_PAGES=FILES_PAGES,
            llm_model=llm_model,
            org_context=org_context
        ):

            # answer = answer.model_dump()
            GENERATED_ANSWER = answer.get("content", "")
            images_references = answer.get("images_references", []) 
            tables_references = answer.get("tables_references", []) 
            
            yield json.dumps(answer) + "\n"
            
        timing_logs["answer_generation"] = time() - answer_start


        # --- Step 6: Save the new message in thread ---
        save_start = time()
        await _update_chat_history(
            thread_id=thread_id,
            chat_history=chat_history,
            chat_request=chat_request,
            generated_answer=GENERATED_ANSWER,
            files_pages=FILES_PAGES[0] if FILES_PAGES else {},
            is_regenerated=is_regenerated,
            images_references=images_references,
            tables_references=tables_references,
        )
        timing_logs["firebase_save"] = time() - save_start

        # --- Final: Total time ---
        total_time = time() - total_start
        timing_logs["total"] = total_time

        print("\nAnswer generation timing:")
        for step, duration in timing_logs.items():
            print(f"{step:<20}: {duration:.2f} seconds")
        print("-" * 50)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating ticket answer: {str(e)}"
        )
    
async def get_thread_by_ticket_id(ticket_id: str) -> Dict:
    """Get chat thread for a project"""
    try:
        thread = await firebase_manager.query_collection(
            thread_collection,
            filters=[
                # ("project_id", "==", project_id),
                ("ticket_id", "==", ticket_id),
            ],
        )
        if thread:
            return thread[0]
        else:
            return {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting thread: {str(e)}")


async def delete_thread(project_id: str = None, ticket_id: str = None) -> Dict:
    """Delete the thread for a specific project."""
    try:
        if project_id:
            threads = await firebase_manager.query_collection(
                thread_collection,
                filters=[
                    ("project_id", "==", project_id),
                ],
            )
            operations = [
                {
                    "type": "delete",
                    "collection": thread_collection,
                    "document_id": thread.get("id"),
                }
                for thread in threads
            ]
            await firebase_manager.batch_operation(operations)
        if ticket_id:
            thread = await firebase_manager.query_collection(
                thread_collection,
                filters=[
                    ("ticket_id", "==", ticket_id),
                ],
            )
            await firebase_manager.update_document(
                thread_collection, thread[0].get("id"), {"thread": []}
            )
            return {"success": True}
        else:
            return {"success": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting thread: {str(e)}")


async def generate_highlights(thread_id: str, message_id: str, llm_model: LLMModel) -> Dict:
    """Generate highlights for a specific project."""
    try:
        print("Generating highlights: ", thread_id, "message_id: ", message_id)
        thread = await firebase_manager.get_document(thread_collection, thread_id)

        if not thread:
            return {"error": "No thread found"}
        chat_history = thread.get("thread", [])
        message = next((msg for msg in chat_history if msg["id"] == message_id), None)

        if not message:
            return {"error": "Message not found"}
        # Clean current chat to exclude 'explanation' field

        current_chat = [
            {key: msg[key] for key in msg if key != "explanation"}
            for msg in chat_history
        ]

        answer, files_pages = next(
            (msg["content"], msg["files_pages"])
            for msg in current_chat
            if msg["id"] == message_id and msg["role"] == "assistant"
        )
        if not files_pages:
            return {"error": "No files pages found"}

        files = await firebase_manager.get_documents(
            file_collection, list(files_pages.keys())
        )

        files_content = "\n\n".join(
            f"File ID: {file['id']}\nContent:\n```{get_pdf_text(file['url'], files_pages[file['id']])}```"
            for file in files
        )
        # print("FILES PAGES", files_pages)
        # print("File content", files_content)
        # # return {}

        highlight_data, highlights_usage = await _generate_highlight_snippets(
            files_content, answer, llm_model
        )
        print("HIGHLIGHT DATA", highlight_data)

        # Generate highlights
        complete_file_highlights = []
        for file in files:
            file_highlight_data = next(
                (h for h in highlight_data if h.file_id == file["id"]), None
            )

            highlight_objects = []
            if file_highlight_data and file_highlight_data.snippets:
                pages_num = [int(page.split("_")[-1]) for page in files_pages[file.get("id")]]
                # num_words = 100 if len(file_highlight_data.snippets) > 1 else 3
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
            # Update chat history with highlights
            for msg in chat_history:
                if msg["id"] == message_id and msg["role"] == "assistant":
                    msg["explanation"] = {"file_highlights": complete_file_highlights}
                    break

        await firebase_manager.update_document(
            thread_collection, thread_id, {"thread": chat_history}
        )

        return {
            "role": "assistant",
            "content": answer,
            "explanation": {"file_highlights": complete_file_highlights},
            "timestamp": int(datetime.now().timestamp()),
            "usage": highlights_usage,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating highlights: {str(e)}"
        )


async def create_project_thread(
    user_id: str,
    project_id: str,
    is_web_search: bool,
    file_ids: List[str],
    initial_message: MessageRequest,
):
    """Create a new thread."""
    try:
        if initial_message:
            title = (
                initial_message.content
                if initial_message.role == "user"
                else "New Thread"
            )
        else:
            title = "Untitled Thread"
        thread_id = str(uuid4())
        await firebase_manager.create_document(
            thread_collection,
            Thread(
                id=thread_id,
                user_id=user_id,
                project_id=project_id,
                title=title,
                is_web_search=is_web_search,
                is_project_thread=True,
                file_ids=file_ids,
                thread=[
                    {
                        "id": str(uuid4()),
                        "role": initial_message.role,
                        "content": initial_message.content,
                        "timestamp": initial_message.timestamp,
                    }
                ],
                created_at=int(datetime.now().timestamp()),
                updated_at=int(datetime.now().timestamp()),
            ),
            document_id=thread_id,
        )
        return {"id": thread_id}
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}


async def get_project_thread(thread_id: str) -> Dict:
    """Get a project thread."""
    try:
        thread = await firebase_manager.query_collection(
            thread_collection,
            filters=[
                ("id", "==", thread_id),
            ],
        )
        if thread:
            return thread[0]
        else:
            return {"error": "No thread found"}
    except Exception as e:
        return {"error": str(e)}


async def update_project_thread(thread_id: str, updates: dict) -> Dict:
    """Update a project thread."""
    try:
        await firebase_manager.update_document(thread_collection, thread_id, updates)
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


async def delete_project_thread(thread_id: str) -> Dict:
    """Delete a project thread."""
    try:
        await firebase_manager.delete_document(thread_collection, thread_id)
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


async def get_threads_by_project_id(project_id: str, limit: int) -> Dict:
    """Get threads by project ID."""
    try:
        threads = await firebase_manager.query_collection(
            thread_collection,
            filters=[
                ("project_id", "==", project_id),
                ("is_project_thread", "==", True),
            ],
            limit=limit,
            order_by="created_at",
            ascending=False,
        )
        return threads
    except Exception as e:
        return {"error": str(e)}


async def _update_thread_with_message(
    thread_id: str,
    chat_request: ChatRequest,
    chat_history: List[Dict[str, Any]],
    generated_answer: str,
    files_pages: Dict[str, List[int]],
    images_references: List[Dict[str, Any]] = [],
    tables_references: List[Dict[str, Any]] = [],
    user_time: int = None,
):
    """Update thread with new messages."""
    try:
        id = str(uuid4()) if chat_request.id is None else chat_request.id
        # Add user message if not already present
        chat_history.extend(
            [
                {
                    "id": id,
                    "role": "user",
                    "content": chat_request.prompt,
                    "timestamp": user_time,
                    
                },
                {
                    "id": id,
                    "role": "assistant",
                    "content": generated_answer,
                    "timestamp": user_time,
                    "files_pages": files_pages,
                    "images_references": images_references,
                    "tables_references": tables_references,
                },
            ]
        )

        # Update thread
        await firebase_manager.update_document(
            thread_collection,
            thread_id,
            {
                "thread": chat_history,
                "is_new_thread": False,
            },
        )

        return id
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}


async def _get_or_create_thread_data(thread_id: str, project_id: str, title: str, is_web_search: bool, file_ids: List[dict]) -> Dict:
    thread_data = await firebase_manager.get_document(thread_collection, thread_id)
    if not thread_data:
        thread = Thread(
            id=thread_id,
            project_id=project_id,
            # user_id=user_id,
            title=title,
            thread=[],
            is_project_thread=True,
            is_web_search=is_web_search,
            file_ids=file_ids,
        )
        await firebase_manager.create_document(thread_collection, thread, document_id=thread_id)
        return thread.to_dict()
    return thread_data

async def _knowledge_hub_context(file_ids: List[dict]):
    try:
        kh_itemsIds = [item.get("itemId") for item in file_ids if not item.get("contentId")]
        # print("KH ITEMS IDS", kh_itemsIds)
        if not kh_itemsIds:
            return ""
        kh_items = await firebase_manager.query_collection(knowledge_hub_collection, filters=[("id", "in", kh_itemsIds)])
        kh_items_content = {}
        _ = "\n" + "-"*50 + "\n"
        for item in kh_items:
            if item.get("type") == "curated_qa":
                kh_items_content["curated_qa"] = _ + "## Curated QAs\n" + f"**Question:** {item.get("content",{}).get('question')}\n**Answer:** {item.get("content",{}).get('answer')}"
            elif item.get("type") == "web_page":
                kh_items_content["web_page"] = _ + "## Web Pages\n" + f"**URL:** {item.get("content",{}).get('url')}\n**Title:** {item.get("content",{}).get('title')}\n**Content:** {item.get("content",{}).get('scraped_text')}"

        kh_items_content = "\n\n".join(kh_items_content.values())
        return kh_items_content
    except Exception as e:
        traceback.print_exc()
        return str(e)

async def _handle_context(args, user_prompt, user_id, file_ids, all_kh_files, logs):
    context_start = time()
    filters = {}

    if all_kh_files:
        filters["user_id"] = [user_id]
    elif file_ids:
        filters["file_id"] = [item.get("contentId") for item in file_ids if item.get("contentId")]

    context, FILES_PAGES = await generate_context(args.get("query", user_prompt), filters, top_k=5)
    kh_items = await _knowledge_hub_context(file_ids)
    context += "\n\n" + kh_items
    logs["context_generation"] = time() - context_start
    print("-"*100)
    print("CONTEXT", context[:500])
    print("KH ITEMS", kh_items[:500])
    print("-"*100)
   
    return context, FILES_PAGES
   


def _log_timings(timings, usage_metadata = None):
    print("\n" + "-" * 50)
    print("Answer generation timing:")
    for step, duration in timings.items():
        print(f"{step:<20}: {duration:.2f} seconds")
    print("-" * 50)
    if usage_metadata:
        print("Usage metadata:")
        print(usage_metadata)



async def stream_project_chat(
    thread_id: str,
    project_id: str,
    chat_request: ChatRequest,
    llm_model: LLMModel,
    is_web_search: bool = False,
    file_ids: Optional[List[dict]] = None,
    all_kh_files: bool = False,
    is_regenerated: bool = False,
):
    file_ids = file_ids or []
    FILES_PAGES = {}
    GENERATED_ANSWER = ""
    images_references = []
    tables_references = []
    timing_logs = {}
    total_start = time()
    user_prompt = chat_request.prompt

    try:
        # --- Fetch Project Data ---
        firebase_start = time()
        project_data = await firebase_manager.get_document(project_collection, project_id)
        user_data = await firebase_manager.get_document(user_collection, project_data.get("user_id", ""))

        user_id = project_data.get("user_id")
        metadata = f"**Project Title:** {project_data.get('title')}\n**Summary:** {project_data.get('details', {}).get('summary')}"
        org_context = f"""Organization Name: {user_data.get("company_name")}
Organization URL: {user_data.get("company_url")}
Organization Description: {user_data.get("company_description")}
"""

        # --- Get or create thread ---
        thread_data = await _get_or_create_thread_data(thread_id, project_id, user_prompt, is_web_search, file_ids)
        timing_logs["firebase_fetch"] = time() - firebase_start

        chat_history = thread_data.get("thread", [])
        if is_regenerated:
            chat_history_regenerated = []
            for msg in chat_history:
                if msg["id"] == chat_request.id:
                    break
                chat_history_regenerated.append(msg)
            chat_history = chat_history_regenerated
       
        formatted_history = [{"role": msg["role"], "content": msg["content"]} for msg in chat_history]

        # --- Prepare tool messages ---
        tools_start = time()
        TOOL_SYSTEM_PROMPT  = TOOLS_CHOICE_PROMPT.compile(project_context = metadata, org_context = org_context) 
        #TOOL_SYSTEM_PROMPT + f"\n\n**Project Metadata:**\n{metadata}"
        timing_logs["tool_system_prompt"] = time() - tools_start
        tools_messages = [
            {"role": "system", "content": TOOL_SYSTEM_PROMPT},
            *formatted_history,
            {"role": "user", "content": user_prompt},
        ]

        tools = [generate_answer_from_conversation, search_and_answer_from_files]
        tools_response = await LLMFactory.get_llm(llm_model).bind_tools(tools).ainvoke(
            input=tools_messages,
            tool_choice=force_tool_choice(llm_model) 
        )
        tool_call = tools_response.tool_calls
        timing_logs["tool_call"] = time() - tools_start

        # --- Process Tool Call ---
        if not tool_call:
            yield json.dumps(
                {"content": "I'm having trouble processing your request. Please try again.", 
                "images_references": images_references, 
                "tables_references": tables_references,
                # "files_pages": FILES_PAGES
                }) + "\n"
            return

        tool = tool_call[0]
        function_name = tool.get("name")
        args = tool.get("args")

        answer_start = time()
        print("FUNCTION NAME", function_name, args)
        if function_name == "generate_answer_from_conversation":
            GENERATED_ANSWER = args.get("answer", "")
            yield json.dumps(
                {"content": GENERATED_ANSWER, 
                "images_references": images_references, 
                "tables_references": tables_references,
                # "files_pages": FILES_PAGES
                }) + "\n"
            timing_logs["answer_generation"] = 0
            

        elif function_name == "search_and_answer_from_files":
            context, FILES_PAGES = await _handle_context(
                args, user_prompt, user_id, file_ids, all_kh_files, timing_logs
            )
            # context = "## Uploaded Files Context\n" + context + "\n" + "-"*50 
          
            async for chunk in generate_answer(
                 user_prompt=user_prompt,
                 kh_context=context,
                 project_details=metadata,
                 tickets_details=None,
                 chat_history=formatted_history,
                 llm_model=llm_model,
                 org_context=org_context
                ):
                chunk = chunk.model_dump()
                GENERATED_ANSWER = chunk.get("markdown", "")
                images_references = chunk.get("image_references", []) if chunk.get("image_references") else []
                tables_references = chunk.get("table_references", []) if chunk.get("table_references") else []

                images_references = [image for image in images_references if image.get("image_id") in context]
                tables_references = [table for table in tables_references if table.get("table_id") in context]

                yield json.dumps(
                    {"content": GENERATED_ANSWER, 
                    "images_references": images_references, 
                    "tables_references": tables_references,
                    
                    }) + "\n"

            timing_logs["answer_generation"] = time() - answer_start

        # --- Save Chat Message ---
        save_start = time()
        await _update_thread_with_message(
            thread_id=thread_id, 
            chat_request=chat_request, 
            chat_history=chat_history,
            generated_answer=''.join(GENERATED_ANSWER) if isinstance(GENERATED_ANSWER, list) else GENERATED_ANSWER,
            files_pages=FILES_PAGES,
            user_time=int(time()),
            images_references=images_references,
            tables_references=tables_references
        )
        timing_logs["firebase_save"] = time() - save_start

        # --- Logging ---
        timing_logs["total"] = time() - total_start
        _log_timings(timing_logs)

    except Exception as e:
        traceback.print_exc()
        yield "Error processing your request. Please try again."

