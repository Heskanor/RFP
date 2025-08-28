from typing import Dict, List, Optional
from app.config.mistral import mistral_client
# from app.models.models import DocumentFile, DocumentPage, PageImage, BoundingBox, PageDimensions, StructuredDocument, ProcessorMetadata, FileStatus
from app.models.models import File, FileStatus
import asyncio
from app.services.websocket_manager import ws_manager

def parse_mistral_response(
    raw: dict,
    *,
    file_id: str,
    dossier_id: str,
    project_id: str,
    provider: str = "mistral"
) -> Dict[str, any]:
    """
    Parse the Mistral OCR response into a structured format.
    
    Args:
        raw: Raw response from Mistral OCR
        file_id: ID of the processed file
        dossier_id: ID of the dossier
        project_id: ID of the project
        provider: Provider name (default: "mistral")
    
    Returns:
        Dict containing parsed file information
    """
    file_markdown = {
        f"page_{page.index+1}": page.markdown 
        for page in raw.pages
    }

    return {
        "id": file_id,
        "dossier_id": dossier_id,
        "project_id": project_id,
        "status": FileStatus.PARSED.value,
        "progress": 100,
        "provider": provider,
        "markdown": file_markdown
    }


async def ocr_mistral_single_file(
    file: Dict[str, any],
    ocr_model: str = "mistral-ocr-latest",
    channel_id: Optional[str] = None,
    data: Optional[Dict[str, any]] = None
) -> Dict[str, any]:
    """
    Process a single file using Mistral OCR asynchronously.
    
    Args:
        file: File information dictionary
        ocr_model: OCR model to use
        channel_id: WebSocket channel ID for progress updates
        data: Progress data dictionary
    
    Returns:
        Processed document information
    """
    try:
        mistral_response = await mistral_client.ocr.process_async(
            model=ocr_model,
            document={
                "type": "document_url",
                "document_url": file["url"]
            },
            include_image_base64=False
        )

        document = parse_mistral_response(
            raw=mistral_response,
            file_id=file.get("id"),
            dossier_id=file.get("dossier_id", ""),
            project_id=file.get("project_id", "")
        )

        if channel_id and data:
            file_id = file.get("id")
            if file_id in data:
                data[file_id].update({
                    "progress": 100,
                    "status": FileStatus.PARSED.value
                })
                await ws_manager.send(
                    channel_id=channel_id,
                    event="files_processing_progress",
                    data=data
                )

        return document
    except Exception as e:
        # Log the error and re-raise
        print(f"Error processing file {file.get('id')}: {str(e)}")
        raise


async def ocr_mistral_batch(
    files: List[Dict[str, any]],
    channel_id: Optional[str] = None,
    data: Optional[Dict[str, any]] = None
) -> List[Dict[str, any]]:
    """
    Process multiple files using Mistral OCR in parallel.
    
    Args:
        files: List of file information dictionaries
        channel_id: WebSocket channel ID for progress updates
        data: Progress data dictionary
    
    Returns:
        List of processed document information
    """
    tasks = [
        ocr_mistral_single_file(file, channel_id=channel_id, data=data)
        for file in files
    ]
    return await asyncio.gather(*tasks)




