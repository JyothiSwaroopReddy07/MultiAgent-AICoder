"""
Reviewer Agent - Reviews code quality and provides feedback
"""
from typing import Dict, Any, List
import json
import structlog
from agents.base_agent import BaseAgent
from models.schemas import AgentRole, ReviewFeedback, GeneratedCode

logger = structlog.get_logger()


class ReviewerAgent(BaseAgent):
    """
    Reviewer Agent performs code review and quality assessment
    """

    def __init__(self, mcp_server, openai_client):
        super().__init__(
            role=AgentRole.REVIEWER,
            mcp_server=mcp_server,
            openai_client=openai_client
        )

    def get_system_prompt(self) -> str:
        return """You are an expert code reviewer with deep knowledge of software engineering best practices. Your role is to:

1. Review code for quality, correctness, and maintainability
2. Identify bugs, security issues, and performance problems
3. Suggest improvements and best practices
4. Assess code against industry standards
5. Provide constructive feedback

 **USE CHAIN OF THOUGHT REASONING**

Think step-by-step when reviewing code:

**Step 1: Understand the Code**
- What is this code supposed to do?
- Does it align with requirements?
- Is the overall approach sound?
- Are design patterns appropriate?

**Step 2: Review Code Correctness**
- Does the code work as intended?
- Are there any logic errors?
- Are edge cases handled?
- Are there any bugs?

**Step 3: Check Security**
- Input validation present?
- SQL injection vulnerabilities?
- XSS vulnerabilities?
- Sensitive data exposed?
- Authentication/authorization proper?

**Step 4: Assess Performance**
- Are algorithms efficient? (O(n) vs O(n²))
- Are database queries optimized?
- Any unnecessary loops or operations?
- Memory usage reasonable?
- Caching opportunities?

**Step 5: Evaluate Readability**
- Are names clear and descriptive?
- Is code structure logical?
- Is complexity manageable?
- Are functions/methods appropriately sized?
- Is nesting depth reasonable?

**Step 6: Check Maintainability**
- Is code modular and reusable?
- Are responsibilities clear (SRP)?
- Are dependencies minimal?
- Is it easy to test?
- Is it easy to modify?

**Step 7: Review Code Standards**
- Follows language conventions? (PEP 8, etc.)
- Consistent style throughout?
- Proper naming conventions?
- Appropriate use of language features?

**Step 8: Check Error Handling**
- Are exceptions handled properly?
- Are error messages helpful?
- Is error recovery appropriate?
- Are resources cleaned up?

**Step 9: Review Documentation**
- Are docstrings present?
- Are comments helpful (not redundant)?
- Is complex logic explained?
- Are API contracts clear?

**Step 10: Assess Test Coverage**
- Are tests present?
- Do tests cover key functionality?
- Are edge cases tested?
- Are tests meaningful?

**Step 11: Calculate Quality Score**
- Count critical/major/minor issues
- Consider: correctness (30%), security (20%), performance (15%), 
  readability (15%), maintainability (10%), standards (10%)
- Deduct points for issues
- Score: 0-10

Review criteria:
- Code correctness and functionality
- Security vulnerabilities
- Performance considerations
- Readability and maintainability
- Adherence to coding standards
- Error handling
- Documentation quality
- Test coverage
- Design patterns and architecture

**IMPORTANT: Think through Steps 1-11 systematically, then provide JSON.**

First, systematically review the code from all angles.

Then provide feedback in JSON format:
{
    "reasoning": "My step-by-step review process: [code understanding, correctness check, security review, etc.]...",
    "issues": ["Issue 1", "Issue 2", ...],
    "suggestions": ["Suggestion 1", "Suggestion 2", ...],
    "quality_score": 7.5,
    "approved": true
}

Be thorough but constructive. Focus on important issues.
Think step-by-step. Show your review reasoning."""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Review generated code

        Args:
            task_data: Should contain 'code_files', 'test_files', 'language'

        Returns:
            Dictionary containing review feedback
        """
        activity = await self.start_activity("Reviewing code quality")

        try:
            code_files_data = task_data.get("code_files", [])
            test_files_data = task_data.get("test_files", [])
            language = task_data.get("language", "python")

            if not code_files_data:
                raise ValueError("No code files provided for review")

            code_files = [GeneratedCode(**cf) for cf in code_files_data]

            logger.info(
                "code_review_started",
                language=language,
                code_files_count=len(code_files),
                test_files_count=len(test_files_data)
            )

            # Review each code file
            reviews: List[ReviewFeedback] = []

            for code_file in code_files:
                logger.debug("reviewing_file", filename=code_file.filename)

                review = await self._review_file(
                    code_file=code_file,
                    language=language,
                    has_tests=len(test_files_data) > 0
                )

                reviews.append(review)

            # Calculate overall review
            overall_review = self._create_overall_review(reviews)

            await self.complete_activity("completed")

            logger.info(
                "code_review_completed",
                files_reviewed=len(reviews),
                overall_quality=overall_review.quality_score,
                approved=overall_review.approved
            )

            return {
                "review": overall_review.model_dump(),
                "file_reviews": [r.model_dump() for r in reviews],
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }

        except Exception as e:
            await self.complete_activity("failed")
            logger.error("code_review_failed", error=str(e))
            raise

    async def _review_file(
        self,
        code_file: GeneratedCode,
        language: str,
        has_tests: bool
    ) -> ReviewFeedback:
        """Review a single code file"""

        prompt = f"""Review the following code file:

Filename: {code_file.filename}
Language: {language}
Purpose: {code_file.description}
Has Tests: {has_tests}

Code:
```{language}
{code_file.content}
```

Please provide a thorough code review including:
1. Any issues found (bugs, security, performance, style)
2. Suggestions for improvement
3. Quality score (0-10)
4. Whether you approve this code

Respond in JSON format:
{{
    "issues": ["list of issues"],
    "suggestions": ["list of suggestions"],
    "quality_score": 7.5,
    "approved": true
}}"""

        response = await self.call_llm(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # Lower temperature for consistent reviews
            max_tokens=2000
        )

        # Parse review response
        review_data = self._parse_review_response(response, code_file.filename)

        return ReviewFeedback(
            file=code_file.filename,
            **review_data
        )

    def _parse_review_response(self, response: str, filename: str) -> Dict[str, Any]:
        """Parse LLM review response"""
        try:
            # Clean up response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]

            response = response.strip()

            review_data = json.loads(response)

            # Validate and set defaults
            return {
                "issues": review_data.get("issues", []),
                "suggestions": review_data.get("suggestions", []),
                "quality_score": float(review_data.get("quality_score", 7.0)),
                "approved": bool(review_data.get("approved", True))
            }

        except (json.JSONDecodeError, ValueError) as e:
            logger.error("review_parse_error", error=str(e), response=response[:200])

            # Fallback: Create basic review
            return {
                "issues": ["Review parsing failed - manual review recommended"],
                "suggestions": ["Ensure code follows best practices"],
                "quality_score": 6.0,
                "approved": False
            }

    def _create_overall_review(self, reviews: List[ReviewFeedback]) -> ReviewFeedback:
        """Create an overall review from individual file reviews"""
        all_issues = []
        all_suggestions = []
        total_score = 0.0

        for review in reviews:
            all_issues.extend([f"{review.file}: {issue}" for issue in review.issues])
            all_suggestions.extend([f"{review.file}: {sug}" for sug in review.suggestions])
            total_score += review.quality_score

        avg_score = total_score / len(reviews) if reviews else 0.0
        all_approved = all(r.approved for r in reviews)

        return ReviewFeedback(
            file="Overall Project",
            issues=all_issues,
            suggestions=all_suggestions,
            quality_score=round(avg_score, 2),
            approved=all_approved and avg_score >= 7.0
        )
