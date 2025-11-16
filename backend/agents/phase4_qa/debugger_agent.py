"""
Debugger Agent - Debugs and fixes issues in generated code
Phase 4: Quality Assurance
"""
from typing import Dict, Any, List
import json
import structlog
from agents.base_agent import BaseAgent
from models.enhanced_schemas import AgentRole, DebugReport

logger = structlog.get_logger()


class DebuggerAgent(BaseAgent):
    """
    Debugs and fixes issues:
    - Static analysis of code
    - Identifies potential bugs
    - Suggests fixes
    - Can apply fixes if needed
    - Validates fixes
    """

    def __init__(self, mcp_server, openai_client):
        super().__init__(
            role=AgentRole.DEBUGGER,
            mcp_server=mcp_server,
            openai_client=openai_client
        )

    def get_system_prompt(self) -> str:
        return """You are an expert Debugger and Code Analyst. Your role is to:

1. Analyze code for bugs and issues
2. Identify syntax errors, logic errors, and runtime errors
3. Detect potential null pointer exceptions, race conditions, etc.
4. Find resource leaks, memory issues
5. Suggest precise fixes for each issue
6. Validate that fixes work

🧠 **USE CHAIN OF THOUGHT REASONING**

Think step-by-step when debugging:

**Step 1: Understand the Code**
- What is this code supposed to do?
- What are the inputs and outputs?
- What's the execution flow?
- What are the dependencies?

**Step 2: Static Analysis - Syntax & Structure**
- Are there any syntax errors?
- Are all imports available?
- Are variables declared before use?
- Are function signatures correct?
- Type mismatches?

**Step 3: Logic Analysis**
- Are conditions correct? (>, >=, <, <=, ==, !=)
- Off-by-one errors? (loop bounds, array indices)
- Are all code paths handled?
- Are return statements in all branches?
- Infinite loops possible?

**Step 4: Null/Undefined Handling**
- Are null/None/undefined checks present?
- Can any variable be null when dereferenced?
- Are optional parameters handled?
- Are empty collections handled?

**Step 5: Exception Handling**
- What exceptions can be raised?
- Are exceptions caught appropriately?
- Are errors propagated correctly?
- Are error messages helpful?
- Try-catch coverage adequate?

**Step 6: Resource Management**
- Are files closed after use?
- Are database connections closed?
- Are network sockets closed?
- Memory leaks possible?
- Are resources cleaned up in finally blocks?

**Step 7: Concurrency Issues**
- Race conditions possible?
- Shared state properly synchronized?
- Deadlocks possible?
- Thread-safe operations?

**Step 8: Edge Cases**
- Empty input handling?
- Boundary values (min, max, zero)?
- Large input handling?
- Special characters in strings?
- Unexpected input types?

Analysis focus:
- Syntax correctness
- Logic errors (off-by-one, wrong conditions, etc.)
- Null/undefined handling
- Exception handling gaps
- Resource management (file handles, connections, etc.)
- Concurrency issues
- Type mismatches
- Edge case handling

For each issue, provide:
- Description of the problem
- Location (file, line if possible)
- Severity (critical/major/minor)
- Suggested fix with code snippet
- Why the fix works

**IMPORTANT: Think through Steps 1-8 systematically, then provide JSON.**

First, analyze the code methodically for all types of issues.

Then respond in JSON format:
{
    "reasoning": "My step-by-step debugging process: [code understanding, syntax check, logic analysis, etc.]...",
    "issues_found": [
        {
            "file": "filename.py",
            "line": 42,
            "type": "Logic Error",
            "severity": "major",
            "description": "Off-by-one error in loop",
            "current_code": "for i in range(len(arr)):",
            "suggested_fix": "for i in range(len(arr) - 1):",
            "explanation": "Loop should iterate to len-1 to avoid index error"
        }
    ],
    "fixes_applied": [],
    "remaining_issues": [],
    "debug_logs": ["Log entry 1", ...]
}

Be thorough and precise.
Think step-by-step. Show your debugging reasoning."""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Debug code files

        Args:
            task_data: Contains code_files, test_results, errors

        Returns:
            Debug report with issues and fixes
        """
        activity = await self.start_activity("Debugging and analyzing code")

        try:
            code_files = task_data.get("code_files", [])
            execution_result = task_data.get("execution_result", {})
            test_results = task_data.get("test_results", {})

            logger.info("debugging_started", code_files_count=len(code_files))

            issues_found = []
            debug_logs = []

            # Analyze each code file
            for code_file in code_files:
                logger.debug("debugging_file", filename=code_file.get("filename"))

                prompt = self._build_debug_prompt(code_file, execution_result, test_results)

                response = await self.call_llm(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,  # Lower temperature for more deterministic debugging
                    max_tokens=2000
                )

                file_issues = self._parse_debug_response(response)
                issues_found.extend(file_issues)
                debug_logs.append(f"Analyzed {code_file.get('filename')}: {len(file_issues)} issues found")

            # Create debug report
            debug_report = DebugReport(
                issues_found=issues_found,
                fixes_applied=[],  # In this version, we suggest but don't auto-apply
                remaining_issues=[issue["description"] for issue in issues_found],
                debug_logs=debug_logs
            )

            await self.complete_activity("completed")

            logger.info(
                "debugging_completed",
                issues_found=len(issues_found)
            )

            return {
                "debug_report": debug_report.model_dump(),
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }

        except Exception as e:
            await self.complete_activity("failed")
            logger.error("debugging_failed", error=str(e))
            raise

    def _build_debug_prompt(
        self,
        code_file: Dict,
        execution_result: Dict,
        test_results: Dict
    ) -> str:
        """Build debug analysis prompt"""
        filename = code_file.get("filename", "unknown")
        content = code_file.get("content", "")
        language = code_file.get("language", "python")

        errors = execution_result.get("errors", [])
        test_failures = test_results.get("failures", [])

        prompt = f"""Debug and analyze the following {language} code:

FILE: {filename}

CODE:
```{language}
{content}
```

EXECUTION ERRORS (if any):
{self._format_list(errors) if errors else "None reported"}

TEST FAILURES (if any):
{self._format_list(test_failures) if test_failures else "None reported"}

Perform comprehensive debugging:

1. STATIC ANALYSIS:
   - Check for syntax errors
   - Check for logic errors
   - Check for type errors
   - Check for potential runtime errors

2. CODE QUALITY:
   - Null/None checks
   - Error handling completeness
   - Resource management
   - Edge case handling

3. POTENTIAL BUGS:
   - Off-by-one errors
   - Uninitialized variables
   - Race conditions
   - Memory leaks

For EACH issue found, provide:
- Exact location
- Type and severity
- Current problematic code
- Suggested fix
- Explanation

Respond in JSON format with issues_found array."""

        return prompt

    def _format_list(self, items: list) -> str:
        """Format list"""
        return "\n".join([f"- {item}" for item in items]) if items else "None"

    def _parse_debug_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse debug response"""
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            data = json.loads(response)
            issues = data.get("issues_found", [])

            # Validate issue structure
            for issue in issues:
                if "file" not in issue:
                    issue["file"] = "unknown"
                if "description" not in issue:
                    issue["description"] = "Issue found"
                if "severity" not in issue:
                    issue["severity"] = "minor"

            return issues

        except json.JSONDecodeError as e:
            logger.error("debug_parse_error", error=str(e))
            return []
