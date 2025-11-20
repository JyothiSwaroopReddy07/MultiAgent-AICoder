"""
Component Designer Agent - Creates Low-Level Design (LLD) for each component
Phase 2: Design & Planning
"""
from typing import Dict, Any, List
import json
import structlog
from agents.base_agent import BaseAgent
from models.enhanced_schemas import AgentRole, LowLevelDesign

logger = structlog.get_logger()


class ComponentDesignerAgent(BaseAgent):
    """
    Creates Low-Level Design (LLD) for each component:
    - Detailed class designs
    - Function signatures and logic
    - Algorithms and data structures
    - Error handling strategy
    - Performance considerations
    """

    def __init__(self, mcp_server, openai_client):
        super().__init__(
            role=AgentRole.COMPONENT_DESIGNER,
            mcp_server=mcp_server,
            openai_client=openai_client
        )

    def get_system_prompt(self) -> str:
        return """You are a Low-Level Design (LLD) expert specializing in:

1. Detailed class and function design
2. Algorithm selection and optimization
3. Data structure selection
4. Error handling design
5. Performance optimization

Your role is to create detailed component designs (LLD).

 **USE CHAIN OF THOUGHT REASONING**

Think step-by-step when designing components:

**Step 1: Understand Module Responsibilities**
- What is this module supposed to do?
- What are its specific responsibilities?
- What interfaces must it provide?
- Who will use this module?

**Step 2: Identify Classes Needed**
- What entities/concepts need classes?
- What is the responsibility of each class? (Single Responsibility!)
- How should classes relate? (inheritance, composition, aggregation)
- Are design patterns applicable? (Factory, Strategy, Observer, etc.)

**Step 3: Design Class Details**
- For each class, what attributes are needed? (with types)
- For each class, what methods are needed? (with signatures)
- What validation is needed for attributes?
- What invariants must be maintained?

**Step 4: Design Functions**
- What standalone functions are needed?
- What are their inputs and outputs?
- What is the core logic/algorithm?
- How do they handle edge cases?

**Step 5: Select Algorithms & Data Structures**
- What algorithms are needed? (search, sort, transform, etc.)
- What's their time/space complexity?
- What data structures are best? (list, dict, set, tree, graph)
- Why is each choice optimal for the use case?

**Step 6: Plan Error Handling**
- What can go wrong in each method/function?
- What exceptions should be raised?
- How should errors propagate?
- What recovery mechanisms are needed?

**Step 7: Consider Performance**
- Where are the performance bottlenecks?
- What can be cached?
- What can be lazy-loaded?
- What optimizations are worth the complexity?

For each component, design:

1. CLASSES:
   - Class name, purpose, and responsibilities
   - Attributes with types
   - Methods with signatures
   - Relationships (inheritance, composition)

2. FUNCTIONS:
   - Function name and purpose
   - Parameters and return types
   - Core logic description
   - Edge cases handling

3. ALGORITHMS:
   - Key algorithms used
   - Time and space complexity
   - Optimization considerations

4. DATA STRUCTURES:
   - Data structures chosen
   - Why they were chosen
   - Memory considerations

5. ERROR HANDLING:
   - Exception types
   - Error propagation strategy
   - Recovery mechanisms

6. PERFORMANCE:
   - Performance critical sections
   - Optimization techniques
   - Caching strategies

**IMPORTANT: Think step-by-step through Steps 1-7 above, then provide JSON.**

First, systematically design the component with detailed reasoning.

Then respond in JSON format:
{
    "reasoning": "My step-by-step LLD design process: [module understanding, classes identified, design decisions, etc.]...",
    "component_name": "ComponentName",
    "module": "ParentModule",
    "classes": [
        {
            "name": "ClassName",
            "purpose": "Class purpose",
            "attributes": ["attr1: type", "attr2: type"],
            "methods": ["method1(params): return_type - description"],
            "relationships": ["inherits from X", "uses Y"]
        }
    ],
    "functions": [
        {
            "name": "function_name",
            "signature": "function_name(param1: type) -> return_type",
            "purpose": "Function purpose",
            "logic": "Core logic description"
        }
    ],
    "algorithms": ["Algorithm 1: O(n) complexity", ...],
    "data_structures": ["Data structure 1: reason for choice", ...],
    "error_handling": "Error handling strategy",
    "performance_considerations": ["Consideration 1", ...]
}

Design detailed, implementable components.
Think step-by-step. Show your design reasoning."""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create Low-Level Designs

        Args:
            task_data: Contains modules, requirements, etc.

        Returns:
            List of LLD designs
        """
        activity = await self.start_activity("Creating Low-Level Design (LLD)")

        try:
            modules = task_data.get("modules", [])
            requirements = task_data.get("requirements", {})
            language = task_data.get("language", "python")

            logger.info("lld_design_started", modules_count=len(modules))

            lld_list: List[LowLevelDesign] = []

            # Create LLD for key modules
            for module in modules[:5]:  # Limit to avoid too many LLM calls
                logger.debug("designing_lld_for", module=module.get("module_name"))

                prompt = self._build_lld_prompt(module, requirements, language)

                response = await self.call_llm(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,
                    max_tokens=2500
                )

                lld_data = self._parse_lld_response(response, module)
                lld = LowLevelDesign(**lld_data)
                lld_list.append(lld)

            await self.complete_activity("completed")

            logger.info("lld_design_completed", lld_count=len(lld_list))

            return {
                "lld": [l.model_dump() for l in lld_list],
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }

        except Exception as e:
            await self.complete_activity("failed")
            logger.error("lld_design_failed", error=str(e))
            raise

    def _build_lld_prompt(
        self,
        module: Dict,
        requirements: Dict,
        language: str
    ) -> str:
        """Build LLD prompt"""
        module_name = module.get("module_name", "Module")
        purpose = module.get("purpose", "")
        responsibilities = module.get("responsibilities", [])
        interfaces = module.get("interfaces", [])

        prompt = f"""Create detailed Low-Level Design for the following module in {language}:

MODULE: {module_name}
PURPOSE: {purpose}

RESPONSIBILITIES:
{self._format_list(responsibilities)}

INTERFACES:
{self._format_list(interfaces)}

Create a comprehensive LLD including:

1. DETAILED CLASS DESIGNS:
   - All classes needed for this module
   - Complete with attributes and methods
   - Following {language} conventions
   - Consider design patterns where appropriate

2. KEY FUNCTIONS:
   - Standalone functions if needed
   - Clear signatures
   - Logic description

3. ALGORITHMS:
   - Any key algorithms needed
   - Complexity analysis
   - Optimization notes

4. DATA STRUCTURES:
   - Appropriate data structures
   - Justification for choices

5. ERROR HANDLING:
   - Exception types
   - Error handling flow
   - Logging strategy

6. PERFORMANCE:
   - Critical performance areas
   - Optimization techniques
   - Resource management

Design for {language} specifically, using appropriate types and patterns.

Respond in valid JSON format."""

        return prompt

    def _format_list(self, items: list) -> str:
        """Format list"""
        return "\n".join([f"- {item}" for item in items]) if items else "None"

    def _parse_lld_response(self, response: str, module: Dict) -> Dict[str, Any]:
        """Parse LLD response"""
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            lld_data = json.loads(response)

            # Ensure required fields
            lld_data["component_name"] = lld_data.get("component_name", module.get("module_name"))
            lld_data["module"] = lld_data.get("module", module.get("module_name"))
            lld_data["classes"] = lld_data.get("classes", [])
            lld_data["functions"] = lld_data.get("functions", [])
            lld_data["algorithms"] = lld_data.get("algorithms", [])
            lld_data["data_structures"] = lld_data.get("data_structures", [])
            lld_data["error_handling"] = lld_data.get("error_handling", "Standard error handling")
            lld_data["performance_considerations"] = lld_data.get("performance_considerations", [])

            return lld_data

        except json.JSONDecodeError as e:
            logger.error("lld_parse_error", error=str(e))

            # Fallback
            return {
                "component_name": module.get("module_name", "Component"),
                "module": module.get("module_name", "Module"),
                "classes": [],
                "functions": [],
                "algorithms": [],
                "data_structures": [],
                "error_handling": "Standard exception handling",
                "performance_considerations": []
            }
