"""
Orchestrator - Coordinates multi-agent workflow
"""
import asyncio
from typing import Dict, Any, Optional
import uuid
from datetime import datetime
import structlog
from models.schemas import (
    CodeRequest, CodeGenerationResult, AgentActivity,
    Plan, GeneratedCode, TestCase, ReviewFeedback
)
from agents.planner_agent import PlannerAgent
from agents.coder_agent import CoderAgent
from agents.tester_agent import TesterAgent
from agents.reviewer_agent import ReviewerAgent
from mcp.server import MCPServer
from utils.openai_client import OpenAIClient
from utils.llm_tracker import tracker

logger = structlog.get_logger()


class AgentOrchestrator:
    """
    Orchestrates the multi-agent workflow for code generation
    """

    def __init__(self, openai_client: OpenAIClient):
        self.openai = openai_client
        self.mcp = MCPServer()

        # Initialize agents
        self.planner = PlannerAgent(self.mcp, self.openai)
        self.coder = CoderAgent(self.mcp, self.openai)
        self.tester = TesterAgent(self.mcp, self.openai)
        self.reviewer = ReviewerAgent(self.mcp, self.openai)

        # Track active requests
        self.active_requests: Dict[str, CodeGenerationResult] = {}

        logger.info("orchestrator_initialized")

    async def generate_code(self, request: CodeRequest) -> CodeGenerationResult:
        """
        Main workflow: orchestrate all agents to generate code

        Args:
            request: Code generation request

        Returns:
            Complete code generation result
        """
        request_id = str(uuid.uuid4())

        logger.info(
            "code_generation_started",
            request_id=request_id,
            language=request.language
        )

        # Initialize result
        result = CodeGenerationResult(
            request_id=request_id,
            status="in_progress",
            created_at=datetime.utcnow()
        )

        self.active_requests[request_id] = result

        # Reset tracker for this request
        tracker.reset()

        try:
            # Step 1: Planner creates implementation plan
            logger.info("step_1_planning", request_id=request_id)
            plan_result = await self.planner.process_task({
                "description": request.description,
                "language": request.language,
                "framework": request.framework,
                "requirements": request.requirements
            })

            result.plan = Plan(**plan_result["plan"])
            if plan_result.get("activity"):
                result.agent_activities.append(AgentActivity(**plan_result["activity"]))

            # Step 2: Coder generates code
            logger.info("step_2_coding", request_id=request_id)
            code_result = await self.coder.process_task({
                "plan": plan_result["plan"],
                "description": request.description,
                "language": request.language
            })

            result.code_files = [
                GeneratedCode(**cf) for cf in code_result["code_files"]
            ]
            if code_result.get("activity"):
                result.agent_activities.append(AgentActivity(**code_result["activity"]))

            # Step 3: Tester creates tests
            logger.info("step_3_testing", request_id=request_id)
            test_result = await self.tester.process_task({
                "code_files": code_result["code_files"],
                "language": request.language,
                "description": request.description
            })

            result.test_files = [
                TestCase(**tf) for tf in test_result["test_files"]
            ]
            if test_result.get("activity"):
                result.agent_activities.append(AgentActivity(**test_result["activity"]))

            # Step 4: Reviewer reviews code
            logger.info("step_4_reviewing", request_id=request_id)
            review_result = await self.reviewer.process_task({
                "code_files": code_result["code_files"],
                "test_files": test_result["test_files"],
                "language": request.language
            })

            result.review = ReviewFeedback(**review_result["review"])
            if review_result.get("activity"):
                result.agent_activities.append(AgentActivity(**review_result["activity"]))

            # Get LLM usage summary
            usage_summary = tracker.get_summary()
            result.total_llm_usage = {
                "total_calls": usage_summary["total_calls"],
                "total_tokens": usage_summary["total_tokens"]
            }
            result.total_cost = usage_summary["total_cost"]

            # Mark as completed
            result.status = "completed"
            result.completed_at = datetime.utcnow()

            logger.info(
                "code_generation_completed",
                request_id=request_id,
                files_generated=len(result.code_files),
                tests_generated=len(result.test_files),
                quality_score=result.review.quality_score,
                total_tokens=result.total_llm_usage["total_tokens"],
                total_cost=result.total_cost
            )

            return result

        except Exception as e:
            result.status = "failed"
            result.completed_at = datetime.utcnow()

            logger.error(
                "code_generation_failed",
                request_id=request_id,
                error=str(e)
            )

            raise

    def get_request_status(self, request_id: str) -> Optional[CodeGenerationResult]:
        """Get the status of a code generation request"""
        return self.active_requests.get(request_id)

    async def start_background_tasks(self):
        """Start background tasks (MCP message processing, etc.)"""
        # Start MCP message processor
        asyncio.create_task(self.mcp.process_messages())
        logger.info("background_tasks_started")
