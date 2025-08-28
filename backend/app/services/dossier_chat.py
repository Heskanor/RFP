# from app.config.openai import async_client

# # from openai.types.chat.chat_completion_tool_param import FunctionDefinition
# # from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
# from app.config.firebase_ref import firebase_manager
# from .llm_agents import (
#     AnswerGenerationTool,
#     ContextGenerationTool,
#     generate_context,
#     generate_answer,
#     TOOL_SYSTEM_PROMPT,
# )

# from app.models.models import ColumnDefinition
# from typing import List, Dict, Any, Union
# from time import time

# from typing import List, Dict, Any, Optional
# from datetime import datetime
# from time import time

# from app.services.explanation import get_pdf_text, generate_highlight_objects
# from app.services.dossier_service import get_dossier
# from app.services.thread_service import (
#     get_chat_history,
#     update_chat_history,
# )
# from app.services.vectorization_service import VectorizationService
# from pydantic import BaseModel
# from app.models.models import Collections
# import json
# import asyncio

# import logging

# file_collection = Collections.FILE.value

# CHAT_SYSTEM_PROMPT = """
# You are a helpful assistant analyzing documents in a dossier and project files. Your task is to:
# 1. Answer questions based on all documents in the dossier and previous chat history
# 2. Provide accurate, concise responses
# 3. Base your answers strictly on the documents' content and chat history
# 4. If you cannot find relevant information in any document, state that clearly

# NB: Project is composed of dossiers and files shared between dossiers.
# Keep responses focused and relevant to the documents' content.
# """

# HIGHLIGHT_SYSTEM_PROMPT = """
# Given the chat history and the latest answer, identify exact text snippets from the documents that support or justify the answer.
# The snippets should be direct, verbatim extracts that will be used to highlight relevant sections in the documents. do not add even a single word or punctuation mark.
# Your result will be used to search for the snippets in the documents, so do not add any extra text or punctuation marks.
# Make sure to parse symbols like &amp; to &. since the documents are stored as markdown but the lookup is done in the original pdf.
# Return only the most relevant snippets that directly support the answer, grouped by file.

# Expected output format:
# {
#     "highlights": [
#         {
#             "file_id": "file1",
#             "snippets": ["snippet1", "snippet2"]
#         },
#         {
#             "file_id": "file2",
#             "snippets": ["snippet3"]
#         }
#     ]
# }
# if the answer is not related to the files or the information is not in the files, return an empty list.
# """


# def _extract_token_usage(usage: Any) -> Dict[str, int]:
#     """Extract token usage statistics from API response"""
#     return {
#         "input_tokens": usage.prompt_tokens,
#         "output_tokens": usage.completion_tokens,
#         "cached_tokens": (
#             usage.prompt_tokens_details.cached_tokens
#             if hasattr(usage, "prompt_tokens_details")
#             else 0
#         ),
#     }


# async def _generate_highlight_snippets(
#     files_content: str, chat_history: List[Dict[str, Any]], answer: str
# ) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
#     """Generate highlight snippets for each file based on chat history and answer"""
#     # chat_context = "\n".join(
#     #     [
#     #         f"{msg['role']}: {msg['content']}"
#     #         for msg in chat_history[-3:]  # Include last 3 messages for context
#     #     ]
#     # )

#     messages = [
#         {"role": "system", "content": HIGHLIGHT_SYSTEM_PROMPT},
#         {
#             "role": "user",
#             "content": f"Dossier Files Content:\n{files_content}\n\nLatest Answer:\n{answer}",
#         },
#     ]

#     class FileHighlights(BaseModel):
#         file_id: str
#         snippets: List[str]

#     class HighlightFormat(BaseModel):
#         highlights: List[FileHighlights]

#     response = await async_client.beta.chat.completions.parse(
#         model="gpt-4o",
#         messages=messages,
#         response_format=HighlightFormat,
#         temperature=0,
#     )

#     return response.choices[0].message.parsed.highlights, _extract_token_usage(
#         response.usage
#     )


# async def _update_chat_history(
#     dossier_id,
#     message_id,
#     user_prompt,
#     generated_answer,
#     files_pages,
#     is_tickets_thread,
#     project_id,
#     user_time,
# ):
#     """Update chat history with new messages."""
#     assistant_time = int(datetime.now().timestamp())
#     messages = [
#         {
#             "id": message_id,
#             "role": "user",
#             "content": user_prompt,
#             "timestamp": user_time,
#         },
#         {
#             "id": message_id,
#             "role": "assistant",
#             "content": generated_answer,
#             "timestamp": assistant_time,
#             "files_pages": files_pages,
#             "explanation": {"file_highlights": []},
#         },
#     ]
#     await update_chat_history(dossier_id, messages, is_tickets_thread, project_id)


# async def stream_dossier_chat(
#     dossier_id: str,
#     message_id: str,
#     user_prompt: str,
#     timestamp: int | None = None,
#     is_tickets_thread: bool = False,
# ):
#     """Stream LLM response for the chatbot."""
#     FILES_PAGES = {}

#     async def _process_tool_response(
#         tool_call, dossier_id, project_files, chat_history
#     ):
#         """Process tool call response and generate an answer."""

#         nonlocal FILES_PAGES

#         if tool_call:
#             tool_call = tool_call[0]
#             function_name = tool_call.function.name
#             function_args = json.loads(tool_call.function.arguments)

#             if function_name == "generate_answer_from_conversation":
#                 generated_answer = function_args.get("answer", "")
#                 yield generated_answer

#             elif function_name == "search_and_answer_from_files":
#                 query = function_args["query"]
#                 print(f"Search Query: {query}")
#                 dossier_context_task = generate_context(
#                     query,
#                     filters={
#                         "dossier_id": [dossier_id],
#                     },
#                     top_k=3,
#                 )

#                 project_files_context_task = generate_context(
#                     query,
#                     filters={
#                         "file_id": [file["id"] for file in project_files],
#                     },
#                     top_k=1,
#                 )

#                 # Run both tasks in parallel
#                 dossier_results, project_files_results = await asyncio.gather(
#                     dossier_context_task,
#                     project_files_context_task
#                 )

#                 dossier_context, dossier_pages = dossier_results
#                 project_files_context, project_files_pages = project_files_results

#                 context = f"# Dossier Context:\n{dossier_context}\n\n# Project Files Context:\n{project_files_context}"


#                 FILES_PAGES = {**dossier_pages, **project_files_pages}
#                 async for answer in generate_answer(
#                     query, context, chat_history, CHAT_SYSTEM_PROMPT
#                 ):
#                     yield answer

#     timing_logs = {}
#     total_start = time()

#     user_time = timestamp or int(datetime.now().timestamp())

#     try:
#         # Fetch dossier data and chat history
#         firebase_start = time()
#         dossier_data = await get_dossier(dossier_id, include_content=True)

#         if "error" in dossier_data:
#             raise ValueError(dossier_data["error"])

#         project_id = dossier_data.get("project_id")
#         project_files = await firebase_manager.query_collection(
#             file_collection,
#             [("dossier_id", "==", dossier_id), ("is_project_file", "==", True)],
#         )
#         chat_history = await get_chat_history(dossier_id, is_tickets_thread)
#         timing_logs["firebase_fetch"] = time() - firebase_start

#         formatted_history = [
#             {"role": msg["role"], "content": msg["content"]} for msg in chat_history
#         ]

#         # Prepare messages for tool call
#         dossier_context = f"\n\nDossier title:\n{dossier_data.get('title', '')}"
#         if dossier_data.get("files"):
#             dossier_context += f"\n\nFiles:\n{[file.get('title', '') for file in dossier_data.get('files', [])]}"

#         answer_start = time()
#         tools_messages = [
#             {"role": "system", "content": TOOL_SYSTEM_PROMPT + dossier_context},
#             *formatted_history,
#             {"role": "user", "content": user_prompt},
#         ]
#         tools = [AnswerGenerationTool, ContextGenerationTool]
#         tools_response = await async_client.chat.completions.create(
#             model="gpt-4o", messages=tools_messages, tools=tools, tool_choice="required"
#         )
#         tool_call = tools_response.choices[0].message.tool_calls
#         timing_logs["tool_call"] = time() - answer_start

#         GENERATED_ANSWER = ""

#         # Process tool response
#         answer_start = time()
#         async for answer in _process_tool_response(
#             tool_call, dossier_id, project_files, chat_history
#         ):
#             GENERATED_ANSWER += answer
#             yield answer

#         timing_logs["answer_generation"] = time() - answer_start

#         print(f"FILES_PAGES: {FILES_PAGES}")

#         # Save chat history
#         save_start = time()
#         await _update_chat_history(
#             dossier_id,
#             message_id,
#             user_prompt,
#             GENERATED_ANSWER,
#             FILES_PAGES,
#             is_tickets_thread,
#             project_id,
#             user_time,
#         )
#         timing_logs["firebase_save"] = time() - save_start

#         # Log execution times
#         total_time = time() - total_start
#         timing_logs["total"] = total_time
#         print(f"\nTotal time: {total_time:.2f} seconds")
#         print("-" * 50)
#         print("\nAnswer generation timing:")
#         for step, duration in timing_logs.items():
#             print(f"{step:<20}: {duration:.2f} seconds")
#         print("-" * 50)

#     except Exception as e:
#         logging.error(f"Error: {e}")


# async def generate_highlights(
#     dossier_id: str, message_id: str, is_tickets_thread: bool = False
# ) -> Dict[str, Any]:
#     """Generate highlights based on LLM response."""
#     try:
#         timing_logs = {}
#         total_start = time()

#         # Get dossier data and chat history
#         firebase_start = time()
#         thread = await get_chat_history(dossier_id, is_tickets_thread)

#         chat_history = thread  # thread.get("threads", [])
#         timing_logs["firebase_fetch"] = time() - firebase_start

#         # print(f"Chat history: {chat_history}")
#         # Check if the answer exists in the chat history
#         if not any(msg.get("id") == message_id for msg in chat_history):
#             raise ValueError(
#                 "The provided message id does not exist in the chat history."
#             )

#         # Clean current chat to exclude 'explanation' field
#         current_chat = [
#             {key: msg[key] for key in msg if key != "explanation"}
#             for msg in chat_history
#         ]

#         answer, files_pages = next(
#             (msg["content"], msg["files_pages"])
#             for msg in current_chat
#             if msg["id"] == message_id and msg["role"] == "assistant"
#         )

#         if not files_pages:
#             return {"error": "No files pages found"}

#         files = await firebase_manager.get_documents(
#             file_collection, list(files_pages.keys())
#         )
#         # Get highlights for each file
#         content_fetch_start = time()
#         files_content = "\n\n".join(
#             f"File ID: {file['id']}\nContent:\n{get_pdf_text(file['url'], files_pages[file['id']])}"
#             for file in files
#         )
#         timing_logs["content_fetch"] = time() - content_fetch_start

#         # Generate snippets
#         snippets_start = time()
#         highlight_data, highlights_usage = await _generate_highlight_snippets(
#             files_content, current_chat, answer
#         )
#         timing_logs["snippets_generation"] = time() - snippets_start

#         # Generate highlight objects
#         highlights_start = time()
#         complete_file_highlights = []
#         for file in files:
#             file_highlight_data = next(
#                 (h for h in highlight_data if h.file_id == file["id"]), None
#             )

#             highlight_objects = []
#             if file_highlight_data and file_highlight_data.snippets:
#                 highlight_objects = await generate_highlight_objects(
#                     file["url"], file_highlight_data.snippets
#                 )

#             complete_file_highlights.append(
#                 {
#                     "id": file["id"],
#                     "name": file["name"],
#                     "url": file["url"],
#                     "highlights": highlight_objects,
#                 }
#             )
#         timing_logs["highlight_objects"] = time() - highlights_start

#         # Sort files - files with highlights first, then by filename
#         complete_file_highlights.sort(
#             key=lambda x: (0 if x["highlights"] else 1, x["name"])
#         )

#         total_time = time() - total_start
#         timing_logs["total"] = total_time

#         print(f"\nHighlight generation timing:")
#         for step, duration in timing_logs.items():
#             print(f"{step:<20}: {duration:.2f} seconds")
#         print("-" * 50)

#         # Update chat history with highlights
#         for msg in chat_history:
#             if msg["content"] == answer:
#                 msg["explanation"] = {"file_highlights": complete_file_highlights}
#                 break

#         # Update threads in dossier
#         await update_chat_history(dossier_id, chat_history, is_tickets_thread, update_thread_with_chat=True)

#         return {
#             "role": "assistant",
#             "content": answer,
#             "explanation": {"file_highlights": complete_file_highlights},
#             "timestamp": int(datetime.now().timestamp()),
#             "usage": highlights_usage,
#         }
#     except Exception as e:
#         print("Error:", e)
#         return {"error": str(e)}
