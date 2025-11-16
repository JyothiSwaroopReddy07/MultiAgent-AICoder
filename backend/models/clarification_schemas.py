"""
Clarification and interactive question schemas
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class QuestionType(str, Enum):
    """Types of clarification questions"""
    MULTIPLE_CHOICE = "multiple_choice"
    TEXT_INPUT = "text_input"
    YES_NO = "yes_no"
    NUMERIC = "numeric"
    SCALE = "scale"  # 1-10 scale


class ClarificationQuestion(BaseModel):
    """A clarification question to ask the user"""
    question_id: str = Field(..., description="Unique question ID")
    question: str = Field(..., description="The question to ask")
    question_type: QuestionType = Field(..., description="Type of question")
    context: str = Field(..., description="Why this question is being asked")
    options: Optional[List[str]] = Field(None, description="Options for multiple choice")
    default_value: Optional[str] = Field(None, description="Default/suggested answer")
    required: bool = Field(default=True, description="Is this question required?")
    category: str = Field(..., description="Category (requirements, tech_stack, scalability, etc)")


class ClarificationAnswer(BaseModel):
    """User's answer to a clarification question"""
    question_id: str = Field(..., description="Question ID being answered")
    answer: Any = Field(..., description="User's answer")


class ClarificationRequest(BaseModel):
    """Request for clarifications from user"""
    request_id: str = Field(..., description="Generation request ID")
    phase: str = Field(..., description="Phase requesting clarification")
    agent: str = Field(..., description="Agent requesting clarification")
    reason: str = Field(..., description="Reason for requesting clarification")
    questions: List[ClarificationQuestion] = Field(..., description="Questions to ask")
    can_skip: bool = Field(default=False, description="Can user skip these questions?")


class ClarificationResponse(BaseModel):
    """User's response to clarification request"""
    request_id: str = Field(..., description="Generation request ID")
    answers: List[ClarificationAnswer] = Field(..., description="User's answers")
    skipped: bool = Field(default=False, description="Did user skip?")


class TechStackDecision(BaseModel):
    """Tech stack decision with justification"""
    reasoning: Optional[str] = Field(None, description="Step-by-step reasoning process")
    language: str = Field(..., description="Primary programming language")
    language_justification: str = Field(..., description="Why this language")

    framework: Optional[str] = Field(None, description="Framework choice")
    framework_justification: Optional[str] = Field(None, description="Why this framework")

    database: str = Field(..., description="Database choice")
    database_justification: str = Field(..., description="Why this database")

    architecture_pattern: str = Field(..., description="Architecture pattern (monolith/microservices/etc)")
    architecture_justification: str = Field(..., description="Why this architecture")

    additional_technologies: Dict[str, str] = Field(default={}, description="Other tech choices with justifications")

    scalability_approach: str = Field(..., description="How to handle scalability")
    availability_approach: str = Field(..., description="How to ensure availability")

    trade_offs: List[str] = Field(..., description="Trade-offs of these choices")
    alternatives_considered: List[str] = Field(default=[], description="Alternatives that were considered")
