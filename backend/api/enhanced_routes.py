"""
Enhanced API Routes for advanced multi-agent workflow
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
import structlog
from pydantic import BaseModel, Field
from models.enhanced_schemas import EnhancedCodeGenerationResult, WorkflowPhase
from models.clarification_schemas import ClarificationResponse, ClarificationAnswer
from agents.advanced_orchestrator import AdvancedOrchestrator
from agents.streaming_wrapper import StreamingOrchestrator
from utils.openai_client import OpenAIClient
from utils.llm_tracker import tracker
from config import get_settings

logger = structlog.get_logger()

router = APIRouter()

# Global orchestrator instance
advanced_orchestrator: Optional[AdvancedOrchestrator] = None


class EnhancedCodeRequest(BaseModel):
    """Enhanced code generation request"""
    description: str = Field(..., description="Software description")
    language: str = Field(default="python", description="Programming language")
    framework: Optional[str] = Field(default=None, description="Framework")
    requirements: list = Field(default=[], description="User requirements")
    workflow_mode: str = Field(default="complete", description="Workflow mode: complete|fast|custom")


class ClarificationSubmission(BaseModel):
    """User's clarification answers"""
    answers: list[Dict[str, Any]] = Field(..., description="List of answers to clarification questions")


def get_advanced_orchestrator() -> AdvancedOrchestrator:
    """Get the advanced orchestrator instance"""
    global advanced_orchestrator
    if advanced_orchestrator is None:
        raise HTTPException(status_code=500, detail="Advanced orchestrator not initialized")
    return advanced_orchestrator


@router.post("/generate/enhanced", response_model=Dict[str, Any])
async def generate_code_enhanced(request: EnhancedCodeRequest) -> Dict[str, Any]:
    """
    Enhanced code generation with full 6-phase workflow:

    Phase 1: Discovery & Analysis
      - Requirements analysis
      - Research

    Phase 2: Design & Planning
      - High-Level Design (HLD)
      - Module Design
      - Low-Level Design (LLD)

    Phase 3: Implementation
      - Code generation
      - Test generation

    Phase 4: Quality Assurance
      - Security audit
      - Code review
      - Debugging

    Phase 5: Validation
      - Execution validation

    Phase 6: Monitoring
      - Agent health monitoring

    Returns comprehensive results with all phase outputs.
    """
    try:
        logger.info(
            "enhanced_generation_request",
            language=request.language,
            mode=request.workflow_mode
        )

        orch = get_advanced_orchestrator()

        # Convert request to dict
        request_data = {
            "description": request.description,
            "language": request.language,
            "framework": request.framework,
            "requirements": request.requirements
        }

        result = await orch.generate_code(request_data)

        # Convert to dict for response
        return result.model_dump()

    except Exception as e:
        logger.error("enhanced_generation_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Enhanced code generation failed: {str(e)}"
        )


@router.post("/generate/enhanced/interactive", response_model=Dict[str, Any])
async def generate_code_interactive(request: EnhancedCodeRequest) -> Dict[str, Any]:
    """
    Interactive code generation with clarification support:

    This endpoint starts the generation process but may pause if clarifications
    are needed during requirements gathering.

    If clarifications are needed, the response will include:
    - status: "awaiting_clarifications"
    - clarification_request: Questions to ask the user

    If no clarifications are needed, it will proceed with full generation.

    Returns:
        - Complete result if no clarifications needed
        - Partial result with clarification_request if clarifications needed
    """
    try:
        logger.info(
            "interactive_generation_request",
            language=request.language,
            mode=request.workflow_mode
        )

        orch = get_advanced_orchestrator()

        # Convert request to dict
        request_data = {
            "description": request.description,
            "language": request.language,
            "framework": request.framework,
            "requirements": request.requirements
        }

        result = await orch.generate_code_interactive(request_data)

        # Convert to dict for response
        return result.model_dump()

    except Exception as e:
        logger.error("interactive_generation_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Interactive code generation failed: {str(e)}"
        )


@router.post("/generate/enhanced/{request_id}/clarifications", response_model=Dict[str, Any])
async def submit_clarifications(request_id: str, submission: ClarificationSubmission) -> Dict[str, Any]:
    """
    Submit clarification answers and resume workflow

    After receiving clarification questions from the interactive endpoint,
    use this endpoint to submit answers and resume the generation process.

    Args:
        request_id: The generation request ID
        submission: User's answers to the clarification questions

    Returns:
        Updated result with continued generation (may still request more clarifications)
    """
    try:
        logger.info(
            "clarifications_submitted",
            request_id=request_id,
            answer_count=len(submission.answers)
        )

        orch = get_advanced_orchestrator()

        # Convert submission to ClarificationResponse
        answers = [
            ClarificationAnswer(
                question_id=ans.get("question_id", ""),
                answer=ans.get("answer", "")
            )
            for ans in submission.answers
        ]

        clarification_response = ClarificationResponse(
            request_id=request_id,
            answers=answers,
            skipped=False
        )

        result = await orch.submit_clarifications(request_id, clarification_response)

        return result.model_dump()

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("clarification_submission_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Clarification submission failed: {str(e)}"
        )


@router.get("/generate/enhanced/{request_id}/clarifications")
async def get_clarifications(request_id: str) -> Dict[str, Any]:
    """
    Get clarification request for a generation request

    Returns the clarification questions if the workflow is paused for clarifications

    Returns:
        - clarification_request: The questions to ask the user
        - awaiting_clarifications: Boolean indicating if clarifications are needed
    """
    orch = get_advanced_orchestrator()
    result = orch.get_request_status(request_id)

    if not result:
        raise HTTPException(status_code=404, detail="Request not found")

    if not result.awaiting_clarifications:
        return {
            "awaiting_clarifications": False,
            "clarification_request": None
        }

    return {
        "awaiting_clarifications": True,
        "clarification_request": result.clarification_request
    }


@router.get("/generate/enhanced/status/{request_id}")
async def get_enhanced_status(request_id: str) -> Dict[str, Any]:
    """
    Get status of enhanced code generation request

    Returns current phase, progress, and all completed outputs
    """
    orch = get_advanced_orchestrator()
    result = orch.get_request_status(request_id)

    if not result:
        raise HTTPException(status_code=404, detail="Request not found")

    return result.model_dump()


@router.get("/workflow/phases")
async def get_workflow_phases() -> Dict[str, Any]:
    """
    Get information about all workflow phases

    Returns description of each phase and the agents involved
    """
    return {
        "phases": [
            {
                "phase": "discovery",
                "name": "Discovery & Analysis",
                "description": "Analyze requirements and conduct research",
                "agents": [
                    {
                        "role": "requirements_analyst",
                        "name": "Requirements Analyst",
                        "description": "Extracts functional and non-functional requirements"
                    },
                    {
                        "role": "research",
                        "name": "Research Agent",
                        "description": "Researches best practices and technologies"
                    }
                ]
            },
            {
                "phase": "design",
                "name": "Design & Planning",
                "description": "Create comprehensive system designs",
                "agents": [
                    {
                        "role": "architect",
                        "name": "Architect",
                        "description": "Creates High-Level Design (HLD)"
                    },
                    {
                        "role": "module_designer",
                        "name": "Module Designer",
                        "description": "Plans module architecture"
                    },
                    {
                        "role": "component_designer",
                        "name": "Component Designer",
                        "description": "Creates Low-Level Design (LLD)"
                    },
                    {
                        "role": "ui_designer",
                        "name": "UI Designer",
                        "description": "Designs UI/UX and component architecture"
                    }
                ]
            },
            {
                "phase": "implementation",
                "name": "Implementation",
                "description": "Generate code and tests",
                "agents": [
                    {
                        "role": "code_generator",
                        "name": "Code Generator",
                        "description": "Generates production-ready code"
                    },
                    {
                        "role": "test_generator",
                        "name": "Test Generator",
                        "description": "Creates comprehensive test suites"
                    }
                ]
            },
            {
                "phase": "quality_assurance",
                "name": "Quality Assurance",
                "description": "Test, audit, and review code",
                "agents": [
                    {
                        "role": "security_auditor",
                        "name": "Security Auditor",
                        "description": "Performs security analysis"
                    },
                    {
                        "role": "debugger",
                        "name": "Debugger",
                        "description": "Finds and fixes bugs"
                    },
                    {
                        "role": "code_reviewer",
                        "name": "Code Reviewer",
                        "description": "Reviews code quality"
                    }
                ]
            },
            {
                "phase": "validation",
                "name": "Validation & Deployment",
                "description": "Validate and prepare for deployment",
                "agents": [
                    {
                        "role": "executor",
                        "name": "Executor",
                        "description": "Validates code execution"
                    }
                ]
            },
            {
                "phase": "monitoring",
                "name": "Monitoring",
                "description": "Monitor agent health",
                "agents": [
                    {
                        "role": "monitor",
                        "name": "Monitor",
                        "description": "Monitors all agent health"
                    }
                ]
            }
        ],
        "total_phases": 6,
        "total_agents": 13
    }


@router.get("/agents/enhanced")
async def get_enhanced_agents() -> Dict[str, Any]:
    """
    Get information about all enhanced agents

    Returns comprehensive agent information organized by phase
    """
    orch = get_advanced_orchestrator()

    return {
        "total_agents": len(orch._get_all_agents()),
        "agents_by_phase": {
            "Phase 1 - Discovery & Analysis": [
                "Requirements Analyst",
                "Research Agent"
            ],
            "Phase 2 - Design & Planning": [
                "Architect (HLD)",
                "Module Designer",
                "Component Designer (LLD)",
                "UI Designer"
            ],
            "Phase 3 - Implementation": [
                "Code Generator",
                "Test Generator"
            ],
            "Phase 4 - Quality Assurance": [
                "Security Auditor",
                "Debugger",
                "Code Reviewer"
            ],
            "Phase 5 - Validation": [
                "Executor"
            ],
            "Phase 6 - Monitoring": [
                "Monitor"
            ]
        },
        "mcp_server": {
            "status": "running",
            "message_queue_active": True
        }
    }


@router.get("/health/enhanced")
async def health_check_enhanced() -> Dict[str, str]:
    """Enhanced health check"""
    return {
        "status": "healthy",
        "service": "AI Coder - Enhanced Multi-Agent System",
        "version": "2.0.0",
        "workflow_phases": "6",
        "total_agents": "13"
    }
