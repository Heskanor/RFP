from enum import Enum
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List, Any, Optional, Dict, Literal, Union

from pydantic import BaseModel as PydanticBaseModel, Field
from dataclasses import asdict, is_dataclass
from app.config.llm_factory import LLMModel

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


class RFPStatus(str, Enum):
    CREATED = "created"
    PROCESSING = "processing"
    GENERATED = "generated"


class ProjectStatus(str, Enum):
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"
    FAILED = "failed"
    ARCHIVED = "archived"


class Collections(str, Enum):
    PROJECT = "Projects"
    DOSSIER = "Dossiers"
    FILE = "Files"
    TICKET = "Tickets"
    THREAD = "Threads"
    USER = "Users"
    CURATED_QA = "CuratedQA"
    WEB_PAGE = "WebPages"
    CONNECTORS = "connectors"
    UPLOADED_DOCS = "UploadedDocs"

    KNOWLEDGE_HUB = "KnowledgeHub"
    LABELS = "Labels"
    FILE_DATA = "FilesData"



@dataclass
class User(BaseModel):
    email: str = field(default="")
    name: str = field(default="")
    full_name: str = field(default="")
    title: str = field(default="")
    company_name: str = field(default="")
    company_url: str = field(default="")
    company_description: str = field(default="")
    is_active: bool = field(default=True)
    is_admin: bool = field(default=False)
    image_url: str = field(default="")
    llm_model: Optional[LLMModel] = field(default=LLMModel.GPT_4O_MINI)


@dataclass
class Project(BaseModel):
    user_id: str = field(default="")
    title: str = field(default="")
    description: str = field(default="")
    status: ProjectStatus = field(default=ProjectStatus.IN_PROGRESS)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Dossier(BaseModel):
    user_id: str = field(default="")
    # project_id: str = field(default="")
    type: Literal["uploaded_documents", "web_search", "custom_connectors", "curated_qa"] = field(default="uploaded_documents")
    subtype: str = field(default="")
    labels: List[str] = field(default_factory=list)
    title: str = field(default="")
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_open: bool = field(default=True)

@dataclass
class Label(BaseModel):
    user_id: str = field(default="")
    name: Optional[str] = field(default=None)
    description: Optional[str] = field(default=None)
    color: Optional[str] = field(default=None)
    parentLabelId: Optional[str] = field(default=None)
   

@dataclass
class UploadedDocuments(BaseModel):
    user_id: str = field(default="")
    name: Optional[str] = field(default="")
    type: Optional[str] = field(default="")  # pdf, image, etc.
    labelIds: Optional[List[str]] = field(default_factory=list)
    metadata: Optional[dict] = field(default_factory=dict)  # optional additional info

@dataclass
class CuratedQA(BaseModel):
    user_id: str = field(default="")
    question: Optional[str] = field(default=None)
    answer: Optional[str] = field(default=None)
    labelIds: Optional[List[str]] = field(default_factory=list)
    sourceFileId: Optional[str] = field(default=None)
    is_open: bool = field(default=True)

@dataclass
class WebPage(BaseModel):
    user_id: str = field(default="")
    url: str = field(default="")
    content: str = field(default="")
    title: str = field(default="")
    description: str = field(default="")
    labelIds: List[str] = field(default_factory=list)
    is_open: bool = field(default=True)

@dataclass
class Connector(BaseModel):
    user_id: str = field(default="")
    name: str = field(default="")
    description: str = field(default="")
    type: str = field(default="")
    config: Dict[str, Any] = field(default_factory=dict)
    status: str = field(default="")
    is_open: bool = field(default=True)

class BaseKnowledgeItem(BaseModel):
    user_id: str = field(default="")
    labelIds: Optional[List[str]] = field(default_factory=list)
    type: Literal["uploaded_file", "curated_qa", "web_page", "custom_connector"]
    subtype: Optional[str] = field(default=None)


# -------------------
# Content Per Type
# -------------------

class UploadedFileContent(PydanticBaseModel):
    id: str                     # FK to File collection
    name: str
    type: str = "pdf"
    size: int = 0
    url: Optional[str] = None
   

class CuratedQAContent(PydanticBaseModel):
    file_id: Optional[str] = None
    file_name: Optional[str] = None
    page_number: Optional[List[str]] = None
    question: str
    answer: str
    source_type: Optional[Literal["text", "table", "image"]] = None
    reference: Optional[Dict] = {}


class WebPageContent(PydanticBaseModel):
    url: str
    title: Optional[str] = None
    scraped_text: Optional[str] = None
    last_scraped: Optional[int] = None


class CustomConnectorContent(PydanticBaseModel):
    provider: Literal["google_drive", "dropbox", "notion", "custom"]
    config: Dict[str, str]
    linked_file_ids: List[str] = Field(default_factory=list)

class EmptyContent(PydanticBaseModel):
    pass


# -------------------
# Knowledge Item Main
# -------------------
@dataclass
class KnowledgeItem(BaseModel):
    user_id: str = field(default="")
    labelIds: Optional[List[str]] = field(default_factory=list)
    type: Literal["uploaded_documents", "curated_qa", "web_page", "custom_connector"] = field(default="uploaded_documents")
    subtype: Optional[str] = field(default=None)
    content: Optional[Union[
        UploadedFileContent,
        CuratedQAContent,
        WebPageContent,
        CustomConnectorContent,
        EmptyContent
    ]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = super().to_dict()
        if isinstance(self.content, PydanticBaseModel):
            data['content'] = self.content.model_dump()
        elif isinstance(self.content, dict):
            data['content'] = self.content
        else:
            data['content'] = None
        return data

typeMapper = {
    "uploaded_documents": "Uploaded Documents",
    "company": "Company Documents",
    "rfps": "Previous RFPs",
    "curated_qa": "Curated QA",
    "web_page": "Web Page",
    "custom_connector": "Custom Connector"
}


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
    provider: Literal["docling", "mistral"] = field(default="mistral")  # Provider of the file
    progress: int = field(default=0)  # Progress percentage of the parsing
    markdown: Optional[Dict[str, str]] = field(
        default=None
    )  # Markdown content for the file



@dataclass
class FileSource(PydanticBaseModel):
    paragraph_id: str = field(default="")
    text: str = field(default="")
    file_id: str = field(default="")
    pages: List[int] = field(default_factory=list)
    url: str = field(default="")


@dataclass
class Sources(PydanticBaseModel):
    highlights: list = field(default=list)
    sources: List[FileSource]


@dataclass
class AnswerWithSources(PydanticBaseModel):
    markdown: str = field(default="")
    references: Dict[str, Sources] = field(default_factory=dict)


@dataclass
class Ticket(BaseModel):
    project_id: str = field(default="")  # ID of the associated dossier
    type: str = Literal["requirement", "question", "issue"]
    status: str = Literal["new", "progress", "inreview", "closed"]
    assignee: str = field(default="")  # User ID of the assignee
    reviewer: str = field(default="")  # User ID of the reviewer
    page_nums: List[int] = field(
        default_factory=list
    )  # List of page numbers related to the ticket
    title: str = field(default="")  # Title of the ticket
    description: str = field(default="")  # Description of the ticket
    answer: Dict[str, Any] = field(default_factory=dict)  # Answer to the ticket
    explanation: List[str] = field(
        default_factory=list
    )  # List of explanations related to the ticket
    reference: dict = field(default_factory=dict)  # Reference of the ticket
    weight: Union[float, None] = field(default=None)  # Weight of the ticket    


@dataclass
class Thread(BaseModel):
    ticket_id: str = field(default="")  # ID of the associated ticket
    project_id: str = field(default="")  # ID of the associated project
    user_id: str = field(default="")  # ID of the user who uploaded the file
    title: str = field(default="")  # Title of the thread
    thread: List[Dict[str, Any]] = field(default_factory=list)
    is_project_thread: bool = field(default=False)
    is_web_search: bool = field(default=False)
    file_ids: List[dict] = field(default_factory=list)


