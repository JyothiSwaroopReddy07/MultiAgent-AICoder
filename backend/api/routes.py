"""
API Routes for the AI Coder system
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, Optional
import structlog
from models.schemas import CodeRequest, CodeGenerationResult, ErrorResponse
from agents.orchestrator import AgentOrchestrator
from utils.openai_client import OpenAIClient
from utils.llm_tracker import tracker
from config import get_settings

logger = structlog.get_logger()

router = APIRouter()

# Global orchestrator instance (initialized on startup)
orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    """Get the orchestrator instance"""
    global orchestrator
    if orchestrator is None:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")
    return orchestrator


@router.post("/generate", response_model=CodeGenerationResult)
async def generate_code(request: CodeRequest) -> CodeGenerationResult:
    """
    Generate code from requirements

    This endpoint coordinates all agents to:
    1. Create an implementation plan
    2. Generate code files
    3. Create test cases
    4. Review the code

    Returns the complete result including code, tests, and metrics.
    """
    try:
        logger.info(
            "generate_code_request",
            language=request.language,
            framework=request.framework
        )

        orch = get_orchestrator()
        result = await orch.generate_code(request)

        return result

    except Exception as e:
        logger.error("generate_code_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Code generation failed: {str(e)}"
        )


@router.get("/status/{request_id}", response_model=CodeGenerationResult)
async def get_status(request_id: str) -> CodeGenerationResult:
    """
    Get the status of a code generation request

    Args:
        request_id: The unique request ID

    Returns:
        The current status and results
    """
    orch = get_orchestrator()
    result = orch.get_request_status(request_id)

    if not result:
        raise HTTPException(status_code=404, detail="Request not found")

    return result


@router.get("/usage", response_model=Dict[str, Any])
async def get_usage() -> Dict[str, Any]:
    """
    Get current LLM usage statistics

    Returns:
        Usage summary including calls, tokens, and cost
    """
    return tracker.get_summary()


@router.post("/usage/reset")
async def reset_usage() -> Dict[str, str]:
    """
    Reset LLM usage statistics

    Returns:
        Success message
    """
    tracker.reset()
    return {"message": "Usage statistics reset successfully"}


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint

    Returns:
        Status message
    """
    return {
        "status": "healthy",
        "service": "AI Coder Multi-Agent System"
    }


@router.get("/agents")
async def get_agents() -> Dict[str, Any]:
    """
    Get information about registered agents

    Returns:
        Agent information
    """
    orch = get_orchestrator()

    return {
        "agents": [
            {
                "role": "planner",
                "description": "Analyzes requirements and creates implementation plans",
                "status": "active"
            },
            {
                "role": "coder",
                "description": "Generates code based on implementation plans",
                "status": "active"
            },
            {
                "role": "tester",
                "description": "Creates test cases for generated code",
                "status": "active"
            },
            {
                "role": "reviewer",
                "description": "Reviews code quality and provides feedback",
                "status": "active"
            }
        ],
        "mcp_server": {
            "status": "running",
            "host": get_settings().mcp_server_host,
            "port": get_settings().mcp_server_port
        }
    }
