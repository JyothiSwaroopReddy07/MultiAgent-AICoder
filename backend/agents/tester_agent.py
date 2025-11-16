"""
Tester Agent - Generates and runs test cases for generated code
"""
from typing import Dict, Any, List
import structlog
from agents.base_agent import BaseAgent
from models.schemas import AgentRole, TestCase, GeneratedCode

logger = structlog.get_logger()


class TesterAgent(BaseAgent):
    """
    Tester Agent creates comprehensive test cases for generated code
    """

    def __init__(self, mcp_server, openai_client):
        super().__init__(
            role=AgentRole.TESTER,
            mcp_server=mcp_server,
            openai_client=openai_client
        )

    def get_system_prompt(self) -> str:
        return """You are an expert software testing engineer. Your role is to:

1. Create comprehensive test suites
2. Write unit tests, integration tests, and end-to-end tests
3. Cover edge cases and error conditions
4. Follow testing best practices and patterns
5. Ensure code coverage and quality

🧠 **USE CHAIN OF THOUGHT REASONING**

Think step-by-step when writing tests:

**Step 1: Understand the Code**
- What does this code do?
- What are the inputs and outputs?
- What are the key functions/methods/classes?
- What dependencies does it have?

**Step 2: Identify Test Cases**
- Happy path: What's the normal, expected usage?
- Edge cases: Empty inputs, null values, boundary values
- Error cases: Invalid inputs, missing data, exceptions
- Integration: How does it interact with other components?

**Step 3: Plan Test Structure**
- What testing framework to use? (pytest, jest, junit, etc.)
- What fixtures/mocks are needed?
- How to set up test data?
- How to isolate tests?

**Step 4: Design Test Cases**
- For each function/method, list test cases:
  * Test name (descriptive, what is being tested)
  * Setup (arrange): What data/state is needed?
  * Action (act): What function is called with what args?
  * Verification (assert): What should the result be?

**Step 5: Cover Edge Cases**
- Empty/null inputs
- Boundary values (min, max, zero, negative)
- Special characters in strings
- Large datasets
- Concurrent access (if applicable)

**Step 6: Test Error Handling**
- What exceptions should be raised?
- What error messages should appear?
- How are errors handled gracefully?

**Step 7: Write the Tests**
- Clear, descriptive test names (test_function_does_x_when_y)
- Follow AAA pattern (Arrange, Act, Assert)
- One logical assertion per test
- Tests are independent (can run in any order)

Guidelines for test creation:
- Write clear, descriptive test names
- Use appropriate testing frameworks (pytest, unittest, jest, etc.)
- Test both happy paths and error cases
- Include setup and teardown when needed
- Add assertions that verify expected behavior
- Make tests independent and repeatable
- Add docstrings explaining what's being tested

Test structure:
- Arrange: Set up test data and conditions
- Act: Execute the code being tested
- Assert: Verify the results

**IMPORTANT: Think through Steps 1-7, then write the test code.**

Provide complete, runnable test code.
Think step-by-step. Write comprehensive tests."""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate test cases for code

        Args:
            task_data: Should contain 'code_files', 'language', 'description'

        Returns:
            Dictionary containing generated test files
        """
        activity = await self.start_activity("Generating test cases")

        try:
            code_files_data = task_data.get("code_files", [])
            language = task_data.get("language", "python")
            description = task_data.get("description", "")

            if not code_files_data:
                raise ValueError("No code files provided for testing")

            code_files = [GeneratedCode(**cf) for cf in code_files_data]

            logger.info(
                "test_generation_started",
                language=language,
                code_files_count=len(code_files)
            )

            # Generate tests for each code file
            test_files: List[TestCase] = []

            for code_file in code_files:
                logger.debug("generating_tests_for", filename=code_file.filename)

                test_content = await self._generate_tests_for_file(
                    code_file=code_file,
                    language=language,
                    project_description=description
                )

                test_filename = self._get_test_filename(code_file.filename, language)

                test_case = TestCase(
                    name=f"Tests for {code_file.filename}",
                    filepath=f"./tests/{test_filename}",
                    content=test_content,
                    test_type="unit",
                    target_file=code_file.filepath
                )

                test_files.append(test_case)

            await self.complete_activity("completed")

            logger.info(
                "test_generation_completed",
                tests_generated=len(test_files)
            )

            return {
                "test_files": [t.model_dump() for t in test_files],
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }

        except Exception as e:
            await self.complete_activity("failed")
            logger.error("test_generation_failed", error=str(e))
            raise

    async def _generate_tests_for_file(
        self,
        code_file: GeneratedCode,
        language: str,
        project_description: str
    ) -> str:
        """Generate test cases for a single code file"""

        # Determine testing framework based on language
        framework = self._get_test_framework(language)

        prompt = f"""Generate comprehensive test cases for the following code:

Filename: {code_file.filename}
Language: {language}
Testing Framework: {framework}

Code Purpose: {code_file.description}

Code to Test:
```{language}
{code_file.content}
```

Project Context:
{project_description}

Please generate:
1. Complete test file with all necessary imports
2. Test cases for all functions/methods/classes
3. Tests for happy paths and edge cases
4. Tests for error handling
5. Clear test names and documentation
6. Appropriate assertions

Follow {framework} best practices and conventions.
Return ONLY the test code, no explanations."""

        test_code = await self.call_llm(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=3000
        )

        # Clean up the response
        test_code = self._clean_code_response(test_code)

        return test_code

    def _get_test_framework(self, language: str) -> str:
        """Get appropriate testing framework for language"""
        frameworks = {
            "python": "pytest",
            "javascript": "jest",
            "typescript": "jest",
            "java": "junit",
            "go": "testing package",
            "rust": "built-in test framework",
            "ruby": "rspec"
        }
        return frameworks.get(language.lower(), "appropriate testing framework")

    def _get_test_filename(self, original_filename: str, language: str) -> str:
        """Generate test filename based on original file"""
        # Remove extension
        name_parts = original_filename.rsplit(".", 1)
        base_name = name_parts[0]

        # Language-specific conventions
        if language.lower() == "python":
            return f"test_{base_name}.py"
        elif language.lower() in ["javascript", "typescript"]:
            return f"{base_name}.test.{name_parts[1]}"
        else:
            return f"{base_name}_test.{name_parts[1] if len(name_parts) > 1 else 'txt'}"

    def _clean_code_response(self, code: str) -> str:
        """Clean up LLM response to get just the code"""
        code = code.strip()

        # Remove markdown code blocks
        lines = code.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]

        return "\n".join(lines).strip()
