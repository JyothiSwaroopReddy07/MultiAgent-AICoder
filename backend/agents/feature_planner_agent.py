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
        return """You are a Product Manager and Feature Analyst expert.

Your task is to analyze a problem statement and propose a comprehensive list of features that should be implemented.

For each feature, provide:
1. **name**: Short, descriptive name
2. **description**: What this feature does
3. **priority**: "must-have", "should-have", or "nice-to-have"
4. **complexity**: "low", "medium", or "high"
5. **user_story**: As a [user], I want [feature] so that [benefit]
6. **acceptance_criteria**: List of criteria to consider the feature complete

## Response Format

```json
{
    "app_name": "Suggested application name",
    "app_description": "Brief description of the application",
    "target_users": ["Primary user types"],
    "core_features": [
        {
            "name": "Feature Name",
            "description": "What this feature does",
            "priority": "must-have",
            "complexity": "medium",
            "user_story": "As a user, I want X so that Y",
            "acceptance_criteria": [
                "Criterion 1",
                "Criterion 2"
            ],
            "technical_notes": "Any technical considerations"
        }
    ],
    "optional_features": [
        {
            "name": "Optional Feature",
            "description": "Nice-to-have feature",
            "priority": "nice-to-have",
            "complexity": "low"
        }
    ],
    "tech_recommendations": {
        "frontend": "Recommended frontend stack",
        "backend": "Recommended backend stack",
        "database": "Recommended database",
        "reasoning": "Why these technologies"
    },
    "estimated_files": 15,
    "estimated_complexity": "medium"
}
```

Be thorough but realistic. Focus on features that solve the user's actual problem.
Prioritize core functionality over bells and whistles.
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
            prompt = f"""Analyze this application requirement and propose a comprehensive feature list:

## Problem Statement
{problem_statement}

## Instructions
1. Identify the core problem being solved
2. List all essential features (must-have)
3. List recommended features (should-have)
4. List optional enhancements (nice-to-have)
5. Provide technical recommendations
6. Estimate complexity

Be specific and actionable. Each feature should be clearly defined.

Respond with a complete JSON feature plan."""

            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=4000
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

## Current Feature Plan
{json.dumps(feature_plan, indent=2)}

## User Feedback
{user_feedback}

## Instructions
1. Incorporate the user's suggestions
2. Add any new features they requested
3. Remove or modify features they don't want
4. Keep the same JSON structure
5. Update priorities if needed

Respond with the updated JSON feature plan."""

            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=4000
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
        """Parse feature plan response"""
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
            logger.error("feature_plan_parse_error", error=str(e))
            return {
                "app_name": "Application",
                "core_features": [],
                "optional_features": [],
                "error": str(e)
            }

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

