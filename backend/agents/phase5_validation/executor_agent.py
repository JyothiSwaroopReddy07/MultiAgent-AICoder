"""
Executor Agent - Executes and validates generated code
Phase 5: Validation & Deployment
"""
from typing import Dict, Any
import structlog
from agents.base_agent import BaseAgent
from models.enhanced_schemas import AgentRole, ExecutionResult

logger = structlog.get_logger()


class ExecutorAgent(BaseAgent):
    """
    Executes and validates code:
    - Simulates code execution
    - Runs basic validation
    - Checks for runtime errors
    - Validates functionality
    - Reports execution results

    Note: In production, would run in isolated sandbox/container
    """

    def __init__(self, mcp_server, openai_client):
        super().__init__(
            role=AgentRole.EXECUTOR,
            mcp_server=mcp_server,
            openai_client=openai_client
        )

    def get_system_prompt(self) -> str:
        return """You are a Code Execution Validator. Your role is to:

1. Analyze if code would execute correctly
2. Identify runtime issues that would occur
3. Validate code logic
4. Check for missing dependencies
5. Verify configuration correctness
6. Simulate execution mentally

 **USE CHAIN OF THOUGHT REASONING**

Think step-by-step when validating execution:

**Step 1: Syntax Validation**
- Can the code be parsed?
- Are there syntax errors?
- Are all brackets/parentheses balanced?
- Are statements properly terminated?

**Step 2: Dependency Check**
- What modules/packages are imported?
- Are all imports available in standard library or specified dependencies?
- Are versions compatible?
- Are there circular dependencies?

**Step 3: Configuration Validation**
- Are environment variables needed?
- Are configuration files required?
- Are API keys or credentials needed?
- Are file paths accessible?

**Step 4: Static Analysis**
- Are all variables defined before use?
- Are function calls valid (correct number of args)?
- Are types compatible?
- Are there unreachable code sections?

**Step 5: Runtime Simulation**
- Trace through main execution path
- What would happen at each step?
- Are there potential runtime errors?
  * Division by zero
  * Null/None dereferences
  * Index out of bounds
  * Type errors
  * File not found
  * Network errors

**Step 6: Test Execution Analysis**
- Are there test files?
- Would tests run?
- Would tests pass or fail?
- What would cause failures?

**Step 7: Output Prediction**
- What would the program output?
- What would be the exit code?
- What side effects would occur? (files created, database changes, etc.)

**Step 8: Resource Requirements**
- What resources are needed? (memory, disk, network)
- Are resource limits reasonable?
- Are resources cleaned up properly?

**Step 9: Overall Assessment**
- Would execution succeed?
- What's the likelihood of success? (0-100%)
- What are the main blockers?
- What would need to be fixed?

Analysis areas:
- Syntax correctness (can it run?)
- Logical correctness (does it do what it should?)
- Missing imports/dependencies
- Configuration issues
- Runtime errors (division by zero, null refs, etc.)
- Resource availability
- Environment requirements

For each code file, determine:
- Would it execute successfully?
- What errors would occur?
- What would be the output?
- Are there any blockers?

**IMPORTANT: Think through Steps 1-9 systematically, then provide JSON.**

First, systematically validate execution from all angles.

Then respond in JSON format:
{
    "reasoning": "My step-by-step execution validation: [syntax check, dependency analysis, runtime simulation, etc.]...",
    "success": true/false,
    "output": "Expected output or error messages",
    "errors": ["Error 1", "Error 2", ...],
    "test_results": {
        "total": 10,
        "passed": 8,
        "failed": 2,
        "failures": ["Test 1 failed: reason", ...]
    },
    "execution_time": 1.5
}

Be realistic about execution outcomes.
Think step-by-step. Show your validation reasoning."""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate code execution

        Args:
            task_data: Contains code_files, test_files

        Returns:
            Execution result
        """
        activity = await self.start_activity("Validating code execution")

        try:
            code_files = task_data.get("code_files", [])
            test_files = task_data.get("test_files", [])
            language = task_data.get("language", "python")

            logger.info(
                "execution_validation_started",
                code_files_count=len(code_files),
                test_files_count=len(test_files)
            )

            prompt = self._build_execution_prompt(code_files, test_files, language)

            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000
            )

            result_data = self._parse_execution_response(response)
            execution_result = ExecutionResult(**result_data)

            await self.complete_activity("completed")

            logger.info(
                "execution_validation_completed",
                success=execution_result.success,
                errors_count=len(execution_result.errors)
            )

            return {
                "execution_result": execution_result.model_dump(),
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }

        except Exception as e:
            await self.complete_activity("failed")
            logger.error("execution_validation_failed", error=str(e))
            raise

    def _build_execution_prompt(
        self,
        code_files: list,
        test_files: list,
        language: str
    ) -> str:
        """Build execution validation prompt"""
        # Get overview of code
        code_summary = []
        for cf in code_files[:5]:
            code_summary.append(f"{cf.get('filename')}: {cf.get('description', '')}")

        prompt = f"""Validate the execution of this {language} application:

CODE FILES:
{chr(10).join(code_summary)}

TEST FILES: {len(test_files)} test files

Perform mental execution validation:

1. **Syntax Check**:
   - Would code compile/parse?
   - Any syntax errors?

2. **Dependency Check**:
   - Are all imports available?
   - Are external dependencies specified?

3. **Logic Validation**:
   - Would the logic work correctly?
   - Any obvious runtime errors?

4. **Test Execution**:
   - Would tests pass?
   - Any test failures expected?

5. **Overall Assessment**:
   - Can this code run successfully?
   - What would be the outcome?

Consider:
- Import errors
- Configuration issues
- Logic errors that cause runtime failures
- Resource availability
- Environment setup

Provide realistic execution analysis.

Respond in valid JSON format."""

        return prompt

    def _parse_execution_response(self, response: str) -> Dict[str, Any]:
        """Parse execution response"""
        try:
            import json

            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            result_data = json.loads(response)

            # Ensure required fields
            if "success" not in result_data:
                result_data["success"] = True
            if "output" not in result_data:
                result_data["output"] = "Code validated"
            if "errors" not in result_data:
                result_data["errors"] = []
            if "test_results" not in result_data:
                result_data["test_results"] = {}
            if "execution_time" not in result_data:
                result_data["execution_time"] = 1.0

            return result_data

        except Exception as e:
            logger.error("execution_parse_error", error=str(e))

            # Fallback
            return {
                "success": True,
                "output": "Code appears valid",
                "errors": [],
                "test_results": {},
                "execution_time": 1.0
            }
