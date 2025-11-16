"""
Tech Stack Decision Agent - Makes informed technology choices based on requirements
Phase 1: Discovery & Analysis
"""
from typing import Dict, Any
import json
import structlog
from agents.base_agent import BaseAgent
from models.enhanced_schemas import AgentRole
from models.clarification_schemas import TechStackDecision

logger = structlog.get_logger()


class TechStackDecisionAgent(BaseAgent):
    """
    Makes intelligent tech stack decisions based on:
    - Requirements (functional & non-functional)
    - Scalability needs
    - Availability requirements
    - Security requirements
    - Team constraints
    - Budget constraints
    """

    def __init__(self, mcp_server, openai_client):
        super().__init__(
            role=AgentRole.RESEARCH,  # Reuse RESEARCH role
            mcp_server=mcp_server,
            openai_client=openai_client
        )

    def get_system_prompt(self) -> str:
        return """You are an expert Technology Consultant and Solution Architect.

Your role is to make informed technology stack decisions based on:
1. Functional requirements
2. Non-functional requirements (performance, security, scalability, availability)
3. Business constraints (budget, team size, timeline)
4. Trade-offs between different options

🧠 **USE CHAIN OF THOUGHT REASONING**

For each technology decision, think step-by-step:

**Step 1: Analyze Requirements**
- What are the key functional requirements?
- What are the critical non-functional requirements?
- What scale are we dealing with (users, requests, data)?
- What are the constraints (budget, team, timeline)?

**Step 2: Evaluate Options**
- List 2-4 viable options for each technology choice
- For each option, analyze: pros, cons, fit with requirements
- Consider: performance, scalability, cost, learning curve, ecosystem

**Step 3: Make Decision**
- Choose the best option based on Step 2 analysis
- Explain WHY this option beats the alternatives
- Be specific about what requirements drove this decision

**Step 4: Validate Decision**
- Does this choice support the scalability needs?
- Does this choice support the availability needs?
- Is this within budget constraints?
- Can the team work with this technology?

KEY DECISION FACTORS:

**Language Selection:**
- Performance requirements
- Team expertise
- Ecosystem maturity
- Scalability needs
- Development speed
- Type safety requirements

**Framework Selection:**
- Project complexity
- Time to market
- Community support
- Performance needs
- Learning curve

**Database Selection:**
- Data model (relational vs document vs graph)
- Scale (reads/writes per second)
- Consistency vs availability trade-offs
- Query patterns
- Transaction requirements

**Architecture Pattern:**
- Scalability requirements
- Team size
- Complexity tolerance
- Deployment requirements
- Monolith vs Microservices vs Serverless

**Scalability Approach:**
- Expected growth
- Budget constraints
- Horizontal vs vertical scaling
- Caching strategy
- Load balancing needs

**Availability Approach:**
- Downtime tolerance
- Recovery time objectives (RTO)
- Recovery point objectives (RPO)
- Redundancy needs
- Disaster recovery

**IMPORTANT: Show your reasoning, then provide the final JSON.**

First, think through each decision step-by-step:
1. Analyze the requirements (scale, performance, constraints)
2. For each technology choice (language, framework, database, architecture):
   - List 2-3 options
   - Evaluate each option against requirements
   - Choose the best fit with clear reasoning
3. Design scalability and availability approaches
4. Document trade-offs honestly

Then respond in JSON format:
{
    "reasoning": "Step-by-step thought process of your decisions...",
    "language": "python",
    "language_justification": "Python chosen because [specific requirements it satisfies]...",
    "framework": "fastapi",
    "framework_justification": "FastAPI chosen because [specific requirements it satisfies]...",
    "database": "postgresql",
    "database_justification": "PostgreSQL chosen because [specific requirements it satisfies]...",
    "architecture_pattern": "monolith",
    "architecture_justification": "Monolith chosen because [specific requirements it satisfies]...",
    "additional_technologies": {
        "cache": "redis: Needed for session management and caching",
        "message_queue": "rabbitmq: For async task processing"
    },
    "scalability_approach": "Horizontal scaling with load balancer...",
    "availability_approach": "Multi-region deployment with...",
    "trade_offs": [
        "Python over Go: Slower but faster development",
        "Monolith over microservices: Simpler but less scalable"
    ],
    "alternatives_considered": [
        "Node.js + Express: Fast but callback hell",
        "MongoDB: Flexible schema but no ACID"
    ]
}

Be honest about trade-offs. There's no perfect solution.
Think step-by-step. Show your work."""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make tech stack decisions based on requirements

        Args:
            task_data: Contains requirements, clarifications, constraints

        Returns:
            Complete tech stack decision with justifications
        """
        activity = await self.start_activity("Making tech stack decisions based on requirements")

        try:
            requirements = task_data.get("requirements", {})
            clarifications = task_data.get("clarifications", {})
            user_preferences = task_data.get("user_preferences", {})

            logger.info("tech_stack_decision_started")

            prompt = self._build_decision_prompt(
                requirements, clarifications, user_preferences
            )

            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,  # Lower for more consistent decisions
                max_tokens=2500
            )

            decision_data = self._parse_decision_response(response)
            tech_decision = TechStackDecision(**decision_data)

            await self.complete_activity("completed")

            logger.info(
                "tech_stack_decision_completed",
                language=tech_decision.language,
                database=tech_decision.database,
                architecture=tech_decision.architecture_pattern
            )

            return {
                "tech_stack_decision": tech_decision.model_dump(),
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }

        except Exception as e:
            await self.complete_activity("failed")
            logger.error("tech_stack_decision_failed", error=str(e))
            raise

    def _build_decision_prompt(
        self,
        requirements: Dict,
        clarifications: Dict,
        user_preferences: Dict
    ) -> str:
        """Build tech stack decision prompt"""

        # Extract key information
        functional = requirements.get("functional", [])
        non_functional = requirements.get("non_functional", [])
        security_reqs = requirements.get("security_requirements", [])
        performance_reqs = requirements.get("performance_requirements", [])

        # Extract clarifications
        scale = clarifications.get("expected_users", "Not specified")
        availability = clarifications.get("availability_requirement", "Not specified")
        budget = clarifications.get("budget_constraint", "Not specified")
        team_size = clarifications.get("team_size", "Not specified")

        prompt = f"""Make comprehensive tech stack decisions for this project:

FUNCTIONAL REQUIREMENTS:
{self._format_list(functional[:10])}

NON-FUNCTIONAL REQUIREMENTS:
{self._format_list(non_functional[:8])}

SECURITY REQUIREMENTS:
{self._format_list(security_reqs[:5])}

PERFORMANCE REQUIREMENTS:
{self._format_list(performance_reqs[:5])}

PROJECT CONTEXT:
- Expected Scale: {scale}
- Availability Requirement: {availability}
- Budget: {budget}
- Team Size: {team_size}

USER PREFERENCES:
{json.dumps(user_preferences, indent=2) if user_preferences else "No specific preferences"}

MAKE DECISIONS FOR:

1. **Programming Language**
   - Consider: performance, team expertise, ecosystem
   - Options: Python, JavaScript/TypeScript, Java, Go, Rust, etc.
   - Justify your choice

2. **Framework**
   - Consider: project complexity, time to market, support
   - Choose appropriate framework for the language
   - Justify your choice

3. **Database**
   - Consider: data model, scale, consistency needs
   - Options: PostgreSQL, MySQL, MongoDB, Cassandra, etc.
   - Justify your choice

4. **Architecture Pattern**
   - Consider: scale, team size, complexity
   - Options: Monolith, Microservices, Serverless
   - Justify your choice

5. **Additional Technologies**
   - Cache (Redis, Memcached)?
   - Message Queue (RabbitMQ, Kafka)?
   - Search (Elasticsearch)?
   - Based on requirements

6. **Scalability Approach**
   - How will system handle growth?
   - Horizontal vs vertical scaling?
   - Caching strategy?

7. **Availability Approach**
   - How ensure high availability?
   - Redundancy strategy?
   - Failover approach?

8. **Trade-offs**
   - What are you sacrificing?
   - What are you gaining?
   - Be honest

9. **Alternatives Considered**
   - What else did you consider?
   - Why did you reject them?

Base all decisions on the SPECIFIC requirements, not generic best practices.

Respond in valid JSON format."""

        return prompt

    def _format_list(self, items: list) -> str:
        """Format list"""
        if not items:
            return "None specified"
        return "\n".join([f"- {item}" for item in items])

    def _parse_decision_response(self, response: str) -> Dict[str, Any]:
        """Parse tech stack decision response"""
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            decision_data = json.loads(response)

            # Ensure required fields
            required_fields = [
                "language", "language_justification",
                "database", "database_justification",
                "architecture_pattern", "architecture_justification",
                "scalability_approach", "availability_approach",
                "trade_offs"
            ]

            for field in required_fields:
                if field not in decision_data:
                    logger.warning(f"Missing tech decision field: {field}")
                    if field.endswith("_justification") or field.endswith("_approach"):
                        decision_data[field] = f"Standard {field}"
                    elif field == "trade_offs":
                        decision_data[field] = []
                    else:
                        decision_data[field] = "standard"

            if "additional_technologies" not in decision_data:
                decision_data["additional_technologies"] = {}
            if "alternatives_considered" not in decision_data:
                decision_data["alternatives_considered"] = []

            return decision_data

        except Exception as e:
            logger.error("tech_decision_parse_error", error=str(e))

            # Fallback
            return {
                "language": "python",
                "language_justification": "Versatile and widely supported",
                "framework": None,
                "framework_justification": None,
                "database": "postgresql",
                "database_justification": "Robust RDBMS with ACID compliance",
                "architecture_pattern": "monolith",
                "architecture_justification": "Simplicity for initial version",
                "additional_technologies": {},
                "scalability_approach": "Horizontal scaling with load balancing",
                "availability_approach": "Multi-instance deployment with health checks",
                "trade_offs": ["Simplicity over maximum scalability"],
                "alternatives_considered": []
            }
