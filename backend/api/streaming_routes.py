"""
Streaming Routes for Real-Time Code Generation
Provides Server-Sent Events (SSE) for live updates with validation and error handling
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List
import asyncio
import json
import structlog

from agents.advanced_orchestrator import AdvancedOrchestrator
from utils.openai_client import get_openai_client
from utils.validators import (
    validate_description,
    validate_database_preference,
    sanitize_string,
    ValidationError
)
from constants import (
    MIN_DESCRIPTION_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    ErrorMessages
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v2/generate", tags=["streaming"])

# In-memory storage for active generations
active_generations = {}


class StreamGenerateRequest(BaseModel):
    """Request model for streaming code generation with validation"""
    
    description: str = Field(
        ...,
        min_length=MIN_DESCRIPTION_LENGTH,
        max_length=MAX_DESCRIPTION_LENGTH,
        description="Project description"
    )
    database_preference: str = Field(
        default="auto",
        description="Database preference: 'auto', 'postgresql', or 'mongodb'"
    )
    
    @validator('description')
    def validate_description_field(cls, v):
        """Validate and sanitize description"""
        if not v or not v.strip():
            raise ValueError("Description cannot be empty")
        
        # Sanitize input
        sanitized = sanitize_string(v, max_length=MAX_DESCRIPTION_LENGTH)
        
        # Validate
        is_valid, error = validate_description(sanitized)
        if not is_valid:
            raise ValueError(error)
        
        return sanitized
    
    @validator('database_preference')
    def validate_database_preference_field(cls, v):
        """Validate database preference"""
        v = v.lower().strip()
        is_valid, error = validate_database_preference(v)
        if not is_valid:
            raise ValueError(error)
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "description": "Build a Next.js e-commerce application with user authentication, product catalog, shopping cart, and checkout process",
                "database_preference": "auto"
            }
        }


async def generate_code_stream(request_id: str, request_data: dict):
    """Generator function that yields SSE events during code generation"""
    
    try:
        # Send initial event
        yield f"data: {json.dumps({'type': 'started', 'request_id': request_id})}\n\n"
        
        # Initialize services
        openai_client = get_openai_client()
        orchestrator = AdvancedOrchestrator(openai_client)
        
        # Store orchestrator for potential cancellation
        active_generations[request_id] = {
            'orchestrator': orchestrator,
            'status': 'running'
        }
        
        # Phase 1: Requirements Analysis
        yield f"data: {json.dumps({'type': 'phase_started', 'phase': 'Phase 1: Discovery & Analysis', 'agent': 'Requirements Analyst'})}\n\n"
        await asyncio.sleep(0.1)  # Small delay for UI update
        
        # Phase updates with progress
        phases = [
            {'phase': 1, 'name': 'Discovery & Analysis', 'agents': ['Requirements Analyst', 'Research Agent', 'Tech Stack Decision']},
            {'phase': 2, 'name': 'Design & Planning', 'agents': ['Architect', 'Module Designer', 'Component Designer', 'UI Designer']},
            {'phase': 3, 'name': 'Implementation', 'agents': ['Code Generator', 'Test Generator']},
            {'phase': 4, 'name': 'Quality Assurance', 'agents': ['Security Auditor', 'Debugger', 'Code Reviewer']},
            {'phase': 5, 'name': 'Validation', 'agents': ['Executor']},
            {'phase': 6, 'name': 'Monitoring', 'agents': ['Monitor']}
        ]
        
        # Actually run the generation with event streaming
        async for event in orchestrator.generate_with_streaming(request_data):
            # Stream each event to the client
            yield f"data: {json.dumps(event)}\n\n"
            await asyncio.sleep(0.01)  # Prevent overwhelming the client
        
        # Send completion event
        yield f"data: {json.dumps({'type': 'completed', 'request_id': request_id})}\n\n"
        
    except Exception as e:
        logger.error("streaming_generation_failed", error=str(e), request_id=request_id)
        error_event = {
            'type': 'error',
            'error': str(e),
            'request_id': request_id
        }
        yield f"data: {json.dumps(error_event)}\n\n"
    
    finally:
        # Cleanup
        if request_id in active_generations:
            del active_generations[request_id]


@router.post("/stream")
async def stream_generate(request: StreamGenerateRequest):
    """
    Start streaming code generation with real-time updates
    
    Validates input, initializes orchestrator, and streams events in real-time.
    
    Args:
        request: StreamGenerateRequest with description and database_preference
    
    Returns:
        StreamingResponse: SSE stream with events:
        - started: Generation started
        - phase_started: New phase began
        - agent_activity: Agent is working
        - file_generated: New file created
        - file_content_chunk: Partial file content
        - completed: Generation finished
        - error: Error occurred
    
    Raises:
        HTTPException: If validation fails (handled by Pydantic)
    """
    import uuid
    
    request_id = str(uuid.uuid4())
    
    logger.info(
        "stream_generation_started",
        request_id=request_id,
        description=request.description[:100],
        database_preference=request.database_preference
    )
    
    # Prepare request data for orchestrator
    request_data = {
        "description": request.description,
        "database_preference": request.database_preference,
    }
    
    return StreamingResponse(
        generate_code_stream(request_id, request_data),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "text/event-stream",
        }
    )


@router.post("/stream/cancel/{request_id}")
async def cancel_generation(request_id: str):
    """Cancel an active generation"""
    if request_id not in active_generations:
        raise HTTPException(status_code=404, detail="Generation not found or already completed")
    
    active_generations[request_id]['status'] = 'cancelled'
    logger.info("generation_cancelled", request_id=request_id)
    
    return {"status": "cancelled", "request_id": request_id}


@router.get("/stream/status/{request_id}")
async def get_generation_status(request_id: str):
    """Get the status of a generation"""
    if request_id not in active_generations:
        return {"status": "not_found", "request_id": request_id}
    
    return {
        "status": active_generations[request_id]['status'],
        "request_id": request_id
    }
