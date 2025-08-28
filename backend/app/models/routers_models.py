from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class ProjectResponse(BaseModel):
    projects: List[Dict[str, Any]]
    # dossiers_hub: List[Dict[str, Any]]


class ProjectDataResponse(BaseModel):
    id: str
    title: str
    description: str
    files: List[Dict[str, Any]]
    supporting_files: List[Dict[str, Any]]
    exported_files: List[Dict[str, Any]]
    # dossiers_hub: List[Dict[str, Any]]
    linked_project: List[Dict[str, Any]]
    status: str
    details: Dict[str, Any]


class MagicColumnDataResponse(BaseModel):
    data: Dict[str, Any]


class MessageResponse(BaseModel):
    message: str


class ComputeMagicColumnResponse(BaseModel):
    message: str
    values: Dict[str, Any]


class ExplanationResponse(BaseModel):
    highlights: List[Dict[str, Any]]


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: int
    explanation: Optional[Dict[str, Any]] = {}


class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessage]


class AssistantAnswer(BaseModel):
    answer: str


class ChatRequest(BaseModel):
    id: str
    prompt: str
    timestamp: Optional[int] = None


class DossierMetadataResponse(BaseModel):
    dossier_id: str
    title: str
    files: List[Dict[str, Any]]


class FileResponse(BaseModel):
    id: str
    name: str
    type: str
    url: str
    markdown: Optional[str] = None


class InsightCreate(BaseModel):
    title: str
    insight: str
    explanation: List[Dict[str, Any]]


class InsightUpdate(BaseModel):
    title: Optional[str] = None
    insight: Optional[str] = None


class RFPRequest(BaseModel):
    rfp_md: str


class Answer(BaseModel):
    html_text: str


class MessageRequest(BaseModel):
    role: str
    content: str
    timestamp: int


class ThreadRequest(BaseModel):
    is_web_search: bool
    file_ids: List[str]
    messages: List[MessageRequest]


class ThreadResponse(BaseModel):
    id: str
    title: Optional[str] = "Untitled Thread"
    user_id: str
    project_id: str
    messages: List[dict]
    is_web_search: bool
    file_ids: List[str]
    created_at: int
    updated_at: int


class ExportParams(BaseModel):
    summary: bool
    stakeholders: bool
    timeline: bool
    tickets: bool
    filteredTickets: list = []
    
