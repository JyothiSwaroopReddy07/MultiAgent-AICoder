"""
Conversation State Models for Chat-Based Code Generation
Manages multi-turn conversations with feature planning and code modification
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class ConversationPhase(str, Enum):
    """Phases of conversation"""
    INITIAL = "initial"
    FEATURE_PLANNING = "feature_planning"
    FEATURE_REFINEMENT = "feature_refinement"
    FEATURES_APPROVED = "features_approved"
    IMPLEMENTATION = "implementation"
    CODE_GENERATED = "code_generated"
    MODIFICATION = "modification"
    COMPLETED = "completed"


class MessageRole(str, Enum):
    """Role of message sender"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationMessage(BaseModel):
    """Single message in conversation"""
    id: str
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


class Feature(BaseModel):
    """Planned feature for implementation"""
    id: str
    title: str
    description: str
    priority: Literal["high", "medium", "low"] = "medium"
    category: str  # e.g., "authentication", "data-management", "ui"
    technical_details: Optional[str] = None
    approved: bool = False
    
    @field_validator('priority', mode='before')
    @classmethod
    def normalize_priority(cls, v):
        """Normalize priority to valid values"""
        if not v or not isinstance(v, str):
            return "medium"
        
        v_lower = str(v).lower().strip()
        
        # Handle empty strings, null, none
        if not v_lower or v_lower in ["null", "none", ""]:
            return "medium"
        
        # Map invalid values to valid ones
        priority_map = {
            "high": "high",
            "medium": "medium",
            "low": "low",
            "critical": "high",
            "important": "high",
            "normal": "medium",
            "minor": "low",
            "optional": "low"
        }
        
        return priority_map.get(v_lower, "medium")


class FeaturePlan(BaseModel):
    """Complete feature plan"""
    features: List[Feature]
    tech_stack: Dict[str, str]
    database_type: Literal["postgresql", "mongodb", "auto"] = "auto"
    estimated_complexity: Literal["simple", "medium", "complex"] = "medium"
    notes: Optional[str] = None
    
    @field_validator('database_type', mode='before')
    @classmethod
    def normalize_database_type(cls, v):
        """Normalize database_type to valid values"""
        if not v or not isinstance(v, str):
            return "auto"
        
        v_lower = str(v).lower().strip()
        
        # Handle empty strings, null, none
        if not v_lower or v_lower in ["null", "none", "", "undefined"]:
            return "auto"
        
        # Map variations to valid values
        if "postgres" in v_lower or "psql" in v_lower or v_lower == "sql":
            return "postgresql"
        elif "mongo" in v_lower:
            return "mongodb"
        elif v_lower in ["postgresql", "mongodb", "auto"]:
            return v_lower
        else:
            # Default to auto for any unclear cases
            return "auto"
    
    @field_validator('estimated_complexity', mode='before')
    @classmethod
    def normalize_complexity(cls, v):
        """Normalize estimated_complexity to valid values"""
        if not v or not isinstance(v, str):
            return "medium"
        
        v_lower = str(v).lower().strip()
        
        # Handle empty strings, null, none
        if not v_lower or v_lower in ["null", "none", "", "undefined"]:
            return "medium"
        
        # Map invalid values to valid ones
        complexity_map = {
            "simple": "simple",
            "medium": "medium",
            "complex": "complex",
            "low": "simple",      # Map 'low' to 'simple'
            "high": "complex",
            "easy": "simple",
            "moderate": "medium",
            "difficult": "complex",
            "hard": "complex",
            "basic": "simple",
            "advanced": "complex"
        }
        
        return complexity_map.get(v_lower, "medium")


class CodeModificationRequest(BaseModel):
    """Request to modify generated code"""
    modification_type: Literal["add", "modify", "remove", "fix"]
    description: str
    target_files: Optional[List[str]] = None
    specific_changes: Optional[str] = None


class GeneratedCode(BaseModel):
    """Generated code files"""
    files: List[Dict[str, Any]]
    file_structure: Dict[str, List[str]]
    setup_instructions: List[str]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ConversationState(BaseModel):
    """Complete conversation state"""
    conversation_id: str
    phase: ConversationPhase = ConversationPhase.INITIAL
    messages: List[ConversationMessage] = []
    
    # Problem statement
    problem_statement: Optional[str] = None
    
    # Feature planning
    proposed_features: Optional[FeaturePlan] = None
    approved_features: Optional[FeaturePlan] = None
    
    # Implementation
    generated_code: Optional[GeneratedCode] = None
    
    # Modification tracking
    modification_history: List[CodeModificationRequest] = []
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Context for agents
    context: Dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    """User chat message request"""
    conversation_id: Optional[str] = None
    message: str
    action: Optional[Literal["plan", "approve", "implement", "modify"]] = None


class ChatResponse(BaseModel):
    """Response to user chat"""
    conversation_id: str
    phase: ConversationPhase
    message: str
    features: Optional[List[Feature]] = None
    code_files: Optional[List[Dict[str, Any]]] = None
    awaiting_user_action: bool = False
    suggested_actions: List[str] = []


class StreamEvent(BaseModel):
    """Server-sent event for streaming"""
    type: Literal[
        "message_start",
        "message_chunk", 
        "message_end",
        "phase_change",
        "features_proposed",
        "implementation_started",
        "code_generated",
        "file_generated",
        "modification_applied",
        "error"
    ]
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

