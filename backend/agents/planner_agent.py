"""
Planner Agent - Analyzes requirements and creates implementation plans
"""
from typing import Dict, Any, List
import json
import structlog
from agents.base_agent import BaseAgent
from models.schemas import AgentRole, Plan

logger = structlog.get_logger()


class PlannerAgent(BaseAgent):
    """
    Planner Agent creates detailed implementation plans from requirements
    """

    def __init__(self, mcp_server, openai_client):
        super().__init__(
            role=AgentRole.PLANNER,
            mcp_server=mcp_server,
            openai_client=openai_client
        )

    def get_system_prompt(self) -> str:
        return """You are an expert software architect and planner. Your role is to:

1. Analyze software requirements and descriptions
2. Create detailed, actionable implementation plans
3. Design appropriate file structures
4. Identify required dependencies and technologies
5. Break down complex projects into manageable steps

You should provide:
- A clear overview of the project
- Detailed step-by-step implementation plan
- Proposed file structure with descriptions
- List of dependencies
- Complexity estimate

Respond in JSON format with the following structure:
{
    "overview": "High-level project description",
    "steps": ["Step 1", "Step 2", ...],
    "file_structure": {
        "filename": "description of file purpose",
        ...
    },
    "dependencies": ["dependency1", "dependency2", ...],
    "estimated_complexity": "low|medium|high"
}

Be thorough, practical, and consider best practices."""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an implementation plan from requirements

        Args:
            task_data: Should contain 'description', 'language', 'framework', 'requirements'

        Returns:
            Dictionary containing the plan
        """
        activity = await self.start_activity("Creating implementation plan")

        try:
            description = task_data.get("description", "")
            language = task_data.get("language", "python")
            framework = task_data.get("framework", "")
            requirements = task_data.get("requirements", [])

            logger.info(
                "planning_started",
                language=language,
                framework=framework,
                requirements_count=len(requirements)
            )

            # Build prompt for LLM
            prompt = self._build_planning_prompt(
                description, language, framework, requirements
            )

            # Call LLM
            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000
            )

            # Parse response
            plan_data = self._parse_plan_response(response)

            # Validate and create Plan object
            plan = Plan(**plan_data)

            await self.complete_activity("completed")

            logger.info(
                "planning_completed",
                steps_count=len(plan.steps),
                files_count=len(plan.file_structure),
                complexity=plan.estimated_complexity
            )

            return {
                "plan": plan.model_dump(),
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }

        except Exception as e:
            await self.complete_activity("failed")
            logger.error("planning_failed", error=str(e))
            raise

    def _build_planning_prompt(
        self,
        description: str,
        language: str,
        framework: str,
        requirements: List[str]
    ) -> str:
        """Build the prompt for plan generation"""
        prompt = f"""Create a detailed implementation plan for the following software project:

Description: {description}

Programming Language: {language}
Framework: {framework if framework else "None specified"}

Specific Requirements:
{self._format_requirements(requirements)}

Please provide a comprehensive implementation plan including:
1. Project overview
2. Step-by-step implementation plan
3. File structure with clear descriptions
4. Required dependencies
5. Complexity assessment

Respond in valid JSON format."""

        return prompt

    def _format_requirements(self, requirements: List[str]) -> str:
        """Format requirements list for prompt"""
        if not requirements:
            return "- No specific requirements provided"

        return "\n".join([f"- {req}" for req in requirements])

    def _parse_plan_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into plan data"""
        try:
            # Try to parse as JSON
            # Remove markdown code blocks if present
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]

            response = response.strip()

            plan_data = json.loads(response)

            # Validate required fields
            required_fields = ["overview", "steps", "file_structure", "dependencies", "estimated_complexity"]
            for field in required_fields:
                if field not in plan_data:
                    raise ValueError(f"Missing required field: {field}")

            return plan_data

        except json.JSONDecodeError as e:
            logger.error("json_parse_error", error=str(e), response=response[:200])

            # Fallback: create a basic plan from the response
            return {
                "overview": "Plan generated from requirements",
                "steps": response.split("\n"),
                "file_structure": {"main.py": "Main application file"},
                "dependencies": [],
                "estimated_complexity": "medium"
            }
