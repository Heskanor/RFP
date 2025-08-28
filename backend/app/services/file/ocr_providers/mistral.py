from typing import Dict, List, Any, Optional
import asyncio
from app.config.mistral import mistral_client
from app.models.models import FileStatus
from app.services.websocket_manager import ws_manager
from .base import OCRProvider

class MistralOCRProvider(OCRProvider):
    """Mistral OCR provider implementation"""
    
    def __init__(self, ocr_model: str = "mistral-ocr-latest"):
        self.ocr_model = ocr_model
    
    def parse_response(
        self,
        raw: Any,
        file_id: str,
        dossier_id: str,
        project_id: str,
        provider: str = "mistral"
    ) -> Dict[str, Any]:
        """Parse the Mistral OCR response into a structured format"""
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
    
    async def process_single_file(
        self,
        file: Dict[str, Any],
        channel_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a single file using Mistral OCR"""
        try:
            mistral_response = await mistral_client.ocr.process_async(
                model=self.ocr_model,
                document={
                    "type": "document_url",
                    "document_url": file["url"]
                },
                include_image_base64=False
            )

            document = self.parse_response(
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
            print(f"Error processing file {file.get('id')}: {str(e)}")
            raise
    
    async def process_batch(
        self,
        files: List[Dict[str, Any]],
        channel_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Process multiple files using Mistral OCR in parallel"""
        tasks = [
            self.process_single_file(file, channel_id=channel_id, data=data)
            for file in files
        ]
        return await asyncio.gather(*tasks)