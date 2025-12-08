# Jyothi Swaroop - 59607464

"""
Feature Planner Agent - Proposes features and gets user confirmation before code generation
"""
from typing import Dict, Any, List, Optional
import json
import structlog

from agents.base_agent import BaseAgent
from models.schemas import AgentRole

logger = structlog.get_logger()


class FeaturePlannerAgent(BaseAgent):
    """
    Feature Planner Agent that analyzes requirements and proposes detailed features.
    
    This agent:
    1. Analyzes the problem statement
    2. Proposes a list of features with descriptions
    3. Asks user for confirmation/modifications
    4. Returns the finalized feature list for code generation
    """

    def __init__(self, mcp_server=None, openai_client=None):
        super().__init__(
            role=AgentRole.MODULE_DESIGNER,
            mcp_server=mcp_server,
            openai_client=openai_client
        )

    def get_system_prompt(self) -> str:
        return """You are a Product Manager expert. Analyze requirements and propose CONCISE feature lists.

IMPORTANT: Keep responses SHORT. No verbose descriptions. Maximum 5-7 core features, 3-4 optional.

## Response Format (STRICTLY follow this compact format)

```json
{
    "app_name": "App Name",
    "app_description": "One sentence description",
    "core_features": [
        {
            "name": "Feature Name",
            "description": "One sentence",
            "priority": "must-have",
            "complexity": "medium"
        }
    ],
    "optional_features": [
        {
            "name": "Feature Name",
            "description": "One sentence",
            "priority": "nice-to-have",
            "complexity": "low"
        }
    ],
    "tech_recommendations": {
        "frontend": "React/Next.js",
        "backend": "Node.js or Python",
        "database": "PostgreSQL or MongoDB"
    },
    "estimated_files": 15,
    "estimated_complexity": "medium"
}
```

RULES:
- Keep descriptions to ONE sentence max
- No acceptance_criteria, no user_stories, no technical_notes
- Maximum 7 core features, 4 optional features
- Be practical and focused
"""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a feature planning task.
        
        Args:
            task_data: Contains 'problem_statement' and optionally 'user_feedback'
            
        Returns:
            Feature plan result
        """
        problem_statement = task_data.get("problem_statement", "")
        user_feedback = task_data.get("user_feedback")
        current_plan = task_data.get("feature_plan")
        
        if user_feedback and current_plan:
            return await self.refine_features(current_plan, user_feedback)
        else:
            return await self.propose_features(problem_statement)

    async def propose_features(
        self,
        problem_statement: str
    ) -> Dict[str, Any]:
        """
        Analyze problem statement and propose features
        """
        activity = await self.start_activity("Analyzing requirements and proposing features")
        
        try:
            prompt = f"""Analyze this requirement and propose a CONCISE feature list:

{problem_statement}

Reply with compact JSON. Max 7 core features, 4 optional. One-sentence descriptions only."""

            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=8192
            )
            
            feature_plan = self._parse_feature_plan(response)
            
            await self.complete_activity("completed")
            
            return {
                "feature_plan": feature_plan,
                "raw_response": response,
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }
            
        except Exception as e:
            await self.complete_activity("failed")
            logger.error("feature_planning_failed", error=str(e))
            raise

    async def refine_features(
        self,
        feature_plan: Dict[str, Any],
        user_feedback: str
    ) -> Dict[str, Any]:
        """
        Refine feature plan based on user feedback
        """
        activity = await self.start_activity("Refining features based on feedback")
        
        try:
            prompt = f"""Refine this feature plan based on user feedback:

Current Plan:
{json.dumps(feature_plan, indent=2)}

User Feedback: {user_feedback}

Return updated JSON. Keep it concise. Same structure."""

            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=8192
            )
            
            refined_plan = self._parse_feature_plan(response)
            
            await self.complete_activity("completed")
            
            return {
                "feature_plan": refined_plan,
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }
            
        except Exception as e:
            await self.complete_activity("failed")
            logger.error("feature_refinement_failed", error=str(e))
            raise

    def _parse_feature_plan(self, response: str) -> Dict[str, Any]:
        """Parse feature plan response with truncation recovery"""
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning("feature_plan_parse_error", error=str(e), attempting_recovery=True)
            
            recovered = self._attempt_json_recovery(response)
            if recovered:
                return recovered
            
            return {
                "app_name": "Application",
                "core_features": [],
                "optional_features": [],
                "error": str(e)
            }
    
    def _attempt_json_recovery(self, truncated: str) -> Optional[Dict[str, Any]]:
        """Attempt to recover partial JSON from truncated response"""
        import re
        
        try:
            app_name_match = re.search(r'"app_name"\s*:\s*"([^"]+)"', truncated)
            app_desc_match = re.search(r'"app_description"\s*:\s*"([^"]+)"', truncated)
            
            core_features = []
            feature_pattern = re.compile(
                r'\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"description"\s*:\s*"([^"]+)"\s*,\s*"priority"\s*:\s*"([^"]+)"\s*,\s*"complexity"\s*:\s*"([^"]+)"',
                re.DOTALL
            )
            
            core_section = re.search(r'"core_features"\s*:\s*\[(.*?)(?:\]|"optional_features")', truncated, re.DOTALL)
            if core_section:
                for match in feature_pattern.finditer(core_section.group(1)):
                    core_features.append({
                        "name": match.group(1),
                        "description": match.group(2),
                        "priority": match.group(3),
                        "complexity": match.group(4)
                    })
            
            optional_features = []
            optional_section = re.search(r'"optional_features"\s*:\s*\[(.*?)(?:\]|"tech_recommendations")', truncated, re.DOTALL)
            if optional_section:
                for match in feature_pattern.finditer(optional_section.group(1)):
                    optional_features.append({
                        "name": match.group(1),
                        "description": match.group(2),
                        "priority": match.group(3),
                        "complexity": match.group(4)
                    })
            
            tech_match = re.search(
                r'"tech_recommendations"\s*:\s*\{\s*"frontend"\s*:\s*"([^"]+)"\s*,\s*"backend"\s*:\s*"([^"]+)"\s*,\s*"database"\s*:\s*"([^"]+)"',
                truncated
            )
            
            files_match = re.search(r'"estimated_files"\s*:\s*(\d+)', truncated)
            complexity_match = re.search(r'"estimated_complexity"\s*:\s*"([^"]+)"', truncated)
            
            if core_features:
                logger.info("json_recovery_success", features_recovered=len(core_features))
                return {
                    "app_name": app_name_match.group(1) if app_name_match else "Application",
                    "app_description": app_desc_match.group(1) if app_desc_match else "",
                    "core_features": core_features,
                    "optional_features": optional_features,
                    "tech_recommendations": {
                        "frontend": tech_match.group(1) if tech_match else "React",
                        "backend": tech_match.group(2) if tech_match else "Node.js",
                        "database": tech_match.group(3) if tech_match else "PostgreSQL"
                    } if tech_match else {},
                    "estimated_files": int(files_match.group(1)) if files_match else 15,
                    "estimated_complexity": complexity_match.group(1) if complexity_match else "medium",
                    "recovered": True
                }
            
            return None
            
        except Exception as e:
            logger.error("json_recovery_failed", error=str(e))
            return None

    def format_features_for_display(self, feature_plan: Dict[str, Any]) -> str:
        """Format feature plan for user-friendly display"""
        output = []
        
        app_name = feature_plan.get("app_name", "Application")
        app_desc = feature_plan.get("app_description", "")
        
        output.append(f"## 📱 {app_name}")
        if app_desc:
            output.append(f"*{app_desc}*\n")
        
        core_features = feature_plan.get("core_features", [])
        if core_features:
            output.append("### ✅ Core Features (Must-Have)")
            for i, f in enumerate(core_features, 1):
                output.append(f"**{i}. {f.get('name', 'Feature')}**")
                output.append(f"   {f.get('description', '')}")
                if f.get('user_story'):
                    output.append(f"   📝 {f.get('user_story')}")
                output.append("")
        
        optional_features = feature_plan.get("optional_features", [])
        if optional_features:
            output.append("### 💡 Optional Features (Nice-to-Have)")
            for i, f in enumerate(optional_features, 1):
                output.append(f"**{i}. {f.get('name', 'Feature')}**")
                output.append(f"   {f.get('description', '')}")
                output.append("")
        
        tech = feature_plan.get("tech_recommendations", {})
        if tech:
            output.append("### 🛠️ Technical Recommendations")
            output.append(f"- **Frontend**: {tech.get('frontend', 'N/A')}")
            output.append(f"- **Backend**: {tech.get('backend', 'N/A')}")
            output.append(f"- **Database**: {tech.get('database', 'N/A')}")
            output.append("")
        
        estimated = feature_plan.get("estimated_files", 0)
        complexity = feature_plan.get("estimated_complexity", "medium")
        output.append(f"📊 **Estimated**: {estimated} files | Complexity: {complexity}")
        
        return "\n".join(output)

