"""
Coder Agent - Generates code based on implementation plans
"""
from typing import Dict, Any, List
import structlog
from agents.base_agent import BaseAgent
from models.schemas import AgentRole, GeneratedCode, Plan

logger = structlog.get_logger()


class CoderAgent(BaseAgent):
    """
    Coder Agent generates code files based on implementation plans
    """

    def __init__(self, mcp_server, openai_client):
        super().__init__(
            role=AgentRole.CODER,
            mcp_server=mcp_server,
            openai_client=openai_client
        )

    def get_system_prompt(self) -> str:
        return """You are an expert software developer. Your role is to:

1. Write clean, efficient, and well-documented code
2. Follow best practices and coding standards
3. Implement features according to specifications
4. Create maintainable and testable code
5. Add appropriate comments and documentation

🧠 **USE CHAIN OF THOUGHT REASONING**

Think step-by-step when writing code:

**Step 1: Understand Requirements**
- What is this file supposed to do?
- What functionality must it implement?
- What are the inputs and outputs?
- What are the dependencies?

**Step 2: Plan the Structure**
- What classes/functions are needed?
- How should the code be organized?
- What's the logical flow?
- What design patterns apply?

**Step 3: Consider Implementation Details**
- What data structures to use?
- What algorithms are appropriate?
- How to handle edge cases?
- What validations are needed?

**Step 4: Plan Error Handling**
- What can go wrong?
- What exceptions to catch/raise?
- How to handle errors gracefully?
- What error messages to show?

**Step 5: Add Documentation**
- What docstrings to include?
- What inline comments for complex logic?
- What type hints to add?
- What usage examples to provide?

**Step 6: Optimize & Polish**
- Any performance optimizations needed?
- Code readable and maintainable?
- Following language conventions?
- Any security considerations?

Guidelines:
- Write production-ready code
- Follow PEP 8 for Python, appropriate style guides for other languages
- Include docstrings and comments
- Handle errors appropriately
- Consider edge cases
- Make code modular and reusable

When generating code:
- Provide complete, runnable code
- Include necessary imports
- Add clear function/class documentation
- Consider security and performance

**IMPORTANT: Think through Steps 1-6, then write the code.**

Think step-by-step. Write clean, well-documented code."""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate code based on a plan

        Args:
            task_data: Should contain 'plan', 'description', 'language'

        Returns:
            Dictionary containing generated code files
        """
        activity = await self.start_activity("Generating code from plan")

        try:
            plan_data = task_data.get("plan", {})
            plan = Plan(**plan_data) if plan_data else None
            description = task_data.get("description", "")
            language = task_data.get("language", "python")

            if not plan:
                raise ValueError("No plan provided for code generation")

            logger.info(
                "code_generation_started",
                language=language,
                files_count=len(plan.file_structure)
            )

            # Generate code for each file in the plan
            generated_files: List[GeneratedCode] = []

            for filename, file_description in plan.file_structure.items():
                logger.debug("generating_file", filename=filename)

                code_content = await self._generate_file_code(
                    filename=filename,
                    description=file_description,
                    plan=plan,
                    language=language,
                    overall_description=description
                )

                generated_file = GeneratedCode(
                    filename=filename,
                    filepath=f"./{filename}",
                    content=code_content,
                    language=language,
                    description=file_description
                )

                generated_files.append(generated_file)

            await self.complete_activity("completed")

            logger.info(
                "code_generation_completed",
                files_generated=len(generated_files)
            )

            return {
                "code_files": [f.model_dump() for f in generated_files],
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }

        except Exception as e:
            await self.complete_activity("failed")
            logger.error("code_generation_failed", error=str(e))
            raise

    async def _generate_file_code(
        self,
        filename: str,
        description: str,
        plan: Plan,
        language: str,
        overall_description: str
    ) -> str:
        """Generate code for a single file"""

        prompt = f"""Generate complete, production-ready code for the following file:

Filename: {filename}
Purpose: {description}
Language: {language}

Project Context:
{overall_description}

Implementation Plan Overview:
{plan.overview}

Key Implementation Steps:
{self._format_steps(plan.steps)}

Dependencies to consider:
{', '.join(plan.dependencies)}

Please provide:
1. Complete, runnable code for this file
2. Appropriate imports
3. Clear documentation and comments
4. Error handling where appropriate
5. Following best practices for {language}

Return ONLY the code content, no explanations or markdown formatting."""

        code = await self.call_llm(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,  # Lower temperature for more consistent code
            max_tokens=3000
        )

        # Clean up the response
        code = self._clean_code_response(code)

        return code

    def _format_steps(self, steps: List[str]) -> str:
        """Format implementation steps for prompt"""
        return "\n".join([f"{i+1}. {step}" for i, step in enumerate(steps)])

    def _clean_code_response(self, code: str) -> str:
        """Clean up LLM response to get just the code"""
        # Remove markdown code blocks if present
        code = code.strip()

        # Remove ```python or ```javascript style markers
        lines = code.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]

        return "\n".join(lines).strip()
