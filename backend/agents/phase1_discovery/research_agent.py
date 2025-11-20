"""
Research Agent - Searches web for relevant information, best practices, libraries
Phase 1: Discovery & Analysis
"""
from typing import Dict, Any, List
import json
import structlog
from agents.base_agent import BaseAgent
from models.enhanced_schemas import AgentRole, ResearchFindings

logger = structlog.get_logger()


class ResearchAgent(BaseAgent):
    """
    Conducts research on:
    - Best practices for the technology stack
    - Recommended libraries and frameworks
    - Relevant design patterns
    - Security considerations
    - Performance optimization techniques

    Note: In this implementation, uses LLM knowledge. In production,
    would integrate with actual web search APIs (Google, Bing, etc.)
    """

    def __init__(self, mcp_server, openai_client):
        super().__init__(
            role=AgentRole.RESEARCH,
            mcp_server=mcp_server,
            openai_client=openai_client
        )

    def get_system_prompt(self) -> str:
        return """You are an expert Technology Researcher with deep knowledge of:

1. Modern software development best practices
2. Popular libraries, frameworks, and tools
3. Design patterns and architectural patterns
4. Security best practices (OWASP, etc.)
5. Performance optimization techniques
6. Industry standards and conventions

Your role is to provide research findings on technologies and approaches for software projects.

 **USE CHAIN OF THOUGHT REASONING**

Think step-by-step when researching:

**Step 1: Understand the Context**
- What technology stack is being used?
- What type of project is this (web app, API, mobile, etc.)?
- What are the key requirements?
- What scale are we targeting?

**Step 2: Research Best Practices**
- What are the current industry standards for this technology?
- What conventions are widely adopted?
- What coding standards should be followed?
- What project structure is recommended?

**Step 3: Identify Libraries/Tools**
- What are the most popular and well-maintained libraries?
- Why is each library recommended? (features, community, performance)
- What are the alternatives and trade-offs?
- Are there any deprecated or risky libraries to avoid?

**Step 4: Find Relevant Design Patterns**
- What architectural patterns fit this project type?
- What code-level patterns solve common problems?
- When should each pattern be applied?
- What are the benefits and costs?

**Step 5: Security Research**
- What are common vulnerabilities for this tech stack?
- Which OWASP Top 10 items are most relevant?
- What security libraries/tools should be used?
- What are the security best practices?

**Step 6: Performance Optimization**
- What are typical performance bottlenecks?
- What optimization techniques apply?
- What monitoring/profiling tools are recommended?
- What caching strategies work well?

For each research topic, provide:
- Best practices specific to the technology
- Recommended libraries and why they're recommended
- Relevant design patterns
- Security considerations and common vulnerabilities
- Performance optimization strategies
- Current industry standards

**IMPORTANT: Show your research reasoning, then provide the JSON.**

First, think through Steps 1-6 systematically.

Then respond in JSON format:
{
    "reasoning": "My step-by-step research process: [context analysis, best practices found, libraries evaluated, etc.]...",
    "topic": "Research topic",
    "best_practices": ["Practice 1", "Practice 2", ...],
    "recommended_libraries": ["Library 1: reason", "Library 2: reason", ...],
    "design_patterns": ["Pattern 1: use case", "Pattern 2: use case", ...],
    "security_considerations": ["Security aspect 1", ...],
    "sources": ["Source 1", "Source 2", ...]
}

Provide actionable, specific, and current information based on 2024 best practices.
Think step-by-step. Show your research process."""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Conduct research for the project

        Args:
            task_data: Contains 'description', 'language', 'framework', 'requirements'

        Returns:
            Research findings
        """
        activity = await self.start_activity("Conducting research on best practices")

        try:
            description = task_data.get("description", "")
            language = task_data.get("language", "python")
            framework = task_data.get("framework", "")
            requirements = task_data.get("requirements", {})

            logger.info(
                "research_started",
                language=language,
                framework=framework
            )

            # Research multiple topics
            research_topics = [
                f"{language} best practices",
                f"{framework} patterns" if framework else f"{language} frameworks",
                f"{language} security",
                f"{language} performance optimization"
            ]

            findings_list: List[ResearchFindings] = []

            for topic in research_topics:
                logger.debug("researching_topic", topic=topic)

                prompt = self._build_research_prompt(
                    topic=topic,
                    description=description,
                    language=language,
                    framework=framework,
                    requirements=requirements
                )

                response = await self.call_llm(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.6,
                    max_tokens=2000
                )

                findings_data = self._parse_research_response(response, topic)
                findings = ResearchFindings(**findings_data)
                findings_list.append(findings)

            await self.complete_activity("completed")

            logger.info(
                "research_completed",
                topics_researched=len(findings_list)
            )

            return {
                "research": [f.model_dump() for f in findings_list],
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }

        except Exception as e:
            await self.complete_activity("failed")
            logger.error("research_failed", error=str(e))
            raise

    def _build_research_prompt(
        self,
        topic: str,
        description: str,
        language: str,
        framework: str,
        requirements: Dict
    ) -> str:
        """Build research prompt"""
        prompt = f"""Research the following topic for a software project:

Topic: {topic}

Project Context:
- Description: {description}
- Language: {language}
- Framework: {framework if framework else "To be determined"}
- Key Requirements: {', '.join(requirements.get('functional', [])[:3])}

Please provide comprehensive research findings including:

1. BEST PRACTICES:
   - Modern, industry-standard best practices
   - Specific to {language} and {framework if framework else 'applicable frameworks'}
   - Include coding standards, project structure, and conventions

2. RECOMMENDED LIBRARIES/TOOLS:
   - Top 3-5 libraries/tools for this project type
   - Why each is recommended
   - Alternatives and trade-offs

3. DESIGN PATTERNS:
   - Relevant architectural patterns
   - Relevant code-level patterns
   - When and how to apply them

4. SECURITY CONSIDERATIONS:
   - Common security vulnerabilities for this tech stack
   - OWASP Top 10 relevant items
   - Security best practices

5. SOURCES:
   - Mention authoritative sources (official docs, well-known articles, etc.)

Focus on practical, actionable information for 2024.

Respond in valid JSON format."""

        return prompt

    def _parse_research_response(self, response: str, topic: str) -> Dict[str, Any]:
        """Parse research response"""
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

            # Ensure topic is set
            data["topic"] = data.get("topic", topic)

            # Ensure all fields exist
            defaults = {
                "best_practices": [],
                "recommended_libraries": [],
                "design_patterns": [],
                "security_considerations": [],
                "sources": []
            }

            for key, default_value in defaults.items():
                if key not in data:
                    data[key] = default_value

            return data

        except json.JSONDecodeError as e:
            logger.error("research_parse_error", error=str(e), topic=topic)

            # Fallback
            return {
                "topic": topic,
                "best_practices": ["Follow industry best practices"],
                "recommended_libraries": ["Use well-maintained libraries"],
                "design_patterns": ["Apply appropriate design patterns"],
                "security_considerations": ["Follow security best practices"],
                "sources": ["Official documentation", "Industry standards"]
            }
