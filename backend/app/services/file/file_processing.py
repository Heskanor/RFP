import asyncio
import traceback
import pandas as pd
import re
from uuid import uuid4
from typing import List, Dict, Any, Tuple

from app.config.firebase import firebase_manager
from app.config.mistral import mistral_client
from app.services.vectorization_service import VectorizationService
from app.config.llm_factory import LLMModel
from app.services.file.image import extract_context_around_image_id, convert_image_to_structured_output, maybe_compress_base64_image
from app.models.files_models import TextContent, TableContent, ImageContent, BoundingBox
from app.models.images_models import ChartContent
from app.models.models import Collections, FileStatus
from app.services.websocket_manager import ws_manager
from app.models.models import FileStatus
import json

file_collection = Collections.FILE.value
file_data_collection = Collections.FILE_DATA.value

import re

def _clean_latex_math(text):
    # 1. Remove \$ (escaped dollar signs) → just show the number
    text = re.sub(r'\\\$', '', text)

    # 2. Replace LaTeX percent symbol \% with %
    text = text.replace(r'\%', '%')

    # Remove html tags
    text = re.sub(r'<[^>]*>', '', text)

    # Replace \mathbf{...}, \textbf{...}, \mathrm{...} etc. with just the content
    text = re.sub(r'\\(?:mathbf|textbf|mathrm|text|mathit|mathsf|boldsymbol)\{(.*?)\}', r'\1', text)

    # Remove block math delimiters $$...$$
    text = re.sub(r'\$\$(.*?)\$\$', r'\1', text, flags=re.DOTALL)

    # Remove inline math delimiters $...$
    text = re.sub(r'\$(.*?)\$', r'\1', text)

    # Remove common LaTeX commands (non-brace ones)
    text = re.sub(r'\\[a-zA-Z]+\s*', '', text)

    #  Remove empty superscripts like ${}^{(1)}$
    text = re.sub(r'\s*\{\s*\}\s*\^\{\(\d+\)\}\s', '', text)

    # Handle expressions like ${1234}^{(1)}$ → keep only the base (1234)
    text = re.sub(r'\s*\{?([^\}]+)\}?\s*\^\{\(\d+\)\}\s*', r'\1', text)

    return text

_EMPTY_COLUMN_PREFIX = "__empty_col_"
_TABLE_REFERENCE_PREFIX = "table-"

def extract_tables_from_markdown(markdown: str, table_index: int = 0) -> Tuple[str, List[Dict[str, Any]]]:
    """Extract tables and return modified markdown with table reference tags and list of table data."""
    markdown = markdown.replace('\r\n', '\n')
    markdown = _clean_latex_math(markdown)
    table_pattern = re.compile(
        r"""(
            (?:^\|.*\|\s*\n)+
            ^\|(?:\s*:?-+:?\s*\|)+\s*\n
            (?:^\|.*\|\s*\n?)*
        )""",
        re.MULTILINE | re.VERBOSE
    )

    extracted_tables = []
    # table_index = 0
    modified_markdown = markdown
    offset = 0  # tracks character offset from prior replacements

    for match in table_pattern.finditer(markdown):
        table_markdown = match.group(0)
        start, end = match.span()
        start += offset
        end += offset

        lines = table_markdown.strip().splitlines()
        lines = [line for line in lines if not re.match(r'^\|\s*:?-+:?\s*\|', line)]
        rows = [re.split(r'\s*\|\s*', line.strip('|')) for line in lines]
        rows = [[cell.strip() for cell in row] for row in rows]

        if not rows:
            continue

        header = [col if col else f"{_EMPTY_COLUMN_PREFIX}{i}" for i, col in enumerate(rows[0])]
        data_rows = rows[1:]

        normalized_rows = [
            row + [''] * (len(header) - len(row)) if len(row) < len(header) else row[:len(header)]
            for row in data_rows
        ]

        try:
            df = pd.DataFrame(normalized_rows, columns=header)
            table_id = f"{_TABLE_REFERENCE_PREFIX}{table_index}"

            extracted_tables.append({
                # "table_id": table_id,
                # "table_markdown": table_markdown,
                "columns": [
                        {"key": col, "label": "" if col.startswith(_EMPTY_COLUMN_PREFIX) else col}
                        for col in df.columns
                    ],
                "fields": df.to_dict(orient='records')
            })

            # Inject a reference tag after the table
            replacement = f"<!--TABLE_REFERENCE: {table_id}-->\n{table_markdown.strip()}\n"
            modified_markdown = (
                modified_markdown[:start]
                + replacement
                + modified_markdown[end:]
            )

            offset += len(replacement) - (end - start)
            table_index += 1

        except Exception:
            traceback.print_exc()
            continue

    return modified_markdown, extracted_tables

def process_batch_pages(pages: List, file_id: str, llm_model: LLMModel = LLMModel.GEMINI_2_FLASH):
    """Process a batch of pages and extract text, tables, and images."""
    text_docs, table_docs, image_docs, image_tasks = [], [], [], []
    table_index = 0
    for page in pages:
        page_number = page.index + 1
        markdown = page.markdown
        modified_markdown, tables = extract_tables_from_markdown(markdown, table_index)
        table_ids = []

        for table in tables:
            table_id = str(uuid4())
            table_name = f"{_TABLE_REFERENCE_PREFIX}{table_index}"
            table_docs.append(TableContent(
                id=table_id,
                name=table_name,
                file_id=file_id,
                page_number=page_number,
                csv_data=table
            ))
            table_ids.append(table_id)
            table_index += 1

        image_ids = []
        for image in page.images:
            image_url = maybe_compress_base64_image(image.image_base64)
            image_id = str(uuid4())
            image_docs.append(ImageContent(
                id=image_id,
                file_id=file_id,
                page_number=page_number,
                image_url=image_url,
                name=image.id,
                bounding_boxes=BoundingBox(
                    height=page.dimensions.height,
                    width=page.dimensions.width,
                    top_left_x=image.top_left_x,
                    top_left_y=image.top_left_y,
                    bottom_right_x=image.bottom_right_x,
                    bottom_right_y=image.bottom_right_y
                )
            ))
            image_ids.append(image_id)

            context = extract_context_around_image_id(markdown, image.id)
            context = context.get("context_before") + "\n" + context.get("context_after")
            image_tasks.append(
                convert_image_to_structured_output(image_url, context, llm_model=llm_model)
            )

        text_docs.append(TextContent(
            id=str(uuid4()),
            file_id=file_id,
            page_number=page_number,
            markdown=modified_markdown,
            table_ids=table_ids,
            image_ids=image_ids
        ))

    return {
        "text": text_docs,
        "tables": table_docs,
        "images": image_docs,
        "image_tasks": image_tasks
    }

async def build_bulk_operations(texts, tables, images):
    """Write bulk data to Firebase."""
    print("Writing bulk data to Firebase")
    try:
        ops = [{
            "type": "create",
            "collection": file_data_collection,
            "document_id": doc.id,
            "data": doc.to_dict()
        } for doc in images + tables + texts]
        await firebase_manager.batch_operation(ops)
    except Exception:
        traceback.print_exc()
        raise Exception("Failed during bulk operation")

# def enrich_markdown_with_image(img: ImageContent, text_docs: List[TextContent]):
#     """Enrich markdown content with image information."""
#     for text_doc in text_docs:
#         if img.id in text_doc.image_ids:
#             img_md = f"![{img.name}]({img.name})\n{img.markdown}"
#             if img.structured_output.get('chart_data'):
#                 chart_json = json.dumps(img.structured_output.get('chart_data'), indent=2)
#                 img_md += f"\n\n```json\n{chart_json}\n```"
#             if img.structured_output.get('table_data'):
#                 table_json = json.dumps(img.structured_output.get('table_data'), indent=2)
#                 img_md += f"\n\n```json\n{table_json}\n```"
#             text_doc.markdown = text_doc.markdown.replace(f"![{img.name}]({img.name})", img_md)
#   
#           break
def chart_data_to_summary(chart_data: List[dict]) -> str:
    """Convert structured chart data (as dicts) into human-readable summary."""
    summaries = []
    for chart in chart_data:
        title = f"**{chart.get('title')}**" if chart.get("title") else "Chart Data"
        chart_summary = [f"{title}:"]
        for series in chart.get("series", []):
            if series.get("name"):
                chart_summary.append(f"- {series['name']}:")
            for dp in series.get("data", []):
                label = dp.get("label", "Unknown")
                value = dp.get("value", "N/A")
                chart_summary.append(f"  - {label}: {value}")
        summaries.append("\n".join(chart_summary))
    return "\n\n".join(summaries)



def table_data_to_summary(table_data: List[dict]) -> str:
    """Convert structured table data (as list of dicts) into human-readable summary."""
    summaries = []
    for row in table_data:
        row_summary = ", ".join(f"{k}: {v}" for k, v in row.items())
        summaries.append(f"- {row_summary}")
    return "**Table Data:**\n" + "\n".join(summaries)



def enrich_markdown_with_image(img: ImageContent, text_docs: List[TextContent]):
    """Enrich markdown content with human-readable image summary."""
    for text_doc in text_docs:
        if img.id in text_doc.image_ids:
            # Insert image reference
            img_md = f"![{img.name}]({img.name})"
            
            # Add image markdown summary
            if img.markdown:
                img_md += f"\n{img.markdown}"

            # Add structured chart data (human-readable, not JSON)
            if img.structured_output.get('chart_data'):
                chart_summary = chart_data_to_summary(img.structured_output['chart_data'])
                img_md += f"\n\n{chart_summary}"

            # Add table data summary
            if img.structured_output.get('table_data'):
                table_summary = table_data_to_summary(img.structured_output['table_data'])
                img_md += f"\n\n{table_summary}"

            # Replace placeholder with enriched version
            text_doc.markdown = text_doc.markdown.replace(f"![{img.name}]({img.name})", img_md)
            break

async def update_progress(file_id: str, progress: float, status: FileStatus, channel_id: str = None, data: dict = {}):
    """Update processing progress."""
    print(f"Updating progress for file {file_id} to {progress} with status {status}")
    if channel_id and data:
        data[file_id].update({
            "progress": progress,
            "status": status.value
        })
        await ws_manager.send(channel_id=channel_id, event="files_processing_progress", data=data)

async def process_single_file(
        file_id: str, 
        file_url: str, 
        batch_size: int = 10, 
        analyze_image: bool = True, 
        llm_model_for_images: LLMModel = LLMModel.GEMINI_2_FLASH,
        channel_id: str = None,
        data: dict = None
        ):
    """Process a single file using the specified OCR provider."""
    try:
        response = await mistral_client.ocr.process_async(
            model="mistral-ocr-latest",
            document={
                "type": "document_url", 
                "document_url": file_url
                },
            include_image_base64=True
        )

        pages = response.pages
        num_pages = len(pages)
        
        for i in range(0, num_pages, batch_size):
            try:
                batch_pages = pages[i:i + batch_size]
                batch_results = process_batch_pages(batch_pages, file_id, llm_model_for_images)

                if analyze_image and batch_results["image_tasks"]:
                    try:
                        analyzed_images = await asyncio.gather(*batch_results["image_tasks"], return_exceptions=True)
                        for img, result in zip(batch_results["images"], analyzed_images):
                            if isinstance(result, Exception):
                                print(f"Image analysis failed: {result}")
                                continue
                            if result and result.image_summary:
                                img.markdown = result.image_summary
                                img.structured_output = result.image_data.model_dump()
                                enrich_markdown_with_image(img, batch_results["text"])
                    except Exception:
                        traceback.print_exc()

                await build_bulk_operations(batch_results["text"], batch_results["tables"], batch_results["images"])
                await update_progress(file_id, round((min(i+batch_size, num_pages)/ num_pages)*100,2), FileStatus.PROCESSING, channel_id, data)
            except Exception as e:
                traceback.print_exc()
                print(f"Error processing file {file_id} in batch {i}: {e}")

        await update_progress(file_id, 100, FileStatus.PARSED, channel_id, data)
        return file_id
    except Exception as e:
        traceback.print_exc()
        await update_progress(file_id, round((min(i+batch_size, num_pages)/ num_pages)*100,2), FileStatus.FAILED, channel_id, data)
        raise Exception(f"Error processing file {file_id}: {e}")

        


async def enrich_files_with_markdown(files_ids):
    """Enrich files with markdown content."""
    BATCH_SIZE = 10  # Adjust based on Firestore limits
    async def fetch_file_with_markdown(file):
        """Fetch markdown pages for a single file and enrich it."""
        pages = await firebase_manager.query_collection(
            file_data_collection,
            [("file_id", "==", file.get("id")), ("type", "==", "text")],
            order_by="page_number"
        )
        file["markdown"] = {
            f"page_{page.get('page_number')}": page.get("markdown") for page in pages
        }
        return file

    files = await firebase_manager.get_documents(file_collection, list_ids=files_ids)
    enriched_files = []
    for i in range(0, len(files), BATCH_SIZE):
        batch = files[i:i + BATCH_SIZE]
        enriched_batch = await asyncio.gather(*(fetch_file_with_markdown(file) for file in batch))
        enriched_files.extend(enriched_batch)
    return enriched_files

async def vectorize_files_batch(files_ids: List[str]):
    """Vectorize a batch of files."""
    if not files_ids:
        return 
    
    vectorization_service = VectorizationService()      
    async def _vectorize_file(file: dict):
        try:
           
            markdown = file.get("markdown")
            metadata = {
                "file_id": file.get("id", ""),
                "dossier_id": file.get("dossier_id", ""),
                "project_id": file.get("project_id", ""),
                "user_id": file.get("user_id", ""),
                "created_at": file.get("created_at", ""),
                # "updated_at": file.get("updated_at", ""),
                "type": file.get("type", "")
            }

            if markdown:
                chunks = vectorization_service.hybrid_chunk_markdown_with_headers(markdown, max_tokens=500, add_image_metadata=True, add_table_metadata=True)
                await vectorization_service.embed_and_upload(
                    chunks=chunks, metadata=metadata, batch_size=50
                )
        except Exception as e:
            traceback.print_exc()
            print(f"Error vectorizing file {file.get('name')}: {e}")
    
    files = await enrich_files_with_markdown(files_ids)
    print(f"Vectorizing files: {files_ids}")
    await asyncio.gather(*(_vectorize_file(file) for file in files))    
    return {"success": True}

async def process_files(
        file_ids: List[str], 
        llm_model: LLMModel = LLMModel.GEMINI_2_FLASH, 
        files_batch_size: int = 5, 
        pages_batch: int = 10, 
        analyze_image: bool = True,
        channel_id: str = None,
        data: dict = {},
        vectorize: bool = True
        ):
    """Process multiple files using the specified OCR provider."""
    print("Starting file processing")
    try:
        if not file_ids:
            return
        files = await firebase_manager.get_documents(file_collection, list_ids=file_ids)
        for i in range(0, len(files), files_batch_size):
            current_batch = files[i:i + files_batch_size]
            results = await asyncio.gather(*[
                process_single_file(
                    file.get("id"),
                    file.get("url"),
                    batch_size=pages_batch,
                    analyze_image=analyze_image,
                    llm_model_for_images=llm_model,
                    channel_id=channel_id,
                    data=data
                ) for file in current_batch
            ], return_exceptions=True)
            
            processed_files = []
            
            for result in results:
                if isinstance(result, Exception):
                    print(f"File failed: {result}")
                else:
                    processed_files.append(result)
                    
            if vectorize:
                await vectorize_files_batch(processed_files)

            ops =  [
                {
                    "type": "update",
                    "collection": file_collection,
                    "document_id": file,
                    "data": {"status": FileStatus.PARSED.value, "progress": 100}
                } for file in processed_files
            ]
            await firebase_manager.batch_operation(ops)
        return file_ids
    except Exception:
        traceback.print_exc()
        raise Exception("Fatal error during multi-file processing")
