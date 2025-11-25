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
- **Cumulative**: When users ask for MORE features, ADD to existing ones (don't replace!)

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

**CRITICAL: When Refining Features (User Feedback)**
- If user says "add X" or "also want Y" or "more features" → KEEP all existing features AND add new ones
- If user says "remove X" or "don't want Y" → Remove specific features only
- If user says "change X to Y" → Modify that specific feature
- If user says "instead of X, do Y" → Replace that specific feature
- DEFAULT: When in doubt, ADD to existing features, don't replace them!

**IMPORTANT: Respond in VALID JSON format**

**CRITICAL: Follow these EXACT field values (case-sensitive):**
- database_type: MUST be "postgresql", "mongodb", or "auto" (NEVER empty, null, or other values)
- estimated_complexity: MUST be "simple", "medium", or "complex" (NEVER "low", "high", empty, or null)
- priority (for each feature): MUST be "high", "medium", or "low" (NEVER empty or null)

**Default values if uncertain:**
- database_type: "auto"
- estimated_complexity: "medium"
- priority: "medium"

**Example Response:**
{
    "reasoning": "Step-by-step analysis: User wants a task management app with user authentication. Core features include CRUD operations for tasks, user login system, and a clean UI. This is a standard web application of medium complexity requiring a relational database for user and task data.",
    "problem_summary": "Task management application with user authentication and CRUD operations",
    "features": [
        {
            "id": "feat-001",
            "title": "User Authentication",
            "description": "Secure login and registration system with email/password and session management",
            "priority": "high",
            "category": "authentication",
            "technical_details": "NextAuth.js with JWT tokens, password hashing with bcrypt, secure session storage"
        },
        {
            "id": "feat-002",
            "title": "Task Management",
            "description": "Create, read, update, and delete tasks with titles, descriptions, and status",
            "priority": "high",
            "category": "data-management",
            "technical_details": "RESTful API endpoints, PostgreSQL database with tasks table, real-time updates"
        },
        {
            "id": "feat-003",
            "title": "Dashboard UI",
            "description": "Clean and responsive interface to display and manage tasks",
            "priority": "high",
            "category": "ui",
            "technical_details": "Tailwind CSS components, responsive grid layout, dark mode support"
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
    "notes": "This is a straightforward CRUD application. Start with core features (auth + task management) and add enhancements later."
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
        
        # Detect if user is asking to ADD features vs REPLACE features
        feedback_lower = user_feedback.lower()
        is_adding = any(word in feedback_lower for word in [
            'add', 'also', 'more', 'additional', 'another', 'include', 
            'plus', 'and also', 'want also', 'need also'
        ])
        is_removing = any(word in feedback_lower for word in [
            'remove', 'delete', 'don\'t want', 'skip', 'exclude', 'without'
        ])
        is_replacing = any(word in feedback_lower for word in [
            'instead', 'replace', 'change to', 'only', 'just'
        ]) and not is_adding
        
        # Build appropriate instruction based on intent
        if is_adding and not is_removing and not is_replacing:
            instruction = """
**IMPORTANT: User is asking to ADD MORE features to the existing plan**

YOU MUST:
1. ✅ KEEP ALL existing features from the previous plan
2. ✅ ADD the new features the user requested
3. ✅ Return ALL features (existing + new) in the updated plan

DO NOT remove or replace existing features unless explicitly asked!
"""
        elif is_removing:
            instruction = """
**User is asking to REMOVE some features**

YOU MUST:
1. Keep features the user wants
2. Remove the specific features they mentioned
3. Return the remaining features
"""
        elif is_replacing:
            instruction = """
**User is asking to REPLACE the plan**

YOU MUST:
1. Create a new plan based on their feedback
2. Replace features as requested
"""
        else:
            instruction = """
**User is asking to MODIFY the plan**

Based on their feedback:
1. If they ask to add: KEEP existing + ADD new features
2. If they ask to remove: REMOVE specific features
3. If they ask to modify: UPDATE existing features
4. If they want to replace: CREATE new plan

When in doubt, KEEP existing features and ADD to them!
"""
        
        return f"""Refine the feature plan based on user feedback:

ORIGINAL PROBLEM:
{problem_statement}

PREVIOUS FEATURE PLAN (Current features the user approved so far):
{json.dumps(previous_plan, indent=2)}

USER FEEDBACK:
{user_feedback}

{instruction}

**Action Steps:**
1. Carefully read the user feedback to understand their intent
2. Determine if they want to ADD, REMOVE, MODIFY, or REPLACE features
3. If adding: Include ALL existing features + new features
4. If removing: Include all features EXCEPT the ones to remove
5. If modifying: Update the specific features mentioned
6. If replacing: Create a completely new plan

**CRITICAL RULES:**
- When user says "add", "also want", "more features", "additional" → KEEP all existing features AND add new ones
- Only remove features if user explicitly says "remove", "don't want", or "delete"
- Only replace entire plan if user says "instead", "replace all", or "only these features"
- Maintain consistency in tech stack and database choices unless user requests changes
- Generate unique IDs for any new features
- Keep existing feature IDs unchanged

Provide the complete updated feature plan in JSON format with ALL features that should be in the final plan."""
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured format"""
        try:
            # Try to extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                logger.warning("no_json_found_in_response", response_preview=response[:200])
                raise ValueError("No JSON found in response")
            
            json_str = response[start_idx:end_idx]
            result = json.loads(json_str)
            
            # Ensure required fields exist with defaults if missing or empty
            if not result.get("database_type") or str(result.get("database_type", "")).strip() == "":
                result["database_type"] = "auto"
            
            if not result.get("estimated_complexity") or str(result.get("estimated_complexity", "")).strip() == "":
                result["estimated_complexity"] = "medium"
            
            # Validate and fix database_type
            valid_db_types = ["postgresql", "mongodb", "auto"]
            current_db = str(result.get("database_type", "auto")).lower().strip()
            
            # Check if it's already valid
            if current_db in valid_db_types:
                result["database_type"] = current_db
            else:
                # Not valid, try to infer from database field in tech_stack
                db = str(result.get("tech_stack", {}).get("database", "")).lower()
                if "postgres" in db or "sql" in db:
                    result["database_type"] = "postgresql"
                elif "mongo" in db:
                    result["database_type"] = "mongodb"
                else:
                    # Default to auto for any unclear cases
                    result["database_type"] = "auto"
            
            logger.debug(f"database_type normalized: {current_db} -> {result['database_type']}")
            
            # Validate and fix estimated_complexity
            valid_complexity = ["simple", "medium", "complex"]
            current_complexity = str(result.get("estimated_complexity", "medium")).lower().strip()
            
            # Check if it's already valid
            if current_complexity in valid_complexity:
                result["estimated_complexity"] = current_complexity
            else:
                # Map common values and invalid ones to valid values
                complexity_map = {
                    "low": "simple",
                    "high": "complex",
                    "easy": "simple",
                    "hard": "complex",
                    "difficult": "complex"
                }
                
                # Default everything else to medium (including "unknown", "not determined", etc.)
                result["estimated_complexity"] = complexity_map.get(current_complexity, "medium")
            
            logger.debug(f"estimated_complexity normalized: {current_complexity} -> {result['estimated_complexity']}")
            
            # Generate unique IDs for features if not present and validate priorities
            if "features" in result:
                for feature in result["features"]:
                    if "id" not in feature:
                        feature["id"] = str(uuid.uuid4())[:8]
                    
                    # Validate and fix priority (handle null, empty, invalid)
                    priority = str(feature.get("priority", "medium")).lower().strip()
                    
                    # Handle string "null" and other invalid values
                    if priority in ["null", "none", ""] or priority not in ["high", "medium", "low"]:
                        feature["priority"] = "medium"
                    else:
                        feature["priority"] = priority
            
            return result
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("failed_to_parse_json", error=str(e), response=response[:500])
            
            # Try to extract features from text if JSON parsing failed
            features_from_text = self._extract_features_from_text(response)
            
            # Return a basic structure with extracted features
            return {
                "reasoning": "Extracted from conversational response",
                "problem_summary": "Todo application with task management",
                "features": features_from_text,
                "tech_stack": {
                    "frontend": "Next.js 14 + TypeScript + Tailwind CSS",
                    "backend": "Next.js API Routes",
                    "database": "PostgreSQL",
                    "styling": "Tailwind CSS"
                },
                "database_type": "postgresql",
                "estimated_complexity": "medium",
                "notes": "Features extracted from response"
            }
    
    def _extract_features_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract features from plain text when JSON parsing fails"""
        features = []
        
        # Common feature titles to look for
        feature_keywords = [
            ("task management", "CRUD operations for tasks"),
            ("user authentication", "Secure login and registration"),
            ("task deletion", "Delete tasks from the list"),
            ("task modification", "Edit and update existing tasks"),
            ("todo list ui", "User interface for task management"),
            ("task notifications", "Notifications for due tasks")
        ]
        
        text_lower = text.lower()
        
        for title, description in feature_keywords:
            if title in text_lower:
                features.append({
                    "id": str(uuid.uuid4())[:8],
                    "title": title.title(),
                    "description": description,
                    "priority": "high" if "high" in text_lower or "must" in text_lower else "medium",
                    "category": "core"
                })
        
        # If no features extracted, provide default todo app features
        if not features:
            features = [
                {
                    "id": str(uuid.uuid4())[:8],
                    "title": "Task Management",
                    "description": "Create, read, update, and delete tasks",
                    "priority": "high",
                    "category": "core"
                },
                {
                    "id": str(uuid.uuid4())[:8],
                    "title": "Todo List UI",
                    "description": "User interface to display and manage tasks",
                    "priority": "high",
                    "category": "ui"
                },
                {
                    "id": str(uuid.uuid4())[:8],
                    "title": "User Authentication",
                    "description": "Secure login and registration system",
                    "priority": "medium",
                    "category": "authentication"
                },
                {
                    "id": str(uuid.uuid4())[:8],
                    "title": "Task Notifications",
                    "description": "Notifications for due or overdue tasks",
                    "priority": "low",
                    "category": "notifications"
                }
            ]
        
        return features

