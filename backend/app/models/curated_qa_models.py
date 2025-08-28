from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Union
from enum import Enum


SourceTypes = Literal["text", "table", "image"]


class Reference(BaseModel):
    """
    Schema for reference
    """

    section: str

class CuratedQA(BaseModel):
    question: str = Field(..., description="Question to be answered")
    answer: str = Field(..., description="Answer to the question")
    # page_number: str = Field(..., description="Page sources of the Curated Q&A")
    source_type: SourceTypes = Field(..., description="Type of the source")
    reference: Reference = Field(..., description="Section Reference to the source")


class LLMCuratedQAs(BaseModel):
    curated_qas : List[CuratedQA]