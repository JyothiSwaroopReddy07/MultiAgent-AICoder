"""
Requirements Analyst Agent - Extracts and analyzes functional/non-functional requirements
Phase 1: Discovery & Analysis
"""
from typing import Dict, Any
import json
import structlog
from agents.base_agent import BaseAgent
from models.enhanced_schemas import AgentRole, Requirements

logger = structlog.get_logger()


class RequirementsAnalystAgent(BaseAgent):
    """
    Analyzes user input and extracts structured requirements
    - Functional requirements
    - Non-functional requirements (performance, security, scalability)
    - Technical constraints
    - Business rules
    - User stories and acceptance criteria
    """

    def __init__(self, mcp_server, openai_client):
        super().__init__(
            role=AgentRole.REQUIREMENTS_ANALYST,
            mcp_server=mcp_server,
            openai_client=openai_client
        )

    def get_system_prompt(self) -> str:
        return """You are an expert Business Analyst and Requirements Engineer. Your role is to:

1. Analyze user descriptions and extract structured requirements
2. Identify functional requirements (what the system must do)
3. Identify non-functional requirements (performance, security, scalability, usability)
4. Extract technical constraints and dependencies
5. Define business rules and logic
6. Create user stories with acceptance criteria
7. Identify implicit requirements not explicitly stated

 **USE CHAIN OF THOUGHT REASONING**

Think step-by-step when analyzing requirements:

**Step 1: Read and Parse**
- What is the user trying to build?
- What are the explicit requirements mentioned?
- What domain is this (e-commerce, social media, SaaS, etc.)?

**Step 2: Extract Functional Requirements**
- What features/capabilities must the system have?
- What user actions need to be supported?
- What business processes need to be implemented?
- Are there CRUD operations? Workflows? Integrations?

**Step 3: Identify Non-Functional Requirements**
- Performance: What response times, throughput are implied?
- Scalability: What user load, data volume is expected?
- Security: What data sensitivity, auth requirements exist?
- Availability: What uptime is expected?
- Usability: What UX constraints exist?

**Step 4: Find Implicit Requirements**
- What requirements are implied but not stated?
- What security measures are standard for this domain?
- What error handling is needed?
- What validation is required?
- What logging/monitoring is needed?

**Step 5: Define Business Rules**
- What business logic needs to be enforced?
- What validation rules exist?
- What workflows must be followed?

**Step 6: Create User Stories**
- For each major feature, write: "As a [role], I want [feature] so that [benefit]"
- Include acceptance criteria

Guidelines:
- Be thorough - extract ALL requirements, explicit and implicit
- Categorize requirements properly
- Use SMART criteria (Specific, Measurable, Achievable, Relevant, Time-bound)
- Consider security, performance, and scalability requirements
- Think about edge cases and error scenarios
- Consider user experience requirements

**IMPORTANT: Show your reasoning, then provide the JSON.**

First, think through each step above.

Then respond in JSON format:
{
    "reasoning": "My step-by-step analysis of the requirements...",
    "functional": ["Requirement 1", "Requirement 2", ...],
    "non_functional": ["NFR 1", "NFR 2", ...],
    "technical_constraints": ["Constraint 1", ...],
    "business_rules": ["Rule 1", ...],
    "security_requirements": ["Security req 1", ...],
    "performance_requirements": ["Performance req 1", ...],
    "user_stories": ["As a user, I want...", ...],
    "acceptance_criteria": ["Criteria 1", ...]
}

Be comprehensive and think like a senior business analyst.
Think step-by-step. Show your work."""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze requirements from user input

        Args:
            task_data: Contains 'description', 'language', 'framework', 'requirements'

        Returns:
            Structured requirements analysis
        """
        activity = await self.start_activity("Analyzing requirements")

        try:
            description = task_data.get("description", "")
            language = task_data.get("language", "python")
            framework = task_data.get("framework", "")
            user_requirements = task_data.get("requirements", [])

            logger.info(
                "requirements_analysis_started",
                language=language,
                user_requirements_count=len(user_requirements)
            )

            # Build comprehensive analysis prompt
            prompt = self._build_analysis_prompt(
                description, language, framework, user_requirements
            )

            # Call LLM for analysis
            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,  # Lower temperature for more consistent analysis
                max_tokens=3000
            )

            # Parse response
            requirements_data = self._parse_requirements_response(response)

            # Validate and create Requirements object
            requirements = Requirements(**requirements_data)

            await self.complete_activity("completed")

            logger.info(
                "requirements_analysis_completed",
                functional_count=len(requirements.functional),
                nonfunctional_count=len(requirements.non_functional),
                user_stories_count=len(requirements.user_stories)
            )

            return {
                "requirements": requirements.model_dump(),
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }

        except Exception as e:
            await self.complete_activity("failed")
            logger.error("requirements_analysis_failed", error=str(e))
            raise

    def _build_analysis_prompt(
        self,
        description: str,
        language: str,
        framework: str,
        user_requirements: list
    ) -> str:
        """Build the requirements analysis prompt"""
        prompt = f"""Analyze the following software project and extract comprehensive requirements:

Project Description:
{description}

Target Language: {language}
Framework: {framework if framework else "Not specified"}

User-Specified Requirements:
{self._format_list(user_requirements) if user_requirements else "None specified"}

Please provide a comprehensive requirements analysis including:

1. FUNCTIONAL REQUIREMENTS: What the system must DO
   - Core features and functionality
   - User interactions
   - Data operations (CRUD, etc.)
   - Business logic
   - Integration points

2. NON-FUNCTIONAL REQUIREMENTS:
   - Performance requirements (response time, throughput)
   - Scalability requirements
   - Reliability and availability
   - Usability requirements
   - Maintainability requirements
   - Portability requirements

3. TECHNICAL CONSTRAINTS:
   - Technology limitations
   - Platform constraints
   - Integration constraints
   - Resource limitations

4. BUSINESS RULES:
   - Validation rules
   - Business logic rules
   - Workflow rules

5. SECURITY REQUIREMENTS:
   - Authentication needs
   - Authorization rules
   - Data protection
   - Compliance requirements
   - Audit requirements

6. PERFORMANCE REQUIREMENTS:
   - Response time expectations
   - Concurrent user support
   - Data volume handling
   - Resource usage limits

7. USER STORIES: In "As a [role], I want [feature] so that [benefit]" format

8. ACCEPTANCE CRITERIA: Clear, testable criteria for each major feature

Think deeply about implicit requirements that aren't explicitly stated but are necessary for a production-quality system.

Respond in valid JSON format."""

        return prompt

    def _format_list(self, items: list) -> str:
        """Format list for prompt"""
        return "\n".join([f"- {item}" for item in items])

    def _parse_requirements_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into requirements data"""
        try:
            # Clean response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            requirements_data = json.loads(response)

            # Ensure all required fields exist
            default_structure = {
                "functional": [],
                "non_functional": [],
                "technical_constraints": [],
                "business_rules": [],
                "security_requirements": [],
                "performance_requirements": [],
                "user_stories": [],
                "acceptance_criteria": []
            }

            # Merge with defaults
            for key in default_structure:
                if key not in requirements_data:
                    requirements_data[key] = default_structure[key]

            return requirements_data

        except json.JSONDecodeError as e:
            logger.error("requirements_parse_error", error=str(e))

            # Fallback: extract requirements from text
            return {
                "functional": ["System must implement core functionality as described"],
                "non_functional": ["System must be performant and secure"],
                "technical_constraints": [f"Must use {response[:100]}"],
                "business_rules": [],
                "security_requirements": ["Implement basic security best practices"],
                "performance_requirements": ["Acceptable response times"],
                "user_stories": ["As a user, I want to use the system effectively"],
                "acceptance_criteria": ["System functions as described"]
            }
