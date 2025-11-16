"""
Interactive Requirements Analyst Agent - Asks clarifying questions
Phase 1: Discovery & Analysis
"""
from typing import Dict, Any, List
import json
import uuid
import structlog
from agents.base_agent import BaseAgent
from models.enhanced_schemas import AgentRole, Requirements
from models.clarification_schemas import (
    ClarificationRequest, ClarificationQuestion, QuestionType
)

logger = structlog.get_logger()


class InteractiveRequirementsAnalystAgent(BaseAgent):
    """
    Enhanced Requirements Analyst that asks clarifying questions
    before finalizing requirements
    """

    def __init__(self, mcp_server, openai_client):
        super().__init__(
            role=AgentRole.REQUIREMENTS_ANALYST,
            mcp_server=mcp_server,
            openai_client=openai_client
        )

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a requirements analysis task"""
        # For interactive mode, this delegates to specialized methods
        return await self.analyze_and_generate_questions(task_data)

    def get_system_prompt(self) -> str:
        return """You are an expert Business Analyst conducting requirements gathering.

Your role is to:
1. Analyze the user's description
2. Identify areas that need clarification
3. Generate intelligent clarifying questions
4. Extract comprehensive requirements once you have enough information

🧠 **USE CHAIN OF THOUGHT REASONING**

Think step-by-step when analyzing the description:

**Step 1: Read and Understand**
- What is the user trying to build?
- What is explicitly stated?
- What is implied but not stated?

**Step 2: Identify What's Missing**
- Functional requirements: What features are unclear or missing?
- Scale: Do we know expected users, load, data volume?
- Performance: Are there performance requirements?
- Security: Do we know data sensitivity, compliance needs?
- Availability: Do we know uptime requirements?
- Constraints: Do we know budget, timeline, team size?

**Step 3: Calculate Confidence**
- Rate completeness of each area (0-10)
- Average the scores
- If average < 7, we need clarifications

**Step 4: Generate Questions**
- For each missing/unclear area, create 1-2 questions
- Prioritize questions that affect architecture decisions
- Make questions specific and actionable
- Provide context for why you're asking

When analyzing descriptions, look for:
- Vague or ambiguous statements
- Missing critical information (scale, users, constraints)
- Unclear functional requirements
- Unspecified non-functional requirements (performance, security, availability)
- Technology preferences or constraints
- Business constraints (budget, timeline, team size)
- Scalability expectations
- Availability requirements (24/7? downtime acceptable?)
- Security requirements
- Compliance needs

Generate questions that are:
- Specific and actionable
- Help you make better technical decisions
- Cover functional AND non-functional aspects
- Consider trade-offs

**IMPORTANT: Think step-by-step, then respond in JSON.**

First, reason through:
1. What is explicitly stated in the description?
2. What critical information is missing?
3. Rate confidence for each area (functional, scale, performance, security, etc.)
4. What questions would fill the biggest gaps?

Then respond in JSON format:
{
    "reasoning": "My step-by-step analysis: [what's stated, what's missing, confidence calculation]...",
    "needs_clarification": true/false,
    "confidence_score": 0.8,
    "clarification_questions": [
        {
            "question_id": "q1",
            "question": "How many concurrent users do you expect?",
            "question_type": "multiple_choice",
            "context": "Needed to determine scalability requirements",
            "options": ["< 100", "100-1000", "1000-10000", "> 10000"],
            "category": "scalability"
        }
    ],
    "preliminary_requirements": {
        "functional": ["requirement 1", ...],
        "non_functional": ["requirement 1", ...]
    }
}

Be smart about what questions to ask - don't ask obvious things.
Think step-by-step. Show your reasoning."""

    async def analyze_and_generate_questions(
        self,
        task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze description and generate clarifying questions if needed

        Returns:
            - needs_clarification: bool
            - questions: List of questions
            - preliminary_requirements: Initial requirements
        """
        activity = await self.start_activity("Analyzing requirements and generating clarifying questions")

        try:
            description = task_data.get("description", "")
            language = task_data.get("language", "")
            framework = task_data.get("framework", "")
            user_requirements = task_data.get("requirements", [])

            logger.info("analyzing_for_clarifications", description_length=len(description))

            prompt = self._build_clarification_analysis_prompt(
                description, language, framework, user_requirements
            )

            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=2500
            )

            analysis = self._parse_clarification_response(response)

            await self.complete_activity("completed")

            return {
                "needs_clarification": analysis.get("needs_clarification", False),
                "confidence_score": analysis.get("confidence_score", 1.0),
                "questions": analysis.get("clarification_questions", []),
                "preliminary_requirements": analysis.get("preliminary_requirements", {}),
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }

        except Exception as e:
            await self.complete_activity("failed")
            logger.error("clarification_analysis_failed", error=str(e))
            raise

    async def finalize_requirements(
        self,
        task_data: Dict[str, Any],
        clarifications: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Finalize requirements with clarification answers

        Args:
            task_data: Original request data
            clarifications: User's answers to clarification questions

        Returns:
            Final comprehensive requirements
        """
        activity = await self.start_activity("Finalizing requirements with clarifications")

        try:
            description = task_data.get("description", "")
            preliminary_reqs = task_data.get("preliminary_requirements", {})
            answers = clarifications.get("answers", [])

            logger.info("finalizing_requirements", answers_count=len(answers))

            prompt = self._build_finalization_prompt(
                description, preliminary_reqs, answers
            )

            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=3000
            )

            requirements_data = self._parse_requirements_response(response)
            requirements = Requirements(**requirements_data)

            await self.complete_activity("completed")

            logger.info(
                "requirements_finalized",
                functional_count=len(requirements.functional),
                nonfunctional_count=len(requirements.non_functional)
            )

            return {
                "requirements": requirements.model_dump(),
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }

        except Exception as e:
            await self.complete_activity("failed")
            logger.error("requirements_finalization_failed", error=str(e))
            raise

    def _build_clarification_analysis_prompt(
        self,
        description: str,
        language: str,
        framework: str,
        user_requirements: List[str]
    ) -> str:
        """Build prompt for clarification analysis"""
        return f"""Analyze this software project description and determine if you need clarifying questions:

PROJECT DESCRIPTION:
{description}

SPECIFIED TECH:
- Language: {language if language else "Not specified"}
- Framework: {framework if framework else "Not specified"}

USER-PROVIDED REQUIREMENTS:
{chr(10).join([f"- {req}" for req in user_requirements]) if user_requirements else "None provided"}

ANALYSIS NEEDED:

1. **Is the description clear enough?**
   - Are functional requirements clear?
   - Are non-functional requirements specified?
   - Is the scale/scope clear?

2. **What critical information is missing?**
   - Expected number of users/load?
   - Availability requirements (24/7, acceptable downtime)?
   - Security requirements (compliance, data sensitivity)?
   - Scalability needs?
   - Performance expectations?
   - Budget/timeline constraints?
   - Team size/expertise?

3. **Do we need to ask about technology choices?**
   - If language not specified or unclear
   - If architecture pattern unclear (monolith vs microservices)
   - If database type unclear
   - If deployment environment unclear

4. **Generate smart clarifying questions**
   - Only ask what's truly needed for good technical decisions
   - Prioritize questions about scale, availability, security
   - Ask about business constraints if relevant
   - Ask about tech preferences if not specified

RESPOND IN JSON:
{{
    "needs_clarification": true/false,
    "confidence_score": 0-1 (how confident you are in your understanding),
    "clarification_questions": [
        {{
            "question_id": "unique_id",
            "question": "Clear, specific question",
            "question_type": "multiple_choice|text_input|yes_no|numeric|scale",
            "context": "Why this matters for technical decisions",
            "options": ["option1", "option2"] (for multiple_choice),
            "default_value": "suggested answer if any",
            "category": "scalability|availability|security|tech_stack|requirements|constraints"
        }}
    ],
    "preliminary_requirements": {{
        "functional": ["what we can determine so far"],
        "non_functional": ["what we can determine so far"]
    }}
}}

If confidence_score < 0.7, set needs_clarification = true.
Ask 3-7 most important questions."""

    def _build_finalization_prompt(
        self,
        description: str,
        preliminary_reqs: Dict,
        answers: List[Dict]
    ) -> str:
        """Build prompt for finalizing requirements with answers"""
        answers_text = "\n".join([
            f"Q: {ans.get('question_id')} - A: {ans.get('answer')}"
            for ans in answers
        ])

        return f"""Now finalize the comprehensive requirements with the user's clarifications:

ORIGINAL DESCRIPTION:
{description}

PRELIMINARY REQUIREMENTS:
{json.dumps(preliminary_reqs, indent=2)}

USER'S CLARIFICATION ANSWERS:
{answers_text}

Based on these clarifications, provide COMPLETE requirements in JSON format:
{{
    "functional": ["detailed functional requirement 1", ...],
    "non_functional": ["detailed non-functional requirement 1", ...],
    "technical_constraints": ["constraint 1", ...],
    "business_rules": ["rule 1", ...],
    "security_requirements": ["security req 1", ...],
    "performance_requirements": ["performance req 1", ...],
    "user_stories": ["As a user...", ...],
    "acceptance_criteria": ["criteria 1", ...]
}}

Be comprehensive and specific based on the clarifications received."""

    def _parse_clarification_response(self, response: str) -> Dict[str, Any]:
        """Parse clarification analysis response"""
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

            # Validate structure
            if "needs_clarification" not in data:
                data["needs_clarification"] = False
            if "confidence_score" not in data:
                data["confidence_score"] = 1.0
            if "clarification_questions" not in data:
                data["clarification_questions"] = []
            if "preliminary_requirements" not in data:
                data["preliminary_requirements"] = {"functional": [], "non_functional": []}

            return data

        except Exception as e:
            logger.error("clarification_parse_error", error=str(e))
            return {
                "needs_clarification": False,
                "confidence_score": 0.8,
                "clarification_questions": [],
                "preliminary_requirements": {"functional": [], "non_functional": []}
            }

    def _parse_requirements_response(self, response: str) -> Dict[str, Any]:
        """Parse final requirements response"""
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            requirements_data = json.loads(response)

            # Ensure all fields
            defaults = {
                "functional": [],
                "non_functional": [],
                "technical_constraints": [],
                "business_rules": [],
                "security_requirements": [],
                "performance_requirements": [],
                "user_stories": [],
                "acceptance_criteria": []
            }

            for key in defaults:
                if key not in requirements_data:
                    requirements_data[key] = defaults[key]

            return requirements_data

        except Exception as e:
            logger.error("requirements_parse_error", error=str(e))
            return {
                "functional": ["System must implement core functionality"],
                "non_functional": ["System must be performant and secure"],
                "technical_constraints": [],
                "business_rules": [],
                "security_requirements": ["Follow security best practices"],
                "performance_requirements": ["Acceptable response times"],
                "user_stories": ["As a user, I want to use the system"],
                "acceptance_criteria": ["System functions as described"]
            }
