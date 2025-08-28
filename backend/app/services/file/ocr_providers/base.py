from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.models.models import FileStatus

class OCRProvider(ABC):
    """Base class for OCR providers"""
    
    @abstractmethod
    async def process_single_file(
        self,
        file: Dict[str, Any],
        channel_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a single file and return the results"""
        pass
    
    @abstractmethod
    async def process_batch(
        self,
        files: List[Dict[str, Any]],
        channel_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Process multiple files in batch and return the results"""
        pass
    
    @abstractmethod
    def parse_response(
        self,
        raw: Any,
        file_id: str,
        dossier_id: str,
        project_id: str,
        provider: str
    ) -> Dict[str, Any]:
        """Parse the raw OCR response into a structured format"""
        pass 