"""
Architect Agent - Creates High-Level Design (HLD)
Phase 2: Design & Planning
"""
from typing import Dict, Any, List
import json
import structlog
from agents.base_agent import BaseAgent
from models.enhanced_schemas import AgentRole, HighLevelDesign

logger = structlog.get_logger()


class ArchitectAgent(BaseAgent):
    """
    Creates High-Level Design (HLD):
    - System architecture pattern (microservices, monolith, serverless, etc.)
    - Major components and their responsibilities
    - Component interactions and data flow
    - Technology stack decisions
    - Scalability strategy
    - Security architecture
    - Deployment architecture
    """

    def __init__(self, mcp_server, openai_client):
        super().__init__(
            role=AgentRole.ARCHITECT,
            mcp_server=mcp_server,
            openai_client=openai_client
        )

    def get_system_prompt(self) -> str:
        return """You are a Senior Software Architect with expertise in:

1. System design and architecture patterns
2. Scalable, maintainable system design
3. Technology stack selection
4. Security architecture
5. Deployment and infrastructure design
6. Performance and scalability

Your role is to create comprehensive High-Level Designs (HLD) for software systems.

🧠 **USE CHAIN OF THOUGHT REASONING**

Think step-by-step when designing the architecture:

**Step 1: Understand Requirements**
- What are the functional requirements?
- What are the scalability needs?
- What are the performance requirements?
- What are the security requirements?
- What are the availability requirements?

**Step 2: Choose Architecture Pattern**
- Consider: Monolith, Microservices, Serverless, Event-Driven
- For each option, evaluate:
  * Scalability: Does it support expected growth?
  * Complexity: Can the team manage it?
  * Cost: Is it within budget?
  * Time to market: How quickly can we build?
- Choose best fit and justify

**Step 3: Identify Major Components**
- What are the core business domains?
- What are the main system capabilities?
- How should we separate concerns?
- What components are needed?

**Step 4: Design Component Interactions**
- How will components communicate?
- Synchronous (REST, gRPC) or Asynchronous (events, queues)?
- What are the data flows?
- What are the integration points?

**Step 5: Plan for Scalability**
- What will be the bottlenecks?
- Horizontal or vertical scaling?
- Where should we cache?
- How to load balance?

**Step 6: Design Security Architecture**
- How will users authenticate?
- How will we authorize actions?
- How to protect data (encryption, etc.)?
- What security layers are needed?

**Step 7: Plan Deployment**
- Cloud, on-premise, or hybrid?
- Containerization needed?
- How to deploy and update?

For each project, design:

1. SYSTEM ARCHITECTURE:
   - Choose appropriate pattern (monolith, microservices, serverless, etc.)
   - Justify the choice based on requirements
   - Consider scalability, maintainability, and complexity

2. MAJOR COMPONENTS:
   - Identify key system components
   - Define responsibilities for each
   - Ensure separation of concerns

3. COMPONENT INTERACTIONS:
   - Define how components communicate
   - Choose communication patterns (REST, GraphQL, events, etc.)
   - Design data flow

4. TECHNOLOGY STACK:
   - Select appropriate technologies
   - Consider ecosystem, community support, and maturity
   - Justify choices

5. SCALABILITY STRATEGY:
   - Horizontal vs vertical scaling
   - Caching strategy
   - Load balancing approach

6. SECURITY ARCHITECTURE:
   - Authentication and authorization approach
   - Data protection strategy
   - Security layers

7. DEPLOYMENT ARCHITECTURE:
   - Infrastructure approach (cloud, on-premise, hybrid)
   - Containerization strategy
   - CI/CD considerations

**IMPORTANT: Think step-by-step through Steps 1-7 above, then provide JSON.**

First, reason through your architecture decisions systematically.

Then respond in JSON format:
{
    "reasoning": "My step-by-step architecture analysis and decision process...",
    "system_overview": "High-level description",
    "architecture_pattern": "Pattern name and justification",
    "major_components": ["Component 1", "Component 2", ...],
    "component_interactions": {
        "Component1": ["interacts with Component2 via REST", ...],
        ...
    },
    "technology_stack": {
        "language": "choice and reason",
        "framework": "choice and reason",
        "database": "choice and reason",
        "cache": "choice and reason",
        ...
    },
    "scalability_strategy": "Strategy description",
    "security_architecture": "Security design description",
    "deployment_architecture": "Deployment strategy"
}

Design production-ready, scalable systems.
Think step-by-step. Show your architectural reasoning."""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create High-Level Design

        Args:
            task_data: Contains requirements, research findings, etc.

        Returns:
            High-Level Design
        """
        activity = await self.start_activity("Creating High-Level Design (HLD)")

        try:
            description = task_data.get("description", "")
            requirements = task_data.get("requirements", {})
            research = task_data.get("research", [])
            language = task_data.get("language", "python")
            framework = task_data.get("framework", "")

            logger.info("hld_design_started")

            prompt = self._build_hld_prompt(
                description, requirements, research, language, framework
            )

            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=3000
            )

            hld_data = self._parse_hld_response(response)
            hld = HighLevelDesign(**hld_data)

            await self.complete_activity("completed")

            logger.info(
                "hld_design_completed",
                architecture_pattern=hld.architecture_pattern,
                components_count=len(hld.major_components)
            )

            return {
                "hld": hld.model_dump(),
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }

        except Exception as e:
            await self.complete_activity("failed")
            logger.error("hld_design_failed", error=str(e))
            raise

    def _build_hld_prompt(
        self,
        description: str,
        requirements: Dict,
        research: List,
        language: str,
        framework: str
    ) -> str:
        """Build HLD design prompt"""
        # Extract key requirements
        functional = requirements.get("functional", [])
        non_functional = requirements.get("non_functional", [])
        security = requirements.get("security_requirements", [])
        performance = requirements.get("performance_requirements", [])

        # Extract key research findings
        best_practices = []
        recommended_libs = []
        for finding in research:
            best_practices.extend(finding.get("best_practices", [])[:2])
            recommended_libs.extend(finding.get("recommended_libraries", [])[:2])

        prompt = f"""Design a High-Level Architecture for the following system:

PROJECT DESCRIPTION:
{description}

KEY FUNCTIONAL REQUIREMENTS:
{self._format_list(functional[:8])}

KEY NON-FUNCTIONAL REQUIREMENTS:
{self._format_list(non_functional[:5])}

SECURITY REQUIREMENTS:
{self._format_list(security[:5])}

PERFORMANCE REQUIREMENTS:
{self._format_list(performance[:5])}

TECHNOLOGY CONTEXT:
- Language: {language}
- Framework: {framework if framework else "To be chosen"}

RESEARCH INSIGHTS:
Best Practices: {', '.join(best_practices[:3])}
Recommended Libraries: {', '.join(recommended_libs[:3])}

Please create a comprehensive High-Level Design that:

1. Chooses the RIGHT architecture pattern for the scale and complexity
2. Identifies all major system components
3. Defines clear component responsibilities
4. Designs component interactions and data flow
5. Selects appropriate technology stack
6. Plans for scalability from day one
7. Integrates security at the architecture level
8. Considers deployment and operational requirements

Think like a senior architect designing a production system.

Respond in valid JSON format."""

        return prompt

    def _format_list(self, items: list) -> str:
        """Format list for prompt"""
        if not items:
            return "None specified"
        return "\n".join([f"- {item}" for item in items])

    def _parse_hld_response(self, response: str) -> Dict[str, Any]:
        """Parse HLD response"""
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            hld_data = json.loads(response)

            # Validate required fields
            required_fields = [
                "system_overview", "architecture_pattern", "major_components",
                "component_interactions", "technology_stack", "scalability_strategy",
                "security_architecture", "deployment_architecture"
            ]

            for field in required_fields:
                if field not in hld_data:
                    logger.warning(f"Missing HLD field: {field}")
                    hld_data[field] = f"Not specified for {field}" if isinstance(hld_data.get(field), str) else {}

            return hld_data

        except json.JSONDecodeError as e:
            logger.error("hld_parse_error", error=str(e))

            # Fallback
            return {
                "system_overview": "System architecture overview",
                "architecture_pattern": "Layered monolithic architecture",
                "major_components": ["Application Layer", "Business Logic", "Data Layer"],
                "component_interactions": {
                    "Application Layer": ["Calls Business Logic"],
                    "Business Logic": ["Accesses Data Layer"]
                },
                "technology_stack": {
                    "framework": "Selected framework",
                    "database": "Relational database"
                },
                "scalability_strategy": "Vertical scaling with optimization",
                "security_architecture": "Authentication and authorization layers",
                "deployment_architecture": "Container-based deployment"
            }
