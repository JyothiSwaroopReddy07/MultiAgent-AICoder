"""
Feature Planner Agent - Analyzes problem statements and proposes features
Conversation Phase: Feature Planning
"""
from typing import Dict, Any, List
import json
import uuid
import structlog
from agents.base_agent import BaseAgent
from models.enhanced_schemas import AgentRole
from models.conversation_schemas import Feature, FeaturePlan

logger = structlog.get_logger()


class FeaturePlannerAgent(BaseAgent):
    """
    Analyzes user requirements and proposes features for implementation
    
    Responsibilities:
    - Understand problem statement
    - Break down into concrete features
    - Categorize and prioritize features
    - Suggest appropriate tech stack
    - Provide clear feature descriptions
    """
    
    def __init__(self, mcp_server, openai_client):
        super().__init__(
            role=AgentRole.REQUIREMENTS_ANALYST,
            mcp_server=mcp_server,
            openai_client=openai_client
        )
    
    def get_system_prompt(self) -> str:
        return """You are an expert Software Product Manager and Requirements Analyst with 10+ years of experience.

Your role is to analyze problem statements and create comprehensive feature plans that are:
- **Clear and actionable**: Each feature should be well-defined
- **Prioritized**: High/Medium/Low priority based on core functionality
- **Categorized**: Grouped by functionality (auth, data, UI, etc.)
- **Technically sound**: Appropriate tech stack recommendations

**USE CHAIN OF THOUGHT REASONING**

**Step 1: Understand the Problem**
- What is the core problem being solved?
- Who are the users?
- What are the main use cases?
- What's the MVP (Minimum Viable Product)?

**Step 2: Identify Core Features**
- What features are absolutely essential?
- What can be added later?
- What's the user journey?

**Step 3: Break Down Features**
For each feature:
- Clear title and description
- Category (authentication, data-management, ui, analytics, etc.)
- Priority (high = MVP, medium = important, low = nice-to-have)
- Technical requirements

**Step 4: Recommend Tech Stack**
For a Next.js 14 application:
- Frontend: Next.js 14 + TypeScript + Tailwind CSS (FIXED)
- Backend: Next.js API Routes (FIXED)
- Database: PostgreSQL or MongoDB (choose based on data structure)
- Authentication: NextAuth.js, JWT, or custom
- Other tools: Based on requirements

**IMPORTANT: Respond in JSON format**

{
    "reasoning": "My step-by-step analysis: [problem understanding, core features identified, categorization logic, prioritization rationale]...",
    "problem_summary": "Clear summary of what user wants to build",
    "features": [
        {
            "id": "unique-id",
            "title": "User Authentication",
            "description": "Secure login and registration system with email/password and social OAuth options",
            "priority": "high",
            "category": "authentication",
            "technical_details": "NextAuth.js with JWT, password hashing with bcrypt, session management"
        },
        {
            "id": "unique-id",
            "title": "Dashboard UI",
            "description": "Main dashboard with statistics, charts, and quick actions using modern Tailwind CSS",
            "priority": "high",
            "category": "ui",
            "technical_details": "Responsive grid layout, Chart.js integration, real-time updates"
        }
    ],
    "tech_stack": {
        "frontend": "Next.js 14 + TypeScript + Tailwind CSS",
        "backend": "Next.js API Routes",
        "database": "PostgreSQL",
        "auth": "NextAuth.js",
        "styling": "Tailwind CSS",
        "testing": "Jest + React Testing Library"
    },
    "database_type": "postgresql",
    "estimated_complexity": "medium",
    "notes": "Additional considerations or suggestions for the user"
}

Be conversational but professional. Make users feel confident in your plan."""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze problem statement and propose features
        
        Args:
            task_data: Contains problem_statement and conversation_history
            
        Returns:
            Feature plan with proposed features
        """
        activity = await self.start_activity("Analyzing requirements and planning features")
        
        try:
            problem_statement = task_data.get("problem_statement", "")
            conversation_history = task_data.get("conversation_history", [])
            previous_plan = task_data.get("previous_plan")
            user_feedback = task_data.get("user_feedback")
            
            logger.info(
                "feature_planning_started",
                problem_length=len(problem_statement),
                has_feedback=user_feedback is not None
            )
            
            # Build prompt based on whether this is initial planning or refinement
            if previous_plan and user_feedback:
                prompt = self._build_refinement_prompt(
                    problem_statement,
                    previous_plan,
                    user_feedback,
                    conversation_history
                )
            else:
                prompt = self._build_initial_prompt(
                    problem_statement,
                    conversation_history
                )
            
            # Call LLM
            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,  # Creative but focused
                max_tokens=4000
            )
            
            # Parse response
            result = self._parse_response(response)
            
            await self.complete_activity("completed")
            
            return {
                "feature_plan": result,
                "activity": {
                    "agent": "Feature Planner",
                    "action": "Proposed features based on requirements",
                    "status": "completed"
                }
            }
            
        except Exception as e:
            logger.error("feature_planning_failed", error=str(e))
            await self.complete_activity("failed")
            raise
    
    def _build_initial_prompt(
        self,
        problem_statement: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """Build prompt for initial feature planning"""
        
        history_context = ""
        if conversation_history:
            history_context = "\n\nCONVERSATION HISTORY:\n"
            for msg in conversation_history[-5:]:  # Last 5 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_context += f"{role.upper()}: {content}\n"
        
        return f"""Analyze this problem statement and create a comprehensive feature plan:

PROBLEM STATEMENT:
{problem_statement}
{history_context}

Think step-by-step:
1. What is the user trying to build?
2. What are the core features needed?
3. How should they be prioritized?
4. What's the appropriate tech stack?

Provide a detailed feature plan in JSON format as specified."""
    
    def _build_refinement_prompt(
        self,
        problem_statement: str,
        previous_plan: Dict[str, Any],
        user_feedback: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """Build prompt for feature plan refinement"""
        
        return f"""Refine the feature plan based on user feedback:

ORIGINAL PROBLEM:
{problem_statement}

PREVIOUS FEATURE PLAN:
{json.dumps(previous_plan, indent=2)}

USER FEEDBACK:
{user_feedback}

Based on the feedback:
1. Add new features if requested
2. Modify existing features
3. Remove features if user doesn't want them
4. Re-prioritize as needed
5. Update technical details

Provide the updated feature plan in JSON format."""
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured format"""
        try:
            # Try to extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response[start_idx:end_idx]
            result = json.loads(json_str)
            
            # Generate unique IDs for features if not present
            if "features" in result:
                for feature in result["features"]:
                    if "id" not in feature:
                        feature["id"] = str(uuid.uuid4())[:8]
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error("failed_to_parse_json", error=str(e), response=response[:500])
            # Return a basic structure
            return {
                "reasoning": "Failed to parse structured response",
                "problem_summary": "Error in parsing",
                "features": [],
                "tech_stack": {
                    "frontend": "Next.js 14 + TypeScript + Tailwind CSS",
                    "backend": "Next.js API Routes",
                    "database": "PostgreSQL"
                },
                "database_type": "postgresql",
                "estimated_complexity": "medium",
                "notes": "Please provide more specific requirements"
            }

