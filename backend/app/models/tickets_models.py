from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Union
from enum import Enum


class Reference(BaseModel):
    """
    Schema for reference
    """

    section: str
    # page: str

class TicketTypeEnum(str, Enum):
    """
    Enum defining the types of tickets with their descriptions
    """
    requirement = "requirement"  # Requirements that need to be addressed in the proposal
    question = "question"       # Questions that need to be answered in the proposal
    issue = "issue"            # Issues or concerns that need to be addressed
    submission = "submission"   # Instructions for proposal formatting, delivery, etc.
    pricing = "pricing"        # Details or structure of pricing the client expects

    @classmethod
    def get_description(cls, type_value: str) -> str:
        descriptions = {
            cls.requirement: "Technical, functional, or business requirements that need to be addressed in the proposal",
            cls.question: "Specific questions from the RFP that need to be answered in the proposal",
            cls.issue: "Problems, concerns, or challenges that need to be addressed or mitigated",
            cls.submission: "Instructions for proposal formatting, delivery method, submission deadlines, etc.",
            cls.pricing: "Details about pricing structure, budget constraints, or cost breakdown requirements"
        }
        return descriptions.get(type_value, "")

TicketType = Literal["requirement", "question", "evaluation", "issue", "submission", "pricing"]

class LLMTicket(BaseModel):
    """
    Schema for ticket
    """

    title: str = Field(..., description="Title of the ticket")
    description: str = Field(
        ..., 
        description="Verbatim or near-verbatim excerpt from the RFP that expresses the requirement, question, or issue. Do NOT paraphrase or summarize unless absolutely necessary."
    )
    type: TicketType = Field(
        ..., 
        description="The type of ticket that best categorizes this item:\n"
                   "- requirement: Technical, functional, or business requirements to address\n"
                   "- question: Specific questions from the RFP to answer\n"
                   "- issue: Problems, concerns, or challenges to address\n"
                   "- evaluation: Evaluation criteria for the proposal\n"
                   "- submission: Instructions for proposal formatting and delivery\n"
                   "- pricing: Details about pricing structure and requirements"
    )
    weight: Optional[float] = Field(
        None,
        description="If the ticket relates to evaluation criteria, this is the weight or score percentage allocated to it (range 0-100). If unspecified, consider it evenly weighted or unknown.",
    )
    reference: Reference


class Contact(BaseModel):
    """
    Schema for stakeholder contact information
    """

    name: str
    title: str
    email: str


class Milestone(BaseModel):
    date: str
    milestone: str


class Tickets(BaseModel):
    """
    Schema for RFP requirements output
    """

    # summary: str
    timeline: Optional[List[Milestone]]
    stakeholders: Optional[List[Contact]]
    tickets: Optional[List[LLMTicket]]


class Context(BaseModel):
    summary: str
    timeline: List[Milestone]
    stakeholders: List[Contact]