from app.config.llm_factory import LLMFactory, LLMModel
# from openai.types.chat.chat_completion_tool_param import FunctionDefinition
# from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.services.vectorization_service import VectorizationService
from app.config.firebase import firebase_manager
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from collections import defaultdict

import re
from app.models.models import Collections
from app.services.prompts import PROJECT_CHAT_PROMPT, TICKET_ANSWER_GENERATION_PROMPT

file_collection = Collections.FILE.value


TOOL_SYSTEM_PROMPT = """You are a helpful assistant that uses two specialized tools to provide accurate and context-aware answers. Choose the most appropriate tool based on the user's question and the available context:
---

**Tool 1: generate_answer_from_conversation**
- Use this tool when the answer can be derived directly from the ongoing conversation.
- Appropriate for:
  - Follow-up questions that reference previous messages
  - Greetings, small talk, or general clarifications
  - Questions already answered earlier in the thread

**Tool 2: search_and_answer_from_files**
- Use this tool when the answer is not in the current conversation and must be retrieved from the user’s knowledge hub.
- Always create a self-contained query with full context, even for follow-up questions.
- Prioritize this tool unless the answer is obviously available in the conversation.

---

Always choose the tool that will produce the most complete and accurate response.
"""

# AnswerGenerationTool = ChatCompletionToolParam(
#     function=FunctionDefinition(
#         name="generate_answer_from_conversation",
#         description="Generate answers based on conversation history and context.",
#         parameters={
#             "type": "object",
#             "properties": {
#                 "answer": {
#                     "type": "string",
#                     "description": "The complete response to the user's question",
#                 }
#             },
#             "required": ["answer"],
#             "strict": True,
#         },
#     ),
#     type="function",
# )

# ContextGenerationTool = ChatCompletionToolParam(
#     function=FunctionDefinition(
#         name="search_and_answer_from_files",
#         description="Search and generate context from uploaded files.",
#         parameters={
#             "type": "object",
#             "properties": {
#                 "query": {
#                     "type": "string",
#                     "description": "The complete, self-contained query to search in files. Should be adapted to file types. (like Resume require a specific query to retrieve the right information)",
#                 }
#             },
#             "required": ["query"],
#             "strict": True,
#         },
#     ),
#     type="function",
# )

class GenerateAnswerInput(BaseModel):
    answer: str = Field(..., description="The complete response to the user's question")


class ImagesReference(BaseModel):
        image_id: str = Field(description="The id of the image used in the context like (image_id: img-3.jpeg)")
        file_id: str = Field(description="The id of the file where the image is located")
        label: str = Field(description="Short title for the image")

class TableReference(BaseModel):
    table_id: str
    file_id: str
    label: str = Field(description="Short title for the table")

class AnswerSchema(BaseModel):
    markdown: str
    image_references: List[ImagesReference] = Field(default_factory=list)
    table_references: List[TableReference] = Field(default_factory=list)
    
@tool(args_schema=GenerateAnswerInput,description="Generate answers based on conversation history and context.")
def generate_answer_from_conversation(answer: str) -> str:
    """Generate answers based on conversation history and context."""
    pass

class SearchFilesInput(BaseModel):
    query: str = Field(..., description="Self-contained query to search and retrieve information semantically from Knowledge Hub.")


@tool(args_schema=SearchFilesInput, description="Search and retrieve from Knowledge Hub.")
def search_and_answer_from_files(query: str) -> str:
    """Search and retrieve information from Knowledge Hub."""
    pass


async def openai_struct(provider: LLMModel, messages, output_schema):
    client = LLMFactory.get_llm_with_structured_output(provider, output_schema)
    response = await client.ainvoke(messages)
    return response


async def generate_context_for_rfp_tickets(
    user_prompt: str, filters: Dict[str, Any], top_k: int = 1
) -> tuple[str, Dict[str, int]]:
    """Generate answer based on all dossier documents and chat history"""
    vectorization_service = VectorizationService()
    docs = await vectorization_service.query_context(
        user_prompt, filters=filters, aggregation=False, top_k=top_k
    )
    context, files_pages = "", {}
    for doc in docs:
        context += (
            f"""
**File ID: {doc.metadata.get('file_id')}**
**Pages: {doc.metadata.get('page_numbers')}**
**Content:**
{doc.metadata.get('text')}
------------------------ \
"""
            + "\n\n"
        )
        files_pages[doc.metadata.get("file_id")] = doc.metadata.get("page_numbers")
    return context, files_pages


async def generate_context(
    user_prompt: str, filters: Dict[str, Any], top_k: int = 1
) -> tuple[str, Dict[str, int]]:
    """Generate answer based on all dossier documents and chat history"""
    vectorization_service = VectorizationService()
    docs = await vectorization_service.query_context(
        user_prompt, filters=filters, top_k=top_k, aggregation=False
    )
    
    context, files_pages = "", {}
    for doc in docs:
        file_id = doc.metadata["file_id"]
        
        files_pages.setdefault(file_id, []).extend(
            [
                p
                for p in doc.metadata["page_numbers"]
                if p not in files_pages[file_id]
            ]
        )
        context += f"- **File ID:** `{file_id}`\n\n" + "- **Context:**\n" + doc.metadata["text"] + " \n" + "---" + "\n\n"
    return context, files_pages


async def generate_answer(
    user_prompt: str,
    kh_context: str,
    project_details: str,
    tickets_details: str,
    chat_history: List[Dict[str, Any]],
    llm_model: LLMModel,
    org_context: str
):
    """Generate answer based on the provided context"""

   

    # messages = [
    #     {"role": "system", "content": CHAT_SYSTEM_PROMPT},
    #     *chat_history,
    #     {"role": "user", "content": f"# Knowledge Hub Context:\n{context}"},
    #     {"role": "user", "content": user_prompt}
    # ]
    CHAT_PROMPT = PROJECT_CHAT_PROMPT.compile(
        project_details = project_details, 
        tickets_details= tickets_details, 
        kh_context = kh_context,
        org_context = org_context) # CHAT_SYSTEM_PROMPT
    
    messages = [
        CHAT_PROMPT[0],
        *chat_history,
        CHAT_PROMPT[1],
        {
            "role": "user",
            "content": user_prompt
        }
    ]

    client = LLMFactory.get_llm_with_structured_output(llm_model, AnswerSchema)
    async for chunk in client.astream(messages):
        # yield chunk.
        yield chunk
    


async def generate_answer_for_rfp_tickets(
  ticket_details: str, kh_context: str,  files_pages: str, model: LLMModel
):
    """
    Generates a response for RFP tickets using an AI model and provides citations from reference files.
    """
    CHAT_SYSTEM_PROMPT = (
    "You are an AI assistant designed to help vendors generate high-quality responses to RFP (Request for Proposal) requirements. "
    "Your role is to draft compelling, accurate, and professional responses that reflect the vendor's expertise and offerings.\n\n"

    "You will receive:\n"
    "- A specific RFP requirement or question.\n"
    "- Context extracted from the vendor's Knowledge Hub (documents, capabilities, past projects).\n"
    "- Metadata about the vendor organization (e.g., name, services, tone of voice).\n\n"

    "Your goal is to generate a structured, markdown-formatted response on behalf of the vendor, using their tone and positioning to address the requirement effectively.\n\n"
    "### Guidelines for Answer Generation:\n"
    "1. **Voice and Perspective**:\n"
    "   - Write from the vendor's point of view.\n"
    "   - Adopt the vendor’s tone: professional, confident, and aligned with how they communicate in official documents.\n"
    "   - Use the same language (e.g., English, French) as the input requirement.\n\n"
    "2. **Content Quality**:\n"
    "   - Be specific, practical, and solution-oriented.\n"
    "   - Demonstrate how the vendor meets or exceeds the requirement.\n"
    "   - Use content from the Knowledge Hub and vendor metadata as factual support.\n"
    "   - Do **not** fabricate information. If no relevant information is found, acknowledge it.\n\n"
    "3. **Formatting**:\n"
    "   - Use markdown for clarity (e.g., paragraphs, bullet points, tables, quotes).\n"
    "   - Use LaTeX (`$$`) for mathematical expressions when relevant.\n"
    "   - Code blocks should use markdown syntax highlighting.\n\n"

    "### Citations and Paragraph Tracking:\n"
    "4. **Paragraph Identifiers**:\n"
    "   - End each paragraph that includes sourced content with a unique identifier in the form `p_1`, `p_2`, etc.\n"
    "   - These identifiers must correspond to the `paragraph_id` in the structured output.\n"
    "   - If a paragraph is not based on any source material, do **not** add a paragraph identifier.\n\n"
    "5. **Source Attribution**:\n"
    "   - If you used content from a Knowledge Hub file to support a paragraph, ensure the corresponding `Source` object is included.\n"
    "   - Cite **only** the most relevant, non-redundant source materials.\n"
    "   - If no reference was used, exclude the paragraph ID\n\n"

    "### Minimum Length:\n"
    "6. **Response Volume**:\n"
    "   - Write at least 2 paragraphs (minimum 100 words total).\n"
    "   - Prioritize completeness, clarity, and alignment with the vendor’s offering.\n\n"

    "### Example:\n"
    "To ensure secure connectivity to the Proof of Concept (PoC) environment, we employ encrypted data transmission protocols, including TLS 1.3 and VPN tunneling. p_1\n"
    "Our systems leverage AES-256-GCM encryption, ensuring both performance and security throughout the communication lifecycle. p_2"
)

    # messages = [
    #     {"role": "system", "content": CHAT_SYSTEM_PROMPT},
    #     {"role": "user", "content": f"\n# Knowledge Hub Context:\n{files_context}"},
    #     {"role": "user", "content": user_prompt},
        
    # ]
    messages  = TICKET_ANSWER_GENERATION_PROMPT.compile(kh_context = kh_context, ticket_details = ticket_details)

    class Source(BaseModel):
        paragraph_id: str = Field(
            ..., description="Paragraph identifier Id (p_1, p_2, etc.)"
        )
        file_id: str
        pages: List[str]
        text: str = Field(
            ...,
            description="exact text snippet used from the file to answer question will be used to highlight in the files",
        )

    class AnswerWithSources(BaseModel):
        markdown: str = Field(
            ..., description="Markdown-formatted answer with paragraph labels"
        )
        sources: List[Source]

    try:
        result = await openai_struct(model, messages, AnswerWithSources)
        _PARAGRAPH_TAG_RE = re.compile(r"p_\d+")

        # -- Collect placeholders that actually appear in the answer ----------
        answer: str = result.markdown
        used_paragraph_ids: set[str] = set(_PARAGRAPH_TAG_RE.findall(answer))

        # -- Build the reference map -----------------------------------------
        references: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"sources": [], "highlights": []}
        )
        for src in result.sources:
            references[src.paragraph_id]["sources"].append(
                {"file_id": src.file_id, "pages": src.pages, "text": src.text}
            )

        # -- Remove reference entries OR placeholders that are not needed -----
        for pid in list(references):  # copy; we'll mutate the dict
            if pid not in used_paragraph_ids:           # reference never cited
                del references[pid]
            else:
                used_paragraph_ids.discard(pid)         # still needed → keep it

        # Any remaining IDs are tokens that slipped through without sources
        for orphan_pid in used_paragraph_ids:
            answer = answer.replace(orphan_pid, "")

        return answer, references

    except Exception as exc:  # noqa: BLE001
        print("Error generating response: %s", exc)
        return "No answer found, please try again.", {}