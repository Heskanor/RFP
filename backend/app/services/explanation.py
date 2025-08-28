from app.config.llm_factory import LLMFactory, LLMModel


from typing import List, Dict, Any
import pymupdf
import requests
from pydantic import BaseModel
from io import BytesIO
from app.services.prompts import HIGHLIGHT_GENERATION_PROMPT
from app.models.models import Collections

file_collection = Collections.FILE.value
dossier_collection = Collections.DOSSIER.value


class FileHighlights(BaseModel):
    file_id: str
    snippets: List[str]


class HighlightFormat(BaseModel):
    highlights: List[FileHighlights]


HIGHLIGHT_SYSTEM_PROMPT = """
You are a PDF text matching assistant. Your task is to find exact, verbatim text snippets in the provided File content that support or are related to the target information.

⚠️ Very important:
- You may **not generate or paraphrase any text**.
- You may **not quote the answer**.
- Only extract **exact text as it appears** in the files, **preserving all spacing and formatting exactly**.
- The PDF may contain invisible characters (e.g., \u202d, \u202c), weird spacing, and line breaks. Copy the text EXACTLY as it appears - these characters are crucial for matching.
- If a single logical unit is split across multiple lines, include the entire unit with all line breaks intact.

✅ Good examples include:
- Definitions, descriptions, or features from the file that align with technical or conceptual points in the answer.
- Mentions of modularity, scalability, cloud access, abstraction layers, etc. that support general API design principles discussed in the answer.

❌ Do NOT:
- Make up any wording.
- Extract from the answer.
- Return metadata or context that is not directly quoted.
- Clean, normalize, or modify the extracted text in any way.

Expected output format:
{
  "highlights": [
    {
      "file_id": "file1",
      "snippets": ["snippet1 exactly as it appears with all whitespace and special characters ascii", "snippet2"]
    },
    {
      "file_id": "file2",
      "snippets": ["snippet3"]
    }
  ]
}
Remember: The EXACT text preservation is critical for successful PDF highlighting. Do not "fix" or clean the text in any way
If no relevant or supportive text is found, return an empty list.
"""

def get_pdf_text(url: str, page_nums: List = None) -> str:
    """
    Get the text from the pdf at the given url

    Parameters:
    - url (str): The url of the document to get the text from.

    Returns:
    - str: The text from the document
    """

    response = requests.get(url)
    pdf_bytes = BytesIO(response.content)
    doc = pymupdf.Document(stream=pdf_bytes, filetype="pdf")
    page_nums = [int(page_num.split("_")[-1]) for page_num in page_nums]

    if page_nums:
        return "\n".join(
            [page.get_text() for page in doc if page.number + 1 in page_nums]
        )

    return "\n".join([page.get_text() for page in doc])


def _split_snippet(snippet, num_words=2):
    """Split snippet into overlapping chunks of 'num_words' words each."""
    words = snippet.split()
    if len(words) <= num_words:
        return [snippet]  # Return full snippet if it's short

    return [
        " ".join(words[i : i + num_words]) for i in range(len(words) - num_words + 1)
    ]

def _find_pdf_highlight_fallback(doc, snippet, pages_to_search):
    """
    Search for text snippet in a PDF and return formatted highlight positions.
    """
    search_flags = (
        pymupdf.TEXT_PRESERVE_WHITESPACE | pymupdf.TEXT_PRESERVE_LIGATURES
    )
    highlight_rects = []
    for p in pages_to_search:
        page = doc[p-1]
        tree_first_word = " ".join(snippet.split()[:5])
  
        results = page.search_for(tree_first_word, flags=search_flags)
        if results:
            page_found = page
            highlight_rects.extend(results)
            break
    if not highlight_rects:
        return None, None
    return highlight_rects, page_found

def _find_pdf_highlight_positions(doc, snippet, page_num: int | list[int] = None, num_words: int = 2):
    """
    Search for text snippet in a PDF and return formatted highlight positions.

    Args:
        doc: PyMuPDF document object
        snippet: Full text snippet to search
        page_num: Single page number or list of page numbers to search on (optional)

    Returns:
        dict: Formatted highlight position data, or None if not found.
    """


    # snippet_parts = _split_snippet(snippet, num_words=num_words)  # Split snippet into smaller parts
    highlight_rects = []
    page_found = None

    # Normalize page_num to a set of page numbers (1-based indexing)
    if isinstance(page_num, int):
        pages_to_search = {page_num}
    elif isinstance(page_num, list):
        pages_to_search = set(page_num)
    else:
        pages_to_search = None  # Search all pages

    for page in doc:
        current_page_number = page.number + 1  # PyMuPDF uses 0-based indexing
        if pages_to_search and current_page_number not in pages_to_search:
            continue  # Skip pages not in the list

        search_flags = (
            pymupdf.TEXT_PRESERVE_WHITESPACE | pymupdf.TEXT_PRESERVE_LIGATURES
        )
   
        results = page.search_for(snippet, flags=search_flags)
        if results:
            page_found = page  # Track which page contains the snippet
            highlight_rects.extend(results)
            break  # Stop after first full match

        # for part in snippet_parts:
        #     results = page.search_for(part, flags=search_flags)
        #     if results:
        #         page_found = page
        #         highlight_rects.extend(results)
    highlight_rects, page_found = _find_pdf_highlight_fallback(doc, snippet, pages_to_search) if not highlight_rects else (highlight_rects, page_found)
    if not highlight_rects:
        if page_num:
            page_num = page_num if isinstance(page_num, int) else page_num[0]
        else:
            page_num = 1
        return {
        "content": {"text": snippet},
        "position": {
            "boundingRect": {
                "x1": 0,
                "y1": 0,
                "x2": 0,
                "y2": 0,
                "width": 0,
                "height": 0,
            },
            "rects": [],
            "pageNumber": page_num,
        },
    }

    # Merge rectangles (assuming they belong to the same snippet)
    min_x1, min_y1 = float("inf"), float("inf")
    max_x2, max_y2 = float("-inf"), float("-inf")

    merged_rects = []
    for rect in highlight_rects:
        x1, y1, x2, y2 = rect
        merged_rects.append(
            {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "width": page_found.rect.width,
                "height": page_found.rect.height,
            }
        )
        min_x1, min_y1 = min(min_x1, x1), min(min_y1, y1)
        max_x2, max_y2 = max(max_x2, x2), max(max_y2, y2)

    return {
        "content": {"text": snippet},
        "position": {
            "boundingRect": {
                "x1": min_x1,
                "y1": min_y1,
                "x2": max_x2,
                "y2": max_y2,
                "width": page_found.rect.width,
                "height": page_found.rect.height,
            },
            "rects": merged_rects,
            "pageNumber": page_found.number + 1,
        },
    }


class ExplanationResponse(BaseModel):
    highlights: List[Dict[str, Any]]


async def generate_highlight_objects(
    document_url: str, highlight_snippets: List[str], page_num: int | list[int] = None, num_words: int = 2
) -> List[Dict[str, Any]]:
    """
    Generate and sort highlight objects from text snippets

    Args:
        document_url: URL of the PDF document
        highlight_snippets: List of text snippets to highlight

    Returns:
        List of formatted highlight objects, sorted by page and position
    """
    # Generate highlight objects
    response = requests.get(document_url)
    pdf_bytes = BytesIO(response.content)
    doc = pymupdf.Document(stream=pdf_bytes, filetype="pdf")

    highlight_objects = []
    for snippet in highlight_snippets:
        highlight_obj = _find_pdf_highlight_positions(doc, snippet, page_num, num_words)
        if highlight_obj:
            highlight_objects.append(highlight_obj)
        else:
            highlight_objects.append({"content": {"text": snippet}})

    # Sort by page number and position
    highlight_objects.sort(
        key=lambda obj: (
            obj["position"]["pageNumber"] if "position" in obj else float("inf"),
            (
                obj["position"]["boundingRect"]["y1"]
                if "position" in obj
                else float("inf")
            ),
        )
    )

    return highlight_objects


def _extract_token_usage(usage: Any) -> Dict[str, int]:
    """Extract token usage statistics from API response"""
    return {
        "input_tokens": usage.prompt_tokens,
        "output_tokens": usage.completion_tokens,
        "cached_tokens": (
            usage.prompt_tokens_details.cached_tokens
            if hasattr(usage, "prompt_tokens_details")
            else 0
        ),
    }


async def _generate_highlight_snippets(
    files_content: str, answer: str, model: LLMModel = LLMModel.GPT_4O_MINI
) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Generate highlight snippets for each file based on chat history and answer"""
    llm = LLMFactory.get_llm_with_structured_output(model, HighlightFormat)
    # messages = [
    #     {
    #         "role": "system",
    #         "content": HIGHLIGHT_SYSTEM_PROMPT
    #         + f"\n\n# Files Content:\n{files_content}\n\n",
    #     },
    #     {
    #         "role": "user",
    #         "content": f"**Target information:**\n{answer}",
    #     },
    # ]
  
    messages = HIGHLIGHT_GENERATION_PROMPT.compile(files_content = files_content, answer = answer)
    


    response = await llm.ainvoke(messages)
 
  
    # return response.highlights, _extract_token_usage(
    #     response.usage
    # )
    return response.highlights, {}
