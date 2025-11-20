"""
Chat-based API Routes for Interactive Code Generation
Provides conversation-based code generation with SSE streaming
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
import json
import asyncio
import structlog

from agents.conversation.conversation_orchestrator import ConversationOrchestrator
from utils.openai_client import get_openai_client
from models.conversation_schemas import ConversationPhase

logger = structlog.get_logger()

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Global orchestrator instance
orchestrator: Optional[ConversationOrchestrator] = None


def get_orchestrator() -> ConversationOrchestrator:
    """Get or create conversation orchestrator"""
    global orchestrator
    if orchestrator is None:
        openai_client = get_openai_client()
        orchestrator = ConversationOrchestrator(openai_client)
    return orchestrator


class ChatMessage(BaseModel):
    """Chat message from user"""
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID or null for new")
    message: str = Field(..., min_length=1, max_length=5000, description="User message")
    action: Optional[str] = Field(None, description="Explicit action: plan, refine, approve, implement, modify")
    
    class Config:
        schema_extra = {
            "example": {
                "conversation_id": None,
                "message": "I want to build a task management app with teams and real-time collaboration",
                "action": None
            }
        }


@router.post("/message")
async def send_message(request: ChatMessage):
    """
    Send a message in the conversation and get streaming response
    
    Workflow:
    1. Initial message → AI proposes features
    2. Feedback/refinement → AI updates features
    3. Approval → AI implements code
    4. Modification request → AI updates code
    """
    try:
        orchestrator = get_orchestrator()
        
        logger.info(
            "chat_message_received",
            conversation_id=request.conversation_id,
            message_length=len(request.message),
            action=request.action
        )
        
        async def event_generator():
            """Generate SSE events"""
            try:
                # Send started event
                yield f"data: {json.dumps({'type': 'started', 'conversation_id': request.conversation_id or 'new'})}\n\n"
                
                # Process message and stream events
                async for event in orchestrator.process_message(
                    conversation_id=request.conversation_id,
                    user_message=request.message,
                    action=request.action
                ):
                    event_dict = {
                        "type": event.type,
                        "data": event.data,
                        "timestamp": event.timestamp.isoformat()
                    }
                    yield f"data: {json.dumps(event_dict)}\n\n"
                    await asyncio.sleep(0.01)  # Small delay for client
                
                # Send completed event
                yield f"data: {json.dumps({'type': 'completed'})}\n\n"
                
            except Exception as e:
                logger.error("chat_stream_error", error=str(e))
                error_event = {
                    "type": "error",
                    "data": {"error": str(e)},
                    "timestamp": "now"
                }
                yield f"data: {json.dumps(error_event)}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*",
            }
        )
    
    except Exception as e:
        logger.error("chat_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    Get conversation state and history
    
    Returns:
    - Full conversation state
    - Message history
    - Current phase
    - Generated code (if any)
    """
    try:
        orchestrator = get_orchestrator()
        conversation = orchestrator.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {
            "conversation_id": conversation.conversation_id,
            "phase": conversation.phase,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in conversation.messages
            ],
            "proposed_features": conversation.proposed_features.dict() if conversation.proposed_features else None,
            "approved_features": conversation.approved_features.dict() if conversation.approved_features else None,
            "generated_code": {
                "files": conversation.generated_code.files,
                "file_structure": conversation.generated_code.file_structure,
                "setup_instructions": conversation.generated_code.setup_instructions
            } if conversation.generated_code else None,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_conversation_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations")
async def list_conversations():
    """
    List all active conversations
    
    Returns:
    - List of conversations with basic info
    """
    try:
        orchestrator = get_orchestrator()
        
        conversations = []
        for conv_id, conv in orchestrator.conversations.items():
            conversations.append({
                "conversation_id": conv.conversation_id,
                "phase": conv.phase,
                "message_count": len(conv.messages),
                "has_code": conv.generated_code is not None,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "problem_statement": conv.problem_statement[:100] if conv.problem_statement else None
            })
        
        return {
            "conversations": conversations,
            "total": len(conversations)
        }
    
    except Exception as e:
        logger.error("list_conversations_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    try:
        orchestrator = get_orchestrator()
        
        if conversation_id in orchestrator.conversations:
            del orchestrator.conversations[conversation_id]
            logger.info("conversation_deleted", conversation_id=conversation_id)
            return {"status": "deleted", "conversation_id": conversation_id}
        else:
            raise HTTPException(status_code=404, detail="Conversation not found")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_conversation_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def chat_health():
    """Health check for chat service"""
    orchestrator = get_orchestrator()
    
    return {
        "status": "healthy",
        "service": "chat",
        "active_conversations": len(orchestrator.conversations)
    }

