from typing import Optional, List, Dict, Literal
from dataclasses import dataclass, field, asdict
from pydantic import BaseModel

from datetime import datetime
from enum import Enum


@dataclass
class BaseModel:
    id: str
    created_at: Optional[int] = int(datetime.now().timestamp())
    updated_at: Optional[int] = int(datetime.now().timestamp())

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}
    
class FileStatus(str, Enum):
    CREATED = "created"
    PROCESSING = "processing"
    PARSED = "parsed"
    FAILED = "failed"

@dataclass
class File(BaseModel):
    user_id: str = field(default="")  # ID of the user who uploaded the file
    project_id: str = field(default="")  # ID of the associated project
    dossier_id: str = field(default="")

    is_knowledge_hub: bool = field(default=False)
    is_supporting_file: bool = field(default=False)
    is_proposal_draft: bool = field(default=False)
    is_used: bool = field(
        default=False
    )  # Indicates if file is used in project (retrieved from pinecone)
   
    name: str = field(default="")  # Name of the file
    type: str = field(default="pdf")  # Type of the file (e.g., pdf)
    url: Optional[str] = field(default=None)  # URL to access the file
    size: int = field(default=0)  # Size of the file
    status: FileStatus = field(
        default=FileStatus.CREATED
    )  # Current status of the file, could be different status: created, processing, parsed
    provider: Literal["docling", "mistral"] = field(default="docling")  # Provider of the file
    progress: int = field(default=0)  # Progress percentage of the parsing

    
@dataclass
class BoundingBox:
    height: int
    width: int
    top_left_x: int
    top_left_y: int
    bottom_right_x: int
    bottom_right_y: int

# text content 
@dataclass  
class TextContent(BaseModel):
    file_id: str = field(default="")
    page_number: int = field(default=0)
    type: Literal["text"] = field(default="text")
    
    text: Optional[str] = field(default=None)
    table_ids: List[str] = field(default_factory=list)  # References to TableContent
    image_ids: List[str] = field(default_factory=list)  # References to ImageContent

    markdown: Optional[str] = field(default="")  # Optional rendered markdown if needed

# table content 
@dataclass
class TableContent(BaseModel):
    file_id: str = field(default="")
    name: str = field(default="")
    page_number: int = field(default=0)
    type: Literal["table"] = field(default="table")
    
    csv_data: Optional[List[Dict]] = field(default=None)
    markdown: Optional[str] = field(default=None)
    image_url: Optional[str] = field(default=None)
    bounding_boxes: Optional[BoundingBox] = field(default=None)

# image content 
@dataclass
class ImageContent(BaseModel):
    file_id: str = field(default="") 
    name: str = field(default="")   
    page_number: int = field(default=0)
    type: Literal["image"] = field(default="image")

    image_url: str = field(default="")
    markdown: Optional[str] = field(default=None)
    structured_output: Optional[Dict] = field(default=None)  # OCR output, diagram data, etc.
    bounding_boxes: Optional[BoundingBox] = field(default=None)