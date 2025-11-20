"""
Module Designer Agent - Plans what modules the project needs
Phase 2: Design & Planning
"""
from typing import Dict, Any, List
import json
import structlog
from agents.base_agent import BaseAgent
from models.enhanced_schemas import AgentRole, ModuleDesign

logger = structlog.get_logger()


class ModuleDesignerAgent(BaseAgent):
    """
    Designs module-level architecture:
    - Identifies all modules needed
    - Defines module responsibilities
    - Designs module interfaces/APIs
    - Plans module dependencies
    - Defines data models for each module
    """

    def __init__(self, mcp_server, openai_client):
        super().__init__(
            role=AgentRole.MODULE_DESIGNER,
            mcp_server=mcp_server,
            openai_client=openai_client
        )

    def get_system_prompt(self) -> str:
        return """You are a Module Design expert specializing in:

1. Breaking down systems into cohesive modules
2. Applying SOLID principles and clean architecture
3. Designing clear module interfaces
4. Managing module dependencies
5. Ensuring high cohesion and low coupling

 **USE CHAIN OF THOUGHT REASONING**

Think step-by-step when designing modules:

**Step 1: Understand the System**
- What is the system's purpose?
- What are the major functional areas?
- What are the main business domains?

**Step 2: Identify Module Candidates**
- Group related functionality together
- Look for bounded contexts (DDD)
- Consider: User management, data access, business logic, API, etc.
- List 5-10 potential modules

**Step 3: Apply Single Responsibility**
- For each module, what is its ONE main purpose?
- Is the module doing too much? → Split it
- Is functionality scattered? → Consolidate

**Step 4: Define Module Interfaces**
- What public APIs should each module expose?
- Keep interfaces minimal and clear
- Think about: What do other modules need from this one?

**Step 5: Map Dependencies**
- Which modules depend on which others?
- Ensure no circular dependencies
- Prefer depending on abstractions

**Step 6: Validate Design**
- High cohesion within modules? (related functionality together)
- Low coupling between modules? (minimal dependencies)
- Clear interfaces? (easy to understand and use)

Your role is to design the module structure for software systems.

For each module, define:

1. MODULE NAME: Clear, descriptive name
2. PURPOSE: Single responsibility of the module
3. RESPONSIBILITIES: Specific tasks the module handles
4. INTERFACES: Public APIs/methods the module exposes
5. DEPENDENCIES: Other modules this module depends on
6. DATA MODELS: Key data structures/models used

Design principles:
- Single Responsibility Principle
- High cohesion within modules
- Low coupling between modules
- Clear, minimal interfaces
- Dependency direction (depend on abstractions)

**IMPORTANT: Think step-by-step through Steps 1-6 above, then provide JSON.**

First, reason through your module design systematically.

Then respond with a JSON object:
{
    "reasoning": "My step-by-step module design process...",
    "modules": [
        {
            "module_name": "ModuleName",
            "purpose": "Clear, concise purpose",
            "responsibilities": ["Responsibility 1", "Responsibility 2", ...],
            "interfaces": ["Interface 1: description", ...],
            "dependencies": ["Module1", "Module2", ...],
            "data_models": ["Model1", "Model2", ...]
        },
        ...
    ]
}

Design clean, maintainable module architectures.
Think step-by-step. Show your modular design reasoning."""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Design module architecture

        Args:
            task_data: Contains HLD, requirements, etc.

        Returns:
            List of module designs
        """
        activity = await self.start_activity("Designing module architecture")

        try:
            hld = task_data.get("hld", {})
            requirements = task_data.get("requirements", {})
            language = task_data.get("language", "python")

            logger.info("module_design_started")

            prompt = self._build_module_design_prompt(hld, requirements, language)

            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=3000
            )

            modules_data = self._parse_modules_response(response)
            modules = [ModuleDesign(**m) for m in modules_data]

            await self.complete_activity("completed")

            logger.info(
                "module_design_completed",
                modules_count=len(modules)
            )

            return {
                "modules": [m.model_dump() for m in modules],
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }

        except Exception as e:
            await self.complete_activity("failed")
            logger.error("module_design_failed", error=str(e))
            raise

    def _build_module_design_prompt(
        self,
        hld: Dict,
        requirements: Dict,
        language: str
    ) -> str:
        """Build module design prompt"""
        major_components = hld.get("major_components", [])
        functional = requirements.get("functional", [])

        prompt = f"""Design the module architecture for a {language} system:

HIGH-LEVEL ARCHITECTURE:
Architecture Pattern: {hld.get('architecture_pattern', 'Not specified')}
Major Components: {', '.join(major_components)}

KEY FUNCTIONAL REQUIREMENTS:
{self._format_list(functional[:10])}

COMPONENT INTERACTIONS:
{json.dumps(hld.get('component_interactions', {}), indent=2)}

Based on this architecture, design the modules needed. For each major component,
break it down into cohesive modules.

Consider:
- Each module should have a single, clear responsibility
- Modules should be loosely coupled
- Design clear interfaces between modules
- Plan for testability
- Consider module reusability

Design all necessary modules including:
- Core business logic modules
- Data access modules
- API/interface modules
- Utility modules
- Configuration modules

Respond with a JSON array of module designs."""

        return prompt

    def _format_list(self, items: list) -> str:
        """Format list"""
        return "\n".join([f"- {item}" for item in items]) if items else "None"

    def _parse_modules_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse modules response"""
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            modules_data = json.loads(response)

            if not isinstance(modules_data, list):
                logger.warning("Modules response not a list, wrapping")
                modules_data = [modules_data]

            # Validate each module has required fields
            for module in modules_data:
                if "module_name" not in module:
                    module["module_name"] = "UnnamedModule"
                if "purpose" not in module:
                    module["purpose"] = "Module purpose"
                if "responsibilities" not in module:
                    module["responsibilities"] = []
                if "interfaces" not in module:
                    module["interfaces"] = []
                if "dependencies" not in module:
                    module["dependencies"] = []
                if "data_models" not in module:
                    module["data_models"] = []

            return modules_data

        except json.JSONDecodeError as e:
            logger.error("modules_parse_error", error=str(e))

            # Fallback
            return [
                {
                    "module_name": "CoreModule",
                    "purpose": "Core business logic",
                    "responsibilities": ["Handle main functionality"],
                    "interfaces": ["Public API"],
                    "dependencies": [],
                    "data_models": ["MainModel"]
                }
            ]
